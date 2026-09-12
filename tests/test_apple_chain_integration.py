#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Apple 引擎鏈整合測試（WAVE-03b；SI-02／SI-03／SI-09／SI-10）。

以 monkeypatch 假造 helper 離場碼，驗證 ``TranscriptionService.transcribe_detailed``
的三條凍結語意：

1. 顯式 ``ASR_BACKEND=apple``：Apple 失敗（helper 回 4／6／1）直接向上拋，
   鏈長 1、不試 mlx_whisper（fail-closed）。
2. ``auto``（mock darwin arm64）：Apple 失敗（非取消）→ 進度提示後 fallback
   mlx_whisper。
3. ``auto`` ＋ helper 回 7（``APPLE_CANCELLED``）：取消永不 fallback。

另補 Apple 分支的 ``_detect_runtime``／``_load_model``／``get_device_info``
（不偵測裝置、不載入模型、不 import mlx/torch）與 settings 轉接。

``backend/services/asr_apple/apple_cli.py`` 的介面已凍結；本檔只 monkeypatch
其中的 ``resolve_executable``／``probe_executable``／``build_transcribe_argv``／
``run_helper``，其餘（payload 驗證、錯誤分類、正規化）走真實實作。
"""

import json
import os
import sys
import tempfile
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

os.environ["DATA_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.core.asr_model_resolver import resolve_asr_model  # noqa: E402
from backend.core.config import settings  # noqa: E402
from backend.services.asr_apple import apple as apple_provider  # noqa: E402
from backend.services.asr_apple import apple_cli  # noqa: E402
from backend.services.asr_apple.contract import (  # noqa: E402
    APPLE_ASSET_ERROR,
    APPLE_CANCELLED,
    APPLE_OUTPUT_INVALID,
    APPLE_TRANSCRIPTION_ERROR,
    ASRSegment,
    AppleSpeechError,
)
from backend.services.device_detector import DeviceType  # noqa: E402
from backend.services.transcription import (  # noqa: E402
    DetailedTranscriptionResult,
    TranscriptionChunk,
    TranscriptionService,
)

FAKE_HELPER = "/fake/bin/apple-speech-cli"

EXPECTED_METADATA_KEYS = {
    "requested_engine",
    "resolved_engine",
    "engine_chain",
    "locale",
    "audio_duration_seconds",
    "elapsed_seconds",
    "real_time_factor",
    "helper_invocations",
    "conversion_reason",
    "conversion_seconds",
    "segment_count",
    "segments_dropped",
    "segments_time_degraded",
}

#: schema 1.0 的最小成功 payload（走真實 ``validate_transcription_payload``）。
SUCCESS_PAYLOAD = {
    "schema_version": "1.0",
    "engine": "apple",
    "text": "今天天氣很好 ，我們一起去公園散步",
    "locale": "zh-Hant-TW",
    "segments": [
        {"start": 0.0, "end": 1.5, "text": "今天天氣很好 ，"},
        {"start": 1.5, "end": 3.0, "text": "我們一起去公園散步"},
    ],
    "metadata": {"audio_duration_seconds": 12.0, "asset_status": "installed"},
}


def _helper_result(returncode=0, stdout="", stderr="", timed_out=False, cancelled=False):
    return apple_cli.HelperResult(
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        timed_out=timed_out,
        cancelled=cancelled,
    )


@pytest.fixture
def darwin_apple_platform(monkeypatch):
    """把平台判定固定成 Apple（測試可移植，不在真實平台跑真 helper）。"""

    monkeypatch.setattr("backend.core.asr_model_resolver.is_darwin_arm64", lambda: True)
    monkeypatch.setattr("backend.core.platform_config.is_darwin_arm64", lambda: True)
    monkeypatch.setattr(apple_provider, "_current_platform", lambda: "Darwin")


@pytest.fixture
def apple_env(darwin_apple_platform, tmp_path, monkeypatch):
    """假造 helper 邊界；回傳 (state, audio_path)。

    ``state.returncode``／``state.stdout`` 控制 helper 的離開碼與輸出；
    ``state.events`` 記錄引擎實際被呼叫的順序。
    """

    # uploads_dir 是 DATA_DIR 的 property；改 DATA_DIR 讓音檔落在暫存目錄內。
    monkeypatch.setattr(settings, "DATA_DIR", str(tmp_path))
    uploads_dir = Path(settings.uploads_dir)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    audio_path = uploads_dir / "meeting.m4a"  # 原生容器：不觸發轉檔
    audio_path.write_bytes(b"fake-m4a")

    monkeypatch.setattr(settings, "APPLE_LOCALE", "zh-Hant-TW")
    monkeypatch.setattr(settings, "APPLE_PRESET", "time-indexed")
    monkeypatch.setattr(settings, "APPLE_ENABLE_PREFLIGHT", True)
    monkeypatch.setattr(settings, "APPLE_SPEECH_CLI_PATH", "/configured/apple-speech-cli")

    # ffprobe 量長度屬 I/O；整合測試固定回 12 秒。
    monkeypatch.setattr(apple_provider, "_measure_duration_seconds", lambda path: 12.0)

    state = SimpleNamespace(
        resolve_configured=[],
        probe_calls=[],
        helper_calls=[],
        build_kwargs=None,
        returncode=0,
        stdout="",
        events=[],
    )

    def fake_resolve(configured=None, *, repo_root=None, which=None):
        state.resolve_configured.append(configured)
        return FAKE_HELPER

    def fake_probe(executable, *, locale, timeout_seconds=None, cancel_event=None):
        state.probe_calls.append({"executable": executable, "locale": locale})
        return {"locale_supported": True, "asset_status": "installed"}

    real_build = apple_cli.build_transcribe_argv

    def recording_build(executable, *, input_path, locale, preset, timeout_seconds):
        state.build_kwargs = {
            "executable": executable,
            "input_path": input_path,
            "locale": locale,
            "preset": preset,
            "timeout_seconds": timeout_seconds,
        }
        return real_build(
            executable,
            input_path=input_path,
            locale=locale,
            preset=preset,
            timeout_seconds=timeout_seconds,
        )

    def fake_run_helper(argv, *, timeout_seconds, cancel_event=None, on_progress=None):
        state.helper_calls.append({"argv": list(argv), "timeout_seconds": timeout_seconds})
        state.events.append("apple")
        return _helper_result(returncode=state.returncode, stdout=state.stdout, stderr="helper boom")

    monkeypatch.setattr(apple_cli, "resolve_executable", fake_resolve)
    monkeypatch.setattr(apple_cli, "probe_executable", fake_probe)
    monkeypatch.setattr(apple_cli, "build_transcribe_argv", recording_build)
    monkeypatch.setattr(apple_cli, "run_helper", fake_run_helper)
    return state, audio_path


def _patch_mlx(monkeypatch, calls, events=None):
    """假造 mlx_whisper 引擎：不載入模型、回傳可辨識的結果。"""

    def fake_transcribe_mlx(self, audio_path):
        calls.append(audio_path)
        if events is not None:
            events.append("mlx")
        return DetailedTranscriptionResult(
            text="mlx 逐字稿",
            duration_seconds=3.0,
            language="zh",
            chunks=[TranscriptionChunk(start=0.0, end=3.0, text="mlx 逐字稿")],
            backend="mlx_whisper",
        )

    monkeypatch.setattr(TranscriptionService, "_transcribe_with_mlx_whisper", fake_transcribe_mlx)
    monkeypatch.setattr(TranscriptionService, "_load_mlx_whisper_model", lambda self: None)


# ---------------------------------------------------------------------------
# 語意 1：顯式 apple ＋ helper 失敗 → fail-closed
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("helper_exit", "expected_code"),
    [
        (4, APPLE_ASSET_ERROR),
        (6, APPLE_TRANSCRIPTION_ERROR),
        (1, APPLE_OUTPUT_INVALID),
    ],
)
def test_explicit_apple_failure_never_falls_back(apple_env, monkeypatch, helper_exit, expected_code):
    state, audio_path = apple_env
    state.returncode = helper_exit
    monkeypatch.setattr(settings, "ASR_BACKEND", "apple")

    service = TranscriptionService()
    mlx_calls = []
    _patch_mlx(monkeypatch, mlx_calls)

    with pytest.raises(AppleSpeechError) as excinfo:
        service.transcribe_detailed(str(audio_path))

    assert excinfo.value.code == expected_code
    assert "未 fallback" in excinfo.value.user_message
    assert len(state.helper_calls) == 1
    assert state.events == ["apple"]
    assert mlx_calls == []


# ---------------------------------------------------------------------------
# 語意 2：auto ＋ Apple 失敗（非取消）→ fallback mlx_whisper
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("helper_exit", [4, 6, 1])
def test_auto_apple_failure_falls_back_to_mlx_whisper(apple_env, monkeypatch, helper_exit):
    state, audio_path = apple_env
    state.returncode = helper_exit
    monkeypatch.setattr(settings, "ASR_BACKEND", "auto")

    service = TranscriptionService()
    mlx_calls = []
    _patch_mlx(monkeypatch, mlx_calls, events=state.events)
    progress = []

    result = service.transcribe_detailed(
        str(audio_path),
        progress_callback=lambda percent, message: progress.append((percent, message)),
    )

    assert result.backend == "mlx_whisper"
    assert result.text == "mlx 逐字稿"
    assert state.events == ["apple", "mlx"]  # Apple 先試、失敗後才換手
    assert len(state.helper_calls) == 1
    assert mlx_calls == [str(audio_path)]
    assert any("mlx_whisper" in message for _, message in progress)


# ---------------------------------------------------------------------------
# 語意 3：auto ＋ APPLE_CANCELLED → 永不 fallback
# ---------------------------------------------------------------------------


def test_auto_cancelled_apple_never_falls_back(apple_env, monkeypatch):
    state, audio_path = apple_env
    state.returncode = 7  # 凍結離場碼：APPLE_CANCELLED
    monkeypatch.setattr(settings, "ASR_BACKEND", "auto")

    service = TranscriptionService()
    mlx_calls = []
    _patch_mlx(monkeypatch, mlx_calls, events=state.events)

    with pytest.raises(AppleSpeechError) as excinfo:
        service.transcribe_detailed(str(audio_path))

    assert excinfo.value.code == APPLE_CANCELLED
    assert "未 fallback" in excinfo.value.user_message
    assert state.events == ["apple"]
    assert mlx_calls == []


# ---------------------------------------------------------------------------
# 成功路徑：payload 驗證、正規化、metadata、settings 轉接
# ---------------------------------------------------------------------------


def test_auto_apple_success_exposes_metadata_and_skips_mlx(apple_env, monkeypatch):
    state, audio_path = apple_env
    state.stdout = json.dumps(SUCCESS_PAYLOAD, ensure_ascii=False)
    monkeypatch.setattr(settings, "ASR_BACKEND", "auto")

    service = TranscriptionService()
    mlx_calls = []
    _patch_mlx(monkeypatch, mlx_calls, events=state.events)
    progress = []

    result = service.transcribe_detailed(
        str(audio_path),
        progress_callback=lambda percent, message: progress.append((percent, message)),
    )

    assert result.backend == "apple"
    assert result.text == "今天天氣很好，我們一起去公園散步"
    assert [chunk.text for chunk in result.chunks] == ["今天天氣很好，", "我們一起去公園散步"]
    assert result.chunks[0].start == 0.0 and result.chunks[0].end == 1.5
    assert result.language == "zh-Hant-TW"
    assert result.duration_seconds == 12.0

    assert set(result.metadata) == EXPECTED_METADATA_KEYS
    assert result.metadata["requested_engine"] == "auto"
    assert result.metadata["resolved_engine"] == "apple"
    assert result.metadata["engine_chain"] == "apple,mlx_whisper"
    assert result.metadata["locale"] == "zh-Hant-TW"
    assert result.metadata["audio_duration_seconds"] == 12.0
    assert result.metadata["helper_invocations"] == 1
    assert result.metadata["segment_count"] == 2

    # 設定層轉接：executable／locale／preset（helper argv 內含）
    assert state.resolve_configured == ["/configured/apple-speech-cli"]
    assert state.build_kwargs["locale"] == "zh-Hant-TW"
    assert state.build_kwargs["preset"] == "time-indexed"
    assert state.build_kwargs["executable"] == FAKE_HELPER
    assert "--locale" in state.helper_calls[0]["argv"]

    assert state.events == ["apple"]
    assert mlx_calls == []
    assert progress[-1] == (60.0, "轉錄完成")


def test_apple_engine_forwards_settings_and_maps_provider_result(apple_env, monkeypatch):
    """以 recorder 取代 provider：驗證 locale/preset/executable/preflight 轉接與欄位映射。"""

    _, audio_path = apple_env
    monkeypatch.setattr(settings, "ASR_BACKEND", "apple")
    monkeypatch.setattr(settings, "APPLE_LOCALE", "ja-JP")
    monkeypatch.setattr(settings, "APPLE_PRESET", "progressive")
    monkeypatch.setattr(settings, "APPLE_ENABLE_PREFLIGHT", False)
    monkeypatch.setattr(settings, "APPLE_SPEECH_CLI_PATH", "/custom/helper")

    captured = {}

    def fake_provider(
        path,
        *,
        locale,
        preset,
        progress_callback=None,
        cancel_event=None,
        executable_path=None,
        enable_preflight=True,
    ):
        captured.update(
            {
                "path": path,
                "locale": locale,
                "preset": preset,
                "executable_path": executable_path,
                "enable_preflight": enable_preflight,
                "cancel_event": cancel_event,
            }
        )
        return apple_provider.AppleTranscriptionResult(
            text="こんにちは",
            segments=(ASRSegment(start=None, end=None, text="こんにちは"),),
            metadata={"helper_invocations": 1, "locale": locale},
            duration_seconds=1.5,
            language=locale,
        )

    monkeypatch.setattr(apple_provider, "transcribe_with_apple", fake_provider)

    service = TranscriptionService()
    result = service.transcribe_detailed(str(audio_path))

    assert captured["path"] == str(audio_path)
    assert captured["locale"] == "ja-JP"
    assert captured["preset"] == "progressive"
    assert captured["executable_path"] == "/custom/helper"
    assert captured["enable_preflight"] is False
    assert captured["cancel_event"] is None

    assert result.backend == "apple"
    assert result.language == "ja-JP"
    assert result.duration_seconds == 1.5
    assert result.chunks[0].text == "こんにちは"
    assert result.metadata["requested_engine"] == "apple"
    assert result.metadata["resolved_engine"] == "apple"
    assert result.metadata["engine_chain"] == "apple"
    assert result.metadata["helper_invocations"] == 1


# ---------------------------------------------------------------------------
# Apple 分支：不偵測裝置、不載入模型、裝置資訊無害
# ---------------------------------------------------------------------------


def test_apple_runtime_detection_touches_no_device_detector(darwin_apple_platform, monkeypatch):
    service = TranscriptionService()
    monkeypatch.setattr(settings, "ASR_BACKEND", "apple")

    def forbidden_detection():
        raise AssertionError("Apple 路徑不得偵測裝置")

    monkeypatch.setattr(
        "backend.services.transcription.device_detector.detect_best_device",
        forbidden_detection,
    )

    assert service._detect_runtime() == ("cpu", "int8")


def test_apple_load_model_is_model_free(apple_env, monkeypatch):
    service = TranscriptionService()
    monkeypatch.setattr(settings, "ASR_BACKEND", "apple")

    class _ExplodingModule(types.ModuleType):
        def __getattr__(self, name):
            raise AssertionError(f"Apple 路徑不得觸碰 {name}")

    monkeypatch.setitem(sys.modules, "mlx_whisper", _ExplodingModule("mlx_whisper"))
    monkeypatch.setitem(sys.modules, "torch", _ExplodingModule("torch"))

    service._load_model()

    assert service._backend == "apple"
    assert service._model is None
    assert service._device == DeviceType.CPU
    assert service._compute_type == "int8"


def test_get_device_info_apple_reports_neural_engine(apple_env, monkeypatch):
    service = TranscriptionService()
    monkeypatch.setattr(settings, "ASR_BACKEND", "apple")
    service._backend = "apple"

    info = service.get_device_info()

    assert info["device"] == "apple-neural"
    assert info["accelerator"] == "apple-neural"
    assert info["compute_type"] == "n/a"
    assert info["backend"] == "apple"
    assert info["asr_backend"] == "apple"
    assert info["model"] == resolve_asr_model(settings.WHISPER_MODEL, settings.ASR_BACKEND)
    assert set(info) == {
        "device",
        "compute_type",
        "backend",
        "accelerator",
        "asr_backend",
        "model",
        "revision",
        "asr_model",
    }
