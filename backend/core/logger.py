"""
MeetingScribe 日誌系統
"""

import sys
from loguru import logger
from backend.core.config import settings


def setup_logger():
    """設定日誌系統"""
    # 移除預設處理器
    logger.remove()
    
    # 添加控制台輸出
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=settings.LOG_LEVEL,
        colorize=True
    )
    
    return logger


# 初始化日誌
log = setup_logger()
