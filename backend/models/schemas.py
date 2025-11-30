"""
MeetingScribe 資料模型
v2.1 - 包含排隊系統和 User Prompt 支援
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """任務狀態"""
    QUEUED = "queued"              # 排隊中
    PENDING = "pending"            # 等待處理
    UPLOADING = "uploading"        # 上傳中
    TRANSCRIBING = "transcribing"  # 轉錄中
    SUMMARIZING = "summarizing"    # 生成摘要中
    COMPLETED = "completed"        # 已完成
    FAILED = "failed"              # 失敗
    CANCELLED = "cancelled"        # 已取消


class ProcessingMode(str, Enum):
    """處理模式"""
    LOCAL = "local"       # 本地模式（Ollama）
    LMSTUDIO = "lmstudio" # 本地模式（LM Studio - OpenAI 相容）
    CLOUD = "cloud"       # 雲端模式（Gemini API）


class TaskInfo(BaseModel):
    """任務資訊"""
    task_id: str
    filename: str
    original_filename: str
    file_size: int
    status: TaskStatus = TaskStatus.QUEUED
    progress: float = 0.0
    stage: str = "等待中"
    queue_position: Optional[int] = None
    estimated_wait_seconds: Optional[int] = None
    processing_mode: ProcessingMode = ProcessingMode.LOCAL
    user_prompt: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None


class TranscriptionResult(BaseModel):
    """轉錄結果"""
    task_id: str
    filename: str
    transcript: str
    summary: str
    duration_seconds: float
    processing_time_seconds: float
    word_count: int
    processing_mode: ProcessingMode
    user_prompt_used: Optional[str] = None
    device_used: str = "unknown"
    model_info: dict = Field(default_factory=dict)


class ProgressMessage(BaseModel):
    """WebSocket 進度訊息"""
    task_id: str
    status: TaskStatus
    progress: float
    stage: str
    message: str
    eta_seconds: Optional[int] = None
    queue_position: Optional[int] = None
    queue_total: Optional[int] = None


class QueueStatus(BaseModel):
    """排隊狀態"""
    total_queued: int
    processing_count: int
    estimated_wait_seconds: int
    max_concurrent: int
    queue_max_size: int


class UploadResponse(BaseModel):
    """上傳回應"""
    task_id: str
    filename: str
    file_size: int
    queue_position: int
    estimated_wait_seconds: int
    message: str


class HealthStatus(BaseModel):
    """健康狀態"""
    status: str
    version: str = "2.1.0"
    gpu_available: bool
    gpu_name: Optional[str] = None
    ollama_available: bool
    lmstudio_available: bool = False
    gemini_available: bool
    queue_status: QueueStatus
    device_info: dict = Field(default_factory=dict)


class ErrorResponse(BaseModel):
    """錯誤回應"""
    error: str
    detail: Optional[str] = None
    code: str = "UNKNOWN_ERROR"
