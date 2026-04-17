"""
MeetingScribe ASR 轉錄服務

- 支援官方 Transformers Whisper 模型（Breeze-ASR-26）
- 保留 faster-whisper / CTranslate2 回滾路徑
- 支援 GPU/CPU 自動偵測與釋放
"""

from __future__ import annotations

import gc
import os
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

from backend.core.asr_model_resolver import infer_asr_backend, resolve_model_revision, resolve_transformers_model_source
from backend.core.config import settings
from backend.core.logger import log
from backend.services.device_detector import DeviceType, device_detector


@dataclass
class TranscriptionChunk:
    start: float
    end: float
    text: str


@dataclass
class DetailedTranscriptionResult:
    text: str
    duration_seconds: float
    language: str
    chunks: List[TranscriptionChunk] = field(default_factory=list)
    backend: str = "unknown"


def _is_within_directory(path: str, directory: str) -> bool:
    try:
        return os.path.commonpath([path, directory]) == directory
    except ValueError:
        return False


class TranscriptionService:
    """ASR 轉錄服務。"""

    def __init__(self):
        self._model = None
        self._device: Optional[DeviceType] = None
        self._compute_type: str = "int8"
        self._fw_version: Optional[str] = None
        self._backend: str = "unknown"

    def _build_vad_params(
        self,
        threshold: float,
        min_speech_ms: int,
        min_silence_ms: int,
        speech_pad_ms: int,
    ) -> dict:
        import faster_whisper
        from packaging import version

        fw_version = version.parse(faster_whisper.__version__)
        self._fw_version = str(fw_version)

        if fw_version >= version.parse("1.2.0"):
            return {
                "threshold": threshold,
                "min_speech_duration_ms": min_speech_ms,
                "min_silence_duration_ms": min_silence_ms,
                "speech_pad_ms": speech_pad_ms,
            }
        offset = max(threshold - 0.15, 0.01)
        return {
            "onset": threshold,
            "offset": offset,
            "min_speech_duration_ms": min_speech_ms,
            "min_silence_duration_ms": min_silence_ms,
            "speech_pad_ms": speech_pad_ms,
        }

    def _detect_runtime(self, force_cpu: bool = False) -> tuple[str, str]:
        backend = infer_asr_backend(settings.WHISPER_MODEL, settings.ASR_BACKEND)
        if force_cpu:
            return "cpu", "float32" if backend == "transformers" else "int8"

        device_detector.current_device = None
        device_type, compute_type = device_detector.detect_best_device()
        device = device_type.value

        if device_type == DeviceType.MPS:
            log.info("目前 ASR 路徑不使用 MPS，降級到 CPU")
            device = "cpu"
            compute_type = "int8"

        if backend == "transformers":
            if device == "cuda":
                try:
                    import torch

                    if not torch.cuda.is_available():
                        log.warning("系統偵測到 NVIDIA GPU，但目前 torch 未啟用 CUDA，改用 CPU 執行 Transformers ASR")
                        return "cpu", "float32"
                except ImportError:
                    return "cpu", "float32"
                free_vram = device_detector.gpu_memory_mb or 0
                if free_vram < settings.ASR_TRANSFORMERS_MIN_VRAM_MB:
                    log.warning(
                        "可用 VRAM 僅 {}MB，低於 Transformers ASR 建議值 {}MB，降級 CPU",
                        free_vram,
                        settings.ASR_TRANSFORMERS_MIN_VRAM_MB,
                    )
                    return "cpu", "float32"
                return "cuda", "float16"
            return "cpu", "float32"

        if device == "cuda":
            compute_type = settings.WHISPER_COMPUTE_TYPE
        return device, compute_type

    def _load_model(self, force_cpu: bool = False) -> None:
        self._backend = infer_asr_backend(settings.WHISPER_MODEL, settings.ASR_BACKEND)
        device, compute_type = self._detect_runtime(force_cpu=force_cpu)
        self._device = DeviceType(device) if device != "cpu" else DeviceType.CPU
        self._compute_type = compute_type

        if self._backend == "transformers":
            self._load_transformers_pipeline(device=device, compute_type=compute_type)
            return

        self._load_faster_whisper_model(device=device, compute_type=compute_type)

    def _load_faster_whisper_model(self, device: str, compute_type: str) -> None:
        from faster_whisper import WhisperModel

        log.info("載入 faster-whisper 模型: {}, 裝置: {}, 精度: {}", settings.WHISPER_MODEL, device, compute_type)
        self._model = WhisperModel(
            settings.WHISPER_MODEL,
            device=device,
            compute_type=compute_type,
        )

    def _load_transformers_pipeline(self, device: str, compute_type: str) -> None:
        try:
            import torch
            from transformers import pipeline
        except ImportError as exc:
            raise RuntimeError(
                "官方 Breeze-ASR-26 需要 transformers + torch，請先安裝對應依賴。"
            ) from exc

        model_source = resolve_transformers_model_source(
            settings.WHISPER_MODEL,
            revision=resolve_model_revision(
                settings.WHISPER_MODEL,
                settings.WHISPER_MODEL_REVISION,
            ),
            local_files_only=settings.ASR_LOCAL_FILES_ONLY,
            allow_patterns=settings.asr_safe_allow_patterns_list,
            deny_patterns=settings.asr_safe_deny_patterns_list,
        )

        torch_dtype = torch.float16 if device == "cuda" and compute_type == "float16" else torch.float32
        pipeline_device = 0 if device == "cuda" else -1

        log.info(
            "載入 Transformers ASR 模型: {}@{}, 裝置: {}, dtype: {}",
            settings.WHISPER_MODEL,
            resolve_model_revision(settings.WHISPER_MODEL, settings.WHISPER_MODEL_REVISION) or "unpinned",
            device,
            torch_dtype,
        )
        self._model = pipeline(
            task="automatic-speech-recognition",
            model=model_source,
            tokenizer=model_source,
            feature_extractor=model_source,
            device=pipeline_device,
            torch_dtype=torch_dtype,
            model_kwargs={
                "use_safetensors": True,
                "low_cpu_mem_usage": True,
            },
        )

    def _unload_model(self) -> None:
        if self._model is None:
            return

        log.info("釋放 ASR 模型與快取...")
        del self._model
        self._model = None
        gc.collect()

        if self._device == DeviceType.CUDA:
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                    torch.cuda.synchronize()
            except Exception as exc:  # noqa: BLE001
                log.warning("清空 CUDA 快取時發生錯誤: {}", exc)

        self._device = None
        self._compute_type = "int8"

    @staticmethod
    def _probe_duration(audio_path: str) -> float:
        try:
            import ffmpeg

            probe = ffmpeg.probe(audio_path)
            return float(probe["format"]["duration"])
        except Exception:
            return 0.0

    @staticmethod
    def _normalize_chunks(raw_chunks: list[dict]) -> list[TranscriptionChunk]:
        chunks: list[TranscriptionChunk] = []
        for raw_chunk in raw_chunks:
            timestamp = raw_chunk.get("timestamp") or raw_chunk.get("timestamps") or (0.0, 0.0)
            if isinstance(timestamp, (list, tuple)) and len(timestamp) == 2:
                start, end = timestamp
            else:
                start, end = 0.0, 0.0
            chunks.append(
                TranscriptionChunk(
                    start=float(start or 0.0),
                    end=float(end or 0.0),
                    text=(raw_chunk.get("text") or "").strip(),
                )
            )
        return [chunk for chunk in chunks if chunk.text]

    @staticmethod
    def _load_audio_array(audio_path: str) -> np.ndarray:
        import av

        with av.open(audio_path) as container:
            resampler = av.audio.resampler.AudioResampler(format="s16", layout="mono", rate=16000)
            frames: list[np.ndarray] = []
            for frame in container.decode(audio=0):
                converted = resampler.resample(frame)
                if isinstance(converted, list):
                    iterable = converted
                else:
                    iterable = [converted]
                for item in iterable:
                    if item is None:
                        continue
                    frames.append(item.to_ndarray().reshape(-1).astype(np.int16))
        if not frames:
            raise RuntimeError(f"無法讀取音訊資料: {audio_path}")
        return np.concatenate(frames).astype(np.float32) / 32768.0

    def _build_transformers_generate_kwargs(self) -> dict:
        kwargs = {"task": "transcribe"}
        if settings.WHISPER_LANGUAGE and settings.WHISPER_LANGUAGE != "auto":
            kwargs["language"] = settings.WHISPER_LANGUAGE

        tokenizer = getattr(self._model, "tokenizer", None)
        if settings.ASR_INITIAL_PROMPT and settings.WHISPER_LANGUAGE != "auto" and tokenizer:
            get_prompt_ids = getattr(tokenizer, "get_prompt_ids", None)
            if callable(get_prompt_ids):
                try:
                    kwargs["prompt_ids"] = get_prompt_ids(settings.ASR_INITIAL_PROMPT)
                except Exception as exc:  # noqa: BLE001
                    log.warning("無法套用 transformers prompt_ids，忽略初始提示詞: {}", exc)
        return kwargs

    def _transcribe_with_faster_whisper(self, audio_path: str) -> DetailedTranscriptionResult:
        vad_params = self._build_vad_params(
            threshold=settings.ASR_VAD_THRESHOLD,
            min_speech_ms=settings.ASR_VAD_MIN_SPEECH_MS,
            min_silence_ms=settings.ASR_VAD_MIN_SILENCE_MS,
            speech_pad_ms=settings.ASR_VAD_SPEECH_PAD_MS,
        )
        segments, info = self._model.transcribe(
            audio_path,
            language=settings.WHISPER_LANGUAGE if settings.WHISPER_LANGUAGE != "auto" else None,
            beam_size=settings.ASR_BEAM_SIZE,
            initial_prompt=settings.ASR_INITIAL_PROMPT or None,
            vad_filter=settings.ASR_VAD_ENABLED,
            vad_parameters=vad_params,
            condition_on_previous_text=True,
            no_speech_threshold=0.6,
            compression_ratio_threshold=2.4,
        )

        chunks: list[TranscriptionChunk] = []
        texts: list[str] = []
        for segment in segments:
            text = segment.text.strip()
            if not text:
                continue
            chunks.append(TranscriptionChunk(start=float(segment.start), end=float(segment.end), text=text))
            texts.append(text)

        return DetailedTranscriptionResult(
            text=" ".join(texts).strip(),
            duration_seconds=float(info.duration or 0.0),
            language=info.language or settings.WHISPER_LANGUAGE,
            chunks=chunks,
            backend="faster_whisper",
        )

    def _transcribe_with_transformers(self, audio_path: str) -> DetailedTranscriptionResult:
        audio_array = self._load_audio_array(audio_path)
        chunk_samples = max(settings.ASR_CHUNK_LENGTH_SECONDS, 1) * 16000
        generate_kwargs = self._build_transformers_generate_kwargs()
        texts: list[str] = []
        chunks: list[TranscriptionChunk] = []
        detected_language = settings.WHISPER_LANGUAGE or "auto"

        for start_index in range(0, len(audio_array), chunk_samples):
            window = audio_array[start_index:start_index + chunk_samples]
            if window.size == 0:
                continue

            result = self._model(
                {"array": window, "sampling_rate": 16000},
                return_timestamps=settings.ASR_RETURN_TIMESTAMPS,
                generate_kwargs=generate_kwargs,
            )
            offset = start_index / 16000.0
            window_text = (result.get("text") or "").strip()
            window_chunks = self._normalize_chunks(result.get("chunks", []))
            if window_chunks and any(chunk.end > chunk.start for chunk in window_chunks):
                for chunk in window_chunks:
                    chunk.start += offset
                    chunk.end += offset
                    chunks.append(chunk)
                    texts.append(chunk.text)
            elif window_text:
                end = offset + (len(window) / 16000.0)
                chunks.append(TranscriptionChunk(start=offset, end=end, text=window_text))
                texts.append(window_text)

            if result.get("language"):
                detected_language = result["language"]

        text = " ".join(texts).strip()
        duration = len(audio_array) / 16000.0
        language = detected_language

        return DetailedTranscriptionResult(
            text=text,
            duration_seconds=duration,
            language=language,
            chunks=chunks,
            backend="transformers",
        )

    def transcribe_detailed(
        self,
        audio_path: str,
        progress_callback: Optional[callable] = None,
        max_retries: int = 1,
        force_cpu: bool = False,
    ) -> DetailedTranscriptionResult:
        abs_audio_path = os.path.abspath(audio_path)
        abs_uploads_dir = os.path.abspath(settings.uploads_dir)

        if not _is_within_directory(abs_audio_path, abs_uploads_dir):
            raise ValueError(f"不允許的檔案路徑: {audio_path}")
        if not os.path.exists(abs_audio_path):
            raise FileNotFoundError(f"音訊檔案不存在: {audio_path}")

        try:
            if progress_callback:
                progress_callback(5.0, "載入 ASR 模型...")
            self._load_model(force_cpu=force_cpu)

            if progress_callback:
                progress_callback(15.0, f"開始轉錄 ({self._backend}, {self._device.value.upper() if self._device else 'CPU'})...")

            result = (
                self._transcribe_with_transformers(abs_audio_path)
                if self._backend == "transformers"
                else self._transcribe_with_faster_whisper(abs_audio_path)
            )

            if progress_callback:
                progress_callback(60.0, "轉錄完成")
            return result

        except Exception as exc:
            log.error("轉錄失敗: {}", exc)
            if self._device != DeviceType.CPU and max_retries > 0:
                log.info("嘗試降級到 CPU 重新轉錄...")
                device_detector.fallback_to_cpu()
                self._unload_model()
                return self.transcribe_detailed(
                    audio_path,
                    progress_callback=progress_callback,
                    max_retries=max_retries - 1,
                    force_cpu=True,
                )
            raise
        finally:
            self._unload_model()

    def transcribe(
        self,
        audio_path: str,
        progress_callback: Optional[callable] = None,
        max_retries: int = 1,
    ) -> Tuple[str, float]:
        result = self.transcribe_detailed(
            audio_path,
            progress_callback=progress_callback,
            max_retries=max_retries,
        )
        return result.text, result.duration_seconds

    def get_device_info(self) -> dict:
        return {
            "device": self._device.value if self._device else "not_loaded",
            "compute_type": self._compute_type,
            "backend": self._backend,
            "model": settings.WHISPER_MODEL,
            "revision": resolve_model_revision(settings.WHISPER_MODEL, settings.WHISPER_MODEL_REVISION),
        }


transcription_service = TranscriptionService()
