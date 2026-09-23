#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P7-B 診斷探針：把「會議尾段」單獨餵給同一顆地端模型跑同一份萃取提示詞。

目的（唯一）：分辨 gemma 的尾段事實漏失是
  (A) 萃取階段的一次性長輸入稀釋（尾段單獨萃取就能救回）→ 分塊／尾段補萃取有效
  (B) 生成階段寫不進去（尾段單獨萃取也一樣救不回）→ 槓桿要打在生成／補強

本探針**不修改產品程式**，只呼叫 LM Studio 既有的 OpenAI 相容端點，套用
`SummarizationService._local_extraction_prompt()` 與 `_build_chunk_extraction_message()`
（＝與產品完全同一份提示詞，避免提示詞漂移造成假結論）。

用法：
  uv run --frozen python <本檔> --start 00:33:00 --out <輸出目錄>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))
TRANSCRIPT = REPO / "data/cache/e2e/p7a-gemma31b-e7c/backend_data/outputs/0903-科務會議_bb492356_逐字稿.txt"
ENDPOINT = "http://localhost:1234/v1/chat/completions"

# 尾段應涵蓋的事實探針（來自 fact_checklist.json 的 gemma 缺失項；字面）
PROBES = {
    "F044 選舉政治敏感": ["選舉"],
    "F054 搬遷時程拖很久": ["兩階段", "搬遷"],
    "F055 三樓淹水溢流禮堂": ["禮堂", "淹水"],
    "F056 防水刨除／排水管": ["刨除", "排水管", "防水"],
    "F060 空辦公室霉味": ["霉味", "黴味"],
    "F065 分兩階段／工產科財管科": ["工產科", "工廠科", "財管科"],
    "F066 移交新聞行銷處": ["新聞行銷處", "新聞學校處"],
}


def seg_start(ts: str) -> int:
    h, m, s = (int(x) for x in ts.split(":"))
    return h * 3600 + m * 60 + s


def load_segments() -> list[tuple[int, int, str]]:
    text = TRANSCRIPT.read_text(encoding="utf-8")
    out = []
    for m in re.finditer(r"\[(\d{2}:\d{2}:\d{2})-(\d{2}:\d{2}:\d{2})\](.*)", text):
        out.append((seg_start(m.group(1)), seg_start(m.group(2)), m.group(0).strip()))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="00:33:00")
    ap.add_argument("--model", default="gemma-4-31b-it-mlx")
    ap.add_argument("--max-tokens", type=int, default=2048)
    ap.add_argument("--temperature", type=float, default=0.1)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    from backend.core.templates import get_template
    from backend.services.summarization import SummarizationService

    template = get_template("section_meeting")
    service = SummarizationService.__new__(SummarizationService)  # 只借純函式，不初始化 I/O
    system_prompt = service._local_extraction_prompt(template)

    start = seg_start(args.start)
    segs = [s for s in load_segments() if s[0] >= start]
    chunk = "\n".join(s[2] for s in segs)
    user_message = service._build_chunk_extraction_message(chunk, 1, 1)

    payload = {
        "model": args.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": args.temperature,
        "max_tokens": args.max_tokens,
        "stream": False,
    }
    req = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=3600) as resp:  # noqa: S310
        body = json.loads(resp.read().decode("utf-8"))

    notes = body["choices"][0]["message"]["content"]
    outdir = Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / "tail_slice.txt").write_text(chunk, encoding="utf-8")
    (outdir / "tail_notes.md").write_text(notes, encoding="utf-8")

    hits = {k: [w for w in words if w in notes] for k, words in PROBES.items()}
    summary = {
        "model": args.model,
        "slice_start": args.start,
        "segments": len(segs),
        "slice_chars": len(chunk),
        "notes_chars": len(notes),
        "usage": body.get("usage"),
        "finish_reason": body["choices"][0].get("finish_reason"),
        "probe_hits": hits,
        "probe_hit_count": sum(1 for v in hits.values() if v),
        "probe_total": len(PROBES),
    }
    (outdir / "result.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
