#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Windows/跨平台 Whisper 轉錄器
支援 faster-whisper-xxl (Windows) 和 faster-whisper (Python)

設計原則：
1. 自動檢測最佳後端
2. CUDA 優先，自動回退到 CPU
3. 智能快取避免重複轉錄
4. 進度回報支援
"""
import subprocess
import logging
import time
import hashlib
import json
import platform
from pathlib import Path
from typing import Optional, Callable, Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionResult:
    """轉錄結果"""
    text: str
    language: str
    duration_seconds: float
    processing_time: float
    model: str
    device: str
    source_file: str
    from_cache: bool = False
    segments: List[Dict[str, Any]] = field(default_factory=list)
    
    @property
    def speed_ratio(self) -> float:
        """處理速度比（音訊時長/處理時間）"""
        if self.processing_time > 0:
            return self.duration_seconds / self.processing_time
        return 0
    
    @property
    def word_count(self) -> int:
        """字數統計"""
        return len(self.text)


class TranscriptionError(Exception):
    """轉錄錯誤基類"""
    pass


class AudioFileNotFoundError(TranscriptionError):
    """檔案不存在"""
    pass


class UnsupportedFormatError(TranscriptionError):
    """不支援的格式"""
    pass


class WhisperTranscriber:
    """
    通用 Whisper 轉錄器
    
    支援兩種後端：
    1. faster-whisper-xxl.exe (Windows 獨立執行檔)
    2. faster-whisper Python 套件
    
    自動選擇最佳後端和運算裝置
    """
    
    # 支援的音訊/視訊格式
    SUPPORTED_FORMATS = {
        '.mp3', '.mp4', '.wav', '.m4a', '.mkv', 
        '.webm', '.flac', '.ogg', '.wma', '.aac',
        '.avi', '.mov', '.wmv', '.opus', '.amr'
    }
    
    # 模型大小對照
    MODEL_SIZES = {
        'tiny': '~75MB',
        'base': '~145MB',
        'small': '~465MB',
        'medium': '~1.5GB',
        'large-v2': '~3.1GB',
        'large-v3': '~3.1GB',
    }
    
    def __init__(
        self, 
        exe_path: Optional[str] = None,
        model: str = "large-v3",
        language: str = "zh",
        device: str = "auto",
        compute_type: str = "float16",
        cache_dir: Optional[str] = None
    ):
        """
        初始化轉錄器
        
        Args:
            exe_path: faster-whisper-xxl.exe 路徑（Windows）
            model: 模型大小
            language: 語言代碼
            device: 運算裝置 (auto/cuda/cpu)
            compute_type: 計算精度 (float16/int8/int8_float16)
            cache_dir: 快取目錄
        """
        self.model = model
        self.language = language
        self.compute_type = compute_type
        self.cache_dir = Path(cache_dir) if cache_dir else None
        
        # 決定後端和裝置
        self.backend = self._detect_backend(exe_path)
        self.device = self._detect_device(device)
        self.exe_path = self._resolve_exe_path(exe_path) if self.backend == "exe" else None
        
        logger.info("[Whisper] 初始化完成")
        logger.info("[Whisper] 後端: %s", self.backend)
        logger.info("[Whisper] 裝置: %s", self.device)
        logger.info("[Whisper] 模型: %s", model)
        logger.info("[Whisper] 語言: %s", language)
    
    def _detect_backend(self, exe_path: Optional[str]) -> str:
        """檢測可用的後端"""
        # Windows 優先使用獨立執行檔
        if platform.system() == "Windows":
            if exe_path and Path(exe_path).exists():
                return "exe"
            
            # 檢查常見位置
            common_paths = [
                Path.cwd() / "faster-whisper-xxl.exe",
                Path.cwd() / "Whisper-Faster-XXL" / "faster-whisper-xxl.exe",
            ]
            for p in common_paths:
                if p.exists():
                    return "exe"
        
        # 嘗試使用 Python 套件
        try:
            import faster_whisper
            return "python"
        except ImportError:
            pass
        
        # Windows 時回退到 exe
        if platform.system() == "Windows":
            return "exe"
        
        raise TranscriptionError(
            "找不到可用的 Whisper 後端\n"
            "請安裝 faster-whisper-xxl.exe 或 pip install faster-whisper"
        )
    
    def _detect_device(self, device: str) -> str:
        """檢測運算裝置"""
        if device != "auto":
            return device
        
        # 檢測 CUDA
        if self._check_cuda():
            return "cuda"
        
        logger.warning("[Whisper] CUDA 不可用，使用 CPU")
        return "cpu"
    
    def _check_cuda(self) -> bool:
        """檢查 CUDA 是否可用"""
        try:
            result = subprocess.run(
                ["nvidia-smi"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def _resolve_exe_path(self, exe_path: Optional[str]) -> Path:
        """解析執行檔路徑"""
        if exe_path:
            p = Path(exe_path)
            if p.exists():
                return p.resolve()
        
        # 檢查常見位置
        search_paths = [
            Path.cwd() / "faster-whisper-xxl.exe",
            Path.cwd() / "Whisper-Faster-XXL" / "faster-whisper-xxl.exe",
            Path.home() / "faster-whisper-xxl" / "faster-whisper-xxl.exe",
        ]
        
        for p in search_paths:
            if p.exists():
                return p.resolve()
        
        raise AudioFileNotFoundError(
            "找不到 faster-whisper-xxl.exe\n"
            "請從 https://github.com/Purfview/whisper-standalone-win/releases 下載"
        )
    
    def _get_cache_path(self, audio_path: Path) -> Optional[Path]:
        """取得快取檔案路徑"""
        if not self.cache_dir:
            return None
        
        # 使用檔案內容的 hash 作為快取 key
        file_hash = self._calculate_file_hash(audio_path)
        cache_name = f"{audio_path.stem}_{file_hash[:8]}.json"
        
        return self.cache_dir / cache_name
    
    def _calculate_file_hash(self, file_path: Path) -> str:
        """計算檔案 hash（使用 SHA256 確保安全性）"""
        hasher = hashlib.sha256()
        
        # 讀取整個檔案以確保 hash 準確性
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b""):
                hasher.update(chunk)
            # 加入檔案大小
            hasher.update(str(file_path.stat().st_size).encode())
        
        return hasher.hexdigest()
    
    def _load_cache(self, cache_path: Path) -> Optional[TranscriptionResult]:
        """載入快取"""
        if not cache_path or not cache_path.exists():
            return None
        
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 驗證快取版本和模型
            if data.get('model') != self.model:
                logger.info("[快取] 模型不符，重新轉錄")
                return None
            
            result = TranscriptionResult(
                text=data['text'],
                language=data.get('language', self.language),
                duration_seconds=data.get('duration_seconds', 0),
                processing_time=data.get('processing_time', 0),
                model=data.get('model', self.model),
                device=data.get('device', 'cached'),
                source_file=data.get('source_file', ''),
                from_cache=True,
                segments=data.get('segments', [])
            )
            
            logger.info("[快取] 載入成功: %s", cache_path.name)
            return result
            
        except Exception as e:
            logger.warning("[快取] 載入失敗: %s", e)
            return None
    
    def _save_cache(self, cache_path: Path, result: TranscriptionResult):
        """儲存快取"""
        if not cache_path:
            return
        
        try:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            
            data = {
                'text': result.text,
                'language': result.language,
                'duration_seconds': result.duration_seconds,
                'processing_time': result.processing_time,
                'model': result.model,
                'device': result.device,
                'source_file': result.source_file,
                'segments': result.segments,
                'cached_at': datetime.now().isoformat()
            }
            
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info("[快取] 儲存成功: %s", cache_path.name)
            
        except Exception as e:
            logger.warning("[快取] 儲存失敗: %s", e)
    
    def transcribe(
        self, 
        audio_path: str,
        use_cache: bool = True,
        on_progress: Optional[Callable[[str, float], None]] = None
    ) -> TranscriptionResult:
        """
        轉錄音訊檔案
        
        Args:
            audio_path: 音訊/視訊檔案路徑
            use_cache: 是否使用快取
            on_progress: 進度回調函數 (message, progress)
        
        Returns:
            轉錄結果
        """
        audio_path = Path(audio_path).resolve()
        
        # 驗證檔案
        self._validate_file(audio_path)
        
        # 檢查快取
        cache_path = self._get_cache_path(audio_path) if use_cache else None
        if cache_path:
            cached = self._load_cache(cache_path)
            if cached:
                return cached
        
        # 執行轉錄
        if self.backend == "exe":
            result = self._transcribe_exe(audio_path, on_progress)
        else:
            result = self._transcribe_python(audio_path, on_progress)
        
        # 儲存快取
        if cache_path and result.text:
            self._save_cache(cache_path, result)
        
        return result
    
    def _validate_file(self, audio_path: Path) -> None:
        """驗證輸入檔案"""
        if not audio_path.exists():
            raise AudioFileNotFoundError("找不到檔案: %s" % audio_path)
        
        suffix = audio_path.suffix.lower()
        if suffix not in self.SUPPORTED_FORMATS:
            raise UnsupportedFormatError(
                "不支援的格式: %s\n支援格式: %s" % (suffix, ', '.join(sorted(self.SUPPORTED_FORMATS)))
            )
    
    def _transcribe_exe(
        self, 
        audio_path: Path,
        on_progress: Optional[Callable[[str, float], None]]
    ) -> TranscriptionResult:
        """使用獨立執行檔轉錄"""
        output_dir = audio_path.parent
        
        # 取得檔案資訊
        file_size_mb = audio_path.stat().st_size / (1024 * 1024)
        logger.info("[轉錄] 檔案: %s (%.1f MB)", audio_path.name, file_size_mb)
        
        if on_progress:
            on_progress("準備轉錄...", 0)
        
        # 建立命令
        cmd = [
            str(self.exe_path),
            str(audio_path),
            "--language", self.language,
            "--model", self.model,
            "--output_format", "json",  # 使用 JSON 取得更多資訊
            "--output_dir", str(output_dir),
            "--device", self.device,
            "--task", "transcribe"
        ]
        
        if self.device == "cuda":
            cmd.extend(["--compute_type", self.compute_type])
        
        logger.info(f"[轉錄] 開始處理...")
        start_time = time.time()
        
        if on_progress:
            on_progress("轉錄中...", 10)
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                cwd=str(self.exe_path.parent)
            )
            
            elapsed = time.time() - start_time
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "未知錯誤"
                raise TranscriptionError("轉錄失敗: %s" % error_msg)
            
            # 讀取輸出
            json_file = output_dir / f"{audio_path.stem}.json"
            txt_file = output_dir / f"{audio_path.stem}.txt"
            
            text = ""
            segments = []
            duration = 0
            
            if json_file.exists():
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    segments = data.get('segments', [])
                    text = ' '.join(s.get('text', '') for s in segments)
                    
                    if segments:
                        duration = segments[-1].get('end', 0)
                        
                json_file.unlink()  # 清理 JSON
                
            elif txt_file.exists():
                text = txt_file.read_text(encoding='utf-8').strip()
            
            if on_progress:
                on_progress("轉錄完成", 100)
            
            logger.info("[轉錄] 完成！耗時: %.1f 秒", elapsed)
            logger.info("[轉錄] 字數: %d", len(text))
            
            return TranscriptionResult(
                text=text,
                language=self.language,
                duration_seconds=duration,
                processing_time=elapsed,
                model=self.model,
                device=self.device,
                source_file=str(audio_path),
                segments=segments
            )
            
        except subprocess.TimeoutExpired:
            raise TranscriptionError("轉錄超時")
    
    def _transcribe_python(
        self, 
        audio_path: Path,
        on_progress: Optional[Callable[[str, float], None]]
    ) -> TranscriptionResult:
        """使用 Python 套件轉錄"""
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            raise TranscriptionError("請安裝 faster-whisper: pip install faster-whisper")
        
        file_size_mb = audio_path.stat().st_size / (1024 * 1024)
        logger.info(f"[轉錄] 檔案: {audio_path.name} ({file_size_mb:.1f} MB)")
        
        if on_progress:
            on_progress("載入模型...", 5)
        
        # 載入模型
        model = WhisperModel(
            self.model,
            device=self.device,
            compute_type=self.compute_type
        )
        
        if on_progress:
            on_progress("轉錄中...", 20)
        
        logger.info(f"[轉錄] 開始處理...")
        start_time = time.time()
        
        # 執行轉錄
        segments_iter, info = model.transcribe(
            str(audio_path),
            language=self.language if self.language != "auto" else None,
            beam_size=5,
            vad_filter=True
        )
        
        # 收集結果
        segments = []
        texts = []
        
        for segment in segments_iter:
            segments.append({
                'start': segment.start,
                'end': segment.end,
                'text': segment.text
            })
            texts.append(segment.text)
        
        elapsed = time.time() - start_time
        text = ' '.join(texts)
        
        if on_progress:
            on_progress("轉錄完成", 100)
        
        logger.info(f"[轉錄] 完成！耗時: {elapsed:.1f} 秒")
        logger.info(f"[轉錄] 字數: {len(text):,}")
        
        return TranscriptionResult(
            text=text,
            language=info.language,
            duration_seconds=info.duration,
            processing_time=elapsed,
            model=self.model,
            device=self.device,
            source_file=str(audio_path),
            segments=segments
        )
    
    def get_gpu_info(self) -> Optional[Dict[str, Any]]:
        """取得 GPU 資訊"""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,memory.free,utilization.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                parts = result.stdout.strip().split(', ')
                if len(parts) >= 4:
                    return {
                        'name': parts[0],
                        'memory_total_mb': int(parts[1]),
                        'memory_free_mb': int(parts[2]),
                        'utilization_percent': int(parts[3])
                    }
        except Exception:
            pass
        
        return None


# 便捷函數
def transcribe_audio(
    audio_path: str,
    model: str = "large-v3",
    language: str = "zh",
    **kwargs
) -> str:
    """
    快速轉錄音訊
    
    Args:
        audio_path: 音訊檔案路徑
        model: 模型大小
        language: 語言
    
    Returns:
        轉錄文字
    """
    transcriber = WhisperTranscriber(model=model, language=language, **kwargs)
    result = transcriber.transcribe(audio_path)
    return result.text
