"""
後端服務匯出入口。

整合裝置偵測、排隊、轉錄、摘要與檔案管理等核心服務，供 API 與主程式直接使用。

流程說明：
- API 會先從這裡取得服務實例，再依任務生命週期呼叫對應服務。

錯誤情境說明：
- 子服務若初始化失敗，會在匯入階段暴露問題，避免系統半啟動狀態。
"""

from backend.services.device_detector import device_detector, DeviceType
from backend.services.queue_manager import task_queue
from backend.services.transcription import transcription_service
from backend.services.summarization import summarization_service
from backend.services.file_manager import file_manager
from backend.services.task_processor import task_processor

__all__ = [
    "device_detector",
    "DeviceType",
    "task_queue",
    "transcription_service",
    "summarization_service",
    "file_manager",
    "task_processor"
]
