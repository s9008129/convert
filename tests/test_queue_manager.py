#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
這份測試會確認任務排隊系統是否依規則運作。
它驗證新增、取件、取消、等待時間與併行限制等行為，
確保多個使用者同時送件時，流程仍公平且可預測。

測試流程（給非技術同仁快速理解）：
1) 先建立乾淨佇列，再模擬多筆任務送件。
2) 驗證先進先出（FIFO）、排隊位置變化與等待時間估算。
3) 驗證完成、失敗、取消後，系統是否正確更新狀態。

關鍵分支與錯誤情境：
- 佇列滿載時應拒絕新任務。
- 任務處理中時不得被取消。
- 查詢不存在任務或更新不存在任務時，系統應平穩處理不崩潰。
"""
import os
import sys
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest

# 使用暫存資料夾隔離測試，避免寫入正式資料目錄。
os.environ['DATA_DIR'] = tempfile.mkdtemp()

# 加入專案根目錄到匯入路徑，確保可直接載入 backend 模組。
sys.path.insert(0, str(Path(__file__).parent.parent))

from backend.models.schemas import TaskStatus, ProcessingMode, TaskInfo


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def queue_manager():
    """Create a fresh TaskQueueManager instance."""
    from backend.services.queue_manager import TaskQueueManager
    return TaskQueueManager()


@pytest.fixture
def mock_settings():
    """Mock settings with controllable values."""
    with patch('backend.services.queue_manager.settings') as mock:
        mock.QUEUE_MAX_SIZE = 50
        mock.MAX_CONCURRENT_TASKS = 1
        mock.ESTIMATED_MINUTES_PER_TASK = 4
        yield mock


# =============================================================================
# Add Task Tests
# =============================================================================

class TestAddTask:
    """Tests for adding tasks to the queue."""
    
    @pytest.mark.asyncio
    async def test_add_task_returns_task_info(self, queue_manager, mock_settings):
        """Test that add_task returns a TaskInfo object."""
        task = await queue_manager.add_task(
            filename="test123.mp3",
            original_filename="meeting.mp3",
            file_size=1024000
        )
        
        assert task is not None
        assert isinstance(task, TaskInfo)
        assert task.filename == "test123.mp3"
        assert task.original_filename == "meeting.mp3"
        assert task.file_size == 1024000
        assert task.status == TaskStatus.QUEUED
    
    @pytest.mark.asyncio
    async def test_add_task_generates_unique_id(self, queue_manager, mock_settings):
        """Test that each task gets a unique ID."""
        task1 = await queue_manager.add_task(
            filename="test1.mp3",
            original_filename="meeting1.mp3",
            file_size=1024
        )
        task2 = await queue_manager.add_task(
            filename="test2.mp3",
            original_filename="meeting2.mp3",
            file_size=1024
        )
        
        assert task1.task_id != task2.task_id
    
    @pytest.mark.asyncio
    async def test_add_task_assigns_queue_position(self, queue_manager, mock_settings):
        """Test that tasks get sequential queue positions."""
        task1 = await queue_manager.add_task(
            filename="test1.mp3",
            original_filename="meeting1.mp3",
            file_size=1024
        )
        task2 = await queue_manager.add_task(
            filename="test2.mp3",
            original_filename="meeting2.mp3",
            file_size=1024
        )
        task3 = await queue_manager.add_task(
            filename="test3.mp3",
            original_filename="meeting3.mp3",
            file_size=1024
        )
        
        assert task1.queue_position == 1
        assert task2.queue_position == 2
        assert task3.queue_position == 3
    
    @pytest.mark.asyncio
    async def test_add_task_with_processing_mode(self, queue_manager, mock_settings):
        """Test adding task with specific processing mode."""
        task = await queue_manager.add_task(
            filename="test.mp3",
            original_filename="meeting.mp3",
            file_size=1024,
            processing_mode=ProcessingMode.CLOUD
        )
        
        assert task.processing_mode == ProcessingMode.CLOUD
    
    @pytest.mark.asyncio
    async def test_add_task_with_user_prompt(self, queue_manager, mock_settings):
        """Test adding task with user prompt."""
        user_prompt = "請特別注意技術討論"
        task = await queue_manager.add_task(
            filename="test.mp3",
            original_filename="meeting.mp3",
            file_size=1024,
            user_prompt=user_prompt
        )
        
        assert task.user_prompt == user_prompt
    
    @pytest.mark.asyncio
    async def test_add_task_queue_full(self, queue_manager, mock_settings):
        """Test that add_task returns None when queue is full."""
        mock_settings.QUEUE_MAX_SIZE = 2
        
        await queue_manager.add_task(
            filename="test1.mp3",
            original_filename="m1.mp3",
            file_size=1024
        )
        await queue_manager.add_task(
            filename="test2.mp3",
            original_filename="m2.mp3",
            file_size=1024
        )
        
        # Queue is now full
        task3 = await queue_manager.add_task(
            filename="test3.mp3",
            original_filename="m3.mp3",
            file_size=1024
        )
        
        assert task3 is None
    
    @pytest.mark.asyncio
    async def test_add_task_sets_estimated_wait(self, queue_manager, mock_settings):
        """Test that estimated wait time is calculated."""
        task = await queue_manager.add_task(
            filename="test.mp3",
            original_filename="meeting.mp3",
            file_size=1024
        )
        
        assert task.estimated_wait_seconds is not None
        assert task.estimated_wait_seconds >= 0


# =============================================================================
# Get Task Tests
# =============================================================================

class TestGetTask:
    """Tests for retrieving tasks from the queue."""
    
    @pytest.mark.asyncio
    async def test_get_task_returns_task(self, queue_manager, mock_settings):
        """Test that get_task returns the task by ID."""
        added_task = await queue_manager.add_task(
            filename="test.mp3",
            original_filename="meeting.mp3",
            file_size=1024
        )
        
        retrieved_task = queue_manager.get_task(added_task.task_id)
        
        assert retrieved_task is not None
        assert retrieved_task.task_id == added_task.task_id
    
    @pytest.mark.asyncio
    async def test_get_task_not_found(self, queue_manager, mock_settings):
        """Test that get_task returns None for non-existent task."""
        result = queue_manager.get_task("nonexistent123")
        
        assert result is None


# =============================================================================
# Get Next Task Tests
# =============================================================================

class TestGetNextTask:
    """Tests for getting the next task to process (FIFO)."""
    
    @pytest.mark.asyncio
    async def test_get_next_task_fifo_order(self, queue_manager, mock_settings):
        """Test that tasks are retrieved in FIFO order."""
        task1 = await queue_manager.add_task(
            filename="first.mp3",
            original_filename="first.mp3",
            file_size=1024
        )
        task2 = await queue_manager.add_task(
            filename="second.mp3",
            original_filename="second.mp3",
            file_size=1024
        )
        task3 = await queue_manager.add_task(
            filename="third.mp3",
            original_filename="third.mp3",
            file_size=1024
        )
        
        # Should get first task first
        next_task = await queue_manager.get_next_task()
        assert next_task.task_id == task1.task_id
        
        # Complete first task
        await queue_manager.complete_task(task1.task_id)
        
        # Should get second task next
        next_task = await queue_manager.get_next_task()
        assert next_task.task_id == task2.task_id
    
    @pytest.mark.asyncio
    async def test_get_next_task_empty_queue(self, queue_manager, mock_settings):
        """Test get_next_task when queue is empty."""
        result = await queue_manager.get_next_task()
        
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_next_task_respects_concurrent_limit(self, queue_manager, mock_settings):
        """Test that concurrent task limit is respected."""
        mock_settings.MAX_CONCURRENT_TASKS = 1
        
        await queue_manager.add_task(
            filename="test1.mp3",
            original_filename="m1.mp3",
            file_size=1024
        )
        await queue_manager.add_task(
            filename="test2.mp3",
            original_filename="m2.mp3",
            file_size=1024
        )
        
        # Get first task
        task1 = await queue_manager.get_next_task()
        assert task1 is not None
        
        # Should not get another while first is processing
        task2 = await queue_manager.get_next_task()
        assert task2 is None
    
    @pytest.mark.asyncio
    async def test_get_next_task_updates_status(self, queue_manager, mock_settings):
        """Test that get_next_task updates task status to PENDING."""
        await queue_manager.add_task(
            filename="test.mp3",
            original_filename="meeting.mp3",
            file_size=1024
        )
        
        task = await queue_manager.get_next_task()
        
        assert task.status == TaskStatus.PENDING
    
    @pytest.mark.asyncio
    async def test_get_next_task_clears_queue_position(self, queue_manager, mock_settings):
        """Test that get_next_task clears queue_position."""
        await queue_manager.add_task(
            filename="test.mp3",
            original_filename="meeting.mp3",
            file_size=1024
        )
        
        task = await queue_manager.get_next_task()
        
        assert task.queue_position is None
    
    @pytest.mark.asyncio
    async def test_get_next_task_sets_started_at(self, queue_manager, mock_settings):
        """Test that get_next_task sets started_at timestamp."""
        await queue_manager.add_task(
            filename="test.mp3",
            original_filename="meeting.mp3",
            file_size=1024
        )
        
        task = await queue_manager.get_next_task()
        
        assert task.started_at is not None
        assert isinstance(task.started_at, datetime)


# =============================================================================
# Complete Task Tests
# =============================================================================

class TestCompleteTask:
    """Tests for completing tasks."""
    
    @pytest.mark.asyncio
    async def test_complete_task_success(self, queue_manager, mock_settings):
        """Test successfully completing a task."""
        task = await queue_manager.add_task(
            filename="test.mp3",
            original_filename="meeting.mp3",
            file_size=1024
        )
        task = await queue_manager.get_next_task()
        
        await queue_manager.complete_task(task.task_id, success=True)
        
        completed = queue_manager.get_task(task.task_id)
        assert completed.status == TaskStatus.COMPLETED
        assert completed.progress == 100.0
        assert completed.completed_at is not None
    
    @pytest.mark.asyncio
    async def test_complete_task_failure(self, queue_manager, mock_settings):
        """Test marking a task as failed."""
        task = await queue_manager.add_task(
            filename="test.mp3",
            original_filename="meeting.mp3",
            file_size=1024
        )
        task = await queue_manager.get_next_task()
        
        await queue_manager.complete_task(
            task.task_id,
            success=False,
            error_message="Processing error"
        )
        
        failed = queue_manager.get_task(task.task_id)
        assert failed.status == TaskStatus.FAILED
        assert failed.error_message == "Processing error"
    
    @pytest.mark.asyncio
    async def test_complete_task_frees_slot(self, queue_manager, mock_settings):
        """Test that completing a task frees a processing slot."""
        mock_settings.MAX_CONCURRENT_TASKS = 1
        
        await queue_manager.add_task(
            filename="test1.mp3",
            original_filename="m1.mp3",
            file_size=1024
        )
        await queue_manager.add_task(
            filename="test2.mp3",
            original_filename="m2.mp3",
            file_size=1024
        )
        
        task1 = await queue_manager.get_next_task()
        
        # Second task should not be available yet
        assert await queue_manager.get_next_task() is None
        
        # Complete first task
        await queue_manager.complete_task(task1.task_id)
        
        # Now second task should be available
        task2 = await queue_manager.get_next_task()
        assert task2 is not None


# =============================================================================
# Cancel Task Tests
# =============================================================================

class TestCancelTask:
    """Tests for cancelling tasks."""
    
    @pytest.mark.asyncio
    async def test_cancel_queued_task(self, queue_manager, mock_settings):
        """Test cancelling a queued task."""
        task = await queue_manager.add_task(
            filename="test.mp3",
            original_filename="meeting.mp3",
            file_size=1024
        )
        
        result = await queue_manager.cancel_task(task.task_id)
        
        assert result is True
        cancelled = queue_manager.get_task(task.task_id)
        assert cancelled.status == TaskStatus.CANCELLED
    
    @pytest.mark.asyncio
    async def test_cancel_processing_task_fails(self, queue_manager, mock_settings):
        """Test that cancelling a processing task fails."""
        task = await queue_manager.add_task(
            filename="test.mp3",
            original_filename="meeting.mp3",
            file_size=1024
        )
        await queue_manager.get_next_task()  # Start processing
        
        result = await queue_manager.cancel_task(task.task_id)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_cancel_nonexistent_task(self, queue_manager, mock_settings):
        """Test cancelling a non-existent task."""
        result = await queue_manager.cancel_task("nonexistent")
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_cancel_updates_queue_positions(self, queue_manager, mock_settings):
        """Test that cancelling a task updates queue positions."""
        task1 = await queue_manager.add_task(
            filename="test1.mp3",
            original_filename="m1.mp3",
            file_size=1024
        )
        task2 = await queue_manager.add_task(
            filename="test2.mp3",
            original_filename="m2.mp3",
            file_size=1024
        )
        task3 = await queue_manager.add_task(
            filename="test3.mp3",
            original_filename="m3.mp3",
            file_size=1024
        )
        
        # Cancel first task
        await queue_manager.cancel_task(task1.task_id)
        
        # Remaining tasks should have updated positions
        t2 = queue_manager.get_task(task2.task_id)
        t3 = queue_manager.get_task(task3.task_id)
        
        assert t2.queue_position == 1
        assert t3.queue_position == 2


# =============================================================================
# Queue Position Tests
# =============================================================================

class TestQueuePosition:
    """Tests for queue position tracking."""
    
    @pytest.mark.asyncio
    async def test_get_task_position(self, queue_manager, mock_settings):
        """Test getting task position in queue."""
        task1 = await queue_manager.add_task(
            filename="test1.mp3",
            original_filename="m1.mp3",
            file_size=1024
        )
        task2 = await queue_manager.add_task(
            filename="test2.mp3",
            original_filename="m2.mp3",
            file_size=1024
        )
        
        pos1 = queue_manager.get_task_position(task1.task_id)
        pos2 = queue_manager.get_task_position(task2.task_id)
        
        assert pos1 == 1
        assert pos2 == 2
    
    @pytest.mark.asyncio
    async def test_get_task_position_not_in_queue(self, queue_manager, mock_settings):
        """Test getting position for task not in queue."""
        task = await queue_manager.add_task(
            filename="test.mp3",
            original_filename="meeting.mp3",
            file_size=1024
        )
        await queue_manager.get_next_task()  # Remove from queue
        
        position = queue_manager.get_task_position(task.task_id)
        
        assert position is None
    
    @pytest.mark.asyncio
    async def test_get_task_position_nonexistent(self, queue_manager, mock_settings):
        """Test getting position for non-existent task."""
        position = queue_manager.get_task_position("nonexistent")
        
        assert position is None


# =============================================================================
# Queue Status Tests
# =============================================================================

class TestQueueStatus:
    """Tests for queue status reporting."""
    
    @pytest.mark.asyncio
    async def test_get_queue_status_empty(self, queue_manager, mock_settings):
        """Test queue status when empty."""
        status = queue_manager.get_queue_status()
        
        assert status.total_queued == 0
        assert status.processing_count == 0
    
    @pytest.mark.asyncio
    async def test_get_queue_status_with_tasks(self, queue_manager, mock_settings):
        """Test queue status with tasks."""
        await queue_manager.add_task(
            filename="test1.mp3",
            original_filename="m1.mp3",
            file_size=1024
        )
        await queue_manager.add_task(
            filename="test2.mp3",
            original_filename="m2.mp3",
            file_size=1024
        )
        
        status = queue_manager.get_queue_status()
        
        assert status.total_queued == 2
        assert status.processing_count == 0
    
    @pytest.mark.asyncio
    async def test_get_queue_status_with_processing(self, queue_manager, mock_settings):
        """Test queue status with processing task."""
        await queue_manager.add_task(
            filename="test1.mp3",
            original_filename="m1.mp3",
            file_size=1024
        )
        await queue_manager.add_task(
            filename="test2.mp3",
            original_filename="m2.mp3",
            file_size=1024
        )
        
        await queue_manager.get_next_task()  # Start processing one
        
        status = queue_manager.get_queue_status()
        
        assert status.total_queued == 1
        assert status.processing_count == 1
    
    @pytest.mark.asyncio
    async def test_get_queue_status_includes_config(self, queue_manager, mock_settings):
        """Test that queue status includes config values."""
        status = queue_manager.get_queue_status()
        
        assert status.max_concurrent == mock_settings.MAX_CONCURRENT_TASKS
        assert status.queue_max_size == mock_settings.QUEUE_MAX_SIZE


# =============================================================================
# Progress Update Tests
# =============================================================================

class TestProgressUpdate:
    """Tests for updating task progress."""
    
    @pytest.mark.asyncio
    async def test_update_task_progress(self, queue_manager, mock_settings):
        """Test updating task progress."""
        task = await queue_manager.add_task(
            filename="test.mp3",
            original_filename="meeting.mp3",
            file_size=1024
        )
        
        queue_manager.update_task_progress(task.task_id, 50.0, "轉錄中")
        
        updated = queue_manager.get_task(task.task_id)
        assert updated.progress == 50.0
        assert updated.stage == "轉錄中"
    
    @pytest.mark.asyncio
    async def test_update_task_progress_with_status(self, queue_manager, mock_settings):
        """Test updating task progress with status change."""
        task = await queue_manager.add_task(
            filename="test.mp3",
            original_filename="meeting.mp3",
            file_size=1024
        )
        
        queue_manager.update_task_progress(
            task.task_id,
            25.0,
            "轉錄中",
            status=TaskStatus.TRANSCRIBING
        )
        
        updated = queue_manager.get_task(task.task_id)
        assert updated.status == TaskStatus.TRANSCRIBING
    
    def test_update_nonexistent_task(self, queue_manager, mock_settings):
        """Test updating non-existent task."""
        # Should not raise an exception
        queue_manager.update_task_progress("nonexistent", 50.0, "test")


# =============================================================================
# Wait Time Calculation Tests
# =============================================================================

class TestWaitTimeCalculation:
    """Tests for wait time estimation."""
    
    @pytest.mark.asyncio
    async def test_wait_time_single_task(self, queue_manager, mock_settings):
        """Test wait time for single task in queue."""
        mock_settings.ESTIMATED_MINUTES_PER_TASK = 4
        mock_settings.MAX_CONCURRENT_TASKS = 1
        
        task = await queue_manager.add_task(
            filename="test.mp3",
            original_filename="meeting.mp3",
            file_size=1024
        )
        
        # First task should have 0 wait time (it's next)
        assert task.estimated_wait_seconds == 0
    
    @pytest.mark.asyncio
    async def test_wait_time_multiple_tasks(self, queue_manager, mock_settings):
        """Test wait time for multiple tasks."""
        mock_settings.ESTIMATED_MINUTES_PER_TASK = 4
        mock_settings.MAX_CONCURRENT_TASKS = 1
        
        task1 = await queue_manager.add_task(
            filename="test1.mp3",
            original_filename="m1.mp3",
            file_size=1024
        )
        task2 = await queue_manager.add_task(
            filename="test2.mp3",
            original_filename="m2.mp3",
            file_size=1024
        )
        task3 = await queue_manager.add_task(
            filename="test3.mp3",
            original_filename="m3.mp3",
            file_size=1024
        )
        
        # Each subsequent task should have longer wait time
        assert task2.estimated_wait_seconds > task1.estimated_wait_seconds
        assert task3.estimated_wait_seconds > task2.estimated_wait_seconds
    
    @pytest.mark.asyncio
    async def test_wait_time_considers_concurrent_tasks(self, queue_manager, mock_settings):
        """Test that wait time considers concurrent task limit."""
        mock_settings.ESTIMATED_MINUTES_PER_TASK = 4
        mock_settings.MAX_CONCURRENT_TASKS = 2
        
        task1 = await queue_manager.add_task(
            filename="test1.mp3",
            original_filename="m1.mp3",
            file_size=1024
        )
        task2 = await queue_manager.add_task(
            filename="test2.mp3",
            original_filename="m2.mp3",
            file_size=1024
        )
        
        # With 2 concurrent tasks, first 2 should have same or very similar wait time
        # Allow small difference due to potential timing variations
        wait_time_diff = abs(task1.estimated_wait_seconds - task2.estimated_wait_seconds)
        assert wait_time_diff <= 1, f"Wait times differ by {wait_time_diff} seconds"


# =============================================================================
# Get All Tasks Tests
# =============================================================================

class TestGetAllTasks:
    """Tests for getting all tasks."""
    
    @pytest.mark.asyncio
    async def test_get_all_tasks_empty(self, queue_manager, mock_settings):
        """Test get_all_tasks when empty."""
        tasks = queue_manager.get_all_tasks()
        
        assert tasks == []
    
    @pytest.mark.asyncio
    async def test_get_all_tasks(self, queue_manager, mock_settings):
        """Test get_all_tasks returns all tasks."""
        await queue_manager.add_task(
            filename="test1.mp3",
            original_filename="m1.mp3",
            file_size=1024
        )
        await queue_manager.add_task(
            filename="test2.mp3",
            original_filename="m2.mp3",
            file_size=1024
        )
        
        tasks = queue_manager.get_all_tasks()
        
        assert len(tasks) == 2
        assert all(isinstance(t, TaskInfo) for t in tasks)


# =============================================================================
# Concurrency Tests
# =============================================================================

class TestConcurrency:
    """Tests for concurrent operations."""
    
    @pytest.mark.asyncio
    async def test_concurrent_add_tasks(self, queue_manager, mock_settings):
        """Test adding tasks concurrently."""
        mock_settings.QUEUE_MAX_SIZE = 100
        
        async def add_task(i):
            return await queue_manager.add_task(
                filename=f"test{i}.mp3",
                original_filename=f"m{i}.mp3",
                file_size=1024
            )
        
        # Add 10 tasks concurrently
        tasks = await asyncio.gather(*[add_task(i) for i in range(10)])
        
        # All should succeed
        assert len([t for t in tasks if t is not None]) == 10
        
        # All should have unique IDs
        task_ids = [t.task_id for t in tasks]
        assert len(set(task_ids)) == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
