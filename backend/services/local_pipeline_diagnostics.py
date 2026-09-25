"""Privacy-safe, opt-in event collection for local summarization diagnostics.

The default recorder is memory-only. Raw content is written only when the caller
explicitly enables snapshots; manifests contain hashes, counts, and allow-listed
metadata, never prompts, transcripts, or model text.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from backend.core.logger import log


_SAFE_STAGE = re.compile(r"^[a-zA-Z0-9_.-]{1,120}$")
_SAFE_METADATA_KEYS = {
    "provider",
    "backend",
    "family",
    "model_key",
    "model_identity",
    "loaded_instance_id",
    "context_length",
    "planner_context_length",
    "native_schema_capability",
    "error_class",
    "http_status",
    "schema",
    "requested_max_tokens",
    "temperature",
    "baseline_temperature",
    "finish_reason",
    "prompt_tokens",
    "completion_tokens",
    "reasoning_tokens",
    "reasoning_present",
    "reasoning_char_count",
    "semantic_retry_count",
    "network_retry_count",
    "generation_count",
    "elapsed_ms",
    "engine",
    "code_revision",
    "transcript_sha256",
    "raw_source_sha256",
    "corrected_view_supplied",
    "corrected_alignment",
    "template_id",
    "claim_id",
    "context_window_source",
    "chunk_count",
    "source_excerpt_count",
    "merge_rounds",
    "validation_issue_count",
    "planned_sections",
    "required_claim_count",
    "coverage_issue_count",
    "duplicate_claim_count",
    "template_term_missing_count",
    "unsupported_control_count",
    "supported_profile_control_count",
    "unsupported_controls",
    "supported_controls",
}
_CLAIM_STATUSES = {
    "CORRECT",
    "MISSING",
    "DISTORTED",
    "UNSUPPORTED_ADDITION",
    "AMBIGUOUS",
    "NOT_APPLICABLE",
}


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class LocalPipelineDiagnosticRecorder:
    """Collect ordered stage metadata and optionally persist local-only snapshots."""

    def __init__(
        self,
        *,
        run_id: str,
        raw_snapshot_dir: Optional[Path] = None,
        raw_snapshots_enabled: bool = False,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        self.run_id = run_id
        self.raw_snapshot_dir = Path(raw_snapshot_dir) if raw_snapshot_dir is not None else None
        self.raw_snapshots_enabled = bool(raw_snapshots_enabled and self.raw_snapshot_dir)
        self.metadata = self._safe_metadata(metadata or {})
        self.events: list[dict[str, Any]] = []
        self.claim_status: dict[str, str] = {}

    @staticmethod
    def _safe_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
        safe: dict[str, Any] = {}
        for key in _SAFE_METADATA_KEYS:
            value = metadata.get(key)
            if value is None or isinstance(value, (str, int, float, bool)):
                if value is not None:
                    safe[key] = value
        return safe

    def record(
        self,
        stage_id: str,
        *,
        input_text: Optional[str] = None,
        output_text: Optional[str] = None,
        source_branch: Optional[str] = None,
        status: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Append a redacted event; diagnostics must never affect product behavior."""
        if not _SAFE_STAGE.fullmatch(stage_id):
            log.warning("local diagnostics skipped an invalid stage identifier")
            return
        event: dict[str, Any] = {
            "sequence": len(self.events) + 1,
            "stage_id": stage_id,
            "parent_stage_id": self.events[-1]["stage_id"] if self.events else None,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }
        if input_text is not None:
            event.update(
                input_sha256=_sha256(input_text),
                input_char_count=len(input_text),
                input_estimated_tokens=max(1, (len(input_text) + 3) // 4) if input_text else 0,
            )
            self.write_raw_snapshot(f"{stage_id}.input", input_text)
        if output_text is not None:
            event.update(
                output_sha256=_sha256(output_text),
                output_char_count=len(output_text),
                output_estimated_tokens=max(1, (len(output_text) + 3) // 4) if output_text else 0,
            )
            self.write_raw_snapshot(stage_id, output_text)
        if source_branch is not None:
            event["source_branch"] = source_branch
        if status is not None:
            event["status"] = status
        event.update(self._safe_metadata(metadata or {}))
        self.events.append(event)

    def set_claim_status(self, claim_id: str, status: str) -> None:
        if not _SAFE_STAGE.fullmatch(claim_id) or status not in _CLAIM_STATUSES:
            log.warning("local diagnostics skipped an invalid claim status")
            return
        self.claim_status[claim_id] = status

    def write_raw_snapshot(self, stage_id: str, content: str) -> None:
        if not self.raw_snapshots_enabled or self.raw_snapshot_dir is None:
            return
        if not _SAFE_STAGE.fullmatch(stage_id):
            return
        try:
            self.raw_snapshot_dir.mkdir(parents=True, exist_ok=True)
            (self.raw_snapshot_dir / f"{stage_id}.txt").write_text(content, encoding="utf-8")
        except Exception as exc:  # noqa: BLE001 - tracing is explicitly fail-soft
            log.warning("local diagnostic raw snapshot write failed ({})", type(exc).__name__)

    def redacted_manifest(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "run_id": self.run_id,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "metadata": dict(self.metadata),
            "events": [dict(event) for event in self.events],
            "claim_status": dict(self.claim_status),
        }

    def write_redacted_manifest(self, path: Path) -> bool:
        try:
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(self.redacted_manifest(), ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            return True
        except Exception as exc:  # noqa: BLE001 - tracing is explicitly fail-soft
            log.warning("local diagnostic manifest write failed ({})", type(exc).__name__)
            return False
