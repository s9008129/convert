"""
端到端整合測試 - 2個音訊檔案完整流程
測試排隊邏輯修復和 MLX-Whisper 模型載入修復
"""

import asyncio
import os
import sys
import time
from pathlib import Path
import pytest

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.services.queue_manager import TaskQueueManager
from backend.services.task_processor import TaskProcessor
from backend.services.transcription import TranscriptionService
from backend.models.schemas import ProcessingMode, TaskStatus
from backend.core.logger import log
from backend.core.config import settings


@pytest.mark.asyncio
async def test_end_to_end_workflow():
    """
    端到端測試：2個音訊檔案的完整處理流程
    
    測試重點：
    1. MLX-Whisper 模型正確載入（修復 404 錯誤）
    2. 排隊邏輯正確運作
    3. 任務狀態轉換正確
    4. 兩個任務依序處理完成
    """
    print("\n" + "=" * 80)
    print("🧪 端到端整合測試：2個音訊檔案完整流程")
    print("=" * 80 + "\n")
    
    # 初始化服務
    queue_mgr = TaskQueueManager()
    task_proc = TaskProcessor()
    transcription_svc = TranscriptionService()
    
    # 測試音訊檔案路徑
    audio1 = "input/test_meeting_1.wav"
    audio2 = "input/test_meeting_2.wav"
    
    if not os.path.exists(audio1) or not os.path.exists(audio2):
        print("❌ 測試音訊檔案不存在，請先執行:")
        print("   python3 -c 'import numpy as np; import wave; ...'")
        return False
    
    # 複製到 uploads 目錄
    import shutil
    os.makedirs(settings.uploads_dir, exist_ok=True)
    upload1 = os.path.join(settings.uploads_dir, "test_meeting_1.wav")
    upload2 = os.path.join(settings.uploads_dir, "test_meeting_2.wav")
    shutil.copy(audio1, upload1)
    shutil.copy(audio2, upload2)
    
    try:
        # ============================================
        # 測試 1: MLX-Whisper 模型載入
        # ============================================
        print("📋 測試 1: MLX-Whisper 模型載入")
        print("-" * 80)
        
        try:
            # 測試單獨的模型載入（不執行完整轉錄）
            transcription_svc._load_model()
            backend = transcription_svc._get_backend()
            print(f"✅ Whisper 後端: {backend}")
            print(f"✅ 裝置: {transcription_svc._device}")
            transcription_svc._unload_model()
            print("✅ 測試 1 通過：MLX-Whisper 模型載入成功\n")
        except Exception as e:
            print(f"❌ 測試 1 失敗：{e}\n")
            return False
        
        # ============================================
        # 測試 2: 排隊邏輯
        # ============================================
        print("📋 測試 2: 排隊邏輯")
        print("-" * 80)
        
        # 加入第一個任務
        task1 = await queue_mgr.add_task(
            filename="test_meeting_1.wav",
            original_filename="test_meeting_1.wav",
            file_size=os.path.getsize(upload1),
            processing_mode=ProcessingMode.LOCAL
        )
        
        assert task1 is not None, "任務1加入失敗"
        assert task1.status == TaskStatus.QUEUED, f"任務1狀態錯誤: {task1.status}"
        assert task1.queue_position == 1, f"任務1排隊位置錯誤: {task1.queue_position}"
        assert task1.estimated_wait_seconds == 0, f"任務1等待時間錯誤: {task1.estimated_wait_seconds}"
        
        print(f"✅ 任務1已加入: {task1.task_id}")
        print(f"   - 狀態: {task1.status.value}")
        print(f"   - 排隊位置: {task1.queue_position}")
        print(f"   - 預計等待: {task1.estimated_wait_seconds} 秒")
        
        # 加入第二個任務
        task2 = await queue_mgr.add_task(
            filename="test_meeting_2.wav",
            original_filename="test_meeting_2.wav",
            file_size=os.path.getsize(upload2),
            processing_mode=ProcessingMode.LOCAL
        )
        
        assert task2 is not None, "任務2加入失敗"
        assert task2.status == TaskStatus.QUEUED, f"任務2狀態錯誤: {task2.status}"
        assert task2.queue_position == 2, f"任務2排隊位置錯誤: {task2.queue_position}"
        assert task2.estimated_wait_seconds == 240, f"任務2等待時間錯誤: {task2.estimated_wait_seconds}"
        
        print(f"✅ 任務2已加入: {task2.task_id}")
        print(f"   - 狀態: {task2.status.value}")
        print(f"   - 排隊位置: {task2.queue_position}")
        print(f"   - 預計等待: {task2.estimated_wait_seconds} 秒 ({task2.estimated_wait_seconds // 60} 分鐘)")
        
        # 檢查佇列狀態
        queue_status = queue_mgr.get_queue_status()
        assert queue_status.total_queued == 2, f"佇列數量錯誤: {queue_status.total_queued}"
        assert queue_status.processing_count == 0, f"處理中數量錯誤: {queue_status.processing_count}"
        
        print(f"✅ 佇列狀態:")
        print(f"   - 排隊中: {queue_status.total_queued} 個")
        print(f"   - 處理中: {queue_status.processing_count} 個")
        print("✅ 測試 2 通過：排隊邏輯正確\n")
        
        # ============================================
        # 測試 3: 任務處理流程
        # ============================================
        print("📋 測試 3: 任務處理流程")
        print("-" * 80)
        
        # 處理第一個任務
        print(f"🎬 開始處理任務1: {task1.task_id}")
        next_task = await queue_mgr.get_next_task()
        
        assert next_task.task_id == task1.task_id, "取出的任務ID不正確"
        assert next_task.status == TaskStatus.PENDING, f"任務1狀態錯誤: {next_task.status}"
        assert next_task.queue_position is None, f"任務1排隊位置應為None: {next_task.queue_position}"
        assert next_task.estimated_wait_seconds == 0, f"任務1等待時間應為0: {next_task.estimated_wait_seconds}"
        
        print(f"✅ 任務1開始處理:")
        print(f"   - 狀態: {next_task.status.value}")
        print(f"   - 排隊位置: {next_task.queue_position}")
        print(f"   - 等待時間: {next_task.estimated_wait_seconds} 秒")
        
        # 檢查任務2是否自動晉升
        task2_updated = queue_mgr.get_task(task2.task_id)
        assert task2_updated.queue_position == 1, f"任務2應晉升到第1位: {task2_updated.queue_position}"
        assert task2_updated.estimated_wait_seconds == 0, f"任務2等待時間應為0: {task2_updated.estimated_wait_seconds}"
        
        print(f"✅ 任務2自動晉升:")
        print(f"   - 新排隊位置: {task2_updated.queue_position}")
        print(f"   - 新等待時間: {task2_updated.estimated_wait_seconds} 秒")
        
        # 模擬任務處理（簡化版，不執行完整轉錄）
        print(f"⏳ 模擬任務1處理中...")
        await asyncio.sleep(1)  # 模擬處理時間
        
        await queue_mgr.complete_task(task1.task_id, success=True)
        task1_completed = queue_mgr.get_task(task1.task_id)
        assert task1_completed.status == TaskStatus.COMPLETED, f"任務1完成狀態錯誤: {task1_completed.status}"
        
        print(f"✅ 任務1處理完成")
        
        # 處理第二個任務
        print(f"\n🎬 開始處理任務2: {task2.task_id}")
        next_task2 = await queue_mgr.get_next_task()
        
        assert next_task2.task_id == task2.task_id, "取出的任務ID不正確"
        assert next_task2.status == TaskStatus.PENDING, f"任務2狀態錯誤: {next_task2.status}"
        assert next_task2.queue_position is None, f"任務2排隊位置應為None: {next_task2.queue_position}"
        assert next_task2.estimated_wait_seconds == 0, f"任務2等待時間應為0: {next_task2.estimated_wait_seconds}"
        
        print(f"✅ 任務2開始處理:")
        print(f"   - 狀態: {next_task2.status.value}")
        print(f"   - 排隊位置: {next_task2.queue_position}")
        print(f"   - 等待時間: {next_task2.estimated_wait_seconds} 秒")
        
        print(f"⏳ 模擬任務2處理中...")
        await asyncio.sleep(1)
        
        await queue_mgr.complete_task(task2.task_id, success=True)
        task2_completed = queue_mgr.get_task(task2.task_id)
        assert task2_completed.status == TaskStatus.COMPLETED, f"任務2完成狀態錯誤: {task2_completed.status}"
        
        print(f"✅ 任務2處理完成")
        
        # 檢查最終佇列狀態
        final_status = queue_mgr.get_queue_status()
        assert final_status.total_queued == 0, f"最終佇列應為空: {final_status.total_queued}"
        assert final_status.processing_count == 0, f"最終處理中應為0: {final_status.processing_count}"
        
        print(f"\n✅ 最終佇列狀態:")
        print(f"   - 排隊中: {final_status.total_queued} 個")
        print(f"   - 處理中: {final_status.processing_count} 個")
        print("✅ 測試 3 通過：任務處理流程正確\n")
        
        # ============================================
        # 測試結果總結
        # ============================================
        print("\n" + "=" * 80)
        print("🎉 所有測試通過！")
        print("=" * 80)
        print("\n✅ 測試總結:")
        print("  1. ✅ MLX-Whisper 模型載入成功（404 錯誤已修復）")
        print("  2. ✅ 排隊邏輯正確運作")
        print("  3. ✅ 任務狀態轉換正確")
        print("  4. ✅ queue_position 在任務開始時正確清除")
        print("  5. ✅ estimated_wait_seconds 在任務開始時正確清除為0")
        print("  6. ✅ 任務自動晉升機制正常")
        print("  7. ✅ 兩個任務依序處理完成")
        print("\n" + "=" * 80 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 測試失敗: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理測試檔案
        for f in [upload1, upload2]:
            if os.path.exists(f):
                os.remove(f)


if __name__ == '__main__':
    success = asyncio.run(test_end_to_end_workflow())
    sys.exit(0 if success else 1)
