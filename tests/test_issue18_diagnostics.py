from __future__ import annotations

import json

import pytest

from backend.services.local_pipeline_diagnostics import LocalPipelineDiagnosticRecorder


REQUIRED_EVENTS = [
    "pipeline.start",
    "extraction.chunk.1.input",
    "extraction.chunk.1.raw",
    "extraction.chunk.1.cleaned",
    "consolidation.input",
    "consolidation.output",
    "final.input",
    "final.raw",
    "final.cleaned",
    "final.finalized",
    "final.validation",
    "refinement.round.1.input",
    "refinement.round.1.raw",
    "refinement.round.1.cleaned",
    "refinement.round.1.finalized",
    "refinement.round.1.validation",
    "refinement.round.1.accepted_or_discarded",
    "selection.final",
    "pipeline.end",
]


def test_recorder_emits_redacted_ordered_events_and_exact_source_branch(tmp_path):
    recorder = LocalPipelineDiagnosticRecorder(
        run_id="unit-safe-run",
        raw_snapshot_dir=tmp_path / "raw",
        raw_snapshots_enabled=True,
        metadata={"model_key": "safe-model-key", "context_length": 32000},
    )

    recorder.record("pipeline.start", input_text="private transcript", source_branch="source")
    recorder.record("final.input", input_text="private prompt and transcript", source_branch="notes_only")
    recorder.record("final.raw", output_text="private generated text", source_branch="notes_only")
    recorder.record("final.cleaned", output_text="clean text", source_branch="notes_only")
    recorder.record("final.cleaned.copy", output_text="clean text", source_branch="notes_only")
    recorder.set_claim_status("claim-1", "CORRECT")
    recorder.record("pipeline.end", status="complete")

    manifest = recorder.redacted_manifest()
    assert [event["stage_id"] for event in manifest["events"]] == [
        "pipeline.start", "final.input", "final.raw", "final.cleaned", "final.cleaned.copy", "pipeline.end"
    ]
    assert manifest["events"][1]["source_branch"] == "notes_only"
    assert manifest["events"][2]["source_branch"] == "notes_only"
    assert manifest["events"][1]["input_sha256"] != manifest["events"][2]["output_sha256"]
    assert manifest["events"][3]["output_sha256"] == manifest["events"][4]["output_sha256"]
    assert manifest["claim_status"] == {"claim-1": "CORRECT"}
    serialized = json.dumps(manifest, ensure_ascii=False)
    for secret in ("private transcript", "private prompt", "private generated text"):
        assert secret not in serialized
    assert (tmp_path / "raw" / "final.raw.txt").read_text() == "private generated text"


def test_disabled_recorder_writes_no_raw_content_and_writer_failure_is_fail_soft(tmp_path, monkeypatch):
    recorder = LocalPipelineDiagnosticRecorder(
        run_id="disabled-run", raw_snapshot_dir=tmp_path / "raw", raw_snapshots_enabled=False
    )
    recorder.record("final.raw", output_text="sensitive")
    recorder.write_raw_snapshot("final.raw", "sensitive")
    assert not (tmp_path / "raw").exists()

    enabled = LocalPipelineDiagnosticRecorder(
        run_id="failed-writer-run", raw_snapshot_dir=tmp_path / "raw", raw_snapshots_enabled=True
    )

    def fail_write(*_args, **_kwargs):
        raise OSError("disk unavailable")

    monkeypatch.setattr("pathlib.Path.write_text", fail_write)
    enabled.record("final.raw", output_text="still returned to caller")
    assert enabled.redacted_manifest()["events"][0]["stage_id"] == "final.raw"


def test_ollama_raw_capture_precedes_provider_cleaning(monkeypatch):
    from unittest.mock import AsyncMock

    from backend.services.summarization import SummarizationService

    service = SummarizationService()
    raw = "OK, 來源原文"
    monkeypatch.setattr(service, "_get_ollama_client", AsyncMock(return_value=object()))
    monkeypatch.setattr(service, "_get_effective_model", lambda: "safe-model")
    monkeypatch.setattr(service, "_post_ollama_chat", AsyncMock(return_value=(raw, {}, False)))
    collected = []

    import asyncio

    cleaned = asyncio.run(
        service._summarize_with_ollama(
            "system", "message", num_predict=32, context_window_tokens=512,
            expand_output_budget=False, raw_output_collector=collected,
        )
    )
    assert collected == [raw]
    assert cleaned != raw


def test_diagnostic_runner_rejects_nonignored_root_and_requires_claim_contract(tmp_path, monkeypatch):
    import subprocess

    from scripts.e2e.diagnose_local_fidelity import assert_gitignored, read_claim_spec

    monkeypatch.setattr(
        subprocess, "run", lambda *_args, **_kwargs: subprocess.CompletedProcess([], 1)
    )
    with pytest.raises(RuntimeError, match="not gitignored"):
        assert_gitignored(tmp_path / "unsafe")

    claim_path = tmp_path / "claim.json"
    claim_path.write_text('{"claim_id":"c1"}', encoding="utf-8")
    with pytest.raises(ValueError, match="missing required fields"):
        read_claim_spec(claim_path)


def test_claim_stage_evidence_is_hash_linked_and_contains_only_categories():
    from scripts.e2e.write_claim_stage_evidence import build_evidence

    claim = {
        "claim_id": "safe-claim-id",
        "claim_type": "attribution",
        "source_anchor": "00:06:56; transcript speaker index 3",
        "expected_relation": "private semantic description",
    }
    manifest = {
        "run_id": "safe-run-id",
        "metadata": {"claim_id": "safe-claim-id"},
        "events": [
            {"sequence": 2, "stage_id": "extraction.chunk.1.raw", "input_sha256": "a" * 64, "output_sha256": "b" * 64},
            {"sequence": 3, "stage_id": "final.raw", "input_sha256": "c" * 64, "output_sha256": "d" * 64},
            {"sequence": 4, "stage_id": "selection.final", "input_sha256": "e" * 64, "output_sha256": "f" * 64},
        ],
    }
    evidence = build_evidence(manifest, claim, [
        {"stage_id": "selection.final", "status": "MISSING"},
        {"stage_id": "final.raw", "status": "MISSING"},
        {"stage_id": "extraction.chunk.1.raw", "status": "DISTORTED"},
        {"stage_id": "source", "status": "CORRECT"},
    ])

    assert evidence["first_divergence_stage"] == "extraction.chunk.1.raw"
    assert evidence["final_delivery_status"] == "MISSING"
    assert evidence["stages"][1]["output_sha256"] == "b" * 64
    assert "private semantic description" not in json.dumps(evidence)

    with pytest.raises(ValueError, match="selection.final"):
        build_evidence(manifest, claim, [
            {"stage_id": "source", "status": "CORRECT"},
            {"stage_id": "extraction.chunk.1.raw", "status": "DISTORTED"},
        ])

    duplicated_manifest = {**manifest, "events": manifest["events"] + [manifest["events"][0]]}
    with pytest.raises(ValueError, match="unique"):
        build_evidence(duplicated_manifest, claim, [
            {"stage_id": "source", "status": "CORRECT"},
            {"stage_id": "selection.final", "status": "MISSING"},
        ])

    expanded_manifest = {**manifest, "events": manifest["events"] + [
        {"sequence": 5, "stage_id": "final.cleaned", "input_sha256": "1" * 64, "output_sha256": "2" * 64},
    ]}
    with pytest.raises(ValueError, match="omit required"):
        build_evidence(expanded_manifest, claim, [
            {"stage_id": "source", "status": "CORRECT"},
            {"stage_id": "extraction.chunk.1.raw", "status": "DISTORTED"},
            {"stage_id": "final.raw", "status": "MISSING"},
            {"stage_id": "selection.final", "status": "MISSING"},
        ])

    duplicate_sequence = {**manifest, "events": [
        *manifest["events"],
        {"sequence": 4, "stage_id": "final.cleaned", "output_sha256": "1" * 64},
    ]}
    with pytest.raises(ValueError, match="sequences must be unique"):
        build_evidence(duplicate_sequence, claim, [
            {"stage_id": "source", "status": "CORRECT"},
            {"stage_id": "extraction.chunk.1.raw", "status": "DISTORTED"},
            {"stage_id": "final.raw", "status": "MISSING"},
            {"stage_id": "selection.final", "status": "MISSING"},
        ])


def test_pipeline_trace_covers_required_stage_order_and_neutral_default(monkeypatch, tmp_path):
    from unittest.mock import AsyncMock, Mock

    from backend.core.config import settings
    from backend.services.summarization import LocalContextPlan, SummarizationService

    service = SummarizationService()
    plan = LocalContextPlan(
        context_window_tokens=8192,
        estimated_transcript_tokens=6000,
        chunk_input_budget_tokens=1200,
        merge_input_budget_tokens=1500,
        merge_visible_target_tokens=900,
        merge_provider_output_tokens=3072,
        needs_chunking=True,
        estimated_chunk_count=2,
    )
    notes = "筆記"
    initial = "# 標題\n過短"
    refined = "會議名稱：x\n\n一、測試紀錄\n（二）議題\n1. 已確認項目。\n" + "內容。" * 200
    responses = iter([notes, notes, notes, initial, refined])
    monkeypatch.setattr(service, "_select_local_engine", AsyncMock(return_value="ollama"))
    monkeypatch.setattr(service, "_effective_context_tokens", Mock(return_value=32000))
    monkeypatch.setattr(service, "_build_local_context_plan", Mock(return_value=plan))
    monkeypatch.setattr(service, "_split_transcript_into_chunks", Mock(return_value=["chunk-1", "chunk-2"]))
    monkeypatch.setattr(service, "_validate_summary_quality", Mock(side_effect=[["test issue"], []]))
    monkeypatch.setattr(
        service,
        "_generate_with_local_engine",
        AsyncMock(side_effect=lambda *_args, **_kwargs: next(responses)),
    )

    recorder = LocalPipelineDiagnosticRecorder(
        run_id="pipeline-run", raw_snapshot_dir=tmp_path / "raw", raw_snapshots_enabled=False
    )
    result = __import__("asyncio").run(
        service._summarize_with_local_pipeline(
            "fixed source", settings.DEFAULT_SYSTEM_PROMPT, diagnostic_recorder=recorder
        )
    )
    assert result
    stages = [event["stage_id"] for event in recorder.redacted_manifest()["events"]]
    positions = [stages.index(stage) for stage in REQUIRED_EVENTS]
    assert positions == sorted(positions)
    generation_events = [
        event for event in recorder.redacted_manifest()["events"]
        if event["stage_id"].endswith((".input", ".raw", ".cleaned", ".finalized"))
    ]
    for event in generation_events:
        expected_branch = (
            "transcript_chunk"
            if event["stage_id"].startswith("extraction.")
            else "notes_plus_transcript"
            if event["stage_id"].startswith(("final.", "refinement."))
            else "notes_only"
        )
        assert event["source_branch"] == expected_branch
    assert not (tmp_path / "raw").exists()

    responses_without_trace = iter([notes, notes, notes, initial, refined])
    generator_without_trace = AsyncMock(side_effect=lambda *_args, **_kwargs: next(responses_without_trace))
    monkeypatch.setattr(service, "_generate_with_local_engine", generator_without_trace)
    monkeypatch.setattr(service, "_validate_summary_quality", Mock(side_effect=[["test issue"], []]))
    without_trace = __import__("asyncio").run(
        service._summarize_with_local_pipeline("fixed source", settings.DEFAULT_SYSTEM_PROMPT)
    )
    assert without_trace == result
    assert generator_without_trace.await_count == 5


def test_local_final_generation_receives_source_when_the_effective_context_fits(monkeypatch):
    from unittest.mock import AsyncMock, Mock

    from backend.core.config import settings
    from backend.core.templates import get_template
    from backend.services.summarization import LocalContextPlan, SummarizationService

    service = SummarizationService()
    source = "[source-anchor] 因果關係 A 導致 B。"
    extracted_notes = "[source-anchor] 因果關係 B 導致 A。"
    plan = LocalContextPlan(
        context_window_tokens=32000,
        estimated_transcript_tokens=100,
        chunk_input_budget_tokens=8000,
        merge_input_budget_tokens=8000,
        merge_visible_target_tokens=4096,
        merge_provider_output_tokens=3072,
        needs_chunking=False,
        estimated_chunk_count=1,
    )
    corrected_final = "會議紀錄：因果關係 A 導致 B。"
    generator = AsyncMock(side_effect=[extracted_notes, corrected_final])
    monkeypatch.setattr(service, "_select_local_engine", AsyncMock(return_value="ollama"))
    monkeypatch.setattr(service, "_effective_context_tokens", Mock(return_value=32000))
    monkeypatch.setattr(service, "_build_local_context_plan", Mock(return_value=plan))
    monkeypatch.setattr(service, "_split_transcript_into_chunks", Mock(return_value=[source]))
    monkeypatch.setattr(service, "_validate_summary_quality", Mock(return_value=[]))
    monkeypatch.setattr(service, "_generate_with_local_engine", generator)

    recorder = LocalPipelineDiagnosticRecorder(run_id="source-grounding")
    result = __import__("asyncio").run(
        service._summarize_with_local_pipeline(
            source,
            settings.DEFAULT_SYSTEM_PROMPT,
            template=get_template("section_meeting"),
            diagnostic_recorder=recorder,
        )
    )

    assert "因果關係 A 導致 B" in result
    final_message = generator.await_args_list[1].args[2]
    assert source in final_message
    final_input_event = next(
        event for event in recorder.redacted_manifest()["events"]
        if event["stage_id"] == "final.input"
    )
    assert final_input_event["source_branch"] == "notes_plus_transcript"


def test_local_source_grounding_uses_complete_ranked_excerpt_or_explicit_notes_fallback():
    from backend.services.summarization import SummarizationService

    service = SummarizationService()
    transcript = "source-window-one " * 120 + "[00:06:56] 發言者3：內稽前整理物品。"
    message = "內稽前整理物品 [00:06:56]"
    excerpted, branch, excerpt_count = service._resolve_local_source_grounding_message(
        message,
        transcript=transcript,
        source_chunks=["unrelated source " * 20, "[00:06:56] 發言者3：內稽前整理物品。"],
        system_prompt="system",
        relevance_text=message,
        context_window_tokens=200,
        output_budget_tokens=16,
    )
    assert branch == "notes_plus_source_excerpt"
    assert excerpt_count == 1
    assert "[00:06:56] 發言者3：內稽前整理物品。" in excerpted
    assert "source-window-one" not in excerpted

    fallback, branch, excerpt_count = service._resolve_local_source_grounding_message(
        "notes",
        transcript="very long source " * 100,
        source_chunks=["very long source " * 100],
        system_prompt="system",
        relevance_text="unrelated",
        context_window_tokens=16,
        output_budget_tokens=16,
    )
    assert fallback == "notes"
    assert branch == "notes_only"
    assert excerpt_count == 0
