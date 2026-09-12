#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for model preload script.
"""

import os
import platform
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
    resolve_engine_chain,
    resolve_mlx_model_source,
    resolve_model_revision,
    resolve_transformers_model_source,
)
from backend.core.config import settings
from backend.core.errors import ASR_MODEL_UNAVAILABLE, StableServiceError
from scripts.download_models import download_breeze_asr


def test_download_models_uses_safe_transformers_resolution(monkeypatch):
    # 顯式 transformers 是 Windows／Linux 語意；固定在非 Mac 平台避免測試
    # 依賴執行主機（Mac 上顯式 legacy 一律 fail-closed）。
    monkeypatch.setattr("backend.core.asr_model_resolver.is_darwin_arm64", lambda: False)
    monkeypatch.setattr("backend.core.platform_config.is_darwin_arm64", lambda: False)
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
    # 以顯式 MLX 模型名稱驗證 shared cache 路徑，不再依賴 Mac auto 的模型映射
    # （Mac 已無 Whisper 模型與 fallback）。
    monkeypatch.setattr(settings, "WHISPER_MODEL", DEFAULT_BREEZE_ASR_26_MLX_MODEL)
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


def test_download_models_apple_auto_skips_model_preload(monkeypatch, capsys):
    """Mac auto → apple：使用 macOS 系統內建模型，完全不預載任何 HF 模型（無 fallback）。"""

    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    monkeypatch.setattr(platform, "machine", lambda: "arm64")
    monkeypatch.setattr(settings, "WHISPER_MODEL", "MediaTek-Research/Breeze-ASR-26")
    monkeypatch.setattr(settings, "ASR_BACKEND", "auto")
    monkeypatch.setattr(settings, "WHISPER_MODEL_REVISION", None)

    with patch(
        "scripts.download_models.resolve_mlx_model_source",
    ) as mock_mlx, patch(
        "scripts.download_models.resolve_transformers_model_source",
    ) as mock_transformers:
        assert download_breeze_asr() is True

    mock_mlx.assert_not_called()
    mock_transformers.assert_not_called()
    assert "macOS 系統內建模型" in capsys.readouterr().out


def test_download_models_explicit_apple_skips_hf_preload(monkeypatch):
    """顯式 apple 為 fail-closed（無 fallback 引擎）：不預載 HF 模型，成功結束。"""
    monkeypatch.setattr(platform, "system", lambda: "Darwin")
    monkeypatch.setattr(platform, "machine", lambda: "arm64")
    monkeypatch.setattr(settings, "WHISPER_MODEL", "MediaTek-Research/Breeze-ASR-26")
    monkeypatch.setattr(settings, "ASR_BACKEND", "apple")
    monkeypatch.setattr(settings, "WHISPER_MODEL_REVISION", None)

    with patch("scripts.download_models.resolve_mlx_model_source") as mock_mlx, patch(
        "scripts.download_models.resolve_transformers_model_source"
    ) as mock_transformers:
        assert download_breeze_asr() is True

    mock_mlx.assert_not_called()
    mock_transformers.assert_not_called()


def test_resolve_model_revision_only_auto_pins_breeze():
    assert resolve_model_revision("MediaTek-Research/Breeze-ASR-26", None) == "949c87bca9dbe90e160cf739460cc765e80805f3"
    assert resolve_model_revision("openai/whisper-large-v3", None) is None
    assert resolve_model_revision("openai/whisper-large-v3", "custom-rev") == "custom-rev"


def test_darwin_auto_selects_apple_and_rejects_whisper_backends(monkeypatch):
    monkeypatch.setattr("backend.core.asr_model_resolver.is_darwin_arm64", lambda: True)
    monkeypatch.setattr("backend.core.platform_config.is_darwin_arm64", lambda: True)

    # Mac auto 預設改走 Apple SpeechAnalyzer（T20260912-2242-01）：鏈長 1、無
    # 任何 Whisper fallback 段，且不得暴露 MLX（或其他 Whisper）模型 id。
    assert infer_asr_backend("MediaTek-Research/Breeze-ASR-26", "auto") == "apple"
    chain = resolve_engine_chain("auto", "MediaTek-Research/Breeze-ASR-26")
    assert chain == ("apple",)
    assert "mlx_whisper" not in chain
    assert resolve_asr_model("MediaTek-Research/Breeze-ASR-26", "auto") == ""

    # Mac 上顯式 legacy（含大小寫／連字號變體）一律 fail-closed。
    for requested in ("transformers", "faster-whisper", "MLX-Whisper"):
        with pytest.raises(ValueError, match="Mac 僅提供 Apple SpeechAnalyzer"):
            infer_asr_backend("MediaTek-Research/Breeze-ASR-26", requested)
        with pytest.raises(ValueError, match="Mac 僅提供 Apple SpeechAnalyzer"):
            resolve_engine_chain(requested, "MediaTek-Research/Breeze-ASR-26")

    # 非 Mac 完全不變：顯式 legacy 原樣通過、auto 維持模型型解析、模型不映射。
    monkeypatch.setattr("backend.core.asr_model_resolver.is_darwin_arm64", lambda: False)
    monkeypatch.setattr("backend.core.platform_config.is_darwin_arm64", lambda: False)
    assert infer_asr_backend("MediaTek-Research/Breeze-ASR-26", "transformers") == "transformers"
    assert infer_asr_backend("MediaTek-Research/Breeze-ASR-26", "mlx-whisper") == "mlx_whisper"
    assert resolve_engine_chain("auto", "MediaTek-Research/Breeze-ASR-26") == ("transformers",)
    assert resolve_asr_model("MediaTek-Research/Breeze-ASR-26", "auto") == "MediaTek-Research/Breeze-ASR-26"
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
