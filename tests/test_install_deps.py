#!/usr/bin/env python
# -*- coding: utf-8 -*-

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
