"""離線說話者分離（speaker diarization）服務（T20260913-1900-01）。

引擎：sherpa-onnx（pyannote segmentation-3.0 ＋ 3D-Speaker CAM++ 中文 embedding）。

定位：**加值層**，不是任務必要條件——任何失敗（套件缺失、模型缺失、解碼失敗、
分群異常、逾時）都回 ``None`` 並記 warning，主流程維持現行（無發言者標籤）行為；
diarization 的失敗永遠不得讓任務失敗（fail-soft，SI-D1）。

離線契約：正式機不得連外。模型由 ``scripts/download_diarization_models.py``
預先放置於 ``settings.DIARIZATION_MODEL_DIR``（預設 ``models/diarization/``；
Docker 內為 ``/app/models/diarization``，與既有 models volume 同構）。

匯入紀律：``sherpa_onnx`` 只在本模組內延後 import；未安裝或未佈署模型時，
本模組可被安全 import（backend.main 啟動不受影響）。

凍結語意（SI-D2）：回傳的 ``speaker`` 為**語音分群編號**，非姓名、非職稱；
任何下游都不得把它當人名寫進正式文件。
"""

from __future__ import annotations

import asyncio
import os
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from typing import List, Optional

from backend.core.config import settings
from backend.core.errors import describe_exception
from backend.core.logger import log


@dataclass
class DiarizationTurn:
    """一段連續發言：時間區間 ＋ 語音分群編號。"""

    start: float
    end: float
    speaker: int


@dataclass
class DiarizationResult:
    """說話者分離結果（純結構，無文字內容）。"""

    turns: List[DiarizationTurn]
    speaker_count: int
    duration_seconds: float
    elapsed_seconds: float
    engine: str = "sherpa-onnx"
    metadata: dict = field(default_factory=dict)


class DiarizationUnavailable(RuntimeError):
    """diarization 不可用（套件或模型缺失）；由呼叫端轉為 fail-soft 回退。"""


class DiarizationService:
    """sherpa-onnx 離線說話者分離封裝（單例；引擎延後載入並重複使用）。"""

    def __init__(self) -> None:
        self._engine = None
        self._engine_key: Optional[tuple] = None

    # ------------------------------------------------------------------
    # 模型路徑與可用性
    # ------------------------------------------------------------------

    def model_dir(self) -> str:
        """模型目錄（相對路徑以工作目錄為基準；Docker 內即 /app/models/diarization）。"""

        return os.path.abspath(settings.DIARIZATION_MODEL_DIR)

    def segmentation_model_path(self) -> str:
        """pyannote segmentation 模型路徑（優先 fp32，其次 int8）。

        v4.7.1 實測（45 分鐘真實會議、k=8）：fp32 覆蓋率 86.8% vs int8 81.3%，
        最大群佔比 79.8% vs 85.9%（int8 會把不同人併進同一群），且速度相同
        （RTF 0.054 vs 0.058）→ 正式路徑以 fp32 為預設。
        """

        base = os.path.join(self.model_dir(), "sherpa-onnx-pyannote-segmentation-3-0")
        for name in ("model.onnx", "model.int8.onnx"):
            candidate = os.path.join(base, name)
            if os.path.exists(candidate):
                return candidate
        return ""

    def embedding_model_path(self) -> str:
        """說話者 embedding 模型路徑（3D-Speaker CAM++ 中文）。"""

        base = self.model_dir()
        for name in (
            "3dspeaker_speech_campplus_sv_zh-cn_16k-common.onnx",
            "embedding.onnx",
        ):
            candidate = os.path.join(base, name)
            if os.path.exists(candidate):
                return candidate
        return ""

    def availability_report(self) -> dict:
        """可用性診斷（給 health／啟動日誌用；不得拋例外）。"""

        report = {
            "enabled": bool(settings.ENABLE_DIARIZATION),
            "package": False,
            "segmentation_model": False,
            "embedding_model": False,
            "model_dir": self.model_dir(),
        }
        try:
            import sherpa_onnx  # noqa: F401

            report["package"] = True
        except Exception as exc:  # noqa: BLE001 — 診斷不得拋例外
            report["package_error"] = type(exc).__name__
        report["segmentation_model"] = bool(self.segmentation_model_path())
        report["embedding_model"] = bool(self.embedding_model_path())
        report["available"] = all(
            (report["package"], report["segmentation_model"], report["embedding_model"])
        )
        return report

    def is_available(self) -> bool:
        return bool(settings.ENABLE_DIARIZATION) and bool(self.availability_report()["available"])

    # ------------------------------------------------------------------
    # 音訊解碼（16kHz mono float32；PyAV 優先，ffmpeg 子程序為後備）
    # ------------------------------------------------------------------

    @staticmethod
    def _decode_with_pyav(audio_path: str):
        import av
        import numpy as np

        chunks = []
        with av.open(audio_path) as container:
            stream = next((s for s in container.streams if s.type == "audio"), None)
            if stream is None:
                raise RuntimeError("音檔沒有 audio stream")
            resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
            for frame in container.decode(stream):
                frame.pts = None
                for resampled in resampler.resample(frame):
                    chunks.append(resampled.to_ndarray().reshape(-1))
            for resampled in resampler.resample(None):
                chunks.append(resampled.to_ndarray().reshape(-1))
        if not chunks:
            raise RuntimeError("音檔解碼後沒有取樣資料")
        samples = np.concatenate(chunks).astype(np.float32) / 32768.0
        return samples

    @staticmethod
    def _decode_with_ffmpeg(audio_path: str):
        import wave

        import numpy as np

        fd, wav_path = tempfile.mkstemp(prefix="diar_", suffix=".wav")
        os.close(fd)
        try:
            completed = subprocess.run(
                [
                    "ffmpeg",
                    "-v",
                    "error",
                    "-y",
                    "-i",
                    audio_path,
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-c:a",
                    "pcm_s16le",
                    wav_path,
                ],
                capture_output=True,
                timeout=1800,
            )
            if completed.returncode != 0:
                raise RuntimeError(
                    f"ffmpeg 解碼失敗（exit={completed.returncode}）："
                    f"{completed.stderr.decode('utf-8', errors='replace')[-500:]}"
                )
            with wave.open(wav_path) as wav:
                frames = wav.readframes(wav.getnframes())
            return np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        finally:
            try:
                os.remove(wav_path)
            except OSError:
                pass

    def _decode_to_16k_mono(self, audio_path: str):
        try:
            return self._decode_with_pyav(audio_path)
        except Exception as exc:  # noqa: BLE001 — 後備解碼器不得讓流程中斷
            log.warning(f"diarization PyAV 解碼失敗（{describe_exception(exc)}），改用 ffmpeg 後備")
            return self._decode_with_ffmpeg(audio_path)

    # ------------------------------------------------------------------
    # 引擎
    # ------------------------------------------------------------------

    def _engine_signature(self) -> tuple:
        return (
            self.segmentation_model_path(),
            self.embedding_model_path(),
            float(settings.DIARIZATION_THRESHOLD),
            int(settings.DIARIZATION_NUM_CLUSTERS),
            float(settings.DIARIZATION_MIN_DURATION_ON),
            float(settings.DIARIZATION_MIN_DURATION_OFF),
        )

    def _load_engine(self):
        """延後載入 sherpa-onnx 引擎（模組級 import 保持純潔）。"""

        segmentation = self.segmentation_model_path()
        embedding = self.embedding_model_path()
        if not segmentation or not embedding:
            raise DiarizationUnavailable(
                f"找不到 diarization 模型（segmentation={bool(segmentation)}, "
                f"embedding={bool(embedding)}, dir={self.model_dir()}）"
            )
        try:
            import sherpa_onnx
        except Exception as exc:  # noqa: BLE001
            raise DiarizationUnavailable(f"sherpa-onnx 未安裝：{describe_exception(exc)}") from exc

        config = sherpa_onnx.OfflineSpeakerDiarizationConfig(
            segmentation=sherpa_onnx.OfflineSpeakerSegmentationModelConfig(
                pyannote=sherpa_onnx.OfflineSpeakerSegmentationPyannoteModelConfig(
                    model=segmentation
                )
            ),
            embedding=sherpa_onnx.SpeakerEmbeddingExtractorConfig(model=embedding),
            clustering=sherpa_onnx.FastClusteringConfig(
                num_clusters=int(settings.DIARIZATION_NUM_CLUSTERS),
                threshold=float(settings.DIARIZATION_THRESHOLD),
            ),
            min_duration_on=float(settings.DIARIZATION_MIN_DURATION_ON),
            min_duration_off=float(settings.DIARIZATION_MIN_DURATION_OFF),
        )
        return sherpa_onnx.OfflineSpeakerDiarization(config)

    def _get_engine(self):
        signature = self._engine_signature()
        if self._engine is not None and self._engine_key == signature:
            return self._engine
        self._engine = self._load_engine()
        self._engine_key = signature
        return self._engine

    # ------------------------------------------------------------------
    # 對外 API
    # ------------------------------------------------------------------

    def diarize(self, audio_path: str) -> Optional[DiarizationResult]:
        """執行說話者分離；任何失敗一律回 ``None``（fail-soft）。"""

        if not settings.ENABLE_DIARIZATION:
            log.info("diarization 已停用（ENABLE_DIARIZATION=false），略過")
            return None

        started = time.time()
        try:
            engine = self._get_engine()
            samples = self._decode_to_16k_mono(audio_path)
            if samples.size == 0:
                raise RuntimeError("解碼後樣本數為 0")
            duration = samples.size / 16000.0
            segmentation = engine.process(samples).sort_by_start_time()
            turns = [
                DiarizationTurn(start=float(seg.start), end=float(seg.end), speaker=int(seg.speaker))
                for seg in segmentation
                if float(seg.end) > float(seg.start)
            ]
            if not turns:
                raise RuntimeError("diarization 未產生任何發言區段")
            speakers = sorted({turn.speaker for turn in turns})
            elapsed = time.time() - started
            log.info(
                "diarization 完成：{} 段、{} 位發言者、音檔 {:.0f}s、耗時 {:.1f}s（RTF {:.3f}）",
                len(turns),
                len(speakers),
                duration,
                elapsed,
                elapsed / duration if duration else 0.0,
            )
            return DiarizationResult(
                turns=turns,
                speaker_count=len(speakers),
                duration_seconds=duration,
                elapsed_seconds=elapsed,
                metadata={
                    "threshold": float(settings.DIARIZATION_THRESHOLD),
                    "num_clusters": int(settings.DIARIZATION_NUM_CLUSTERS),
                    "min_duration_on": float(settings.DIARIZATION_MIN_DURATION_ON),
                    "min_duration_off": float(settings.DIARIZATION_MIN_DURATION_OFF),
                    "segmentation_model": os.path.basename(self.segmentation_model_path()),
                },
            )
        except DiarizationUnavailable as exc:
            log.warning(f"diarization 不可用，改用無發言者標籤流程：{exc}")
            return None
        except Exception as exc:  # noqa: BLE001 — fail-soft 契約
            log.warning(f"diarization 失敗（不影響任務）：{describe_exception(exc)}")
            return None

    async def diarize_async(self, audio_path: str) -> Optional[DiarizationResult]:
        """在 thread executor 執行 diarize()，避免阻塞事件迴圈。

        fail-soft 契約涵蓋這一層：執行緒派工失敗或整體逾時都必須回 ``None``
        （否則 diarization 卡住會讓整個任務無限等待）。
        """
        if not settings.ENABLE_DIARIZATION:
            return None
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self.diarize, audio_path),
                timeout=settings.DIARIZATION_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            log.warning(
                f"diarization 逾時（>{settings.DIARIZATION_TIMEOUT_SECONDS:.0f}s），"
                "改用無發言者標籤流程（背景執行緒仍在收尾，不影響任務結果）"
            )
            return None
        except Exception as exc:  # noqa: BLE001 — fail-soft 契約
            log.warning(f"diarization 執行失敗（不影響任務）：{describe_exception(exc)}")
            return None


diarization_service = DiarizationService()
