#!/usr/bin/env python
# -*- coding: utf-8 -*-

from scripts import verify_env


def test_effective_asr_backend_uses_mlx_only_for_darwin_arm64_auto():
    assert verify_env.effective_asr_backend(
        system_name="Darwin",
        machine_name="arm64",
        configured_backend="auto",
    ) == "mlx_whisper"
    assert verify_env.effective_asr_backend(
        system_name="Darwin",
        machine_name="arm64",
        configured_backend="transformers",
    ) == "transformers"


def test_critical_modules_follow_effective_mlx_backend(monkeypatch):
    monkeypatch.setattr(verify_env.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(verify_env.platform, "machine", lambda: "arm64")
    monkeypatch.setenv("ASR_BACKEND", "auto")
    checked = []
    monkeypatch.setattr(
        verify_env,
        "check_module",
        lambda module_name, display_name, import_test=None: (checked.append(module_name) or (True, display_name)),
    )

    assert all(ok for ok, _ in verify_env.check_critical_modules())
    assert "mlx_whisper" in checked
    assert "faster_whisper" not in checked


def test_critical_modules_do_not_require_mlx_on_windows(monkeypatch):
    monkeypatch.setattr(verify_env.platform, "system", lambda: "Windows")
    monkeypatch.setattr(verify_env.platform, "machine", lambda: "AMD64")
    monkeypatch.setenv("ASR_BACKEND", "transformers")
    checked = []
    monkeypatch.setattr(
        verify_env,
        "check_module",
        lambda module_name, display_name, import_test=None: (checked.append(module_name) or (True, display_name)),
    )

    verify_env.check_critical_modules()
    assert "mlx_whisper" not in checked
    assert "transformers" in checked
    assert verify_env.effective_asr_backend(
        system_name="Windows",
        machine_name="AMD64",
        configured_backend="auto",
        model_name="MediaTek-Research/Breeze-ASR-26",
    ) == "transformers"


def test_evaluate_windows_cuda_torch_status_flags_cpu_only_runtime():
    ok, message = verify_env.evaluate_windows_cuda_torch_status(
        runtime_status={
            "installed": True,
            "version": "2.11.0+cpu",
            "cuda_version": None,
            "cuda_available": False,
        },
        system_name="Windows",
        nvidia_gpu_available=True,
    )

    assert ok is False
    assert "requirements.windows-cuda.txt" in message
    assert "install_deps.py" in message


def test_evaluate_windows_cuda_torch_status_accepts_cuda_runtime():
    ok, message = verify_env.evaluate_windows_cuda_torch_status(
        runtime_status={
            "installed": True,
            "version": "2.11.0+cu126",
            "cuda_version": "12.6",
            "cuda_available": True,
        },
        system_name="Windows",
        nvidia_gpu_available=True,
    )

    assert ok is True
    assert "2.11.0+cu126" in message
