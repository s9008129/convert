#!/usr/bin/env python3
"""Create a hash-linked, redacted claim-stage table from a local run.

The stage judgments are human-adjudicated input. This utility validates their
shape and joins them to safe hashes in the run manifest; it never reads raw
stage snapshots or writes claim text.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


STATUSES = {
    "CORRECT", "MISSING", "DISTORTED", "UNSUPPORTED_ADDITION", "AMBIGUOUS", "NOT_APPLICABLE"
}
FIRST_DIVERGENCE_STATUSES = {"MISSING", "DISTORTED", "UNSUPPORTED_ADDITION"}
CLAIM_STAGE_PREFIXES = ("extraction.chunk.", "consolidation.", "final.", "refinement.", "selection.", "pipeline.end")


def _read_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read {label}") from exc


def build_evidence(manifest: dict[str, Any], claim: dict[str, Any], judgments: list[dict[str, str]]) -> dict[str, Any]:
    claim_id = claim.get("claim_id")
    if not isinstance(claim_id, str) or not claim_id:
        raise ValueError("claim specification has no claim_id")
    if manifest.get("metadata", {}).get("claim_id") != claim_id:
        raise ValueError("claim id does not match the run manifest")
    events = manifest.get("events")
    if not isinstance(events, list):
        raise ValueError("manifest has no event list")
    event_by_stage: dict[str, dict[str, Any]] = {}
    event_sequences: set[int] = set()
    for event in events:
        if not isinstance(event, dict) or not isinstance(event.get("stage_id"), str):
            raise ValueError("manifest contains an invalid event")
        stage_id = event["stage_id"]
        if stage_id in event_by_stage:
            raise ValueError("manifest event stage ids must be unique")
        sequence = event.get("sequence")
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence <= 0:
            raise ValueError("manifest event sequences must be positive integers")
        if sequence in event_sequences:
            raise ValueError("manifest event sequences must be unique")
        event_sequences.add(sequence)
        for hash_key in ("input_sha256", "output_sha256"):
            digest = event.get(hash_key)
            if digest is not None and (not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)):
                raise ValueError("manifest contains an invalid event hash")
        event_by_stage[stage_id] = event

    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    first_divergence = None
    source_correct = False
    if not isinstance(judgments, list) or not judgments:
        raise ValueError("stage judgments must be a non-empty list")
    normalized: list[tuple[int, dict[str, str]]] = []
    for item in judgments:
        if not isinstance(item, dict):
            raise ValueError("each stage judgment must be an object")
        stage_id = item.get("stage_id")
        if stage_id == "source":
            normalized.append((-1, item))
        else:
            event = event_by_stage.get(stage_id)
            if event is None or not isinstance(event.get("sequence"), int):
                raise ValueError("stage judgment does not match a manifest event")
            normalized.append((event["sequence"], item))
    normalized.sort(key=lambda pair: pair[0])

    for _sequence, item in normalized:
        stage_id = item.get("stage_id")
        status = item.get("status")
        if not isinstance(stage_id, str) or not stage_id or stage_id in seen:
            raise ValueError("stage judgments must have unique non-empty stage ids")
        if status not in STATUSES:
            raise ValueError("stage judgment has an unknown categorical status")
        seen.add(stage_id)
        event = event_by_stage.get(stage_id)
        if stage_id != "source" and event is None:
            raise ValueError("stage judgment does not match a manifest event")
        if stage_id == "source":
            if status != "CORRECT":
                raise ValueError("source stage must be adjudicated CORRECT")
            source_correct = True
            event_sequence = None
            input_hash = None
            output_hash = hashlib.sha256(claim.get("source_anchor", "").encode("utf-8")).hexdigest()
        else:
            event_sequence = event.get("sequence")
            input_hash = event.get("input_sha256")
            output_hash = event.get("output_sha256")
            if source_correct and first_divergence is None and status in FIRST_DIVERGENCE_STATUSES:
                first_divergence = stage_id
        rows.append({
            "stage_id": stage_id,
            "status": status,
            "event_sequence": event_sequence,
            "input_sha256": input_hash,
            "output_sha256": output_hash,
        })

    if not rows or rows[0]["stage_id"] != "source" or not source_correct:
        raise ValueError("stage judgments must begin with the verified source claim")
    if "selection.final" not in seen:
        raise ValueError("stage judgments must include selection.final")
    required_stage_ids = {
        stage_id for stage_id in event_by_stage
        if stage_id.startswith(CLAIM_STAGE_PREFIXES)
    }
    missing_stages = required_stage_ids - seen
    if missing_stages:
        raise ValueError("stage judgments omit required claim stages")
    final_status = next(row["status"] for row in rows if row["stage_id"] == "selection.final")
    source_anchor = claim.get("source_anchor", "")
    return {
        "schema_version": 1,
        "run_id": manifest.get("run_id"),
        "claim_id": claim_id,
        "claim_type": claim.get("claim_type"),
        "source_anchor_sha256": hashlib.sha256(source_anchor.encode("utf-8")).hexdigest(),
        "manifest_sha256": hashlib.sha256(json.dumps(manifest, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest(),
        "first_divergence_stage": first_divergence,
        "final_delivery_status": final_status,
        "stages": rows,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--claim-spec", type=Path, required=True)
    parser.add_argument("--judgments", type=Path, required=True, help="Local JSON array of {stage_id,status}; no claim text.")
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = _read_json(args.manifest, "redacted manifest")
    claim = _read_json(args.claim_spec, "claim specification")
    judgments = _read_json(args.judgments, "categorical judgments")
    if not isinstance(manifest, dict) or not isinstance(claim, dict) or not isinstance(judgments, list):
        raise ValueError("manifest, claim, or judgments have the wrong shape")
    evidence = build_evidence(manifest, claim, judgments)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "run_id": evidence["run_id"],
        "claim_id": evidence["claim_id"],
        "first_divergence_stage": evidence["first_divergence_stage"],
        "final_delivery_status": evidence["final_delivery_status"],
        "stage_count": len(evidence["stages"]),
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
