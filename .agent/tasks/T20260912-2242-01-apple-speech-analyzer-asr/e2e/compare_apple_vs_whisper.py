#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Apple SpeechAnalyzer vs Whisper(MLX) 逐字稿品質/速度對照（Owner 指定實測）。

用同一個產品服務層（`transcription_service.transcribe_detailed`）跑兩個引擎，
只換 `ASR_BACKEND`，因此差異純粹來自引擎（含各自的 VAD/分段策略）：

- apple      ：`ASR_BACKEND=apple`（顯式、fail-closed；helper 子程序 + SpeechAnalyzer）
- mlx_whisper：`ASR_BACKEND=mlx_whisper`（Whisper 模型 `settings.WHISPER_MODEL`，MLX/Metal）

每個引擎在**獨立子程序**執行（乾淨的 import 狀態與計時），逐字稿原文只落在
gitignored runtime dir；報告只放指標與短摘錄。

用法：
    uv run python .../compare_apple_vs_whisper.py \
        --audio "tests/0903-科務會議.m4a" \
        --runtime-dir data/cache/apple-vs-whisper-0903 \
        --report .agent/tasks/T20260912-2242-01-apple-speech-analyzer-asr/e2e/comparison-0903
"""

import argparse
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
ENGINES = ("apple", "mlx_whisper")

CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff]")
PUNCT_RE = re.compile(r"[，。！？；：、,.!?;:]")
SPACE_RE = re.compile(r"\s+")


# ---------------------------------------------------------------------------
# child：單一引擎轉錄
# ---------------------------------------------------------------------------
def run_engine_child(engine: str, audio: str, out_path: str, data_dir: str, model: str = "") -> int:
    os.environ["DATA_DIR"] = data_dir
    os.environ["ASR_BACKEND"] = engine
    if model:
        os.environ["WHISPER_MODEL"] = model
        os.environ["WHISPER_MODEL_REVISION"] = ""
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    sys.path.insert(0, str(REPO_ROOT))

    from backend.services.transcription import transcription_service  # noqa: E402

    progress_marks = []

    def progress_callback(progress: float, message: str) -> None:
        progress_marks.append([round(float(progress), 1), str(message)[:80]])

    started = time.time()
    result = transcription_service.transcribe_detailed(audio, progress_callback)
    elapsed = time.time() - started

    payload = {
        "engine": engine,
        "backend": getattr(result, "backend", "unknown"),
        "language": getattr(result, "language", "auto"),
        "duration_seconds": float(getattr(result, "duration_seconds", 0.0) or 0.0),
        "elapsed_seconds": elapsed,
        "real_time_factor": (elapsed / float(getattr(result, "duration_seconds", 0.0) or 1.0)),
        "text": result.text,
        "text_chars": len(result.text or ""),
        "chunk_count": len(result.chunks or []),
        "metadata": dict(getattr(result, "metadata", {}) or {}),
        "whisper_model": model or None,
        "progress_marks": progress_marks[-12:],
    }
    Path(out_path).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"[child] {engine} 完成：{elapsed:.1f}s / {payload['text_chars']} 字 / {payload['chunk_count']} chunks")
    return 0


# ---------------------------------------------------------------------------
# parent：指標與比較
# ---------------------------------------------------------------------------
def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_for_compare(text: str) -> str:
    return SPACE_RE.sub("", PUNCT_RE.sub("", text or ""))


def repeat_ngram_ratio(text: str, n: int = 8) -> dict:
    """重複 n-gram 比例：值越高代表越多重複/迴圈式輸出。"""

    chars = normalize_for_compare(text)
    if len(chars) < n:
        return {"top": [], "repeated_ratio": 0.0}
    grams = [chars[i : i + n] for i in range(len(chars) - n + 1)]
    counts = Counter(grams)
    repeated = sum(count - 1 for count in counts.values() if count > 1)
    top = [[gram, count] for gram, count in counts.most_common(5) if count > 1]
    return {"top": top, "repeated_ratio": repeated / len(grams)}


def text_stats(text: str) -> dict:
    text = text or ""
    cjk = len(CJK_RE.findall(text))
    digits = len(re.findall(r"[0-9０-９]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    punct = len(PUNCT_RE.findall(text))
    return {
        "chars": len(text),
        "cjk_chars": cjk,
        "punctuation_marks": punct,
        "punctuation_per_100_cjk": round(punct / cjk * 100, 2) if cjk else 0.0,
        "digit_chars": digits,
        "latin_chars": latin,
        "repeat_ngram8": repeat_ngram_ratio(text),
    }


def excerpt(text: str, positions) -> dict:
    out = {}
    for label, start, length in positions:
        out[label] = (text or "")[start : start + length]
    return out


def find_snippet(text: str, needle: str) -> str:
    index = (text or "").find(needle)
    if index < 0:
        return ""
    return (text or "")[max(0, index - 40) : index + 120]


def main() -> int:
    parser = argparse.ArgumentParser(description="Apple vs Whisper(MLX) 逐字稿對照")
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--runtime-dir", type=Path, required=True, help="gitignored raw 輸出（逐字稿原文）")
    parser.add_argument("--report", type=Path, required=True, help="報告目錄（tracked 區，只放指標/摘錄）")
    parser.add_argument("--engines", default=",".join(ENGINES))
    parser.add_argument(
        "--spec",
        action="append",
        default=None,
        help="引擎規格 name=backend[:WHISPER_MODEL]，可重複（預設沿用 --engines）",
    )
    parser.add_argument("--child-out", default=None, help="內部用：child 模式輸出 JSON")
    parser.add_argument("--data-dir", default=None, help="內部用：child 模式 DATA_DIR")
    parser.add_argument("--timeout", type=float, default=5400.0, help="單一引擎逾時（秒）")
    args = parser.parse_args()

    if args.child_out:
        backend, _, model = args.engines.partition(":")
        return run_engine_child(
            backend,
            str(args.audio),
            args.child_out,
            args.data_dir or str(Path(args.child_out).parent / f"data-{backend}"),
            model,
        )

    audio_path = args.audio if args.audio.is_absolute() else REPO_ROOT / args.audio
    runtime_dir = args.runtime_dir if args.runtime_dir.is_absolute() else REPO_ROOT / args.runtime_dir
    report_dir = args.report if args.report.is_absolute() else REPO_ROOT / args.report
    runtime_dir.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)

    if not audio_path.exists():
        print(f"[FAIL] 音檔不存在：{audio_path}", file=sys.stderr)
        return 1
    duration = float(
        subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(audio_path)],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    )
    audio_sha = sha256_file(audio_path)
    print(f"[INFO] audio={audio_path.name} duration={duration:.1f}s sha256={audio_sha[:12]}…")

    specs = []
    if args.spec:
        for item in args.spec:
            name, _, value = item.partition("=")
            specs.append((name.strip(), value.strip()))
    else:
        specs = [(item.strip(), item.strip()) for item in args.engines.split(",") if item.strip()]

    results = {}
    for engine, backend_and_model in specs:
        child_out = runtime_dir / f"engine-{engine}.json"
        log_path = runtime_dir / f"engine-{engine}.log"
        # `transcribe_detailed` 只接受位於 settings.uploads_dir 內的檔案（路徑守衛），
        # 因此每個引擎各複製一份到自己的 DATA_DIR/uploads（模擬真實上傳落地）。
        engine_data_dir = runtime_dir / f"data-{engine}"
        uploads_dir = engine_data_dir / "uploads"
        uploads_dir.mkdir(parents=True, exist_ok=True)
        staged_audio = uploads_dir / audio_path.name
        if not staged_audio.exists() or staged_audio.stat().st_size != audio_path.stat().st_size:
            subprocess.run(["cp", str(audio_path), str(staged_audio)], check=True)
        if child_out.exists():
            print(f"[INFO] {engine}：沿用既有 child 輸出 {child_out}")
        else:
            started = time.time()
            with open(log_path, "wb") as log_handle:
                proc = subprocess.run(
                    [
                        sys.executable,
                        str(Path(__file__).resolve()),
                        "--audio", str(staged_audio),
                        "--runtime-dir", str(runtime_dir),
                        "--report", str(report_dir),
                        "--engines", backend_and_model,
                        "--child-out", str(child_out),
                        "--data-dir", str(engine_data_dir),
                    ],
                    cwd=str(REPO_ROOT),
                    stdout=log_handle,
                    stderr=subprocess.STDOUT,
                    timeout=args.timeout,
                    env={**os.environ, "PYTHONIOENCODING": "utf-8"},
                )
            print(f"[INFO] {engine}：child exit={proc.returncode} wall={time.time() - started:.1f}s log={log_path}")
            if proc.returncode != 0 or not child_out.exists():
                print(f"[FAIL] {engine} 子程序失敗（見 {log_path}）", file=sys.stderr)
                return 1
        payload = json.loads(child_out.read_text(encoding="utf-8"))
        (runtime_dir / f"transcript-{engine}.txt").write_text(payload["text"], encoding="utf-8")
        results[engine] = payload

    comparison = {"audio": {"name": audio_path.name, "duration_seconds": duration, "sha256": audio_sha}}
    for engine, payload in results.items():
        stats = text_stats(payload["text"])
        comparison[engine] = {
            "engine": engine,
            "backend": payload["backend"],
            "whisper_model": payload.get("whisper_model"),
            "language": payload["language"],
            "elapsed_seconds": round(payload["elapsed_seconds"], 2),
            "real_time_factor": round(payload["real_time_factor"], 4),
            "chunk_count": payload["chunk_count"],
            "metadata": payload["metadata"],
            "stats": stats,
            "head": (payload["text"] or "")[:200],
            "tail": (payload["text"] or "")[-200:],
            "transcript_path": str(runtime_dir / f"transcript-{engine}.txt"),
        }

    engines_present = [name for name in results]
    if len(engines_present) == 2:
        left, right = engines_present
        left_text = normalize_for_compare(results[left]["text"])
        right_text = normalize_for_compare(results[right]["text"])
        comparison["agreement"] = {
            "engine_pair": f"{left} vs {right}",
            "char_ratio": round(difflib.SequenceMatcher(None, left_text, right_text).ratio(), 4),
            "length_ratio": round(len(left_text) / len(right_text), 4) if right_text else None,
            "left_only_chars": len(left_text) - len(right_text),
        }
        comparison["shared_checks"] = {
            "逾期視同沒有意見": {name: find_snippet(results[name]["text"], "沒有意見") for name in engines_present},
            "社交工程演練": {name: find_snippet(results[name]["text"], "社交工程") for name in engines_present},
            "尖峰時段": {name: find_snippet(results[name]["text"], "尖峰") for name in engines_present},
        }

    report_json = report_dir / "comparison.json"
    report_json.write_text(json.dumps(comparison, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    lines = [
        "# Apple SpeechAnalyzer vs Whisper(MLX) — 同一檔案實測對照",
        "",
        f"- 音檔：`{comparison['audio']['name']}`（{duration / 60:.1f} 分鐘，sha256 `{audio_sha[:16]}…`）",
        "- 兩者都走同一服務層 `transcription_service.transcribe_detailed`，只換 `ASR_BACKEND`。",
        "- 逐字稿原文（未節錄）：`" + str(runtime_dir) + "`（gitignored）。",
        "",
        "## 速度",
        "",
        "| 引擎 | 後端 | 耗時(s) | RTF（越小越快） | 音訊分鐘/耗時分鐘 |",
        "|---|---|---|---|---|",
    ]
    for engine in engines_present:
        item = comparison[engine]
        speedup = (duration / 60) / (item["elapsed_seconds"] / 60) if item["elapsed_seconds"] else 0
        lines.append(
            f"| {engine} | {item['backend']}"
        + (f"（{item['whisper_model']}）" if item.get("whisper_model") else "")
        + f" | {item['elapsed_seconds']:.1f} | {item['real_time_factor']:.4f} | {speedup:.1f}× |"
        )
    lines += ["", "## 逐字稿統計", ""]
    for engine in engines_present:
        stats = comparison[engine]["stats"]
        lines.append(
            f"- **{engine}**：{stats['chars']} 字（CJK {stats['cjk_chars']}）、標點 {stats['punctuation_marks']}"
            f"（每百 CJK {stats['punctuation_per_100_cjk']}）、數字 {stats['digit_chars']}、拉丁 {stats['latin_chars']}、"
            f"重複 8-gram 比例 {stats['repeat_ngram8']['repeated_ratio']:.4f}"
        )
    if "agreement" in comparison:
        lines += [
            "",
            "## 兩者一致度（無 ground truth，僅為交叉比對）",
            "",
            f"- 字元相似度：{comparison['agreement']['char_ratio']}（1.0 = 完全相同）",
            f"- 長度比：{comparison['agreement']['length_ratio']}（左/右）",
        ]
    lines += ["", "## 共同片段對照（同一時間點誰寫得對）", ""]
    for label, snippets in (comparison.get("shared_checks") or {}).items():
        lines.append(f"### {label}")
        for engine, snippet in snippets.items():
            lines.append(f"- `{engine}`：{snippet or '（找不到對應片段）'}")
        lines.append("")
    report_md = report_dir / "comparison.md"
    report_md.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"[INFO] report={report_json}")
    print("\n".join(lines[:40]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
