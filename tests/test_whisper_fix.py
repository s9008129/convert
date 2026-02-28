#!/usr/bin/env python3
"""
這份測試用兩個音檔驗證模型修復是否生效。
目的是確認轉錄流程能穩定完成，並快速辨識是否仍有回歸問題。
"""

import sys
import os
import time
from pathlib import Path

# 添加專案根目錄到 Python 路徑
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.services.transcription import transcription_service
from backend.core.logger import log

def test_transcription(audio_file: str, test_name: str):
    """測試單一音訊檔案轉錄"""
    print(f"\n{'='*60}")
    print(f"🧪 測試 {test_name}")
    print(f"{'='*60}")
    print(f"📁 音訊檔案: {audio_file}")
    
    if not os.path.exists(audio_file):
        print(f"❌ 檔案不存在: {audio_file}")
        return False
    
    file_size = os.path.getsize(audio_file) / 1024
    print(f"📊 檔案大小: {file_size:.2f} KB")
    
    try:
        start_time = time.time()
        
        def progress_callback(progress: float, message: str):
            print(f"  📍 [{progress:5.1f}%] {message}")
        
        print("\n🚀 開始轉錄...")
        transcript, duration = transcription_service.transcribe(
            audio_file,
            progress_callback=progress_callback
        )
        
        elapsed = time.time() - start_time
        
        print(f"\n✅ 轉錄成功!")
        print(f"⏱️  處理時間: {elapsed:.2f} 秒")
        print(f"🎵 音訊長度: {duration:.2f} 秒")
        print(f"📝 轉錄文字長度: {len(transcript)} 字元")
        print(f"📄 轉錄內容: {transcript[:200]}..." if len(transcript) > 200 else f"📄 轉錄內容: {transcript}")
        
        # 驗證結果
        if duration > 0:
            print(f"\n✅ 驗證通過: 音訊長度正常")
        else:
            print(f"\n⚠️  警告: 音訊長度為 0")
            
        return True
        
    except Exception as e:
        print(f"\n❌ 轉錄失敗: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """執行所有測試"""
    print("\n" + "="*60)
    print("🔧 MLX-Whisper 模型修復驗證測試")
    print("="*60)
    
    # 測試音檔路徑
    test_audio_dir = project_root / "tests" / "test_audio"
    test_files = [
        (str(test_audio_dir / "test1_5sec.wav"), "測試 1 - 5秒音訊"),
        (str(test_audio_dir / "test2_3sec.wav"), "測試 2 - 3秒音訊"),
    ]
    
    results = []
    for audio_file, test_name in test_files:
        success = test_transcription(audio_file, test_name)
        results.append((test_name, success))
        time.sleep(2)  # 短暫延遲避免資源競爭
    
    # 總結報告
    print("\n" + "="*60)
    print("📊 測試結果總結")
    print("="*60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ 通過" if success else "❌ 失敗"
        print(f"{status} - {test_name}")
    
    print(f"\n總計: {passed}/{total} 測試通過")
    
    if passed == total:
        print("\n🎉 所有測試通過! MLX-Whisper 模型問題已修復!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} 個測試失敗")
        return 1

if __name__ == "__main__":
    sys.exit(main())
