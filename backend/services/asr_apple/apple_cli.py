"""Apple SpeechAnalyzer helper 的 Python 執行邊界（WAVE-03a）。

本模組是 Swift helper ``apple-speech-cli`` 唯一的 Python 呼叫層，職責刻意收斂在：

- 執行檔探索：``configured → <repo>/apple_speech_cli/.build/release → PATH``；找不到只
  給建置指令，永不自動編譯（DEC-04）。
- 子行程執行：``stdout``／``stderr`` 各自獨立執行緒排空、逾時公式、取消優先、
  ``terminate`` → 寬限 → ``kill``，返回前一定回收子行程（DEC-07 / NFR-02）。
- schema ``1.0`` payload 的嚴格驗證與穩定錯誤碼分類（REQ-07 / SI-04）。
- Apple 邊界專用的 CJK 空白正規化（DEC-08）。

進度診斷（best-effort）：helper 以 stderr 的 ``apple-speech-cli:progress {json}`` 回報
進度（helper 凍結協定；stdout 只會有單一 JSON）。``run_helper(on_progress=...)`` 因此
解析 stderr 的逐行輸出；stdout 行同樣會嘗試解析，好讓把進度寫到 stdout 的 helper 變體
也能回報，正式 helper 不會因此重複回報。

Import 純潔（NFR-03 / SI-11）：頂層只依賴標準函式庫與
``backend.services.asr_apple.contract``，不得拉入 ``mlx_whisper`` / ``torch`` /
``silero`` / ``faster_whisper``；import 期不偵測平台、不啟動子程序、不寫檔。
"""

from __future__ import annotations

import json
import logging
import math
import os
import re
import shutil
import subprocess
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .contract import (
    APPLE_CANCELLED,
    APPLE_ERROR_CODES,
    APPLE_EXIT_CODE_TO_ERROR_CODE,
    APPLE_OUTPUT_INVALID,
    APPLE_TIMEOUT,
    APPLE_UNAVAILABLE,
    HELPER_ENGINE_NAME,
    SCHEMA_VERSION,
    AppleSpeechError,
    ASRSegment,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 凍結常數（WAVE-03a 公開介面）
# ---------------------------------------------------------------------------

#: 逾時下限（秒）：短檔與 ffprobe 失敗時都不得低於此值（REQ-05 / SI-06）。
DEFAULT_TIMEOUT_FLOOR_SECONDS = 600.0

#: duration-aware 逾時公式 ``max(floor, duration * 3 + 300)``（SI-06）。
TIMEOUT_DURATION_FACTOR = 3.0
TIMEOUT_MARGIN_SECONDS = 300.0

#: stdout 擷取上限（字元）：長會議的 segments JSON 可能很大（DEC-07）。
STDOUT_CAPTURE_LIMIT = 8_000_000

#: stderr 擷取上限（字元）：只保留診斷。
STDERR_CAPTURE_LIMIT = 64_000

#: ``terminate()`` 後等待子行程自行結束的寬限秒數（DEC-07 / NFR-02）。
TERMINATE_GRACE_SECONDS = 5.0

#: 輪詢子行程狀態的間隔（秒）。
POLL_INTERVAL_SECONDS = 0.05

#: 讀取執行緒收尾的等待秒數。
READER_JOIN_TIMEOUT_SECONDS = 2.0

#: ``PATH`` 上的 helper 名稱。
HELPER_EXECUTABLE_NAME = "apple-speech-cli"

#: 缺少 helper 時要提示使用者的建置指令（永不自動編譯，DEC-04）。
HELPER_BUILD_COMMAND = "swift build -c release --package-path apple_speech_cli"

#: repo 內 ``swift build -c release`` 產出的 helper 相對路徑。
HELPER_PACKAGE_RELEASE_PATH = (
    Path("apple_speech_cli") / ".build" / "release" / HELPER_EXECUTABLE_NAME
)

#: 本 repo 根目錄（``backend/services/asr_apple/apple_cli.py`` 往上三層）。
REPO_ROOT = Path(__file__).resolve().parents[3]

#: helper 結構化進度行的前綴（helper 凍結協定；診斷一律走 stderr）。
PROGRESS_STDERR_PREFIX = "apple-speech-cli:progress "

#: 訊息與 context 的字元上限（避免把 stderr／payload 整段塞進 log）。
MAX_MESSAGE_CHARACTERS = 300
MAX_CONTEXT_VALUE_CHARACTERS = 300
MAX_STDERR_TAIL_LINES = 3
MAX_PROGRESS_LINE_CHARACTERS = 2000


# ---------------------------------------------------------------------------
# 文字工具
# ---------------------------------------------------------------------------


def clip_text(value: object, limit: int = MAX_MESSAGE_CHARACTERS) -> str:
    """把任意值轉成單行、有長度上限的字串。"""

    text = "" if value is None else str(value)
    text = text.replace("\r\n", " ").replace("\r", " ").replace("\n", " ")
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)] + "…"


def tail_lines(text: str, *, lines: int = MAX_STDERR_TAIL_LINES) -> str:
    """取最後幾行非空診斷文字（有上限）。"""

    candidates = [line.strip() for line in str(text).splitlines() if line.strip()]
    if not candidates:
        return ""
    return clip_text(" | ".join(candidates[-lines:]), MAX_CONTEXT_VALUE_CHARACTERS)


# ---------------------------------------------------------------------------
# 超時公式
# ---------------------------------------------------------------------------


def resolved_timeout_seconds(duration_seconds: float | None) -> float:
    """duration-aware 逾時：``max(600, duration * 3 + 300)``（SI-06）。

    ``None``、非有限數值或負值（例如 ``ffprobe`` 失敗／無輸出）一律回下限
    ``600.0``，絕不因此讓流程失敗。
    """

    if duration_seconds is None or isinstance(duration_seconds, bool):
        return DEFAULT_TIMEOUT_FLOOR_SECONDS
    if not isinstance(duration_seconds, (int, float)):
        return DEFAULT_TIMEOUT_FLOOR_SECONDS
    value = float(duration_seconds)
    if not math.isfinite(value) or value < 0:
        return DEFAULT_TIMEOUT_FLOOR_SECONDS
    return max(
        DEFAULT_TIMEOUT_FLOOR_SECONDS,
        value * TIMEOUT_DURATION_FACTOR + TIMEOUT_MARGIN_SECONDS,
    )


# ---------------------------------------------------------------------------
# 執行檔探索
# ---------------------------------------------------------------------------


def is_executable_file(path: Path) -> bool:
    """判斷路徑是否為可執行的一般檔案。"""

    try:
        return path.is_file() and os.access(path, os.X_OK)
    except OSError:
        return False


def helper_missing_message(*, configured_rejected: bool = False) -> str:
    """回傳缺少 helper 時的使用者訊息（含精確建置指令，永不自動編譯）。"""

    message = (
        "找不到 Apple Speech 命令列工具 apple-speech-cli。"
        f"請先執行「{HELPER_BUILD_COMMAND}」建置，本工具不會自動編譯。"
    )
    if configured_rejected:
        return f"{message}（設定的 helper 路徑不存在或不可執行，已改找預設位置）"
    return message


def resolve_executable(
    configured: str | None = None,
    *,
    repo_root: Path | None = None,
    which: Callable[[str], str | None] | None = None,
) -> str:
    """依序探索 helper：``configured → repo release 產物 → PATH``（DEC-04）。

    設定的路徑無效（不存在／不可執行）時只記 log 並繼續往後找，不會因此直接失敗；
    三個位置都找不到才丟 ``AppleSpeechError(APPLE_UNAVAILABLE)``，訊息含精確建置指令。
    """

    root = Path(repo_root) if repo_root is not None else REPO_ROOT
    lookup = which if which is not None else shutil.which

    configured_rejected = False
    if configured is not None and str(configured).strip():
        candidate = Path(str(configured)).expanduser()
        if is_executable_file(candidate):
            logger.debug("Apple helper：使用設定的執行檔 %s", candidate)
            return str(candidate)
        configured_rejected = True
        logger.warning(
            "Apple helper：設定的路徑不存在或不可執行（%s），改找預設位置",
            clip_text(configured, MAX_CONTEXT_VALUE_CHARACTERS),
        )

    packaged = Path(root) / HELPER_PACKAGE_RELEASE_PATH
    if is_executable_file(packaged):
        logger.debug("Apple helper：使用 repo release 產物 %s", packaged)
        return str(packaged)

    found = lookup(HELPER_EXECUTABLE_NAME)
    if found:
        logger.debug("Apple helper：使用 PATH 上的 %s", clip_text(found, MAX_CONTEXT_VALUE_CHARACTERS))
        return str(found)

    raise AppleSpeechError(
        APPLE_UNAVAILABLE,
        helper_missing_message(configured_rejected=configured_rejected),
        context={"stage": "helper_resolve"},
    )


# ---------------------------------------------------------------------------
# 子行程執行
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class HelperResult:
    """一次 helper 執行的結果（逾時與取消互斥，取消優先）。"""

    returncode: int | None = None
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    cancelled: bool = False


class _BoundedTextSink:
    """有上限的字串累積器；超過上限只丟棄多餘內容，不影響行程讀取。"""

    __slots__ = ("_chunks", "_limit", "_size", "truncated")

    def __init__(self, limit: int) -> None:
        self._chunks: list[str] = []
        self._limit = max(0, int(limit))
        self._size = 0
        self.truncated = False

    def add(self, chunk: str) -> None:
        if not chunk:
            return
        remaining = self._limit - self._size
        if remaining <= 0:
            self.truncated = True
            return
        if len(chunk) > remaining:
            self._chunks.append(chunk[:remaining])
            self._size = self._limit
            self.truncated = True
            return
        self._chunks.append(chunk)
        self._size += len(chunk)

    def text(self) -> str:
        return "".join(self._chunks)


def _make_progress_handler(
    on_progress: Callable[[float, str], None],
) -> Callable[[str], None]:
    """把進度行轉成 ``on_progress(fraction, message)``；無法解析的行直接忽略。"""

    def handle(line: str) -> None:
        parsed = parse_progress_line(line)
        if parsed is None:
            return
        fraction, message = parsed
        on_progress(fraction, message)

    return handle


def _drain_stream(
    stream: Any,
    sink: _BoundedTextSink,
    handler: Callable[[str], None] | None,
) -> None:
    """獨立執行緒排空一個 pipe；handler 的例外永遠不得讓辨識失敗。"""

    try:
        for line in stream:
            sink.add(line)
            if handler is not None:
                try:
                    handler(line.rstrip("\n"))
                except Exception:  # noqa: BLE001 - 進度回報是 best-effort
                    continue
    except (OSError, ValueError):
        return
    finally:
        try:
            stream.close()
        except (OSError, ValueError):
            pass


def _wait_for_exit(child: Any, seconds: float) -> bool:
    """等待子行程結束；回 ``True`` 表示已結束。"""

    deadline = time.monotonic() + max(0.0, float(seconds))
    while True:
        if child.poll() is not None:
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(max(0.0, float(POLL_INTERVAL_SECONDS)))


def _terminate_child(child: Any, *, grace_seconds: float) -> None:
    """``terminate()`` → 寬限 → ``kill()``，確保子行程回到已結束狀態。"""

    try:
        child.terminate()
    except (OSError, ValueError):
        pass

    if _wait_for_exit(child, grace_seconds):
        return

    try:
        child.kill()
    except (OSError, ValueError):
        pass

    _wait_for_exit(child, grace_seconds)


def run_helper(
    argv: Sequence[str],
    *,
    timeout_seconds: float,
    cancel_event: threading.Event | None = None,
    on_progress: Callable[[float, str], None] | None = None,
) -> HelperResult:
    """執行 helper 並回傳 ``HelperResult``（DEC-07 / NFR-02 凍結語意）。

    - ``stdout`` 與 ``stderr`` 由各自獨立執行緒排空，pipe 滿載不會卡死；``stdout``
      擷取上限為 ``STDOUT_CAPTURE_LIMIT`` 字元（超過只截斷，行程照常讀完）。
    - 取消（``cancel_event``）優先於逾時：取消時 ``cancelled=True``、``timed_out=False``。
    - 逾期或取消：``terminate()`` → ``TERMINATE_GRACE_SECONDS`` 寬限 → ``kill()``，
      返回前一定 ``wait()`` 回收子行程（無殭屍、無 orphan）。
    - ``on_progress`` 只收到 ``parse_progress_line`` 解析成功的行；回呼例外不得影響
      辨識結果。
    - 執行檔無法啟動（``OSError``）時丟 ``AppleSpeechError(APPLE_UNAVAILABLE)``。
    """

    try:
        timeout_value = float(timeout_seconds)
    except (TypeError, ValueError) as exc:
        raise ValueError("run_helper 需要 timeout_seconds 數值（秒）") from exc

    args = tuple(str(item) for item in argv)
    stdout_sink = _BoundedTextSink(STDOUT_CAPTURE_LIMIT)
    stderr_sink = _BoundedTextSink(STDERR_CAPTURE_LIMIT)
    handler = None if on_progress is None else _make_progress_handler(on_progress)

    try:
        child = subprocess.Popen(
            list(args),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
    except OSError as exc:
        raise AppleSpeechError(
            APPLE_UNAVAILABLE,
            "無法啟動 Apple Speech 命令列工具。",
            context={"stage": "helper_spawn", "error": clip_text(exc, MAX_CONTEXT_VALUE_CHARACTERS)},
        ) from exc

    stdout_reader = threading.Thread(
        target=_drain_stream, args=(child.stdout, stdout_sink, handler), daemon=True
    )
    stderr_reader = threading.Thread(
        target=_drain_stream, args=(child.stderr, stderr_sink, handler), daemon=True
    )
    stdout_reader.start()
    stderr_reader.start()

    deadline = time.monotonic() + max(0.0, timeout_value)
    cancelled = False
    timed_out = False

    try:
        while True:
            if child.poll() is not None:
                break
            if cancel_event is not None and cancel_event.is_set():
                cancelled = True
                break
            if time.monotonic() >= deadline:
                timed_out = True
                break
            time.sleep(max(0.0, float(POLL_INTERVAL_SECONDS)))

        if cancelled or timed_out:
            _terminate_child(child, grace_seconds=float(TERMINATE_GRACE_SECONDS))
        try:
            child.wait()
        except OSError:
            pass
    finally:
        stdout_reader.join(timeout=READER_JOIN_TIMEOUT_SECONDS)
        stderr_reader.join(timeout=READER_JOIN_TIMEOUT_SECONDS)

    return HelperResult(
        returncode=child.returncode,
        stdout=stdout_sink.text(),
        stderr=stderr_sink.text(),
        timed_out=timed_out,
        cancelled=cancelled,
    )


# ---------------------------------------------------------------------------
# schema 1.0 payload 驗證
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ApplePayload:
    """已驗證且正規化後的 transcribe payload。"""

    text: str
    segments: tuple[ASRSegment, ...]
    locale: str | None
    metadata: Mapping[str, object]
    segments_dropped: int
    segments_time_degraded: int


def output_invalid(message: str, *, context: Mapping[str, str] | None = None) -> AppleSpeechError:
    """建立 ``APPLE_OUTPUT_INVALID`` 錯誤（可參與 auto fallback）。"""

    return AppleSpeechError(APPLE_OUTPUT_INVALID, message, context=context)


def try_decode_payload(stdout: str) -> Mapping[str, Any] | None:
    """盡力把 stdout 解析成單一 JSON object；任何污染都回 ``None``。"""

    if not isinstance(stdout, str) or not stdout.strip():
        return None
    try:
        decoded = json.loads(stdout)
    except (TypeError, ValueError):
        return None
    if not isinstance(decoded, dict):
        return None
    return decoded


def payload_error_code(payload: Mapping[str, Any] | None) -> str | None:
    """取出 payload 內合法的穩定錯誤碼（``APPLE_TIMEOUT`` 等子型別靠此區分）。"""

    if not isinstance(payload, Mapping):
        return None
    error = payload.get("error")
    if not isinstance(error, Mapping):
        return None
    code = error.get("code")
    if isinstance(code, str) and code in APPLE_ERROR_CODES:
        return code
    return None


def payload_error_message(payload: Mapping[str, Any] | None) -> str:
    """取出 payload 內的錯誤訊息（有上限）。"""

    if not isinstance(payload, Mapping):
        return ""
    error = payload.get("error")
    if isinstance(error, Mapping):
        message = error.get("message")
        if isinstance(message, str) and message.strip():
            return clip_text(message)
        return ""
    if isinstance(error, str) and error.strip():
        return clip_text(error)
    return ""


class _Drop:
    """哨兵：代表「丟棄這個值」。"""


_DROP = _Drop()


def _as_json_scalar(value: object) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value if math.isfinite(value) else _DROP
    if isinstance(value, str):
        return value
    if value is None:
        return None
    return _DROP


def sanitize_metadata(raw: object, *, command: str) -> dict[str, object]:
    """把 helper metadata 收斂成扁平 JSON scalar（容器直接丟棄）。"""

    if raw is None:
        return {}
    if not isinstance(raw, Mapping):
        raise output_invalid(
            f"Apple 命令列工具輸出 metadata 非物件（{clip_text(type(raw).__name__, 40)}）。",
            context={"command": command},
        )

    sanitized: dict[str, object] = {}
    for key, value in raw.items():
        if not isinstance(key, str):
            continue
        scalar = _as_json_scalar(value)
        if scalar is _DROP:
            continue
        sanitized[clip_text(key, 80)] = scalar
    return sanitized


def _require_schema_envelope(payload: Mapping[str, Any], *, command: str) -> None:
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise output_invalid(
            "Apple 命令列工具輸出 schema_version 非 "
            f"{SCHEMA_VERSION}（{clip_text(payload.get('schema_version'), 40)}）。",
            context={"command": command},
        )
    if payload.get("engine") != HELPER_ENGINE_NAME:
        raise output_invalid(
            "Apple 命令列工具輸出 engine 非 "
            f"{HELPER_ENGINE_NAME}（{clip_text(payload.get('engine'), 40)}）。",
            context={"command": command},
        )


def _coerce_bool(payload: Mapping[str, Any], key: str, *, command: str) -> bool:
    value = payload.get(key)
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    raise output_invalid(
        f"Apple 命令列工具輸出 {key} 非布林值（{clip_text(value, 40)}）。",
        context={"command": command},
    )


def _coerce_text(payload: Mapping[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if isinstance(value, str) and value.strip():
        return value
    return None


def _coerce_time_bound(value: object, *, field: str, index: int) -> float | None:
    """segment 的 start／end 只接受 number 或 null；其餘視為輸出違反。"""

    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise output_invalid(
            f"Apple 命令列工具輸出的 segments[{index}].{field} 非數字或 null。",
            context={"segment_index": str(index)},
        )
    number = float(value)
    if not math.isfinite(number):
        raise output_invalid(
            f"Apple 命令列工具輸出的 segments[{index}].{field} 非有限數值。",
            context={"segment_index": str(index)},
        )
    return number


def _validated_transcription(payload: Mapping[str, Any]) -> ApplePayload:
    """嚴格驗證已解碼的 transcribe payload（REQ-07 / SI-04）。"""

    _require_schema_envelope(payload, command="transcribe")

    raw_text = payload.get("text")
    if not isinstance(raw_text, str):
        raise output_invalid(
            f"Apple 命令列工具輸出的 text 非字串（{clip_text(type(raw_text).__name__, 40)}）。",
            context={"command": "transcribe"},
        )
    text = normalize_apple_text(raw_text)
    if not text:
        raise output_invalid(
            "Apple 命令列工具輸出的 text 在正規化後為空。",
            context={"command": "transcribe"},
        )

    raw_segments = payload.get("segments")
    if not isinstance(raw_segments, list):
        raise output_invalid(
            f"Apple 命令列工具輸出的 segments 非陣列（{clip_text(type(raw_segments).__name__, 40)}）。",
            context={"command": "transcribe"},
        )

    segments: list[ASRSegment] = []
    dropped = 0
    degraded = 0
    for index, raw_segment in enumerate(raw_segments):
        if not isinstance(raw_segment, Mapping):
            raise output_invalid(
                f"Apple 命令列工具輸出的 segments[{index}] 非物件。",
                context={"segment_index": str(index)},
            )
        segment_text = raw_segment.get("text")
        if not isinstance(segment_text, str):
            raise output_invalid(
                f"Apple 命令列工具輸出的 segments[{index}].text 非字串。",
                context={"segment_index": str(index)},
            )
        start = _coerce_time_bound(raw_segment.get("start"), field="start", index=index)
        end = _coerce_time_bound(raw_segment.get("end"), field="end", index=index)

        if start is not None and end is not None and end < start:
            # 時間軸局部降級：保留文字，只把不可信的 end 設回 None（REQ-07）。
            end = None
            degraded += 1

        normalized_text = normalize_apple_text(segment_text)
        if not normalized_text:
            dropped += 1
            continue

        segments.append(ASRSegment(start=start, end=end, text=normalized_text))

    raw_metadata = payload.get("metadata")
    if not isinstance(raw_metadata, Mapping):
        raise output_invalid(
            f"Apple 命令列工具輸出 metadata 非物件（{clip_text(type(raw_metadata).__name__, 40)}）。",
            context={"command": "transcribe"},
        )

    return ApplePayload(
        text=text,
        segments=tuple(segments),
        locale=_coerce_text(payload, "locale"),
        metadata=sanitize_metadata(raw_metadata, command="transcribe"),
        segments_dropped=dropped,
        segments_time_degraded=degraded,
    )


def validate_transcription_payload(raw_stdout: str) -> ApplePayload:
    """嚴格驗證 transcribe 的 stdout：必須是單一 schema 1.0 JSON 文件（SI-04）。

    stdout 污染（多份 JSON、前後雜訊、非 JSON、非物件）、缺欄位、型別錯誤、
    ``end < start`` 以外的任何違反都是 ``APPLE_OUTPUT_INVALID``；``end < start``
    只把該 segment 的 ``end`` 降級為 ``None`` 並累計 ``segments_time_degraded``；
    正規化後為空的 segment 丟棄並累計 ``segments_dropped``。
    """

    if not isinstance(raw_stdout, str) or not raw_stdout.strip():
        raise output_invalid(
            "Apple 命令列工具 stdout 為空，缺少 schema 1.0 JSON。",
            context={"command": "transcribe"},
        )
    try:
        decoded = json.loads(raw_stdout)
    except (TypeError, ValueError) as exc:
        raise output_invalid(
            "Apple 命令列工具 stdout 不是單一 JSON 文件（含多份 JSON 或雜訊）。",
            context={"command": "transcribe"},
        ) from exc
    if not isinstance(decoded, dict):
        raise output_invalid(
            f"Apple 命令列工具輸出不是 JSON 物件（{clip_text(type(decoded).__name__, 40)}）。",
            context={"command": "transcribe"},
        )
    return _validated_transcription(decoded)


# ---------------------------------------------------------------------------
# helper 命令列
# ---------------------------------------------------------------------------


def build_probe_argv(executable: str, *, locale: str) -> list[str]:
    """probe 的 argv（不觸發模型安裝）。"""

    return [str(executable), "probe", "--locale", str(locale), "--output-format", "json"]


def build_transcribe_argv(
    executable: str,
    *,
    input_path: str,
    locale: str,
    preset: str,
    timeout_seconds: float,
) -> list[str]:
    """transcribe 的 argv。

    ``--timeout`` 讓 helper 自己也能在時間預算內協作式收尾（Python 端仍以
    ``run_helper(timeout_seconds=...)`` 為硬性上限）。
    """

    return [
        str(executable),
        "transcribe",
        "--input",
        str(input_path),
        "--locale",
        str(locale),
        "--output-format",
        "json",
        "--preset",
        str(preset),
        "--timeout",
        _format_timeout_argument(timeout_seconds),
    ]


def _format_timeout_argument(timeout_seconds: float) -> str:
    value = float(timeout_seconds)
    if not math.isfinite(value) or value < 0:
        return "0"
    return f"{value:g}"


def _validate_probe_document(payload: Mapping[str, Any]) -> None:
    """驗證 probe payload 的 envelope 與欄位型別（寬鬆缺欄位、嚴格型別）。"""

    _require_schema_envelope(payload, command="probe")

    command_value = payload.get("command")
    if isinstance(command_value, str) and command_value != "probe":
        raise output_invalid(
            f"Apple 命令列工具 probe 輸出的 command 非 probe（{clip_text(command_value, 40)}）。",
            context={"command": "probe"},
        )

    asset_status = payload.get("asset_status")
    if asset_status is not None and not isinstance(asset_status, str):
        raise output_invalid(
            f"Apple 命令列工具 probe 輸出 asset_status 非字串（{clip_text(asset_status, 40)}）。",
            context={"command": "probe"},
        )

    for key in (
        "locale_supported",
        "locale_in_supported_list",
        "locale_installed",
        "transcriber_is_available",
    ):
        _coerce_bool(payload, key, command="probe")

    sanitize_metadata(payload.get("metadata"), command="probe")


def probe_executable(
    executable: str,
    *,
    locale: str,
    timeout_seconds: float = 120.0,
    cancel_event: threading.Event | None = None,
) -> dict[str, Any]:
    """執行 ``probe`` 並回傳解析後的 probe 文件（REQ-04 / REQ-07）。

    失敗時依穩定錯誤碼丟 ``AppleSpeechError``：helper 離場碼／逾時／取消走
    ``error_from_helper_result``；stdout 不是單一 schema 1.0 JSON、或 probe 欄位
    型別違反則為 ``APPLE_OUTPUT_INVALID``。
    """

    argv = build_probe_argv(executable, locale=locale)
    result = run_helper(argv, timeout_seconds=timeout_seconds, cancel_event=cancel_event)

    if result.cancelled or result.timed_out or result.returncode != 0:
        raise error_from_helper_result(result, stage="helper_probe")

    payload = try_decode_payload(result.stdout)
    if payload is None:
        raise output_invalid(
            "Apple 命令列工具 probe 輸出不是單一 schema 1.0 JSON 文件。",
            context={"command": "probe"},
        )
    _validate_probe_document(payload)
    return dict(payload)


# ---------------------------------------------------------------------------
# 錯誤分類
# ---------------------------------------------------------------------------


def _classify_helper_failure(result: HelperResult) -> str:
    """把一次失敗的 helper 執行分類成穩定錯誤碼（SI-05）。

    規則（依序）：取消 → ``APPLE_CANCELLED``；逾時 → ``APPLE_TIMEOUT``；
    payload ``error.code`` 合法 → 直接採用（exit 1 的 ``APPLE_TIMEOUT`` 靠此）；
    離場碼 2–7 → 對應碼；被訊號終止且沒有合法 JSON → ``APPLE_UNAVAILABLE``；
    其餘（含 exit 1 沒有合法 ``error.code``、exit 0 卻落到失敗分類）→
    ``APPLE_OUTPUT_INVALID``。
    """

    if result.cancelled:
        return APPLE_CANCELLED
    if result.timed_out:
        return APPLE_TIMEOUT

    payload = try_decode_payload(result.stdout)
    subtype = payload_error_code(payload)
    if subtype is not None:
        return subtype

    if result.returncode is not None:
        mapped = APPLE_EXIT_CODE_TO_ERROR_CODE.get(int(result.returncode))
        if mapped is not None:
            return mapped

    if result.returncode is None or result.returncode < 0:
        # 被訊號終止（或沒有離場碼）：helper 崩潰／無法執行，不是輸出格式問題。
        return APPLE_UNAVAILABLE if payload is None else APPLE_OUTPUT_INVALID

    return APPLE_OUTPUT_INVALID


def _failure_message(code: str, payload: Mapping[str, Any] | None) -> str:
    """組出對應錯誤碼的使用者訊息（有上限、不含逐字稿）。"""

    detail = payload_error_message(payload)
    if code == APPLE_TIMEOUT:
        return "Apple 語音辨識逾時，未能在時間預算內完成。"
    if code == APPLE_CANCELLED:
        return "Apple 語音辨識已取消。"
    if code == APPLE_OUTPUT_INVALID:
        if detail:
            return f"Apple 命令列工具輸出無法解析（{detail}）。"
        return "Apple 命令列工具輸出無法解析（缺少合法的 schema 1.0 JSON）。"
    if detail:
        return f"Apple 語音辨識失敗（{code}）：{detail}"
    return f"Apple 語音辨識失敗（{code}）。"


def failure_context(result: HelperResult, *, stage: str) -> dict[str, str]:
    """組出可安全記錄的失敗 context（絕不含逐字稿或原始 payload）。"""

    context = {
        "stage": clip_text(stage, 80),
        "helper_exit_code": "unknown" if result.returncode is None else str(result.returncode),
        "helper_timed_out": "true" if result.timed_out else "false",
        "helper_cancelled": "true" if result.cancelled else "false",
    }
    stderr_tail = tail_lines(result.stderr)
    if stderr_tail:
        context["helper_stderr_tail"] = stderr_tail
    return context


def error_from_helper_result(result: HelperResult, *, stage: str) -> AppleSpeechError:
    """把失敗的 ``HelperResult`` 轉成帶穩定錯誤碼的 ``AppleSpeechError``。"""

    code = _classify_helper_failure(result)
    payload = try_decode_payload(result.stdout)
    return AppleSpeechError(
        code,
        _failure_message(code, payload),
        context=failure_context(result, stage=stage),
    )


# ---------------------------------------------------------------------------
# Apple 專屬文字正規化（DEC-08）
# ---------------------------------------------------------------------------

#: 視為「不留空白」的 CJK 文字單位（漢字、相容漢字、假名）。
_CJK_TEXT_CLASS = "\u3040-\u30ff\u31f0-\u31ff\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff"

#: 全形／CJK 標點（不含 U+3000 表意空格，因為它本身是空白）。
_CJK_MARK_CLASS = (
    "\u2014\u2018\u2019\u201c\u201d\u2026"
    "\u3001-\u303f"
    "\uff01-\uff0f\uff1a-\uff20\uff3b-\uff40\uff5b-\uff65"
)

_WHITESPACE_RUN_RE = re.compile(r"\s+")
_SPACE_BETWEEN_CJK_RE = re.compile(rf"(?<=[{_CJK_TEXT_CLASS}])[\s]+(?=[{_CJK_TEXT_CLASS}])")
_SPACE_BEFORE_CJK_MARK_RE = re.compile(rf"[\s]+(?=[{_CJK_MARK_CLASS}])")
_SPACE_AFTER_CJK_MARK_RE = re.compile(rf"(?<=[{_CJK_MARK_CLASS}])[\s]+")


def normalize_apple_text(text: str) -> str:
    """正規化 Apple 逐字稿的 CJK 空白（只作用於 Apple 邊界，不動共用 normalizer）。

    1. 所有空白序列收斂成單一空格。
    2. 兩個 CJK 文字單位之間的空白全部移除。
    3. 全形／CJK 標點前後的空白移除。
    4. 去除頭尾空白。

    例如 ``今天天氣很好 ，我們一起去公園散步`` 會變成
    ``今天天氣很好，我們一起去公園散步``。
    """

    if not isinstance(text, str):
        return ""

    normalized = _WHITESPACE_RUN_RE.sub(" ", text)
    normalized = _SPACE_BETWEEN_CJK_RE.sub("", normalized)
    normalized = _SPACE_BEFORE_CJK_MARK_RE.sub("", normalized)
    normalized = _SPACE_AFTER_CJK_MARK_RE.sub("", normalized)
    return normalized.strip()


# ---------------------------------------------------------------------------
# 進度診斷（best-effort）
# ---------------------------------------------------------------------------


def _decode_progress_line(line: str) -> Mapping[str, Any] | None:
    """解析 ``apple-speech-cli:progress {json}``；不合法一律回 ``None``。"""

    if not isinstance(line, str):
        return None
    stripped = line.strip()
    if not stripped.startswith(PROGRESS_STDERR_PREFIX):
        return None
    if len(stripped) > MAX_PROGRESS_LINE_CHARACTERS:
        return None
    body = stripped[len(PROGRESS_STDERR_PREFIX) :].strip()
    if not body:
        return None
    try:
        decoded = json.loads(body)
    except (ValueError, TypeError):
        return None
    if not isinstance(decoded, dict):
        return None
    return decoded


def progress_fraction(update: Mapping[str, Any]) -> float | None:
    """從進度物件取出 0–1 的分數（找不到或非有限數值時回 ``None``）。

    主要鍵是 helper 凍結的 ``fractionCompleted``；大於 1 的數值與 ``percent`` 視為
    百分比。其餘鍵只是無害的向後相容 fallback。
    """

    for key in (
        "fractionCompleted",
        "fraction_completed",
        "completedFraction",
        "completed_fraction",
        "fraction",
        "progress",
        "percent",
    ):
        value = update.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            continue
        number = float(value)
        if not math.isfinite(number):
            continue
        if key == "percent" or number > 1.0:
            number = number / 100.0
        return min(1.0, max(0.0, number))
    return None


def progress_message(update: Mapping[str, Any]) -> str:
    """把進度物件轉成簡短、有上限的中文狀態訊息（不回顯任意 helper 文字）。

    ``asset_install`` 是使用者唯一會長時間等待的階段（首次使用要下載模型），
    因此給它固定的中文說法；其他 phase 使用通用訊息並帶上限。
    """

    status = update.get("status")
    status_text = status if isinstance(status, str) else ""
    phase = update.get("phase")
    phase_text = phase if isinstance(phase, str) else ""

    if phase_text == "asset_install":
        if status_text == "finished":
            return "Apple 語音模型安裝完成"
        if status_text == "failed":
            error_code = update.get("error_code")
            if isinstance(error_code, str) and error_code in APPLE_ERROR_CODES:
                return f"Apple 語音模型安裝失敗（{error_code}）"
            return "Apple 語音模型安裝失敗"
        return "Apple 語音模型安裝中…"

    label = clip_text(phase_text, 40) or "helper"
    if status_text == "started":
        return f"Apple 語音辨識：{label} 開始…"
    if status_text == "finished":
        return f"Apple 語音辨識：{label} 完成"
    if status_text == "failed":
        return f"Apple 語音辨識：{label} 失敗"
    return f"Apple 語音辨識：{label} 進行中…"


def parse_progress_line(line: str) -> tuple[float, str] | None:
    """解析 helper 的結構化進度行；回 ``(fraction, message)`` 或 ``None``。

    只有同時滿足「``apple-speech-cli:progress`` 前綴＋合法 JSON 物件＋可取得 0–1
    分數」的行才算解析成功；沒有分數的診斷行（例如 asset install 的 started）
    回 ``None``，讓呼叫端不會把進度條錯誤地重設成 0。
    """

    update = _decode_progress_line(line)
    if update is None:
        return None
    fraction = progress_fraction(update)
    if fraction is None:
        return None
    return (fraction, progress_message(update))
