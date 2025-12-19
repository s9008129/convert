"""
MeetingScribe Whisper 轉錄服務
支援 GPU/CPU 自動偵測和降級

v4.0.0: 升級至 Breeze-ASR-25 模型
- 專為台灣繁體中文和中英混用優化
- 整合 Silero VAD v6 語音活動偵測
- 大幅降低長音檔幻覺問題

v3.5.2: 修復 GPU 加速失效 + 實現 VRAM 資源釋放機制
"""

import os
import gc
import time
from typing import Optional, Generator, Tuple
from backend.core.config import settings
from backend.core.logger import log
from backend.services.device_detector import device_detector, DeviceType


class TranscriptionService:
    """
    Whisper 語音轉錄服務
    支援 CUDA/MPS/CPU 自動選擇和降級
    
    v4.0.0 改進：
    - 升級至 Breeze-ASR-25 (MediaTek Research 台灣專用模型)
    - 整合 Silero VAD v6 預處理，過濾靜音減少幻覺
    - 優化長音檔處理，解決重複字樣問題
    
    v3.5.2 改進：
    - 每次轉錄後釋放模型，避免 VRAM 持續佔用
    - 強制重新偵測 GPU 可用性，避免與 Ollama 資源競爭
    """
    
    def __init__(self):
        self._model = None
        self._device: Optional[DeviceType] = None
        self._compute_type: str = "int8"
        
    def _load_model(self, force_cpu: bool = False):
        """
        載入 Whisper 模型（每次轉錄前重新載入以確保 GPU 可用）
        
        v4.0.0: 支援從 HuggingFace 載入 Breeze-ASR-25 模型
        """
        from faster_whisper import WhisperModel
        
        if force_cpu:
            device = "cpu"
            compute_type = "int8"
        else:
            # v3.5.2: 強制重新偵測，確保取得最新 GPU 狀態
            # 這是解決 GPU 加速失效的關鍵
            device_detector.current_device = None  # 重置快取
            device_type, compute_type = device_detector.detect_best_device()
            device = device_type.value
            
            # MPS 暫不支援，降級到 CPU
            if device_type == DeviceType.MPS:
                log.info("faster-whisper 不支援 MPS，使用 CPU 模式")
                device = "cpu"
                compute_type = "int8"
            
            # v4.0.0: 使用設定檔中的 compute_type（如果是 CUDA）
            if device == "cuda":
                compute_type = settings.WHISPER_COMPUTE_TYPE
        
        self._device = DeviceType(device) if device != "cpu" else DeviceType.CPU
        self._compute_type = compute_type
        
        # v4.0.0: 使用 settings.WHISPER_MODEL（支援 HuggingFace repo）
        model_name = settings.WHISPER_MODEL
        log.info(f"載入 Whisper 模型: {model_name}, 裝置: {device}, 精度: {compute_type}")
        
        try:
            self._model = WhisperModel(
                model_name,
                device=device,
                compute_type=compute_type
            )
            log.info(f"✅ Whisper 模型載入成功 (裝置: {device.upper()}, 模型: {model_name})")
        except Exception as e:
            log.error(f"Whisper 模型載入失敗: {e}")
            if device != "cpu":
                log.info("嘗試降級到 CPU 模式...")
                self._load_model(force_cpu=True)
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
            
        v3.5.2 改進：
        - 轉錄完成後自動釋放模型
        - 確保 VRAM 不會被持續佔用
        """
        try:
            # v3.5.2: 每次轉錄前重新載入模型（確保使用最新 GPU 狀態）
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
            
            if progress_callback:
                progress_callback(10.0, f"開始轉錄 (裝置: {self._device.value.upper() if self._device else 'CPU'})...")
            
            # 執行轉錄 - v4.0.0: 使用 Breeze-ASR-25 + Silero VAD v6
            # Breeze-ASR-25 專為台灣繁體中文和中英混用優化
            # VAD 參數來自 settings，可透過 config.yaml 調整
            
            # v4.0.0: 使用設定檔中的參數
            vad_params = {
                "threshold": settings.ASR_VAD_THRESHOLD,
                "min_speech_duration_ms": settings.ASR_VAD_MIN_SPEECH_MS,
                "min_silence_duration_ms": settings.ASR_VAD_MIN_SILENCE_MS,
                "speech_pad_ms": settings.ASR_VAD_SPEECH_PAD_MS
            }
            
            segments, info = self._model.transcribe(
                audio_path,
                language="zh",  # 指定中文語言
                beam_size=settings.ASR_BEAM_SIZE,
                initial_prompt=settings.ASR_INITIAL_PROMPT,  # 引導輸出繁體中文風格
                vad_filter=settings.ASR_VAD_ENABLED,  # v4.0.0: 使用 Silero VAD v6
                vad_parameters=vad_params,
                condition_on_previous_text=True,  # 啟用上下文連貫性
                no_speech_threshold=0.6,  # 降低靜音誤判
                compression_ratio_threshold=2.4,  # 避免重複輸出
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
                    progress = 10.0 + (processed_duration / total_duration) * 50.0
                    progress_callback(progress, f"轉錄中... {processed_duration:.0f}/{total_duration:.0f}秒")
            
            transcript = " ".join(transcript_parts)
            
            # v4.0.0: Breeze-ASR-25 直接輸出繁體中文，無需額外轉換
            
            elapsed = time.time() - start_time
            speed_ratio = total_duration / elapsed if elapsed > 0 else 0
            log.info(f"轉錄完成，耗時: {elapsed:.1f}秒，音訊時長: {total_duration:.1f}秒，速度: {speed_ratio:.1f}x，裝置: {self._device.value.upper() if self._device else 'CPU'}")
            
            if progress_callback:
                progress_callback(60.0, "轉錄完成")
            
            return transcript, total_duration
            
        except Exception as e:
            log.error(f"轉錄失敗: {e}")
            
            # 如果是 GPU 錯誤，嘗試降級（限制重試次數避免無限遞迴）
            if self._device != DeviceType.CPU and max_retries > 0:
                log.info("嘗試降級到 CPU 重新轉錄...")
                device_detector.fallback_to_cpu()
                self._unload_model()  # v3.5.2: 降級前先釋放模型
                self._load_model(force_cpu=True)
                return self.transcribe(audio_path, progress_callback, max_retries - 1)
            
            raise
        
        finally:
            # v3.5.2: 轉錄完成後一律釋放模型，確保 VRAM 可供 Ollama 使用
            self._unload_model()
    
    def get_device_info(self) -> dict:
        """取得目前使用的裝置資訊"""
        return {
            "device": self._device.value if self._device else "not_loaded",
            "compute_type": self._compute_type,
            "model": settings.WHISPER_MODEL
        }


# 全域轉錄服務實例
transcription_service = TranscriptionService()
