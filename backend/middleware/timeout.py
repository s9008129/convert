"""
HTTP 請求逾時保護中間件。

當單一請求等待太久時，會主動回應逾時錯誤，避免整體服務被少數慢請求拖住。
v3.5.4 - 防止 GPU 滿載時阻塞新請求
"""

import asyncio
from typing import Iterable
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from backend.core.logger import log


class TimeoutMiddleware(BaseHTTPMiddleware):
    """
    請求超時中間件
    防止長時間阻塞的請求影響其他用戶
    """
    
    def __init__(self, app, timeout: float = 30.0, excluded_paths: Iterable[str] | None = None):
        """
        初始化中間件
        
        Args:
            app: FastAPI 應用
            timeout: 請求超時時間（秒），預設 30 秒
        """
        super().__init__(app)
        self.timeout = timeout
        self.excluded_paths = tuple(excluded_paths or ())

    def _is_excluded_path(self, path: str) -> bool:
        return any(path == excluded or path.startswith(f"{excluded}/") for excluded in self.excluded_paths)
    
    async def dispatch(self, request: Request, call_next):
        """
        處理請求並加入超時控制
        
        Args:
            request: HTTP 請求
            call_next: 下一個中間件/路由處理器
            
        Returns:
            HTTP 響應
        """
        if self._is_excluded_path(request.url.path):
            return await call_next(request)

        try:
            # 為請求加入超時限制
            response = await asyncio.wait_for(
                call_next(request),
                timeout=self.timeout
            )
            return response
        except asyncio.TimeoutError:
            # 請求超時，返回 503 Service Unavailable
            log.warning(
                f"請求超時: {request.method} {request.url.path} "
                f"(超過 {self.timeout} 秒)"
            )
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "服務繁忙，請稍後再試",
                    "error": "Request timeout",
                    "timeout_seconds": self.timeout,
                    "suggestion": "系統資源使用率高，請等待當前任務完成後再試"
                }
            )
        except Exception as e:
            # 其他未預期錯誤
            log.error(f"中間件處理請求時發生錯誤: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "detail": "內部伺服器錯誤",
                    "error": str(e)
                }
            )
