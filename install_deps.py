#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""會議轉錄工具 - 安裝依賴腳本"""
from pathlib import Path
import subprocess
import sys

ROOT_DIR = Path(__file__).parent
REQUIREMENTS_FILE = ROOT_DIR / "requirements.txt"


def install_requirements() -> int:
    """以 requirements.txt 為主安裝依賴"""
    if not REQUIREMENTS_FILE.exists():
        print("[ERROR] 找不到 requirements.txt，請確認檔案存在於專案根目錄。")
        return 1
    print("使用 requirements.txt 安裝 Python 套件...")
    print(f"  檔案: {REQUIREMENTS_FILE}")
    cmd = [
        sys.executable,
        "-m",
        "pip",
        "install",
        "-r",
        str(REQUIREMENTS_FILE)
    ]
    return subprocess.call(cmd)


def main() -> None:
    exit_code = install_requirements()
    if exit_code == 0:
        print("\n依賴安裝完成。")
    else:
        print("\n依賴安裝失敗，請檢查上方輸出。")


if __name__ == "__main__":
    main()
