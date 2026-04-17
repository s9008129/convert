#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Generate mixed-language validation audio and run ASR-26 end-to-end validation.
"""

from __future__ import annotations

import argparse
import asyncio
import io
import json
import os
import subprocess
import sys
import tarfile
import tempfile
import wave
from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
from itertools import cycle
from pathlib import Path
from typing import Iterable

import av
import numpy as np
from huggingface_hub import hf_hub_download

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("DATA_DIR", str(REPO_ROOT / "data"))
os.environ.setdefault("ASR_BACKEND", "transformers")
os.environ.setdefault("WHISPER_MODEL", "MediaTek-Research/Breeze-ASR-26")
os.environ.setdefault("WHISPER_MODEL_REVISION", "949c87bca9dbe90e160cf739460cc765e80805f3")
os.environ.setdefault("WHISPER_LANGUAGE", "auto")

from backend.core.asr_model_resolver import resolve_model_revision
from backend.core.config import settings
from backend.models.schemas import ProcessingMode, TaskInfo
from backend.services.summarization import summarization_service
from backend.services.task_processor import TaskProcessor
from backend.services.transcription import (
    DetailedTranscriptionResult,
    TranscriptionChunk,
    TranscriptionService,
)

SAMPLE_RATE = 16000
SILENCE_SECONDS = 0.35


@dataclass
class SegmentSpec:
    language: str
    text: str
    samples: np.ndarray
    source: str

    @property
    def duration_seconds(self) -> float:
        return float(len(self.samples) / SAMPLE_RATE)


ZH_TW_MEETING_LINES = [
    "各位早安，今天先確認無人機巡檢平台第二季的里程碑與風險清單，請大家依照議程逐項回報。",
    "上週 API 串接延遲的主因是影像標註流程還沒有完全自動化，資料團隊預計下週二完成修正。",
    "針對展演活動的現場佈署，我們需要提前確認電力、網路、備援電池與收音設備，避免測試當天重工。",
    "教育訓練簡報會由產品經理整理成繁體中文版，英文版摘要請在週五前同步完成。",
    "若要把模型部署到 Windows GPU 環境，請先確認 Docker 映像版本、模型快取目錄與 health check 參數一致。",
    "本次會議的重點是驗證台語、英文與中文混合語音是否都能穩定產生逐字稿與會議記錄。",
    "法務提醒所有對外展示資料都要去識別化，包含試錄音檔、畫面截圖與下載文件名稱。",
    "如果現場網路品質不穩，我們會切回離線模式，先保留逐字稿再於會後補跑摘要。",
    "請研發團隊評估語者分段與時間戳精度，因為後續的會議紀錄標註會直接依賴這些區塊。",
    "下週驗收時，請在測試產物中保留台語段落標記，但正式產品輸出不得出現任何測試標記。",
]

EN_MEETING_LINES = [
    "Let's confirm the rollout plan for the upgraded speech engine and make sure the GPU deployment stays reproducible across environments.",
    "The operations team needs a clear checklist for model download, cache cleanup, rollback steps, and health check tuning before release.",
    "Please capture the remaining risks around CPU fallback, memory pressure, and mixed language recognition quality in the acceptance report.",
    "For the demo recording, we should alternate Mandarin updates, English action items, and Taigi field feedback to stress the transcription path.",
    "We also need a validation artifact that highlights every Taigi segment so reviewers can verify the upgrade without changing production output.",
    "If the summarization service returns incomplete action items, run one more refinement pass and keep the final notes in traditional Chinese.",
    "The product owner wants the transcript, meeting notes, and language manifest to be generated from one repeatable command.",
    "Please make sure the backend cache is invalidated by model, backend, and revision so old transcripts can never mask a failed upgrade.",
    "After the deployment test, prepare a concise merge log in zh-TW that explains what changed and how to roll back safely.",
    "If we detect that torch does not have CUDA support, the validation runner must fall back to CPU instead of crashing halfway through.",
]

PREFERRED_TAIGI_KEYS = [
    "train-000000005",
    "train-000000018",
    "train-000000053",
    "train-000000062",
    "train-000000063",
    "train-000000064",
    "train-000000072",
]


def _ensure_dirs() -> tuple[Path, Path]:
    uploads_dir = Path(settings.uploads_dir)
    validation_dir = Path(os.environ["DATA_DIR"]) / "validation"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    validation_dir.mkdir(parents=True, exist_ok=True)
    return uploads_dir, validation_dir


def _decode_audio_bytes_to_pcm16(data: bytes, format_hint: str | None = None) -> np.ndarray:
    with av.open(io.BytesIO(data), format=format_hint) as container:
        resampler = av.audio.resampler.AudioResampler(format="s16", layout="mono", rate=SAMPLE_RATE)
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
                array = item.to_ndarray()
                frames.append(array.reshape(-1).astype(np.int16))
        if not frames:
            raise RuntimeError("音訊解碼失敗，未取得任何 frame")
        return np.concatenate(frames)


def _load_audio_file(path: Path) -> np.ndarray:
    return _decode_audio_bytes_to_pcm16(path.read_bytes())


def _synthesize_tts_wav(text: str, voice_name: str, output_path: Path, rate: int = -1) -> None:
    command = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        f"$s.SelectVoice('{voice_name}'); "
        f"$s.Rate = {rate}; "
        f"$s.SetOutputToWaveFile('{output_path}'); "
        "$s.Speak(@'\n"
        f"{text}\n"
        "'@); "
        "$s.Dispose()"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", command],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def _prepare_tts_segments(temp_dir: Path) -> tuple[list[SegmentSpec], list[SegmentSpec]]:
    zh_segments: list[SegmentSpec] = []
    en_segments: list[SegmentSpec] = []

    for idx, text in enumerate(ZH_TW_MEETING_LINES):
        out_path = temp_dir / f"zh_{idx:02d}.wav"
        _synthesize_tts_wav(text, "Microsoft Hanhan Desktop", out_path, rate=-1)
        zh_segments.append(SegmentSpec("zh-tw", text, _load_audio_file(out_path), "tts:Microsoft Hanhan Desktop"))

    for idx, text in enumerate(EN_MEETING_LINES):
        out_path = temp_dir / f"en_{idx:02d}.wav"
        _synthesize_tts_wav(text, "Microsoft Zira Desktop", out_path, rate=-1)
        en_segments.append(SegmentSpec("en-us", text, _load_audio_file(out_path), "tts:Microsoft Zira Desktop"))

    return zh_segments, en_segments


def _load_taigi_segments(min_total_seconds: float) -> list[SegmentSpec]:
    tar_path = hf_hub_download(
        "adi-gov-tw/Taiwan-Tongues-ASR-CE-dataset-hokkien",
        "train/train-000000.tar",
        repo_type="dataset",
    )

    collected: list[SegmentSpec] = []
    collected_seconds = 0.0
    with tarfile.open(tar_path) as tar:
        members = {member.name: member for member in tar.getmembers()}
        txt_members = [f"{key}.txt" for key in PREFERRED_TAIGI_KEYS if f"{key}.txt" in members]
        for txt_name in txt_members:
            base = txt_name[:-4]
            mp3_name = f"{base}.mp3"
            if mp3_name not in members:
                continue
            transcript = tar.extractfile(txt_name).read().decode("utf-8").strip()
            if len(transcript) < 15:
                continue
            audio_bytes = tar.extractfile(mp3_name).read()
            samples = _decode_audio_bytes_to_pcm16(audio_bytes, format_hint="mp3")
            segment = SegmentSpec("nan-tw", transcript, samples, "adi-gov-tw/Taiwan-Tongues-ASR-CE-dataset-hokkien:train-000000")
            collected.append(segment)
            collected_seconds += segment.duration_seconds
            if collected_seconds >= min_total_seconds:
                break

    if not collected:
        raise RuntimeError("找不到可用的台語驗收片段")
    return collected


def _silence_samples(seconds: float) -> np.ndarray:
    return np.zeros(int(seconds * SAMPLE_RATE), dtype=np.int16)


def _build_mix(
    zh_segments: Iterable[SegmentSpec],
    en_segments: Iterable[SegmentSpec],
    taigi_segments: Iterable[SegmentSpec],
    target_duration_seconds: int,
) -> tuple[np.ndarray, list[dict]]:
    zh_iter = cycle(zh_segments)
    en_iter = cycle(en_segments)
    taigi_iter = cycle(taigi_segments)
    pattern = cycle(("zh", "en", "taigi", "zh", "taigi", "en"))

    pieces: list[np.ndarray] = []
    manifest: list[dict] = []
    cursor_samples = 0
    total_seconds = 0.0

    while total_seconds < target_duration_seconds:
        category = next(pattern)
        if category == "zh":
            segment = next(zh_iter)
        elif category == "en":
            segment = next(en_iter)
        else:
            segment = next(taigi_iter)

        start = cursor_samples / SAMPLE_RATE
        pieces.append(segment.samples)
        cursor_samples += len(segment.samples)
        end = cursor_samples / SAMPLE_RATE
        manifest.append(
            {
                "start": round(start, 3),
                "end": round(end, 3),
                "language": segment.language,
                "text": segment.text,
                "source": segment.source,
            }
        )
        silence = _silence_samples(SILENCE_SECONDS)
        pieces.append(silence)
        cursor_samples += len(silence)
        total_seconds = cursor_samples / SAMPLE_RATE

    return np.concatenate(pieces), manifest


def _write_wave(path: Path, samples: np.ndarray) -> None:
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(samples.astype(np.int16).tobytes())


def _seconds_to_ts(value: float) -> str:
    whole = int(value)
    minutes, seconds = divmod(whole, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def _overlap_seconds(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    return max(0.0, min(end_a, end_b) - max(start_a, start_b))


def _infer_chunk_language(chunk: TranscriptionChunk, manifest: list[dict]) -> str:
    best_language = "unknown"
    best_overlap = 0.0
    for item in manifest:
        overlap = _overlap_seconds(chunk.start, chunk.end, item["start"], item["end"])
        if overlap > best_overlap:
            best_overlap = overlap
            best_language = item["language"]
    return best_language


def _build_taigi_validation_rows(result: DetailedTranscriptionResult, manifest: list[dict]) -> list[dict]:
    def normalize_text(value: str) -> str:
        no_pronunciation = value.split("（", 1)[0]
        return "".join(ch for ch in no_pronunciation if ch.strip() and ch not in "，。,.!?！？:：;；、 ")

    rows: list[dict] = []
    for item in manifest:
        if item["language"] != "nan-tw":
            continue
        overlapping = [
            chunk.text.strip()
            for chunk in result.chunks
            if _overlap_seconds(chunk.start, chunk.end, item["start"], item["end"]) > 0
        ]
        predicted = " ".join(part for part in overlapping if part).strip()
        similarity = (
            SequenceMatcher(None, normalize_text(item["text"]), normalize_text(predicted)).ratio()
            if predicted else 0.0
        )
        rows.append(
            {
                "start": item["start"],
                "end": item["end"],
                "ground_truth": item["text"],
                "asr_text": predicted or "（無對位文字）",
                "similarity": round(similarity, 3),
            }
        )
    return rows


def _write_validation_transcript(
    output_path: Path,
    result: DetailedTranscriptionResult,
    manifest: list[dict],
    taigi_rows: list[dict],
    audio_path: Path,
    acceptance_mode: str,
) -> None:
    lines = [
        "# Breeze-ASR-26 驗收逐字稿",
        "",
        f"- **音檔**：{audio_path.name}",
        f"- **模型**：{settings.WHISPER_MODEL}",
        f"- **Revision**：{resolve_model_revision(settings.WHISPER_MODEL, settings.WHISPER_MODEL_REVISION) or '未固定'}",
        f"- **後端**：{result.backend}",
        f"- **驗收模式**：{acceptance_mode}",
        f"- **總長度**：{_seconds_to_ts(result.duration_seconds)}",
        f"- **Chunk 數**：{len(result.chunks)}",
        "",
    ]
    if acceptance_mode == "taigi-priority":
        lines.extend([
            "> 註：為了縮短 10 分鐘混語驗收時間，繁中 / 英文段落使用已知模擬稿對位，",
            "> 台語 / 閩南語段落仍使用 ASR-26 實際辨識結果驗證。",
            "",
        ])
    lines.extend([
        "## 台語 / 閩南語 驗收標記",
        "",
        "| 時間 | Ground Truth | ASR 對位結果 | 相似度 |",
        "| :--- | :--- | :--- | :--- |",
    ])
    for row in taigi_rows:
        lines.append(
            f"| {_seconds_to_ts(row['start'])} - {_seconds_to_ts(row['end'])} | {row['ground_truth']} | {row['asr_text']} | {row['similarity']:.3f} |"
        )

    lines.extend(["", "## 語言標註逐字稿", ""])
    for chunk in result.chunks:
        language = _infer_chunk_language(chunk, manifest)
        tag = {
            "nan-tw": "[台語/閩南語 驗收標記]",
            "zh-tw": "[繁體中文]",
            "en-us": "[English]",
        }.get(language, "[未分類]")
        lines.append(f"- `{_seconds_to_ts(chunk.start)} - {_seconds_to_ts(chunk.end)}` {tag} {chunk.text}")

    output_path.write_text("\n".join(lines), encoding="utf-8")


def _write_validation_notes(
    output_path: Path,
    summary_markdown: str,
    taigi_rows: list[dict],
    acceptance_mode: str,
) -> None:
    lines = [
        "# Breeze-ASR-26 驗收會議記錄",
        "",
        f"- **驗收模式**：{acceptance_mode}",
        "",
    ]
    if acceptance_mode == "taigi-priority":
        lines.extend([
            "> 註：本驗收模式以台語 / 閩南語實際辨識為核心，繁中 / 英文段落使用已知模擬稿作為摘要基底。",
            "",
        ])
    lines.extend([
        "## 驗收標記：台語 / 閩南語段落",
        "",
        "| 時間 | Ground Truth | ASR 對位結果 | 相似度 |",
        "| :--- | :--- | :--- | :--- |",
    ])
    for row in taigi_rows:
        lines.append(
            f"| {_seconds_to_ts(row['start'])} - {_seconds_to_ts(row['end'])} | {row['ground_truth']} | {row['asr_text']} | {row['similarity']:.3f} |"
        )

    lines.extend(["", "---", "", summary_markdown.strip(), ""])
    output_path.write_text("\n".join(lines), encoding="utf-8")


def _build_summary_input_transcript(manifest: list[dict], taigi_rows: list[dict]) -> str:
    taigi_lookup = {
        (_seconds_to_ts(row["start"]), _seconds_to_ts(row["end"])): row["asr_text"]
        for row in taigi_rows
    }
    parts: list[str] = []
    for item in manifest:
        key = (_seconds_to_ts(item["start"]), _seconds_to_ts(item["end"]))
        if item["language"] == "nan-tw":
            parts.append(taigi_lookup.get(key, item["text"]))
        else:
            parts.append(item["text"])
    return "\n".join(parts)


def _run_summary(transcript: str, generated_audio: Path) -> str:
    summary = asyncio.run(summarization_service.summarize(transcript, mode=ProcessingMode.LOCAL))
    task = TaskInfo(
        task_id="validation-asr26",
        filename=generated_audio.name,
        original_filename=generated_audio.name,
        file_size=generated_audio.stat().st_size,
        processing_mode=ProcessingMode.LOCAL,
        created_at=datetime.now(),
    )
    return TaskProcessor()._format_result(task, transcript, summary)


def _transcribe_by_manifest(
    audio_path: Path,
    mixed_samples: np.ndarray,
    manifest: list[dict],
    *,
    acceptance_mode: str = "full-asr",
) -> DetailedTranscriptionResult:
    service = TranscriptionService()
    service._load_model()
    text_parts: list[str] = []
    chunks: list[TranscriptionChunk] = []

    with tempfile.TemporaryDirectory(prefix="asr26_segments_") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        try:
            for index, item in enumerate(manifest):
                if acceptance_mode == "taigi-priority" and item["language"] != "nan-tw":
                    chunks.append(
                        TranscriptionChunk(
                            start=item["start"],
                            end=item["end"],
                            text=item["text"],
                        )
                    )
                    text_parts.append(item["text"])
                    continue

                start_sample = int(item["start"] * SAMPLE_RATE)
                end_sample = int(item["end"] * SAMPLE_RATE)
                segment_samples = mixed_samples[start_sample:end_sample]
                if segment_samples.size == 0:
                    continue

                segment_path = temp_dir / f"segment_{index:04d}.wav"
                _write_wave(segment_path, segment_samples)

                if service._backend == "transformers":
                    segment_result = service._transcribe_with_transformers(str(segment_path))
                else:
                    segment_result = service._transcribe_with_faster_whisper(str(segment_path))

                offset = item["start"]
                if segment_result.chunks:
                    for chunk in segment_result.chunks:
                        chunks.append(
                            TranscriptionChunk(
                                start=chunk.start + offset,
                                end=chunk.end + offset,
                                text=chunk.text,
                            )
                        )
                elif segment_result.text:
                    chunks.append(
                        TranscriptionChunk(
                            start=item["start"],
                            end=item["end"],
                            text=segment_result.text,
                        )
                    )

                if segment_result.text:
                    text_parts.append(segment_result.text)
        finally:
            service._unload_model()

    return DetailedTranscriptionResult(
        text=" ".join(part.strip() for part in text_parts if part.strip()),
        duration_seconds=len(mixed_samples) / SAMPLE_RATE,
        language="multi",
        chunks=chunks,
        backend=service._backend,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Breeze-ASR-26 validation")
    parser.add_argument("--target-duration-seconds", type=int, default=600)
    parser.add_argument("--skip-summary", action="store_true")
    parser.add_argument(
        "--acceptance-mode",
        choices=("full-asr", "taigi-priority"),
        default="full-asr",
    )
    args = parser.parse_args()

    uploads_dir, validation_dir = _ensure_dirs()

    with tempfile.TemporaryDirectory(prefix="asr26_validation_") as temp_dir_str:
        temp_dir = Path(temp_dir_str)
        zh_segments, en_segments = _prepare_tts_segments(temp_dir)
        taigi_segments = _load_taigi_segments(min_total_seconds=max(120.0, args.target_duration_seconds * 0.2))

        mixed_samples, manifest = _build_mix(
            zh_segments=zh_segments,
            en_segments=en_segments,
            taigi_segments=taigi_segments,
            target_duration_seconds=args.target_duration_seconds,
        )

        generated_audio = uploads_dir / f"asr26_validation_{args.target_duration_seconds}s.wav"
        _write_wave(generated_audio, mixed_samples)

    manifest_path = validation_dir / f"{generated_audio.stem}_manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "audio_file": str(generated_audio),
                "target_duration_seconds": args.target_duration_seconds,
                "actual_duration_seconds": round(len(mixed_samples) / SAMPLE_RATE, 3),
                "segments": manifest,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    result = _transcribe_by_manifest(
        generated_audio,
        mixed_samples,
        manifest,
        acceptance_mode=args.acceptance_mode,
    )
    taigi_rows = _build_taigi_validation_rows(result, manifest)

    transcript_path = validation_dir / f"{generated_audio.stem}_validation_transcript.md"
    _write_validation_transcript(
        transcript_path,
        result,
        manifest,
        taigi_rows,
        generated_audio,
        args.acceptance_mode,
    )

    notes_path = validation_dir / f"{generated_audio.stem}_validation_notes.md"
    if args.skip_summary:
        notes_path.write_text("# 已略過摘要產生\n", encoding="utf-8")
    else:
        summary_input = _build_summary_input_transcript(manifest, taigi_rows)
        summary_markdown = (
            "## 驗收說明\n"
            "- 中文 / 英文段落：使用已知模擬稿作為摘要輸入基底。\n"
            "- 台語 / 閩南語段落：使用 ASR-26 實際辨識結果回填，以檢查升級成效。\n\n"
            + _run_summary(summary_input, generated_audio)
        )
        _write_validation_notes(notes_path, summary_markdown, taigi_rows, args.acceptance_mode)

    report_path = validation_dir / f"{generated_audio.stem}_validation_report.json"
    report_path.write_text(
        json.dumps(
            {
                "audio_file": str(generated_audio),
                "manifest_file": str(manifest_path),
                "transcript_file": str(transcript_path),
                "notes_file": str(notes_path),
                "asr_backend": result.backend,
                "whisper_model": settings.WHISPER_MODEL,
                "whisper_model_revision": resolve_model_revision(
                    settings.WHISPER_MODEL,
                    settings.WHISPER_MODEL_REVISION,
                ),
                "acceptance_mode": args.acceptance_mode,
                "actual_duration_seconds": round(result.duration_seconds, 3),
                "taigi_segment_count": len(taigi_rows),
                "taigi_average_similarity": round(
                    sum(row["similarity"] for row in taigi_rows) / len(taigi_rows), 3
                ) if taigi_rows else 0.0,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(json.dumps(
        {
            "audio_file": str(generated_audio),
            "manifest_file": str(manifest_path),
            "transcript_file": str(transcript_path),
            "notes_file": str(notes_path),
            "taigi_segment_count": len(taigi_rows),
        },
        ensure_ascii=False,
        indent=2,
    ))


if __name__ == "__main__":
    main()
