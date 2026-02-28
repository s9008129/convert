"""
版本號讀取工具。

統一從 VERSION 檔案取得版本，避免前後端或日誌顯示版本不一致。

流程說明：
- 先定位專案根目錄下的 VERSION 檔，再讀取文字內容回傳。

錯誤情境說明：
- 若檔案不存在或讀取失敗，會回退到 0.0.0，讓服務仍可啟動並提示後續排查。
"""

import os

def get_version() -> str:
    """從 VERSION 檔案讀取版本號"""
    version_file = os.path.join(
        os.path.dirname(__file__), '..', '..', 'VERSION'
    )
    try:
        with open(version_file, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception:
        return "0.0.0"  # 預設版本

__version__ = get_version()
