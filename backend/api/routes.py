"""
MeetingScribe API 路由
v2.1 - 包含排隊系統和 User Prompt 支援
"""

import os
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse

from backend.core.config import settings
from backend.core.logger import log
from backend.models.schemas import (
    TaskStatus, ProcessingMode, TaskInfo, QueueStatus,
    UploadResponse, HealthStatus, ErrorResponse
)
from backend.services import (
    device_detector, task_queue, file_manager,
    summarization_service
)

router = APIRouter(prefix="/api", tags=["API"])


@router.get("/health", response_model=HealthStatus)
async def health_check():
    """
    健康檢查端點
    回傳系統狀態、GPU 資訊、排隊狀態
    """
    # 偵測裝置
    device_detector.detect_best_device()
    device_info = device_detector.get_device_info()
    
    # 檢查服務狀態
    ollama_available = await summarization_service.check_ollama_health()
    lmstudio_available = await summarization_service.check_lmstudio_health()
    gemini_available = summarization_service.check_gemini_available()
    
    # 取得排隊狀態
    queue_status = task_queue.get_queue_status()
    
    return HealthStatus(
        status="healthy",
        version="2.2.0",
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
    user_prompt: Optional[str] = Form(default=None)
):
    """
    上傳音訊/視訊檔案
    
    - **file**: 音訊或視訊檔案（最大 100MB）
    - **processing_mode**: 處理模式 (local/cloud)
    - **user_prompt**: 使用者自訂 prompt（選填）
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
    valid, error_msg, file_size = await file_manager.validate_file_size(file)
    if not valid:
        raise HTTPException(status_code=413, detail=error_msg)
    
    # 驗證處理模式
    try:
        mode = ProcessingMode(processing_mode)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"無效的處理模式: {processing_mode}")
    
    # 如果選擇雲端模式，檢查 API Key
    if mode == ProcessingMode.CLOUD and not summarization_service.check_gemini_available():
        raise HTTPException(
            status_code=400,
            detail="未設定 Gemini API Key，無法使用雲端模式。請執行 setup-api-key.ps1 設定 API Key。"
        )
    
    # 儲存檔案
    file_path, unique_filename, actual_size = await file_manager.save_upload(file)
    
    # 加入排隊
    task = await task_queue.add_task(
        filename=unique_filename,
        original_filename=file.filename,
        file_size=actual_size,
        processing_mode=mode,
        user_prompt=user_prompt
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
    查詢任務狀態和進度
    """
    task = task_queue.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"找不到任務: {task_id}")
    
    # 更新排隊位置
    position = task_queue.get_task_position(task_id)
    if position:
        task.queue_position = position
    
    return task


@router.get("/tasks/{task_id}/result")
async def get_task_result(task_id: str, format: str = "md"):
    """
    取得處理結果（支援 Markdown / DOCX）
    """
    format = format.lower()
    if format not in ("md", "docx"):
        raise HTTPException(
            status_code=400,
            detail=f"不支援的格式: {format}，僅支援 md 或 docx"
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

    if format == "md":
        return FileResponse(
            result_path,
            media_type="text/markdown",
            filename=result_filename
        )

    from backend.services.docx_converter import docx_converter

    docx_filename = f"{safe_base_name}_{task_id}.docx"
    docx_path = os.path.join(settings.outputs_dir, docx_filename)

    if not os.path.exists(docx_path) or (
        os.path.getmtime(docx_path) < os.path.getmtime(result_path)
    ):
        try:
            with open(result_path, 'r', encoding='utf-8') as f:
                md_content = f.read()
            docx_converter.convert(md_content, docx_path)
        except Exception as e:
            log.error(f"[DOCX] 轉換失敗: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"DOCX 轉換失敗: {str(e)}"
            )

    return FileResponse(
        docx_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=docx_filename
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
    查詢排隊狀態
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
    return {
        "max_file_size_mb": settings.MAX_FILE_SIZE_MB,
        "enable_batch_upload": settings.ENABLE_BATCH_UPLOAD,
        "allowed_extensions": settings.allowed_extensions_list,
        "max_concurrent_tasks": settings.MAX_CONCURRENT_TASKS,
        "queue_max_size": settings.QUEUE_MAX_SIZE,
        "default_mode": settings.DEFAULT_MODE,
        "gemini_available": summarization_service.check_gemini_available(),
        "lmstudio_model": settings.LMSTUDIO_MODEL
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
