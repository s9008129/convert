"""
MeetingScribe 檔案管理服務
"""

import os
import uuid
import hashlib
import aiofiles
from typing import Optional, Tuple
from fastapi import UploadFile

from backend.core.config import settings
from backend.core.logger import log


class FileManagerService:
    """
    檔案管理服務
    處理檔案上傳、驗證、儲存
    """
    
    def __init__(self):
        # 確保目錄存在
        os.makedirs(settings.uploads_dir, exist_ok=True)
        os.makedirs(settings.outputs_dir, exist_ok=True)
        os.makedirs(settings.cache_dir, exist_ok=True)
    
    def validate_file(self, file: UploadFile) -> Tuple[bool, str]:
        """
        驗證上傳的檔案
        
        Returns:
            (是否有效, 錯誤訊息或空字串)
        """
        # 檢查檔名
        if not file.filename:
            return False, "檔案名稱不能為空"
        
        # 檢查副檔名
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in settings.allowed_extensions_list:
            return False, f"不支援的檔案格式: {ext}。支援的格式: {settings.ALLOWED_EXTENSIONS}"
        
        return True, ""
    
    async def validate_file_size(self, file: UploadFile) -> Tuple[bool, str, int]:
        """
        驗證檔案大小
        
        Returns:
            (是否有效, 錯誤訊息或空字串, 檔案大小)
        """
        # 讀取檔案內容以獲取大小
        content = await file.read()
        file_size = len(content)
        
        # 重置檔案指標
        await file.seek(0)
        
        if file_size > settings.max_file_size_bytes:
            return False, f"檔案大小超過限制: {file_size / 1024 / 1024:.1f}MB > {settings.MAX_FILE_SIZE_MB}MB", file_size
        
        return True, "", file_size
    
    async def save_upload(self, file: UploadFile) -> Tuple[str, str, int]:
        """
        儲存上傳的檔案
        
        Returns:
            (儲存的檔案路徑, 唯一檔名, 檔案大小)
        """
        # 生成唯一檔名
        ext = os.path.splitext(file.filename)[1].lower()
        unique_filename = f"{uuid.uuid4().hex[:12]}{ext}"
        file_path = os.path.join(settings.uploads_dir, unique_filename)
        
        # 讀取並儲存檔案
        content = await file.read()
        file_size = len(content)
        
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(content)
        
        log.info(f"檔案已儲存: {unique_filename}, 大小: {file_size / 1024 / 1024:.2f}MB")
        
        return file_path, unique_filename, file_size
    
    def get_file_hash(self, file_path: str) -> str:
        """計算檔案 hash（使用 SHA256 確保安全性）"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def get_cached_transcript(self, file_hash: str) -> Optional[str]:
        """取得快取的逐字稿"""
        cache_file = os.path.join(settings.cache_dir, f"{file_hash}.txt")
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                return f.read()
        return None
    
    def save_transcript_cache(self, file_hash: str, transcript: str):
        """儲存逐字稿到快取"""
        cache_file = os.path.join(settings.cache_dir, f"{file_hash}.txt")
        with open(cache_file, 'w', encoding='utf-8') as f:
            f.write(transcript)
        log.debug(f"逐字稿已快取: {file_hash}")
    
    async def save_result(self, task_id: str, filename: str, content: str) -> str:
        """
        儲存處理結果
        
        Returns:
            結果檔案路徑
        """
        # 使用原始檔名（去除副檔名）+ 任務 ID
        base_name = os.path.splitext(filename)[0]
        result_filename = f"{base_name}_{task_id}.md"
        result_path = os.path.join(settings.outputs_dir, result_filename)
        
        async with aiofiles.open(result_path, 'w', encoding='utf-8') as f:
            await f.write(content)
        
        log.info(f"結果已儲存: {result_filename}")
        return result_path
    
    def delete_file(self, file_path: str) -> bool:
        """刪除檔案"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
        except Exception as e:
            log.error(f"刪除檔案失敗: {e}")
        return False


# 全域檔案管理服務實例
file_manager = FileManagerService()
