"""P7-C C1b 離線重播：以**產品自身**的分塊器預測不同 ceiling 下的塊與落點。

零模型呼叫。輸入＝P7-B gemma E8 那場的交付逐字稿（與 P7-B E2E 同一份檔案）、
context window 71,936（該場 backend.log 實錄：lmstudio_instance）。輸出＝replay.json。
"""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", ".."))

from backend.core.config import settings
from backend.core.templates import get_template
from backend.services.summarization import SummarizationService

TRANSCRIPT = "data/cache/e2e/p7b-gemma31b-e8/backend_data/outputs/0903-科務會議_5444cdef_逐字稿.txt"
CONTEXT_WINDOW = 71936  # backend.log: context_window=71936(lmstudio_instance)
CEILINGS = [6000, 5500, 5000, 4500, 4000, 3000]
# 尾段探針：F044/F054/F055/F056/F060/F065/F066（P7-B §5 的阻斷集合）。
# 錨點用 **checklist 既有 probes（關鍵詞對）** 而非時間碼——各場 ASR 逐字稿時間碼不同，
# 時間碼錨會落空；關鍵詞錨與 E2E 量尺（measure_coverage.py）同一判準。
CHECKLIST = ".agent/tasks/T20260922-2037-02-local-model-quality-parity/quality/fact_checklist.json"
TAIL_IDS = ["F044", "F054", "F055", "F056", "F060", "F065", "F066"]


def load_probes() -> dict:
    payload = json.load(open(CHECKLIST, encoding="utf-8"))
    facts = payload["facts"] if isinstance(payload, dict) else payload
    return {f["id"]: f.get("probes") or [] for f in facts if f["id"] in TAIL_IDS}


def chunk_char_spans(transcript: str, chunks: list) -> list:
    """把每個 chunk 映回逐字稿的字元區間（chunk 依序且帶少量重疊）。"""
    spans = []
    cursor = 0
    for chunk in chunks:
        head = chunk[:60]
        start = transcript.find(head, max(0, cursor - 400))
        if start < 0:
            start = transcript.find(head)
        spans.append((start, start + len(chunk)))
        cursor = max(cursor, start)
    return spans


def locate_offset(transcript: str, probes: list) -> tuple:
    """以**字元位移**定位事實證據（比行級定位精確：本逐字稿的行是長段落）。

    回傳（offset, 命中 probe, 命中型別, 引文）。先要求 probe 全詞命中，
    落空才退單詞並明確標記 single_token_fallback——不混淆兩種強度。
    """
    for probe in probes:
        if len(probe) > 1 and probe[1] in transcript:
            for match in __import__("re").finditer(__import__("re").escape(probe[0]), transcript):
                window = transcript[match.start(): match.start() + 1200]
                if all(token in window for token in probe):
                    return match.start(), list(probe), "pair", window[:120]
    for probe in probes:
        for token in probe:
            offset = transcript.find(token)
            if offset >= 0:
                return offset, [token], "single_token_fallback", transcript[offset: offset + 120]
    return None, None, None, None


def main() -> int:
    transcript = open(TRANSCRIPT, encoding="utf-8").read()
    probes = load_probes()
    svc = SummarizationService()
    template = get_template("section_meeting")
    system_prompt = template.resolve_system_prompt()

    result = {
        "kind": "p7c-chunk-replay",
        "transcript_path": TRANSCRIPT,
        "transcript_chars": len(transcript),
        "context_window_tokens": CONTEXT_WINDOW,
        "source_of_context_window": "data/cache/e2e/p7b-gemma31b-e8/backend_data/logs/app_2026-09-23.log:96",
        "model_calls": 0,
        "tail_probe_ids": TAIL_IDS,
        "tail_probe_source": CHECKLIST,
        "runs": [],
    }

    for ceiling in CEILINGS:
        settings.LOCAL_LLM_EXTRACTION_CHUNK_CEILING_TOKENS = ceiling
        plan = svc._build_local_context_plan(
            transcript, system_prompt, template=template, context_window_tokens=CONTEXT_WINDOW
        )
        chunks = (
            svc._split_transcript_into_chunks(transcript, plan.chunk_input_budget_tokens)
            if plan.needs_chunking
            else [transcript]
        )
        labels = []
        for chunk in chunks:
            tags = __import__("re").findall(r"\[\d{2}:\d{2}:\d{2}-\d{2}:\d{2}:\d{2}\]", chunk)
            labels.append([tags[0] if tags else None, tags[-1] if tags else None])
        spans = chunk_char_spans(transcript, chunks)
        landing = {}
        for fact_id in TAIL_IDS:
            offset, matched, kind, snippet = locate_offset(transcript, probes[fact_id])
            if offset is None:
                landing[fact_id] = {"chunk_index": None, "probe": None, "match": None, "snippet": None}
                continue
            hits = [
                idx for idx, (start, end) in enumerate(spans) if start <= offset < end
            ]
            landing[fact_id] = {
                "chunk_index": hits[0] if hits else None,
                "chunk_indices_all": hits,
                "probe": matched,
                "match": kind,
                "char_offset": offset,
                "snippet": snippet,
            }
        result["runs"].append(
            {
                "extraction_ceiling_tokens": ceiling,
                "estimated_transcript_tokens": plan.estimated_transcript_tokens,
                "context_derived_chunk_budget_tokens": None,
                "chunk_input_budget_tokens": plan.chunk_input_budget_tokens,
                "chunk_count": len(chunks),
                "chunk_estimated_tokens": [svc._estimate_tokens(c) for c in chunks],
                "chunk_time_ranges": labels,
                "tail_fact_chunk_index": landing,
            }
        )

    baseline = {
        "kind": "product-log-baseline",
        "note": "P7-B gemma E8 實跑（ceiling=6000）的 backend.log 實錄值，供重播對帳",
        "context_window_tokens": 71936,
        "estimated_transcript_tokens": 11711,
        "chunk_input_budget_tokens": 6000,
        "context_derived_budget_tokens": 65953,
    }
    result["product_log_baseline"] = baseline

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "replay.json")
    with open(out, "w", encoding="utf-8") as handle:
        json.dump(result, handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    sys.stderr.write(f"wrote {out}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
