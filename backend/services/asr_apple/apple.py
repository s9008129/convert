#!/usr/bin/env python3
"""Apple SpeechAnalyzer provider（僅 macOS）。

責任範圍（SI-06／SI-07／SI-08、REQ-05/06/09/10）：

- 先 ``probe`` 再 ``transcribe``：探測失敗（helper 缺失、locale／asset 不可用）
  即該引擎失敗，不觸發無謂的模型安裝等待。
- ffmpeg 前處理邊界：非原生容器與 MP3 一律先轉成 16 kHz 單聲道 WAV
  （``CONVERSION_ARGS``）；transcriber 只宣告 16k/8k 單聲道格式，預轉可免去
  framework 內部的重新取樣成本。
- 暫存檔衛生：``.<stem>.<12hex>.apple.wav`` 只在輸入檔同目錄建立，正常結束
  ``finally`` 刪除；行程被硬殺的殘留由 :func:`sweep_stale_apple_temp_files`
  在 24 小時後回收。
- 可觀測 metadata（13 個純量鍵，不含逐字稿）與 Apple 邊界 CJK 空白正規化
  （``normalize_apple_text`` 由 ``apple_cli`` 提供）。

母本為 ``yt_down_txt/media_toolbox/asr/apple.py``，本 repo 契約差異：

- 不建立 VAD、不載入 mlx／torch／silero、不寫 Markdown（逐字稿清理與存檔由
  ``task_processor`` 負責）。
- 逾時公式由 ``apple_cli.resolved_timeout_seconds`` 提供（凍結介面）；本模組
  只把 ffprobe 結果餵進去，ffprobe 失敗視為 ``duration=None``（600s 下限）。
- 不做「native 讀取失敗後才轉檔」的第二次嘗試（母本
  ``RETRYABLE_CONVERSION_ERROR_CODES`` 路徑）：本 repo 一律先轉不賭原生，
  改為轉檔本身失敗時重試一次。
- metadata 只輸出凍結的 13 鍵（母本的 30+ 鍵屬來源專案）。

Import 純潔（NFR-03／SI-11）：模組頂層不得拉入 ``mlx_whisper``／``torch``／
``silero``／``faster_whisper``，也不得在 import 期偵測平台、啟動子程序或寫檔。
"""

from __future__ import annotations

import logging
import os
import platform
import re
import secrets
import shutil
import subprocess
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from . import apple_cli
from .contract import (
    APPLE_CANCELLED,
    APPLE_INPUT_ERROR,
    APPLE_TIMEOUT,
    APPLE_TRANSCRIPTION_ERROR,
    APPLE_UNAVAILABLE,
    ASRSegment,
    AppleSpeechError,
)

LOGGER = logging.getLogger(__name__)

#: 轉檔輸出的容器（凍結，SI-07）。
CONVERSION_SUFFIX = ".wav"

#: 轉檔參數（凍結，SI-07）：16 kHz 單聲道無損 PCM，Apple framework 原生格式。
CONVERSION_ARGS = ("-vn", "-c:a", "pcm_s16le", "-ar", "16000", "-ac", "1")

#: helper（AVAudioFile）可直接讀取的容器；其餘一律先轉檔（SI-07）。
NATIVE_INPUT_SUFFIXES = frozenset({".m4a", ".mp4", ".wav", ".aif", ".aiff", ".caf", ".mp3"})

#: 即使原生可讀也先轉檔的脆弱容器（SI-07）。長 MP3 的原生讀取不可靠，不賭原生。
PREFLIGHT_CONVERSION_SUFFIXES = frozenset({".mp3"})

#: 暫存轉檔檔名樣式（凍結，SI-08）：``.<stem>.<12 位 hex>.apple.<wav|m4a>``。
STALE_TEMP_NAME_PATTERN = re.compile(r"^\..+\.[0-9a-f]{12}\.apple\.(?:wav|m4a)$")

#: 轉檔逾時下限（凍結，SI-06）。
CONVERSION_TIMEOUT_FLOOR_SECONDS = 600.0

#: 未指定 locale 時的預設值（設定層的 ``APPLE_LOCALE`` 優先）。
DEFAULT_LOCALE = "zh-Hant-TW"

#: probe 的預設時間預算（probe 不做推論，只需要寬鬆上限）。
PROBE_TIMEOUT_SECONDS = 60.0

#: 量測音訊長度的 ffprobe 時間上限；逾時視為量不到長度。
FFPROBE_TIMEOUT_SECONDS = 30.0

#: 殘留暫存檔的容忍年齡（SI-08）。
STALE_TEMP_MAX_AGE_SECONDS = 24 * 60 * 60.0

#: 暫存檔名的 stem 長度上限（避免超過檔名長度限制）。
MAX_TEMP_NAME_STEM = 80

#: 建立唯一暫存檔名的最大嘗試次數。
MAX_TEMP_NAME_ATTEMPTS = 8


# ---------------------------------------------------------------------------
# 平台與工具探索（測試可注入的窄縫）
# ---------------------------------------------------------------------------


def _current_platform() -> str:
    """目前平台名稱；非 macOS 一律不得進入 Apple 路徑（DEC-10／SI-12）。"""

    return platform.system()


def apple_platform_supported() -> bool:
    """目前平台是否可能執行 Apple Speech helper（僅 macOS，零子程序）。"""

    return _current_platform() == "Darwin"


def _resolve_ffprobe() -> Optional[str]:
    return shutil.which("ffprobe")


def _resolve_ffmpeg() -> Optional[str]:
    return shutil.which("ffmpeg")


# ---------------------------------------------------------------------------
# 轉檔政策（SI-07）
# ---------------------------------------------------------------------------


def preflight_conversion_reason(input_suffix: str) -> Optional[str]:
    """回傳「必須先轉檔」的原因；``None`` 代表可直接嘗試原生讀取。"""

    if input_suffix not in NATIVE_INPUT_SUFFIXES:
        return "non_native_container"
    if input_suffix in PREFLIGHT_CONVERSION_SUFFIXES:
        return "fragile_native_container"
    return None


def sweep_stale_apple_temp_files(directory: os.PathLike[str] | str, *, max_age_seconds: float = STALE_TEMP_MAX_AGE_SECONDS) -> int:
    """清掉 ``directory`` 中過期的本工具轉檔暫存檔，回傳刪除數量（SI-08）。

    安全條件刻意從嚴，避免任何誤刪：

    * 只比對 ``STALE_TEMP_NAME_PATTERN`` 這個精確樣式；
    * 只處理單層目錄內的一般檔案（不跟隨符號連結、不遞迴）；
    * 只刪超過 ``max_age_seconds`` 的檔案，避開同時在跑的另一個行程；
    * 任何檔案系統錯誤一律靜默略過（清理永遠不得讓轉錄失敗）。
    """

    try:
        entries = list(os.scandir(directory))
    except OSError:
        return 0

    deadline = time.time() - max(0.0, float(max_age_seconds))
    removed = 0
    for entry in entries:
        try:
            if not entry.is_file(follow_symlinks=False):
                continue
            if STALE_TEMP_NAME_PATTERN.match(entry.name) is None:
                continue
            if entry.stat(follow_symlinks=False).st_mtime > deadline:
                continue
            os.unlink(entry.path)
        except OSError:
            continue
        removed += 1
    return removed


# ---------------------------------------------------------------------------
# 數值工具
# ---------------------------------------------------------------------------


def _finite_float(value: object) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


def _positive_float(value: object) -> Optional[float]:
    number = _finite_float(value)
    if number is None or number <= 0:
        return None
    return number


def _non_negative_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return 0
    return value


def _payload_field(payload: object, name: str, default: object = None) -> object:
    """同時支援 dataclass payload 與 mapping payload（凍結介面只保證欄位語意）。"""

    if isinstance(payload, Mapping):
        return payload.get(name, default)
    return getattr(payload, name, default)


# ---------------------------------------------------------------------------
# 進度回報
# ---------------------------------------------------------------------------


class _ProgressRelay:
    """把 provider／helper 進度轉成既有的 ``(percent, message)`` 回呼。

    * 百分比單調不遞減、夾在 0–100；
    * 回呼失敗（型別錯誤或使用者回呼拋錯）永遠不得讓辨識失敗。
    """

    def __init__(self, callback: Optional[Callable[[float, str], None]]) -> None:
        self._callback = callback
        self._last = 0.0

    def emit(self, percent: float, message: str) -> None:
        if self._callback is None:
            return
        try:
            value = float(percent)
        except (TypeError, ValueError):
            return
        value = max(self._last, min(100.0, value))
        self._last = value
        try:
            self._callback(value, message)
        except Exception:  # noqa: BLE001 - 進度回報不得讓辨識失敗
            return

    def helper_event(self, *args: object) -> None:
        """helper 進度事件。

        同時接受兩種形態（凍結介面未逐字規定回呼參數）：``(fraction, message)``
        與原始 stderr 行（交由 ``parse_progress_line`` 解析）。
        """

        fraction: object = None
        message: object = None
        if len(args) >= 2:
            fraction, message = args[0], args[1]
        elif len(args) == 1:
            parsed = apple_cli.parse_progress_line(str(args[0]))
            if parsed is None:
                return
            fraction, message = parsed
        else:
            return

        if isinstance(fraction, bool) or not isinstance(fraction, (int, float)):
            return
        clamped = min(1.0, max(0.0, float(fraction)))
        self.emit(20.0 + clamped * 35.0, str(message or ""))


# ---------------------------------------------------------------------------
# 結果型別（凍結介面）
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AppleTranscriptionResult:
    """一次成功的 Apple SpeechAnalyzer 轉錄。"""

    text: str
    segments: tuple[ASRSegment, ...]
    metadata: dict[str, object]
    duration_seconds: float
    language: str


# ---------------------------------------------------------------------------
# 音訊前處理
# ---------------------------------------------------------------------------


def _measure_duration_seconds(audio_path: str) -> Optional[float]:
    """以 bounded ffprobe 取得音訊長度；任何失敗都回 ``None``（SI-06）。"""

    executable = _resolve_ffprobe()
    if not executable:
        LOGGER.info("找不到 ffprobe，Apple 轉錄逾時改用 600 秒下限")
        return None

    argv = [
        executable,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        audio_path,
    ]
    try:
        completed = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=FFPROBE_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if completed.returncode != 0:
        return None
    try:
        value = float(str(completed.stdout or "").strip())
    except ValueError:
        return None
    return _positive_float(value)


def _conversion_timeout_seconds(duration_seconds: Optional[float]) -> float:
    """轉檔逾時：與 helper 同一條 duration-aware 預算，且不低於凍結下限（SI-06）。"""

    return max(CONVERSION_TIMEOUT_FLOOR_SECONDS, apple_cli.resolved_timeout_seconds(duration_seconds))


def _temp_target(source: Path) -> Path:
    """在輸入檔同目錄建立唯一的轉檔暫存檔名（SI-08）。"""

    directory = source.parent
    sweep_stale_apple_temp_files(directory)
    stem = source.stem[:MAX_TEMP_NAME_STEM] or "audio"
    for _ in range(MAX_TEMP_NAME_ATTEMPTS):
        candidate = directory / f".{stem}.{secrets.token_hex(6)}.apple{CONVERSION_SUFFIX}"
        if not candidate.exists():
            return candidate
    raise AppleSpeechError(
        APPLE_INPUT_ERROR,
        "無法在音訊檔目錄建立唯一的轉檔暫存檔名。",
        context={"stage": "conversion"},
    )


def _discard(path: Path) -> None:
    """刪除暫存檔（best-effort；成功、失敗與取消都會呼叫）。"""

    try:
        path.unlink(missing_ok=True)
    except OSError:
        return


def _raise_if_cancelled(cancel_event: object) -> None:
    if cancel_event is not None and getattr(cancel_event, "is_set", lambda: False)():
        raise AppleSpeechError(APPLE_CANCELLED, "Apple 語音辨識已取消。")


def _converted_ok(result: object, target: Path) -> bool:
    if getattr(result, "returncode", None) != 0:
        return False
    try:
        return target.is_file() and target.stat().st_size > 0
    except OSError:
        return False


def _convert(
    source: Path,
    target: Path,
    *,
    reason: str,
    timeout_seconds: float,
    cancel_event: object,
    relay: _ProgressRelay,
) -> float:
    """以 ffmpeg 轉成 16 kHz 單聲道 WAV；任何失敗都清掉暫存檔並丟穩定錯誤。"""

    _raise_if_cancelled(cancel_event)

    executable = _resolve_ffmpeg()
    input_suffix = source.suffix.lower()
    if not executable:
        raise AppleSpeechError(
            APPLE_INPUT_ERROR,
            "找不到 ffmpeg，無法把此音訊容器轉成 Apple 可讀取的格式。",
            context={"stage": "conversion", "input_suffix": input_suffix, "conversion_reason": reason},
        )

    relay.emit(12.0, f"Apple 語音辨識：轉換音訊格式（{input_suffix or '未知'} → {CONVERSION_SUFFIX}）…")
    argv = [
        executable,
        "-nostdin",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(source),
        *CONVERSION_ARGS,
        str(target),
    ]

    started = time.monotonic()
    try:
        result = apple_cli.run_helper(argv, timeout_seconds=timeout_seconds, cancel_event=cancel_event)
    except AppleSpeechError:
        _discard(target)
        raise
    except OSError as exc:
        _discard(target)
        raise AppleSpeechError(
            APPLE_INPUT_ERROR,
            "無法啟動 ffmpeg 進行音訊轉檔。",
            context={"stage": "conversion", "error_type": type(exc).__name__, "conversion_reason": reason},
        ) from exc

    seconds = time.monotonic() - started

    if getattr(result, "cancelled", False):
        _discard(target)
        raise AppleSpeechError(APPLE_CANCELLED, "Apple 語音辨識已取消。", context={"stage": "conversion"})
    if getattr(result, "timed_out", False):
        _discard(target)
        raise AppleSpeechError(
            APPLE_TIMEOUT,
            "音訊轉檔逾時，未能在時間預算內完成。",
            context={"stage": "conversion"},
        )
    if not _converted_ok(result, target):
        _discard(target)
        raise AppleSpeechError(
            APPLE_INPUT_ERROR,
            f"ffmpeg 無法讀取或轉換此音訊（{input_suffix or '未知容器'}）。",
            context={
                "stage": "conversion",
                "input_suffix": input_suffix,
                "conversion_reason": reason,
                "helper_exit_code": "unknown" if getattr(result, "returncode", None) is None else str(result.returncode),
            },
        )

    return seconds


def _convert_with_retry(
    source: Path,
    target: Path,
    *,
    reason: str,
    timeout_seconds: float,
    cancel_event: object,
    relay: _ProgressRelay,
) -> float:
    """轉檔失敗重試一次；取消永不重試（SI-03）。"""

    last_error: Optional[AppleSpeechError] = None
    for attempt in (1, 2):
        try:
            return _convert(
                source,
                target,
                reason=reason,
                timeout_seconds=timeout_seconds,
                cancel_event=cancel_event,
                relay=relay,
            )
        except AppleSpeechError as error:
            if error.code == APPLE_CANCELLED:
                raise
            last_error = error
            LOGGER.warning("Apple 音訊轉檔失敗（%s），第 %s 次嘗試", error.code, attempt)
            _discard(target)
    assert last_error is not None
    raise last_error


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------


def transcribe_with_apple(
    audio_path: str,
    *,
    locale: str,
    preset: str,
    progress_callback: Optional[Callable[[float, str], None]] = None,
    cancel_event: object = None,
    executable_path: Optional[str] = None,
    enable_preflight: bool = True,
) -> AppleTranscriptionResult:
    """呼叫 helper 轉錄單一音訊檔；失敗時丟帶穩定錯誤碼的 ``AppleSpeechError``。

    流程（凍結順序）：``resolve_executable`` → ``probe_executable`` → ffprobe
    duration（失敗用 600 下限，絕不因此失敗）→ 依 preflight 轉檔 → helper
    transcribe → payload 驗證 → CJK 正規化 → 回傳。

    ``use_vad=False`` 語意（SI-09）：Apple 嘗試不吃 Whisper 的 VAD／beam／
    hotwords／prompt 參數，本函式不接收也不需要這些入參。
    """

    relay = _ProgressRelay(progress_callback)

    if not apple_platform_supported():
        raise AppleSpeechError(
            APPLE_UNAVAILABLE,
            f"Apple Speech 僅支援 macOS，目前平台為 {_current_platform()}。",
            context={"platform": _current_platform()},
        )

    input_path = Path(audio_path).expanduser()
    input_suffix = input_path.suffix.lower()

    temp_path: Optional[Path] = None
    conversion_reason: Optional[str] = None
    conversion_seconds: Optional[float] = None

    try:
        relay.emit(5.0, "Apple 語音辨識：檢查命令列工具…")
        executable = apple_cli.resolve_executable(executable_path)

        relay.emit(10.0, "Apple 語音辨識：探測可用性…")
        apple_cli.probe_executable(
            executable,
            locale=locale,
            timeout_seconds=PROBE_TIMEOUT_SECONDS,
            cancel_event=cancel_event,
        )

        duration_seconds = _measure_duration_seconds(str(input_path))
        timeout_seconds = apple_cli.resolved_timeout_seconds(duration_seconds)

        conversion_reason = preflight_conversion_reason(input_suffix)
        if conversion_reason == "fragile_native_container" and not enable_preflight:
            # 只有「脆弱但原生可讀」的容器受此開關影響；非原生容器仍必須轉檔，
            # 否則 helper 根本讀不到輸入（關閉開關只影響速度，不影響正確性）。
            conversion_reason = None

        analysis_path = input_path
        if conversion_reason is not None:
            temp_path = _temp_target(input_path)
            conversion_seconds = _convert_with_retry(
                input_path,
                temp_path,
                reason=conversion_reason,
                timeout_seconds=_conversion_timeout_seconds(duration_seconds),
                cancel_event=cancel_event,
                relay=relay,
            )
            analysis_path = temp_path

        _raise_if_cancelled(cancel_event)
        relay.emit(20.0, "Apple 語音辨識：分析中…")
        argv = apple_cli.build_transcribe_argv(
            executable,
            input_path=str(analysis_path),
            locale=locale,
            preset=preset,
            timeout_seconds=timeout_seconds,
        )

        started = time.monotonic()
        result = apple_cli.run_helper(
            argv,
            timeout_seconds=timeout_seconds,
            cancel_event=cancel_event,
            on_progress=relay.helper_event,
        )
        elapsed_seconds = time.monotonic() - started

        if (
            getattr(result, "cancelled", False)
            or getattr(result, "timed_out", False)
            or getattr(result, "returncode", None) != 0
        ):
            raise apple_cli.error_from_helper_result(result, stage="transcribe")

        relay.emit(57.0, "Apple 語音辨識：驗證輸出…")
        payload = apple_cli.validate_transcription_payload(str(getattr(result, "stdout", "") or ""))

        text = apple_cli.normalize_apple_text(str(_payload_field(payload, "text", "") or ""))
        segments: list[ASRSegment] = []
        for raw_segment in _payload_field(payload, "segments", ()) or ():
            segment_text = apple_cli.normalize_apple_text(str(_payload_field(raw_segment, "text", "") or ""))
            if not segment_text:
                continue
            segments.append(
                ASRSegment(
                    start=_finite_float(_payload_field(raw_segment, "start")),
                    end=_finite_float(_payload_field(raw_segment, "end")),
                    text=segment_text,
                )
            )

        helper_metadata = _payload_field(payload, "metadata", {})
        if duration_seconds is None and isinstance(helper_metadata, Mapping):
            duration_seconds = _positive_float(helper_metadata.get("audio_duration_seconds"))

        real_time_factor = None
        if duration_seconds is not None and duration_seconds > 0:
            real_time_factor = round(elapsed_seconds / duration_seconds, 4)

        metadata: dict[str, object] = {
            "requested_engine": "apple",
            "resolved_engine": "apple",
            "engine_chain": "apple",
            "locale": str(locale),
            "audio_duration_seconds": round(duration_seconds, 3) if duration_seconds is not None else None,
            "elapsed_seconds": round(elapsed_seconds, 3),
            "real_time_factor": real_time_factor,
            "helper_invocations": 1,
            "conversion_reason": conversion_reason,
            "conversion_seconds": round(conversion_seconds, 3) if conversion_seconds is not None else None,
            "segment_count": len(segments),
            "segments_dropped": _non_negative_int(_payload_field(payload, "segments_dropped", 0)),
            "segments_time_degraded": _non_negative_int(_payload_field(payload, "segments_time_degraded", 0)),
        }

        LOGGER.info(
            "apple transcribe ok | text_chars=%s | segment_count=%s | elapsed=%.3fs | rtf=%s | helper_invocations=1 | conversion=%s",
            len(text),
            len(segments),
            elapsed_seconds,
            real_time_factor,
            conversion_reason or "none",
        )

        resolved_locale = _payload_field(payload, "locale")
        return AppleTranscriptionResult(
            text=text,
            segments=tuple(segments),
            metadata=metadata,
            duration_seconds=float(duration_seconds or 0.0),
            language=str(resolved_locale or locale),
        )
    except AppleSpeechError:
        raise
    except Exception as exc:  # noqa: BLE001 - 未預期例外仍須是 typed error
        raise AppleSpeechError(
            APPLE_TRANSCRIPTION_ERROR,
            "Apple 語音辨識發生未預期的錯誤。",
            context={"stage": "transcribe", "error_type": type(exc).__name__},
        ) from exc
    finally:
        if temp_path is not None:
            _discard(temp_path)


def _default_locale() -> str:
    """health 探測用 locale：以設定層 ``APPLE_LOCALE`` 為準（函式內延後 import）。"""

    from backend.core.config import settings

    return str(getattr(settings, "APPLE_LOCALE", "") or "").strip() or DEFAULT_LOCALE


def apple_helper_status(*, configured_path: Optional[str] = None) -> dict:
    """回報 helper 的健康狀態（REQ-10／CHECK-11）。

    * 非 macOS：直接回 ``supported=False``，**不**啟動子程序、不寫檔（SI-12）。
    * macOS：``available`` 代表 helper 找到且 probe 成功；``probe`` 是 probe
      payload（失敗為 ``None``），``reason`` 是穩定錯誤碼或 ``None``。
    """

    if not apple_platform_supported():
        return {"supported": False, "available": False, "path": None, "probe": None, "reason": "non_darwin"}

    try:
        executable = apple_cli.resolve_executable(configured_path)
    except AppleSpeechError as error:
        return {"supported": True, "available": False, "path": None, "probe": None, "reason": error.code}

    try:
        probe = apple_cli.probe_executable(
            executable,
            locale=_default_locale(),
            timeout_seconds=PROBE_TIMEOUT_SECONDS,
        )
    except AppleSpeechError as error:
        return {"supported": True, "available": False, "path": executable, "probe": None, "reason": error.code}
    except Exception as exc:  # noqa: BLE001 - 健康檢查不得讓呼叫端崩潰
        return {
            "supported": True,
            "available": False,
            "path": executable,
            "probe": None,
            "reason": type(exc).__name__,
        }

    return {
        "supported": True,
        "available": True,
        "path": executable,
        "probe": probe if isinstance(probe, dict) else None,
        "reason": None,
    }
