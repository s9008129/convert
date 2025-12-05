"""
MeetingScribe Whisper 轉錄服務
支援 GPU/CPU 自動偵測和降級
使用 whisper-medium 模型直接輸出台灣繁體中文
"""

import os
import time
from typing import Optional, Generator, Tuple
from backend.core.config import settings
from backend.core.logger import log
from backend.services.device_detector import device_detector, DeviceType


class TranscriptionService:
    """
    Whisper 語音轉錄服務
    支援 CUDA/MPS/CPU 自動選擇和降級
    """
    
    def __init__(self):
        self._model = None
        self._device: Optional[DeviceType] = None
        self._compute_type: str = "int8"
        
    def _load_model(self, force_cpu: bool = False):
        """載入 Whisper 模型"""
        from faster_whisper import WhisperModel
        
        if force_cpu:
            device = "cpu"
            compute_type = "int8"
        else:
            # 使用智能偵測器
            device_type, compute_type = device_detector.detect_best_device()
            device = device_type.value
            
            # MPS 暫不支援，降級到 CPU
            if device_type == DeviceType.MPS:
                log.info("faster-whisper 不支援 MPS，使用 CPU 模式")
                device = "cpu"
                compute_type = "int8"
        
        self._device = DeviceType(device) if device != "cpu" else DeviceType.CPU
        self._compute_type = compute_type
        
        log.info(f"載入 Whisper 模型: {settings.WHISPER_MODEL}, 裝置: {device}, 精度: {compute_type}")
        
        try:
            self._model = WhisperModel(
                settings.WHISPER_MODEL,
                device=device,
                compute_type=compute_type
            )
            log.info("✅ Whisper 模型載入成功")
        except Exception as e:
            log.error(f"Whisper 模型載入失敗: {e}")
            if device != "cpu":
                log.info("嘗試降級到 CPU 模式...")
                self._load_model(force_cpu=True)
            else:
                raise
    
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
        """
        if not self._model:
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
        
        try:
            if progress_callback:
                progress_callback(10.0, "開始轉錄...")
            
            # 執行轉錄 - 使用繁體中文 initial_prompt 引導輸出
            # Whisper 不區分 zh-TW/zh-CN，使用 initial_prompt 是業界最佳實踐
            # 注意：initial_prompt 不應該包含指令性文字，應該是「範例內容」格式
            # 參考: https://github.com/openai/whisper/discussions/117
            traditional_chinese_prompt = "這是一場專業會議的逐字記錄，討論主題包含專案進度、決議事項。"
            
            segments, info = self._model.transcribe(
                audio_path,
                language="zh",  # 指定中文語言
                beam_size=5,
                initial_prompt=traditional_chinese_prompt,  # 引導輸出繁體中文風格
                vad_filter=True,  # 過濾靜音
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    speech_pad_ms=400
                ),
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
            
            # whisper-medium 模型直接輸出繁體中文，無需額外轉換
            
            elapsed = time.time() - start_time
            log.info(f"轉錄完成，耗時: {elapsed:.1f}秒，音訊時長: {total_duration:.1f}秒")
            
            if progress_callback:
                progress_callback(60.0, "轉錄完成")
            
            return transcript, total_duration
            
        except Exception as e:
            log.error(f"轉錄失敗: {e}")
            
            # 如果是 GPU 錯誤，嘗試降級（限制重試次數避免無限遞迴）
            if self._device != DeviceType.CPU and max_retries > 0:
                log.info("嘗試降級到 CPU 重新轉錄...")
                device_detector.fallback_to_cpu()
                self._model = None
                self._load_model(force_cpu=True)
                return self.transcribe(audio_path, progress_callback, max_retries - 1)
            
            raise
    
    def get_device_info(self) -> dict:
        """取得目前使用的裝置資訊"""
        return {
            "device": self._device.value if self._device else "not_loaded",
            "compute_type": self._compute_type,
            "model": settings.WHISPER_MODEL
        }


# 全域轉錄服務實例
transcription_service = TranscriptionService()
