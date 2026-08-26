#!/usr/bin/env python3
"""
這份測試會直接驗證語音模型能否順利載入並產生轉錄結果。
若模型或環境有問題，可快速從這裡看出基本功能是否正常。
"""

import os
from pathlib import Path

import pytest

mlx_whisper = pytest.importorskip("mlx_whisper", reason="mlx_whisper 僅限 Apple Silicon 環境（Windows/Linux 自動跳過）")


@pytest.mark.skipif(
    os.getenv("RUN_MLX_LIVE_TESTS") != "1",
    reason="live MLX model test is opt-in; use the offline adapter test for normal CI",
)
def test_mlx_whisper_direct_transcription():
    """Opt-in smoke test for a locally available MLX model and audio fixture."""
    test_file = Path(__file__).parent / "test_audio" / "test1_5sec.wav"
    if not test_file.exists():
        pytest.skip(f"optional audio fixture is not available: {test_file}")

    result = mlx_whisper.transcribe(
        str(test_file),
        path_or_hf_repo="mlx-community/whisper-medium",
        language="zh",
        word_timestamps=False,
    )

    assert isinstance(result, dict)
    assert "segments" in result
