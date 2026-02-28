"""
這份測試專注在 WebSocket 異常情境的穩定性。
它會驗證連線中斷、Broken pipe 等錯誤發生時，
系統是否能平順清理並維持正確狀態。
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch
from fastapi import WebSocket, WebSocketDisconnect

from backend.api.websocket import ConnectionManager, websocket_endpoint
from backend.models.schemas import TaskInfo, TaskStatus, ProgressMessage, ProcessingMode


class TestWebSocketErrorHandling:
    """測試 WebSocket 連線錯誤處理"""
    
    @pytest.mark.asyncio
    async def test_broken_pipe_in_send_progress(self):
        """測試 send_progress 處理 BrokenPipeError"""
        manager = ConnectionManager()
        
        # 模擬 WebSocket 連線
        mock_ws = AsyncMock(spec=WebSocket)
        mock_ws.send_json = AsyncMock(side_effect=BrokenPipeError("Broken pipe"))
        
        task_id = "test123"
        await manager.connect(mock_ws, task_id)
        
        # 發送進度訊息
        message = ProgressMessage(
            task_id=task_id,
            status=TaskStatus.PENDING,
            progress=50.0,
            stage="處理中",
            message="測試訊息"
        )
        
        # 應該不會拋出異常
        await manager.send_progress(task_id, message)
        
        # 驗證失效連線已被清除
        assert task_id not in manager._connections or len(manager._connections[task_id]) == 0
    
    @pytest.mark.asyncio
    async def test_connection_reset_in_send_progress(self):
        """測試 send_progress 處理 ConnectionResetError"""
        manager = ConnectionManager()
        
        # 模擬 WebSocket 連線
        mock_ws = AsyncMock(spec=WebSocket)
        mock_ws.send_json = AsyncMock(side_effect=ConnectionResetError("Connection reset"))
        
        task_id = "test456"
        await manager.connect(mock_ws, task_id)
        
        # 發送進度訊息
        message = ProgressMessage(
            task_id=task_id,
            status=TaskStatus.PENDING,
            progress=75.0,
            stage="處理中",
            message="測試訊息"
        )
        
        # 應該不會拋出異常
        await manager.send_progress(task_id, message)
        
        # 驗證失效連線已被清除
        assert task_id not in manager._connections or len(manager._connections[task_id]) == 0
    
    @pytest.mark.asyncio
    async def test_runtime_error_in_send_progress(self):
        """測試 send_progress 處理 RuntimeError"""
        manager = ConnectionManager()
        
        # 模擬 WebSocket 連線
        mock_ws = AsyncMock(spec=WebSocket)
        mock_ws.send_json = AsyncMock(side_effect=RuntimeError("WebSocket is closed"))
        
        task_id = "test789"
        await manager.connect(mock_ws, task_id)
        
        # 發送進度訊息
        message = ProgressMessage(
            task_id=task_id,
            status=TaskStatus.PENDING,
            progress=25.0,
            stage="處理中",
            message="測試訊息"
        )
        
        # 應該不會拋出異常
        await manager.send_progress(task_id, message)
        
        # 驗證失效連線已被清除
        assert task_id not in manager._connections or len(manager._connections[task_id]) == 0
    
    @pytest.mark.asyncio
    async def test_multiple_connections_partial_failure(self):
        """測試多個連線中部分失敗的情況"""
        manager = ConnectionManager()
        
        task_id = "test_multi"
        
        # 建立 3 個連線：1 個正常，2 個失敗
        good_ws = AsyncMock(spec=WebSocket)
        good_ws.send_json = AsyncMock()
        
        bad_ws1 = AsyncMock(spec=WebSocket)
        bad_ws1.send_json = AsyncMock(side_effect=BrokenPipeError())
        
        bad_ws2 = AsyncMock(spec=WebSocket)
        bad_ws2.send_json = AsyncMock(side_effect=ConnectionResetError())
        
        await manager.connect(good_ws, task_id)
        await manager.connect(bad_ws1, task_id)
        await manager.connect(bad_ws2, task_id)
        
        # 發送訊息
        message = ProgressMessage(
            task_id=task_id,
            status=TaskStatus.PENDING,
            progress=50.0,
            stage="處理中",
            message="測試"
        )
        
        await manager.send_progress(task_id, message)
        
        # 驗證：只有 good_ws 還在連線中
        assert task_id in manager._connections
        assert good_ws in manager._connections[task_id]
        assert bad_ws1 not in manager._connections[task_id]
        assert bad_ws2 not in manager._connections[task_id]
        assert len(manager._connections[task_id]) == 1
    
    @pytest.mark.asyncio
    async def test_websocket_endpoint_broken_pipe_on_initial_send(self):
        """測試 websocket_endpoint 在初始發送時遇到 BrokenPipeError"""
        from backend.services.queue_manager import task_queue
        
        # 準備測試任務
        task_id = "test_initial"
        task = TaskInfo(
            task_id=task_id,
            filename="test.mp3",
            original_filename="test.mp3",
            file_size=1000,
            status=TaskStatus.QUEUED,
            queue_position=1,
            estimated_wait_seconds=60,
            processing_mode=ProcessingMode.LOCAL
        )
        
        # 注入任務
        task_queue._tasks[task_id] = task
        
        # 模擬 WebSocket
        mock_ws = AsyncMock(spec=WebSocket)
        mock_ws.send_json = AsyncMock(side_effect=BrokenPipeError("初始發送失敗"))
        
        # 執行 websocket_endpoint（應該優雅地返回）
        try:
            await websocket_endpoint(mock_ws, task_id)
        except Exception as e:
            pytest.fail(f"websocket_endpoint 不應拋出異常: {e}")
        
        # 清理
        if task_id in task_queue._tasks:
            del task_queue._tasks[task_id]
    
    @pytest.mark.asyncio
    async def test_websocket_endpoint_broken_pipe_on_heartbeat(self):
        """測試 websocket_endpoint 在心跳回應時遇到 BrokenPipeError"""
        from backend.services.queue_manager import task_queue
        
        # 準備測試任務
        task_id = "test_heartbeat"
        task = TaskInfo(
            task_id=task_id,
            filename="test.mp3",
            original_filename="test.mp3",
            file_size=1000,
            status=TaskStatus.PENDING,
            queue_position=None,
            estimated_wait_seconds=0,
            processing_mode=ProcessingMode.LOCAL
        )
        
        # 注入任務
        task_queue._tasks[task_id] = task
        
        # 模擬 WebSocket
        mock_ws = AsyncMock(spec=WebSocket)
        mock_ws.send_json = AsyncMock()  # 初始發送成功
        mock_ws.receive_text = AsyncMock(return_value="ping")  # 收到心跳
        mock_ws.send_text = AsyncMock(side_effect=BrokenPipeError("心跳回應失敗"))
        
        # 執行 websocket_endpoint（應該在心跳失敗後中斷）
        try:
            await websocket_endpoint(mock_ws, task_id)
        except Exception as e:
            pytest.fail(f"websocket_endpoint 不應拋出異常: {e}")
        
        # 清理
        if task_id in task_queue._tasks:
            del task_queue._tasks[task_id]


class TestQueueDisplayConsistency:
    """測試排隊顯示一致性"""
    
    @pytest.mark.asyncio
    async def test_queue_position_updates_correctly(self):
        """測試排隊位置正確更新"""
        from backend.services.queue_manager import task_queue
        
        # 清空隊列
        task_queue._queue.clear()
        task_queue._tasks.clear()
        task_queue._processing.clear()
        
        # 加入 3 個任務
        task1 = await task_queue.add_task(
            filename="file1.mp3",
            original_filename="file1.mp3",
            file_size=1000,
            processing_mode=ProcessingMode.LOCAL
        )
        
        task2 = await task_queue.add_task(
            filename="file2.mp3",
            original_filename="file2.mp3",
            file_size=1000,
            processing_mode=ProcessingMode.LOCAL
        )
        
        task3 = await task_queue.add_task(
            filename="file3.mp3",
            original_filename="file3.mp3",
            file_size=1000,
            processing_mode=ProcessingMode.LOCAL
        )
        
        # 驗證初始排隊位置
        assert task1.queue_position == 1
        assert task2.queue_position == 2
        assert task3.queue_position == 3
        
        # 驗證 total_queued
        queue_status = task_queue.get_queue_status()
        assert queue_status.total_queued == 3
        
        # 取出第一個任務
        next_task = await task_queue.get_next_task()
        assert next_task.task_id == task1.task_id
        
        # 驗證排隊位置已更新
        queue_status = task_queue.get_queue_status()
        assert queue_status.total_queued == 2
        
        # 重新取得任務資訊
        task2_updated = task_queue.get_task(task2.task_id)
        task3_updated = task_queue.get_task(task3.task_id)
        
        assert task2_updated.queue_position == 1
        assert task3_updated.queue_position == 2
        
        # 清理
        task_queue._queue.clear()
        task_queue._tasks.clear()
        task_queue._processing.clear()
    
    @pytest.mark.asyncio
    async def test_queue_position_none_when_processing(self):
        """測試任務開始處理時 queue_position 應為 None"""
        from backend.services.queue_manager import task_queue
        
        # 清空隊列
        task_queue._queue.clear()
        task_queue._tasks.clear()
        task_queue._processing.clear()
        
        # 加入任務
        task = await task_queue.add_task(
            filename="file.mp3",
            original_filename="file.mp3",
            file_size=1000,
            processing_mode=ProcessingMode.LOCAL
        )
        
        assert task.queue_position == 1
        assert task.status == TaskStatus.QUEUED
        
        # 開始處理
        processing_task = await task_queue.get_next_task()
        
        assert processing_task.queue_position is None
        assert processing_task.status == TaskStatus.PENDING
        assert task.task_id in task_queue._processing
        
        # 清理
        task_queue._queue.clear()
        task_queue._tasks.clear()
        task_queue._processing.clear()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
