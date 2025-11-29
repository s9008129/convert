"""
MeetingScribe 主應用程式
v2.1 - 跨平台 Docker 服務
"""

import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import settings
from backend.core.logger import log
from backend.api import router, websocket_endpoint
from backend.services import task_processor, device_detector


@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用程式生命週期管理"""
    log.info("=" * 50)
    log.info("🚀 MeetingScribe v2.1 啟動中...")
    log.info("=" * 50)
    
    # 初始化裝置偵測
    device_type, compute_type = device_detector.detect_best_device()
    log.info(f"裝置偵測完成: {device_type.value}, 精度: {compute_type}")
    
    # 啟動任務處理器
    processor_task = asyncio.create_task(task_processor.start())
    
    log.info(f"服務已就緒，監聽端口: 9527")
    log.info(f"預設處理模式: {settings.DEFAULT_MODE}")
    log.info(f"最大檔案大小: {settings.MAX_FILE_SIZE_MB}MB")
    log.info(f"批次上傳: {'啟用' if settings.ENABLE_BATCH_UPLOAD else '停用'}")
    log.info(f"最大同時處理: {settings.MAX_CONCURRENT_TASKS}")
    log.info("=" * 50)
    
    yield
    
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
    title="MeetingScribe",
    description="會議轉錄工具 - 將會議錄音轉換為結構化會議記錄",
    version="2.1.2",
    lifespan=lifespan
)

# CORS 設定
# 注意：生產環境應限制 allow_origins 為特定域名
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: 生產環境應設定為特定域名
    allow_credentials=True,
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
    """首頁 - 返回前端頁面"""
    return FileResponse("frontend/index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=9527,
        reload=False
    )
