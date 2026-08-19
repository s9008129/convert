"""
任務處理協調器。

負責把「上傳檔案 → 轉錄 → 確定性清理 → 語意校正 → 摘要 → 儲存結果」
串成完整流程，並將進度即時推送到前端畫面。

v4.2 重構重點：
- 新增語意校正層（確定性清理 P1-2 ＋ 選擇性 LLM 校正與同音閘門 P1-3/P1-4）
- 摘要失敗不再偽裝成功：輸出檔案帶顯著警告、進度訊息明示（P0-5）
- 記錄級後處理已移入 summarization（驗證前執行），本模組不再改寫
  已通過驗證的會議紀錄本文（P1-9）
"""

import asyncio
import os
import time
from typing import Optional

from backend.core.config import settings
from backend.core.errors import describe_exception
from backend.core.logger import log
from backend.models.schemas import TaskInfo, TaskStatus, ProcessingMode, ProgressMessage
from backend.services.asr_subprocess import transcribe_isolated
from backend.services.summarization import summarization_service
from backend.services.correction import transcript_correction_service, CorrectionReport
from backend.services.file_manager import file_manager
from backend.services.queue_manager import task_queue
from backend.services.device_detector import device_detector
from backend.api.websocket import connection_manager


SUMMARY_FAILED_BANNER = (
    "> ⚠️ **注意：會議紀錄生成失敗，本檔僅包含逐字稿。**\n"
    "> 請重新送出任務或人工撰寫會議紀錄；勿將本檔直接作為正式會議紀錄使用。"
)


class TaskProcessor:
    """
    任務處理器
    執行完整的轉錄、校正和摘要流程
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
                preview=preview,
                summary_failed=task.summary_failed,
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
                log.exception(f"任務處理器錯誤: {describe_exception(e)}")
                await asyncio.sleep(1)

    async def stop(self):
        """停止任務處理器"""
        self._running = False
        log.info("任務處理器已停止")

    async def _obtain_transcript(self, task: TaskInfo, file_path: str) -> str:
        """取得逐字稿（優先使用快取，否則執行 ASR 轉錄）。"""
        file_hash = file_manager.get_file_hash(file_path)
        cache_signature = file_manager.get_asr_cache_signature()
        cached_transcript = file_manager.get_cached_transcript(file_hash, cache_signature)

        if cached_transcript:
            log.info(f"找到快取的逐字稿: {file_hash}")
            await self._update_progress(task.task_id, 60.0, "使用快取逐字稿", TaskStatus.TRANSCRIBING)
            return cached_transcript

        # 單卡 VRAM 競爭：ASR 開跑前主動請 Ollama 釋放常駐模型，
        # 避免 keep_alive（P0-7）讓 ASR 因 VRAM 不足降級 CPU
        await summarization_service.release_local_model()

        await self._update_progress(task.task_id, 10.0, "載入 Whisper 模型...", TaskStatus.TRANSCRIBING)

        # v4.7.0：ASR 預設走獨立子程序（backend/services/asr_subprocess.py）——
        # 程序退出保證 CUDA context／分配器殘留完全釋回，Ollama 之後載入
        # 才看得到乾淨的可用 VRAM（offload 根因之一）
        async def async_progress_update(progress: float, message: str):
            await self._update_progress(task.task_id, progress, message)

        transcript, _duration = await transcribe_isolated(file_path, async_progress_update)

        if not transcript or not transcript.strip():
            raise RuntimeError("轉錄結果為空")

        file_manager.save_transcript_cache(file_hash, transcript, cache_signature)
        return transcript

    async def _apply_semantic_correction(self, task: TaskInfo, transcript: str) -> tuple[str, Optional[CorrectionReport]]:
        """語意校正層：確定性清理（P1-2）＋ 選擇性 LLM 校正與同音閘門（P1-3/P1-4）。

        任一步驟失敗都不阻斷主流程，一律退回上一版逐字稿。
        """
        from backend.core.text_postprocess import clean_transcript

        cleaned, stats = clean_transcript(transcript)
        if stats["hallucinations_removed"] or stats["dedup_removed"] or stats["term_fixes"]:
            log.info(
                "確定性清理：移除幻覺 {} 處、重複句 {} 處、公務用字修正 {} 項",
                stats["hallucinations_removed"],
                stats["dedup_removed"],
                len(stats["term_fixes"]),
            )

        if not settings.ENABLE_TRANSCRIPT_CORRECTION or (settings.CORRECTION_SCOPE or "").lower() == "off":
            return cleaned, None

        await self._update_progress(task.task_id, 62.0, "語意校正逐字稿（同音錯字/專有名詞）...")
        try:
            # v4.4.0：注入會議模板術語表（僅 LLM 校正層，不碰 ASR hotwords／快取）
            from backend.core.templates import template_glossary_block

            corrected, report = await transcript_correction_service.correct_transcript(
                cleaned,
                lambda system_prompt, user_message: summarization_service.generate_local(
                    system_prompt, user_message, temperature=0.0
                ),
                extra_glossary_block=template_glossary_block(task.template_id),
            )
            return corrected, report
        except Exception as exc:  # noqa: BLE001
            # 校正層與摘要層共用本地 LLM——這裡的失敗常是摘要失敗的早期警訊，
            # 訊息必須完整（timeout 類例外 str() 為空，需帶類別名稱）
            log.warning(f"語意校正失敗，沿用清理後逐字稿: {describe_exception(exc)}")
            return cleaned, None

    async def _process_task(self, task: TaskInfo):
        """處理單一任務的完整生命週期，並在失敗時回寫錯誤狀態給前端。"""
        start_time = time.time()

        try:
            log.info(f"開始處理任務: {task.task_id}, 檔案: {task.original_filename}")

            # 更新狀態
            await self._update_progress(task.task_id, 5.0, "準備處理", TaskStatus.PENDING)

            # 取得檔案路徑（安全地組合路徑）
            safe_filename = os.path.basename(task.filename)
            file_path = os.path.join(settings.uploads_dir, safe_filename)

            if not os.path.exists(file_path):
                raise FileNotFoundError(f"找不到上傳的檔案: {file_path}")

            # 步驟 1：轉錄（含快取）
            transcript = await self._obtain_transcript(task, file_path)

            # 步驟 1.5：預熱本地 LLM（v4.6.2）
            # ASR 前已強制卸載 Ollama 模型（VRAM 交接），這裡先以 load-only
            # 請求把冷載入時間從後續生成呼叫的 timeout 額度中拆出，
            # 並記錄 CPU offload 狀態供正式機診斷。
            needs_local_llm = task.processing_mode == ProcessingMode.LOCAL or (
                settings.ENABLE_TRANSCRIPT_CORRECTION
                and (settings.CORRECTION_SCOPE or "").lower() != "off"
            )
            if needs_local_llm:
                await self._update_progress(task.task_id, 61.0, "載入本地模型...")
                await summarization_service.warmup_local_model()

            # 步驟 2：語意校正（確定性清理 ＋ LLM 校正）
            transcript, correction_report = await self._apply_semantic_correction(task, transcript)

            # 步驟 2.5：逐字稿另存為獨立檔案（v4.2.2 前端可單獨下載）
            try:
                await file_manager.save_transcript_result(task.task_id, task.original_filename, transcript)
            except Exception as exc:  # noqa: BLE001
                log.warning(f"逐字稿獨立檔儲存失敗（不影響主流程）: {exc}")

            # 步驟 3：生成會議紀錄
            await self._update_progress(task.task_id, 65.0, "生成摘要", TaskStatus.SUMMARIZING)

            def sync_progress_cb(progress: float, message: str):
                asyncio.run_coroutine_threadsafe(
                    self._update_progress(task.task_id, progress, message),
                    asyncio.get_event_loop()
                )

            summary = None
            summary_error: Optional[str] = None
            try:
                summary = await summarization_service.summarize(
                    transcript,
                    mode=task.processing_mode,
                    user_prompt=task.user_prompt,
                    progress_callback=sync_progress_cb,
                    template_id=task.template_id,
                )
            except Exception as e:
                # P0-5：摘要失敗不偽裝成功——保留逐字稿輸出，但以顯著警告標示
                # v4.6.2：timeout 類例外 str() 為空，必須帶類別名稱＋完整 traceback
                summary_error = describe_exception(e)
                task.summary_failed = True
                log.exception(f"摘要生成失敗（輸出將明確標示為僅逐字稿）: {summary_error}")
                await self._update_progress(task.task_id, 70.0, f"⚠️ 會議紀錄生成失敗，輸出僅含逐字稿: {summary_error[:50]}")

            # 步驟 4：組合最終結果
            result_content = self._format_result(
                task,
                transcript,
                summary,
                correction_report=correction_report,
                summary_error=summary_error,
            )

            await file_manager.save_result(task.task_id, task.original_filename, result_content)

            processing_time = time.time() - start_time

            task.progress = 100.0
            final_stage = "完成" if summary else "完成（⚠️ 僅逐字稿，會議紀錄生成失敗）"
            task.stage = final_stage

            await task_queue.complete_task(task.task_id, success=True)

            await self._update_progress(task.task_id, 100.0, final_stage, TaskStatus.COMPLETED, preview=result_content)

            log.info(f"任務 {task.task_id} 處理完成，耗時: {processing_time:.1f}秒")

        except Exception as e:
            error_text = describe_exception(e)
            log.exception(f"任務 {task.task_id} 處理失敗: {error_text}")
            await task_queue.complete_task(task.task_id, success=False, error_message=error_text)

            message = ProgressMessage(
                task_id=task.task_id,
                status=TaskStatus.FAILED,
                progress=0.0,
                stage="失敗",
                message=error_text
            )
            await connection_manager.send_progress(task.task_id, message)

    def _format_result(
        self,
        task: TaskInfo,
        transcript: str,
        summary: Optional[str] = None,
        correction_report: Optional[CorrectionReport] = None,
        summary_error: Optional[str] = None,
    ) -> str:
        """整理最終輸出內容。

        會議紀錄本文在 summarization 已完成「後處理→驗證」（P1-9），
        此處只負責包裝標題與失敗警告，不再改寫紀錄本文。

        v4.2.3：交付文件只保留會議紀錄本文——處理資訊（檔案/時間/模式/裝置）
        與語意校正對照表改記錄於 log；逐字稿由「下載逐字稿」獨立提供，
        不再附錄於文件內。
        """
        if not device_detector.current_device:
            device_detector.detect_best_device()
        device_info = device_detector.get_device_info()

        summary_failed = not summary
        body = summary if summary else transcript

        log.info(
            f"任務 {task.task_id} 處理資訊: 檔案={task.original_filename}, "
            f"處理時間={task.created_at.strftime('%Y-%m-%d %H:%M:%S')}, "
            f"模式={'本地 (Ollama)' if task.processing_mode == ProcessingMode.LOCAL else '雲端 (Gemini)'}, "
            f"會議模板={task.template_id}, "
            f"裝置={device_info.get('current_device', 'unknown')}"
        )
        if correction_report and correction_report.accepted_changes:
            log.info(
                f"任務 {task.task_id} 語意校正對照表（僅記錄於 log，供人工複核）:\n"
                f"{correction_report.to_markdown()}"
            )

        from backend.core.templates import get_template

        title = get_template(task.template_id).result_title
        sections: list[str] = []

        if summary_failed:
            title = "# 逐字稿（會議紀錄生成失敗）"
            failure_note = SUMMARY_FAILED_BANNER
            # v4.6.2：失敗原因行無條件輸出——空訊息例外曾讓此行整個消失
            reason = summary_error or "未知錯誤（無例外訊息）"
            failure_note += f"\n> 失敗原因：{reason[:200]}"
            sections.append(failure_note)

        sections.append(body)

        result = f"{title}\n\n" + "\n\n".join(sections) + "\n"

        if task.user_prompt:
            result += (
                "\n---\n\n"
                "### 使用者附加格式偏好（本次未直接套用至模型輸出）\n\n"
                "系統目前仍以固定會議記錄格式生成結果；以下內容僅保留供人工比對參考：\n\n"
                f"{task.user_prompt}\n"
            )

        return result


# 全域任務處理器實例
task_processor = TaskProcessor()
