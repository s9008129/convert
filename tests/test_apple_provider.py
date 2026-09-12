#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Apple SpeechAnalyzer provider 單測（WAVE-03b）。

覆蓋 plan CHECK-06（逾時下限）、CHECK-08（輸出驗證後的組裝）、CHECK-09（CJK
空白）、CHECK-10（暫存衛生）、CHECK-11（健康可觀察）與 REQ-05/06/09/10。

``backend/services/asr_apple/apple_cli.py`` 由另一個 wave 平行實作；本檔一律以
monkeypatch 假造其凍結函式，因此不依賴其實作細節。若該檔尚未出現，測試會先注入
一個忠實的 fake 模組（介面照 handoff 凍結簽名）再 import provider。
"""

import types
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import os
import re
import sys
import tempfile
import time

import pytest

os.environ["DATA_DIR"] = tempfile.mkdtemp()
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.services.asr_apple.contract import (  # noqa: E402
    APPLE_ASSET_ERROR,
    APPLE_CANCELLED,
    APPLE_INPUT_ERROR,
    APPLE_LOCALE_UNSUPPORTED,
    APPLE_OUTPUT_INVALID,
    APPLE_TIMEOUT,
    APPLE_TRANSCRIPTION_ERROR,
    APPLE_UNAVAILABLE,
    AppleSpeechError,
)

FAKE_FFMPEG = "/fake/bin/ffmpeg"
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

_SCALAR_TYPES = (str, int, float, bool, type(None))


# ---------------------------------------------------------------------------
# fake apple_cli（僅在真檔尚未出現時使用）
# ---------------------------------------------------------------------------


def _build_fake_apple_cli() -> types.ModuleType:
    module = types.ModuleType("backend.services.asr_apple.apple_cli")

    cjk_text_class = "\u3040-\u30ff\u31f0-\u31ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"
    cjk_mark_class = (
        "\u2014\u2018\u2019\u201c\u201d\u2026"
        "\u3001-\u303f"
        "\uff01-\uff0f\uff1a-\uff20\uff3b-\uff40\uff5b-\uff65"
    )
    whitespace_run = re.compile(r"\s+")
    space_between_cjk = re.compile(rf"(?<=[{cjk_text_class}])[\s]+(?=[{cjk_text_class}])")
    space_before_mark = re.compile(rf"[\s]+(?=[{cjk_mark_class}])")
    space_after_mark = re.compile(rf"(?<=[{cjk_mark_class}])[\s]+")

    def normalize_apple_text(text: str) -> str:
        if not isinstance(text, str):
            return ""
        normalized = whitespace_run.sub(" ", text)
        normalized = space_between_cjk.sub("", normalized)
        normalized = space_before_mark.sub("", normalized)
        normalized = space_after_mark.sub("", normalized)
        return normalized.strip()

    def resolved_timeout_seconds(duration_seconds) -> float:
        if not isinstance(duration_seconds, (int, float)) or isinstance(duration_seconds, bool):
            return 600.0
        value = float(duration_seconds)
        if value <= 0 or value != value:
            return 600.0
        return max(600.0, value * 3.0 + 300.0)

    @dataclass(frozen=True)
    class HelperResult:
        returncode: int | None = None
        stdout: str = ""
        stderr: str = ""
        timed_out: bool = False
        cancelled: bool = False

    exit_codes = {
        2: APPLE_UNAVAILABLE,
        3: APPLE_LOCALE_UNSUPPORTED,
        4: APPLE_ASSET_ERROR,
        5: APPLE_INPUT_ERROR,
        6: APPLE_TRANSCRIPTION_ERROR,
        7: APPLE_CANCELLED,
    }

    def error_from_helper_result(result, *, stage: str) -> AppleSpeechError:
        if getattr(result, "cancelled", False):
            code = APPLE_CANCELLED
        elif getattr(result, "timed_out", False):
            code = APPLE_TIMEOUT
        elif getattr(result, "returncode", None) in exit_codes:
            code = exit_codes[getattr(result, "returncode", None)]
        else:
            code = APPLE_OUTPUT_INVALID
        return AppleSpeechError(code, f"fake helper error ({code})", context={"stage": stage})

    def _not_patched(name):
        def _fail(*args, **kwargs):
            raise AssertionError(f"fake apple_cli.{name} 必須由測試 monkeypatch")

        return _fail

    module.HelperResult = HelperResult
    module.normalize_apple_text = normalize_apple_text
    module.resolved_timeout_seconds = resolved_timeout_seconds
    module.error_from_helper_result = error_from_helper_result
    module.resolve_executable = _not_patched("resolve_executable")
    module.probe_executable = _not_patched("probe_executable")
    module.run_helper = _not_patched("run_helper")
    module.build_probe_argv = _not_patched("build_probe_argv")
    module.build_transcribe_argv = _not_patched("build_transcribe_argv")
    module.validate_transcription_payload = _not_patched("validate_transcription_payload")
    module.parse_progress_line = lambda line: None
    return module


def _load_apple_cli() -> types.ModuleType:
    import importlib

    try:
        return importlib.import_module("backend.services.asr_apple.apple_cli")
    except ModuleNotFoundError:
        module = _build_fake_apple_cli()
        sys.modules[module.__name__] = module
        package = importlib.import_module("backend.services.asr_apple")
        setattr(package, module.__name__.rsplit(".", 1)[1], module)
        return module


apple_cli = _load_apple_cli()

from backend.services.asr_apple import apple  # noqa: E402


# ---------------------------------------------------------------------------
# 測試替身
# ---------------------------------------------------------------------------


def _helper_result(returncode=0, stdout="", stderr="", timed_out=False, cancelled=False):
    cls = getattr(apple_cli, "HelperResult", None)
    if cls is not None:
        try:
            return cls(
                returncode=returncode,
                stdout=stdout,
                stderr=stderr,
                timed_out=timed_out,
                cancelled=cancelled,
            )
        except TypeError:  # pragma: no cover - 真檔欄位順序不同時的最後防線
            pass
    return SimpleNamespace(
        returncode=returncode,
        stdout=stdout,
        stderr=stderr,
        timed_out=timed_out,
        cancelled=cancelled,
    )


def _payload(
    text="今天天氣很好 ，我們一起去公園散步。",
    segments=None,
    locale="zh-Hant-TW",
    metadata=None,
    dropped=0,
    degraded=0,
):
    if segments is None:
        segments = (
            SimpleNamespace(start=0.0, end=1.5, text="今天天氣很好"),
            SimpleNamespace(start=None, end=None, text="我們一起去公園散步。"),
        )
    return SimpleNamespace(
        text=text,
        segments=segments,
        locale=locale,
        metadata=metadata or {},
        segments_dropped=dropped,
        segments_time_degraded=degraded,
    )


class _StubCli:
    """可控的 apple_cli 替身，記錄 provider 實際傳入的參數。"""

    def __init__(self):
        self.resolved_configured = []
        self.probe_calls = []
        self.build_transcribe_kwargs = None
        self.helper_calls = []
        self.conversion_calls = []
        self.progress = []
        self.helper_result_factory = lambda: _helper_result(returncode=0, stdout="{}")
        self.conversion_result_factory = lambda argv, index: _helper_result(returncode=0)
        self.helper_events = []
        self.payload = _payload()
        self.resolve_error = None
        self.probe_error = None
        self.executable = FAKE_HELPER

    def conversion_timeouts(self):
        return [call["timeout_seconds"] for call in self.conversion_calls]


@pytest.fixture
def stub_cli(monkeypatch):
    stub = _StubCli()

    monkeypatch.setattr(apple, "_current_platform", lambda: "Darwin")
    monkeypatch.setattr(apple, "_resolve_ffmpeg", lambda: FAKE_FFMPEG)
    monkeypatch.setattr(apple, "_resolve_ffprobe", lambda: "/fake/bin/ffprobe")

    def fake_resolve(configured=None, *, repo_root=None, which=None):
        stub.resolved_configured.append(configured)
        if stub.resolve_error is not None:
            raise stub.resolve_error
        return stub.executable

    def fake_probe(executable, *, locale, timeout_seconds=120.0, cancel_event=None):
        stub.probe_calls.append(
            {"executable": executable, "locale": locale, "timeout_seconds": timeout_seconds}
        )
        if stub.probe_error is not None:
            raise stub.probe_error
        return {"locale_supported": True, "helper_version": "0.1.0"}

    def fake_build_transcribe_argv(executable, *, input_path, locale, preset, timeout_seconds):
        stub.build_transcribe_kwargs = {
            "executable": executable,
            "input_path": input_path,
            "locale": locale,
            "preset": preset,
            "timeout_seconds": timeout_seconds,
        }
        return [executable, "transcribe", "--input", input_path, "--locale", locale, "--preset", preset]

    def fake_run_helper(argv, *, timeout_seconds, cancel_event=None, on_progress=None):
        argv = list(argv)
        if argv and argv[0] == FAKE_FFMPEG:
            stub.conversion_calls.append({"argv": argv, "timeout_seconds": timeout_seconds})
            result = stub.conversion_result_factory(argv, len(stub.conversion_calls))
            if (
                getattr(result, "returncode", None) == 0
                and not getattr(result, "timed_out", False)
                and not getattr(result, "cancelled", False)
            ):
                Path(argv[-1]).write_bytes(b"RIFF-fake-wav")
            return result

        stub.helper_calls.append({"argv": argv, "timeout_seconds": timeout_seconds})
        for event in stub.helper_events:
            if on_progress is not None:
                on_progress(*event)
        return stub.helper_result_factory()

    monkeypatch.setattr(apple_cli, "resolve_executable", fake_resolve)
    monkeypatch.setattr(apple_cli, "probe_executable", fake_probe)
    monkeypatch.setattr(apple_cli, "build_transcribe_argv", fake_build_transcribe_argv)
    monkeypatch.setattr(apple_cli, "run_helper", fake_run_helper)
    monkeypatch.setattr(apple_cli, "validate_transcription_payload", lambda raw_stdout: stub.payload)
    return stub


def _audio(tmp_path: Path, name: str = "meeting.mp3", payload: bytes = b"fake-audio") -> Path:
    path = tmp_path / name
    path.write_bytes(payload)
    return path


def _transcribe(tmp_path, stub_cli, name="meeting.mp3", **kwargs):
    audio_path = _audio(tmp_path, name)
    options = {
        "locale": "zh-Hant-TW",
        "preset": "time-indexed",
        "progress_callback": None,
        "cancel_event": None,
        "executable_path": None,
        "enable_preflight": True,
    }
    options.update(kwargs)
    result = apple.transcribe_with_apple(str(audio_path), **options)
    return audio_path, result


# ---------------------------------------------------------------------------
# 轉檔政策（SI-07）
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("suffix", "expected"),
    [
        (".mp3", "fragile_native_container"),
        (".webm", "non_native_container"),
        (".ogg", "non_native_container"),
        (".flac", "non_native_container"),
        (".m4a", None),
        (".mp4", None),
        (".wav", None),
        (".aif", None),
        (".aiff", None),
        (".caf", None),
    ],
)
def test_preflight_conversion_reason_matrix(suffix, expected):
    assert apple.preflight_conversion_reason(suffix) == expected


def test_frozen_provider_surface_signatures():
    """凍結呼叫面：WAVE-04（routes／health）以這些簽名直接呼叫 provider。"""

    import inspect

    transcribe = inspect.signature(apple.transcribe_with_apple)
    assert list(transcribe.parameters) == [
        "audio_path",
        "locale",
        "preset",
        "progress_callback",
        "cancel_event",
        "executable_path",
        "enable_preflight",
    ]
    assert transcribe.parameters["audio_path"].kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
    for name in ("locale", "preset", "progress_callback", "cancel_event", "executable_path", "enable_preflight"):
        assert transcribe.parameters[name].kind is inspect.Parameter.KEYWORD_ONLY
    assert transcribe.parameters["enable_preflight"].default is True
    assert transcribe.parameters["progress_callback"].default is None

    status = inspect.signature(apple.apple_helper_status)
    assert list(status.parameters) == ["configured_path"]
    assert status.parameters["configured_path"].kind is inspect.Parameter.KEYWORD_ONLY
    assert status.parameters["configured_path"].default is None

    sweep = inspect.signature(apple.sweep_stale_apple_temp_files)
    assert list(sweep.parameters) == ["directory", "max_age_seconds"]
    assert sweep.parameters["max_age_seconds"].kind is inspect.Parameter.KEYWORD_ONLY

    assert list(apple.AppleTranscriptionResult.__dataclass_fields__) == [
        "text",
        "segments",
        "metadata",
        "duration_seconds",
        "language",
    ]
    assert apple.AppleTranscriptionResult.__dataclass_params__.frozen is True


def test_frozen_constants_match_contract():
    assert apple.CONVERSION_SUFFIX == ".wav"
    assert apple.CONVERSION_ARGS == ("-vn", "-c:a", "pcm_s16le", "-ar", "16000", "-ac", "1")
    assert apple.NATIVE_INPUT_SUFFIXES == frozenset({".m4a", ".mp4", ".wav", ".aif", ".aiff", ".caf", ".mp3"})
    assert apple.PREFLIGHT_CONVERSION_SUFFIXES == frozenset({".mp3"})
    assert apple.CONVERSION_TIMEOUT_FLOOR_SECONDS == 600.0


def test_transcribe_converts_mp3_with_frozen_flags_and_cleans_temp(tmp_path, stub_cli):
    audio_path, result = _transcribe(tmp_path, stub_cli, name="Meeting.MP3")

    assert len(stub_cli.conversion_calls) == 1
    argv = stub_cli.conversion_calls[0]["argv"]

    # ffmpeg 參數逐項斷言（凍結順序）
    frozen = list(apple.CONVERSION_ARGS)
    assert argv[0] == FAKE_FFMPEG
    assert argv[1:8] == ["-nostdin", "-hide_banner", "-loglevel", "error", "-y", "-i", str(audio_path)]
    assert argv[8 : 8 + len(frozen)] == frozen
    target = Path(argv[-1])

    # 暫存命名：同目錄、精確樣式、.wav 結尾
    assert target.parent == audio_path.parent
    assert apple.STALE_TEMP_NAME_PATTERN.match(target.name)
    assert target.suffix == ".wav"

    # 大寫容器仍被視為 MP3（provider 會先 lower）
    assert result.metadata["conversion_reason"] == "fragile_native_container"
    assert result.metadata["conversion_seconds"] is not None

    # 正常結束不留殘留
    assert sorted(os.listdir(tmp_path)) == [audio_path.name]


def test_transcribe_non_native_container_converts(tmp_path, stub_cli):
    _, result = _transcribe(tmp_path, stub_cli, name="recording.webm")

    assert len(stub_cli.conversion_calls) == 1
    assert result.metadata["conversion_reason"] == "non_native_container"
    assert Path(stub_cli.build_transcribe_kwargs["input_path"]).suffix == ".wav"


def test_transcribe_native_container_skips_conversion(tmp_path, stub_cli):
    _, result = _transcribe(tmp_path, stub_cli, name="meeting.m4a")

    assert stub_cli.conversion_calls == []
    assert result.metadata["conversion_reason"] is None
    assert result.metadata["conversion_seconds"] is None
    assert stub_cli.build_transcribe_kwargs["input_path"] == str(tmp_path / "meeting.m4a")


def test_transcribe_preflight_disabled_skips_mp3_conversion_but_not_foreign_containers(tmp_path, stub_cli):
    _, result = _transcribe(tmp_path, stub_cli, name="meeting.mp3", enable_preflight=False)

    assert stub_cli.conversion_calls == []
    assert result.metadata["conversion_reason"] is None

    stub_cli.conversion_calls.clear()
    _, foreign = _transcribe(tmp_path, stub_cli, name="meeting.webm", enable_preflight=False)
    assert len(stub_cli.conversion_calls) == 1
    assert foreign.metadata["conversion_reason"] == "non_native_container"


def test_conversion_failure_retries_once_then_raises(tmp_path, stub_cli):
    stub_cli.conversion_result_factory = lambda argv, index: _helper_result(returncode=1, stderr="boom")

    with pytest.raises(AppleSpeechError) as excinfo:
        _transcribe(tmp_path, stub_cli)

    assert excinfo.value.code == APPLE_INPUT_ERROR
    assert len(stub_cli.conversion_calls) == 2
    assert stub_cli.helper_calls == []
    assert sorted(os.listdir(tmp_path)) == ["meeting.mp3"]


def test_conversion_cancel_is_not_retried(tmp_path, stub_cli):
    stub_cli.conversion_result_factory = lambda argv, index: _helper_result(returncode=None, cancelled=True)

    with pytest.raises(AppleSpeechError) as excinfo:
        _transcribe(tmp_path, stub_cli)

    assert excinfo.value.code == APPLE_CANCELLED
    assert len(stub_cli.conversion_calls) == 1
    assert sorted(os.listdir(tmp_path)) == ["meeting.mp3"]


# ---------------------------------------------------------------------------
# 逾時與 helper 錯誤（SI-05／SI-06）
# ---------------------------------------------------------------------------


def test_ffprobe_failure_uses_600_second_floor(tmp_path, stub_cli, monkeypatch):
    monkeypatch.setattr(apple, "_measure_duration_seconds", lambda path: None)

    _transcribe(tmp_path, stub_cli)

    assert stub_cli.build_transcribe_kwargs["timeout_seconds"] == 600.0
    assert stub_cli.helper_calls[0]["timeout_seconds"] == 600.0
    assert stub_cli.conversion_timeouts() == [600.0]


def test_duration_drives_timeout_formula(tmp_path, stub_cli, monkeypatch):
    monkeypatch.setattr(apple, "_measure_duration_seconds", lambda path: 3600.0)

    _transcribe(tmp_path, stub_cli)

    assert stub_cli.build_transcribe_kwargs["timeout_seconds"] == pytest.approx(11100.0)


def test_helper_exit_code_becomes_apple_error(tmp_path, stub_cli):
    stub_cli.helper_result_factory = lambda: _helper_result(returncode=4)

    with pytest.raises(AppleSpeechError) as excinfo:
        _transcribe(tmp_path, stub_cli)

    assert excinfo.value.code == APPLE_ASSET_ERROR


def test_helper_timeout_becomes_apple_timeout(tmp_path, stub_cli):
    stub_cli.helper_result_factory = lambda: _helper_result(returncode=None, timed_out=True)

    with pytest.raises(AppleSpeechError) as excinfo:
        _transcribe(tmp_path, stub_cli)

    assert excinfo.value.code == APPLE_TIMEOUT


def test_probe_failure_fails_engine_before_transcribe(tmp_path, stub_cli):
    stub_cli.probe_error = AppleSpeechError(APPLE_UNAVAILABLE, "helper 不存在")

    with pytest.raises(AppleSpeechError) as excinfo:
        _transcribe(tmp_path, stub_cli)

    assert excinfo.value.code == APPLE_UNAVAILABLE
    assert stub_cli.helper_calls == []
    assert len(stub_cli.probe_calls) == 1


# ---------------------------------------------------------------------------
# 成功路徑：正常化、metadata、進度
# ---------------------------------------------------------------------------


def test_success_payload_is_normalized_and_metadata_complete(tmp_path, stub_cli):
    stub_cli.payload = _payload(
        text="今天天氣很好 ，我們一起去公園散步",
        segments=(
            SimpleNamespace(start=0.0, end=1.5, text="今天天氣很好 ，"),
            SimpleNamespace(start=1.5, end=3.0, text="我們一起去公園散步"),
        ),
        metadata={"audio_duration_seconds": 12.0},
        dropped=2,
        degraded=1,
    )

    _, result = _transcribe(tmp_path, stub_cli)

    assert result.text == "今天天氣很好，我們一起去公園散步"
    assert [segment.text for segment in result.segments] == ["今天天氣很好，", "我們一起去公園散步"]
    assert result.language == "zh-Hant-TW"

    assert set(result.metadata) == EXPECTED_METADATA_KEYS
    assert all(isinstance(value, _SCALAR_TYPES) for value in result.metadata.values())
    assert result.metadata["requested_engine"] == "apple"
    assert result.metadata["resolved_engine"] == "apple"
    assert result.metadata["engine_chain"] == "apple"
    assert result.metadata["helper_invocations"] == 1
    assert result.metadata["segment_count"] == 2
    assert result.metadata["segments_dropped"] == 2
    assert result.metadata["segments_time_degraded"] == 1
    assert result.metadata["audio_duration_seconds"] == 12.0
    assert result.metadata["real_time_factor"] is not None
    assert result.duration_seconds == 12.0
    assert len(stub_cli.helper_calls) == 1


def test_helper_progress_lines_are_relayed_as_percent_and_message(tmp_path, stub_cli, monkeypatch):
    monkeypatch.setattr(
        apple_cli,
        "parse_progress_line",
        lambda line: (0.5, "Apple 語音辨識：分析中…") if "progress" in line else None,
    )
    stub_cli.helper_events = [("apple-speech-cli:progress {}",), (0.25, "Apple 語音辨識：分析中…")]
    progress = []

    _transcribe(tmp_path, stub_cli, progress_callback=lambda percent, message: progress.append((percent, message)))

    percentages = [percent for percent, _ in progress]
    assert percentages == sorted(percentages)
    assert any("分析中" in message for _, message in progress)


def test_empty_segments_stay_out_of_result(tmp_path, stub_cli):
    stub_cli.payload = _payload(
        segments=(
            SimpleNamespace(start=0.0, end=1.0, text="保留"),
            SimpleNamespace(start=1.0, end=2.0, text="   "),
        ),
    )

    _, result = _transcribe(tmp_path, stub_cli)

    assert [segment.text for segment in result.segments] == ["保留"]


def test_unexpected_segment_payload_is_typed_error(tmp_path, stub_cli):
    stub_cli.helper_result_factory = lambda: _helper_result(returncode=0, stdout="{not json")

    def explode(raw_stdout):
        raise AppleSpeechError(APPLE_OUTPUT_INVALID, "Apple 命令列工具輸出無法解析。")

    monkeypatch_validate = pytest.MonkeyPatch()
    monkeypatch_validate.setattr(apple_cli, "validate_transcription_payload", explode)
    try:
        with pytest.raises(AppleSpeechError) as excinfo:
            _transcribe(tmp_path, stub_cli)
    finally:
        monkeypatch_validate.undo()

    assert excinfo.value.code == APPLE_OUTPUT_INVALID


# ---------------------------------------------------------------------------
# 暫存清掃（SI-08）
# ---------------------------------------------------------------------------


def test_sweep_only_removes_old_exact_pattern_files(tmp_path):
    old = time.time() - (25 * 60 * 60)
    fresh = time.time()

    stale_temp = tmp_path / ".meeting.0123456789ab.apple.wav"
    stale_temp.write_bytes(b"stale")
    os.utime(stale_temp, (old, old))

    fresh_temp = tmp_path / ".meeting.fedcba987654.apple.wav"
    fresh_temp.write_bytes(b"fresh")
    os.utime(fresh_temp, (fresh, fresh))

    # 注意：macOS 預設檔案系統大小寫不敏感，keeper 不可用「只差大小寫」的檔名，
    # 否則會與 stale_temp 指到同一個檔案；大寫 hex 的拒絕改以純正則斷言驗證。
    keepers = [
        "user-audio.wav",
        ".meeting.0123456789ab.apple.mp3",  # 副檔名不符
        ".meeting.FEEDFACEBEEF.apple.wav",  # 非小寫 hex
        ".meeting.0123456789a.apple.wav",  # hex 長度不符
        ".meeting.0123456789ab.apple.wav.bak",
    ]
    for name in keepers:
        path = tmp_path / name
        path.write_bytes(b"keep")
        os.utime(path, (old, old))

    stale_dir = tmp_path / ".meeting.0123456789ab.apple.wav.d"
    stale_dir.mkdir()
    os.utime(stale_dir, (old, old))

    nested = tmp_path / "nested"
    nested.mkdir()
    nested_temp = nested / ".meeting.0123456789ab.apple.wav"
    nested_temp.write_bytes(b"nested")
    os.utime(nested_temp, (old, old))

    symlink_target = tmp_path / "symlink-target.bin"
    symlink_target.write_bytes(b"target")
    os.utime(symlink_target, (old, old))
    symlink = tmp_path / ".meeting.abcdefabcdef.apple.wav"
    os.symlink(symlink_target, symlink)

    assert apple.STALE_TEMP_NAME_PATTERN.match(".meeting.0123456789AB.apple.wav") is None

    removed = apple.sweep_stale_apple_temp_files(tmp_path)

    assert removed == 1
    assert not stale_temp.exists()
    assert fresh_temp.exists()
    assert symlink.is_symlink()
    assert symlink_target.exists()
    assert nested_temp.exists()
    assert stale_dir.is_dir()
    for name in keepers:
        assert (tmp_path / name).exists()


def test_sweep_respects_custom_max_age(tmp_path):
    old = time.time() - 120
    path = tmp_path / ".meeting.0123456789ab.apple.wav"
    path.write_bytes(b"x")
    os.utime(path, (old, old))

    assert apple.sweep_stale_apple_temp_files(tmp_path, max_age_seconds=60) == 1


def test_sweep_missing_directory_is_noop(tmp_path):
    assert apple.sweep_stale_apple_temp_files(tmp_path / "nope") == 0


# ---------------------------------------------------------------------------
# 健康狀態（SI-12／REQ-10）
# ---------------------------------------------------------------------------


def test_apple_helper_status_non_darwin_has_zero_side_effects(monkeypatch):
    monkeypatch.setattr(apple, "_current_platform", lambda: "Windows")

    def forbidden(*args, **kwargs):
        raise AssertionError("非 macOS 不得探索 helper 或啟動子程序")

    monkeypatch.setattr(apple_cli, "resolve_executable", forbidden)
    monkeypatch.setattr(apple_cli, "probe_executable", forbidden)
    monkeypatch.setattr(apple.shutil, "which", forbidden)

    status = apple.apple_helper_status()

    assert status == {
        "supported": False,
        "available": False,
        "path": None,
        "probe": None,
        "reason": "non_darwin",
    }


def test_apple_helper_status_macos_reports_probe(monkeypatch):
    monkeypatch.setattr(apple, "_current_platform", lambda: "Darwin")
    monkeypatch.setattr(apple_cli, "resolve_executable", lambda configured=None, **kwargs: FAKE_HELPER)
    monkeypatch.setattr(
        apple_cli,
        "probe_executable",
        lambda executable, **kwargs: {"locale_supported": True, "asset_status": "installed"},
    )

    status = apple.apple_helper_status(configured_path="/configured/helper")

    assert status["supported"] is True
    assert status["available"] is True
    assert status["path"] == FAKE_HELPER
    assert status["probe"] == {"locale_supported": True, "asset_status": "installed"}
    assert status["reason"] is None


def test_apple_helper_status_reports_missing_helper(monkeypatch):
    monkeypatch.setattr(apple, "_current_platform", lambda: "Darwin")

    def missing(configured=None, **kwargs):
        raise AppleSpeechError(APPLE_UNAVAILABLE, "找不到 apple-speech-cli")

    monkeypatch.setattr(apple_cli, "resolve_executable", missing)

    status = apple.apple_helper_status()

    assert status["supported"] is True
    assert status["available"] is False
    assert status["path"] is None
    assert status["reason"] == APPLE_UNAVAILABLE


def test_apple_helper_status_reports_probe_failure(monkeypatch):
    monkeypatch.setattr(apple, "_current_platform", lambda: "Darwin")
    monkeypatch.setattr(apple_cli, "resolve_executable", lambda configured=None, **kwargs: FAKE_HELPER)

    def failing_probe(executable, **kwargs):
        raise AppleSpeechError(APPLE_ASSET_ERROR, "asset 不可用")

    monkeypatch.setattr(apple_cli, "probe_executable", failing_probe)

    status = apple.apple_helper_status()

    assert status["available"] is False
    assert status["path"] == FAKE_HELPER
    assert status["probe"] is None
    assert status["reason"] == APPLE_ASSET_ERROR
