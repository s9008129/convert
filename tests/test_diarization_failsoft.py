#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""diarization fail-soft 契約測試（T20260913-1900-01，SI-D1）。

契約：說話者分離是加值層。套件缺失、模型缺失、音檔不存在、音檔過短
（解碼後無樣本／引擎無發言區段）、引擎例外——一律回 ``None``，不拋致命
例外，讓上層 ``task_processor._label_speakers`` 回退為無標籤逐字稿。

所有失敗情境以 monkeypatch 模擬；不載入真實 ONNX 模型、不下載任何檔案、
不使用 GPU，全部 deterministic。

已知實作缺口（唯讀 backend、不在此測試檔修；詳見本次任務回報）：
1. ``diarize_async()`` 沒有包住 ``asyncio.to_thread`` 本身的例外：執行緒派工
   失敗時會外拋 ``RuntimeError``，服務層「一律回 None」的契約不成立
   （``test_diarize_async_thread_dispatch_failure_still_returns_none`` 以
   已於 v4.7.1 修復並由回歸測試鎖住）。
2. ``diarization.py`` 模組 docstring 把「逾時」列為 fail-soft 情境之一，但
   程式中沒有任何整體逾時機制（只有 ffmpeg 子程序 timeout=1800）——sherpa
   卡住時任務會一直等，不會回 None。最小修法：
   ``asyncio.wait_for(asyncio.to_thread(...), timeout=...DIARIZATION_TIMEOUT...)``。
"""

from __future__ import annotations

import importlib
import sys
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import numpy as np
import pytest

from backend.core.config import settings
from backend.services.diarization import (
    DiarizationResult,
    DiarizationService,
    DiarizationTurn,
)
from backend.services.speaker_transcript import SPEAKER_NOTE
from backend.services.task_processor import TaskProcessor

# ``backend.services.task_processor`` 這個「模組」名稱會被 __init__.py 匯出的
# TaskProcessor 實例遮蔽，一律以 importlib 取得真正的模組物件。
task_processor_module = importlib.import_module("backend.services.task_processor")
diarization_module = importlib.import_module("backend.services.diarization")


class _FakeSegment:
    """sherpa-onnx 發言區段替身（只需 start/end/speaker 三欄）。"""

    def __init__(self, start: float, end: float, speaker: int) -> None:
        self.start = start
        self.end = end
        self.speaker = speaker


class _FakeEngine:
    """最小引擎替身：只實作 diarize() 用到的 process().sort_by_start_time()。"""

    def __init__(self, segments=None, error: Exception | None = None) -> None:
        self.segments = list(segments or [])
        self.error = error
        self.processed_samples = None

    def process(self, samples):
        self.processed_samples = samples
        if self.error is not None:
            raise self.error
        return SimpleNamespace(sort_by_start_time=lambda: list(self.segments))


@pytest.fixture(autouse=True)
def _isolate_diarization_settings(monkeypatch, tmp_path):
    """所有測試都不得碰到真實模型目錄，也不得受外部環境設定影響。"""

    monkeypatch.setattr(settings, "ENABLE_DIARIZATION", True)
    monkeypatch.setattr(settings, "DIARIZATION_MODEL_DIR", str(tmp_path / "models"))


def _service_with_fake_engine(monkeypatch, engine: _FakeEngine) -> DiarizationService:
    service = DiarizationService()
    monkeypatch.setattr(service, "_get_engine", lambda: engine)
    return service


def _patch_decode_samples(monkeypatch, service: DiarizationService, samples: np.ndarray):
    monkeypatch.setattr(service, "_decode_to_16k_mono", lambda _path: samples)


def _make_task():
    return SimpleNamespace(task_id="task-diar-1")


def _chunks(*items):
    return SimpleNamespace(
        chunks=[SimpleNamespace(start=start, end=end, text=text) for start, end, text in items]
    )


# ---------------------------------------------------------------------------
# 停用與不可用：回 None，不載入引擎、不拋例外
# ---------------------------------------------------------------------------


def test_disabled_returns_none_without_loading_engine(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_DIARIZATION", False)
    service = DiarizationService()

    def _must_not_load():
        raise AssertionError("ENABLE_DIARIZATION=false 時不得載入引擎")

    monkeypatch.setattr(service, "_get_engine", _must_not_load)

    assert service.diarize("/no/such/audio.m4a") is None


async def test_disabled_diarize_async_returns_none(monkeypatch):
    monkeypatch.setattr(settings, "ENABLE_DIARIZATION", False)
    service = DiarizationService()

    def _must_not_load():
        raise AssertionError("ENABLE_DIARIZATION=false 時不得載入引擎")

    monkeypatch.setattr(service, "_get_engine", _must_not_load)

    assert await service.diarize_async("/no/such/audio.m4a") is None


def test_missing_models_returns_none_and_reports_unavailable(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "DIARIZATION_MODEL_DIR", str(tmp_path / "missing-models"))
    service = DiarizationService()

    report = service.availability_report()  # 診斷本身不得拋例外

    assert report["segmentation_model"] is False
    assert report["embedding_model"] is False
    assert report["available"] is False
    assert service.is_available() is False
    assert service.diarize("/no/such/audio.m4a") is None


def test_sherpa_import_failure_returns_none(monkeypatch):
    monkeypatch.setattr(
        DiarizationService, "segmentation_model_path", lambda self: "/fake/segmentation.onnx"
    )
    monkeypatch.setattr(
        DiarizationService, "embedding_model_path", lambda self: "/fake/embedding.onnx"
    )
    monkeypatch.setitem(sys.modules, "sherpa_onnx", None)  # 模擬套件未安裝
    service = DiarizationService()

    report = service.availability_report()

    assert report["package"] is False
    assert report["package_error"] in ("ImportError", "ModuleNotFoundError")
    assert service.diarize("/no/such/audio.m4a") is None


def test_unexpected_engine_load_error_returns_none(monkeypatch):
    service = DiarizationService()

    def _boom():
        raise RuntimeError("engine load exploded")

    monkeypatch.setattr(service, "_load_engine", _boom)

    assert service.diarize("/no/such/audio.m4a") is None


# ---------------------------------------------------------------------------
# 音訊問題：不存在／過短（無樣本、無發言區段）
# ---------------------------------------------------------------------------


def test_missing_audio_file_returns_none(monkeypatch):
    engine = _FakeEngine(segments=[_FakeSegment(0.0, 1.0, 0)])
    service = _service_with_fake_engine(monkeypatch, engine)

    # 對應真實行為：PyAV 對不存在檔案拋 FileNotFoundError，ffmpeg 後備非零退出
    def _pyav_fail(_path):
        raise FileNotFoundError("/no/such/audio.m4a")

    def _ffmpeg_fail(_path):
        raise RuntimeError("ffmpeg 解碼失敗（exit=1）：No such file or directory")

    monkeypatch.setattr(service, "_decode_with_pyav", _pyav_fail)
    monkeypatch.setattr(service, "_decode_with_ffmpeg", _ffmpeg_fail)

    assert service.diarize("/no/such/audio.m4a") is None
    assert engine.processed_samples is None  # 解碼失敗後不得進入引擎


def test_empty_decoded_samples_returns_none(monkeypatch):
    engine = _FakeEngine()
    service = _service_with_fake_engine(monkeypatch, engine)
    _patch_decode_samples(monkeypatch, service, np.zeros(0, dtype=np.float32))

    assert service.diarize("/no/such/audio.wav") is None
    assert engine.processed_samples is None


def test_engine_without_any_turn_returns_none(monkeypatch):
    engine = _FakeEngine(segments=[])  # 過短／無語音 → 引擎沒有發言區段
    service = _service_with_fake_engine(monkeypatch, engine)
    _patch_decode_samples(monkeypatch, service, np.zeros(16000 // 2, dtype=np.float32))

    assert service.diarize("/no/such/audio.wav") is None
    assert engine.processed_samples is not None


def test_engine_exception_returns_none(monkeypatch):
    engine = _FakeEngine(error=RuntimeError("onnxruntime session failed"))
    service = _service_with_fake_engine(monkeypatch, engine)
    _patch_decode_samples(monkeypatch, service, np.zeros(16000 * 3, dtype=np.float32))

    assert service.diarize("/no/such/audio.wav") is None


# ---------------------------------------------------------------------------
# 正向對照：成功路徑仍回結構化結果（證明上述 None 不是 stub 壞掉造成）
# ---------------------------------------------------------------------------


def test_successful_diarization_returns_structured_result(monkeypatch):
    engine = _FakeEngine(
        segments=[
            _FakeSegment(0.0, 2.0, 1),
            _FakeSegment(2.0, 3.0, 0),
            _FakeSegment(3.0, 3.0, 0),  # 零長度區段必須被過濾
        ]
    )
    service = _service_with_fake_engine(monkeypatch, engine)
    _patch_decode_samples(monkeypatch, service, np.zeros(16000 * 3, dtype=np.float32))

    result = service.diarize("/no/such/audio.wav")

    assert isinstance(result, DiarizationResult)
    assert [(turn.start, turn.end, turn.speaker) for turn in result.turns] == [
        (0.0, 2.0, 1),
        (2.0, 3.0, 0),
    ]
    assert result.speaker_count == 2
    assert result.duration_seconds == pytest.approx(3.0)
    assert result.engine == "sherpa-onnx"
    assert result.metadata["num_clusters"] == settings.DIARIZATION_NUM_CLUSTERS


async def test_diarize_async_returns_same_structured_result(monkeypatch):
    engine = _FakeEngine(segments=[_FakeSegment(0.0, 4.0, 3)])
    service = _service_with_fake_engine(monkeypatch, engine)
    _patch_decode_samples(monkeypatch, service, np.zeros(16000 * 4, dtype=np.float32))

    result = await service.diarize_async("/no/such/audio.wav")

    assert result is not None
    assert [(turn.start, turn.end, turn.speaker) for turn in result.turns] == [(0.0, 4.0, 3)]


async def test_diarize_async_returns_none_when_engine_missing(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "DIARIZATION_MODEL_DIR", str(tmp_path / "missing-models"))
    service = DiarizationService()

    assert await service.diarize_async("/no/such/audio.m4a") is None


async def test_diarize_async_thread_dispatch_failure_still_returns_none(monkeypatch):
    """執行緒派工失敗必須回 None（v4.7.1 已修：diarize_async 包住 to_thread 例外）。"""
    service = DiarizationService()

    def _dispatch_failure(*_args, **_kwargs):
        raise RuntimeError("cannot schedule new futures after shutdown")

    monkeypatch.setattr(diarization_module.asyncio, "to_thread", _dispatch_failure)

    assert await service.diarize_async("/no/such/audio.m4a") is None


# ---------------------------------------------------------------------------
# 上層回退：task_processor._label_speakers 永遠不讓任務失敗
# ---------------------------------------------------------------------------


async def test_label_speakers_skips_diarization_without_chunk_timestamps(monkeypatch):
    processor = TaskProcessor()
    monkeypatch.setattr(processor, "_update_progress", AsyncMock())
    diarize_mock = AsyncMock(return_value=None)
    monkeypatch.setattr(task_processor_module.diarization_service, "diarize_async", diarize_mock)

    assert await processor._label_speakers(_make_task(), "m.m4a", _chunks()) is None
    diarize_mock.assert_not_awaited()


async def test_label_speakers_falls_back_when_diarization_returns_none(monkeypatch):
    processor = TaskProcessor()
    monkeypatch.setattr(processor, "_update_progress", AsyncMock())
    diarize_mock = AsyncMock(return_value=None)
    monkeypatch.setattr(task_processor_module.diarization_service, "diarize_async", diarize_mock)

    result = await processor._label_speakers(
        _make_task(), "m.m4a", _chunks((0.0, 2.0, "大家好"))
    )

    assert result is None
    diarize_mock.assert_awaited_once()


async def test_label_speakers_swallows_unexpected_diarization_exception(monkeypatch):
    processor = TaskProcessor()
    monkeypatch.setattr(processor, "_update_progress", AsyncMock())

    async def _boom(_path):
        raise RuntimeError("diarization exploded")

    monkeypatch.setattr(task_processor_module.diarization_service, "diarize_async", _boom)

    result = await processor._label_speakers(
        _make_task(), "m.m4a", _chunks((0.0, 2.0, "大家好"))
    )

    assert result is None


async def test_diarize_async_timeout_returns_none(monkeypatch):
    """整體逾時必須回 None（v4.7.1）：sherpa 卡住不得讓任務無限等待。"""
    service = DiarizationService()
    monkeypatch.setattr(settings, "DIARIZATION_TIMEOUT_SECONDS", 0.05)

    def _slow(_path):
        time.sleep(0.5)
        return None

    monkeypatch.setattr(service, "diarize", _slow)

    assert await service.diarize_async("/no/such/audio.m4a") is None


async def test_label_speakers_skips_when_timestamps_unusable(monkeypatch):
    """ASR 全零時間軸（Apple 降級片段）不得產生錯誤的發言者標籤。"""
    processor = TaskProcessor()
    monkeypatch.setattr(processor, "_update_progress", AsyncMock())
    diarize_mock = AsyncMock(
        return_value=DiarizationResult(
            turns=[DiarizationTurn(0.0, 4.0, 1)],
            speaker_count=1,
            duration_seconds=4.0,
            elapsed_seconds=0.1,
        )
    )
    monkeypatch.setattr(task_processor_module.diarization_service, "diarize_async", diarize_mock)

    result = await processor._label_speakers(
        _make_task(), "m.m4a", _chunks((0.0, 0.0, "一"), (0.0, 0.0, "二"), (0.0, 0.0, "三"))
    )

    assert result is None
    diarize_mock.assert_not_awaited()


async def test_label_speakers_tolerates_minority_degraded_segments(monkeypatch):
    """少數降級片段（<一半）不影響標註：仍以可用時間軸完成對位。"""
    processor = TaskProcessor()
    monkeypatch.setattr(processor, "_update_progress", AsyncMock())
    monkeypatch.setattr(
        task_processor_module.diarization_service,
        "diarize_async",
        AsyncMock(
            return_value=DiarizationResult(
                turns=[DiarizationTurn(0.0, 2.0, 1), DiarizationTurn(2.0, 4.0, 2)],
                speaker_count=2,
                duration_seconds=4.0,
                elapsed_seconds=0.1,
            )
        ),
    )

    text = await processor._label_speakers(
        _make_task(),
        "m.m4a",
        _chunks((0.0, 2.0, "大家好"), (2.0, 4.0, "你好"), (0.0, 0.0, "雜訊")),
    )

    assert text is not None
    assert "發言者1：大家好" in text


async def test_label_speakers_returns_labeled_text_on_success(monkeypatch):
    processor = TaskProcessor()
    monkeypatch.setattr(processor, "_update_progress", AsyncMock())
    diarized = DiarizationResult(
        turns=[DiarizationTurn(0.0, 2.0, 1), DiarizationTurn(2.0, 4.0, 2)],
        speaker_count=2,
        duration_seconds=4.0,
        elapsed_seconds=0.1,
    )
    monkeypatch.setattr(
        task_processor_module.diarization_service,
        "diarize_async",
        AsyncMock(return_value=diarized),
    )

    text = await processor._label_speakers(
        _make_task(), "m.m4a", _chunks((0.0, 2.0, "大家好"), (2.0, 4.0, "你好"))
    )

    assert text is not None
    assert text.startswith(SPEAKER_NOTE)
    assert "發言者1：大家好" in text
    assert "發言者2：你好" in text
