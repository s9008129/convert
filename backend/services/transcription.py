"""
MeetingScribe Whisper 轉錄服務
支援多後端：MLX-Whisper (macOS MPS)、Faster-Whisper (CUDA/CPU)
v3.5.0: 平台自動偵測，macOS 使用 MLX-Whisper 加速
"""

import os
import gc
import time
from typing import Optional, Generator, Tuple
from backend.core.config import settings
from backend.core.logger import log
from backend.core.platform_config import (
    get_global_config,
    get_config_value,
    get_whisper_backend,
    get_device,
    get_platform
)
from backend.services.device_detector import device_detector, DeviceType


class TranscriptionService:
    """
    Whisper 語音轉錄服務
    支援多後端：MLX-Whisper (macOS MPS)、Faster-Whisper (CUDA/CPU)
    
    v3.5.0 改進：
    - 平台自動偵測：macOS 使用 MLX-Whisper + MPS，效能提升 3-5 倍
    - Windows/Linux 繼續使用 Faster-Whisper + CUDA/CPU
    - 每次轉錄後釋放模型，避免 VRAM 持續佔用
    """
    
    def __init__(self):
        self._model = None
        self._device: Optional[DeviceType] = None
        self._compute_type: str = "int8"
        self._backend: Optional[str] = None  # 'mlx' or 'faster-whisper'
        
    def _get_backend(self) -> str:
        """
        獲取 Whisper 後端
        macOS: mlx (MPS 加速)
        Others: faster-whisper (CUDA/CPU)
        """
        if self._backend is None:
            backend = get_whisper_backend()
            # 正規化後端名稱
            if 'mlx' in backend.lower():
                self._backend = 'mlx'
            elif 'faster' in backend.lower():
                self._backend = 'faster-whisper'
            else:
                self._backend = backend
            log.info(f"Whisper 後端: {self._backend}")
        return self._backend
        
    def _load_model(self, force_cpu: bool = False):
        """
        載入 Whisper 模型（每次轉錄前重新載入以確保 GPU 可用）
        v3.5.0: 支援 MLX-Whisper 和 Faster-Whisper
        """
        backend = self._get_backend()
        
        if backend == 'mlx':
            self._load_mlx_model(force_cpu)
        else:
            self._load_faster_whisper_model(force_cpu)
    
    def _load_mlx_model(self, force_cpu: bool = False):
        """載入 MLX-Whisper 模型（macOS MPS 加速）"""
        try:
            import mlx_whisper
        except ImportError:
            log.error("MLX-Whisper 未安裝，請執行: pip install mlx-whisper")
            log.info("回退到 Faster-Whisper...")
            self._backend = 'faster-whisper'
            self._load_faster_whisper_model(force_cpu)
            return
        
        config = get_global_config()
        model_name = get_config_value(config, 'whisper.mlx.model', None)
        
        # 若未設定 mlx.model，回退到 whisper.model 或預設值
        if not model_name:
            model_name = get_config_value(config, 'whisper.model', 'mlx-community/whisper-large-v3-turbo')
            log.warning(f"未設定 whisper.mlx.model，使用回退值: {model_name}")
        
        # MLX-Whisper 自動使用 MPS，不需要手動指定
        self._device = DeviceType.MPS
        self._compute_type = "fp16" if get_config_value(config, 'whisper.mlx.fp16', True) else "fp32"
        
        log.info(f"載入 MLX-Whisper 模型: {model_name} (MPS 加速)")
        
        try:
            # MLX-Whisper 不需要顯式載入模型，在轉錄時自動載入
            self._model = "mlx"  # 標記已初始化
            log.info(f"✅ MLX-Whisper 已初始化 (裝置: MPS, 模型: {model_name})")
        except Exception as e:
            log.error(f"MLX-Whisper 初始化失敗: {e}")
            raise
    
    def _load_faster_whisper_model(self, force_cpu: bool = False):
        """載入 Faster-Whisper 模型（CUDA/CPU）"""
        from faster_whisper import WhisperModel
        
        if force_cpu:
            device = "cpu"
            compute_type = "int8"
        else:
            # v3.5.2: 強制重新偵測，確保取得最新 GPU 狀態
            device_detector.current_device = None  # 重置快取
            device_type, compute_type = device_detector.detect_best_device()
            device = device_type.value
            
            # MPS 不支援 faster-whisper，降級到 CPU
            if device_type == DeviceType.MPS:
                log.info("faster-whisper 不支援 MPS，使用 CPU 模式")
                device = "cpu"
                compute_type = "int8"
        
        self._device = DeviceType(device) if device != "cpu" else DeviceType.CPU
        self._compute_type = compute_type
        
        log.info(f"載入 Faster-Whisper 模型: {settings.WHISPER_MODEL}, 裝置: {device}, 精度: {compute_type}")
        
        try:
            self._model = WhisperModel(
                settings.WHISPER_MODEL,
                device=device,
                compute_type=compute_type
            )
            log.info(f"✅ Faster-Whisper 模型載入成功 (裝置: {device.upper()})")
        except Exception as e:
            log.error(f"Faster-Whisper 模型載入失敗: {e}")
            if device != "cpu":
                log.info("嘗試降級到 CPU 模式...")
                self._load_faster_whisper_model(force_cpu=True)
            else:
                raise
    
    def _unload_model(self):
        """
        釋放 Whisper 模型，清空 VRAM
        v3.5.2: 新增此方法以解決 VRAM 資源競爭問題
        """
        if self._model is not None:
            log.info("釋放 Whisper 模型，清空 VRAM...")
            del self._model
            self._model = None
            
            # 強制執行垃圾回收
            gc.collect()
            
            # 如果是 CUDA，清空 GPU 快取
            if self._device == DeviceType.CUDA:
                try:
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                        torch.cuda.synchronize()
                        log.info("✅ CUDA 快取已清空")
                except ImportError:
                    pass
                except Exception as e:
                    log.warning(f"清空 CUDA 快取時發生錯誤: {e}")
            
            self._device = None
            self._compute_type = "int8"
            log.info("✅ Whisper 模型已釋放")
    
    def transcribe(
        self,
        audio_path: str,
        progress_callback: Optional[callable] = None,
        max_retries: int = 1
    ) -> Tuple[str, float]:
        """
        轉錄音訊檔案
        
        Args:
            audio_path: 音訊檔案路徑
            progress_callback: 進度回調函數 (progress: float, message: str)
            max_retries: 最大重試次數（用於 CPU 降級）
            
        Returns:
            (逐字稿文字, 音訊時長秒數)
            
        v3.5.0 改進：
        - 支援 MLX-Whisper (macOS MPS 加速) 和 Faster-Whisper
        - 轉錄完成後自動釋放模型，確保 VRAM 不會被持續佔用
        """
        try:
            # 每次轉錄前重新載入模型（確保使用最新 GPU 狀態）
            self._load_model()
            
            # 安全檢查：驗證路徑不包含路徑遍歷字符
            abs_audio_path = os.path.abspath(audio_path)
            abs_uploads_dir = os.path.abspath(settings.uploads_dir)
            
            # 確保檔案在上傳目錄內
            if not abs_audio_path.startswith(abs_uploads_dir):
                raise ValueError(f"不允許的檔案路徑: {audio_path}")
            
            if not os.path.exists(abs_audio_path):
                raise FileNotFoundError(f"音訊檔案不存在: {audio_path}")
            
            start_time = time.time()
            backend = self._get_backend()
            
            if progress_callback:
                progress_callback(10.0, f"開始轉錄 ({backend}, 裝置: {self._device.value.upper() if self._device else 'CPU'})...")
            
            # 根據後端選擇轉錄方法
            if backend == 'mlx':
                transcript, duration = self._transcribe_with_mlx(abs_audio_path, progress_callback)
            else:
                transcript, duration = self._transcribe_with_faster_whisper(abs_audio_path, progress_callback)
            
            elapsed = time.time() - start_time
            log.info(f"轉錄完成，耗時: {elapsed:.2f}秒，音訊長度: {duration:.2f}秒")
            
            return transcript, duration
            
        except Exception as e:
            log.error(f"轉錄失敗: {e}")
            raise
        finally:
            # v3.5.0: 確保轉錄完成後釋放模型
            self._unload_model()
    
    def _transcribe_with_mlx(
        self,
        audio_path: str,
        progress_callback: Optional[callable] = None
    ) -> Tuple[str, float]:
        """
        使用 MLX-Whisper 轉錄（macOS MPS 加速）
        
        Returns:
            (transcript, duration)
        """
        try:
            import mlx_whisper
        except ImportError:
            raise RuntimeError("MLX-Whisper 未安裝，請執行: pip install mlx-whisper")
        
        config = get_global_config()
        model_name = get_config_value(config, 'whisper.mlx.model', None)
        
        # 若未設定 mlx.model，回退到 whisper.model 或預設值
        if not model_name:
            model_name = get_config_value(config, 'whisper.model', 'mlx-community/whisper-large-v3-turbo')
            log.warning(f"未設定 whisper.mlx.model，使用回退值: {model_name}")
        
        language = get_config_value(config, 'whisper.mlx.language', get_config_value(config, 'whisper.language', 'zh'))
        
        log.info(f"使用 MLX-Whisper 轉錄 (model={model_name}, language={language})")
        
        if progress_callback:
            progress_callback(15.0, "載入 MLX-Whisper 模型...")
        
        # 繁體中文引導提示
        traditional_chinese_prompt = "這是一場專業會議的逐字記錄，討論主題包含專案進度、決議事項。"
        
        # 使用 mlx_whisper.transcribe
        result = mlx_whisper.transcribe(
            audio_path,
            path_or_hf_repo=model_name,
            initial_prompt=traditional_chinese_prompt,
            word_timestamps=False,
            language=language  # Pass language as decode_option
        )
        
        # 提取結果
        transcript_parts = []
        duration = 0.0
        
        if progress_callback:
            progress_callback(30.0, "轉錄中...")
        
        for segment in result.get('segments', []):
            transcript_parts.append(segment['text'].strip())
            duration = max(duration, segment.get('end', 0.0))
            
            # 更新進度
            if progress_callback and duration > 0:
                current_time = segment.get('end', 0.0)
                progress = 30.0 + (current_time / duration) * 30.0
                progress_callback(min(progress, 60.0), f"轉錄中... {current_time:.0f}/{duration:.0f}秒")
        
        transcript = " ".join(transcript_parts)
        
        if progress_callback:
            progress_callback(60.0, "MLX 轉錄完成")
        
        log.info(f"MLX-Whisper 轉錄完成，音訊長度: {duration:.2f}秒")
        return transcript, duration
    
    def _transcribe_with_faster_whisper(
        self,
        audio_path: str,
        progress_callback: Optional[callable] = None
    ) -> Tuple[str, float]:
        """
        使用 Faster-Whisper 轉錄（CUDA/CPU）
        
        Returns:
            (transcript, duration)
        """
        if progress_callback:
            progress_callback(15.0, "開始轉錄...")
        
        # 執行轉錄 - 使用繁體中文 initial_prompt 引導輸出
        traditional_chinese_prompt = "這是一場專業會議的逐字記錄，討論主題包含專案進度、決議事項。"
        
        segments, info = self._model.transcribe(
            audio_path,
            language="zh",
            beam_size=5,
            initial_prompt=traditional_chinese_prompt,
            vad_filter=True,
            vad_parameters=dict(
                min_silence_duration_ms=500,
                speech_pad_ms=400
            ),
            condition_on_previous_text=True,
            no_speech_threshold=0.6,
            compression_ratio_threshold=2.4,
        )
        
        # 收集所有段落
        transcript_parts = []
        total_duration = info.duration
        processed_duration = 0.0
        
        for segment in segments:
            transcript_parts.append(segment.text.strip())
            processed_duration = segment.end
            
            # 更新進度
            if progress_callback and total_duration > 0:
                progress = 15.0 + (processed_duration / total_duration) * 45.0
                progress_callback(progress, f"轉錄中... {processed_duration:.0f}/{total_duration:.0f}秒")
        
        transcript = " ".join(transcript_parts)
        
        if progress_callback:
            progress_callback(60.0, "Faster-Whisper 轉錄完成")
        
        log.info(f"Faster-Whisper 轉錄完成，音訊長度: {total_duration:.2f}秒")
        return transcript, total_duration
    
    def get_device_info(self) -> dict:
        """取得目前使用的裝置資訊"""
        return {
            "device": self._device.value if self._device else "not_loaded",
            "compute_type": self._compute_type,
            "model": settings.WHISPER_MODEL
        }


# 全域轉錄服務實例
transcription_service = TranscriptionService()
