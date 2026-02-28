"""
MeetingScribe 日誌系統設定。

提供人看得懂的即時日誌與可供後續分析的結構化日誌，
協助團隊快速追蹤問題、還原任務流程與進行維運排查。
"""

import sys
import os
from pathlib import Path
from loguru import logger

# 嘗試從 settings 取得配置，若失敗則使用環境變數
try:
    from backend.core.config import settings
    LOG_LEVEL = settings.LOG_LEVEL
    DATA_DIR = settings.DATA_DIR
except Exception:
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    DATA_DIR = os.getenv("DATA_DIR", str(Path(__file__).parent.parent.parent / "data"))


def setup_logger():
    """初始化日誌輸出規則（主控台、檔案、錯誤檔與 JSON 結構化檔案）。"""
    # 移除預設處理器
    logger.remove()
    
    # 確保日誌目錄存在
    log_dir = Path(DATA_DIR) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. 控制台輸出（彩色，人類可讀）
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
               "<level>{message}</level>",
        level=LOG_LEVEL,
        colorize=True,
        backtrace=True,
        diagnose=True,
    )
    
    # 2. 檔案日誌 - 所有級別（每日輪轉）
    logger.add(
        str(log_dir / "app_{time:YYYY-MM-DD}.log"),
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
               "{name}:{function}:{line} | {extra} | {message}",
        level="DEBUG",
        rotation="00:00",      # 每天午夜輪轉
        retention="30 days",   # 保留 30 天
        compression="zip",     # 壓縮舊日誌
        encoding="utf-8",
        enqueue=True,          # 非同步寫入（執行緒安全）
    )
    
    # 3. 錯誤日誌（僅 ERROR 和 CRITICAL）
    logger.add(
        str(log_dir / "error_{time:YYYY-MM-DD}.log"),
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | "
               "{name}:{function}:{line} | {message}",
        level="ERROR",
        rotation="100 MB",
        retention="90 days",
        compression="zip",
        encoding="utf-8",
        backtrace=True,        # 包含完整堆疊
        diagnose=True,         # 包含變數值
        enqueue=True,
    )
    
    # 4. JSON 結構化日誌（用於日誌聚合系統）
    logger.add(
        str(log_dir / "structured_{time:YYYY-MM-DD}.jsonl"),
        serialize=True,        # JSON 格式
        level="INFO",
        rotation="100 MB",
        retention="14 days",
        compression="zip",
        enqueue=True,
    )
    
    logger.info(f"日誌系統初始化完成 (目錄: {log_dir})")
    
    return logger


def get_task_logger(task_id: str):
    """
    取得帶有任務 ID 的日誌器
    
    使用範例：
        task_log = get_task_logger("abc123")
        task_log.info("開始處理任務")
    """
    return logger.bind(task_id=task_id)


# 初始化日誌
log = setup_logger()
