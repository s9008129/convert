"""
MeetingScribe API 入口。

集中匯出 HTTP 路由與 WebSocket 端點，讓主程式可以一次載入對外服務。

流程說明：
- 主程式載入此模組後，即可同時取得 REST 路由與即時推播端點。

錯誤情境說明：
- 若子模組匯入失敗，服務會在啟動階段明確報錯，方便維運立即排查。
"""

from backend.api.routes import router
from backend.api.websocket import websocket_endpoint, connection_manager

__all__ = ["router", "websocket_endpoint", "connection_manager"]
