#!/usr/bin/env python3
"""
這份測試會直接驗證語音模型能否順利載入並產生轉錄結果。
若模型或環境有問題，可快速從這裡看出基本功能是否正常。
"""

import sys
import mlx_whisper

print("="*60)
print("🧪 MLX-Whisper 直接測試")
print("="*60)

test_file = "/Users/hsiaojohnny/dev/convert/tests/test_audio/test1_5sec.wav"
model_name = "mlx-community/whisper-medium"

print(f"\n📁 測試音檔: {test_file}")
print(f"🤖 模型: {model_name}")
print("\n🚀 開始轉錄...\n")

try:
    result = mlx_whisper.transcribe(
        test_file,
        path_or_hf_repo=model_name,
        language="zh",
        word_timestamps=False
    )
    
    print("✅ 轉錄成功!")
    print(f"📝 Segments: {len(result.get('segments', []))}")
    
    transcript = " ".join([seg['text'].strip() for seg in result.get('segments', [])])
    print(f"📄 轉錄文字: '{transcript}'")
    
    if len(result.get('segments', [])) == 0:
        print("\n⚠️  注意: 沒有偵測到語音段落（這對純音調音訊是正常的）")
    else:
        print(f"\n🎉 MLX-Whisper 正常運作!")
        
except Exception as e:
    print(f"\n❌ 轉錄失敗: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*60)
print("✅ MLX-Whisper 模型測試完成")
print("="*60)
