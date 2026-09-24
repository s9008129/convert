#!/usr/bin/env python3
"""Run one controlled, privacy-safe local first-divergence diagnostic.

Transcript, claim specification, summary, and optional stage snapshots stay in
an explicitly gitignored diagnostic root. Stdout contains safe configuration
and redacted metadata only.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TASK_ID = "T20260924-1523-01-issue18-local-fidelity"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transcript", type=Path, required=True)
    parser.add_argument("--expected-provider", choices=("lmstudio", "ollama"), required=True)
    parser.add_argument("--expected-model", required=True)
    parser.add_argument("--template", required=True)
    parser.add_argument("--diagnostic-root", type=Path, required=True)
    parser.add_argument("--claim-spec", type=Path, required=True)
    parser.add_argument("--seed", type=int, help="Provider seed support is not currently exposed by this path.")
    parser.add_argument("--raw-snapshot-opt-in", action="store_true")
    return parser.parse_args()


def run_git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=PROJECT_ROOT, check=True, capture_output=True, text=True
    )
    return completed.stdout.strip()


def assert_gitignored(path: Path) -> Path:
    resolved = path.expanduser().resolve()
    probe = resolved / "__diagnostic_privacy_probe__"
    completed = subprocess.run(
        ["git", "check-ignore", "-q", str(probe)], cwd=PROJECT_ROOT,
        capture_output=True, check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError("diagnostic root is not gitignored")
    return resolved


def read_claim_spec(path: Path) -> dict[str, Any]:
    spec = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "claim_id", "claim_type", "source_anchor", "expected_relation",
        "unacceptable_variants", "normalized_keywords",
    }
    if not isinstance(spec, dict) or not required.issubset(spec):
        raise ValueError("claim specification is missing required fields")
    if not isinstance(spec["claim_id"], str) or not spec["claim_id"].strip():
        raise ValueError("claim specification has no claim_id")
    return spec


def lmstudio_loaded_snapshot(base_url: str) -> list[dict[str, Any]]:
    import httpx

    response = httpx.get(f"{base_url.rstrip('/')}/api/v1/models", timeout=10)
    response.raise_for_status()
    payload = response.json()
    result = []
    for model in payload.get("models", []):
        if model.get("type") != "llm":
            continue
        for instance in model.get("loaded_instances") or []:
            result.append({
                "model_key": model.get("key"),
                "instance_id": instance.get("id"),
                "context_length": (instance.get("config") or {}).get("context_length"),
            })
    return sorted(result, key=lambda item: (item["model_key"] or "", item["instance_id"] or ""))


async def run(args: argparse.Namespace) -> int:
    transcript_path = args.transcript.expanduser().resolve()
    claim_path = args.claim_spec.expanduser().resolve()
    if not transcript_path.is_file() or not claim_path.is_file():
        raise FileNotFoundError("diagnostic input is unavailable")
    if args.seed is not None:
        raise ValueError("fixed seeds are not supported by the current production local path")
    if run_git("status", "--porcelain", "--untracked-files=no"):
        raise RuntimeError("tracked working tree must be committed before a controlled run")
    diagnostic_root = assert_gitignored(args.diagnostic_root)
    raw_root = assert_gitignored(diagnostic_root / "raw")
    claim = read_claim_spec(claim_path)
    transcript_bytes = transcript_path.read_bytes()
    transcript = transcript_bytes.decode("utf-8")
    transcript_hash = hashlib.sha256(transcript_bytes).hexdigest()
    code_revision = run_git("rev-parse", "HEAD")
    run_id = uuid.uuid4().hex

    # Keep application log output metadata-only; raw user/model material is only
    # available in memory and in the explicitly opted-in ignored snapshot root.
    os.environ["DATA_DIR"] = str(PROJECT_ROOT / "data")
    os.environ["LOG_LEVEL"] = "CRITICAL"
    sys.path.insert(0, str(PROJECT_ROOT))
    from backend.core.config import settings
    from backend.core.templates import get_template
    from backend.models.schemas import ProcessingMode
    from backend.services.local_pipeline_diagnostics import LocalPipelineDiagnosticRecorder
    from backend.services.summarization import SummarizationService

    template = get_template(args.template)
    service = SummarizationService()
    engine = await service._select_local_engine()
    selection = service._active_lmstudio_selection
    actual_provider = selection.provider if selection else engine
    actual_model = selection.model_identifier if selection else settings.LOCAL_LLM_MODEL
    if actual_provider != args.expected_provider or actual_model != args.expected_model:
        raise RuntimeError("selected provider/model does not match the expected identity")

    before_inventory = None
    if actual_provider == "lmstudio":
        before_inventory = lmstudio_loaded_snapshot(settings.LMSTUDIO_BASE_URL)
        matched = [item for item in before_inventory if item["model_key"] == args.expected_model]
        if len(matched) != 1 or matched[0]["instance_id"] != selection.loaded_instance_id:
            raise RuntimeError("LM Studio loaded-instance identity is not stable")

    frozen = {
        "run_id": run_id,
        "code_revision": code_revision,
        "transcript_sha256": transcript_hash,
        "claim_id": claim["claim_id"],
        "provider": actual_provider,
        "model_key": actual_model,
        "loaded_instance_id": selection.loaded_instance_id if selection else None,
        "context_length": selection.context_length if selection else settings.LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS,
        "template_id": template.id,
        "temperature_extraction": 0.1,
        "temperature_final": 0.2,
        "temperature_refinement": 0.15,
        "requested_max_tokens": settings.LOCAL_LLM_RESERVED_OUTPUT_TOKENS,
        "max_refinement_rounds": settings.LOCAL_LLM_MAX_REFINEMENT_ROUNDS,
        "max_merge_rounds": settings.LOCAL_LLM_MAX_MERGE_ROUNDS,
        "chunk_overlap_budget_tokens": SummarizationService.LOCAL_LLM_CHUNK_OVERLAP_BUDGET_TOKENS,
        "merge_visible_target_ceiling_tokens": SummarizationService.LOCAL_LLM_MERGE_VISIBLE_TARGET_CEILING_TOKENS,
        "disable_thinking": settings.LOCAL_LLM_DISABLE_THINKING,
        "raw_snapshots_enabled": bool(args.raw_snapshot_opt_in),
    }
    print(json.dumps(frozen, ensure_ascii=False, sort_keys=True))

    recorder = LocalPipelineDiagnosticRecorder(
        run_id=run_id,
        raw_snapshot_dir=raw_root,
        raw_snapshots_enabled=args.raw_snapshot_opt_in,
        metadata={**frozen, "engine": engine},
    )
    started = time.monotonic()
    try:
        summary = await service.summarize(
            transcript,
            mode=ProcessingMode.LOCAL,
            template_id=template.id,
            diagnostic_recorder=recorder,
        )
    except Exception as exc:  # noqa: BLE001 - preserve only redacted failure evidence
        recorder.record("pipeline.end", status=f"failed:{type(exc).__name__}")
        recorder.metadata.update({"code_revision": code_revision, "elapsed_ms": int((time.monotonic() - started) * 1000)})
        diagnostic_root.mkdir(parents=True, exist_ok=True)
        recorder.write_redacted_manifest(diagnostic_root / "manifest.json")
        raise
    elapsed_ms = int((time.monotonic() - started) * 1000)

    selected_model = recorder.metadata.get("model_key")
    selected_instance = recorder.metadata.get("loaded_instance_id")
    if selected_model != args.expected_model:
        raise RuntimeError("model identity changed before the pipeline run")
    if selection and selected_instance != selection.loaded_instance_id:
        raise RuntimeError("loaded-instance identity changed before the pipeline run")
    if actual_provider == "lmstudio":
        after_inventory = lmstudio_loaded_snapshot(settings.LMSTUDIO_BASE_URL)
        if after_inventory != before_inventory:
            raise RuntimeError("LM Studio loaded model inventory changed during the run")

    recorder.metadata.update({"code_revision": code_revision, "elapsed_ms": elapsed_ms})
    diagnostic_root.mkdir(parents=True, exist_ok=True)
    output_path = diagnostic_root / "summary.local-only.md"
    output_path.write_text(summary, encoding="utf-8")
    if not recorder.write_redacted_manifest(diagnostic_root / "manifest.json"):
        raise RuntimeError("redacted manifest could not be written")
    print(json.dumps({
        "run_id": run_id,
        "status": "summary_generated",
        "summary_failed": False,
        "elapsed_ms": elapsed_ms,
        "event_count": len(recorder.events),
        "claim_status_requires_human_adjudication": True,
    }, sort_keys=True))
    return 0


def main() -> int:
    args = parse_args()
    try:
        return asyncio.run(run(args))
    except Exception as exc:  # noqa: BLE001 - stdout/stderr must not expose payloads
        print(json.dumps({"status": "diagnostic_failed", "error_type": type(exc).__name__}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
