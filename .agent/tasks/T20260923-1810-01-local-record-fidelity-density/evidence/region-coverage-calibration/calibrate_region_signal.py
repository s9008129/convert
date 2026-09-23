#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""P7-B 校準探針：以「逐字稿區域顯著詞」檢查紀錄覆蓋——CORE-1 期望集合的離線評估。

目的（唯讀，不改產品程式）：
  在實作「區域／尾段期望集合」之前，先用既有交付紀錄回答三個問題——
  (1) 這個訊號能不能區分「有寫到尾段」與「尾段整段沒寫」的紀錄？
  (2) 門檻要定在哪裡才不會在 qwen（已寫到尾段）誤報？
  (3) 各區域的訊號是否一致（head vs tail）？

方法：
  - 逐字稿切成 R 個等量區域（依字元數）。
  - 每個區域取「顯著詞」＝含**罕見字**（全篇出現次數 ≤ rare_max）的 CJK n-gram（長 3-4）。
    罕見字＝名稱／專有名詞的代理訊號（例：黴、遷、舉、禮、聞），不需要字典或分詞。
  - 命中＝該詞出現在紀錄的正規化全文（與 measure_coverage 同一條正規化管線）。
  - 區域命中率＝命中數／探針數；低於門檻即「該區域疑似漏寫」。

用法：
  DATA_DIR=/tmp/calib uv run --frozen python <本檔> \
    --transcript data/cache/e2e/p7a-gemma31b-e7c/backend_data/outputs/0903-科務會議_bb492356_逐字稿.txt \
    --record label=path.md --out out.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
os.environ.setdefault("DATA_DIR", "/tmp/region_calibration_scratch")
sys.path.insert(0, str(REPO / "scripts" / "e2e"))
sys.path.insert(0, str(REPO))

import measure_coverage as mc  # noqa: E402

SEG_RE = re.compile(r"^\[(\d{2}:\d{2}:\d{2})-(\d{2}:\d{2}:\d{2})\]\s*(.*)$")
CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")


def parse_segments(path: Path) -> list[tuple[str, str, str]]:
    """回傳 [(start_ts, raw_line, normalized_body)]，依檔內順序。"""
    normalizer = mc.CoverageNormalizer()
    out: list[tuple[str, str, str]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        m = SEG_RE.match(line.strip())
        if not m:
            continue
        out.append((m.group(1), line.strip(), normalizer.normalize(m.group(3))))
    return out


def region_bounds(segments: list[tuple[str, str, str]], regions: int) -> list[tuple[int, int]]:
    """依字元數把 segment 序列切成 regions 段（回傳 index 範圍 [start, end)）。"""
    total = sum(len(seg[2]) for seg in segments) or 1
    bounds: list[tuple[int, int]] = []
    start = 0
    for index in range(1, regions + 1):
        target = total * index / regions
        acc = sum(len(seg[2]) for seg in segments[:start])
        end = start
        while end < len(segments) and acc < target:
            acc += len(segments[end][2])
            end += 1
        bounds.append((start, max(end, start + 1)))
        start = end
    bounds[-1] = (bounds[-1][0], len(segments))
    return bounds


def build_probes(
    segments: list[tuple[str, str, str]],
    bounds: tuple[int, int],
    char_freq: dict,
    *,
    rare_max: int,
    per_region: int,
) -> list[dict]:
    start, end = bounds
    seen_anchor: set = set()
    candidates: list[dict] = []
    for seg_index in range(start, min(end, len(segments))):
        ts, _raw, body = segments[seg_index]
        for pos, char in enumerate(body):
            if not CJK_RE.match(char) or char_freq.get(char, 0) > rare_max:
                continue
            if char in seen_anchor:
                continue
            seen_anchor.add(char)
            term = body[max(0, pos - 2): pos + 2]
            term = "".join(c for c in term if CJK_RE.match(c))
            if len(term) < 3:
                continue
            candidates.append({"term": term, "anchor": char, "ts": ts, "seg": seg_index})
    if len(candidates) <= per_region:
        return candidates
    step = len(candidates) / per_region
    return [candidates[int(i * step)] for i in range(per_region)]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--transcript", required=True)
    ap.add_argument("--record", action="append", default=[], help="label=path")
    ap.add_argument("--regions", type=int, default=4)
    ap.add_argument("--rare-max", type=int, default=3)
    ap.add_argument("--per-region", type=int, default=6)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    normalizer = mc.CoverageNormalizer()
    segments = parse_segments(Path(args.transcript))
    joined = "".join(seg[2] for seg in segments)
    char_freq: dict = {}
    for char in joined:
        char_freq[char] = char_freq.get(char, 0) + 1

    bounds = region_bounds(segments, args.regions)
    regions = []
    for index, bound in enumerate(bounds, start=1):
        probes = build_probes(
            segments, bound, char_freq, rare_max=args.rare_max, per_region=args.per_region
        )
        first_ts = segments[bound[0]][0] if bound[0] < len(segments) else "?"
        regions.append({"region": index, "first_ts": first_ts, "probes": probes})

    report = {
        "transcript": str(args.transcript),
        "segments": len(segments),
        "regions": args.regions,
        "rare_max": args.rare_max,
        "per_region": args.per_region,
        "records": {},
    }
    for spec in args.record:
        label, _, path = spec.partition("=")
        text = Path(path).read_text(encoding="utf-8")
        normalized = normalizer.normalize(text)
        per_region = []
        for region in regions:
            details = []
            for probe in region["probes"]:
                hit = probe["term"] in normalized
                details.append({**probe, "hit": hit})
            hits = sum(1 for d in details if d["hit"])
            total = len(details)
            per_region.append(
                {
                    "region": region["region"],
                    "first_ts": region["first_ts"],
                    "probes": total,
                    "hits": hits,
                    "ratio": round(hits / total, 4) if total else None,
                    "missing": [
                        {"term": d["term"], "ts": d["ts"]} for d in details if not d["hit"]
                    ],
                }
            )
        report["records"][label] = {"path": path, "char_count": len(text), "regions": per_region}

    print(f"逐字稿：{args.transcript}（{len(segments)} 段；{len(joined)} 字）")
    header = f"{'record':<34}" + "".join(f"R{i+1:<10}" for i in range(args.regions))
    print(header)
    for label, payload in report["records"].items():
        cells = []
        for region in payload["regions"]:
            ratio = region["ratio"]
            cells.append(f"{region['hits']}/{region['probes']}" + (f"({ratio:.2f})" if ratio is not None else ""))
        print(f"{label:<34}" + "".join(f"{c:<12}" for c in cells))
    for label, payload in report["records"].items():
        print(f"\n[{label}] 各區漏寫顯著詞：")
        for region in payload["regions"]:
            if region["missing"]:
                terms = "、".join(f"{m['term']}@{m['ts']}" for m in region["missing"])
                print(f"  R{region['region']}（起 {region['first_ts']}）：{terms}")

    if args.out:
        Path(args.out).write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"\n已寫入 {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
