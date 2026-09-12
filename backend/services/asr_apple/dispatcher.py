"""Apple ASR 路由（唯一路由擁有者，純函式）。

凍結規則（SI-01 / SI-02；Owner 2026-09-13 指示「Mac 僅提供 Apple SpeechAnalyzer」）：

- 顯式 ``apple``：鏈嚴格等於 ``("apple",)``，fail-closed，任何 Apple 錯誤
  （含 ``APPLE_OUTPUT_INVALID``）直接向上拋，不試下一個引擎。
- ``auto`` + Apple 平台（darwin + arm64/aarch64）：``("apple",)``——單一引擎，
  **永不 fallback**（Mac 已移除 Whisper 路徑）。
- Apple 平台上的顯式 ``transformers`` / ``faster_whisper`` / ``mlx_whisper``：
  ``ValueError`` 硬性拒絕（與非 Apple 平台拒絕 ``apple`` 對稱）。
- ``auto`` + 非 Apple 平台：維持既有單點解析（呼叫端提供的 ``default_backend``），
  永遠不會解析到 ``apple``。
- 非 Apple 平台的其他顯式值：單點、原樣尊重（Windows/Linux 行為完全不變）。

本模組維持 import 純潔（NFR-03 / SI-11），且不做平台偵測：Apple 平台判定由
呼叫端注入（``is_apple_platform``），讓三平台矩陣可在單測中以 mock 驗證。
"""

from __future__ import annotations

from .contract import APPLE_AUTO_FALLBACK, DEFAULT_ENGINE, normalize_engine_name


APPLE_ONLY_BACKENDS_ERROR = (
    "ASR_BACKEND={backend} 在 macOS 已不支援：Mac 僅提供 Apple SpeechAnalyzer（auto 或 apple）"
)


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
    if is_apple_platform:
        raise ValueError(APPLE_ONLY_BACKENDS_ERROR.format(backend=normalized))
    return (normalized,)
