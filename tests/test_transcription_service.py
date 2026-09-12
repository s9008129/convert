#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for backend transcription service.
"""

import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

os.environ["DATA_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.core.config import settings
from backend.core.asr_model_resolver import (
    DEFAULT_BREEZE_ASR_26_MLX_MODEL,
    DEFAULT_BREEZE_ASR_26_MLX_REVISION,
)
from backend.services.device_detector import DeviceType
from backend.services.transcription import DetailedTranscriptionResult, TranscriptionService


def test_detect_runtime_falls_back_cpu_when_transformers_vram_insufficient(monkeypatch):
    service = TranscriptionService()

    # 顯式 transformers 是 Windows／Linux 語意：固定在非 Mac 平台，讓測試與
    # 執行主機解耦（Mac 上顯式 legacy backend 已 fail-closed）。
    monkeypatch.setattr("backend.core.asr_model_resolver.is_darwin_arm64", lambda: False)
    monkeypatch.setattr("backend.core.platform_config.is_darwin_arm64", lambda: False)
    monkeypatch.setattr(settings, "WHISPER_MODEL", "MediaTek-Research/Breeze-ASR-26")
    monkeypatch.setattr(settings, "ASR_BACKEND", "transformers")
    monkeypatch.setattr(settings, "ASR_TRANSFORMERS_MIN_VRAM_MB", 6000)
    monkeypatch.setattr(
        "backend.services.transcription.device_detector.detect_best_device",
        lambda: (DeviceType.CUDA, "float16"),
    )
    monkeypatch.setattr("backend.services.transcription.device_detector.gpu_memory_mb", 2048)

    device, compute_type = service._detect_runtime()

    assert device == "cpu"
    assert compute_type == "float32"


def test_detect_runtime_falls_back_cpu_when_torch_has_no_cuda(monkeypatch):
    service = TranscriptionService()

    # 同上：CUDA 降級屬非 Mac 語意，固定平台避免依賴執行主機。
    monkeypatch.setattr("backend.core.asr_model_resolver.is_darwin_arm64", lambda: False)
    monkeypatch.setattr("backend.core.platform_config.is_darwin_arm64", lambda: False)
    monkeypatch.setattr(settings, "WHISPER_MODEL", "MediaTek-Research/Breeze-ASR-26")
    monkeypatch.setattr(settings, "ASR_BACKEND", "transformers")
    monkeypatch.setattr(
        "backend.services.transcription.device_detector.detect_best_device",
        lambda: (DeviceType.CUDA, "float16"),
    )
    monkeypatch.setattr("backend.services.transcription.device_detector.gpu_memory_mb", 24000)

    fake_torch = MagicMock()
    fake_torch.cuda.is_available.return_value = False
    monkeypatch.setitem(sys.modules, "torch", fake_torch)

    device, compute_type = service._detect_runtime()

    assert device == "cpu"
    assert compute_type == "float32"


def test_load_transformers_pipeline_uses_safe_resolution(monkeypatch):
    service = TranscriptionService()

    monkeypatch.setattr(settings, "WHISPER_MODEL", "MediaTek-Research/Breeze-ASR-26")
    monkeypatch.setattr(settings, "WHISPER_MODEL_REVISION", "test-rev")
    monkeypatch.setattr(settings, "ASR_LOCAL_FILES_ONLY", True)
    monkeypatch.setattr(settings, "ASR_SAFE_ALLOW_PATTERNS", "config.json,model-*.safetensors")
    monkeypatch.setattr(settings, "ASR_SAFE_DENY_PATTERNS", "*.bin,training_args.bin")

    fake_pipeline = MagicMock()
    fake_torch = SimpleNamespace(float16="float16", float32="float32")
    fake_transformers = SimpleNamespace(pipeline=fake_pipeline)

    with patch.dict(sys.modules, {"torch": fake_torch, "transformers": fake_transformers}):
        with patch(
            "backend.services.transcription.resolve_transformers_model_source",
            return_value="C:\\models\\breeze",
        ) as mock_resolve:
            service._load_transformers_pipeline(device="cpu", compute_type="float32")

    kwargs = mock_resolve.call_args.kwargs
    assert kwargs["revision"] == "test-rev"
    assert kwargs["local_files_only"] is True
    assert "model-*.safetensors" in kwargs["allow_patterns"]
    assert "training_args.bin" in kwargs["deny_patterns"]
    fake_pipeline.assert_called_once()


def test_load_mlx_model_uses_pinned_shared_snapshot(monkeypatch):
    """MLX 載入路徑以顯式 MLX 模型名稱解析 shared snapshot 與 pinned revision
    （不依賴 Mac auto 的模型映射；Mac 已無 Whisper 模型與 fallback）。"""

    service = TranscriptionService()
    fake_mlx = SimpleNamespace()
    monkeypatch.setitem(sys.modules, "mlx_whisper", fake_mlx)
    monkeypatch.setattr(settings, "WHISPER_MODEL", DEFAULT_BREEZE_ASR_26_MLX_MODEL)
    monkeypatch.setattr(settings, "ASR_BACKEND", "auto")
    monkeypatch.setattr(settings, "WHISPER_MODEL_REVISION", None)
    monkeypatch.setattr(settings, "ASR_LOCAL_FILES_ONLY", True)

    with patch(
        "backend.services.transcription.resolve_mlx_model_source",
        return_value="/shared/hf/snapshot",
    ) as mock_resolve:
        service._backend = "mlx_whisper"
        service._load_mlx_whisper_model()

    assert service._model is fake_mlx
    assert service._mlx_model_source == "/shared/hf/snapshot"
    assert mock_resolve.call_args.args[0] == DEFAULT_BREEZE_ASR_26_MLX_MODEL
    assert mock_resolve.call_args.kwargs["revision"] == DEFAULT_BREEZE_ASR_26_MLX_REVISION
    assert mock_resolve.call_args.kwargs["local_files_only"] is True


def test_transcribe_with_mlx_whisper_normalizes_segments(monkeypatch):
    service = TranscriptionService()
    fake_mlx = SimpleNamespace(
        transcribe=MagicMock(
            return_value={
                "text": "這是 MLX 逐字稿",
                "language": "zh",
                "duration": 4.5,
                "segments": [
                    {"text": "這是 MLX", "start": 0.0, "end": 2.0},
                    {"text": "逐字稿", "timestamp": [2.0, 4.5]},
                ],
            }
        )
    )
    service._model = fake_mlx
    service._mlx_model_source = "/shared/hf/snapshot"
    service._backend = "mlx_whisper"
    monkeypatch.setattr(settings, "WHISPER_MODEL", "doggy8088/Breeze-ASR-26-MLX")
    monkeypatch.setattr(settings, "ASR_BACKEND", "mlx_whisper")
    monkeypatch.setattr(settings, "WHISPER_LANGUAGE", "auto")
    monkeypatch.setattr(settings, "ASR_RETURN_TIMESTAMPS", True)
    monkeypatch.setattr(settings, "ASR_INITIAL_PROMPT", "繁體中文")
    monkeypatch.setattr(settings, "ASR_ENABLE_HOTWORDS", False)

    result = service._transcribe_with_mlx_whisper("dummy.wav")

    assert result.backend == "mlx_whisper"
    assert result.text == "這是 MLX 逐字稿"
    assert result.duration_seconds == 4.5
    assert [(chunk.start, chunk.end) for chunk in result.chunks] == [(0.0, 2.0), (2.0, 4.5)]
    assert fake_mlx.transcribe.call_args.kwargs["path_or_hf_repo"] == "/shared/hf/snapshot"
    assert fake_mlx.transcribe.call_args.kwargs["initial_prompt"] == "繁體中文"
    assert "beam_size" not in fake_mlx.transcribe.call_args.kwargs


def test_transcribe_with_transformers_normalizes_chunks(monkeypatch):
    service = TranscriptionService()
    pipeline_mock = MagicMock()
    pipeline_mock.tokenizer = MagicMock()
    pipeline_mock.return_value = {
        "text": "這是台語段落 English follow-up",
        "language": "zh",
        "chunks": [
            {"text": "這是台語段落", "timestamp": (0.0, 3.2)},
            {"text": "English follow-up", "timestamp": (3.2, 5.0)},
        ],
    }
    service._model = pipeline_mock

    monkeypatch.setattr(settings, "WHISPER_LANGUAGE", "auto")
    monkeypatch.setattr(settings, "ASR_RETURN_TIMESTAMPS", True)
    monkeypatch.setattr(settings, "ASR_CHUNK_LENGTH_SECONDS", 30)
    monkeypatch.setattr(service, "_load_audio_array", lambda _: np.ones(16000 * 5, dtype=np.float32))

    result = service._transcribe_with_transformers("dummy.wav")

    assert isinstance(result, DetailedTranscriptionResult)
    assert result.backend == "transformers"
    assert result.text == "這是台語段落 English follow-up"
    assert len(result.chunks) == 2
    assert result.chunks[0].start == 0.0
    assert result.chunks[1].end == 5.0


def test_transcribe_detailed_retries_once_with_force_cpu(monkeypatch, tmp_path):
    service = TranscriptionService()
    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir()
    audio_path = uploads_dir / "sample.wav"
    audio_path.write_bytes(b"fake")

    # 固定非 Mac 平台 ＋ 顯式 transformers：本測試描述的是 legacy 引擎的
    # CUDA→CPU 重試路徑（Windows／Linux 語意，Mac 已無此選項）。
    monkeypatch.setattr("backend.core.asr_model_resolver.is_darwin_arm64", lambda: False)
    monkeypatch.setattr("backend.core.platform_config.is_darwin_arm64", lambda: False)
    monkeypatch.setattr(settings, "ASR_BACKEND", "transformers")
    monkeypatch.setattr(settings, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(service, "_unload_model", MagicMock())

    calls = []

    def fake_load_model(force_cpu: bool = False):
        calls.append(force_cpu)
        service._backend = "transformers"
        service._device = DeviceType.CUDA if not force_cpu else DeviceType.CPU

    monkeypatch.setattr(service, "_load_model", fake_load_model)

    state = {"count": 0}

    def fake_transcribe(_: str):
        if state["count"] == 0:
            state["count"] += 1
            raise RuntimeError("gpu failure")
        return DetailedTranscriptionResult(
            text="retry success",
            duration_seconds=1.0,
            language="zh",
            backend="transformers",
        )

    monkeypatch.setattr(service, "_transcribe_with_transformers", fake_transcribe)

    result = service.transcribe_detailed(str(audio_path))

    assert result.text == "retry success"
    assert calls == [False, True]


def test_transcribe_detailed_blocks_prefix_bypass_path(monkeypatch, tmp_path):
    service = TranscriptionService()
    uploads_dir = tmp_path / "uploads"
    uploads_dir.mkdir()
    outside_dir = tmp_path / "uploads_evil"
    outside_dir.mkdir()
    audio_path = outside_dir / "payload.wav"
    audio_path.write_bytes(b"fake")

    monkeypatch.setattr(settings, "DATA_DIR", str(tmp_path))

    with pytest.raises(ValueError, match="不允許的檔案路徑"):
        service.transcribe_detailed(str(audio_path))
