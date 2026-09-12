#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Apple SpeechAnalyzer 平台路由與凍結契約測試（WAVE-01）。

對應 plan CHECK-01（Mac auto 預設解析）、CHECK-02（Windows/Linux 排除）、
CHECK-03 的顯式 fail-closed 路由半部，以及 CHECK-05 的契約 import 純潔。
三平台矩陣以 mock ``platform.system``/``platform.machine`` 驗證，不需要真 Mac。

Owner 2026-09-13 凍結語意：Mac 只提供 Apple SpeechAnalyzer。``auto`` 與顯式
``apple`` 的鏈嚴格為 ``("apple",)``（單一引擎、永不 fallback）；Mac 上的顯式
``transformers``／``faster_whisper``／``mlx_whisper`` 一律 ``ValueError``
（``APPLE_ONLY_BACKENDS_ERROR``）。``should_fallback`` 已刪除且不得加回。
非 Apple 平台（Windows/Linux）語意完全不變。
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
from backend.services.asr_apple import dispatcher as dispatcher_module  # noqa: E402
from backend.services.asr_apple.contract import (  # noqa: E402
    APPLE_ASSET_ERROR,
    APPLE_AUTO_FALLBACK,
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
from backend.services.asr_apple.dispatcher import (  # noqa: E402
    APPLE_ONLY_BACKENDS_ERROR,
    resolve_engine_chain as resolve_dispatcher_chain,
)

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


def test_mac_auto_engine_chain_is_single_apple(platform_kind):
    """Mac ``auto`` 的鏈嚴格等於 ``APPLE_AUTO_FALLBACK``：長度 1、無 mlx_whisper。"""

    platform_kind("Darwin", "arm64")

    chain = resolve_engine_chain("auto", BREEZE_MODEL)
    assert chain == ("apple",)
    assert chain == APPLE_AUTO_FALLBACK
    assert len(chain) == 1
    assert "mlx_whisper" not in chain
    assert resolve_engine_chain("", BREEZE_MODEL) == APPLE_AUTO_FALLBACK

    # 純函式（dispatcher）層：平台由呼叫端注入，結果相同。
    assert resolve_dispatcher_chain("auto", is_apple_platform=True) == APPLE_AUTO_FALLBACK


def test_mac_explicit_apple_is_fail_closed(platform_kind):
    platform_kind("Darwin", "arm64")

    assert resolve_platform_asr_backend("apple") == "apple"
    assert infer_asr_backend(BREEZE_MODEL, "apple") == "apple"
    for requested in ("apple", "Apple", " APPLE ", "apple"):
        assert resolve_engine_chain(requested, BREEZE_MODEL) == ("apple",)


def test_mac_explicit_legacy_backends_are_rejected(platform_kind):
    """Mac 上的顯式 Whisper 系列一律 fail-closed（硬性拒絕，無 fallback 選項）。"""

    platform_kind("Darwin", "arm64")

    for requested, normalized in (
        ("transformers", "transformers"),
        ("TRANSFORMERS", "transformers"),
        ("faster_whisper", "faster_whisper"),
        ("faster-whisper", "faster_whisper"),
        ("Faster-Whisper", "faster_whisper"),
        ("mlx_whisper", "mlx_whisper"),
        ("MLX-Whisper", "mlx_whisper"),
        ("  mlx_whisper  ", "mlx_whisper"),
    ):
        expected_message = APPLE_ONLY_BACKENDS_ERROR.format(backend=normalized)
        with pytest.raises(ValueError) as excinfo:
            resolve_engine_chain(requested, BREEZE_MODEL)
        assert str(excinfo.value) == expected_message

        with pytest.raises(ValueError) as excinfo:
            resolve_dispatcher_chain(requested, is_apple_platform=True)
        assert str(excinfo.value) == expected_message

    with pytest.raises(ValueError) as excinfo:
        infer_asr_backend(BREEZE_MODEL, "mlx-whisper")
    assert str(excinfo.value) == APPLE_ONLY_BACKENDS_ERROR.format(backend="mlx_whisper")


def test_non_mac_model_resolution_is_unchanged(platform_kind):
    """非 Mac 的模型解析完全不變：Breeze 原樣回傳，不映射任何 MLX／Whisper 模型。"""

    platform_kind("Linux", "x86_64")

    assert resolve_asr_model(BREEZE_MODEL, "auto") == BREEZE_MODEL
    assert resolve_asr_model(BREEZE_MODEL, "transformers") == BREEZE_MODEL


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


def test_dispatcher_non_mac_regression_guards():
    """非 Mac（Windows/Linux）語意完全不變：auto 單點解析、顯式 legacy 原樣通過。"""

    assert resolve_dispatcher_chain(
        "auto", is_apple_platform=False, default_backend="transformers"
    ) == ("transformers",)
    assert resolve_dispatcher_chain(
        "auto", is_apple_platform=False, default_backend="faster_whisper"
    ) == ("faster_whisper",)
    assert resolve_dispatcher_chain("mlx_whisper", is_apple_platform=False) == ("mlx_whisper",)
    assert resolve_dispatcher_chain("MLX-Whisper", is_apple_platform=False) == ("mlx_whisper",)
    assert resolve_dispatcher_chain("transformers", is_apple_platform=False) == ("transformers",)
    # router 不負責非 Mac 的 apple 拒絕：由 resolve_platform_asr_backend 拒絕
    # （見 test_non_apple_platform_rejects_explicit_apple）。
    assert resolve_dispatcher_chain("apple", is_apple_platform=False) == ("apple",)
    with pytest.raises(ValueError):
        resolve_dispatcher_chain("auto", is_apple_platform=False)


def test_unknown_backend_value_still_fails_fast(platform_kind):
    platform_kind("Windows", "AMD64")

    with pytest.raises(ValueError):
        resolve_platform_asr_backend("whisperx")
    with pytest.raises(ValueError):
        resolve_engine_chain("whisperx", BREEZE_MODEL)


# --------------------------------------------------------------------------
# CHECK-03（路由半部）＋SI-03：Mac 無 fallback 選項（should_fallback 已刪除）
# --------------------------------------------------------------------------


def test_dispatcher_exposes_no_fallback_helper():
    """SI-03：``should_fallback`` 已刪除且不得加回（Mac 已無 Whisper 備援）。"""

    assert not hasattr(dispatcher_module, "should_fallback")


def test_cancelled_error_is_still_a_typed_non_fallback_signal():
    """取消語意不變：``APPLE_CANCELLED`` 仍是可辨識的 typed 錯誤，永不觸發換手。"""

    cancelled = AppleSpeechError(APPLE_CANCELLED, "使用者已取消轉錄")
    assert is_cancelled_error(cancelled) is True
    # 其他 Apple 錯誤（含 APPLE_UNAVAILABLE 等可重試類型）在 Mac 也不再是
    # fallback 訊號：一律 fail-closed（詳見 chain integration 測試）。
    assert is_cancelled_error(AppleSpeechError(APPLE_UNAVAILABLE, "helper 缺失")) is False


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
