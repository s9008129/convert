#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Tests for device detector runtime decisions."""

import importlib
from types import SimpleNamespace

device_detector_module = importlib.import_module("backend.services.device_detector")
from backend.services.device_detector import DeviceDetector, DeviceType


def _mock_nvidia_smi(*args, **kwargs):
    return SimpleNamespace(
        returncode=0,
        stdout="NVIDIA GeForce RTX 4090, 20000, 24564\n",
    )


def test_detect_best_device_falls_back_to_cpu_when_transformers_torch_has_no_cuda(monkeypatch):
    detector = DeviceDetector()

    # 顯式 transformers 是 Windows／Linux 語意：固定在非 Mac 平台，避免測試
    # 依賴執行主機（Mac 上顯式 legacy backend 已 fail-closed）。
    monkeypatch.setattr("backend.core.asr_model_resolver.is_darwin_arm64", lambda: False)
    monkeypatch.setattr("backend.core.platform_config.is_darwin_arm64", lambda: False)
    monkeypatch.setattr(device_detector_module.settings, "WHISPER_MODEL", "MediaTek-Research/Breeze-ASR-26", raising=False)
    monkeypatch.setattr(device_detector_module.settings, "ASR_BACKEND", "transformers", raising=False)
    monkeypatch.setattr(device_detector_module.subprocess, "run", _mock_nvidia_smi)
    monkeypatch.setattr(
        DeviceDetector,
        "_check_torch_cuda_runtime",
        staticmethod(lambda: (False, {"error": "torch.cuda.is_available()=False", "cuda_version": None})),
    )
    monkeypatch.setattr(detector, "_check_mps", lambda: False)

    device, compute_type = detector.detect_best_device()

    assert device == DeviceType.CPU
    assert compute_type == "int8"
    assert detector.gpu_name == "NVIDIA GeForce RTX 4090"
    assert detector.cuda_runtime_available is False
    assert detector.cuda_runtime_error == "torch.cuda.is_available()=False"


def test_detect_best_device_keeps_cuda_for_faster_whisper_without_torch_cuda(monkeypatch):
    detector = DeviceDetector()

    # 同上：faster-whisper／CUDA 屬非 Mac 語意，固定平台避免依賴執行主機。
    monkeypatch.setattr("backend.core.asr_model_resolver.is_darwin_arm64", lambda: False)
    monkeypatch.setattr("backend.core.platform_config.is_darwin_arm64", lambda: False)
    monkeypatch.setattr(device_detector_module.settings, "WHISPER_MODEL", "large-v3", raising=False)
    monkeypatch.setattr(device_detector_module.settings, "ASR_BACKEND", "faster_whisper", raising=False)
    monkeypatch.setattr(device_detector_module.subprocess, "run", _mock_nvidia_smi)

    device, compute_type = detector.detect_best_device()

    assert device == DeviceType.CUDA
    assert compute_type == "float16"
    assert detector.gpu_name == "NVIDIA GeForce RTX 4090"
