"""
檔案管理服務。

負責上傳檔案檢查、儲存、快取、結果輸出與排程清理，確保資料可追蹤且磁碟空間可控。
"""

import os
import re
import uuid
import hashlib
import aiofiles
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Tuple
from fastapi import UploadFile

from backend.core.asr_model_resolver import (
    build_asr_cache_signature,
    infer_asr_backend,
    resolve_asr_model,
    resolve_model_revision,
)
from backend.core.config import settings
from backend.core.logger import log

# 預編譯正則表達式以提升效能
SHA256_HASH_PATTERN = re.compile(r'^[0-9a-f]{64}$')


def _is_within_directory(path: str, directory: str) -> bool:
    try:
        return os.path.commonpath([path, directory]) == directory
    except ValueError:
        return False


class FileManagerService:
    """
    檔案管理服務
    處理檔案上傳、驗證、儲存與自動清理
    """
    
    # 檔案保留天數設定
    UPLOADS_RETENTION_DAYS = 1      # 上傳檔案保留 1 天
    OUTPUTS_RETENTION_DAYS = 7      # 輸出結果保留 7 天
    CACHE_RETENTION_DAYS = 30       # 快取保留 30 天
    
    def __init__(self):
        """建立必要資料夾並準備背景清理工作，避免磁碟空間被舊檔占滿。"""
        # 確保目錄存在
        os.makedirs(settings.uploads_dir, exist_ok=True)
        os.makedirs(settings.outputs_dir, exist_ok=True)
        os.makedirs(settings.cache_dir, exist_ok=True)
        self._cleanup_task: Optional[asyncio.Task] = None
    
    def validate_file(self, file: UploadFile) -> Tuple[bool, str]:
        """
        驗證上傳檔案是否安全且符合規格。

        會檢查檔名、路徑字元與副檔名，提早阻擋不合法或可疑輸入。
        Returns:
            (是否有效, 錯誤訊息或空字串)
        """
        # 檢查檔名
        if not file.filename:
            return False, "檔案名稱不能為空"
        
        # 安全性檢查：防止路徑遍歷
        if ".." in file.filename or "/" in file.filename or "\\" in file.filename:
            return False, "檔案名稱包含無效字符"
        
        # 額外檢查：防止空字節注入
        if "\x00" in file.filename:
            return False, "檔案名稱包含無效字符"
        
        # 檢查副檔名
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in settings.allowed_extensions_list:
            return False, f"不支援的檔案格式: {ext}。支援的格式: {settings.ALLOWED_EXTENSIONS}"
        
        return True, ""
    
    async def validate_file_size(self, file: UploadFile, return_content: bool = False) -> Tuple[bool, str, int] | Tuple[bool, str, int, bytes]:
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
            if return_content:
                return False, f"檔案大小超過限制: {file_size / 1024 / 1024:.1f}MB > {settings.MAX_FILE_SIZE_MB}MB", file_size, content
            return False, f"檔案大小超過限制: {file_size / 1024 / 1024:.1f}MB > {settings.MAX_FILE_SIZE_MB}MB", file_size
        
        if return_content:
            return True, "", file_size, content
        return True, "", file_size
    
    async def save_upload(self, file: UploadFile, content: Optional[bytes] = None) -> Tuple[str, str, int]:
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
        upload_content = content if content is not None else await file.read()
        file_size = len(upload_content)
        
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(upload_content)
        
        log.info(f"檔案已儲存: {unique_filename}, 大小: {file_size / 1024 / 1024:.2f}MB")
        
        return file_path, unique_filename, file_size
    
    def get_file_hash(self, file_path: str) -> str:
        """計算檔案 hash（使用 SHA256 確保安全性）"""
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

    def get_asr_cache_signature(self) -> str:
        return self._build_asr_cache_signature(self._diarization_cache_signature())

    def get_unlabeled_asr_cache_signature(self) -> str:
        """「無發言者標註」版本的 ASR 快取簽章（fail-soft 專用）。

        當次 diarization 沒有產出（模型缺失／資源不足／音檔問題）時，逐字稿
        內容等同現行無標註版本；此時只能把它寫進這個 key，否則日後模型恢復
        後會誤用這份沒有標籤的快取而永遠不再嘗試標註（T20260913-1900-01）。
        """
        return self._build_asr_cache_signature("diarization:off")

    def _build_asr_cache_signature(self, diarization: Optional[str]) -> str:
        backend = infer_asr_backend(settings.WHISPER_MODEL, settings.ASR_BACKEND)
        model_name = resolve_asr_model(settings.WHISPER_MODEL, settings.ASR_BACKEND)
        return build_asr_cache_signature(
            model_name=model_name,
            backend=backend,
            revision=resolve_model_revision(
                model_name,
                settings.WHISPER_MODEL_REVISION,
            ),
            language=settings.WHISPER_LANGUAGE,
            initial_prompt=settings.ASR_INITIAL_PROMPT,
            beam_size=settings.ASR_BEAM_SIZE,
            vad_enabled=settings.ASR_VAD_ENABLED,
            diarization=diarization,
        )

    @staticmethod
    def _diarization_cache_signature() -> str:
        """發言者標註層的快取簽章（停用或參數變更時必須換 key）。

        只有「開關＋會改變分群/對位結果的參數」進簽章；模型路徑不進
        （同機同模型；換模型屬版本升級，由部署流程負責清快取）。
        """
        if not settings.ENABLE_DIARIZATION:
            return "diarization:off"
        return (
            "diarization:"
            f"t{settings.DIARIZATION_THRESHOLD}"
            f"::n{settings.DIARIZATION_NUM_CLUSTERS}"
            f"::on{settings.DIARIZATION_MIN_DURATION_ON}"
            f"::off{settings.DIARIZATION_MIN_DURATION_OFF}"
            f"::gap{settings.DIARIZATION_MERGE_GAP_SECONDS}"
            f"::cov{settings.DIARIZATION_MIN_SEGMENT_COVERAGE}"
        )

    def _build_cache_path(self, file_hash: str, cache_signature: Optional[str] = None) -> str:
        signature = cache_signature or self.get_asr_cache_signature()
        return os.path.join(settings.cache_dir, f"{file_hash}_{signature}.txt")
    
    def get_cached_transcript(self, file_hash: str, cache_signature: Optional[str] = None) -> Optional[str]:
        """取得快取的逐字稿（驗證 hash 格式）"""
        # 驗證 file_hash 格式（應為 64 字元的十六進位字串）
        if not file_hash or not SHA256_HASH_PATTERN.match(file_hash.lower()):
            log.warning(f"無效的快取 hash 格式: {file_hash}")
            return None
        
        cache_file = self._build_cache_path(file_hash, cache_signature=cache_signature)
        if os.path.exists(cache_file):
            with open(cache_file, 'r', encoding='utf-8') as f:
                return f.read()
        return None
    
    def save_transcript_cache(self, file_hash: str, transcript: str, cache_signature: Optional[str] = None):
        """儲存逐字稿到快取（驗證 hash 格式）"""
        # 驗證 file_hash 格式（應為 64 字元的十六進位字串）
        if not file_hash or not SHA256_HASH_PATTERN.match(file_hash.lower()):
            log.warning(f"無效的快取 hash 格式，跳過儲存: {file_hash}")
            return
        
        cache_file = self._build_cache_path(file_hash, cache_signature=cache_signature)
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
        # 安全地處理檔名，避免路徑遍歷
        base_name = os.path.splitext(os.path.basename(filename))[0]
        # 清理檔名，只保留安全字符
        safe_base_name = "".join(c for c in base_name if c.isalnum() or c in ('_', '-', ' ', '.') or '\u4e00' <= c <= '\u9fff')
        result_filename = f"{safe_base_name}_{task_id}.md"
        result_path = os.path.join(settings.outputs_dir, result_filename)
        
        async with aiofiles.open(result_path, 'w', encoding='utf-8') as f:
            await f.write(content)
        
        log.info(f"結果已儲存: {result_filename}")
        return result_path
    
    @staticmethod
    def build_safe_base_name(filename: str) -> str:
        """由原始檔名產生安全的基底檔名（去副檔名、清除路徑遍歷字元，保留中文）。"""
        base_name = os.path.splitext(os.path.basename(filename))[0]
        return "".join(c for c in base_name if c.isalnum() or c in ('_', '-', ' ', '.') or '一' <= c <= '鿿')

    def transcript_result_path(self, task_id: str, filename: str) -> str:
        """逐字稿獨立輸出檔的路徑（v4.2.2：逐字稿可單獨下載，P1-11 部分落地）。"""
        safe_base_name = self.build_safe_base_name(filename)
        return os.path.join(settings.outputs_dir, f"{safe_base_name}_{task_id}_逐字稿.txt")

    async def save_transcript_result(self, task_id: str, filename: str, transcript: str) -> str:
        """將（已清理/校正的）逐字稿另存為獨立檔案，供前端單獨下載。"""
        transcript_path = self.transcript_result_path(task_id, filename)
        async with aiofiles.open(transcript_path, 'w', encoding='utf-8') as f:
            await f.write(transcript)
        log.info(f"逐字稿已儲存: {os.path.basename(transcript_path)}")
        return transcript_path

    def delete_file(self, file_path: str) -> bool:
        """刪除檔案（安全地限制在允許的目錄內）"""
        try:
            # 安全性檢查：確保路徑在允許的目錄內
            abs_path = os.path.abspath(file_path)
            allowed_dirs = [
                os.path.abspath(settings.uploads_dir),
                os.path.abspath(settings.outputs_dir),
                os.path.abspath(settings.cache_dir)
            ]
            
            is_safe = any(_is_within_directory(abs_path, allowed_dir) for allowed_dir in allowed_dirs)
            if not is_safe:
                log.warning(f"嘗試刪除不允許目錄中的檔案: {file_path}")
                return False
            
            if os.path.exists(abs_path):
                os.remove(abs_path)
                return True
        except Exception as e:
            log.error(f"刪除檔案失敗: {e}")
        return False
    
    def cleanup_old_files(self, directory: str, retention_days: int) -> Tuple[int, int]:
        """
        清理指定目錄中超過保留天數的檔案
        
        Args:
            directory: 要清理的目錄
            retention_days: 檔案保留天數
            
        Returns:
            (已刪除檔案數, 釋放的空間大小 bytes)
        """
        deleted_count = 0
        freed_space = 0
        cutoff_time = datetime.now() - timedelta(days=retention_days)
        
        try:
            if not os.path.exists(directory):
                return 0, 0
            
            for filename in os.listdir(directory):
                # 跳過隱藏檔案（如 .DS_Store）
                if filename.startswith('.'):
                    continue
                    
                file_path = os.path.join(directory, filename)
                
                # 只處理檔案，跳過目錄
                if not os.path.isfile(file_path):
                    continue
                
                # 檢查檔案修改時間
                file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                
                if file_mtime < cutoff_time:
                    file_size = os.path.getsize(file_path)
                    if self.delete_file(file_path):
                        deleted_count += 1
                        freed_space += file_size
                        log.debug(f"已清理過期檔案: {filename}")
        
        except Exception as e:
            log.error(f"清理目錄 {directory} 時發生錯誤: {e}")
        
        return deleted_count, freed_space
    
    def run_cleanup(self) -> dict:
        """
        執行所有目錄的清理
        
        Returns:
            清理結果統計
        """
        log.info("開始執行檔案清理任務...")
        results = {
            "timestamp": datetime.now().isoformat(),
            "uploads": {"deleted": 0, "freed_bytes": 0},
            "outputs": {"deleted": 0, "freed_bytes": 0},
            "cache": {"deleted": 0, "freed_bytes": 0},
            "total_freed_mb": 0
        }
        
        # 清理上傳目錄（保留 1 天）
        deleted, freed = self.cleanup_old_files(
            settings.uploads_dir, 
            self.UPLOADS_RETENTION_DAYS
        )
        results["uploads"]["deleted"] = deleted
        results["uploads"]["freed_bytes"] = freed
        
        # 清理輸出目錄（保留 7 天）
        deleted, freed = self.cleanup_old_files(
            settings.outputs_dir, 
            self.OUTPUTS_RETENTION_DAYS
        )
        results["outputs"]["deleted"] = deleted
        results["outputs"]["freed_bytes"] = freed
        
        # 清理快取目錄（保留 30 天）
        deleted, freed = self.cleanup_old_files(
            settings.cache_dir, 
            self.CACHE_RETENTION_DAYS
        )
        results["cache"]["deleted"] = deleted
        results["cache"]["freed_bytes"] = freed
        
        # 計算總共釋放空間
        total_freed = (
            results["uploads"]["freed_bytes"] +
            results["outputs"]["freed_bytes"] +
            results["cache"]["freed_bytes"]
        )
        results["total_freed_mb"] = round(total_freed / 1024 / 1024, 2)
        
        total_deleted = (
            results["uploads"]["deleted"] +
            results["outputs"]["deleted"] +
            results["cache"]["deleted"]
        )
        
        log.info(f"檔案清理完成: 共刪除 {total_deleted} 個檔案，釋放 {results['total_freed_mb']} MB 空間")
        
        return results
    
    async def start_cleanup_scheduler(self):
        """
        啟動每日清理排程器
        每天凌晨 3:00 執行清理任務
        """
        async def scheduler():
            while True:
                try:
                    # 計算距離下一個凌晨 3:00 的秒數
                    now = datetime.now()
                    next_run = now.replace(hour=3, minute=0, second=0, microsecond=0)
                    if next_run <= now:
                        next_run += timedelta(days=1)
                    
                    wait_seconds = (next_run - now).total_seconds()
                    log.info(f"下次清理任務將在 {next_run.strftime('%Y-%m-%d %H:%M:%S')} 執行（{wait_seconds/3600:.1f} 小時後）")
                    
                    # 等待到執行時間
                    await asyncio.sleep(wait_seconds)
                    
                    # 執行清理
                    self.run_cleanup()
                    
                except asyncio.CancelledError:
                    log.info("清理排程器已取消")
                    break
                except Exception as e:
                    log.error(f"清理排程器發生錯誤: {e}")
                    # 發生錯誤時等待 1 小時後重試
                    await asyncio.sleep(3600)
        
        self._cleanup_task = asyncio.create_task(scheduler())
        log.info("檔案清理排程器已啟動（每日凌晨 3:00 執行）")
    
    async def stop_cleanup_scheduler(self):
        """停止清理排程器"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            log.info("檔案清理排程器已停止")
    
    def get_storage_stats(self) -> dict:
        """
        取得儲存空間使用統計
        
        Returns:
            儲存空間使用統計
        """
        stats = {
            "uploads": {"file_count": 0, "total_size_mb": 0},
            "outputs": {"file_count": 0, "total_size_mb": 0},
            "cache": {"file_count": 0, "total_size_mb": 0},
            "total_size_mb": 0
        }
        
        for dir_name, dir_path in [
            ("uploads", settings.uploads_dir),
            ("outputs", settings.outputs_dir),
            ("cache", settings.cache_dir)
        ]:
            if os.path.exists(dir_path):
                for filename in os.listdir(dir_path):
                    if filename.startswith('.'):
                        continue
                    file_path = os.path.join(dir_path, filename)
                    if os.path.isfile(file_path):
                        stats[dir_name]["file_count"] += 1
                        stats[dir_name]["total_size_mb"] += os.path.getsize(file_path) / 1024 / 1024
        
        # 四捨五入
        for key in ["uploads", "outputs", "cache"]:
            stats[key]["total_size_mb"] = round(stats[key]["total_size_mb"], 2)
        
        stats["total_size_mb"] = round(
            stats["uploads"]["total_size_mb"] +
            stats["outputs"]["total_size_mb"] +
            stats["cache"]["total_size_mb"],
            2
        )
        
        return stats


# 全域檔案管理服務實例
file_manager = FileManagerService()
