"""
任務處理協調器。

負責把「上傳檔案 → 轉錄 → 摘要 → 儲存結果」串成完整流程，
並將進度即時推送到前端畫面。
"""

import asyncio
import os
import time
import re
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
        """初始化處理器狀態，記錄目前是否運行與當前正在處理的任務。"""
        self._running = False
        self._current_task: Optional[TaskInfo] = None
        
    async def _update_progress(self, task_id: str, progress: float, stage: str, status: TaskStatus = None, preview: str = None):
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
                queue_total=queue_status.total_queued,
                preview=preview
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
        """處理單一任務的完整生命週期，並在失敗時回寫錯誤狀態給前端。"""
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
            
            # 定義同步進度回調（不使用 asyncio.create_task）
            def sync_progress_cb(progress: float, message: str):
                """同步進度回調，直接使用 run_coroutine_threadsafe"""
                asyncio.run_coroutine_threadsafe(
                    self._update_progress(task.task_id, progress, message),
                    asyncio.get_event_loop()
                )
            
            summary = None
            try:
                summary = await summarization_service.summarize(
                    transcript,
                    mode=task.processing_mode,
                    user_prompt=task.user_prompt,
                    progress_callback=sync_progress_cb
                )
            except Exception as e:
                # 摘要生成失敗時，仍然返回逐字稿（不讓整個任務失敗）
                log.warning(f"摘要生成失敗 (將使用逐字稿作為結果): {e}")
                await self._update_progress(task.task_id, 70.0, f"摘要生成失敗，使用逐字稿: {str(e)[:50]}")
                summary = None
            
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
            
            # 推送完成訊息到 WebSocket（包含結果預覽）
            await self._update_progress(task.task_id, 100.0, "完成", TaskStatus.COMPLETED, preview=result_content)
            
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
    
    @staticmethod
    def _remove_english_segments(text: str) -> str:
        """移除或修復包含過多英文的段落"""
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            stripped = line.lstrip()
            
            if stripped and stripped[0].isascii() and stripped[0].isalpha():
                # 保留 Markdown 標題和特殊符號開頭的行
                if stripped.startswith('#') or stripped.startswith('*') or \
                   stripped.startswith('|') or stripped.startswith('-') or \
                   stripped.startswith('>'):
                    cleaned_lines.append(line)
                else:
                    # 檢查英文詞的比例
                    english_words = len(re.findall(r'\b[a-zA-Z]+\b', line))
                    total_words = len(line.split())
                    
                    if total_words > 0 and english_words / total_words > 0.5:
                        # 英文比例過高，跳過此行
                        log.warning("[清理] 移除高英文比例行: %s...", line[:50])
                        continue
            
            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    @staticmethod
    def _sanitize_text_language(text: str) -> str:
        """淨化文本中的英文詞彙"""
        replacements = {
            r'\bOkay\b': '好',
            r'\bokay\b': '好',
            r'\bLet\b': '讓',
            r'\blet\b': '讓',
            r'\bRecap\b': '總結',
            r'\brecap\b': '總結',
            r'\bAI\b': '人工智慧',
            r'\bRPA\b': '流程自動化',
            r'\bPOC\b': '概念驗證',
            r'\bKPI\b': '關鍵績效指標',
            r'\bCEO\b': '首席執行官',
            r'\bEdge\b': '邊緣',
            r'\bOllama\b': '本地模型系統',
            r'\bCPU\b': '中央處理器',
            r'\bGPU\b': '圖形處理器',
            r'\bAPI\b': '應用介面',
            r'\bJSON\b': '資料格式',
            r'\bSQL\b': '結構化查詢',
            r'\bURL\b': '網址',
            r'\bID\b': '識別碼',
            r'\bDI\b': '數位身份',
        }
        
        result = text
        for pattern, replacement in replacements.items():
            result = re.sub(pattern, replacement, result)
        
        return result
    
    @staticmethod
    def _has_excessive_english(text: str) -> bool:
        """檢查文本中是否有過多英文"""
        english_words = len(re.findall(r'\b[a-zA-Z]+\b', text))
        total_words = len(text.split())
        
        if total_words == 0:
            return False
        
        english_ratio = english_words / total_words
        
        if english_ratio > 0.15:
            log.warning(
                "[品質] 檢測到高英文比例: %.1f%% (%d/%d 詞)",
                english_ratio * 100, 
                english_words, 
                total_words
            )
            return True
        
        return False

    def _format_result(self, task: TaskInfo, transcript: str, summary: str = None) -> str:
        """整理最終輸出內容（含語言清理與結構保護），讓結果更容易閱讀。"""
        # 確保設備偵測已執行，避免顯示 unknown
        if not device_detector.current_device:
            device_detector.detect_best_device()
        device_info = device_detector.get_device_info()
        
        # 如果 summary 為 None（摘要生成失敗），使用逐字稿
        if not summary:
            log.warning("摘要為空，將使用逐字稿作為結果")
            summary = transcript
        
        # 步驟 1：檢查 summary 是否已包含標準 header
        # 避免重複添加 header
        has_standard_header = summary.strip().startswith("# 會議記錄")
        
        # 步驟 2：移除高英文比例的段落
        cleaned_summary = self._remove_english_segments(summary)
        
        # 步驟 3：如果仍有過多英文，執行詞彙替換
        if self._has_excessive_english(cleaned_summary):
            log.warning("[修正] 偵測到英文混入，執行詞彙替換...")
            cleaned_summary = self._sanitize_text_language(cleaned_summary)
        
        # 步驟 4：確保 summary 有適當的結構（針對地端模型輸出品質較差的情況）
        cleaned_summary = self._ensure_structure(cleaned_summary)
        
        # 如果 summary 已經有標準 header，就不要再加
        if has_standard_header:
            result = f"""{cleaned_summary}

---

## 原始逐字稿

<details>
<summary>點擊展開逐字稿</summary>

{transcript}

</details>
"""
        else:
            result = f"""# 會議記錄

> 檔案：{task.original_filename}  
> 處理時間：{task.created_at.strftime('%Y-%m-%d %H:%M:%S')}  
> 處理模式：{'本地模式 (Ollama)' if task.processing_mode == ProcessingMode.LOCAL else '雲端模式 (Gemini)'}  
> 運算裝置：{device_info.get('current_device', 'unknown').upper() if device_info.get('gpu_available') or device_info.get('mps_available') else device_info.get('current_device', 'cpu').upper()}  

---

{cleaned_summary}

---

## 原始逐字稿

<details>
<summary>點擊展開逐字稿</summary>

{transcript}

</details>
"""
        
        if task.user_prompt:
            result = result.replace("---\n\n## 原始逐字稿", f"""---

### 使用者自訂會議記錄格式

{task.user_prompt}

---

## 原始逐字稿""")
        
        return result
    
    def _ensure_structure(self, summary: str) -> str:
        """
        確保摘要具有完整的結構
        針對地端模型可能省略某些區塊的情況進行補充
        """
        required_sections = [
            ("## 1. 會議概況", "## 1. 會議概況\n- **日期**：（逐字稿未提及）\n- **參與者**：（逐字稿未提及）\n- **會議主題**：（待補充）\n"),
            ("## 2. 執行摘要", "## 2. 執行摘要 (Executive Summary)\n（本次會議主要討論內容，詳見下方議題）\n"),
            ("## 4. 待辦事項", "## 4. 待辦事項 (Action Items) - 必填\n| 待辦事項 | 負責人 | 期限 |\n| :--- | :--- | :--- |\n| （待確認） | （待確認） | （待確認） |\n"),
            ("## 5. 其他備註", "## 5. 其他備註\n- 無\n"),
        ]
        
        result = summary
        
        for section_marker, default_content in required_sections:
            # 檢查是否缺少此區塊（允許一些變化）
            section_variations = [
                section_marker,
                section_marker.replace(".", ""),
                section_marker.replace("##", "#"),
            ]
            
            found = False
            for variation in section_variations:
                if variation in result:
                    found = True
                    break
            
            # 如果缺少區塊，在適當位置添加
            if not found:
                log.warning(f"[補充] 摘要缺少區塊: {section_marker}")
                # 找到插入位置：在下一個區塊之前
                # 暫時不自動插入，避免打亂順序
                pass
        
        return result


# 全域任務處理器實例
task_processor = TaskProcessor()
