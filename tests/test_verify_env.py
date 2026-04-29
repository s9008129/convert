#!/usr/bin/env python
# -*- coding: utf-8 -*-

from scripts import verify_env


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
