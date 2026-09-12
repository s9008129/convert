#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Apple SpeechAnalyzer helper 在 /api/health 的可觀測性測試（WAVE-04，REQ-10 / SI-12）。

對應 plan CHECK-11：
- macOS 完整模式：``apple_helper`` 區段欄位齊備（supported/available/path/probe/reason），
  且 configured_path 由設定傳入凍結介面 ``apple_helper_status``。
- 非 macOS：``supported=false``——routes 最早分支返回，不載入 Apple 模組、
  不執行 probe、不 spawn 子程序（SI-12 / NFR-03）。
- ``quick=true``：不啟動 helper（health 保持輕量）。
- 既有 health 欄位不因 additive 區段改變。
- Apple 模組不可用時 health 仍為 healthy（BE-03：欄位缺失不得讓 health 失敗）。

Apple 模組本體（WAVE-03）以 spy 驗證非 macOS 零子程序；不在本檔載入其餘內部。
"""

import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# 每次測試使用獨立資料夾，避免互相污染（比照 tests/test_transcription_service.py）。
os.environ["DATA_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.api import routes as routes_module  # noqa: E402
from backend.core.config import settings  # noqa: E402
from backend.models.schemas import QueueStatus  # noqa: E402


@pytest.fixture
def platform_kind(monkeypatch):
    """把 ``platform.system/machine`` 固定成指定平台（未知平台視為非 Mac）。"""

    def _set(system: str, machine: str = "arm64") -> None:
        monkeypatch.setattr(platform, "system", lambda: system)
        monkeypatch.setattr(platform, "machine", lambda: machine)

    return _set


@pytest.fixture
def health_client():
    """沿用 tests/test_api_routes.py 的 mock 慣例，隔離 /api/health 的外部依賴。"""
    with patch('backend.api.routes.device_detector') as mock_device, \
         patch('backend.api.routes.task_queue') as mock_queue, \
         patch('backend.api.routes.summarization_service') as mock_summary:
        mock_device.detect_best_device.return_value = None
        mock_device.get_device_info.return_value = {
            "current_device": "cpu",
            "compute_type": "int8",
            "fallback_count": 0,
            "gpu_name": None,
            "gpu_memory_mb": None,
            "gpu_available": False,
            "mps_available": False,
        }
        mock_summary.check_ollama_health = AsyncMock(return_value=True)
        mock_summary.check_lmstudio_health = AsyncMock(return_value=False)
        mock_summary.check_gemini_available.return_value = False
        mock_summary.get_local_llm_health.return_value = {
            "provider": "lmstudio",
            "server_reachable": True,
            "selection_status": "LMSTUDIO_NO_LOADED_LLM",
            "loaded_llm_count": 0,
            "selected_model": None,
            "context_length": None,
        }
        mock_queue.get_queue_status.return_value = QueueStatus(
            total_queued=0,
            processing_count=0,
            estimated_wait_seconds=0,
            max_concurrent=1,
            queue_max_size=50,
        )

        app = FastAPI()
        app.include_router(routes_module.router)
        yield TestClient(app)


def _fake_helper_status(**status_overrides):
    """凍結介面回傳值的測試替身（欄位：supported/available/path/probe/reason）。"""

    status = {
        "supported": True,
        "available": True,
        "path": "/tmp/apple-speech-cli",
        "probe": {"macos": "26.0", "assets_installed": True},
        "reason": None,
    }
    status.update(status_overrides)
    return status


def test_health_reports_apple_helper_fields_on_macos(platform_kind, health_client, monkeypatch):
    """macOS 完整模式：apple_helper 欄位齊備，且 configured_path 來自設定。"""
    platform_kind("Darwin", "arm64")
    monkeypatch.setattr(settings, "APPLE_SPEECH_CLI_PATH", "/opt/apple/apple-speech-cli")

    calls: list[dict] = []
    expected = _fake_helper_status()

    def fake_status(*, configured_path=None):
        calls.append({"configured_path": configured_path})
        return dict(expected)

    monkeypatch.setattr(routes_module, "_load_apple_helper_status", lambda: fake_status)

    response = health_client.get("/api/health")

    assert response.status_code == 200
    apple_helper = response.json()["device_info"]["apple_helper"]
    assert set(apple_helper) == {"supported", "available", "path", "probe", "reason"}
    assert apple_helper == expected
    assert calls == [{"configured_path": "/opt/apple/apple-speech-cli"}]


def test_health_empty_configured_path_passes_none(platform_kind, health_client, monkeypatch):
    """未設定 APPLE_SPEECH_CLI_PATH 時傳 None（介面語意：依序搜尋 repo 產物→PATH）。"""
    platform_kind("Darwin", "arm64")
    monkeypatch.setattr(settings, "APPLE_SPEECH_CLI_PATH", "")

    calls: list[dict] = []

    def fake_status(*, configured_path=None):
        calls.append({"configured_path": configured_path})
        return _fake_helper_status(available=False, path=None, probe=None, reason="尚未建置 helper")

    monkeypatch.setattr(routes_module, "_load_apple_helper_status", lambda: fake_status)

    response = health_client.get("/api/health")

    assert response.status_code == 200
    assert calls == [{"configured_path": None}]
    assert response.json()["device_info"]["apple_helper"]["available"] is False


def test_health_windows_apple_helper_unsupported_without_probe(platform_kind, health_client, monkeypatch):
    """Windows：supported=false，最早分支返回——不載入 Apple 模組、不 spawn（SI-12）。"""
    platform_kind("Windows", "AMD64")

    popen_spy = MagicMock(name="subprocess.Popen")
    run_spy = MagicMock(name="subprocess.run")
    monkeypatch.setattr(subprocess, "Popen", popen_spy)
    monkeypatch.setattr(subprocess, "run", run_spy)
    loader_spy = MagicMock(name="_load_apple_helper_status")
    monkeypatch.setattr(routes_module, "_load_apple_helper_status", loader_spy)

    response = health_client.get("/api/health")

    assert response.status_code == 200
    apple_helper = response.json()["device_info"]["apple_helper"]
    assert set(apple_helper) == {"supported", "available", "path", "probe", "reason"}
    assert apple_helper["supported"] is False
    assert apple_helper["available"] is False
    assert apple_helper["path"] is None
    assert apple_helper["probe"] is None
    assert apple_helper["reason"]
    # 連 Apple 模組載入都不得發生，更不得 spawn 任何子程序。
    loader_spy.assert_not_called()
    popen_spy.assert_not_called()
    run_spy.assert_not_called()


def test_health_quick_skips_apple_probe_on_macos(platform_kind, health_client, monkeypatch):
    """quick=true：不得啟動 helper（health 保持輕量）；available 未驗證為 false。"""
    platform_kind("Darwin", "arm64")

    popen_spy = MagicMock(name="subprocess.Popen")
    monkeypatch.setattr(subprocess, "Popen", popen_spy)
    loader_spy = MagicMock(name="_load_apple_helper_status")
    monkeypatch.setattr(routes_module, "_load_apple_helper_status", loader_spy)

    response = health_client.get("/api/health?quick=true")

    assert response.status_code == 200
    apple_helper = response.json()["device_info"]["apple_helper"]
    assert set(apple_helper) == {"supported", "available", "path", "probe", "reason"}
    assert apple_helper["supported"] is True
    assert apple_helper["available"] is False
    assert apple_helper["probe"] is None
    assert apple_helper["reason"]
    loader_spy.assert_not_called()
    popen_spy.assert_not_called()


def test_health_quick_on_windows_also_unsupported(platform_kind, health_client):
    """quick=true 且非 macOS：仍是 supported=false（平台判定不需 probe）。"""
    platform_kind("Windows", "AMD64")

    response = health_client.get("/api/health?quick=true")

    assert response.status_code == 200
    assert response.json()["device_info"]["apple_helper"]["supported"] is False


def test_health_keeps_existing_fields_with_additive_apple_helper(platform_kind, health_client, monkeypatch):
    """既有欄位抽樣斷言：additive 區段不得刪改 GPU/queue/llm 等既有輸出。"""
    platform_kind("Darwin", "arm64")
    monkeypatch.setattr(
        routes_module,
        "_load_apple_helper_status",
        lambda: lambda **kwargs: _fake_helper_status(),
    )

    response = health_client.get("/api/health")

    assert response.status_code == 200
    data = response.json()
    for key in (
        "status",
        "version",
        "gpu_available",
        "gpu_name",
        "ollama_available",
        "lmstudio_available",
        "gemini_available",
        "queue_status",
        "device_info",
        "build_revision",
    ):
        assert key in data, f"既有 health 欄位不得消失: {key}"
    assert data["status"] == "healthy"
    assert data["ollama_available"] is True
    assert data["lmstudio_available"] is False
    assert data["gemini_available"] is False

    info = data["device_info"]
    assert info["llm"]["selection_status"] == "LMSTUDIO_NO_LOADED_LLM"
    for key in ("current_device", "compute_type", "fallback_count", "gpu_available", "mps_available"):
        assert key in info, f"既有 device_info 欄位不得消失: {key}"
    assert "apple_helper" in info


def test_health_stays_healthy_when_apple_module_unavailable(platform_kind, health_client, monkeypatch):
    """BE-03：Apple 模組載入失敗不得讓 /health 失敗，reason 需可觀察。"""
    platform_kind("Darwin", "arm64")

    def broken_loader():
        raise ImportError("backend.services.asr_apple.apple 尚未安裝")

    monkeypatch.setattr(routes_module, "_load_apple_helper_status", broken_loader)

    response = health_client.get("/api/health")

    assert response.status_code == 200
    apple_helper = response.json()["device_info"]["apple_helper"]
    assert apple_helper["available"] is False
    assert "ImportError" in apple_helper["reason"]


def test_real_apple_helper_status_is_side_effect_free_on_windows(platform_kind, monkeypatch):
    """SI-12：真實 apple_helper_status 在非 macOS 最早分支返回、零子程序。

    WAVE-03 的 apple.py 尚未落地時自動跳過；落地後此測試必須通過。
    """
    apple_module = pytest.importorskip("backend.services.asr_apple.apple")
    platform_kind("Windows", "AMD64")
    monkeypatch.setattr(sys, "platform", "win32")

    popen_spy = MagicMock(name="subprocess.Popen")
    run_spy = MagicMock(name="subprocess.run")
    monkeypatch.setattr(subprocess, "Popen", popen_spy)
    monkeypatch.setattr(subprocess, "run", run_spy)

    status = apple_module.apple_helper_status()

    assert status["supported"] is False
    assert status["available"] is False
    assert popen_spy.call_count == 0
    assert run_spy.call_count == 0
