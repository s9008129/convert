"""Apple SpeechAnalyzer ASR 凍結契約（helper schema 1.0）。

本模組是 Swift helper 與 Python 端唯一的介面定義：engine 名稱、helper 離場碼、
穩定錯誤碼與 segment 型別。名稱、離場碼或錯誤碼的任何變更都屬語意變更，必須先
回到 Stage 01 重新規劃（SI-05）。

Import 純潔（NFR-03 / SI-11）：``import backend.services.asr_apple.contract``
不得拉入 ``mlx_whisper`` / ``torch`` / ``silero`` / ``faster_whisper``，也不得在
import 期偵測平台、啟動子程序或寫入檔案。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional

#: helper 寫到 stdout 的 JSON schema 版本（凍結）。
SCHEMA_VERSION = "1.0"

#: helper JSON 的 ``engine`` 識別字串（凍結）。
HELPER_ENGINE_NAME = "apple"

EngineName = str
ResolvedEngineName = str

ENGINE_NAMES: tuple[str, ...] = (
    "auto",
    "apple",
    "transformers",
    "faster_whisper",
    "mlx_whisper",
)
DEFAULT_ENGINE = "auto"

#: ``auto`` 在 Apple 平台（darwin + arm64/aarch64）的凍結引擎鏈（Owner 2026-09-13 指示）。
#: Mac 版**只提供 Apple SpeechAnalyzer**：鏈長固定為 1，永不 fallback 到 Whisper。
#: 非 Apple 平台的 ``auto`` 維持既有單點解析，永不出現 ``apple``（SI-01）。
APPLE_AUTO_FALLBACK: tuple[str, ...] = ("apple",)

# --- 穩定錯誤碼（helper 離場碼 → Python 例外，SI-05 凍結）-------------------

APPLE_UNAVAILABLE = "APPLE_UNAVAILABLE"
APPLE_LOCALE_UNSUPPORTED = "APPLE_LOCALE_UNSUPPORTED"
APPLE_ASSET_ERROR = "APPLE_ASSET_ERROR"
APPLE_INPUT_ERROR = "APPLE_INPUT_ERROR"
APPLE_TRANSCRIPTION_ERROR = "APPLE_TRANSCRIPTION_ERROR"
APPLE_TIMEOUT = "APPLE_TIMEOUT"
APPLE_CANCELLED = "APPLE_CANCELLED"
APPLE_OUTPUT_INVALID = "APPLE_OUTPUT_INVALID"

APPLE_ERROR_CODES: tuple[str, ...] = (
    APPLE_UNAVAILABLE,
    APPLE_LOCALE_UNSUPPORTED,
    APPLE_ASSET_ERROR,
    APPLE_INPUT_ERROR,
    APPLE_TRANSCRIPTION_ERROR,
    APPLE_TIMEOUT,
    APPLE_CANCELLED,
    APPLE_OUTPUT_INVALID,
)

#: helper 離場碼。``0`` 成功；``1`` 是通用槽位（``APPLE_TIMEOUT`` 與
#: ``APPLE_OUTPUT_INVALID`` 共用），實際子型別由 JSON ``error.code`` 決定。
APPLE_EXIT_SUCCESS = 0
APPLE_EXIT_GENERIC = 1

APPLE_EXIT_CODE_TO_ERROR_CODE: Mapping[int, Optional[str]] = {
    0: None,
    1: None,
    2: APPLE_UNAVAILABLE,
    3: APPLE_LOCALE_UNSUPPORTED,
    4: APPLE_ASSET_ERROR,
    5: APPLE_INPUT_ERROR,
    6: APPLE_TRANSCRIPTION_ERROR,
    7: APPLE_CANCELLED,
}


def normalize_engine_name(value: object, *, default: str = DEFAULT_ENGINE) -> str:
    """把設定/環境變數的值正規化為合法 engine 名稱（大小寫與 ``-`` 容錯）。

    非法值回 ``default``（與來源母本 ``normalize_engine_name`` 同義）；需要
    fail-fast 的呼叫端（例如平台守衛）必須自行先驗證。
    """

    if isinstance(value, str):
        normalized = value.strip().lower().replace("-", "_")
        if normalized in ENGINE_NAMES:
            return normalized
    return default


@dataclass(frozen=True, slots=True)
class ASRSegment:
    """單一有序逐字稿片段（秒）。

    ``start`` / ``end`` 可為 ``None``：時間軸缺失只降級該片段，不使非空文字失效
    （REQ-07）。
    """

    start: Optional[float]
    end: Optional[float]
    text: str


class AppleSpeechError(RuntimeError):
    """帶穩定錯誤碼的 Apple ASR 例外。

    ``context`` 只放有界、非敏感的診斷（不得放逐字稿或原始 payload）。
    """

    def __init__(
        self,
        code: str,
        user_message: str,
        *,
        context: Optional[Mapping[str, str]] = None,
    ) -> None:
        super().__init__(user_message)
        self.code = code
        self.user_message = user_message
        self.context: dict[str, str] = dict(context or {})

    def __str__(self) -> str:  # pragma: no cover - 直觀
        return self.user_message


def is_cancelled_error(error: BaseException) -> bool:
    """判斷例外是否代表使用者取消（取消永不 fallback，SI-03）。"""

    return isinstance(error, AppleSpeechError) and error.code == APPLE_CANCELLED
