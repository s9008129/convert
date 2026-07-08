"""
MeetingScribe WebSocket 即時進度推送。

當使用者上傳檔案後，前端會透過這裡即時收到排隊、轉錄、摘要與完成通知。
"""

import asyncio
import os
from typing import Dict, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect

from backend.core.logger import log
from backend.core.config import settings
from backend.models.schemas import ProgressMessage, TaskStatus
from backend.services import task_queue

# v4.3.2：推送給使用者的狀態一律中文（原本直接吐出英文 enum 值，
# 造成畫面「一下中文一下英文」）
STATUS_LABELS = {
    TaskStatus.QUEUED: "排隊等候中",
    TaskStatus.PENDING: "準備處理中",
    TaskStatus.UPLOADING: "檔案上傳中",
    TaskStatus.TRANSCRIBING: "語音轉錄中",
    TaskStatus.SUMMARIZING: "生成會議紀錄中",
    TaskStatus.COMPLETED: "處理完成",
    TaskStatus.FAILED: "處理失敗",
    TaskStatus.CANCELLED: "已取消",
}


def status_label(status: TaskStatus) -> str:
    """把任務狀態轉成使用者看得懂的中文標籤。"""
    return STATUS_LABELS.get(status, str(status.value))


def _get_result_preview(task_id: str, original_filename: str) -> Optional[str]:
    """
    讀取任務結果的前段預覽文字。

    若檔案尚未產生或讀取失敗，會安全地回傳 None，避免中斷整個 WebSocket 流程。
    """
    try:
        base_name = os.path.splitext(os.path.basename(original_filename))[0]
        safe_base_name = "".join(c for c in base_name if c.isalnum() or c in ('_', '-', ' ', '.') or '\u4e00' <= c <= '\u9fff')
        result_filename = f"{safe_base_name}_{task_id}.md"
        result_path = os.path.join(settings.outputs_dir, result_filename)
        
        if os.path.exists(result_path):
            with open(result_path, 'r', encoding='utf-8') as f:
                result_content = f.read()
                maxLength = 2000
                return result_content[:maxLength] if len(result_content) > maxLength else result_content
    except Exception as e:
        log.warning(f"無法讀取結果預覽: {e}")
    
    return None


class ConnectionManager:
    """
    WebSocket 連接管理器
    管理所有活躍的 WebSocket 連接
    """
    
    def __init__(self):
        """初始化連線池，依任務編號分組保存目前連線中的前端頁面。"""
        self._connections: Dict[str, Set[WebSocket]] = {}  # task_id -> WebSocket 集合
        
    async def connect(self, websocket: WebSocket, task_id: str):
        """接受新的 WebSocket 連接，讓前端能持續收到該任務的進度。"""
        await websocket.accept()
        
        if task_id not in self._connections:
            self._connections[task_id] = set()
        self._connections[task_id].add(websocket)
        
        log.debug(f"WebSocket 連接建立: {task_id}")
    
    def disconnect(self, websocket: WebSocket, task_id: str):
        """移除中斷或離線的 WebSocket 連接，避免保留失效連線。"""
        if task_id in self._connections:
            self._connections[task_id].discard(websocket)
            if not self._connections[task_id]:
                del self._connections[task_id]
        
        log.debug(f"WebSocket 連接斷開: {task_id}")
    
    async def send_progress(self, task_id: str, message: ProgressMessage):
        """發送進度訊息到特定任務的所有連接"""
        if task_id not in self._connections:
            return
        
        dead_connections = set()
        
        for websocket in self._connections[task_id]:
            try:
                await websocket.send_json(message.model_dump())
            except (WebSocketDisconnect, RuntimeError, ConnectionResetError, BrokenPipeError) as e:
                # 客戶端已斷開連接，標記為失效
                log.debug(f"WebSocket 發送失敗 ({type(e).__name__}): {task_id}")
                dead_connections.add(websocket)
            except Exception as e:
                # 其他未預期的錯誤
                log.warning(f"WebSocket 發送時發生未預期錯誤: {e}")
                dead_connections.add(websocket)
        
        # 清理失效連接
        for websocket in dead_connections:
            self.disconnect(websocket, task_id)
    
    async def broadcast_queue_update(self):
        """廣播排隊狀態更新到所有連接"""
        queue_status = task_queue.get_queue_status()
        
        for task_id, connections in self._connections.items():
            task = task_queue.get_task(task_id)
            if task and task.status == TaskStatus.QUEUED:
                # 確保 queue_position 更新為最新值
                current_position = task_queue.get_task_position(task_id)
                message = ProgressMessage(
                    task_id=task_id,
                    status=task.status,
                    progress=task.progress,
                    stage=task.stage,
                    message="排隊中",
                    queue_position=current_position or task.queue_position,
                    queue_total=queue_status.total_queued
                )
                await self.send_progress(task_id, message)


# 全域連接管理器
connection_manager = ConnectionManager()


async def websocket_endpoint(websocket: WebSocket, task_id: str):
    """
    WebSocket 端點
    即時推送任務處理進度
    """
    await connection_manager.connect(websocket, task_id)
    
    try:
        # 立即發送當前狀態
        task = task_queue.get_task(task_id)
        if task:
            queue_status = task_queue.get_queue_status()
            
            # 如果任務已完成，取得結果預覽
            preview = None
            if task.status == TaskStatus.COMPLETED:
                preview = _get_result_preview(task_id, task.original_filename)
            
            message = ProgressMessage(
                task_id=task_id,
                status=task.status,
                progress=task.progress,
                stage=task.stage,
                message=status_label(task.status),
                eta_seconds=task.estimated_wait_seconds,
                queue_position=task.queue_position,
                queue_total=queue_status.total_queued,
                preview=preview
            )
            try:
                await websocket.send_json(message.model_dump())
            except (RuntimeError, ConnectionResetError, BrokenPipeError) as e:
                log.warning(f"初始狀態發送失敗 ({type(e).__name__}): {task_id}")
                return
        
        # 保持連接並定期發送更新
        while True:
            try:
                # 等待客戶端訊息（心跳）或超時
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=30.0
                )
                
                # 處理心跳
                if data == "ping":
                    try:
                        await websocket.send_text("pong")
                    except (RuntimeError, ConnectionResetError, BrokenPipeError):
                        log.debug(f"心跳回應失敗，連線已中斷: {task_id}")
                        break
                
            except asyncio.TimeoutError:
                # 超時，發送當前狀態
                task = task_queue.get_task(task_id)
                if task:
                    queue_status = task_queue.get_queue_status()
                    
                    # 如果任務已完成，取得結果預覽
                    preview = None
                    if task.status == TaskStatus.COMPLETED:
                        preview = _get_result_preview(task_id, task.original_filename)
                    
                    message = ProgressMessage(
                        task_id=task_id,
                        status=task.status,
                        progress=task.progress,
                        stage=task.stage,
                        message=task.stage,
                        eta_seconds=task.estimated_wait_seconds,
                        queue_position=task.queue_position,
                        queue_total=queue_status.total_queued,
                        preview=preview
                    )
                    try:
                        await websocket.send_json(message.model_dump())
                    except (RuntimeError, ConnectionResetError, BrokenPipeError):
                        log.debug(f"狀態更新發送失敗，連線已中斷: {task_id}")
                        break
                    
                    # 如果任務已完成，關閉連接
                    if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
                        break
                        
    except WebSocketDisconnect:
        log.debug(f"WebSocket 客戶端斷開: {task_id}")
    except (RuntimeError, ConnectionResetError, BrokenPipeError) as e:
        log.debug(f"WebSocket 連線錯誤 ({type(e).__name__}): {task_id}")
    except Exception as e:
        log.error(f"WebSocket 處理時發生未預期錯誤: {e}")
    finally:
        connection_manager.disconnect(websocket, task_id)
