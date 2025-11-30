"""
MeetingScribe 任務處理器
整合轉錄和摘要服務，執行完整處理流程
"""

import asyncio
import os
import time
from typing import Optional, Callable

from backend.core.config import settings
from backend.core.logger import log
from backend.models.schemas import TaskInfo, TaskStatus, ProcessingMode, TranscriptionResult, ProgressMessage
from backend.services.transcription import transcription_service
from backend.services.summarization import summarization_service
from backend.services.file_manager import file_manager
from backend.services.queue_manager import task_queue
from backend.services.device_detector import device_detector
from backend.api.websocket import connection_manager


class TaskProcessor:
    """
    任務處理器
    執行完整的轉錄和摘要流程
    """
    
    def __init__(self):
        self._running = False
        self._current_task: Optional[TaskInfo] = None
        
    async def _update_progress(self, task_id: str, progress: float, stage: str, status: TaskStatus = None):
        """更新進度並推送 WebSocket"""
        task_queue.update_task_progress(task_id, progress, stage, status)
        
        # 推送 WebSocket 更新
        task = task_queue.get_task(task_id)
        if task:
            queue_status = task_queue.get_queue_status()
            message = ProgressMessage(
                task_id=task_id,
                status=task.status,
                progress=progress,
                stage=stage,
                message=stage,
                eta_seconds=task.estimated_wait_seconds,
                queue_position=task.queue_position,
                queue_total=queue_status.total_queued
            )
            await connection_manager.send_progress(task_id, message)
        
    async def start(self):
        """啟動任務處理器"""
        self._running = True
        log.info("任務處理器已啟動")
        
        while self._running:
            try:
                # 等待有任務可處理
                await task_queue.wait_for_task()
                
                # 取得下一個任務
                task = await task_queue.get_next_task()
                if task:
                    self._current_task = task
                    await self._process_task(task)
                    self._current_task = None
                    
            except asyncio.CancelledError:
                log.info("任務處理器被取消")
                break
            except Exception as e:
                log.error(f"任務處理器錯誤: {e}")
                await asyncio.sleep(1)
    
    async def stop(self):
        """停止任務處理器"""
        self._running = False
        log.info("任務處理器已停止")
    
    async def _process_task(self, task: TaskInfo):
        """處理單一任務"""
        start_time = time.time()
        file_path = None
        
        try:
            log.info(f"開始處理任務: {task.task_id}, 檔案: {task.original_filename}")
            
            # 更新狀態
            await self._update_progress(task.task_id, 5.0, "準備處理", TaskStatus.PENDING)
            
            # 取得檔案路徑（安全地組合路徑）
            # 確保 filename 不包含路徑遍歷字符
            safe_filename = os.path.basename(task.filename)
            file_path = os.path.join(settings.uploads_dir, safe_filename)
            
            # 驗證檔案存在
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"找不到上傳的檔案: {file_path}")
            
            # 計算檔案 hash 並檢查快取
            file_hash = file_manager.get_file_hash(file_path)
            cached_transcript = file_manager.get_cached_transcript(file_hash)
            
            if cached_transcript:
                log.info(f"找到快取的逐字稿: {file_hash}")
                transcript = cached_transcript
                duration = 0.0  # 快取時無法取得時長
                await self._update_progress(task.task_id, 60.0, "使用快取逐字稿", TaskStatus.TRANSCRIBING)
            else:
                # 執行轉錄
                await self._update_progress(task.task_id, 10.0, "載入 Whisper 模型...", TaskStatus.TRANSCRIBING)
                
                # 使用 asyncio 包裝同步轉錄並定期更新進度
                loop = asyncio.get_event_loop()
                
                # 創建一個可以在同步回調中更新異步進度的機制
                async def async_progress_update(progress: float, message: str):
                    await self._update_progress(task.task_id, progress, message)
                
                def sync_progress_cb(progress: float, message: str):
                    # 在事件循環中排程異步更新
                    asyncio.run_coroutine_threadsafe(
                        async_progress_update(progress, message),
                        loop
                    )
                
                transcript, duration = await loop.run_in_executor(
                    None,
                    lambda: transcription_service.transcribe(file_path, sync_progress_cb)
                )
                
                # 驗證轉錄結果
                if not transcript or not transcript.strip():
                    raise RuntimeError("轉錄結果為空")
                
                # 儲存快取
                file_manager.save_transcript_cache(file_hash, transcript)
            
            # 生成摘要
            await self._update_progress(task.task_id, 65.0, "生成摘要", TaskStatus.SUMMARIZING)
            
            async def summarize_progress_cb(progress: float, message: str):
                await self._update_progress(task.task_id, progress, message)
            
            summary = await summarization_service.summarize(
                transcript,
                mode=task.processing_mode,
                user_prompt=task.user_prompt,
                progress_callback=lambda p, m: asyncio.create_task(summarize_progress_cb(p, m))
            )
            
            # 組合最終結果
            result_content = self._format_result(task, transcript, summary)
            
            # 儲存結果
            await file_manager.save_result(task.task_id, task.original_filename, result_content)
            
            # 計算處理時間
            processing_time = time.time() - start_time
            
            # 更新任務完成狀態
            task.progress = 100.0
            task.stage = "完成"
            
            await task_queue.complete_task(task.task_id, success=True)
            
            # 推送完成訊息到 WebSocket
            await self._update_progress(task.task_id, 100.0, "完成", TaskStatus.COMPLETED)
            
            log.info(f"任務 {task.task_id} 處理完成，耗時: {processing_time:.1f}秒")
            
        except Exception as e:
            log.error(f"任務 {task.task_id} 處理失敗: {e}")
            await task_queue.complete_task(task.task_id, success=False, error_message=str(e))
            
            # 推送失敗訊息到 WebSocket
            message = ProgressMessage(
                task_id=task.task_id,
                status=TaskStatus.FAILED,
                progress=0.0,
                stage="失敗",
                message=str(e)
            )
            await connection_manager.send_progress(task.task_id, message)
    
    def _format_result(self, task: TaskInfo, transcript: str, summary: str) -> str:
        """格式化最終結果"""
        device_info = device_detector.get_device_info()
        
        result = f"""# 會議記錄

> 檔案：{task.original_filename}  
> 處理時間：{task.created_at.strftime('%Y-%m-%d %H:%M:%S')}  
> 處理模式：{'本地模式 (Ollama)' if task.processing_mode == ProcessingMode.LOCAL else '雲端模式 (Gemini)'}  
> 運算裝置：{device_info.get('current_device', 'unknown')}  

---

{summary}

---

## 原始逐字稿

<details>
<summary>點擊展開逐字稿</summary>

{transcript}

</details>
"""
        
        if task.user_prompt:
            result = result.replace("---\n\n## 原始逐字稿", f"""---

### 使用者自訂指令

{task.user_prompt}

---

## 原始逐字稿""")
        
        return result


# 全域任務處理器實例
task_processor = TaskProcessor()
