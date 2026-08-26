#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
這份測試會檢查 API 對外服務是否如預期回應。
重點包含健康檢查、檔案上傳、任務查詢與排隊資訊，
確保前端或外部系統呼叫時能得到正確且一致的結果。

測試流程（給非技術同仁快速理解）：
1) 先模擬後端依賴服務，避免測試誤傷真實環境。
2) 依序驗證健康檢查、設定讀取、上傳、查詢、取消等端點。
3) 對每個端點同時驗證「正常回應」與「失敗回應」。

關鍵分支與錯誤情境：
- 上傳檔案格式不支援、檔案過大、處理模式錯誤。
- 雲端模式未配置 Gemini 金鑰。
- 任務不存在、任務尚未完成、佇列滿載無法收件。
"""
import os
import sys
import io
import types
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient

# 每次測試使用獨立資料夾，避免互相污染。
os.environ['DATA_DIR'] = tempfile.mkdtemp()

# 加入專案根目錄到匯入路徑，確保可直接載入 backend/src 模組。
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.models.schemas import (
    TaskStatus, ProcessingMode, TaskInfo, QueueStatus,
    UploadResponse, HealthStatus
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_services():
    """Mock all external services used by routes."""
    with patch('backend.api.routes.device_detector') as mock_device, \
         patch('backend.api.routes.task_queue') as mock_queue, \
         patch('backend.api.routes.file_manager') as mock_file, \
         patch('backend.api.routes.summarization_service') as mock_summary:
        
        # Setup device_detector mock
        mock_device.detect_best_device.return_value = None
        mock_device.get_device_info.return_value = {
            "current_device": "cpu",
            "compute_type": "int8",
            "fallback_count": 0,
            "gpu_name": None,
            "gpu_memory_mb": None,
            "gpu_available": False,
            "mps_available": False
        }
        
        # Setup summarization_service mock
        mock_summary.check_ollama_health = AsyncMock(return_value=True)
        mock_summary.check_lmstudio_health = AsyncMock(return_value=False)
        mock_summary.check_gemini_available.return_value = False
        mock_summary.get_effective_local_model.return_value = "gemma4:31b"
        mock_summary.get_local_llm_health.return_value = {
            "provider": "lmstudio",
            "server_reachable": True,
            "selection_status": "LMSTUDIO_NO_LOADED_LLM",
            "loaded_llm_count": 0,
            "selected_model": None,
            "context_length": None,
        }
        
        # Setup task_queue mock
        mock_queue.get_queue_status.return_value = QueueStatus(
            total_queued=0,
            processing_count=0,
            estimated_wait_seconds=0,
            max_concurrent=1,
            queue_max_size=50
        )
        
        yield {
            'device_detector': mock_device,
            'task_queue': mock_queue,
            'file_manager': mock_file,
            'summarization_service': mock_summary
        }


@pytest.fixture
def test_client(mock_services):
    """Create a test client with mocked services."""
    from fastapi import FastAPI
    from backend.api.routes import router
    
    app = FastAPI()
    app.include_router(router)
    
    return TestClient(app)


@pytest.fixture
def sample_task_info():
    """Create a sample TaskInfo for testing."""
    return TaskInfo(
        task_id="test1234",
        filename="test_abc123.mp3",
        original_filename="test_audio.mp3",
        file_size=1024000,
        status=TaskStatus.QUEUED,
        queue_position=1,
        estimated_wait_seconds=60,
        processing_mode=ProcessingMode.LOCAL
    )


# =============================================================================
# Health Check Endpoint Tests
# =============================================================================

class TestHealthCheckEndpoint:
    """Tests for GET /api/health endpoint."""
    
    def test_health_check_success(self, test_client, mock_services):
        """Test successful health check."""
        response = test_client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "gpu_available" in data
        assert "queue_status" in data
    
    def test_health_check_with_gpu(self, test_client, mock_services):
        """Test health check with GPU available."""
        mock_services['device_detector'].get_device_info.return_value = {
            "current_device": "cuda",
            "compute_type": "float16",
            "fallback_count": 0,
            "gpu_name": "NVIDIA GeForce RTX 3080",
            "gpu_memory_mb": 10000,
            "gpu_available": True,
            "mps_available": False
        }
        
        response = test_client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["gpu_available"] is True
        assert data["gpu_name"] == "NVIDIA GeForce RTX 3080"
    
    def test_health_check_ollama_unavailable(self, test_client, mock_services):
        """Test health check when Ollama is unavailable."""
        mock_services['summarization_service'].check_ollama_health = AsyncMock(return_value=False)
        
        response = test_client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["ollama_available"] is False
    
    def test_health_check_gemini_available(self, test_client, mock_services):
        """Test health check when Gemini is available."""
        mock_services['summarization_service'].check_gemini_available.return_value = True
        
        response = test_client.get("/api/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["gemini_available"] is True

    def test_health_check_includes_additive_lmstudio_selection_status(self, test_client, mock_services):
        response = test_client.get("/api/health")

        assert response.status_code == 200
        assert response.json()["device_info"]["llm"]["selection_status"] == "LMSTUDIO_NO_LOADED_LLM"


# =============================================================================
# Config Endpoint Tests
# =============================================================================

class TestConfigEndpoint:
    """Tests for GET /api/config endpoint."""
    
    def test_get_config_success(self, test_client, mock_services):
        """Test successful config retrieval."""
        response = test_client.get("/api/config")
        
        assert response.status_code == 200
        data = response.json()
        assert "max_file_size_mb" in data
        assert "enable_batch_upload" in data
        assert "allowed_extensions" in data
        assert "max_concurrent_tasks" in data
        assert "queue_max_size" in data
        assert "default_mode" in data
        assert "asr_backend" in data
        assert "whisper_model" in data
        assert "whisper_model_revision" in data
    
    def test_config_contains_gemini_availability(self, test_client, mock_services):
        """Test config includes Gemini availability."""
        response = test_client.get("/api/config")
        
        assert response.status_code == 200
        data = response.json()
        assert "gemini_available" in data

    def test_config_exposes_effective_mlx_revision_on_mac_auto(self, test_client, mock_services, monkeypatch):
        """Mac auto config exposes the effective MLX model and pinned revision."""
        from backend.core.config import settings

        monkeypatch.setattr(settings, "WHISPER_MODEL", "MediaTek-Research/Breeze-ASR-26")
        monkeypatch.setattr(settings, "WHISPER_MODEL_REVISION", None)

        response = test_client.get("/api/config")

        assert response.status_code == 200
        data = response.json()
        assert data["effective_asr_backend"] == "mlx_whisper"
        assert data["effective_whisper_model"] == "doggy8088/Breeze-ASR-26-MLX"
        assert data["whisper_model_revision"] == "619860a64925c0f0dfecdbb5f8d9a2da2df1bc12"


# =============================================================================
# Upload Endpoint Tests
# =============================================================================

class TestUploadEndpoint:
    """Tests for POST /api/upload endpoint."""
    
    def test_upload_success(self, test_client, mock_services, sample_task_info):
        """Test successful file upload."""
        # Setup mocks
        mock_services['file_manager'].validate_file.return_value = (True, "")
        mock_services['file_manager'].validate_file_size = AsyncMock(return_value=(True, "", 1024000))
        mock_services['file_manager'].save_upload = AsyncMock(
            return_value=("/tmp/test.mp3", "test_abc123.mp3", 1024000)
        )
        mock_services['task_queue'].add_task = AsyncMock(return_value=sample_task_info)
        
        # Create test file
        files = {'file': ('test_audio.mp3', b'test audio content', 'audio/mpeg')}
        data = {'processing_mode': 'local'}
        
        response = test_client.post("/api/upload", files=files, data=data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["task_id"] == "test1234"
        assert result["filename"] == "test_audio.mp3"
    
    def test_upload_invalid_format(self, test_client, mock_services):
        """Test upload with invalid file format."""
        mock_services['file_manager'].validate_file.return_value = (False, "不支援的檔案格式: .xyz")
        
        files = {'file': ('test.xyz', b'test content', 'application/octet-stream')}
        data = {'processing_mode': 'local'}
        
        response = test_client.post("/api/upload", files=files, data=data)
        
        assert response.status_code == 400
        assert "不支援的檔案格式" in response.json()["detail"]
    
    def test_upload_file_too_large(self, test_client, mock_services):
        """Test upload with file exceeding size limit."""
        mock_services['file_manager'].validate_file.return_value = (True, "")
        mock_services['file_manager'].validate_file_size = AsyncMock(
            return_value=(False, "檔案大小超過限制: 150.0MB > 100MB", 157286400)
        )
        
        files = {'file': ('test.mp3', b'large content', 'audio/mpeg')}
        data = {'processing_mode': 'local'}
        
        response = test_client.post("/api/upload", files=files, data=data)
        
        assert response.status_code == 413
        assert "檔案大小超過限制" in response.json()["detail"]
    
    def test_upload_local_only_template_rejects_cloud(self, test_client, mock_services):
        """採購評選會模板（local_only）＋雲端模式 → 400（v4.4.0 機敏防線）。"""
        mock_services['file_manager'].validate_file.return_value = (True, "")
        mock_services['file_manager'].validate_file_size = AsyncMock(return_value=(True, "", 1024))
        mock_services['summarization_service'].check_gemini_available.return_value = True

        files = {'file': ('meeting.mp3', b'fake audio', 'audio/mpeg')}
        data = {'processing_mode': 'cloud', 'meeting_template': 'procurement_evaluation'}

        response = test_client.post("/api/upload", files=files, data=data)

        assert response.status_code == 400
        assert "僅限本地模式" in response.json()["detail"]

    def test_upload_unknown_template_rejected(self, test_client, mock_services):
        """未知會議模板 → 400（v4.4.0）。"""
        mock_services['file_manager'].validate_file.return_value = (True, "")
        mock_services['file_manager'].validate_file_size = AsyncMock(return_value=(True, "", 1024))

        files = {'file': ('meeting.mp3', b'fake audio', 'audio/mpeg')}
        data = {'processing_mode': 'local', 'meeting_template': 'no_such_template'}

        response = test_client.post("/api/upload", files=files, data=data)

        assert response.status_code == 400
        assert "無效的會議類型" in response.json()["detail"]

    def test_upload_default_template_is_general(self, test_client, mock_services, sample_task_info):
        """未帶 meeting_template 時預設 general（向下相容 v4.3.3 行為）。"""
        mock_services['file_manager'].validate_file.return_value = (True, "")
        mock_services['file_manager'].validate_file_size = AsyncMock(return_value=(True, "", 1024000))
        mock_services['file_manager'].save_upload = AsyncMock(
            return_value=("/tmp/test.mp3", "test_abc123.mp3", 1024000)
        )
        mock_services['task_queue'].add_task = AsyncMock(return_value=sample_task_info)

        files = {'file': ('test_audio.mp3', b'test audio content', 'audio/mpeg')}
        response = test_client.post("/api/upload", files=files, data={'processing_mode': 'local'})

        assert response.status_code == 200
        _, kwargs = mock_services['task_queue'].add_task.call_args
        assert kwargs["template_id"] == "general"

    def test_upload_procurement_local_mode_accepted(self, test_client, mock_services, sample_task_info):
        """採購評選會模板＋本地模式 → 正常入列，template_id 正確傳遞。"""
        mock_services['file_manager'].validate_file.return_value = (True, "")
        mock_services['file_manager'].validate_file_size = AsyncMock(return_value=(True, "", 1024000))
        mock_services['file_manager'].save_upload = AsyncMock(
            return_value=("/tmp/test.mp3", "test_abc123.mp3", 1024000)
        )
        mock_services['task_queue'].add_task = AsyncMock(return_value=sample_task_info)

        files = {'file': ('meeting.mp3', b'fake audio', 'audio/mpeg')}
        data = {'processing_mode': 'local', 'meeting_template': 'procurement_evaluation'}
        response = test_client.post("/api/upload", files=files, data=data)

        assert response.status_code == 200
        _, kwargs = mock_services['task_queue'].add_task.call_args
        assert kwargs["template_id"] == "procurement_evaluation"

    def test_config_exposes_meeting_templates(self, test_client, mock_services):
        """/api/config 下發模板清單（前端選單資料來源，v4.4.0）。"""
        response = test_client.get("/api/config")

        assert response.status_code == 200
        payload = response.json()
        assert payload["default_meeting_template"] == "general"
        ids = [t["id"] for t in payload["meeting_templates"]]
        assert "general" in ids and "procurement_evaluation" in ids
        procurement = next(t for t in payload["meeting_templates"] if t["id"] == "procurement_evaluation")
        assert procurement["local_only"] is True

    def test_upload_invalid_processing_mode(self, test_client, mock_services):
        """Test upload with invalid processing mode."""
        mock_services['file_manager'].validate_file.return_value = (True, "")
        mock_services['file_manager'].validate_file_size = AsyncMock(return_value=(True, "", 1024))

        files = {'file': ('test.mp3', b'test content', 'audio/mpeg')}
        data = {'processing_mode': 'invalid_mode'}

        response = test_client.post("/api/upload", files=files, data=data)

        assert response.status_code == 400
        assert "無效的處理模式" in response.json()["detail"]
    
    def test_upload_cloud_mode_without_gemini_key(self, test_client, mock_services):
        """Test cloud mode upload when Gemini API key is not configured."""
        mock_services['file_manager'].validate_file.return_value = (True, "")
        mock_services['file_manager'].validate_file_size = AsyncMock(return_value=(True, "", 1024))
        mock_services['summarization_service'].check_gemini_available.return_value = False
        
        files = {'file': ('test.mp3', b'test content', 'audio/mpeg')}
        data = {'processing_mode': 'cloud'}
        
        response = test_client.post("/api/upload", files=files, data=data)
        
        assert response.status_code == 400
        assert "Gemini API Key" in response.json()["detail"]
    
    def test_upload_queue_full(self, test_client, mock_services):
        """Test upload when queue is full."""
        mock_services['file_manager'].validate_file.return_value = (True, "")
        mock_services['file_manager'].validate_file_size = AsyncMock(return_value=(True, "", 1024))
        mock_services['file_manager'].save_upload = AsyncMock(
            return_value=("/tmp/test.mp3", "test.mp3", 1024)
        )
        mock_services['task_queue'].add_task = AsyncMock(return_value=None)
        mock_services['file_manager'].delete_file.return_value = True
        
        files = {'file': ('test.mp3', b'test content', 'audio/mpeg')}
        data = {'processing_mode': 'local'}
        
        response = test_client.post("/api/upload", files=files, data=data)
        
        assert response.status_code == 503
        assert "系統繁忙" in response.json()["detail"]
    
    def test_upload_with_user_prompt(self, test_client, mock_services, sample_task_info):
        """Test upload with custom user prompt."""
        mock_services['file_manager'].validate_file.return_value = (True, "")
        mock_services['file_manager'].validate_file_size = AsyncMock(return_value=(True, "", 1024))
        mock_services['file_manager'].save_upload = AsyncMock(
            return_value=("/tmp/test.mp3", "test.mp3", 1024)
        )
        mock_services['task_queue'].add_task = AsyncMock(return_value=sample_task_info)
        
        files = {'file': ('test.mp3', b'test content', 'audio/mpeg')}
        data = {'processing_mode': 'local', 'user_prompt': '請特別注意技術討論'}
        
        response = test_client.post("/api/upload", files=files, data=data)
        
        assert response.status_code == 200
        # Verify add_task was called with user_prompt
        mock_services['task_queue'].add_task.assert_called_once()
        call_kwargs = mock_services['task_queue'].add_task.call_args.kwargs
        assert call_kwargs['user_prompt'] == '請特別注意技術討論'

    def test_upload_reuses_preloaded_file_content(self, test_client, mock_services, sample_task_info):
        """Test upload route passes preloaded bytes to save_upload when available."""
        preloaded_content = b"audio-bytes"
        mock_services['file_manager'].validate_file.return_value = (True, "")
        mock_services['file_manager'].validate_file_size = AsyncMock(
            return_value=(True, "", len(preloaded_content), preloaded_content)
        )
        mock_services['file_manager'].save_upload = AsyncMock(
            return_value=("/tmp/test.mp3", "test.mp3", len(preloaded_content))
        )
        mock_services['task_queue'].add_task = AsyncMock(return_value=sample_task_info)

        files = {'file': ('test.mp3', preloaded_content, 'audio/mpeg')}
        data = {'processing_mode': 'local'}

        response = test_client.post("/api/upload", files=files, data=data)

        assert response.status_code == 200
        assert mock_services['file_manager'].save_upload.await_args.kwargs["content"] == preloaded_content


# =============================================================================
# Task Status Endpoint Tests
# =============================================================================

class TestTaskStatusEndpoint:
    """Tests for GET /api/tasks/{task_id} endpoint."""
    
    def test_get_task_success(self, test_client, mock_services, sample_task_info):
        """Test successful task status retrieval."""
        mock_services['task_queue'].get_task.return_value = sample_task_info
        mock_services['task_queue'].get_task_position.return_value = 1
        
        response = test_client.get("/api/tasks/test1234")
        
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "test1234"
        assert data["status"] == "queued"
    
    def test_get_task_not_found(self, test_client, mock_services):
        """Test getting non-existent task."""
        mock_services['task_queue'].get_task.return_value = None
        
        response = test_client.get("/api/tasks/nonexistent")
        
        assert response.status_code == 404
        assert "找不到任務" in response.json()["detail"]
    
    def test_get_task_updates_queue_position(self, test_client, mock_services, sample_task_info):
        """Test that queue position is updated when getting task."""
        mock_services['task_queue'].get_task.return_value = sample_task_info
        mock_services['task_queue'].get_task_position.return_value = 3
        
        response = test_client.get("/api/tasks/test1234")
        
        assert response.status_code == 200
        data = response.json()
        assert data["queue_position"] == 3


# =============================================================================
# Task Result Endpoint Tests
# =============================================================================

class TestTaskResultEndpoint:
    """Tests for GET /api/tasks/{task_id}/result endpoint."""
    
    def test_get_result_not_found(self, test_client, mock_services):
        """Test getting result for non-existent task."""
        mock_services['task_queue'].get_task.return_value = None
        
        response = test_client.get("/api/tasks/nonexistent/result")
        
        assert response.status_code == 404
        assert "找不到任務" in response.json()["detail"]
    
    def test_get_result_task_not_completed(self, test_client, mock_services, sample_task_info):
        """Test getting result for incomplete task."""
        sample_task_info.status = TaskStatus.TRANSCRIBING
        mock_services['task_queue'].get_task.return_value = sample_task_info
        
        response = test_client.get("/api/tasks/test1234/result")
        
        assert response.status_code == 400
        assert "任務尚未完成" in response.json()["detail"]
    
    def test_get_result_file_not_found(self, test_client, mock_services, sample_task_info):
        """Test getting result when file doesn't exist."""
        sample_task_info.status = TaskStatus.COMPLETED
        mock_services['task_queue'].get_task.return_value = sample_task_info
        
        response = test_client.get("/api/tasks/test1234/result")
        
        # The result file won't exist, so should return 404
        assert response.status_code == 404
        assert "結果檔案不存在" in response.json()["detail"]
    
    def test_get_result_success(self, test_client, mock_services, sample_task_info):
        """Test successful result retrieval."""
        sample_task_info.status = TaskStatus.COMPLETED
        mock_services['task_queue'].get_task.return_value = sample_task_info
        
        # Create a temporary result file
        from backend.core.config import settings
        os.makedirs(settings.outputs_dir, exist_ok=True)
        result_file = os.path.join(settings.outputs_dir, "test_audio_test1234.md")
        with open(result_file, 'w', encoding='utf-8') as f:
            f.write("# 會議記錄\n\n測試內容")
        
        try:
            response = test_client.get("/api/tasks/test1234/result")
            
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/markdown; charset=utf-8"
            # v4.2.3：下載檔名統一為 YYYYMMDDhhmmss_會議紀錄（中文檔名以 RFC 5987 編碼）
            from urllib.parse import quote
            stamp = sample_task_info.created_at.strftime("%Y%m%d%H%M%S")
            expected = f"attachment; filename*=utf-8''{quote(f'{stamp}_會議紀錄.md')}"
            assert response.headers["content-disposition"] == expected
        finally:
            # Cleanup
            if os.path.exists(result_file):
                os.remove(result_file)

    def test_get_result_invalid_format(self, test_client):
        """Test getting result with unsupported format."""
        response = test_client.get("/api/tasks/test1234/result?format=pdf")

        assert response.status_code == 400
        assert "不支援的格式" in response.json()["detail"]

    def test_get_result_docx_success(self, test_client, mock_services, sample_task_info):
        """Test successful DOCX result retrieval."""
        sample_task_info.status = TaskStatus.COMPLETED
        mock_services['task_queue'].get_task.return_value = sample_task_info

        from backend.core.config import settings
        os.makedirs(settings.outputs_dir, exist_ok=True)
        result_file = os.path.join(settings.outputs_dir, "test_audio_test1234.md")
        docx_file = os.path.join(settings.outputs_dir, "test_audio_test1234.docx")

        with open(result_file, 'w', encoding='utf-8') as f:
            f.write("# 會議記錄\n\n測試內容")

        fake_module = types.ModuleType("backend.services.docx_converter")
        fake_converter = MagicMock()

        def fake_convert(md_content, output_path, template_id="general"):
            assert "# 會議記錄" in md_content
            with open(output_path, 'wb') as f:
                f.write(b"fake docx")
            return output_path

        fake_converter.convert.side_effect = fake_convert
        fake_module.docx_converter = fake_converter

        try:
            with patch.dict(sys.modules, {"backend.services.docx_converter": fake_module}):
                response = test_client.get("/api/tasks/test1234/result?format=docx")

            assert response.status_code == 200
            assert response.headers["content-type"].startswith(
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            from urllib.parse import quote
            stamp = sample_task_info.created_at.strftime("%Y%m%d%H%M%S")
            expected = f"attachment; filename*=utf-8''{quote(f'{stamp}_會議紀錄.docx')}"
            assert response.headers["content-disposition"] == expected
            assert os.path.exists(docx_file)
            fake_converter.convert.assert_called_once()
        finally:
            for path in (result_file, docx_file):
                if os.path.exists(path):
                    os.remove(path)

    def test_get_result_invalid_doc_param(self, test_client, mock_services):
        """doc 參數非法值 → 400（v4.5.0）。"""
        response = test_client.get("/api/tasks/test1234/result?doc=banana")

        assert response.status_code == 400
        assert "不支援的文件種類" in response.json()["detail"]

    def test_get_result_attachment_requires_docx(self, test_client, mock_services):
        """附件僅支援 docx 格式（v4.5.0）。"""
        response = test_client.get("/api/tasks/test1234/result?format=md&doc=attachment")

        assert response.status_code == 400
        assert "附件僅支援 docx" in response.json()["detail"]

    def test_get_result_attachment_rejected_for_general(self, test_client, mock_services, sample_task_info):
        """general 模板無附件定義 → 400（v4.5.0）。"""
        sample_task_info.status = TaskStatus.COMPLETED
        mock_services['task_queue'].get_task.return_value = sample_task_info

        from backend.core.config import settings
        os.makedirs(settings.outputs_dir, exist_ok=True)
        result_file = os.path.join(settings.outputs_dir, "test_audio_test1234.md")
        with open(result_file, 'w', encoding='utf-8') as f:
            f.write("# 會議記錄\n\n測試內容")

        try:
            response = test_client.get("/api/tasks/test1234/result?format=docx&doc=attachment")

            assert response.status_code == 400
            assert "無列管附件" in response.json()["detail"]
        finally:
            if os.path.exists(result_file):
                os.remove(result_file)

    def test_get_result_attachment_section_meeting_success(self, test_client, mock_services, sample_task_info):
        """科務會議附件下載：由本文抽出列管資料再轉 docx（v4.5.0）。"""
        sample_task_info.status = TaskStatus.COMPLETED
        sample_task_info.template_id = "section_meeting"
        mock_services['task_queue'].get_task.return_value = sample_task_info

        from backend.core.config import settings
        os.makedirs(settings.outputs_dir, exist_ok=True)
        result_file = os.path.join(settings.outputs_dir, "test_audio_test1234.md")
        attachment_file = os.path.join(settings.outputs_dir, "test_audio_test1234_attachment.docx")

        record_md = (
            "嘉義縣財政稅務局電子作業科115年7月份第1次科務會議紀錄\n"
            "歷次科務會議決議事項繼續列管案件：無\n"
            "115年7月份第1次科務會議決議事項辦理情形彙整表\n"
            "決議事項：\n"
            "| 案由及承辦單位 | 辦理情形 | 解除列管 | 繼續列管 |\n"
            "| --- | --- | --- | --- |\n"
            "| 實地評核筆電準備，請資管股負責 | 資管股： |  |  |\n"
            "一、科長轉知局務會議工作報告及相關注意事項：（略）\n"
            "散會：上午11時58分"
        )
        with open(result_file, 'w', encoding='utf-8') as f:
            f.write(record_md)

        fake_module = types.ModuleType("backend.services.docx_converter")
        fake_converter = MagicMock()

        def fake_convert(md_content, output_path, template_id="general"):
            # 傳入的必須是「抽出後的附件 md」而非本文 md
            assert template_id == "section_meeting"
            assert "歷次科務會議決議事項繼續列管案件" in md_content
            assert "| 無 |  |  |  |" in md_content
            assert "| 實地評核筆電準備，請資管股負責 | 資管股： |  |  |" in md_content
            assert "一、科長轉知" not in md_content  # 條列內容不得混入附件
            with open(output_path, 'wb') as f:
                f.write(b"fake attachment docx")
            return output_path

        fake_converter.convert.side_effect = fake_convert
        fake_module.docx_converter = fake_converter

        try:
            with patch.dict(sys.modules, {"backend.services.docx_converter": fake_module}):
                response = test_client.get("/api/tasks/test1234/result?format=docx&doc=attachment")

            assert response.status_code == 200
            from urllib.parse import quote
            stamp = sample_task_info.created_at.strftime("%Y%m%d%H%M%S")
            expected = f"attachment; filename*=utf-8''{quote(f'{stamp}_科務會議列管資料.docx')}"
            assert response.headers["content-disposition"] == expected
            assert os.path.exists(attachment_file)
            fake_converter.convert.assert_called_once()
        finally:
            for path in (result_file, attachment_file):
                if os.path.exists(path):
                    os.remove(path)

    def test_config_exposes_attachment_info(self, test_client, mock_services):
        """/api/config 模板清單含附件資訊（前端附件按鈕資料來源，v4.5.0）。"""
        response = test_client.get("/api/config")

        assert response.status_code == 200
        templates = {t["id"]: t for t in response.json()["meeting_templates"]}
        assert templates["section_meeting"]["has_attachment"] is True
        assert templates["section_meeting"]["attachment_label"] == "列管資料"
        assert templates["general"]["has_attachment"] is False

    def test_get_result_docx_conversion_failure(self, test_client, mock_services, sample_task_info):
        """Test DOCX conversion failure is reported as 500."""
        sample_task_info.status = TaskStatus.COMPLETED
        mock_services['task_queue'].get_task.return_value = sample_task_info

        from backend.core.config import settings
        os.makedirs(settings.outputs_dir, exist_ok=True)
        result_file = os.path.join(settings.outputs_dir, "test_audio_test1234.md")
        docx_file = os.path.join(settings.outputs_dir, "test_audio_test1234.docx")

        with open(result_file, 'w', encoding='utf-8') as f:
            f.write("# 會議記錄\n\n測試內容")

        fake_module = types.ModuleType("backend.services.docx_converter")
        fake_converter = MagicMock()
        fake_converter.convert.side_effect = RuntimeError("boom")
        fake_module.docx_converter = fake_converter

        try:
            with patch.dict(sys.modules, {"backend.services.docx_converter": fake_module}):
                response = test_client.get("/api/tasks/test1234/result?format=docx")

            assert response.status_code == 500
            assert "DOCX 轉換失敗" in response.json()["detail"]
        finally:
            for path in (result_file, docx_file):
                if os.path.exists(path):
                    os.remove(path)

    def test_get_result_docx_import_failure(self, test_client, mock_services, sample_task_info):
        """Test DOCX import failure (missing python-docx) is reported as 500."""
        sample_task_info.status = TaskStatus.COMPLETED
        mock_services['task_queue'].get_task.return_value = sample_task_info

        from backend.core.config import settings
        os.makedirs(settings.outputs_dir, exist_ok=True)
        result_file = os.path.join(settings.outputs_dir, "test_audio_test1234.md")
        docx_file = os.path.join(settings.outputs_dir, "test_audio_test1234.docx")

        with open(result_file, 'w', encoding='utf-8') as f:
            f.write("# 會議記錄\n\n測試內容")

        # Simulate the module being missing entirely so the import inside
        # the route handler raises ImportError.
        import importlib
        saved = sys.modules.pop("backend.services.docx_converter", None)

        def _raise_import(name, *a, **kw):
            if name == "backend.services.docx_converter":
                raise ImportError("No module named 'docx'")
            return original_import(name, *a, **kw)

        import builtins
        original_import = builtins.__import__

        try:
            # Remove cached module so the in-function import re-executes
            sys.modules.pop("backend.services.docx_converter", None)
            with patch("builtins.__import__", side_effect=_raise_import):
                response = test_client.get("/api/tasks/test1234/result?format=docx")

            assert response.status_code == 500
            body = response.json()
            assert "python-docx" in body["detail"] or "DOCX" in body["detail"]
        finally:
            if saved is not None:
                sys.modules["backend.services.docx_converter"] = saved
            for path in (result_file, docx_file):
                if os.path.exists(path):
                    os.remove(path)


# =============================================================================
# Cancel Task Endpoint Tests
# =============================================================================

class TestCancelTaskEndpoint:
    """Tests for DELETE /api/tasks/{task_id} endpoint."""
    
    def test_cancel_task_not_found(self, test_client, mock_services):
        """Test cancelling non-existent task."""
        mock_services['task_queue'].get_task.return_value = None
        
        response = test_client.delete("/api/tasks/nonexistent")
        
        assert response.status_code == 404
        assert "找不到任務" in response.json()["detail"]
    
    def test_cancel_already_completed_task(self, test_client, mock_services, sample_task_info):
        """Test cancelling already completed task."""
        sample_task_info.status = TaskStatus.COMPLETED
        mock_services['task_queue'].get_task.return_value = sample_task_info
        
        response = test_client.delete("/api/tasks/test1234")
        
        assert response.status_code == 400
        assert "任務已經結束" in response.json()["detail"]
    
    def test_cancel_failed_task(self, test_client, mock_services, sample_task_info):
        """Test cancelling failed task."""
        sample_task_info.status = TaskStatus.FAILED
        mock_services['task_queue'].get_task.return_value = sample_task_info
        
        response = test_client.delete("/api/tasks/test1234")
        
        assert response.status_code == 400
        assert "任務已經結束" in response.json()["detail"]
    
    def test_cancel_processing_task_fails(self, test_client, mock_services, sample_task_info):
        """Test cancelling task that is currently processing."""
        sample_task_info.status = TaskStatus.TRANSCRIBING
        mock_services['task_queue'].get_task.return_value = sample_task_info
        mock_services['task_queue'].cancel_task = AsyncMock(return_value=False)
        
        response = test_client.delete("/api/tasks/test1234")
        
        assert response.status_code == 400
        assert "無法取消任務" in response.json()["detail"]
    
    def test_cancel_queued_task_success(self, test_client, mock_services, sample_task_info):
        """Test successfully cancelling queued task."""
        sample_task_info.status = TaskStatus.QUEUED
        mock_services['task_queue'].get_task.return_value = sample_task_info
        mock_services['task_queue'].cancel_task = AsyncMock(return_value=True)
        
        response = test_client.delete("/api/tasks/test1234")
        
        assert response.status_code == 200
        assert "已取消" in response.json()["message"]


# =============================================================================
# Queue Status Endpoint Tests
# =============================================================================

class TestQueueStatusEndpoint:
    """Tests for GET /api/queue/status endpoint."""
    
    def test_get_queue_status_empty(self, test_client, mock_services):
        """Test queue status when queue is empty."""
        response = test_client.get("/api/queue/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_queued"] == 0
        assert data["processing_count"] == 0
    
    def test_get_queue_status_with_tasks(self, test_client, mock_services):
        """Test queue status with tasks in queue."""
        mock_services['task_queue'].get_queue_status.return_value = QueueStatus(
            total_queued=5,
            processing_count=1,
            estimated_wait_seconds=1200,
            max_concurrent=1,
            queue_max_size=50
        )
        
        response = test_client.get("/api/queue/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_queued"] == 5
        assert data["processing_count"] == 1
        assert data["estimated_wait_seconds"] == 1200


# =============================================================================
# Queue Position Endpoint Tests
# =============================================================================

class TestQueuePositionEndpoint:
    """Tests for GET /api/queue/position/{task_id} endpoint."""
    
    def test_get_queue_position_not_found(self, test_client, mock_services):
        """Test getting position for non-existent task."""
        mock_services['task_queue'].get_task.return_value = None
        
        response = test_client.get("/api/queue/position/nonexistent")
        
        assert response.status_code == 404
        assert "找不到任務" in response.json()["detail"]
    
    def test_get_queue_position_success(self, test_client, mock_services, sample_task_info):
        """Test successfully getting queue position."""
        mock_services['task_queue'].get_task.return_value = sample_task_info
        mock_services['task_queue'].get_task_position.return_value = 3
        
        response = test_client.get("/api/queue/position/test1234")
        
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "test1234"
        assert data["position"] == 3
        assert "total_queued" in data
        assert "status" in data
    
    def test_get_queue_position_no_longer_in_queue(self, test_client, mock_services, sample_task_info):
        """Test getting position for task no longer in queue."""
        sample_task_info.status = TaskStatus.TRANSCRIBING
        mock_services['task_queue'].get_task.return_value = sample_task_info
        mock_services['task_queue'].get_task_position.return_value = None
        
        response = test_client.get("/api/queue/position/test1234")
        
        assert response.status_code == 200
        data = response.json()
        assert data["position"] is None
        assert data["status"] == "transcribing"


# =============================================================================
# Edge Cases and Security Tests
# =============================================================================

class TestEdgeCasesAndSecurity:
    """Tests for edge cases and security concerns."""
    
    def test_upload_empty_filename_returns_error(self, test_client, mock_services):
        """Test upload with empty filename - FastAPI validates at request level."""
        # Note: FastAPI returns 422 for empty filename at request validation level
        # before our custom validation can run
        files = {'file': ('', b'test content', 'audio/mpeg')}
        data = {'processing_mode': 'local'}
        
        response = test_client.post("/api/upload", files=files, data=data)
        
        # FastAPI's request validation returns 422 for empty filename
        assert response.status_code == 422
    
    def test_upload_empty_filename_custom_validation(self, test_client, mock_services):
        """Test that our custom validation also catches empty filename."""
        mock_services['file_manager'].validate_file.return_value = (False, "檔案名稱不能為空")
        
        # If a filename somehow passes FastAPI validation but is empty
        files = {'file': ('a', b'test content', 'audio/mpeg')}  # Valid for FastAPI
        data = {'processing_mode': 'local'}
        
        response = test_client.post("/api/upload", files=files, data=data)
        
        # Our validation should return 400
        assert response.status_code == 400
    
    def test_upload_path_traversal_attempt(self, test_client, mock_services):
        """Test upload with path traversal in filename."""
        mock_services['file_manager'].validate_file.return_value = (False, "檔案名稱包含無效字符")
        
        files = {'file': ('../../../etc/passwd', b'test content', 'audio/mpeg')}
        data = {'processing_mode': 'local'}
        
        response = test_client.post("/api/upload", files=files, data=data)
        
        assert response.status_code == 400
        assert "無效字符" in response.json()["detail"]
    
    def test_upload_null_byte_injection(self, test_client, mock_services):
        """Test upload with null byte in filename."""
        mock_services['file_manager'].validate_file.return_value = (False, "檔案名稱包含無效字符")
        
        files = {'file': ('test.mp3\x00.txt', b'test content', 'audio/mpeg')}
        data = {'processing_mode': 'local'}
        
        response = test_client.post("/api/upload", files=files, data=data)
        
        assert response.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])


# =============================================================================
# Config Endpoint - 模型資訊欄位（v4.3.1 前端模式卡顯示用）
# =============================================================================

class TestConfigModelInfo:
    def test_config_exposes_effective_model_names(self, test_client, mock_services):
        """前端模式卡的模型名稱以 /api/config 為唯一來源，不得在前端寫死。"""
        response = test_client.get("/api/config")

        assert response.status_code == 200
        data = response.json()
        assert data["local_llm_model"] == "gemma4:31b"
        assert "cloud_llm_model" in data and data["cloud_llm_model"]
