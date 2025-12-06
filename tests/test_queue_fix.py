"""
排隊邏輯修復驗證測試
驗證修復後的排隊邏輯是否正確處理任務狀態轉換
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from backend.services.queue_manager import TaskQueueManager
from backend.models.schemas import TaskStatus, ProcessingMode


class TestQueueLogicFix:
    """測試排隊邏輯修復"""
    
    @pytest.fixture
    def queue_manager(self):
        """建立測試用的排隊管理器"""
        return TaskQueueManager()
    
    @pytest.mark.asyncio
    async def test_first_task_immediately_processing(self, queue_manager):
        """
        測試：第一個任務應該立即進入處理狀態
        
        修復前問題：任務從 QUEUED → PENDING，但 queue_position 沒有清除，導致顯示「排隊位置1但等待0分鐘」
        修復後行為：任務從 QUEUED → PENDING，queue_position 立即變為 None，estimated_wait_seconds 變為 0
        """
        with patch('backend.core.config.settings') as mock_settings:
            mock_settings.QUEUE_MAX_SIZE = 20
            mock_settings.MAX_CONCURRENT_TASKS = 1
            mock_settings.ESTIMATED_MINUTES_PER_TASK = 4
            
            # 1. 加入第一個任務
            task1 = await queue_manager.add_task(
                filename="test1.wav",
                original_filename="test1.wav",
                file_size=96044,
                processing_mode=ProcessingMode.LOCAL
            )
            
            assert task1 is not None
            assert task1.status == TaskStatus.QUEUED
            assert task1.queue_position == 1
            assert task1.estimated_wait_seconds == 0  # 第一個任務不需要等待
            
            # 2. 取出第一個任務（應該立即開始處理）
            next_task = await queue_manager.get_next_task()
            
            assert next_task is not None
            assert next_task.task_id == task1.task_id
            
            # ✅ 核心驗證：狀態應該是 PENDING（準備處理）
            assert next_task.status == TaskStatus.PENDING
            
            # ✅ 核心驗證：排隊位置應該被清除
            assert next_task.queue_position is None
            
            # ✅ 核心驗證：等待時間應該為0
            assert next_task.estimated_wait_seconds == 0
            
            # ✅ 核心驗證：started_at 應該被設定
            assert next_task.started_at is not None
    
    @pytest.mark.asyncio
    async def test_second_task_waits_correctly(self, queue_manager):
        """
        測試：第二個任務在第一個任務處理中時，應該正確顯示等待
        """
        with patch('backend.core.config.settings') as mock_settings:
            mock_settings.QUEUE_MAX_SIZE = 20
            mock_settings.MAX_CONCURRENT_TASKS = 1
            mock_settings.ESTIMATED_MINUTES_PER_TASK = 4
            
            # 1. 加入兩個任務
            task1 = await queue_manager.add_task(
                filename="test1.wav",
                original_filename="test1.wav",
                file_size=96044
            )
            
            task2 = await queue_manager.add_task(
                filename="test2.wav",
                original_filename="test2.wav",
                file_size=96044
            )
            
            # 2. 第二個任務應該排在第2位
            assert task2.queue_position == 2
            assert task2.estimated_wait_seconds == 240  # 4分鐘 = 240秒
            
            # 3. 取出第一個任務
            next_task = await queue_manager.get_next_task()
            assert next_task.task_id == task1.task_id
            assert next_task.status == TaskStatus.PENDING
            assert next_task.queue_position is None
            
            # 4. 第二個任務應該自動更新為第1位
            task2_updated = queue_manager.get_task(task2.task_id)
            assert task2_updated.queue_position == 1
            assert task2_updated.estimated_wait_seconds == 0  # 現在是下一個，不需要等待
            
            # 5. 第一個任務完成
            await queue_manager.complete_task(task1.task_id, success=True)
            
            # 6. 取出第二個任務
            next_task2 = await queue_manager.get_next_task()
            assert next_task2.task_id == task2.task_id
            assert next_task2.status == TaskStatus.PENDING
            assert next_task2.queue_position is None
            assert next_task2.estimated_wait_seconds == 0
    
    @pytest.mark.asyncio
    async def test_task_status_transition(self, queue_manager):
        """
        測試：任務狀態轉換流程
        
        正確的流程應該是：
        QUEUED (加入佇列) → PENDING (從佇列取出，準備處理) → TRANSCRIBING/SUMMARIZING → COMPLETED/FAILED
        """
        with patch('backend.core.config.settings') as mock_settings:
            mock_settings.QUEUE_MAX_SIZE = 20
            mock_settings.MAX_CONCURRENT_TASKS = 1
            mock_settings.ESTIMATED_MINUTES_PER_TASK = 4
            
            # 1. 加入任務 → QUEUED
            task = await queue_manager.add_task(
                filename="test.wav",
                original_filename="test.wav",
                file_size=96044
            )
            
            assert task.status == TaskStatus.QUEUED
            assert task.queue_position == 1
            
            # 2. 取出任務 → PENDING（準備處理）
            next_task = await queue_manager.get_next_task()
            assert next_task.status == TaskStatus.PENDING
            assert next_task.queue_position is None  # ✅ 關鍵：排隊位置已清除
            assert next_task.estimated_wait_seconds == 0  # ✅ 關鍵：等待時間為0
            
            # 3. 任務完成 → COMPLETED
            await queue_manager.complete_task(task.task_id, success=True)
            completed_task = queue_manager.get_task(task.task_id)
            assert completed_task.status == TaskStatus.COMPLETED
            assert completed_task.progress == 100.0
    
    @pytest.mark.asyncio
    async def test_queue_status_accuracy(self, queue_manager):
        """
        測試：佇列狀態的準確性
        
        確保前端顯示的排隊人數和位置是準確的
        """
        with patch('backend.core.config.settings') as mock_settings:
            mock_settings.QUEUE_MAX_SIZE = 20
            mock_settings.MAX_CONCURRENT_TASKS = 1
            mock_settings.ESTIMATED_MINUTES_PER_TASK = 4
            
            # 1. 空佇列狀態
            status = queue_manager.get_queue_status()
            assert status.total_queued == 0
            assert status.processing_count == 0
            
            # 2. 加入3個任務
            task1 = await queue_manager.add_task("test1.wav", "test1.wav", 96044)
            task2 = await queue_manager.add_task("test2.wav", "test2.wav", 96044)
            task3 = await queue_manager.add_task("test3.wav", "test3.wav", 96044)
            
            status = queue_manager.get_queue_status()
            assert status.total_queued == 3
            assert status.processing_count == 0
            
            # 3. 取出第一個任務
            await queue_manager.get_next_task()
            
            status = queue_manager.get_queue_status()
            assert status.total_queued == 2  # 剩餘2個在排隊
            assert status.processing_count == 1  # 1個正在處理


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
