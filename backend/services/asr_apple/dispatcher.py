"""Apple ASR 路由（唯一路由擁有者，純函式）。

凍結規則（SI-01 / SI-02 / SI-03）：

- 顯式 ``apple``：鏈嚴格等於 ``("apple",)``，fail-closed，任何 Apple 錯誤
  （含 ``APPLE_OUTPUT_INVALID``）直接向上拋，不試下一個引擎。
- ``auto`` + Apple 平台（darwin + arm64/aarch64）：``("apple", "mlx_whisper")``。
- ``auto`` + 非 Apple 平台：維持既有單點解析（呼叫端提供的 ``default_backend``），
  永遠不會解析到 ``apple``。
- 其他顯式值：單點、原樣尊重。
- ``APPLE_CANCELLED`` 永不觸發 fallback；取消優先於逾時。

本模組維持 import 純潔（NFR-03 / SI-11），且不做平台偵測：Apple 平台判定由
呼叫端注入（``is_apple_platform``），讓三平台矩陣可在單測中以 mock 驗證。
"""

from __future__ import annotations

from .contract import APPLE_AUTO_FALLBACK, APPLE_CANCELLED, DEFAULT_ENGINE, normalize_engine_name


def resolve_engine_chain(
    requested: str = DEFAULT_ENGINE,
    *,
    is_apple_platform: bool,
    default_backend: str | None = None,
) -> tuple[str, ...]:
    """回傳本次請求的引擎嘗試鏈（凍結語意）。

    ``default_backend`` 只在「非 Apple 平台的 ``auto``」使用，必須由呼叫端以現行
    解析器（``infer_asr_backend``）算出，確保非 Mac 行為與現狀完全一致。
    """

    normalized = normalize_engine_name(requested)
    if normalized == "apple":
        return ("apple",)
    if normalized == "auto":
        if is_apple_platform:
            return APPLE_AUTO_FALLBACK
        if not default_backend:
            raise ValueError("非 Apple 平台的 auto 需要 default_backend 才能解析引擎鏈")
        return (default_backend,)
    return (normalized,)


def should_fallback(error_code: str | None) -> bool:
    """``auto`` 鏈中這個錯誤碼是否允許換下一個引擎。

    取消（``APPLE_CANCELLED``）永不 fallback，避免使用者取消後鏈又被喚醒（SI-03）。
    """

    return error_code != APPLE_CANCELLED
