#!/usr/bin/env python3
"""
MeetingScribe v4.0.0 - 模型預載腳本

此腳本用於首次部署前預先下載所需模型：
1. Breeze-ASR-25 (ASR 模型) - 約 3GB

使用方式：
    python scripts/download_models.py

環境變數：
    HF_HOME: Hugging Face 快取目錄（預設: ./models）
"""

import os
import sys

# 設定模型快取目錄
if not os.environ.get("HF_HOME"):
    os.environ["HF_HOME"] = os.path.join(os.path.dirname(__file__), "..", "models")

def download_breeze_asr():
    """下載 Breeze-ASR-25 模型"""
    print("=" * 60)
    print("MeetingScribe v4.0.0 - 模型預載工具")
    print("=" * 60)
    print()
    
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        print("❌ 錯誤: 請先安裝 faster-whisper")
        print("   pip install faster-whisper>=1.1.0")
        return False
    
    model_name = "SoybeanMilk/faster-whisper-Breeze-ASR-25"
    
    print(f"📦 正在下載 Breeze-ASR-25 模型...")
    print(f"   來源: Hugging Face ({model_name})")
    print(f"   快取目錄: {os.environ.get('HF_HOME', '~/.cache/huggingface')}")
    print()
    print("⏳ 首次下載約需 5-10 分鐘（約 3GB），請耐心等待...")
    print()
    
    try:
        # 使用 CPU 下載，不需要 GPU
        model = WhisperModel(
            model_name,
            device="cpu",
            compute_type="int8"
        )
        
        print()
        print("✅ Breeze-ASR-25 模型下載成功！")
        print()
        
        # 釋放記憶體
        del model
        
        return True
        
    except Exception as e:
        print()
        print(f"❌ 模型下載失敗: {e}")
        print()
        print("💡 建議：")
        print("   1. 確認網路連線正常")
        print("   2. 確認 Hugging Face 可存取")
        print("   3. 檢查磁碟空間（需要約 3GB）")
        return False


def verify_model():
    """驗證模型是否已下載"""
    try:
        from huggingface_hub import snapshot_download, hf_hub_download
        from huggingface_hub.utils import LocalEntryNotFoundError
        
        model_name = "SoybeanMilk/faster-whisper-Breeze-ASR-25"
        
        # 檢查模型是否已在快取中
        cache_dir = os.environ.get("HF_HOME", os.path.expanduser("~/.cache/huggingface"))
        
        print(f"🔍 檢查模型快取...")
        print(f"   快取目錄: {cache_dir}")
        
        # 嘗試取得模型資訊
        try:
            from huggingface_hub import model_info
            info = model_info(model_name)
            print(f"✅ 模型存在: {model_name}")
            print(f"   最後更新: {info.lastModified}")
            return True
        except Exception as e:
            print(f"⚠️ 無法驗證模型: {e}")
            return False
            
    except ImportError:
        print("⚠️ huggingface_hub 未安裝，跳過驗證")
        return True


def main():
    """主函數"""
    print()
    
    # 下載 ASR 模型
    success = download_breeze_asr()
    
    if success:
        print("=" * 60)
        print("🎉 模型預載完成！")
        print("=" * 60)
        print()
        print("下一步：")
        print("  1. 啟動 Docker 容器")
        print("     cd docker")
        print("     docker compose -f docker-compose-windows-gpu.yml up -d")
        print()
        print("  2. 開啟瀏覽器訪問")
        print("     http://localhost:9527")
        print()
        sys.exit(0)
    else:
        print("=" * 60)
        print("❌ 模型預載失敗")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()
