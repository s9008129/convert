"""
後端主程式。

負責啟動 API 服務、背景任務處理器與檔案清理排程，並在關閉時做完整收尾。
（版本號以根目錄 VERSION 檔為唯一來源，見 backend/core/version.py）
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.core.asr_model_resolver import infer_asr_backend, resolve_asr_model, resolve_model_revision
from backend.core.config import settings
from backend.core.logger import log
from backend.core.platform_config import resolve_local_llm_provider
from backend.core.version import __version__
from backend.middleware import TimeoutMiddleware
from backend.api import router, websocket_endpoint
from backend.services import task_processor, device_detector, file_manager, summarization_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """管理服務啟動與關閉流程，確保背景任務與清理器都能正常啟停。"""
    log.info("=" * 50)
    log.info(f"🚀 政府智慧會議紀錄生成系統 v{__version__} 啟動中...")
    log.info("=" * 50)
    
    # 初始化裝置偵測
    device_type, compute_type = device_detector.detect_best_device()
    effective_asr_backend = infer_asr_backend(settings.WHISPER_MODEL, settings.ASR_BACKEND)
    effective_asr_model = resolve_asr_model(settings.WHISPER_MODEL, settings.ASR_BACKEND)
    effective_asr_revision = resolve_model_revision(
        effective_asr_model,
        settings.WHISPER_MODEL_REVISION,
    )
    effective_accelerator = (
        "mlx-metal" if effective_asr_backend == "mlx_whisper" else device_type.value
    )
    log.info(f"裝置偵測完成: {effective_accelerator}, 精度: {compute_type}")
    
    # 啟動任務處理器
    processor_task = asyncio.create_task(task_processor.start())
    
    # 啟動檔案清理排程器
    await file_manager.start_cleanup_scheduler()
    
    # 啟動時執行一次清理（清理重啟前的過期檔案）
    cleanup_result = file_manager.run_cleanup()
    if cleanup_result["total_freed_mb"] > 0:
        log.info(f"啟動清理完成: 釋放 {cleanup_result['total_freed_mb']} MB 空間")
    
    log.info(f"服務已就緒，監聽端口: 9527")
    log.info(f"預設處理模式: {settings.DEFAULT_MODE}")
    log.info(f"最大檔案大小: {settings.MAX_FILE_SIZE_MB}MB")
    log.info(f"批次上傳: {'啟用' if settings.ENABLE_BATCH_UPLOAD else '停用'}")
    log.info(f"最大同時處理: {settings.MAX_CONCURRENT_TASKS}")
    # P0-3(c)：啟動時記錄「實際生效」的關鍵參數，杜絕「改了 config.yaml
    # 卻沒生效」的除錯黑洞（後端僅讀環境變數 / .env）
    log.info("-" * 50)
    log.info("實際生效設定（來源：環境變數 / .env，非 config.yaml）：")
    log.info(
        f"  ASR: backend={effective_asr_backend}, model={effective_asr_model}, "
        f"revision={effective_asr_revision or 'unpinned'}, "
        f"language={settings.WHISPER_LANGUAGE}, beam={settings.ASR_BEAM_SIZE}"
    )
    log.info(
        f"  ASR VAD: enabled={settings.ASR_VAD_ENABLED}, threshold={settings.ASR_VAD_THRESHOLD}, "
        f"min_silence={settings.ASR_VAD_MIN_SILENCE_MS}ms（僅 faster_whisper 路徑）"
    )
    log.info(
        f"  ASR 參數: initial_prompt={'有' if settings.ASR_INITIAL_PROMPT else '無'}, "
        f"hotwords={'啟用' if settings.ASR_ENABLE_HOTWORDS else '停用'}, "
        f"cond_prev={settings.ASR_CONDITION_ON_PREVIOUS_TEXT}, "
        f"chunk={settings.ASR_CHUNK_LENGTH_SECONDS}s+stride{settings.ASR_CHUNK_STRIDE_SECONDS}s"
    )
    effective_local_provider = resolve_local_llm_provider(settings.LOCAL_LLM_PROVIDER)
    effective_local_model = (
        summarization_service.get_effective_local_model()
        if effective_local_provider == "lmstudio"
        else settings.LOCAL_LLM_MODEL
    )
    log.info(
        f"  LLM: provider={effective_local_provider}, model={effective_local_model}, "
        f"num_ctx={settings.LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS}, "
        f"keep_alive={settings.LOCAL_LLM_KEEP_ALIVE}, cloud={settings.GEMINI_MODEL}"
    )
    log.info(
        f"  語意校正: {'啟用' if settings.ENABLE_TRANSCRIPT_CORRECTION else '停用'}"
        f"（scope={settings.CORRECTION_SCOPE}, 改動上限={settings.CORRECTION_MAX_CHANGE_RATIO:.0%}）"
    )
    log.info("=" * 50)
    
    yield
    
    # 停止清理排程器
    await file_manager.stop_cleanup_scheduler()
    
    # 停止任務處理器
    log.info("正在關閉服務...")
    await task_processor.stop()
    processor_task.cancel()
    
    try:
        await processor_task
    except asyncio.CancelledError:
        pass
    
    log.info("服務已關閉")


# 建立 FastAPI 應用
app = FastAPI(
    title="政府智慧會議紀錄生成系統",
    description="會議轉錄工具 - 將會議錄音轉換為結構化會議記錄",
    version=__version__,
    lifespan=lifespan
)

# 請求超時中間件（防止 GPU 滿載時阻塞新請求）
app.add_middleware(
    TimeoutMiddleware,
    timeout=30.0,  # 30 秒超時
    excluded_paths=("/api/upload",),
)

# CORS 設定（P2-7）
# 預設 "*"（內網部署）；此時依 CORS 規範不得同時允許 credentials。
# 生產環境請以 ALLOWED_ORIGINS 環境變數設定明確來源清單。
_cors_origins = settings.allowed_origins_list or ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials="*" not in _cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 註冊 API 路由
app.include_router(router)

# WebSocket 端點
@app.websocket("/ws/tasks/{task_id}")
async def ws_task_progress(websocket: WebSocket, task_id: str):
    """WebSocket 端點 - 即時推送任務進度"""
    await websocket_endpoint(websocket, task_id)

# 靜態檔案（前端）
app.mount("/static", StaticFiles(directory="frontend"), name="static")

# 首頁
@app.get("/")
async def index():
    """首頁 - 返回前端頁面。

    no-cache：改版後使用者不必按 Ctrl+F5 也能拿到新頁面（v4.2.3，
    修正「已部署新版但瀏覽器仍顯示舊頁面」問題）；搭配 index.html 內
    靜態資源網址的 ?v= 版本參數，JS/CSS 也會隨版本自動換新。
    """
    return FileResponse(
        "frontend/index.html",
        headers={"Cache-Control": "no-cache, must-revalidate"},
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=9527,
        reload=False
    )
