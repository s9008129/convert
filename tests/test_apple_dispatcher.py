#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Apple SpeechAnalyzer 平台路由與凍結契約測試（WAVE-01）。

對應 plan CHECK-01（Mac auto 預設解析）、CHECK-02（Windows/Linux 排除）、
CHECK-03 的顯式 fail-closed 路由半部，以及 CHECK-05 的契約 import 純潔。
三平台矩陣以 mock ``platform.system``/``platform.machine`` 驗證，不需要真 Mac。
"""

import json
import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("DATA_DIR", tempfile.mkdtemp())

from backend.core.asr_model_resolver import (  # noqa: E402
    infer_asr_backend,
    resolve_asr_model,
    resolve_engine_chain,
)
from backend.core.platform_config import resolve_platform_asr_backend  # noqa: E402
from backend.services.asr_apple.contract import (  # noqa: E402
    APPLE_ASSET_ERROR,
    APPLE_CANCELLED,
    APPLE_ERROR_CODES,
    APPLE_EXIT_CODE_TO_ERROR_CODE,
    APPLE_INPUT_ERROR,
    APPLE_OUTPUT_INVALID,
    APPLE_TIMEOUT,
    APPLE_TRANSCRIPTION_ERROR,
    APPLE_UNAVAILABLE,
    AppleSpeechError,
    is_cancelled_error,
)
from backend.services.asr_apple.dispatcher import should_fallback  # noqa: E402

BREEZE_MODEL = "MediaTek-Research/Breeze-ASR-26"


@pytest.fixture
def platform_kind(monkeypatch):
    """把 `platform.system/machine` 固定成指定平台（未知平台視為非 Mac）。"""

    def _set(system: str, machine: str) -> None:
        monkeypatch.setattr(platform, "system", lambda: system)
        monkeypatch.setattr(platform, "machine", lambda: machine)

    return _set


# --------------------------------------------------------------------------
# CHECK-01：Mac（darwin + arm64）auto 預設 Apple
# --------------------------------------------------------------------------


def test_mac_auto_resolves_to_apple(platform_kind):
    platform_kind("Darwin", "arm64")

    assert resolve_platform_asr_backend("auto") == "apple"
    assert infer_asr_backend(BREEZE_MODEL, "auto") == "apple"


def test_mac_auto_engine_chain_keeps_mlx_fallback(platform_kind):
    platform_kind("Darwin", "arm64")

    assert resolve_engine_chain("auto", BREEZE_MODEL) == ("apple", "mlx_whisper")
    assert resolve_engine_chain("", BREEZE_MODEL) == ("apple", "mlx_whisper")


def test_mac_explicit_apple_is_fail_closed(platform_kind):
    platform_kind("Darwin", "arm64")

    assert resolve_platform_asr_backend("apple") == "apple"
    assert infer_asr_backend(BREEZE_MODEL, "apple") == "apple"
    for requested in ("apple", "Apple", " APPLE ", "apple"):
        assert resolve_engine_chain(requested, BREEZE_MODEL) == ("apple",)


def test_mac_explicit_backends_are_respected(platform_kind):
    platform_kind("Darwin", "arm64")

    assert resolve_engine_chain("mlx_whisper", BREEZE_MODEL) == ("mlx_whisper",)
    assert resolve_engine_chain("MLX-Whisper", BREEZE_MODEL) == ("mlx_whisper",)
    assert resolve_engine_chain("faster-whisper", "large-v3") == ("faster_whisper",)
    assert resolve_engine_chain("transformers", BREEZE_MODEL) == ("transformers",)
    assert infer_asr_backend(BREEZE_MODEL, "mlx-whisper") == "mlx_whisper"
    # auto 的模型解析仍指向 MLX 版 Breeze（Apple 失敗時的 fallback 模型）。
    assert resolve_asr_model(BREEZE_MODEL, "auto") == "doggy8088/Breeze-ASR-26-MLX"


def test_darwin_intel_is_not_an_apple_platform(platform_kind):
    platform_kind("Darwin", "x86_64")

    assert resolve_engine_chain("auto", BREEZE_MODEL) == ("transformers",)
    with pytest.raises(ValueError, match="僅 macOS"):
        resolve_platform_asr_backend("apple")


# --------------------------------------------------------------------------
# CHECK-02：非 Mac（Windows / Linux / 未知）永遠不含 apple
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("system", "machine"),
    [("Windows", "AMD64"), ("Linux", "x86_64"), ("FreeBSD", "amd64")],
)
def test_non_mac_auto_never_resolves_to_apple(platform_kind, system, machine):
    platform_kind(system, machine)

    chain = resolve_engine_chain("auto", BREEZE_MODEL)
    assert "apple" not in chain
    assert chain == (infer_asr_backend(BREEZE_MODEL, "auto"),)
    assert infer_asr_backend(BREEZE_MODEL, "auto") == "transformers"
    assert resolve_engine_chain("auto", "large-v3") == ("faster_whisper",)


@pytest.mark.parametrize(
    ("system", "machine"),
    [("Windows", "AMD64"), ("Linux", "aarch64"), ("Darwin", "x86_64")],
)
def test_non_apple_platform_rejects_explicit_apple(platform_kind, system, machine):
    platform_kind(system, machine)

    with pytest.raises(ValueError, match="僅 macOS"):
        resolve_platform_asr_backend("apple")
    with pytest.raises(ValueError, match="僅 macOS"):
        resolve_engine_chain("apple", BREEZE_MODEL)
    with pytest.raises(ValueError, match="僅 macOS"):
        infer_asr_backend(BREEZE_MODEL, "apple")


def test_non_mac_explicit_backends_unchanged(platform_kind):
    platform_kind("Linux", "x86_64")

    assert resolve_engine_chain("mlx_whisper", BREEZE_MODEL) == ("mlx_whisper",)
    assert resolve_engine_chain("transformers", BREEZE_MODEL) == ("transformers",)
    assert resolve_engine_chain("faster_whisper", "large-v3") == ("faster_whisper",)


def test_unknown_backend_value_still_fails_fast(platform_kind):
    platform_kind("Windows", "AMD64")

    with pytest.raises(ValueError):
        resolve_platform_asr_backend("whisperx")
    with pytest.raises(ValueError):
        resolve_engine_chain("whisperx", BREEZE_MODEL)


# --------------------------------------------------------------------------
# CHECK-03（路由半部）＋SI-03：取消永不 fallback
# --------------------------------------------------------------------------


def test_cancellation_never_falls_back():
    assert should_fallback(APPLE_CANCELLED) is False
    assert should_fallback(APPLE_UNAVAILABLE) is True
    assert should_fallback(APPLE_ASSET_ERROR) is True
    assert should_fallback(APPLE_INPUT_ERROR) is True
    assert should_fallback(APPLE_TRANSCRIPTION_ERROR) is True
    assert should_fallback(APPLE_TIMEOUT) is True
    assert should_fallback(APPLE_OUTPUT_INVALID) is True
    assert should_fallback(None) is True


# --------------------------------------------------------------------------
# SI-05：helper 離場碼與錯誤碼表凍結
# --------------------------------------------------------------------------


def test_helper_exit_code_table_is_frozen():
    assert APPLE_EXIT_CODE_TO_ERROR_CODE == {
        0: None,
        1: None,
        2: APPLE_UNAVAILABLE,
        3: "APPLE_LOCALE_UNSUPPORTED",
        4: APPLE_ASSET_ERROR,
        5: APPLE_INPUT_ERROR,
        6: APPLE_TRANSCRIPTION_ERROR,
        7: APPLE_CANCELLED,
    }
    assert APPLE_ERROR_CODES == (
        APPLE_UNAVAILABLE,
        "APPLE_LOCALE_UNSUPPORTED",
        APPLE_ASSET_ERROR,
        APPLE_INPUT_ERROR,
        APPLE_TRANSCRIPTION_ERROR,
        APPLE_TIMEOUT,
        APPLE_CANCELLED,
        APPLE_OUTPUT_INVALID,
    )


def test_apple_speech_error_carries_stable_code():
    error = AppleSpeechError(APPLE_ASSET_ERROR, "asset 未安裝", context={"locale": "zh-Hant-TW"})

    assert error.code == APPLE_ASSET_ERROR
    assert str(error) == "asset 未安裝"
    assert error.context == {"locale": "zh-Hant-TW"}
    assert is_cancelled_error(AppleSpeechError(APPLE_CANCELLED, "取消")) is True
    assert is_cancelled_error(error) is False


# --------------------------------------------------------------------------
# CHECK-05：契約 import 純潔（乾淨子行程驗證）
# --------------------------------------------------------------------------


def test_contract_import_stays_lightweight():
    """`import contract` 不得拉入重型 ML 依賴（NFR-03 / SI-11）。"""

    program = (
        "import json, sys\n"
        "import backend.services.asr_apple.contract\n"
        "import backend.services.asr_apple.dispatcher\n"
        "heavy = [name for name in ('torch', 'mlx_whisper', 'mlx', 'silero', "
        "'faster_whisper', 'transformers') if name in sys.modules]\n"
        "print(json.dumps(heavy))\n"
    )
    completed = subprocess.run(
        [sys.executable, "-c", program],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=True,
    )

    # loguru 的啟動訊息會出現在 stdout，取最後一行當作程式輸出。
    payload = json.loads(completed.stdout.strip().splitlines()[-1])
    assert payload == []
