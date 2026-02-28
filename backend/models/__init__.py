"""
資料模型匯出入口。

統一整理 API 會使用到的資料格式，讓前後端欄位定義一致、比較不容易溝通落差。

流程說明：
- API 收到請求與回傳結果時，都會優先套用這裡整理好的模型型別。

錯誤情境說明：
- 若欄位型別不符合模型定義，驗證錯誤會在進出 API 時立即被攔截。
"""

from backend.models.schemas import (
    TaskStatus,
    ProcessingMode,
    TaskInfo,
    TranscriptionResult,
    ProgressMessage,
    QueueStatus,
    UploadResponse,
    HealthStatus,
    ErrorResponse
)

__all__ = [
    "TaskStatus",
    "ProcessingMode",
    "TaskInfo",
    "TranscriptionResult",
    "ProgressMessage",
    "QueueStatus",
    "UploadResponse",
    "HealthStatus",
    "ErrorResponse"
]
