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


MISSING_TEXT = "逐字稿未提及"

# 英文前言/分析句首樣式：這些行即使夾帶少量中文也應整行移除，
# 用以攔截模型在會議紀錄前輸出的英文推理段（如 "Analysis of the Transcript"）。
_ENGLISH_PREAMBLE_RE = re.compile(
    r"^(?:Analysis of the Transcript|Evaluation Criteria|Let'?s\b|Here'?s\b|"
    r"Below is\b|Okay[,，]?\s*(?:let|here)|Sure[,，]?\b)",
    re.IGNORECASE,
)


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
            cache_signature = file_manager.get_asr_cache_signature()
            cached_transcript = file_manager.get_cached_transcript(file_hash, cache_signature)
            
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
                file_manager.save_transcript_cache(file_hash, transcript, cache_signature)
            
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

            # 保護含「（待確認）」的行，避免被英文比例規則誤刪（合法的缺漏標記）。
            if "（待確認）" in stripped:
                cleaned_lines.append(line)
                continue

            if not stripped or stripped.startswith(('#', '*', '|', '-', '>')):
                cleaned_lines.append(line)
                continue

            # 英文前言/分析句首：整行移除（即使夾帶少量中文），攔截英文推理段殘留。
            if _ENGLISH_PREAMBLE_RE.match(stripped):
                log.warning(f"[清理] 移除英文前言行: {stripped[:50]}...")
                continue

            if stripped[0].isascii() and stripped[0].isalpha():
                english_words = len(re.findall(r'\b[a-zA-Z]+\b', line))
                total_words = len(line.split())
                cjk_chars = len(re.findall(r'[\u3400-\u9fff]', line))

                if total_words > 0 and english_words / total_words > 0.5 and cjk_chars < 4:
                    log.warning(f"[清理] 移除高英文比例行: {line[:50]}...")
                    continue

            cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines)
    
    @staticmethod
    def _sanitize_text_language(text: str) -> str:
        """淨化文本中的英文詞彙"""
        replacements = {
            r'\bOkay\b': '好',
            r'\bokay\b': '好',
            r'\bSure\b': '好',
            r'\bsure\b': '好',
            r'\bRecap\b': '總結',
            r'\brecap\b': '總結',
            r'\bExecutive Summary\b': '執行摘要',
            r'\bDiscussion & Decisions\b': '詳細議題與決議',
            r'\bAction Items\b': '待辦事項',
            r'\bStand\s*by\b': '待命',
            r'\bstand\s*by\b': '待命',
            r'\$\s*\\rightarrow\s*\$': '→',
            r'\\rightarrow': '→',
        }
        
        result = text
        for pattern, replacement in replacements.items():
            result = re.sub(pattern, replacement, result)
        
        return result
    
    @staticmethod
    def _has_excessive_english(text: str) -> bool:
        """檢查文本中是否有過多英文"""
        normalized = re.sub(r'[#|>*`\-]+', ' ', text)
        cjk_chars = len(re.findall(r'[\u3400-\u9fff]', normalized))
        english_words = len(re.findall(r'\b[a-zA-Z][A-Za-z0-9_/-]*\b', normalized))
        token_count = cjk_chars + english_words
        
        if token_count == 0:
            return False
        
        english_ratio = english_words / token_count
        
        if english_ratio > 0.25:
            log.warning(f"[品質] 檢測到高英文比例: {english_ratio * 100:.1f}% ({english_words}/{token_count} 詞)")
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
        
        # 步驟 3：固定清理常見語言與格式瑕疵，避免低比例英文殘留漏網
        cleaned_summary = self._sanitize_text_language(cleaned_summary)

        # 步驟 4：如果仍有過多英文，保留警示供人工抽查
        if self._has_excessive_english(cleaned_summary):
            log.warning("[品質] 摘要仍含較多英文詞彙，請人工抽查輸出內容")
        
        # 步驟 5：確保 summary 有適當的結構（針對地端模型輸出品質較差的情況）
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

### 使用者附加格式偏好（本次未直接套用至模型輸出）

系統目前仍以固定會議記錄格式生成結果；以下內容僅保留供人工比對參考：

{task.user_prompt}

---

## 原始逐字稿""")
        
        return result

    @staticmethod
    def _strip_section_heading(section_text: str) -> str:
        """移除 section 第一行標題後回傳內容。"""
        lines = section_text.strip().splitlines()
        if not lines:
            return ""
        if re.match(r'^#{1,3}\s*\d', lines[0].strip()):
            return "\n".join(lines[1:]).strip()
        return section_text.strip()

    @staticmethod
    def _build_action_items_table(section_body: str) -> str:
        """將待辦區塊正規化為 Markdown 表格。"""
        lines = [line.rstrip() for line in section_body.splitlines() if line.strip()]

        existing_rows = [
            line.strip()
            for line in lines
            if line.strip().startswith("|") and line.strip().endswith("|")
        ]
        has_header = any("待辦事項" in row and "負責人" in row and "期限" in row for row in existing_rows)
        data_rows = [
            row for row in existing_rows
            if ":---" not in row and "待辦事項" not in row and "事項說明" not in row
        ]

        if has_header and data_rows:
            table_lines = ["| 待辦事項 | 負責人 | 期限 |", "| :--- | :--- | :--- |"]
            for row in data_rows:
                cells = [cell.strip() for cell in row.strip("|").split("|")]
                normalized_cells = (cells + ["（待確認）", "（待確認）", "（待確認）"])[:3]
                table_lines.append(f"| {normalized_cells[0]} | {normalized_cells[1]} | {normalized_cells[2]} |")
            return "\n".join(table_lines)

        bullet_rows: list[str] = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(("- ", "* ")):
                bullet_rows.append(stripped[2:].strip())
            elif re.match(r'^\d+[.)、]\s+', stripped):
                bullet_rows.append(re.sub(r'^\d+[.)、]\s+', '', stripped).strip())

        if bullet_rows:
            unique_rows: list[str] = []
            seen = set()
            for row in bullet_rows:
                key = re.sub(r'\s+', '', row)
                if key and key not in seen:
                    unique_rows.append(row)
                    seen.add(key)

            table_lines = ["| 待辦事項 | 負責人 | 期限 |", "| :--- | :--- | :--- |"]
            table_lines.extend(f"| {row} | （待確認） | （待確認） |" for row in unique_rows)
            return "\n".join(table_lines)

        return "\n".join([
            "| 待辦事項 | 負責人 | 期限 |",
            "| :--- | :--- | :--- |",
            "| （本次會議未明確指派待辦事項） | — | — |",
        ])

    def _normalize_section_content(
        self,
        number: int,
        title: str,
        section_text: str,
        fallback_text: str = ""
    ) -> str:
        """將單一 section 正規化為可用結構。"""
        body = self._strip_section_heading(section_text)

        if number == 1:
            lines = [line for line in body.splitlines() if line.strip()]
            required_fields = {
                "日期": "- **日期**：逐字稿未提及",
                "參與者": "- **參與者**：逐字稿未提及",
                "會議主題": "- **會議主題**：逐字稿未提及",
            }
            existing_text = "\n".join(lines)
            for field, default_line in required_fields.items():
                if field not in existing_text:
                    lines.append(default_line)
            if not lines:
                lines = list(required_fields.values())
            return f"## {number}. {title}\n" + "\n".join(lines).strip()

        if number == 2:
            content = body or fallback_text or "（本次會議主要討論內容，詳見下方議題）"
            return f"## {number}. {title}\n{content.strip()}"

        if number == 3:
            if not body:
                body = (
                    "- **議題 1**：逐字稿未提及\n"
                    "  - *討論重點*：逐字稿摘要資訊不足，請參考原始逐字稿\n"
                    "  - *最終決議*：（待確認）"
                )
            elif "**議題" not in body and "- **議題" not in body:
                compact = " ".join(line.strip("- ").strip() for line in body.splitlines() if line.strip())
                compact = compact or "逐字稿摘要資訊不足，請參考原始逐字稿"
                body = (
                    "- **議題 1**：主要討論事項\n"
                    f"  - *討論重點*：{compact}\n"
                    "  - *最終決議*：（待確認）"
                )
            elif "最終決議" not in body:
                body = body.rstrip() + "\n  - *最終決議*：（待確認）"

            return f"## {number}. {title}\n{body.strip()}"

        if number == 4:
            table = self._build_action_items_table(body)
            return f"## {number}. {title}\n{table}"

        notes_body = body or "- 無"
        if not any(line.strip().startswith("-") for line in notes_body.splitlines() if line.strip()):
            notes_body = f"- {notes_body.strip()}"
        return f"## {number}. {title}\n{notes_body.strip()}"
    
    def _ensure_structure(self, summary: str) -> str:
        """
        確保摘要具有完整的結構
        針對地端模型可能省略某些區塊的情況進行補充
        """
        missing_text = MISSING_TEXT
        default_fallback_line = f"- {missing_text}（主辦單位：{missing_text}，辦理期程：{missing_text}）"
        cleaned = summary.strip()
        if not cleaned:
            cleaned = ""

        cleaned = re.sub(r'^```(?:markdown)?\s*', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\n?```$', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)

        header_lines = []
        section_lines = []
        required_fields = [
            ("會議名稱", missing_text),
            ("會議時間", missing_text),
            ("會議地點", missing_text),
            ("主  席", missing_text),
            ("出席人員", missing_text),
            ("列席人員", "無"),
            ("記  錄", "AI 會議助理"),
        ]
        field_patterns = [
            (field, default, re.compile(rf'^{re.escape(field)}[:：]', re.MULTILINE))
            for field, default in required_fields
        ]
        for field, default, pattern in field_patterns:
            if not pattern.search(cleaned):
                header_lines.append(f"{field}：{default}")

        if "一、 報告事項：" not in cleaned:
            section_lines.extend([
                "一、 報告事項：",
                "無",
            ])

        if "二、 討論事項：" not in cleaned:
            section_lines.extend([
                "二、 討論事項：",
                f"案由：{missing_text}",
                f"說明：{missing_text}",
                "各單位意見（多方立場）：",
                f"- {missing_text}：{missing_text}",
                "決議：",
                f"1. {missing_text}（主辦單位：{missing_text}，協辦單位：{missing_text}）",
            ])
        else:
            if "案由：" not in cleaned:
                section_lines.append(f"案由：{missing_text}")
            if "說明：" not in cleaned:
                section_lines.append(f"說明：{missing_text}")
            if "各單位意見（多方立場）：" not in cleaned:
                section_lines.extend([
                    "各單位意見（多方立場）：",
                    f"- {missing_text}：{missing_text}",
                ])
            if "決議：" not in cleaned:
                section_lines.extend([
                    "決議：",
                    f"1. {missing_text}（主辦單位：{missing_text}，協辦單位：{missing_text}）",
                ])

        if "三、 主席裁示事項（後續管考與追蹤）：" not in cleaned:
            section_lines.extend([
                "三、 主席裁示事項（後續管考與追蹤）：",
                default_fallback_line,
            ])
        elif "辦理期程：" not in cleaned:
            section_lines.append(default_fallback_line)

        if header_lines:
            prefix = "\n".join(header_lines)
            cleaned = f"{prefix}\n\n{cleaned}" if cleaned else prefix

        if section_lines:
            suffix = "\n".join(section_lines)
            cleaned = f"{cleaned}\n\n{suffix}" if cleaned else suffix

        return cleaned.strip()


# 全域任務處理器實例
task_processor = TaskProcessor()
