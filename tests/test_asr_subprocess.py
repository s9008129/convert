#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""ASR 子程序隔離測試（v4.7.0）。

worker 端：progress JSON lines 格式、結果檔內容、錯誤 exit code。
父程序端：進度轉發、stderr 錯誤傳遞、spawn 失敗退回 in-process、inprocess 模式。
"""

import asyncio
import json
import os
import tempfile
from unittest.mock import AsyncMock, Mock

import pytest

# 必須在 import backend 之前設定 DATA_DIR：loguru 於 backend.core.logger 匯入時
# 就會建立 DATA_DIR/logs 並寫檔（預設 /app/data 在此環境不可寫）。
os.environ["DATA_DIR"] = tempfile.mkdtemp()

from backend.core.config import settings  # noqa: E402
from backend.services import asr_subprocess  # noqa: E402
from backend.services.transcription import (  # noqa: E402
    DetailedTranscriptionResult,
    TranscriptionChunk,
)


# ========================================
# worker 端（in-process 執行 main()）
# ========================================


def test_asr_worker_writes_result_and_progress(tmp_path, monkeypatch, capsys):
    from backend.workers import asr_worker

    def fake_transcribe(audio_path, progress_callback=None, **_kwargs):
        if progress_callback:
            progress_callback(30.0, "轉錄中...")
        return DetailedTranscriptionResult(
            text="逐字稿內容",
            duration_seconds=12.5,
            language="zh",
            chunks=[TranscriptionChunk(start=0.0, end=1.0, text="逐字稿內容")],
            backend="transformers",
        )

    import backend.services.transcription as transcription_module

    monkeypatch.setattr(
        transcription_module.transcription_service, "transcribe_detailed", fake_transcribe
    )

    result_path = tmp_path / "result.json"
    exit_code = asr_worker.main(["fake.mp3", str(result_path)])

    assert exit_code == 0
    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["text"] == "逐字稿內容"
    assert payload["duration_seconds"] == 12.5
    assert payload["chunks"][0]["text"] == "逐字稿內容"

    stdout_lines = [line for line in capsys.readouterr().out.splitlines() if line.strip()]
    progress_lines = [json.loads(line) for line in stdout_lines if line.startswith("{")]
    assert any(p.get("message") == "轉錄中..." for p in progress_lines)


def test_asr_worker_exits_nonzero_on_failure(tmp_path, monkeypatch, capsys):
    from backend.workers import asr_worker

    import backend.services.transcription as transcription_module

    monkeypatch.setattr(
        transcription_module.transcription_service,
        "transcribe_detailed",
        Mock(side_effect=RuntimeError("轉錄爆炸")),
    )

    exit_code = asr_worker.main(["fake.mp3", str(tmp_path / "result.json")])

    assert exit_code == 1
    assert "轉錄爆炸" in capsys.readouterr().err


def test_asr_worker_rejects_bad_argv(capsys):
    from backend.workers import asr_worker

    assert asr_worker.main(["only-one-arg"]) == 2


# ========================================
# 父程序端（fake subprocess）
# ========================================


class _FakeStream:
    def __init__(self, chunks: list[bytes]):
        self._chunks = list(chunks)

    async def readline(self) -> bytes:
        return self._chunks.pop(0) if self._chunks else b""

    async def read(self) -> bytes:
        data = b"".join(self._chunks)
        self._chunks = []
        return data


class _FakeProc:
    def __init__(self, stdout_lines: list[bytes], stderr_bytes: bytes = b"", returncode: int = 0):
        self.stdout = _FakeStream(stdout_lines)
        self.stderr = _FakeStream([stderr_bytes] if stderr_bytes else [])
        self._returncode = returncode
        self.pid = 4321
        self.killed = False

    async def wait(self) -> int:
        return self._returncode

    def kill(self) -> None:
        self.killed = True


def _spawn_factory(proc: _FakeProc, result_payload: dict = None):
    async def fake_spawn(*args, **_kwargs):
        if result_payload is not None:
            result_path = args[-1]
            with open(result_path, "w", encoding="utf-8") as f:
                json.dump(result_payload, f, ensure_ascii=False)
        return proc

    return fake_spawn


@pytest.mark.asyncio
async def test_transcribe_isolated_forwards_progress_and_returns_result(monkeypatch):
    monkeypatch.setattr(settings, "ASR_ISOLATION", "subprocess")

    progress_line = json.dumps({"progress": 42.0, "message": "轉錄中"}).encode("utf-8") + b"\n"
    noise_line = "loguru 雜訊行（非 JSON）\n".encode("utf-8")
    proc = _FakeProc([noise_line, progress_line])

    payload = {"text": "子程序逐字稿", "duration_seconds": 66.0, "backend": "transformers"}
    monkeypatch.setattr(asyncio, "create_subprocess_exec", _spawn_factory(proc, payload))

    received: list[tuple[float, str]] = []

    async def progress_cb(progress: float, message: str):
        received.append((progress, message))

    text, duration = await asr_subprocess.transcribe_isolated("fake.mp3", progress_cb)

    assert text == "子程序逐字稿"
    assert duration == 66.0
    assert (42.0, "轉錄中") in received


@pytest.mark.asyncio
async def test_transcribe_isolated_detailed_preserves_worker_metadata(monkeypatch):
    monkeypatch.setattr(settings, "ASR_ISOLATION", "subprocess")

    proc = _FakeProc([])
    payload = {
        "text": "子程序逐字稿",
        "duration_seconds": 66.0,
        "language": "zh",
        "backend": "mlx_whisper",
        "chunks": [{"start": 0.0, "end": 2.5, "text": "子程序逐字稿"}],
    }
    monkeypatch.setattr(asyncio, "create_subprocess_exec", _spawn_factory(proc, payload))

    result = await asr_subprocess.transcribe_isolated_detailed("fake.mp3")

    assert isinstance(result, DetailedTranscriptionResult)
    assert result.text == "子程序逐字稿"
    assert result.duration_seconds == 66.0
    assert result.language == "zh"
    assert result.backend == "mlx_whisper"
    assert result.chunks[0].end == 2.5


@pytest.mark.asyncio
async def test_transcribe_isolated_raises_with_stderr_on_failure(monkeypatch):
    monkeypatch.setattr(settings, "ASR_ISOLATION", "subprocess")

    proc = _FakeProc([], stderr_bytes="RuntimeError: 轉錄失敗原因".encode("utf-8"), returncode=1)
    monkeypatch.setattr(asyncio, "create_subprocess_exec", _spawn_factory(proc, None))

    with pytest.raises(RuntimeError) as excinfo:
        await asr_subprocess.transcribe_isolated("fake.mp3", None)

    assert "轉錄失敗原因" in str(excinfo.value)


@pytest.mark.asyncio
async def test_transcribe_isolated_falls_back_on_spawn_failure(monkeypatch):
    """spawn 失敗（環境問題）→ 本任務退回 in-process，任務不中斷。"""
    monkeypatch.setattr(settings, "ASR_ISOLATION", "subprocess")

    async def failing_spawn(*_args, **_kwargs):
        raise OSError("spawn blocked")

    monkeypatch.setattr(asyncio, "create_subprocess_exec", failing_spawn)
    monkeypatch.setattr(
        asr_subprocess, "_transcribe_inprocess", AsyncMock(return_value=("退回結果", 3.0))
    )

    text, duration = await asr_subprocess.transcribe_isolated("fake.mp3", None)

    assert text == "退回結果"
    assert duration == 3.0


@pytest.mark.asyncio
async def test_transcribe_isolated_respects_inprocess_mode(monkeypatch):
    monkeypatch.setattr(settings, "ASR_ISOLATION", "inprocess")
    inprocess = AsyncMock(return_value=("舊路徑", 1.0))
    monkeypatch.setattr(asr_subprocess, "_transcribe_inprocess", inprocess)

    text, _ = await asr_subprocess.transcribe_isolated("fake.mp3", None)

    assert text == "舊路徑"
    inprocess.assert_awaited_once()


# ========================================
# WAVE-05a：Apple 引擎 metadata 觀測（隔離子程序）
# ========================================


def _capture_loguru_messages() -> tuple[list[str], int]:
    """掛一個暫時 sink 收集 loguru 訊息（回傳 messages 與 sink id）。"""
    from loguru import logger as loguru_logger

    messages: list[str] = []

    def _sink(message) -> None:
        messages.append(message.record["message"])

    return messages, loguru_logger.add(_sink, level="INFO")


def _detach_loguru_sink(sink_id: int) -> None:
    from loguru import logger as loguru_logger

    loguru_logger.remove(sink_id)


def test_asr_worker_payload_carries_only_json_scalar_metadata(tmp_path, monkeypatch):
    """worker payload 必含 metadata；非純量值安全丟棄（BE-03 best-effort）。"""
    from backend.workers import asr_worker

    import backend.services.transcription as transcription_module

    def fake_transcribe(audio_path, progress_callback=None, **_kwargs):
        return DetailedTranscriptionResult(
            text="apple 逐字稿",
            duration_seconds=9.0,
            language="zh",
            backend="apple",
            metadata={
                "requested_engine": "apple",
                "resolved_engine": "apple_helper",
                "helper_invocations": 3,
                "real_time_factor": 0.75,
                "segments_dropped": None,
                "conversion_seconds": 1.5,
                "conversion_reason": True,
                "engine_chain": ["apple"],  # list → 丟棄（Mac 鏈恆為單段）
                "helper_debug": {"exit_code": 0},  # dict → 丟棄
            },
        )

    monkeypatch.setattr(
        transcription_module.transcription_service, "transcribe_detailed", fake_transcribe
    )

    result_path = tmp_path / "result.json"
    assert asr_worker.main(["fake.mp3", str(result_path)]) == 0

    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["metadata"] == {
        "requested_engine": "apple",
        "resolved_engine": "apple_helper",
        "helper_invocations": 3,
        "real_time_factor": 0.75,
        "segments_dropped": None,
        "conversion_seconds": 1.5,
        "conversion_reason": True,
    }
    assert payload["text"] == "apple 逐字稿"


def test_asr_worker_metadata_defaults_empty_for_legacy_result(tmp_path, monkeypatch):
    """舊物件沒有 metadata 屬性 → getattr 降級為 {}，不影響舊後端 payload。"""
    from types import SimpleNamespace

    from backend.workers import asr_worker

    import backend.services.transcription as transcription_module

    def fake_transcribe(audio_path, progress_callback=None, **_kwargs):
        return SimpleNamespace(
            text="舊後端逐字稿",
            duration_seconds=5.0,
            language="zh",
            backend="transformers",
            chunks=[],
        )

    monkeypatch.setattr(
        transcription_module.transcription_service, "transcribe_detailed", fake_transcribe
    )

    result_path = tmp_path / "result.json"
    assert asr_worker.main(["fake.mp3", str(result_path)]) == 0

    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload["metadata"] == {}
    assert payload["backend"] == "transformers"


def test_payload_to_detailed_restores_metadata():
    payload = {
        "text": "apple 逐字稿",
        "duration_seconds": 30.0,
        "language": "zh",
        "backend": "apple",
        "chunks": [{"start": 0.0, "end": 1.0, "text": "apple 逐字稿"}],
        "metadata": {"requested_engine": "apple", "helper_invocations": 2},
    }

    result = asr_subprocess._payload_to_detailed(payload)

    assert result.metadata == {"requested_engine": "apple", "helper_invocations": 2}


def test_payload_to_detailed_defaults_missing_metadata_to_empty_dict():
    payload = {"text": "舊後端逐字稿", "duration_seconds": 3.0, "backend": "transformers"}

    result = asr_subprocess._payload_to_detailed(payload)

    assert result.metadata == {}


def test_payload_to_detailed_rejects_non_dict_metadata():
    payload = {"text": "x", "duration_seconds": 1.0, "backend": "apple", "metadata": ["a", "b"]}

    assert asr_subprocess._payload_to_detailed(payload).metadata == {}


@pytest.mark.asyncio
async def test_transcribe_isolated_logs_engine_metadata_when_present(monkeypatch):
    monkeypatch.setattr(settings, "ASR_ISOLATION", "subprocess")

    proc = _FakeProc([])
    payload = {
        "text": "apple 逐字稿",
        "duration_seconds": 12.0,
        "language": "zh",
        "backend": "apple",
        "metadata": {"resolved_engine": "apple_helper", "helper_invocations": 1},
    }
    monkeypatch.setattr(asyncio, "create_subprocess_exec", _spawn_factory(proc, payload))

    messages, sink_id = _capture_loguru_messages()
    try:
        result = await asr_subprocess.transcribe_isolated_detailed("fake.mp3")
    finally:
        _detach_loguru_sink(sink_id)

    assert result.metadata == {"resolved_engine": "apple_helper", "helper_invocations": 1}
    engine_logs = [message for message in messages if "ASR 引擎觀測" in message]
    assert len(engine_logs) == 1
    assert '"helper_invocations": 1' in engine_logs[0]
    assert '"resolved_engine": "apple_helper"' in engine_logs[0]


@pytest.mark.asyncio
async def test_transcribe_isolated_skips_metadata_log_when_empty(monkeypatch):
    """舊後端 metadata 空 dict → 不輸出引擎觀測日誌列（既有日誌行不受影響）。"""
    monkeypatch.setattr(settings, "ASR_ISOLATION", "subprocess")

    proc = _FakeProc([])
    payload = {
        "text": "舊後端逐字稿",
        "duration_seconds": 4.0,
        "backend": "mlx_whisper",
        "metadata": {},
    }
    monkeypatch.setattr(asyncio, "create_subprocess_exec", _spawn_factory(proc, payload))

    messages, sink_id = _capture_loguru_messages()
    try:
        result = await asr_subprocess.transcribe_isolated_detailed("fake.mp3")
    finally:
        _detach_loguru_sink(sink_id)

    assert result.metadata == {}
    assert any("ASR 子程序完成" in message for message in messages)
    assert not [message for message in messages if "ASR 引擎觀測" in message]
