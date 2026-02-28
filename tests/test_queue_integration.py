"""
這份整合測試會模擬兩個音檔依序送件的實際情境。
主要確認排隊順序、等待時間與狀態更新都符合預期，
讓使用者看到的進度與系統實際處理流程一致。
"""

import asyncio
import pytest
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from backend.services.queue_manager import TaskQueueManager, task_queue
from backend.services.task_processor import TaskProcessor
from backend.models.schemas import TaskStatus, ProcessingMode


class TestQueueIntegration:
    """整合測試：模擬實際的音訊處理流程"""
    
    @pytest.mark.asyncio
    async def test_two_audio_files_queue_flow(self):
        """
        模擬上傳2個音訊檔案的完整流程
        
        驗證重點：
        1. 第一個任務立即開始處理（queue_position = None）
        2. 第二個任務等待第一個完成
        3. 排隊位置和等待時間計算正確
        4. 狀態轉換正確
        """
        with patch('backend.core.config.settings') as mock_settings:
            mock_settings.QUEUE_MAX_SIZE = 20
            mock_settings.MAX_CONCURRENT_TASKS = 1
            mock_settings.ESTIMATED_MINUTES_PER_TASK = 4
            mock_settings.uploads_dir = "temp/test_audio"
            mock_settings.outputs_dir = "temp/test_outputs"
            
            # 創建新的佇列管理器實例
            queue_mgr = TaskQueueManager()
            
            # 模擬上傳2個音訊檔案
            print("\n📤 模擬上傳第一個音訊檔案...")
            task1 = await queue_mgr.add_task(
                filename="test_audio_1.wav",
                original_filename="test_audio_1.wav",
                file_size=96044,
                processing_mode=ProcessingMode.LOCAL
            )
            
            assert task1 is not None
            assert task1.status == TaskStatus.QUEUED
            assert task1.queue_position == 1
            assert task1.estimated_wait_seconds == 0
            print(f"✅ 任務1已加入佇列: {task1.task_id}")
            print(f"   - 狀態: {task1.status.value}")
            print(f"   - 排隊位置: {task1.queue_position}")
            print(f"   - 預計等待: {task1.estimated_wait_seconds} 秒")
            
            print("\n📤 模擬上傳第二個音訊檔案...")
            task2 = await queue_mgr.add_task(
                filename="test_audio_2.wav",
                original_filename="test_audio_2.wav",
                file_size=96044,
                processing_mode=ProcessingMode.LOCAL
            )
            
            assert task2 is not None
            assert task2.status == TaskStatus.QUEUED
            assert task2.queue_position == 2
            assert task2.estimated_wait_seconds == 240  # 4分鐘
            print(f"✅ 任務2已加入佇列: {task2.task_id}")
            print(f"   - 狀態: {task2.status.value}")
            print(f"   - 排隊位置: {task2.queue_position}")
            print(f"   - 預計等待: {task2.estimated_wait_seconds} 秒 ({task2.estimated_wait_seconds // 60} 分鐘)")
            
            # 檢查佇列狀態
            queue_status = queue_mgr.get_queue_status()
            print(f"\n📊 目前佇列狀態:")
            print(f"   - 排隊中: {queue_status.total_queued} 個")
            print(f"   - 處理中: {queue_status.processing_count} 個")
            assert queue_status.total_queued == 2
            assert queue_status.processing_count == 0
            
            # 處理第一個任務
            print("\n🎬 開始處理第一個任務...")
            next_task = await queue_mgr.get_next_task()
            
            assert next_task.task_id == task1.task_id
            assert next_task.status == TaskStatus.PENDING
            assert next_task.queue_position is None  # ✅ 關鍵驗證
            assert next_task.estimated_wait_seconds == 0  # ✅ 關鍵驗證
            print(f"✅ 任務1開始處理:")
            print(f"   - 狀態: {next_task.status.value}")
            print(f"   - 排隊位置: {next_task.queue_position}")
            print(f"   - 預計等待: {next_task.estimated_wait_seconds} 秒")
            
            # 檢查第二個任務的位置更新
            task2_updated = queue_mgr.get_task(task2.task_id)
            assert task2_updated.queue_position == 1  # 自動晉升到第1位
            assert task2_updated.estimated_wait_seconds == 0  # 現在是下一個，不需等待
            print(f"\n📈 任務2位置自動更新:")
            print(f"   - 新排隊位置: {task2_updated.queue_position}")
            print(f"   - 新預計等待: {task2_updated.estimated_wait_seconds} 秒")
            
            # 檢查佇列狀態
            queue_status = queue_mgr.get_queue_status()
            print(f"\n📊 佇列狀態更新:")
            print(f"   - 排隊中: {queue_status.total_queued} 個")
            print(f"   - 處理中: {queue_status.processing_count} 個")
            assert queue_status.total_queued == 1
            assert queue_status.processing_count == 1
            
            # 完成第一個任務
            print("\n✅ 任務1處理完成")
            await queue_mgr.complete_task(task1.task_id, success=True)
            
            completed_task1 = queue_mgr.get_task(task1.task_id)
            assert completed_task1.status == TaskStatus.COMPLETED
            assert completed_task1.progress == 100.0
            
            # 處理第二個任務
            print("\n🎬 開始處理第二個任務...")
            next_task2 = await queue_mgr.get_next_task()
            
            assert next_task2.task_id == task2.task_id
            assert next_task2.status == TaskStatus.PENDING
            assert next_task2.queue_position is None  # ✅ 關鍵驗證
            assert next_task2.estimated_wait_seconds == 0  # ✅ 關鍵驗證
            print(f"✅ 任務2開始處理:")
            print(f"   - 狀態: {next_task2.status.value}")
            print(f"   - 排隊位置: {next_task2.queue_position}")
            print(f"   - 預計等待: {next_task2.estimated_wait_seconds} 秒")
            
            # 完成第二個任務
            print("\n✅ 任務2處理完成")
            await queue_mgr.complete_task(task2.task_id, success=True)
            
            completed_task2 = queue_mgr.get_task(task2.task_id)
            assert completed_task2.status == TaskStatus.COMPLETED
            assert completed_task2.progress == 100.0
            
            # 最終佇列狀態
            queue_status = queue_mgr.get_queue_status()
            print(f"\n📊 最終佇列狀態:")
            print(f"   - 排隊中: {queue_status.total_queued} 個")
            print(f"   - 處理中: {queue_status.processing_count} 個")
            assert queue_status.total_queued == 0
            assert queue_status.processing_count == 0
            
            print("\n" + "=" * 60)
            print("✅ 排隊邏輯修復驗證通過！")
            print("=" * 60)
            print("\n核心驗證點：")
            print("1. ✅ 第一個任務從佇列取出時，queue_position 立即設為 None")
            print("2. ✅ 第一個任務從佇列取出時，estimated_wait_seconds 設為 0")
            print("3. ✅ 第二個任務在第一個開始處理後，自動晉升到第1位")
            print("4. ✅ 佇列狀態計算正確（排隊中 vs 處理中）")
            print("5. ✅ 任務狀態轉換正確（QUEUED → PENDING → COMPLETED）")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
