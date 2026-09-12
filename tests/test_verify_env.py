#!/usr/bin/env python
# -*- coding: utf-8 -*-

from pathlib import Path

from scripts import verify_env


def test_effective_asr_backend_uses_apple_for_darwin_arm64_auto():
    assert verify_env.effective_asr_backend(
        system_name="Darwin",
        machine_name="arm64",
        configured_backend="auto",
    ) == "apple"
    assert verify_env.effective_asr_backend(
        system_name="Darwin",
        machine_name="arm64",
        configured_backend="transformers",
    ) == "transformers"


def test_critical_modules_do_not_require_mlx_for_apple_backend(monkeypatch):
    """Mac apple：Apple SpeechAnalyzer 走 Swift helper（系統內建模型），
    不再要求任何 Python ASR 模組（沒有 "Apple 路徑 fallback"）。"""

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
    assert "mlx_whisper" not in checked
    assert "mlx" not in checked
    assert "faster_whisper" not in checked
    assert "torch" not in checked
    assert "transformers" not in checked


def test_critical_modules_reject_explicit_legacy_backend_on_mac(monkeypatch):
    """Mac 顯式 legacy：環境驗證回報與啟動時相同的 fail-closed 錯誤。"""

    monkeypatch.setattr(verify_env.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(verify_env.platform, "machine", lambda: "arm64")
    monkeypatch.setenv("ASR_BACKEND", "mlx-whisper")
    checked = []
    monkeypatch.setattr(
        verify_env,
        "check_module",
        lambda module_name, display_name, import_test=None: (checked.append(module_name) or (True, display_name)),
    )

    results = verify_env.check_critical_modules()

    assert any(
        not ok
        and "ASR_BACKEND=mlx_whisper 在 macOS 已不支援" in message
        and "Mac 僅提供 Apple SpeechAnalyzer" in message
        for ok, message in results
    )
    assert "mlx_whisper" not in checked


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


def _patch_all_checks_ok(monkeypatch):
    monkeypatch.setattr(verify_env, "check_python_version", lambda: (True, "ok"))
    monkeypatch.setattr(verify_env, "check_python_path", lambda: (True, "ok"))
    monkeypatch.setattr(verify_env, "check_ffmpeg", lambda: (True, "ok"))
    monkeypatch.setattr(verify_env, "check_critical_modules", lambda: [])
    monkeypatch.setattr(verify_env, "check_optional_modules", lambda: [])
    monkeypatch.setattr(verify_env, "check_windows_cuda_torch", lambda: (True, "ok"))
    monkeypatch.setattr(verify_env, "check_directories", lambda: [])
    monkeypatch.setattr(verify_env, "check_config_files", lambda: [])
    monkeypatch.setattr(verify_env, "has_nvidia_gpu", lambda: False)


def test_apple_section_skipped_on_non_macos_without_apple_wording(monkeypatch, capsys):
    """非 macOS（Windows/Linux）完全跳過 Apple 段，且不得輸出 Apple/Xcode 字樣。"""
    assert verify_env.check_apple_native_environment(
        system_name="Windows", machine_name="AMD64"
    ) is None
    assert verify_env.check_apple_native_environment(
        system_name="Linux", machine_name="x86_64"
    ) is None

    monkeypatch.setattr(verify_env.platform, "system", lambda: "Windows")
    monkeypatch.setattr(verify_env.platform, "machine", lambda: "AMD64")
    _patch_all_checks_ok(monkeypatch)

    assert verify_env.run_all_checks() is True

    output = capsys.readouterr().out.lower()
    for token in ("apple", "xcode", "swift", "apple-speech-cli", "speechanalyzer"):
        assert token not in output


def test_apple_section_hints_missing_helper_and_stays_non_fatal(monkeypatch, capsys):
    """macOS：缺 helper 與 Swift 工具鏈只給建置提示，不阻擋環境驗證通過。"""
    monkeypatch.setattr(verify_env.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(verify_env.platform, "machine", lambda: "arm64")
    monkeypatch.setattr(
        verify_env,
        "APPLE_HELPER_DEFAULT_PATH",
        Path("/nonexistent/apple-speech-cli"),
    )
    monkeypatch.delenv("APPLE_SPEECH_CLI_PATH", raising=False)
    monkeypatch.setattr(verify_env.shutil, "which", lambda name: None)
    monkeypatch.setattr(verify_env, "check_swift_toolchain", lambda: (False, "缺少 swift 工具鏈"))
    _patch_all_checks_ok(monkeypatch)

    results = verify_env.check_apple_native_environment()
    assert results is not None
    messages = "\n".join(msg for _, msg in results)
    assert "尚未建置" in messages
    assert "swift build -c release" in messages

    assert verify_env.run_all_checks() is True
    output = capsys.readouterr().out
    assert "swift build -c release" in output
