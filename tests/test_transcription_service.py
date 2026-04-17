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
from backend.services.device_detector import DeviceType
from backend.services.transcription import DetailedTranscriptionResult, TranscriptionService


def test_detect_runtime_falls_back_cpu_when_transformers_vram_insufficient(monkeypatch):
    service = TranscriptionService()

    monkeypatch.setattr(settings, "WHISPER_MODEL", "MediaTek-Research/Breeze-ASR-26")
    monkeypatch.setattr(settings, "ASR_BACKEND", "auto")
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
