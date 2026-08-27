"""例外訊息描述工具。

httpx 的逾時類例外（ReadTimeout/ConnectTimeout 等）與部分底層 TimeoutError
的 str() 為空字串，直接記錄或呈現會遺失全部診斷資訊（v4.6.2 實際案例：
會議紀錄 fallback 文件缺「失敗原因」行）。所有對外呈現或記錄例外訊息的
地方一律改用 describe_exception()，保證至少帶出例外類別名稱。
"""


# 穩定的子系統錯誤碼。這些錯誤會沿用既有 exception/description 管道，
# 供 task fallback 與 health detail 以可診斷、可測試的方式辨識；不新增 task state。
ASR_BACKEND_UNAVAILABLE = "ASR_BACKEND_UNAVAILABLE"
ASR_MODEL_UNAVAILABLE = "ASR_MODEL_UNAVAILABLE"
LMSTUDIO_UNREACHABLE = "LMSTUDIO_UNREACHABLE"
LMSTUDIO_NO_LOADED_LLM = "LMSTUDIO_NO_LOADED_LLM"
LMSTUDIO_MULTIPLE_LOADED_LLMS = "LMSTUDIO_MULTIPLE_LOADED_LLMS"
LMSTUDIO_MODEL_NOT_LOADED = "LMSTUDIO_MODEL_NOT_LOADED"
LOCAL_LLM_CONTEXT_BUDGET_EXCEEDED = "LOCAL_LLM_CONTEXT_BUDGET_EXCEEDED"
LMSTUDIO_NO_FINAL_CONTENT = "LMSTUDIO_NO_FINAL_CONTENT"


class StableServiceError(RuntimeError):
    """帶有穩定 code 的服務邊界錯誤。"""

    def __init__(self, code: str, detail: str):
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def describe_exception(e: BaseException) -> str:
    """回傳「類別名稱: 訊息」；訊息為空時退回 repr 保留類別資訊。"""
    msg = str(e).strip()
    return f"{type(e).__name__}: {msg}" if msg else f"{type(e).__name__}: {e!r}"
