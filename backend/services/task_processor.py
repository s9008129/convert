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
from backend.core.asr_model_resolver import resolve_engine_chain
from backend.core.errors import describe_exception
from backend.core.logger import log
from backend.models.schemas import TaskInfo, TaskStatus, ProcessingMode, ProgressMessage
from backend.services.asr_subprocess import transcribe_isolated_detailed
from backend.services.summarization import summarization_service
from backend.services.correction import transcript_correction_service, CorrectionReport
from backend.services.file_manager import file_manager
from backend.services.queue_manager import task_queue
from backend.services.device_detector import device_detector
from backend.api.websocket import connection_manager
from backend.services.diarization import DiarizationTurn, diarization_service
from backend.services.speaker_transcript import AsrPiece, build_speaker_labeled_transcript


SUMMARY_FAILED_BANNER = (
    "> ⚠️ **注意：會議紀錄生成失敗，本檔僅包含逐字稿。**\n"
    "> 請重新送出任務或人工撰寫會議紀錄；勿將本檔直接作為正式會議紀錄使用。"
)


def _asr_stage_message() -> str:
    """轉錄起始進度文案：本次解析鏈的第一個引擎是 apple 時不宣稱載入 Whisper。

    文案屬觀測/UX 層（非 gating）：解析失敗一律回退既有 Whisper 文案，
    絕不讓文案解析成為轉錄的新失敗點；Windows／其他後端文案不變。
    """
    try:
        chain = resolve_engine_chain(settings.ASR_BACKEND, settings.WHISPER_MODEL)
    except Exception as exc:  # noqa: BLE001 — 文案解析不得擋轉錄
        log.debug(f"ASR 引擎鏈解析失敗（進度文案回退 Whisper 文案）: {describe_exception(exc)}")
        return "載入 Whisper 模型..."
    if chain and chain[0] == "apple":
        return "Apple 本機轉錄中…"
    return "載入 Whisper 模型..."


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

        await self._update_progress(
            task.task_id, 10.0, _asr_stage_message(), TaskStatus.TRANSCRIBING
        )

        # v4.7.0：ASR 預設走獨立子程序（backend/services/asr_subprocess.py）——
        # 程序退出保證 CUDA context／分配器殘留完全釋回，Ollama 之後載入
        # 才看得到乾淨的可用 VRAM（offload 根因之一）
        async def async_progress_update(progress: float, message: str):
            await self._update_progress(task.task_id, progress, message)

        transcription_result = await transcribe_isolated_detailed(file_path, async_progress_update)
        transcript = transcription_result.text

        if not transcript or not transcript.strip():
            raise RuntimeError("轉錄結果為空")

        # 步驟 1.4：發言者標註（說話者分離；T20260913-1900-01）
        # 加值層、fail-soft：任何失敗都回 None，逐字稿維持純文字（既有行為）。
        labeled_transcript = await self._label_speakers(task, file_path, transcription_result)
        if labeled_transcript:
            transcript = labeled_transcript
            cache_signature_to_save = cache_signature
        else:
            # fail-soft 契約（SI-D1）：這次沒標註成功時，只把逐字稿寫進
            # 「無標註」的 key；否則模型／資源恢復後會命中這份沒有標籤的
            # 快取，永遠不再嘗試說話者分離。
            cache_signature_to_save = file_manager.get_unlabeled_asr_cache_signature()

        file_manager.save_transcript_cache(file_hash, transcript, cache_signature_to_save)
        return transcript

    async def _label_speakers(self, task: TaskInfo, file_path: str, transcription_result) -> Optional[str]:
        """以說話者分離結果標註逐字稿的發言者（失敗一律回 None，不影響任務）。

        需要兩個前提：ASR 有**可用的** segment 時間戳、diarization 可用。
        任一缺少即維持現行純文字逐字稿——這是 diarization 的 fail-soft 契約
        （SI-D1）。
        """
        try:
            chunks = list(getattr(transcription_result, "chunks", None) or [])
            if not chunks:
                log.info("ASR 未提供 segment 時間戳，略過發言者標註")
                return None

            # 時間軸守門（必須在 diarization 之前）：ASR（尤其 Apple）允許
            # start/end 為 null 的降級片段，這些片段在 transcription.py 會被
            # 填成 0.0。若整體時間軸不可用，對位出來的標籤會全部錯誤（比沒有
            # 標籤更糟），此時直接退回純文字，連 diarization 都不必跑。
            pieces = [
                (
                    float(getattr(chunk, "start", 0.0) or 0.0),
                    float(getattr(chunk, "end", 0.0) or 0.0),
                    chunk.text,
                )
                for chunk in chunks
            ]
            usable = [piece for piece in pieces if piece[1] > piece[0]]
            if len(usable) < max(1, len(pieces) // 2):
                log.warning(
                    "ASR 時間軸不可用（僅 {}/{} 段有有效時間區間），略過發言者標註以維持逐字稿正確性",
                    len(usable),
                    len(pieces),
                )
                return None

            await self._update_progress(
                task.task_id, 58.0, "分析發言者（語音分群）...", TaskStatus.TRANSCRIBING
            )
            result = await diarization_service.diarize_async(file_path)
            if not result or not result.turns:
                return None

            segments = [
                AsrPiece(start=start, end=end, text=text) for start, end, text in usable
            ]
            turns = [
                DiarizationTurn(start=turn.start, end=turn.end, speaker=turn.speaker)
                for turn in result.turns
            ]
            labeled = build_speaker_labeled_transcript(
                segments,
                turns,
                merge_gap=settings.DIARIZATION_MERGE_GAP_SECONDS,
                min_segment_coverage=settings.DIARIZATION_MIN_SEGMENT_COVERAGE,
            )
            if not labeled:
                log.info("發言者對位沒有產生任何發言段落，逐字稿維持純文字")
                return None

            log.info(
                "發言者標註完成：{} 位發言者、{} 段發言（diarization {} 段、threshold={}）",
                labeled.speaker_count,
                len(labeled.utterances),
                len(result.turns),
                settings.DIARIZATION_THRESHOLD,
            )
            return labeled.text
        except Exception as exc:  # noqa: BLE001 — 標註失敗永不影響任務
            log.warning(f"發言者標註失敗（不影響任務）：{describe_exception(exc)}")
            return None

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
                    system_prompt, user_message, temperature=0.0, allow_reasoning_retry=False
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
            # Keep immutable ASR output alongside the existing corrected view.
            # Only local V2 consumes this optional argument; legacy/cloud paths
            # continue receiving the same `transcript` value as before.
            raw_source_transcript = transcript

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
                    raw_source_transcript=raw_source_transcript,
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
        local_provider = summarization_service.get_local_llm_health().get("provider", "local")
        local_provider_label = {
            "lmstudio": "LM Studio",
            "ollama": "Ollama",
        }.get(local_provider, local_provider)
        mode_label = (
            f"本地 ({local_provider_label})"
            if task.processing_mode == ProcessingMode.LOCAL
            else f"雲端 ({settings.cloud_llm_provider_label})"
        )

        log.info(
            f"任務 {task.task_id} 處理資訊: 檔案={task.original_filename}, "
            f"處理時間={task.created_at.strftime('%Y-%m-%d %H:%M:%S')}, "
            f"模式={mode_label}, "
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
