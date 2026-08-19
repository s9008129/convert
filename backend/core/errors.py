"""例外訊息描述工具。

httpx 的逾時類例外（ReadTimeout/ConnectTimeout 等）與部分底層 TimeoutError
的 str() 為空字串，直接記錄或呈現會遺失全部診斷資訊（v4.6.2 實際案例：
會議紀錄 fallback 文件缺「失敗原因」行）。所有對外呈現或記錄例外訊息的
地方一律改用 describe_exception()，保證至少帶出例外類別名稱。
"""


def describe_exception(e: BaseException) -> str:
    """回傳「類別名稱: 訊息」；訊息為空時退回 repr 保留類別資訊。"""
    msg = str(e).strip()
    return f"{type(e).__name__}: {msg}" if msg else f"{type(e).__name__}: {e!r}"
