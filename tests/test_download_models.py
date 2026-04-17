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

os.environ["DATA_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.core.asr_model_resolver import resolve_model_revision, resolve_transformers_model_source
from backend.core.config import settings
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


def test_resolve_model_revision_only_auto_pins_breeze():
    assert resolve_model_revision("MediaTek-Research/Breeze-ASR-26", None) == "949c87bca9dbe90e160cf739460cc765e80805f3"
    assert resolve_model_revision("openai/whisper-large-v3", None) is None
    assert resolve_model_revision("openai/whisper-large-v3", "custom-rev") == "custom-rev"


def test_resolve_transformers_model_source_does_not_force_breeze_revision_for_other_models():
    with patch("backend.core.asr_model_resolver.snapshot_download", return_value="C:\\models\\other") as mock_download:
        resolve_transformers_model_source("openai/whisper-large-v3")

    assert mock_download.call_args.kwargs["revision"] is None
