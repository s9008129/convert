"""
任務排隊管理器。

使用先進先出（FIFO）管理任務，避免同時處理過多檔案而造成記憶體或 GPU 壓力過高。
"""

import asyncio
import uuid
from datetime import datetime
from typing import Dict, Optional, List
from collections import deque

from backend.core.config import settings
from backend.core.logger import log
from backend.models.schemas import TaskInfo, TaskStatus, ProcessingMode, QueueStatus


class TaskQueueManager:
    """
    任務排隊管理器
    實現 FIFO 排隊機制，避免資源過度消耗
    """
    
    def __init__(self):
        """初始化排隊資料結構，確保任務依先進先出順序被處理。"""
        self._queue: deque[str] = deque()  # 排隊中的任務 ID
        self._tasks: Dict[str, TaskInfo] = {}  # 所有任務資訊
        self._processing: set[str] = set()  # 正在處理的任務 ID
        self._lock = asyncio.Lock()
        self._process_event = asyncio.Event()
        
    async def add_task(
        self,
        filename: str,
        original_filename: str,
        file_size: int,
        processing_mode: ProcessingMode = ProcessingMode.LOCAL,
        user_prompt: Optional[str] = None,
        template_id: str = "general",
    ) -> Optional[TaskInfo]:
        """
        新增任務到排隊系統。

        若排隊已滿會回傳 None，呼叫端可立即回覆「稍後再試」，避免使用者長時間等待。
        Returns:
            TaskInfo 如果成功加入佇列，None 如果佇列已滿
        """
        async with self._lock:
            # 檢查佇列是否已滿
            if len(self._queue) >= settings.QUEUE_MAX_SIZE:
                log.warning(f"排隊佇列已滿 ({settings.QUEUE_MAX_SIZE})")
                return None
            
            # 生成任務 ID
            task_id = str(uuid.uuid4())[:8]
            
            # 計算排隊位置和預估等待時間
            queue_position = len(self._queue) + 1
            estimated_wait = self._calculate_wait_time(queue_position)
            
            # 建立任務資訊
            task = TaskInfo(
                task_id=task_id,
                filename=filename,
                original_filename=original_filename,
                file_size=file_size,
                status=TaskStatus.QUEUED,
                queue_position=queue_position,
                estimated_wait_seconds=estimated_wait,
                processing_mode=processing_mode,
                user_prompt=user_prompt,
                template_id=template_id,
            )
            
            # 加入佇列
            self._tasks[task_id] = task
            self._queue.append(task_id)
            
            log.info(f"任務 {task_id} 已加入排隊，位置: {queue_position}")
            
            # 觸發處理
            self._process_event.set()
            
            return task
    
    async def get_next_task(self) -> Optional[TaskInfo]:
        """
        取得下一個要處理的任務
        """
        async with self._lock:
            # 檢查是否已達最大同時處理數
            if len(self._processing) >= settings.MAX_CONCURRENT_TASKS:
                return None
            
            # 從佇列取出任務
            if not self._queue:
                return None
            
            task_id = self._queue.popleft()
            task = self._tasks.get(task_id)
            
            if task:
                self._processing.add(task_id)
                task.status = TaskStatus.PENDING
                task.queue_position = None
                task.estimated_wait_seconds = 0
                task.started_at = datetime.now()
                
                # 更新其他任務的排隊位置
                self._update_queue_positions()
                
                log.info(f"任務 {task_id} 開始處理")
            
            return task
    
    async def complete_task(self, task_id: str, success: bool = True, error_message: str = None):
        """
        標記任務完成
        """
        async with self._lock:
            if task_id in self._processing:
                self._processing.remove(task_id)
            
            task = self._tasks.get(task_id)
            if task:
                task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
                task.completed_at = datetime.now()
                task.progress = 100.0 if success else task.progress
                if error_message:
                    task.error_message = error_message
                
                log.info(f"任務 {task_id} 完成，狀態: {task.status}")
            
            # 觸發處理下一個任務
            self._process_event.set()
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任務
        """
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            
            # 如果任務正在處理中，無法取消
            if task_id in self._processing:
                log.warning(f"任務 {task_id} 正在處理中，無法取消")
                return False
            
            # 如果任務在排隊中，從佇列移除
            if task_id in self._queue:
                self._queue.remove(task_id)
                self._update_queue_positions()
            
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            
            log.info(f"任務 {task_id} 已取消")
            return True
    
    def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """取得任務資訊"""
        return self._tasks.get(task_id)
    
    def update_task_progress(self, task_id: str, progress: float, stage: str, status: TaskStatus = None):
        """更新任務進度"""
        task = self._tasks.get(task_id)
        if task:
            task.progress = progress
            task.stage = stage
            if status:
                task.status = status
    
    def get_queue_status(self) -> QueueStatus:
        """取得排隊狀態"""
        total_queued = len(self._queue)
        processing_count = len(self._processing)
        estimated_wait = self._calculate_wait_time(total_queued + 1)
        
        return QueueStatus(
            total_queued=total_queued,
            processing_count=processing_count,
            estimated_wait_seconds=estimated_wait,
            max_concurrent=settings.MAX_CONCURRENT_TASKS,
            queue_max_size=settings.QUEUE_MAX_SIZE
        )
    
    def get_task_position(self, task_id: str) -> Optional[int]:
        """取得任務在佇列中的位置"""
        try:
            return list(self._queue).index(task_id) + 1
        except ValueError:
            return None
    
    def _calculate_wait_time(self, position: int) -> int:
        """計算預估等待時間（秒）"""
        if position <= 0:
            return 0
        # 每個任務預估處理時間（秒）
        time_per_task = settings.ESTIMATED_MINUTES_PER_TASK * 60
        # 考慮同時處理數
        effective_position = max(0, position - settings.MAX_CONCURRENT_TASKS)
        return effective_position * time_per_task
    
    def _update_queue_positions(self):
        """更新所有排隊任務的位置"""
        for i, task_id in enumerate(self._queue):
            task = self._tasks.get(task_id)
            if task:
                task.queue_position = i + 1
                task.estimated_wait_seconds = self._calculate_wait_time(i + 1)
    
    async def wait_for_task(self):
        """等待有任務可處理"""
        await self._process_event.wait()
        self._process_event.clear()
    
    def get_all_tasks(self) -> List[TaskInfo]:
        """取得所有任務"""
        return list(self._tasks.values())


# 全域任務佇列管理器
task_queue = TaskQueueManager()
