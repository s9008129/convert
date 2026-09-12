"""
對外 API 路由。

這裡定義前端會呼叫的功能：健康檢查、上傳檔案、查詢任務進度、下載結果與儲存空間管理。
v3.5.4 - 統一版本號 + 裝置狀態快取
"""

import os
import platform
import time
import inspect
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from backend.core.asr_model_resolver import infer_asr_backend, resolve_asr_model, resolve_model_revision
from backend.core.config import settings
from backend.core.logger import log
from backend.core.templates import GENERAL_TEMPLATE_ID, get_template, template_public_info
from backend.core.version import __version__
from backend.models.schemas import (
    TaskStatus, ProcessingMode, TaskInfo, QueueStatus,
    UploadResponse, HealthStatus, ErrorResponse
)
from backend.services import (
    device_detector, task_queue, file_manager,
    summarization_service
)

router = APIRouter(prefix="/api", tags=["API"])

_BUILD_REVISION_ENV = "MEETINGSCRIBE_BUILD_REVISION"


def _resolve_build_revision() -> Optional[str]:
    """RC-5 runtime provenance：build revision 來源優先序 settings → 環境變數。

    空值（未設定或空白）視為 unknown，以 null 呈現；一般 health 不因
    unknown revision 失敗，revision mismatch 只由 E2E harness 判定。
    """
    value = getattr(settings, "MEETINGSCRIBE_BUILD_REVISION", None) or os.environ.get(_BUILD_REVISION_ENV)
    if isinstance(value, str):
        value = value.strip()
    return value or None


_APPLE_HELPER_REASON_NOT_MACOS = "非 macOS：Apple SpeechAnalyzer 僅支援 macOS"


def _load_apple_helper_status():
    """延後載入 Apple helper 狀態函式（WAVE-03 凍結介面）。

    ``apple_helper_status(*, configured_path=None) -> dict``。以函式包裝讓
    ``/health`` 在 Apple 模組載入失敗時仍可回報可觀察原因（BE-03，永不讓
    health 失敗），並讓測試能在不載入 Apple 模組的前提下替換此 seam。
    """
    from backend.services.asr_apple.apple import apple_helper_status

    return apple_helper_status


def _apple_helper_health_section(*, quick: bool) -> dict:
    """Apple ASR helper 可觀測區段（REQ-10；additive、best-effort、不 gating）。

    - 非 macOS：最早分支返回 ``supported=false``——不載入 Apple 模組、
      不執行 probe、不 spawn 子程序（SI-12 / NFR-03）。
    - ``quick=true``：不得啟動 helper（health 保持輕量）；僅回報平台支援度，
      ``available`` 未經驗證一律 false。
    - 完整模式（macOS）：呼叫凍結介面取得 available/path/probe；任何失敗
      都不得讓 ``/health`` 失敗，以 ``reason`` 回報可觀察的失敗原因。
    """
    if platform.system() != "Darwin":
        return {
            "supported": False,
            "available": False,
            "path": None,
            "probe": None,
            "reason": _APPLE_HELPER_REASON_NOT_MACOS,
        }
    if quick:
        return {
            "supported": True,
            "available": False,
            "path": None,
            "probe": None,
            "reason": "quick 模式：未執行 helper probe",
        }
    try:
        helper_status = _load_apple_helper_status()(
            configured_path=(settings.APPLE_SPEECH_CLI_PATH or None)
        )
    except Exception as exc:  # noqa: BLE001 — Apple 子系統失敗不得讓 /health 失敗（BE-03）
        log.warning(f"Apple helper probe 失敗（/health 回報不可用）: {type(exc).__name__}: {exc}")
        return {
            "supported": True,
            "available": False,
            "path": None,
            "probe": None,
            "reason": f"helper probe 失敗：{type(exc).__name__}",
        }
    if not isinstance(helper_status, dict):
        return {
            "supported": True,
            "available": False,
            "path": None,
            "probe": None,
            "reason": "helper probe 回傳非預期格式",
        }
    return {
        "supported": bool(helper_status.get("supported")),
        "available": bool(helper_status.get("available")),
        "path": helper_status.get("path"),
        "probe": helper_status.get("probe"),
        "reason": helper_status.get("reason"),
    }


@router.get("/health", response_model=HealthStatus)
async def health_check(quick: bool = False):
    """
    健康檢查端點
    回傳系統狀態、GPU 資訊、排隊狀態
    
    v3.5.4 改進：
    - 支援 quick 模式（使用快取，避免 GPU 滿載時阻塞）
    - 支援 CUDA 與 MLX/Metal 狀態
    - Apple SpeechAnalyzer helper 狀態以 additive 區段回報（僅 macOS 完整模式
      probe；quick 模式與非 macOS 一律不啟動 helper）
    
    Query Parameters:
        quick: bool - 是否使用快速模式（預設 False）
                     - True: 使用快取資訊，不重新偵測裝置
                     - False: 完整健康檢查（重新偵測裝置）
    """
    # 根據 quick 參數決定是否重新偵測裝置
    if not quick:
        # 完整模式：重新偵測裝置
        device_detector.detect_best_device()
    
    device_info = device_detector.get_device_info()
    
    # MLX/Metal 會以 additive metadata 回報；不要將其重寫成 PyTorch MPS。
    if device_info.get("accelerator") == "mlx-metal":
        device_info.setdefault("gpu_name", "Apple Silicon (MLX/Metal)")
        device_info["gpu_available"] = True

    # Apple SpeechAnalyzer helper 觀測（additive；非 macOS 不 probe，SI-12）
    device_info["apple_helper"] = _apple_helper_health_section(quick=quick)
    
    async def _resolve_status(result):
        """同時支援同步/非同步檢查結果"""
        if inspect.isawaitable(result):
            return bool(await result)
        return bool(result)
    
    # 檢查服務狀態（容忍同步/異步 mock）
    ollama_available = await _resolve_status(summarization_service.check_ollama_health())
    lmstudio_available = await _resolve_status(summarization_service.check_lmstudio_health())
    gemini_available = bool(summarization_service.check_gemini_available())
    llm_health = summarization_service.get_local_llm_health()
    if isinstance(llm_health, dict):
        device_info["llm"] = llm_health
    
    # 取得排隊狀態
    queue_status = task_queue.get_queue_status()
    
    return HealthStatus(
        status="healthy",
        version=__version__,
        build_revision=_resolve_build_revision(),
        gpu_available=device_info.get("gpu_available", False),
        gpu_name=device_info.get("gpu_name"),
        ollama_available=ollama_available,
        lmstudio_available=lmstudio_available,
        gemini_available=gemini_available,
        queue_status=queue_status,
        device_info=device_info
    )


@router.post("/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    processing_mode: str = Form(default="local"),
    user_prompt: Optional[str] = Form(default=None),
    meeting_template: str = Form(default=GENERAL_TEMPLATE_ID),
):
    """
    上傳音訊/視訊檔案

    - **file**: 音訊或視訊檔案（大小上限依 MAX_FILE_SIZE_MB 設定，預設 200MB）
    - **processing_mode**: 處理模式 (local/cloud)
    - **user_prompt**: 使用者自訂 prompt（選填）
    - **meeting_template**: 會議類型模板 id（v4.4.0，預設 general）
    """
    # 驗證批次上傳設定
    if not settings.ENABLE_BATCH_UPLOAD:
        # 單檔上傳模式
        pass  # 目前只接受單檔
    
    # 驗證檔案格式
    valid, error_msg = file_manager.validate_file(file)
    if not valid:
        raise HTTPException(status_code=400, detail=error_msg)
    
    # 驗證檔案大小
    size_validation = await file_manager.validate_file_size(file, return_content=True)
    if len(size_validation) == 4:
        valid, error_msg, file_size, file_content = size_validation
    else:
        valid, error_msg, file_size = size_validation
        file_content = None
    if not valid:
        raise HTTPException(status_code=413, detail=error_msg)
    
    # 驗證處理模式
    try:
        mode = ProcessingMode(processing_mode)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"無效的處理模式: {processing_mode}")

    # 驗證會議模板（v4.4.0）
    try:
        template = get_template(meeting_template)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"無效的會議類型: {meeting_template}")

    # 機敏模板強制本地處理（前端已鎖定，此處為第二道防線）
    if template.local_only and mode == ProcessingMode.CLOUD:
        raise HTTPException(
            status_code=400,
            detail=f"「{template.display_name}」涉及機敏內容，僅限本地模式處理，請改選本地模式。"
        )

    # 如果選擇雲端模式，檢查 API Key
    if mode == ProcessingMode.CLOUD and not summarization_service.check_gemini_available():
        raise HTTPException(
            status_code=400,
            detail="未設定 Gemini API Key，無法使用雲端模式。請執行 setup-api-key.ps1 設定 API Key。"
        )

    # 儲存檔案
    file_path, unique_filename, actual_size = await file_manager.save_upload(file, content=file_content)

    # 加入排隊
    task = await task_queue.add_task(
        filename=unique_filename,
        original_filename=file.filename,
        file_size=actual_size,
        processing_mode=mode,
        user_prompt=user_prompt,
        template_id=template.id,
    )
    
    if not task:
        # 佇列已滿
        file_manager.delete_file(file_path)
        raise HTTPException(
            status_code=503,
            detail=f"系統繁忙，排隊人數已達上限 ({settings.QUEUE_MAX_SIZE})，請稍後再試"
        )
    
    log.info(f"檔案上傳成功: {file.filename} -> {unique_filename}, 任務ID: {task.task_id}")
    
    return UploadResponse(
        task_id=task.task_id,
        filename=file.filename,
        file_size=actual_size,
        queue_position=task.queue_position or 0,
        estimated_wait_seconds=task.estimated_wait_seconds or 0,
        message="檔案上傳成功，已加入處理佇列"
    )


@router.get("/tasks/{task_id}", response_model=TaskInfo)
async def get_task(task_id: str):
    """
    查詢單一任務目前進度。

    若任務不存在會回傳 404，避免前端誤以為仍在排隊。
    """
    task = task_queue.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"找不到任務: {task_id}")
    
    # 更新排隊位置
    position = task_queue.get_task_position(task_id)
    if position:
        task.queue_position = position
    
    return task


@router.get("/tasks/{task_id}/transcript")
async def get_task_transcript(task_id: str):
    """
    下載任務的逐字稿（純文字 .txt，v4.2.2 新增）。

    逐字稿在轉錄＋語意校正完成後即產生，會議紀錄生成失敗時仍可下載。
    """
    task = task_queue.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"找不到任務: {task_id}")

    transcript_path = file_manager.transcript_result_path(task_id, task.original_filename)
    if not os.path.exists(transcript_path):
        if task.status in (TaskStatus.QUEUED, TaskStatus.PENDING, TaskStatus.TRANSCRIBING):
            raise HTTPException(status_code=400, detail=f"逐字稿尚未產生，目前狀態: {task.status.value}")
        raise HTTPException(status_code=404, detail="逐字稿檔案不存在")

    return FileResponse(
        transcript_path,
        media_type="text/plain",
        filename=f"{task.created_at.strftime('%Y%m%d%H%M%S')}_逐字稿.txt",
    )


@router.get("/tasks/{task_id}/result")
async def get_task_result(task_id: str, format: str = "md", doc: str = "record"):
    """
    下載任務輸出的會議摘要檔。

    支援格式：
    - format=md（預設）：Markdown 格式
    - format=docx：Word 文件格式

    文件種類（v4.5.0）：
    - doc=record（預設）：會議紀錄本文
    - doc=attachment：模板附件（如科務會議「列管資料」；僅支援 docx，
      且該會議類型須定義附件，否則回傳 400）

    只有任務已完成才可下載；若尚未完成或檔案不存在，會回傳明確錯誤訊息。
    """
    # 驗證格式參數
    format = format.lower()
    if format not in ("md", "docx"):
        raise HTTPException(
            status_code=400,
            detail=f"不支援的格式: {format}，僅支援 md 或 docx"
        )

    doc = doc.lower()
    if doc not in ("record", "attachment"):
        raise HTTPException(
            status_code=400,
            detail=f"不支援的文件種類: {doc}，僅支援 record 或 attachment"
        )
    if doc == "attachment" and format != "docx":
        raise HTTPException(
            status_code=400,
            detail="附件僅支援 docx 格式"
        )

    task = task_queue.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"找不到任務: {task_id}")
    
    if task.status != TaskStatus.COMPLETED:
        raise HTTPException(
            status_code=400,
            detail=f"任務尚未完成，目前狀態: {task.status.value}"
        )
    
    # 尋找結果檔案（安全地組合路徑）
    base_name = os.path.splitext(os.path.basename(task.original_filename))[0]
    # 清理檔名，只保留安全字符（含中文）
    safe_base_name = "".join(c for c in base_name if c.isalnum() or c in ('_', '-', ' ', '.') or '\u4e00' <= c <= '\u9fff')
    result_filename = f"{safe_base_name}_{task_id}.md"
    result_path = os.path.join(settings.outputs_dir, result_filename)

    if not os.path.exists(result_path):
        raise HTTPException(status_code=404, detail="結果檔案不存在")

    # 下載檔名統一為「YYYYMMDDhhmmss_會議紀錄」（v4.2.3）；
    # 磁碟檔仍以 task_id 命名，保證唯一性與 docx 快取判斷不受影響
    download_stamp = task.created_at.strftime("%Y%m%d%H%M%S")
    # v4.6.2：摘要失敗的 fallback 文件改名，避免被誤認為正式會議紀錄
    record_label = "逐字稿(會議紀錄生成失敗)" if task.summary_failed else "會議紀錄"

    # 附件（v4.5.0）：由本文 md 確定性建構附件 md，再轉 docx（沿用 mtime 快取）
    if doc == "attachment":
        template = get_template(task.template_id)
        if template.attachment is None:
            raise HTTPException(
                status_code=400,
                detail=f"「{template.display_name}」無列管附件可下載"
            )

        attachment_docx_path = os.path.join(
            settings.outputs_dir, f"{safe_base_name}_{task_id}_attachment.docx"
        )
        if not os.path.exists(attachment_docx_path) or (
            os.path.getmtime(attachment_docx_path) < os.path.getmtime(result_path)
        ):
            try:
                from backend.services.docx_converter import docx_converter
                with open(result_path, 'r', encoding='utf-8') as f:
                    record_md = f.read()
                attachment_md = template.attachment.build_markdown(record_md)
                docx_converter.convert(
                    attachment_md, attachment_docx_path, template_id=task.template_id
                )
            except Exception as e:
                log.error(f"[DOCX] 附件轉換失敗: {e}")
                raise HTTPException(
                    status_code=500,
                    detail=f"附件轉換失敗: {str(e)}"
                )

        return FileResponse(
            attachment_docx_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=f"{download_stamp}_{template.attachment.download_name}.docx"
        )

    # Markdown 格式（原始行為）
    if format == "md":
        return FileResponse(
            result_path,
            media_type="text/markdown",
            filename=f"{download_stamp}_{record_label}.md"
        )
    
    docx_filename = f"{safe_base_name}_{task_id}.docx"
    docx_path = os.path.join(settings.outputs_dir, docx_filename)

    # 快取：若已存在 .docx 且修改時間晚於 .md，直接回傳
    if not os.path.exists(docx_path) or (
        os.path.getmtime(docx_path) < os.path.getmtime(result_path)
    ):
        try:
            from backend.services.docx_converter import docx_converter
            with open(result_path, 'r', encoding='utf-8') as f:
                md_content = f.read()
            docx_converter.convert(md_content, docx_path, template_id=task.template_id)
        except ImportError as e:
            log.error(f"[DOCX] python-docx 未安裝或匯入失敗: {e}")
            raise HTTPException(
                status_code=500,
                detail="DOCX 轉換功能無法使用（缺少 python-docx 套件）"
            )
        except Exception as e:
            log.error(f"[DOCX] 轉換失敗: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"DOCX 轉換失敗: {str(e)}"
            )

    return FileResponse(
        docx_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"{download_stamp}_{record_label}.docx"
    )


@router.delete("/tasks/{task_id}")
async def cancel_task(task_id: str):
    """
    取消/刪除任務
    注意：只能取消排隊中的任務，正在處理中的任務無法取消
    """
    task = task_queue.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"找不到任務: {task_id}")
    
    # 檢查任務狀態
    if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
        raise HTTPException(
            status_code=400,
            detail=f"任務已經結束，狀態: {task.status.value}"
        )
    
    success = await task_queue.cancel_task(task_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"無法取消任務 {task_id}（可能正在處理中）"
        )
    
    return {"message": f"任務 {task_id} 已取消"}


@router.get("/queue/status", response_model=QueueStatus)
async def get_queue_status():
    """
    查詢目前排隊與處理中的整體狀態。
    """
    return task_queue.get_queue_status()


@router.get("/queue/position/{task_id}")
async def get_queue_position(task_id: str):
    """
    查詢特定任務在佇列中的位置
    """
    task = task_queue.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"找不到任務: {task_id}")
    
    position = task_queue.get_task_position(task_id)
    queue_status = task_queue.get_queue_status()
    
    return {
        "task_id": task_id,
        "position": position,
        "total_queued": queue_status.total_queued,
        "estimated_wait_seconds": task.estimated_wait_seconds or 0,
        "status": task.status.value
    }


@router.get("/config")
async def get_config():
    """
    取得系統配置（公開部分）
    """
    effective_asr_backend = infer_asr_backend(settings.WHISPER_MODEL, settings.ASR_BACKEND)
    effective_asr_model = resolve_asr_model(settings.WHISPER_MODEL, settings.ASR_BACKEND)
    # Mac 僅提供 Apple SpeechAnalyzer（fail-closed，無 fallback；Owner 2026-09-13）：
    # 不回報任何 Whisper 模型 id／revision，避免 payload 看起來仍有 Mac Whisper 路徑。
    is_apple_engine = effective_asr_backend == "apple"
    llm_health = summarization_service.get_local_llm_health()
    effective_provider = (
        llm_health.get("provider", settings.LOCAL_LLM_PROVIDER)
        if isinstance(llm_health, dict)
        else settings.LOCAL_LLM_PROVIDER
    )
    return {
        "max_file_size_mb": settings.MAX_FILE_SIZE_MB,
        "enable_batch_upload": settings.ENABLE_BATCH_UPLOAD,
        "allowed_extensions": settings.allowed_extensions_list,
        "max_concurrent_tasks": settings.MAX_CONCURRENT_TASKS,
        "queue_max_size": settings.QUEUE_MAX_SIZE,
        "default_mode": settings.DEFAULT_MODE,
        "asr_backend": settings.ASR_BACKEND,
        "effective_asr_backend": effective_asr_backend,
        "whisper_model": None if is_apple_engine else settings.WHISPER_MODEL,
        "effective_whisper_model": None if is_apple_engine else effective_asr_model,
        "whisper_model_revision": (
            None
            if is_apple_engine
            else resolve_model_revision(
                effective_asr_model,
                settings.WHISPER_MODEL_REVISION,
            )
        ),
        "gemini_available": summarization_service.check_gemini_available(),
        "local_llm_provider": settings.LOCAL_LLM_PROVIDER,
        "effective_local_llm_provider": effective_provider,
        "lmstudio_model": settings.LMSTUDIO_MODEL,
        # v4.3.1：前端模式卡顯示實際使用的模型名稱（唯一來源：後端設定/解析結果，
        # 換模型後前端自動同步，不得在前端寫死）
        "local_llm_model": summarization_service.get_effective_local_model(),
        "cloud_llm_model": settings.GEMINI_MODEL,
        # v4.4.0：會議類型模板清單（前端「選擇會議類型」選單唯一資料來源）
        "meeting_templates": template_public_info(),
        "default_meeting_template": GENERAL_TEMPLATE_ID,
    }


@router.get("/storage/stats")
async def get_storage_stats():
    """
    取得儲存空間使用統計
    """
    stats = file_manager.get_storage_stats()
    stats["retention_policy"] = {
        "uploads_days": file_manager.UPLOADS_RETENTION_DAYS,
        "outputs_days": file_manager.OUTPUTS_RETENTION_DAYS,
        "cache_days": file_manager.CACHE_RETENTION_DAYS
    }
    return stats


@router.post("/storage/cleanup")
async def trigger_cleanup():
    """
    手動觸發檔案清理（僅清理過期檔案）
    """
    results = file_manager.run_cleanup()
    return {
        "message": "清理完成",
        "results": results
    }


@router.get("/gemini/health")
async def check_gemini_health(force_refresh: bool = False):
    """
    檢查 Gemini API 連線狀態（層級2：每日健康檢查）
    
    - 自動快取24小時結果，節省API配額
    - force_refresh=true 強制重新檢查
    - 供定時任務調用（推薦每日早上 7:00）
    
    Query Parameters:
        force_refresh: bool - 是否強制刷新快取
        
    Returns:
        {
            "available": bool - Gemini API 是否可用,
            "cached": bool - 是否使用快取結果,
            "timestamp": str - 檢查時間,
            "message": str - 狀態信息
        }
    """
    start_time = datetime.now()
    health_status = await summarization_service.check_gemini_health(force_refresh)
    
    cache_info = summarization_service._gemini_health_check_cache
    is_cached = not force_refresh and cache_info["last_check_time"] is not None and \
                (start_time - cache_info["last_check_time"]).total_seconds() < cache_info["ttl_seconds"]
    
    return {
        "available": health_status,
        "cached": is_cached,
        "timestamp": start_time.isoformat(),
        "message": "✓ Gemini API 可用" if health_status else "✗ Gemini API 不可用或未配置"
    }
