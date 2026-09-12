"""ASR 子程序執行器（v4.7.0）。

根因背景：ASR 在長駐程序內反覆 CUDA load/unload 會累積 context／分配器殘留
（唯一保證完全釋回 VRAM 的方式是程序退出），蠶食 Ollama 可用 VRAM，
最終使 20GB 模型載入時被 offload 到 CPU、推理崩跌逾時。

本模組把每次轉錄放進獨立子程序（backend/workers/asr_worker.py）：
- 進度：worker stdout 的 JSON lines → 逐行轉發 async progress callback
- 結果：worker 寫入暫存 JSON 檔，父程序讀回
- 失敗：非零 exit code ＋ stderr 內容組成錯誤訊息
- 回退：ASR_ISOLATION=inprocess 或 spawn 失敗時走舊的 executor 路徑
"""

import asyncio
import json
import os
import sys
import tempfile
from typing import Awaitable, Callable, Optional, Tuple

from backend.core.config import settings
from backend.core.errors import describe_exception
from backend.core.logger import log

AsyncProgressCallback = Callable[[float, str], Awaitable[None]]


async def _transcribe_inprocess(
    file_path: str,
    progress_callback: Optional[AsyncProgressCallback],
) -> Tuple[str, float]:
    """舊行為（v4.6.x）：thread executor 內同步轉錄，callback 跨執行緒橋接。"""
    result = await _transcribe_inprocess_detailed(file_path, progress_callback)
    return result.text, result.duration_seconds


async def _transcribe_inprocess_detailed(
    file_path: str,
    progress_callback: Optional[AsyncProgressCallback],
):
    """在 in-process fallback 也保留完整的 normalized ASR result。"""
    from backend.services.transcription import transcription_service

    loop = asyncio.get_event_loop()

    def sync_progress_cb(progress: float, message: str) -> None:
        if progress_callback:
            asyncio.run_coroutine_threadsafe(progress_callback(progress, message), loop)

    return await loop.run_in_executor(
        None,
        lambda: transcription_service.transcribe_detailed(file_path, sync_progress_cb),
    )


async def _pump_progress_lines(
    stream: asyncio.StreamReader,
    progress_callback: Optional[AsyncProgressCallback],
) -> None:
    """逐行讀 worker stdout；JSON 行轉發進度，其他行（雜訊）記 debug。"""
    while True:
        line = await stream.readline()
        if not line:
            break
        text = line.decode("utf-8", errors="replace").strip()
        if not text:
            continue
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            log.debug("ASR worker stdout（非進度行）: {}", text[:200])
            continue
        if progress_callback:
            try:
                await progress_callback(
                    float(data.get("progress", 0.0)), str(data.get("message", ""))
                )
            except Exception as exc:  # noqa: BLE001 — 進度回報失敗不可中斷轉錄
                log.debug("轉發 ASR 進度失敗（忽略）: {}", describe_exception(exc))


async def _read_stream_text(stream: asyncio.StreamReader) -> str:
    data = await stream.read()
    return data.decode("utf-8", errors="replace")


def _payload_to_detailed(payload: dict):
    """把 worker JSON 還原成與 in-process 相同的 DetailedTranscriptionResult。"""
    from backend.services.transcription import DetailedTranscriptionResult, TranscriptionChunk

    if not isinstance(payload, dict) or "text" not in payload:
        raise RuntimeError("ASR worker 結果缺少 text")

    raw_chunks = payload.get("chunks") or []
    chunks = []
    if isinstance(raw_chunks, list):
        for raw_chunk in raw_chunks:
            if not isinstance(raw_chunk, dict):
                continue
            chunks.append(
                TranscriptionChunk(
                    start=float(raw_chunk.get("start") or 0.0),
                    end=float(raw_chunk.get("end") or 0.0),
                    text=str(raw_chunk.get("text") or "").strip(),
                )
            )
    chunks = [chunk for chunk in chunks if chunk.text]
    raw_metadata = payload.get("metadata")
    metadata = raw_metadata if isinstance(raw_metadata, dict) else {}
    return DetailedTranscriptionResult(
        text=str(payload.get("text") or ""),
        duration_seconds=float(payload.get("duration_seconds") or 0.0),
        language=str(payload.get("language") or "auto"),
        chunks=chunks,
        backend=str(payload.get("backend") or "unknown"),
        metadata=metadata,
    )


async def _transcribe_isolated_raw(
    file_path: str,
    progress_callback: Optional[AsyncProgressCallback] = None,
    *,
    detailed_fallback: bool = False,
):
    """執行隔離轉錄；依 caller 需求保留 tuple 或完整 result。"""
    inprocess = _transcribe_inprocess_detailed if detailed_fallback else _transcribe_inprocess
    if (settings.ASR_ISOLATION or "").lower() != "subprocess":
        return await inprocess(file_path, progress_callback)

    fd, result_path = tempfile.mkstemp(prefix="asr_result_", suffix=".json")
    os.close(fd)
    try:
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "backend.workers.asr_worker",
                file_path,
                result_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
        except OSError as exc:
            # spawn 本身失敗（環境問題）→ 本任務退回 in-process，不放棄任務
            log.warning(
                f"ASR 子程序啟動失敗（{describe_exception(exc)}），本任務退回 in-process 模式"
            )
            return await inprocess(file_path, progress_callback)

        log.info(f"ASR 子程序已啟動（pid={proc.pid}，隔離模式保證 VRAM 歸還）")

        try:
            # stdout/stderr 必須同時讀，否則子程序寫滿 pipe buffer 會互相卡死
            _, stderr_text = await asyncio.wait_for(
                asyncio.gather(
                    _pump_progress_lines(proc.stdout, progress_callback),
                    _read_stream_text(proc.stderr),
                ),
                timeout=settings.ASR_WORKER_TIMEOUT_SECONDS,
            )
            returncode = await proc.wait()
        except (asyncio.TimeoutError, TimeoutError):
            proc.kill()
            await proc.wait()
            # 逾時＝病態輸入（超長/損壞音檔），重跑 in-process 只會再耗一輪，直接失敗
            raise RuntimeError(
                f"ASR 子程序逾時（超過 {settings.ASR_WORKER_TIMEOUT_SECONDS:.0f} 秒），已強制終止"
            )

        if returncode != 0:
            tail = stderr_text.strip()[-2000:]
            raise RuntimeError(f"ASR 子程序失敗（exit={returncode}）：{tail or '無錯誤輸出'}")

        if stderr_text.strip():
            log.debug("ASR worker stderr:\n{}", stderr_text.strip()[-2000:])

        with open(result_path, encoding="utf-8") as f:
            payload = json.load(f)

        log.info(
            f"ASR 子程序完成：backend={payload.get('backend')}, "
            f"音檔時長={float(payload.get('duration_seconds') or 0.0):.1f}s"
        )
        metadata = payload.get("metadata")
        if isinstance(metadata, dict) and metadata:
            log.info("ASR 引擎觀測：{}", json.dumps(metadata, ensure_ascii=False, sort_keys=True))
        if detailed_fallback:
            return _payload_to_detailed(payload)
        return payload["text"], float(payload.get("duration_seconds") or 0.0)
    finally:
        try:
            os.remove(result_path)
        except OSError:
            pass


async def transcribe_isolated(
    file_path: str,
    progress_callback: Optional[AsyncProgressCallback] = None,
) -> Tuple[str, float]:
    """相容舊 caller 的 tuple 介面。"""
    return await _transcribe_isolated_raw(file_path, progress_callback)


async def transcribe_isolated_detailed(
    file_path: str,
    progress_callback: Optional[AsyncProgressCallback] = None,
):
    """執行隔離轉錄並回傳統一 DetailedTranscriptionResult。"""
    result = await _transcribe_isolated_raw(
        file_path,
        progress_callback,
        detailed_fallback=True,
    )
    from backend.services.transcription import DetailedTranscriptionResult

    if isinstance(result, DetailedTranscriptionResult):
        return result
    if isinstance(result, (tuple, list)) and len(result) >= 2:
        return DetailedTranscriptionResult(
            text=str(result[0]),
            duration_seconds=float(result[1]),
            language="auto",
            backend="unknown",
        )
    raise RuntimeError("ASR isolated result 格式無法解析")
