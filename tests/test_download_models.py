#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for model preload script.
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

os.environ["DATA_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.core.asr_model_resolver import (
    DEFAULT_BREEZE_ASR_26_MLX_MODEL,
    DEFAULT_BREEZE_ASR_26_MLX_REVISION,
    build_asr_cache_signature,
    infer_asr_backend,
    resolve_asr_model,
    resolve_mlx_model_source,
    resolve_model_revision,
    resolve_transformers_model_source,
)
from backend.core.config import settings
from backend.core.errors import ASR_MODEL_UNAVAILABLE, StableServiceError
from scripts.download_models import download_breeze_asr


def test_download_models_uses_safe_transformers_resolution(monkeypatch):
    monkeypatch.setattr(settings, "WHISPER_MODEL", "MediaTek-Research/Breeze-ASR-26")
    monkeypatch.setattr(settings, "ASR_BACKEND", "transformers")
    monkeypatch.setattr(settings, "WHISPER_MODEL_REVISION", "test-rev")
    monkeypatch.setattr(settings, "ASR_LOCAL_FILES_ONLY", False)
    monkeypatch.setattr(settings, "ASR_SAFE_ALLOW_PATTERNS", "config.json,model-*.safetensors,model.safetensors.index.json")
    monkeypatch.setattr(settings, "ASR_SAFE_DENY_PATTERNS", "*.bin,training_args.bin")

    with patch("scripts.download_models.resolve_transformers_model_source", return_value="C:\\models\\breeze") as mock_resolve:
        assert download_breeze_asr() is True
        kwargs = mock_resolve.call_args.kwargs
        assert kwargs["revision"] == "test-rev"
        assert "model-*.safetensors" in kwargs["allow_patterns"]
        assert "training_args.bin" in kwargs["deny_patterns"]


def test_download_models_supports_mlx_shared_cache(monkeypatch):
    monkeypatch.setattr(settings, "WHISPER_MODEL", "MediaTek-Research/Breeze-ASR-26")
    monkeypatch.setattr(settings, "ASR_BACKEND", "auto")
    monkeypatch.setattr(settings, "WHISPER_MODEL_REVISION", None)

    with patch(
        "scripts.download_models.infer_asr_backend",
        return_value="mlx_whisper",
    ), patch(
        "scripts.download_models.resolve_mlx_model_source",
        return_value="/shared/hf/snapshot",
    ) as mock_resolve:
        assert download_breeze_asr() is True

    assert mock_resolve.call_args.args[0] == DEFAULT_BREEZE_ASR_26_MLX_MODEL
    assert mock_resolve.call_args.kwargs["revision"] == DEFAULT_BREEZE_ASR_26_MLX_REVISION
    assert mock_resolve.call_args.kwargs["local_files_only"] is False


def test_resolve_model_revision_only_auto_pins_breeze():
    assert resolve_model_revision("MediaTek-Research/Breeze-ASR-26", None) == "949c87bca9dbe90e160cf739460cc765e80805f3"
    assert resolve_model_revision("openai/whisper-large-v3", None) is None
    assert resolve_model_revision("openai/whisper-large-v3", "custom-rev") == "custom-rev"


def test_darwin_auto_selects_mlx_and_keeps_explicit_backend(monkeypatch):
    monkeypatch.setattr("backend.core.asr_model_resolver.is_darwin_arm64", lambda: True)

    assert infer_asr_backend("MediaTek-Research/Breeze-ASR-26", "auto") == "mlx_whisper"
    assert resolve_asr_model("MediaTek-Research/Breeze-ASR-26", "auto") == DEFAULT_BREEZE_ASR_26_MLX_MODEL
    assert infer_asr_backend("MediaTek-Research/Breeze-ASR-26", "transformers") == "transformers"
    assert infer_asr_backend("MediaTek-Research/Breeze-ASR-26", "mlx-whisper") == "mlx_whisper"
    assert resolve_asr_model("MediaTek-Research/Breeze-ASR-26", "transformers") == "MediaTek-Research/Breeze-ASR-26"
    assert resolve_model_revision(DEFAULT_BREEZE_ASR_26_MLX_MODEL, None) == DEFAULT_BREEZE_ASR_26_MLX_REVISION


def test_mlx_model_source_uses_shared_hf_snapshot_and_offline_policy(monkeypatch):
    with patch(
        "backend.core.asr_model_resolver.snapshot_download",
        return_value="/shared/hf/snapshot",
    ) as mock_download:
        source = resolve_mlx_model_source(
            DEFAULT_BREEZE_ASR_26_MLX_MODEL,
            local_files_only=True,
            cache_dir="/shared/hf/cache",
        )

    assert source == "/shared/hf/snapshot"
    kwargs = mock_download.call_args.kwargs
    assert kwargs["repo_id"] == DEFAULT_BREEZE_ASR_26_MLX_MODEL
    assert kwargs["revision"] == DEFAULT_BREEZE_ASR_26_MLX_REVISION
    assert kwargs["local_files_only"] is True
    assert kwargs["cache_dir"] == "/shared/hf/cache"


def test_asr_cache_signature_includes_output_affecting_options():
    base = build_asr_cache_signature("model", "mlx_whisper", "rev")
    changed_language = build_asr_cache_signature("model", "mlx_whisper", "rev", language="zh")
    changed_prompt = build_asr_cache_signature("model", "mlx_whisper", "rev", initial_prompt="提示")
    changed_beam = build_asr_cache_signature("model", "mlx_whisper", "rev", beam_size=5)

    assert len({base, changed_language, changed_prompt, changed_beam}) == 4


def test_resolve_transformers_model_source_does_not_force_breeze_revision_for_other_models():
    with patch("backend.core.asr_model_resolver.snapshot_download", return_value="C:\\models\\other") as mock_download:
        resolve_transformers_model_source("openai/whisper-large-v3")

    assert mock_download.call_args.kwargs["revision"] is None


def test_resolve_transformers_model_source_maps_snapshot_failure_to_stable_error():
    with patch(
        "backend.core.asr_model_resolver.snapshot_download",
        side_effect=RuntimeError("offline snapshot missing"),
    ):
        with pytest.raises(StableServiceError) as exc_info:
            resolve_transformers_model_source("MediaTek-Research/Breeze-ASR-26", local_files_only=True)

    assert exc_info.value.code == ASR_MODEL_UNAVAILABLE
    assert "offline snapshot missing" in exc_info.value.detail
