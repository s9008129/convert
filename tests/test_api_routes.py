#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Unit Tests for API Routes

This module contains comprehensive unit tests covering:
- GET /api/health - Health check
- GET /api/config - System configuration
- POST /api/upload - File upload
- GET /api/tasks/{task_id} - Task status query
- GET /api/tasks/{task_id}/result - Get processing result
- DELETE /api/tasks/{task_id} - Cancel task
- GET /api/queue/status - Queue status
- GET /api/queue/position/{task_id} - Queue position query
"""
import os
import sys
import io
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient

# Set DATA_DIR before importing backend modules
os.environ['DATA_DIR'] = tempfile.mkdtemp()

# Add parent directory to path for imports
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
        mock_summary.check_gemini_available.return_value = False
        
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
    
    def test_config_contains_gemini_availability(self, test_client, mock_services):
        """Test config includes Gemini availability."""
        response = test_client.get("/api/config")
        
        assert response.status_code == 200
        data = response.json()
        assert "gemini_available" in data


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
        finally:
            # Cleanup
            if os.path.exists(result_file):
                os.remove(result_file)


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
