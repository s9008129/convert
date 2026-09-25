#!/usr/bin/env python3
"""Privacy-safe real-meeting diagnostic for Issue #18.

The caller supplies an existing transcript/checklist and optional historical
record. Model text is kept in memory only. Stdout contains only hashes/counts
and deterministic coverage/fidelity indicators; no transcript, prompt, fact
statement, person name, or generated minute text is emitted.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

os.environ.setdefault("LOCAL_LLM_PROVIDER", "openrouter")
os.environ.setdefault("LOCAL_PIPELINE_VERSION", "v2")
os.environ.setdefault("LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS", "32768")
os.environ.setdefault("LOCAL_LLM_DISABLE_THINKING", "true")

from backend.core.config import settings  # noqa: E402
from backend.models.schemas import ProcessingMode  # noqa: E402
from backend.services.local_pipeline_v2 import unsupported_high_risk_additions  # noqa: E402
from backend.services.summarization import SummarizationService  # noqa: E402
from backend.services.local_pipeline_diagnostics import LocalPipelineDiagnosticRecorder  # noqa: E402


MODELS = ("google/gemma-4-31b-it", "qwen/qwen3.8-27b")
_ITEM_PREFIX = re.compile(r"^\s*(?:[-*]|\d+[.、]|[（(]\d+[)）])\s*")
_NON_WORD = re.compile(r"[^\w\u3400-\u4dbf\u4e00-\u9fff]+")
_KEEP_COVERAGE = re.compile(
    "[^0-9A-Za-z"
    "\\u3400-\\u4dbf"
    "\\u4e00-\\u9fff"
    "\\uf900-\\ufaff"
    "\\U00020000-\\U0003ffff"
    "]"
)

try:
    from opencc import OpenCC

    _OPENCC = OpenCC("s2twp")
except Exception:  # pragma: no cover - CI has the locked dependency
    _OPENCC = None


def _normalize_coverage(text: str) -> str:
    value = unicodedata.normalize("NFKC", text or "").casefold()
    if _OPENCC is not None:
        value = _OPENCC.convert(value)
    value = re.sub(r"\\s+", "", value)
    return _KEEP_COVERAGE.sub("", value)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _fact_covered(record_norm: str, fact: dict[str, Any]) -> bool:
    probes = fact.get("probes") or []
    for probe in probes:
        if isinstance(probe, str):
            terms = [probe]
        elif isinstance(probe, list):
            terms = [str(term) for term in probe if str(term)]
        else:
            continue
        normalized_terms = [_normalize_coverage(term) for term in terms]
        if normalized_terms and all(term and term in record_norm for term in normalized_terms):
            return True
    return False


def _coverage(record: str, facts: list[dict[str, Any]]) -> dict[str, Any]:
    record_norm = _normalize_coverage(record)
    core = [fact for fact in facts if fact.get("tier") == "core"]
    covered_all = sum(_fact_covered(record_norm, fact) for fact in facts)
    covered_core = sum(_fact_covered(record_norm, fact) for fact in core)
    return {
        "facts_total": len(facts),
        "facts_covered": covered_all,
        "coverage_ratio": round(covered_all / len(facts), 6) if facts else None,
        "core_total": len(core),
        "core_covered": covered_core,
        "core_coverage_ratio": round(covered_core / len(core), 6) if core else None,
    }


def _duplicate_stats(record: str) -> dict[str, int]:
    normalized: list[str] = []
    for line in record.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("|"):
            continue
        text = _ITEM_PREFIX.sub("", stripped)
        text = _NON_WORD.sub("", text)
        if len(text) >= 8:
            normalized.append(text)
    counts: dict[str, int] = {}
    for item in normalized:
        counts[item] = counts.get(item, 0) + 1
    duplicate_groups = sum(count > 1 for count in counts.values())
    duplicate_extra_items = sum(max(0, count - 1) for count in counts.values())
    return {
        "normalized_item_count": len(normalized),
        "duplicate_groups": duplicate_groups,
        "duplicate_extra_items": duplicate_extra_items,
    }


def _metrics(record: str, transcript: str, facts: list[dict[str, Any]]) -> dict[str, Any]:
    high_risk = unsupported_high_risk_additions(transcript, record)
    return {
        "record_sha256": _sha256(record),
        "record_chars": len(record),
        **_coverage(record, facts),
        **_duplicate_stats(record),
        "unsupported_high_risk_count": len(high_risk),
        "unsupported_high_risk_kinds": sorted(set(high_risk)),
        "pending_confirmation_count": record.count("（待確認）"),
        "v2_source_tag_count": len(re.findall(r"〔span-\d+〕", record)),
    }


def _pipeline_metrics(recorder: LocalPipelineDiagnosticRecorder) -> dict[str, Any]:
    events = recorder.events
    extraction = [
        event for event in events
        if event.get("stage_id", "").startswith("v2.extraction.chunk.")
        and event.get("stage_id", "").endswith(".outcome")
        and event.get("status") == "parsed"
    ]
    patch_terminal = [
        event for event in events
        if re.fullmatch(r"v2\.patch\.[^.]+", str(event.get("stage_id", "")))
    ]
    final = next(
        (event for event in reversed(events)
         if event.get("stage_id") == "v2.coverage.final"),
        {},
    )
    evidence_resolution = next(
        (event for event in reversed(events)
         if event.get("stage_id") == "v2.evidence-resolution"),
        {},
    )
    return {
        "extraction_chunk_count": len(extraction),
        "extraction_claim_count": sum(int(event.get("claim_count", 0)) for event in extraction),
        "resolved_claim_count": int(evidence_resolution.get("resolved_count", 0)),
        "ambiguous_claim_count": int(evidence_resolution.get("ambiguous_count", 0)),
        "patch_accepted_count": sum(event.get("status") == "accepted" for event in patch_terminal),
        "patch_rolled_back_count": sum(event.get("status") == "rolled_back" for event in patch_terminal),
        "planned_sections": int(final.get("planned_sections", 0)),
        "required_claim_count": int(final.get("required_claim_count", 0)),
        "coverage_issue_count": int(final.get("coverage_issue_count", 0)),
    }


async def _run_model(
    model: str,
    transcript: str,
    facts: list[dict[str, Any]],
    template_id: str,
) -> dict[str, Any]:
    settings.OPENROUTER_MODEL = model
    service = SummarizationService()
    recorder = LocalPipelineDiagnosticRecorder(
        run_id="issue18-real-meeting-diagnostic"
    )
    try:
        record = await service.summarize(
            transcript,
            mode=ProcessingMode.LOCAL,
            template_id=template_id,
            diagnostic_recorder=recorder,
        )
        result = {
            "model": model,
            "status": "PASS",
            **_metrics(record, transcript, facts),
            "pipeline": _pipeline_metrics(recorder),
        }
        if result["unsupported_high_risk_count"] != 0:
            raise RuntimeError("privacy-safe diagnostic found unsupported high-risk additions")
        return result
    except Exception as exc:  # noqa: BLE001 - peer model must still run
        return {
            "model": model,
            "status": "FAIL",
            "error_class": type(exc).__name__,
            "pipeline": _pipeline_metrics(recorder),
        }
    finally:
        await service.close()


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--transcript", type=Path, required=True)
    parser.add_argument("--checklist", type=Path, required=True)
    parser.add_argument("--baseline-record", type=Path)
    parser.add_argument("--cloud-coverage", type=Path)
    parser.add_argument("--template", default="section_meeting")
    args = parser.parse_args()

    if not settings.OPENROUTER_API_KEY:
        raise SystemExit("OPENROUTER_API_KEY is required")

    transcript = args.transcript.read_text(encoding="utf-8")
    checklist = json.loads(args.checklist.read_text(encoding="utf-8"))
    facts = checklist.get("facts") or checklist.get("items") or []
    if not isinstance(facts, list) or not facts:
        raise SystemExit("checklist facts are missing")

    summary: dict[str, Any] = {
        "diagnostic_scope": "real_meeting_non_designated_source",
        "transcript_sha256": _sha256(transcript),
        "transcript_chars": len(transcript),
        "checklist_sha256": hashlib.sha256(args.checklist.read_bytes()).hexdigest(),
        "checklist_fact_count": len(facts),
    }
    if args.baseline_record is not None:
        baseline = args.baseline_record.read_text(encoding="utf-8")
        summary["historical_baseline"] = _metrics(baseline, transcript, facts)
    if args.cloud_coverage is not None:
        cloud = json.loads(args.cloud_coverage.read_text(encoding="utf-8"))
        summary["historical_cloud_coverage"] = {
            "metric_version": cloud.get("metric_version"),
            "coverage_all": cloud.get("coverage_all"),
            "coverage_core": cloud.get("coverage_core"),
            "covered_total": cloud.get("covered_total"),
            "covered_core": cloud.get("covered_core"),
            "fact_total": cloud.get("fact_total"),
            "fact_core_total": cloud.get("fact_core_total"),
        }

    results = []
    failed = False
    cloud_ref = summary.get("historical_cloud_coverage") or {}
    cloud_all = cloud_ref.get("coverage_all")
    cloud_core = cloud_ref.get("coverage_core")

    # Isolate model failures. A Gemma failure must never erase the Qwen result
    # (or vice versa); every model emits its privacy-safe metrics immediately.
    for model in MODELS:
        result = await _run_model(model, transcript, facts, args.template)
        if result.get("status") != "PASS":
            failed = True
        elif cloud_all and cloud_core:
            result["coverage_vs_cloud_ratio"] = round(
                result["coverage_ratio"] / cloud_all, 6
            )
            result["core_coverage_vs_cloud_ratio"] = round(
                result["core_coverage_ratio"] / cloud_core, 6
            )
        results.append(result)
        print(
            "REAL_DIAGNOSTIC_MODEL "
            + json.dumps(result, ensure_ascii=False, sort_keys=True),
            flush=True,
        )

    summary["models"] = results
    print("REAL_DIAGNOSTIC " + json.dumps(summary, ensure_ascii=False, sort_keys=True))
    print("OPENROUTER_REAL_DIAGNOSTIC=" + ("FAIL" if failed else "PASS"))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
