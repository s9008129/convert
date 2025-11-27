#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
會議轉錄工具 - 安裝依賴腳本
"""
import subprocess
import sys

REQUIRED_PACKAGES = [
    "pyyaml",
    "httpx",
]

OPTIONAL_PACKAGES = [
    "faster-whisper",  # 如果不使用獨立執行檔
]

def main():
    print("安裝必要的 Python 套件...")
    
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
