#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Apple helper 執行邊界測試（WAVE-03a；對應 plan CHECK-06 與 CHECK-08）。

所有子行程測試都用 fake helper（python script），不呼叫真的 Swift
``apple-speech-cli``。逾時／取消／kill 路徑另外檢查子行程已被回收（POSIX 限定）。
"""

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ["DATA_DIR"] = tempfile.mkdtemp()

from backend.services.asr_apple import apple_cli  # noqa: E402
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
    ASRSegment,
)

POSIX_ONLY = pytest.mark.skipif(
    os.name != "posix", reason="需要 POSIX 的訊號、exec bit 與 pid 語意"
)

#: fake helper：完全由環境變數驅動，用來模擬 helper 的各種行為。
FAKE_HELPER_SOURCE = '''\
"""Fake apple-speech-cli（測試用；不是真的 Swift helper）。"""
import os
import signal
import sys
import time


def _emit(stream, payload):
    stream.write(payload)
    stream.flush()


pid_file = os.environ.get("FAKE_PID_FILE")
if pid_file:
    with open(pid_file, "w", encoding="utf-8") as handle:
        handle.write(str(os.getpid()))

if os.environ.get("FAKE_IGNORE_SIGTERM"):
    signal.signal(signal.SIGTERM, signal.SIG_IGN)

sleep_seconds = os.environ.get("FAKE_SLEEP_SECONDS")
if sleep_seconds:
    time.sleep(float(sleep_seconds))

repeat_count = int(os.environ.get("FAKE_STDOUT_REPEAT_COUNT", "") or "0")
if repeat_count > 0:
    remaining = repeat_count
    while remaining > 0:
        piece = "x" * min(remaining, 4096)
        _emit(sys.stdout, piece)
        remaining -= len(piece)
else:
    _emit(sys.stdout, os.environ.get("FAKE_STDOUT", ""))

_emit(sys.stderr, os.environ.get("FAKE_STDERR", ""))
sys.exit(int(os.environ.get("FAKE_EXIT_CODE", "0")))
'''


@pytest.fixture
def fake_helper(tmp_path):
    """可直接用 ``sys.executable`` 啟動的 fake helper 路徑。"""

    script = tmp_path / "fake_apple_cli.py"
    script.write_text(FAKE_HELPER_SOURCE, encoding="utf-8")
    return script


@pytest.fixture
def fake_helper_executable(tmp_path):
    """帶 shebang 且可執行的 fake helper（供接受單一 executable 字串的 API）。"""

    script = tmp_path / "fake-apple-speech-cli"
    script.write_text("#!/usr/bin/env python3\n" + FAKE_HELPER_SOURCE, encoding="utf-8")
    script.chmod(0o755)
    return str(script)


def _helper_argv(script: Path, *extra: str) -> list[str]:
    return [sys.executable, str(script), *extra]


def _pid_alive(pid: int) -> bool:
    """子行程是否仍存在（殭屍也算存在，因此這同時驗證已被回收）。"""

    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _wait_for_pid_file(path: Path, timeout: float = 5.0) -> int:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            return int(path.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            time.sleep(0.02)
    raise AssertionError("fake helper 沒有寫出 pid 檔")


def _valid_payload(**overrides):
    payload = {
        "schema_version": "1.0",
        "engine": "apple",
        "locale": "zh-Hant-TW",
        "text": "今天天氣很好，我們一起去公園散步",
        "segments": [
            {"start": 0.0, "end": 1.25, "text": "今天天氣很好，我們一起去公園散步"},
        ],
        "metadata": {"audio_duration_seconds": 1.25, "segment_count": 1},
    }
    payload.update(overrides)
    return payload


# --------------------------------------------------------------------------
# CHECK-06：超時公式
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("duration", "expected"),
    [
        (None, 600.0),
        (0, 600.0),
        (-5, 600.0),
        (600, 2100.0),
        (3600, 11100.0),
    ],
)
def test_resolved_timeout_seconds_matrix(duration, expected):
    assert apple_cli.resolved_timeout_seconds(duration) == expected
    assert apple_cli.DEFAULT_TIMEOUT_FLOOR_SECONDS == 600.0


def test_resolved_timeout_seconds_never_fails_on_garbage():
    """ffprobe 失敗（None／非有限值）一律用下限，不得因此失敗。"""

    assert apple_cli.resolved_timeout_seconds(None) == 600.0
    assert apple_cli.resolved_timeout_seconds(float("nan")) == 600.0
    assert apple_cli.resolved_timeout_seconds(float("inf")) == 600.0


# --------------------------------------------------------------------------
# runner：逾時、取消、kill、回收
# --------------------------------------------------------------------------


@POSIX_ONLY
def test_run_helper_times_out_and_reaps_child(fake_helper, tmp_path, monkeypatch):
    pid_file = tmp_path / "pid"
    monkeypatch.setenv("FAKE_PID_FILE", str(pid_file))
    monkeypatch.setenv("FAKE_SLEEP_SECONDS", "30")
    monkeypatch.setenv("FAKE_STDOUT", "太慢的輸出")
    monkeypatch.setenv("FAKE_STDERR", "diagnostics")

    started = time.monotonic()
    result = apple_cli.run_helper(_helper_argv(fake_helper, "transcribe"), timeout_seconds=0.4)
    elapsed = time.monotonic() - started

    assert result.timed_out is True
    assert result.cancelled is False
    assert result.returncode is not None
    assert elapsed < 10.0
    assert _pid_alive(_wait_for_pid_file(pid_file)) is False


@POSIX_ONLY
def test_run_helper_cancel_event_beats_timeout_and_reaps_child(fake_helper, tmp_path, monkeypatch):
    pid_file = tmp_path / "pid"
    monkeypatch.setenv("FAKE_PID_FILE", str(pid_file))
    monkeypatch.setenv("FAKE_SLEEP_SECONDS", "30")

    cancel_event = threading.Event()
    timer = threading.Timer(0.2, cancel_event.set)
    timer.start()
    try:
        result = apple_cli.run_helper(
            _helper_argv(fake_helper, "transcribe"),
            timeout_seconds=30.0,
            cancel_event=cancel_event,
        )
    finally:
        timer.cancel()

    assert result.cancelled is True
    assert result.timed_out is False
    assert _pid_alive(_wait_for_pid_file(pid_file)) is False


@POSIX_ONLY
def test_run_helper_cancel_wins_when_event_is_already_set(fake_helper, tmp_path, monkeypatch):
    """取消優先於逾時：事件已 set＋逾時已到期仍必須回報 cancelled。

    事件在 spawn 前就已 set，因此 helper 可能來不及寫出 pid 檔就被回收；此處以
    ``returncode is not None``（``wait()`` 已完成，即子行程已被 OS 回收）驗證不殘留。
    """

    monkeypatch.setenv("FAKE_SLEEP_SECONDS", "30")

    cancel_event = threading.Event()
    cancel_event.set()
    result = apple_cli.run_helper(
        _helper_argv(fake_helper, "transcribe"),
        timeout_seconds=0.05,
        cancel_event=cancel_event,
    )

    assert result.cancelled is True
    assert result.timed_out is False
    assert result.returncode is not None


@POSIX_ONLY
def test_run_helper_kills_child_that_ignores_sigterm(fake_helper, tmp_path, monkeypatch):
    """terminate 無效時走 kill；寬限秒數以 mock 縮短，避免測試空等 5 秒。"""

    pid_file = tmp_path / "pid"
    monkeypatch.setattr(apple_cli, "TERMINATE_GRACE_SECONDS", 0.2)
    monkeypatch.setenv("FAKE_PID_FILE", str(pid_file))
    monkeypatch.setenv("FAKE_IGNORE_SIGTERM", "1")
    monkeypatch.setenv("FAKE_SLEEP_SECONDS", "30")
    assert apple_cli.TERMINATE_GRACE_SECONDS == 0.2

    started = time.monotonic()
    result = apple_cli.run_helper(_helper_argv(fake_helper, "transcribe"), timeout_seconds=0.3)
    elapsed = time.monotonic() - started

    assert result.timed_out is True
    assert result.cancelled is False
    assert elapsed < 10.0
    assert _pid_alive(_wait_for_pid_file(pid_file)) is False


def test_terminate_grace_seconds_default_is_frozen():
    assert apple_cli.TERMINATE_GRACE_SECONDS == 5.0


def test_run_helper_spawn_failure_maps_to_unavailable(tmp_path):
    missing = tmp_path / "does-not-exist" / "apple-speech-cli"
    with pytest.raises(AppleSpeechError) as excinfo:
        apple_cli.run_helper([str(missing)], timeout_seconds=1.0)
    assert excinfo.value.code == APPLE_UNAVAILABLE
    assert excinfo.value.context["stage"] == "helper_spawn"


def test_run_helper_requires_numeric_timeout(fake_helper):
    with pytest.raises(ValueError):
        apple_cli.run_helper(_helper_argv(fake_helper), timeout_seconds=None)


# --------------------------------------------------------------------------
# runner：進度回報與輸出上限
# --------------------------------------------------------------------------


def test_run_helper_reports_progress_lines_from_stderr(fake_helper, monkeypatch):
    monkeypatch.setenv(
        "FAKE_STDERR",
        "apple-speech-cli:progress "
        '{"phase":"asset_install","status":"progress","fractionCompleted":0.42}\n'
        "一般診斷行\n",
    )

    updates: list[tuple[float, str]] = []
    result = apple_cli.run_helper(
        _helper_argv(fake_helper),
        timeout_seconds=10.0,
        on_progress=lambda fraction, message: updates.append((fraction, message)),
    )

    assert result.returncode == 0
    assert updates == [(0.42, "Apple 語音模型安裝中…")]


def test_run_helper_reports_progress_lines_from_stdout(fake_helper, monkeypatch):
    """凍結介面要求 stdout 行也經 parse_progress_line；helper 變體可能如此。"""

    monkeypatch.setenv(
        "FAKE_STDOUT",
        'apple-speech-cli:progress {"phase":"analysis","status":"started","percent":25}\n',
    )

    updates: list[tuple[float, str]] = []
    apple_cli.run_helper(
        _helper_argv(fake_helper),
        timeout_seconds=10.0,
        on_progress=lambda fraction, message: updates.append((fraction, message)),
    )

    assert updates == [(0.25, "Apple 語音辨識：analysis 開始…")]


def test_run_helper_progress_callback_exception_does_not_break_run(fake_helper, monkeypatch):
    monkeypatch.setenv(
        "FAKE_STDERR",
        'apple-speech-cli:progress {"phase":"analysis","status":"progress","fractionCompleted":0.5}\n',
    )

    def boom(fraction, message):
        raise RuntimeError("callback 壞掉不得影響辨識")

    result = apple_cli.run_helper(
        _helper_argv(fake_helper), timeout_seconds=10.0, on_progress=boom
    )

    assert result.returncode == 0
    assert result.timed_out is False


def test_stdout_capture_limit_is_frozen():
    assert apple_cli.STDOUT_CAPTURE_LIMIT == 8_000_000


def test_run_helper_truncates_stdout_at_capture_limit(fake_helper, monkeypatch):
    """超過上限只截斷、行程照常讀完；被截斷的 stdout 之後驗證必為 OUTPUT_INVALID。"""

    monkeypatch.setattr(apple_cli, "STDOUT_CAPTURE_LIMIT", 1_000)
    monkeypatch.setenv("FAKE_STDOUT_REPEAT_COUNT", "5000")

    result = apple_cli.run_helper(_helper_argv(fake_helper), timeout_seconds=10.0)

    assert result.returncode == 0
    assert result.timed_out is False
    assert len(result.stdout) == 1_000
    assert result.stdout == "x" * 1_000

    with pytest.raises(AppleSpeechError) as excinfo:
        apple_cli.validate_transcription_payload(result.stdout)
    assert excinfo.value.code == APPLE_OUTPUT_INVALID


# --------------------------------------------------------------------------
# CHECK-08：stdout 污染與嚴格 payload 驗證
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "stdout",
    [
        "",
        "   ",
        "not json at all",
        '{"schema_version": "1.0"}{"schema_version": "1.0"}',
        'noise line\n{"schema_version": "1.0", "engine": "apple"}',
        '{"schema_version": "1.0", "engine": "apple"}\ntrailing noise',
        '[{"schema_version": "1.0", "engine": "apple"}]',
    ],
)
def test_validate_transcription_payload_rejects_stdout_pollution(stdout):
    with pytest.raises(AppleSpeechError) as excinfo:
        apple_cli.validate_transcription_payload(stdout)
    assert excinfo.value.code == APPLE_OUTPUT_INVALID


@pytest.mark.parametrize(
    "payload",
    [
        _valid_payload(schema_version="2.0"),
        _valid_payload(engine="whisper"),
        {k: v for k, v in _valid_payload().items() if k != "schema_version"},
        {k: v for k, v in _valid_payload().items() if k != "engine"},
        {k: v for k, v in _valid_payload().items() if k != "text"},
        _valid_payload(text=123),
        _valid_payload(text="   "),
        {k: v for k, v in _valid_payload().items() if k != "segments"},
        _valid_payload(segments={"start": 0.0}),
        {k: v for k, v in _valid_payload().items() if k != "metadata"},
        _valid_payload(metadata=["not", "a", "mapping"]),
        _valid_payload(segments=[{"start": 0.0, "end": 1.0}]),
        _valid_payload(segments=[{"start": 0.0, "end": 1.0, "text": 5}]),
        _valid_payload(segments=[{"start": True, "end": 1.0, "text": "hi"}]),
        _valid_payload(segments=[{"start": "0", "end": 1.0, "text": "hi"}]),
        _valid_payload(segments=[{"start": 0.0, "end": float("inf"), "text": "hi"}]),
        _valid_payload(segments=["not an object"]),
    ],
)
def test_validate_transcription_payload_rejects_invalid_documents(payload):
    with pytest.raises(AppleSpeechError) as excinfo:
        apple_cli.validate_transcription_payload(json.dumps(payload))
    assert excinfo.value.code == APPLE_OUTPUT_INVALID


def test_validate_transcription_payload_accepts_valid_payload():
    payload = _valid_payload(
        locale="zh-Hant-TW",
        text="今天天氣很好 ，我們一起去公園散步",
        metadata={"audio_duration_seconds": 1.25, "nested": {"x": 1}, "ratio": float("nan")},
    )

    decoded = apple_cli.validate_transcription_payload(json.dumps(payload, ensure_ascii=False))

    assert isinstance(decoded, apple_cli.ApplePayload)
    assert decoded.text == "今天天氣很好，我們一起去公園散步"
    assert decoded.locale == "zh-Hant-TW"
    assert decoded.segments_dropped == 0
    assert decoded.segments_time_degraded == 0
    assert len(decoded.segments) == 1
    segment = decoded.segments[0]
    assert isinstance(segment, ASRSegment)
    assert (segment.start, segment.end) == (0.0, 1.25)
    assert segment.text == "今天天氣很好，我們一起去公園散步"
    # metadata 只留扁平 scalar（容器與非有限值直接丟棄）。
    assert decoded.metadata == {"audio_duration_seconds": 1.25}


def test_validate_transcription_payload_degrades_inverted_segment_time():
    payload = _valid_payload(
        segments=[
            {"start": 5.0, "end": 2.0, "text": "時間倒反"},
            {"start": None, "end": None, "text": "沒有時間"},
            {"start": 1.0, "end": 2.0, "text": "正常"},
        ]
    )

    decoded = apple_cli.validate_transcription_payload(json.dumps(payload, ensure_ascii=False))

    assert decoded.segments_time_degraded == 1
    assert decoded.segments_dropped == 0
    assert [segment.text for segment in decoded.segments] == ["時間倒反", "沒有時間", "正常"]
    assert decoded.segments[0].start == 5.0
    assert decoded.segments[0].end is None
    assert decoded.segments[1].start is None
    assert decoded.segments[1].end is None


def test_validate_transcription_payload_drops_blank_segments_and_normalizes_text():
    payload = _valid_payload(
        segments=[
            {"start": 0.0, "end": 1.0, "text": "   "},
            {"start": 1.0, "end": 2.0, "text": "\u3000"},
            {"start": 2.0, "end": 3.0, "text": "  第二段 ，含全形標點。"},
        ]
    )

    decoded = apple_cli.validate_transcription_payload(json.dumps(payload, ensure_ascii=False))

    assert decoded.segments_dropped == 2
    assert len(decoded.segments) == 1
    assert decoded.segments[0].text == "第二段，含全形標點。"


# --------------------------------------------------------------------------
# 執行檔探索（DEC-04）
# --------------------------------------------------------------------------


@POSIX_ONLY
def test_resolve_executable_prefers_configured(tmp_path):
    configured = tmp_path / "custom-helper"
    configured.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    configured.chmod(0o755)

    resolved = apple_cli.resolve_executable(
        str(configured), repo_root=tmp_path, which=lambda name: None
    )

    assert resolved == str(configured)


@POSIX_ONLY
def test_resolve_executable_falls_back_to_repo_release_artifact(tmp_path):
    packaged = tmp_path / "apple_speech_cli" / ".build" / "release" / "apple-speech-cli"
    packaged.parent.mkdir(parents=True)
    packaged.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    packaged.chmod(0o755)

    resolved = apple_cli.resolve_executable(
        str(tmp_path / "missing-helper"),
        repo_root=tmp_path,
        which=lambda name: "/from/path/apple-speech-cli",
    )

    assert resolved == str(packaged)


@POSIX_ONLY
def test_resolve_executable_falls_back_to_path(tmp_path):
    resolved = apple_cli.resolve_executable(
        str(tmp_path / "missing-helper"),
        repo_root=tmp_path,
        which=lambda name: "/usr/local/bin/apple-speech-cli" if name == "apple-speech-cli" else None,
    )

    assert resolved == "/usr/local/bin/apple-speech-cli"


@POSIX_ONLY
def test_resolve_executable_missing_everywhere_raises_with_build_command(tmp_path):
    with pytest.raises(AppleSpeechError) as excinfo:
        apple_cli.resolve_executable(
            str(tmp_path / "missing-helper"), repo_root=tmp_path, which=lambda name: None
        )

    error = excinfo.value
    assert error.code == APPLE_UNAVAILABLE
    assert "swift build -c release" in error.user_message
    assert "已改找預設位置" in error.user_message
    assert error.context["stage"] == "helper_resolve"


# --------------------------------------------------------------------------
# 離場碼與錯誤分類（SI-05）
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("returncode", "expected"),
    [
        (2, APPLE_UNAVAILABLE),
        (3, APPLE_LOCALE_UNSUPPORTED),
        (4, APPLE_ASSET_ERROR),
        (5, APPLE_INPUT_ERROR),
        (6, APPLE_TRANSCRIPTION_ERROR),
        (7, APPLE_CANCELLED),
    ],
)
def test_error_from_helper_result_maps_exit_codes(returncode, expected):
    result = apple_cli.HelperResult(returncode=returncode, stdout="", stderr="boom\nmore")

    error = apple_cli.error_from_helper_result(result, stage="helper_transcribe")

    assert error.code == expected
    assert error.context["stage"] == "helper_transcribe"
    assert error.context["helper_exit_code"] == str(returncode)
    assert error.context["helper_stderr_tail"] == "boom | more"


def test_error_from_helper_result_uses_payload_error_code_for_exit_one():
    stdout = json.dumps(
        {
            "schema_version": "1.0",
            "engine": "apple",
            "error": {"code": APPLE_TIMEOUT, "message": "analysis budget exceeded"},
        }
    )
    result = apple_cli.HelperResult(returncode=1, stdout=stdout)

    error = apple_cli.error_from_helper_result(result, stage="helper_transcribe")

    assert error.code == APPLE_TIMEOUT
    assert "逾時" in error.user_message
    assert "budget" not in error.user_message  # 只有穩定訊息，不回顯任意 helper 文字


@pytest.mark.parametrize(
    "stdout",
    [
        "",
        "not json",
        json.dumps({"error": {"code": "NOT_A_REAL_CODE"}}),
    ],
)
def test_error_from_helper_result_exit_one_without_valid_code_is_output_invalid(stdout):
    result = apple_cli.HelperResult(returncode=1, stdout=stdout)
    error = apple_cli.error_from_helper_result(result, stage="helper_transcribe")
    assert error.code == APPLE_OUTPUT_INVALID


def test_error_from_helper_result_timeout_and_cancel_flags():
    timed_out = apple_cli.HelperResult(returncode=None, timed_out=True)
    assert apple_cli.error_from_helper_result(timed_out, stage="helper_transcribe").code == APPLE_TIMEOUT

    result = apple_cli.HelperResult(returncode=None, timed_out=True, cancelled=True)
    assert apple_cli.error_from_helper_result(result, stage="helper_transcribe").code == APPLE_CANCELLED


def test_error_from_helper_result_signal_without_json_is_unavailable():
    killed = apple_cli.HelperResult(returncode=-9, stdout="", stderr="")
    assert apple_cli.error_from_helper_result(killed, stage="helper_transcribe").code == APPLE_UNAVAILABLE


def test_error_from_helper_result_context_is_bounded_and_transcript_free():
    secret = "這是逐字稿內容" * 200
    result = apple_cli.HelperResult(
        returncode=6,
        stdout=json.dumps({"text": secret}),
        stderr="line1\nline2\nline3\nline4\n" + secret,
    )

    error = apple_cli.error_from_helper_result(result, stage="helper_transcribe")

    assert error.code == APPLE_TRANSCRIPTION_ERROR
    joined = " ".join(error.context.values())
    assert secret not in joined
    assert all(len(value) <= 300 for value in error.context.values())
    assert error.context["helper_exit_code"] == "6"


# --------------------------------------------------------------------------
# probe
# --------------------------------------------------------------------------


def test_build_argv_shapes():
    probe_argv = apple_cli.build_probe_argv("/bin/apple-speech-cli", locale="zh-Hant-TW")
    assert probe_argv == [
        "/bin/apple-speech-cli",
        "probe",
        "--locale",
        "zh-Hant-TW",
        "--output-format",
        "json",
    ]

    transcribe_argv = apple_cli.build_transcribe_argv(
        "/bin/apple-speech-cli",
        input_path="/tmp/audio.wav",
        locale="zh-Hant-TW",
        preset="time-indexed",
        timeout_seconds=2100.0,
    )
    assert transcribe_argv == [
        "/bin/apple-speech-cli",
        "transcribe",
        "--input",
        "/tmp/audio.wav",
        "--locale",
        "zh-Hant-TW",
        "--output-format",
        "json",
        "--preset",
        "time-indexed",
        "--timeout",
        "2100",
    ]


@POSIX_ONLY
def test_probe_executable_returns_parsed_dict(fake_helper_executable, monkeypatch):
    probe_document = {
        "schema_version": "1.0",
        "engine": "apple",
        "command": "probe",
        "locale_requested": "zh-Hant-TW",
        "locale_supported": True,
        "asset_status": "installed",
        "metadata": {"probe_seconds": 0.1},
    }
    monkeypatch.setenv("FAKE_STDOUT", json.dumps(probe_document))

    payload = apple_cli.probe_executable(
        fake_helper_executable, locale="zh-Hant-TW", timeout_seconds=10.0
    )

    assert payload["locale_supported"] is True
    assert payload["asset_status"] == "installed"


@POSIX_ONLY
def test_probe_executable_rejects_polluted_or_invalid_documents(fake_helper_executable, monkeypatch):
    monkeypatch.setenv("FAKE_STDOUT", '{"schema_version": "1.0"} trailing')
    with pytest.raises(AppleSpeechError) as excinfo:
        apple_cli.probe_executable(fake_helper_executable, locale="zh-Hant-TW", timeout_seconds=10.0)
    assert excinfo.value.code == APPLE_OUTPUT_INVALID

    monkeypatch.setenv(
        "FAKE_STDOUT",
        json.dumps(
            {"schema_version": "1.0", "engine": "apple", "command": "probe", "locale_supported": "yes"}
        ),
    )
    with pytest.raises(AppleSpeechError) as excinfo:
        apple_cli.probe_executable(fake_helper_executable, locale="zh-Hant-TW", timeout_seconds=10.0)
    assert excinfo.value.code == APPLE_OUTPUT_INVALID


@POSIX_ONLY
def test_probe_executable_maps_helper_exit_code(fake_helper_executable, monkeypatch):
    monkeypatch.setenv("FAKE_EXIT_CODE", "2")

    with pytest.raises(AppleSpeechError) as excinfo:
        apple_cli.probe_executable(fake_helper_executable, locale="zh-Hant-TW", timeout_seconds=10.0)

    assert excinfo.value.code == APPLE_UNAVAILABLE
    assert excinfo.value.context["stage"] == "helper_probe"


@POSIX_ONLY
def test_probe_executable_times_out_with_timeout_code(fake_helper_executable, monkeypatch):
    monkeypatch.setenv("FAKE_SLEEP_SECONDS", "30")

    with pytest.raises(AppleSpeechError) as excinfo:
        apple_cli.probe_executable(fake_helper_executable, locale="zh-Hant-TW", timeout_seconds=0.3)

    assert excinfo.value.code == APPLE_TIMEOUT


# --------------------------------------------------------------------------
# CHECK-09：CJK 空白正規化（DEC-08）
# --------------------------------------------------------------------------


def test_normalize_apple_text_example_and_fullwidth_punctuation():
    assert (
        apple_cli.normalize_apple_text("今天天氣很好 ，我們一起去公園散步")
        == "今天天氣很好，我們一起去公園散步"
    )
    assert (
        apple_cli.normalize_apple_text("今天天氣很好 ， 我們一起去公園散步 。 ")
        == "今天天氣很好，我們一起去公園散步。"
    )
    assert apple_cli.normalize_apple_text("  「 你好 」  ") == "「你好」"


def test_normalize_apple_text_keeps_latin_word_spacing():
    assert apple_cli.normalize_apple_text("hello   world") == "hello world"
    assert apple_cli.normalize_apple_text("我們用 Python 寫程式") == "我們用 Python 寫程式"
    assert apple_cli.normalize_apple_text(None) == ""


# --------------------------------------------------------------------------
# 進度行解析
# --------------------------------------------------------------------------


def test_parse_progress_line_accepts_fraction_lines():
    assert apple_cli.parse_progress_line(
        'apple-speech-cli:progress {"phase":"asset_install","status":"progress","fractionCompleted":0.4}'
    ) == (0.4, "Apple 語音模型安裝中…")
    assert apple_cli.parse_progress_line(
        '  apple-speech-cli:progress {"phase":"analysis","status":"progress","percent":75}'
    ) == (0.75, "Apple 語音辨識：analysis 進行中…")
    assert apple_cli.parse_progress_line(
        'apple-speech-cli:progress {"phase":"asset_install","status":"finished","fractionCompleted":1}'
    ) == (1.0, "Apple 語音模型安裝完成")


@pytest.mark.parametrize(
    "line",
    [
        "",
        "plain diagnostic line",
        'apple-speech-cli:progress {"phase":"asset_install","status":"started"}',
        "apple-speech-cli:progress not-json",
        "apple-speech-cli:progress [1, 2, 3]",
        "apple-speech-cli:progress {}",
        "apple-speech-cli:progress " + "x" * 3000,
        'apple-speech-cli:progress {"fractionCompleted": NaN}',
    ],
)
def test_parse_progress_line_rejects_non_progress_lines(line):
    assert apple_cli.parse_progress_line(line) is None


# --------------------------------------------------------------------------
# CHECK-05（延伸）：apple_cli import 純潔
# --------------------------------------------------------------------------


def test_apple_cli_import_stays_lightweight():
    """`import apple_cli` 不得拉入重型 ML 依賴（NFR-03 / SI-11）。"""

    program = (
        "import json, sys\n"
        "import backend.services.asr_apple.apple_cli\n"
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

    payload = json.loads(completed.stdout.strip().splitlines()[-1])
    assert payload == []
