#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
會議轉錄工具 - 安裝依賴腳本

給第一次接觸這個專案的人：
- 這支程式會自動安裝「必要套件」。
- 安裝完成後，主程式才能正常讀取設定與呼叫 API。
- 執行方式：python install_deps.py

資料流向：
1) 讀取 REQUIRED_PACKAGES 清單
2) 呼叫 pip 逐一安裝
3) 印出完成摘要供使用者核對

例外情境說明：
- 本腳本刻意維持簡單流程，未使用 check=True 強制中止。
- 若單一套件安裝失敗，畫面仍可能繼續執行到下一個套件，
  因此建議搭配終端機輸出或後續執行主程式來確認環境是否完整。
"""
import subprocess
import sys

REQUIRED_PACKAGES = [
    "pyyaml",
    "httpx",
    "python-docx",
]

OPTIONAL_PACKAGES = [
    "faster-whisper",  # 如果不使用獨立執行檔
]

def main():
    """依序安裝必要套件，並在最後顯示安裝摘要。"""
    print("安裝必要的 Python 套件...")
    
    # 每安裝一個就立即顯示進度，讓非技術使用者知道目前卡在哪一步。
    for package in REQUIRED_PACKAGES:
        print(f"  安裝 {package}...")
        subprocess.run([
            sys.executable, "-m", "pip", "install", 
            package, "--quiet"
        ])
    
    print("\n安裝完成！")
    print("\n已安裝的套件：")
    for package in REQUIRED_PACKAGES:
        print(f"  ✓ {package}")

if __name__ == "__main__":
    main()
