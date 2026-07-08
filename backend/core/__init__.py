"""
核心設定入口。

提供全域設定與日誌物件，讓其他模組都能用一致方式讀取配置與紀錄事件。

流程說明：
- 其他模組只要匯入這個入口，就能拿到同一份 settings 與 log。

錯誤情境說明：
- 若設定檔格式有誤，例外會在設定載入階段被拋出，避免帶錯設定繼續執行。
"""

from backend.core.config import settings
from backend.core.logger import log

__all__ = ["settings", "log"]
