"""
中間件匯出入口。

目前提供請求逾時保護，避免單一請求卡住而影響整體服務回應。

流程說明：
- 啟動 API 時掛載 TimeoutMiddleware，超時請求會被自動中止。

錯誤情境說明：
- 若請求超過時限，系統會回傳可理解的錯誤，避免使用者長時間無回應。
"""

from backend.middleware.timeout import TimeoutMiddleware

__all__ = ['TimeoutMiddleware']
