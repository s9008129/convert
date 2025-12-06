"""
版本號管理模組
v3.5.4 - 統一版本號來源
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
