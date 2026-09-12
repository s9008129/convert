#!/usr/bin/env python
# -*- coding: utf-8 -*-

import ast
from pathlib import Path

import install_deps


def test_should_install_windows_cuda_torch_returns_true_for_windows_gpu():
    should_install = install_deps._should_install_windows_cuda_torch(
        system_name="Windows",
        has_nvidia_gpu=True,
    )

    assert should_install is True


def test_validate_windows_cuda_runtime_rejects_cpu_only_torch():
    ok, message = install_deps._validate_windows_cuda_runtime(
        status={
            "installed": True,
            "version": "2.11.0+cpu",
            "cuda_version": None,
            "cuda_available": False,
        },
        system_name="Windows",
        has_nvidia_gpu=True,
    )

    assert ok is False
    assert "requirements.windows-cuda.txt" in message
    assert "2.11.0+cpu" in message


def test_validate_windows_cuda_runtime_accepts_cuda_torch():
    ok, message = install_deps._validate_windows_cuda_runtime(
        status={
            "installed": True,
            "version": "2.11.0+cu126",
            "cuda_version": "12.6",
            "cuda_available": True,
        },
        system_name="Windows",
        has_nvidia_gpu=True,
    )

    assert ok is True
    assert "CUDA" in message


def test_apple_helper_hint_exists_only_on_darwin():
    """Apple/Xcode/Swift 提示只在 macOS 產生；Windows/Linux 一律 None。"""
    assert install_deps.apple_helper_hint(system_name="Windows") is None
    assert install_deps.apple_helper_hint(system_name="Linux") is None

    hint = install_deps.apple_helper_hint(system_name="Darwin")
    assert hint is not None
    assert "swift build -c release" in hint
    assert "apple_speech_cli/.build/release/apple-speech-cli" in hint


def test_windows_check_mode_prints_no_apple_toolchain_wording(monkeypatch, capsys):
    """Windows `--check`：不安裝任何套件，且輸出不得出現 Xcode/Swift/Apple 字樣。"""
    monkeypatch.setattr(install_deps, "_has_nvidia_gpu", lambda: False)

    def _forbidden_install(*args, **kwargs):
        raise AssertionError("--check 模式不得呼叫 pip 安裝")

    monkeypatch.setattr(install_deps, "_run_pip_install", _forbidden_install)

    assert install_deps.main(["--check"], system_name="Windows") == 0

    output = capsys.readouterr().out.lower()
    for token in ("xcode", "swift", "apple", "helper", "speechanalyzer"):
        assert token not in output


def test_macos_check_mode_prints_helper_build_hint_without_installing(monkeypatch, capsys):
    """macOS `--check`：只提示 helper 建置需求，不自動編譯、不呼叫 pip。"""
    monkeypatch.setattr(install_deps, "_has_nvidia_gpu", lambda: False)
    install_calls = []
    monkeypatch.setattr(
        install_deps,
        "_run_pip_install",
        lambda *args, **kwargs: install_calls.append(args),
    )

    assert install_deps.main(["--check"], system_name="Darwin") == 0

    output = capsys.readouterr().out
    assert install_calls == []
    assert "不會自動編譯" in output
    assert "swift build -c release" in output


def test_windows_install_flow_prints_no_apple_toolchain_wording(monkeypatch, capsys):
    """Windows 正常安裝流程（pip 以 stub 取代）同樣不得出現任何 Apple 字樣。"""
    monkeypatch.setattr(install_deps, "_has_nvidia_gpu", lambda: False)
    monkeypatch.setattr(install_deps, "_run_pip_install", lambda *args, **kwargs: None)

    assert install_deps.main([], system_name="Windows") == 0

    output = capsys.readouterr().out.lower()
    for token in ("xcode", "swift", "apple", "helper", "speechanalyzer"):
        assert token not in output


def test_install_deps_imports_no_apple_or_backend_modules():
    """靜態保證：安裝腳本不得 import 任何 Apple / backend 模組（Windows 零 Apple）。"""
    source = Path(install_deps.__file__).read_text(encoding="utf-8")
    imported = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")

    offenders = [
        name for name in imported if "apple" in name.lower() or name.startswith("backend")
    ]
    assert offenders == []
