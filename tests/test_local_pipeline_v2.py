"""Fail-first synthetic A-I coverage for the opt-in V2 contract."""

import hashlib
import json
from types import SimpleNamespace

import pytest

from backend.core.config import settings
from backend.services.summarization import SummarizationService
from backend.services.local_pipeline_v2 import (
    ClaimStatus, EvidenceSpan, FactClaim, FactLedger, LocalPipelineV2Error,
    QualityPolicy, SectionPlan, assemble_sections, build_evidence_spans,
    consolidate_claims, explicit_pipeline_version, guarded_section_patch,
    parse_fact_payload, plan_sections, render_section, snapshot_section,
    fidelity_firewall,
    candidate_runtime_profiles, summarize_profile_samples, template_section_titles,
    validate_runtime_profile, ModelRuntimeProfile, parse_section_render_payload,
    validate_asserted_claims_against_source, validate_relation_metadata,
    template_section_plans, RelationMetadata, relation_is_supported_in_order,
    select_profile_candidate, sample_candidate_profiles,
)
from backend.core.templates import get_template
from backend.services.local_pipeline_diagnostics import LocalPipelineDiagnosticRecorder


def _claim(cid="c1", *, object="完成", refs=("span-1",), **kwargs):
    values = {"subject": "團隊", "predicate": "決定", "object": object,
              "evidence_refs": refs, **kwargs}
    return FactClaim(claim_id=cid, **values)


def test_a_causal_direction_is_typed_and_preserved():
    claim = _claim(relation_type="causal", subject="預算", predicate="導致", object="延後")
    assert claim.relation_type.value == "causal"
    assert claim.object == "延後"


def test_b_negation_and_condition_are_not_lost():
    claim = _claim(polarity="negative", condition="若未核准")
    assert claim.polarity == "negative"
    assert claim.condition == "若未核准"


def test_c_number_date_attribution_and_uncertainty_are_structured():
    claim = _claim(number=12, unit="件", date="2026-09-24", attribution="主席", uncertainty="ambiguous")
    assert (claim.number, claim.unit, claim.date, claim.attribution, claim.uncertainty) == (12, "件", "2026-09-24", "主席", "ambiguous")


def test_d_corrected_text_never_changes_source_hash():
    raw = "原始文字"
    span = EvidenceSpan.from_source("span-1", raw, corrected_text="修正文字")
    assert span.source_sha256 == hashlib.sha256(raw.encode()).hexdigest()
    assert span.raw_text != span.corrected_text


def test_e_unverified_claim_without_evidence_is_rejected():
    with pytest.raises(ValueError):
        _claim(refs=())


def test_f_strict_json_and_single_shape_validation():
    payload = json.dumps({"claims": [{"claim_id": "c1", "subject": "甲", "predicate": "做", "object": "乙", "evidence_refs": ["span-1"]}]})
    ledger = parse_fact_payload(payload, source_sha256="a" * 64)
    assert isinstance(ledger, FactLedger)
    with pytest.raises(ValueError, match="invalid JSON"):
        parse_fact_payload("not-json", source_sha256="a" * 64)


def test_g_overlap_dedupe_and_same_evidence_conflict_are_explicit():
    same = _claim("a")
    duplicate = _claim("b")
    ledger = consolidate_claims([same, duplicate], source_sha256="a" * 64)
    assert len(ledger.claims) == 1
    conflict = consolidate_claims([_claim("a", object="甲"), _claim("b", object="乙")], source_sha256="a" * 64)
    assert len(conflict.conflicts) == 1


def test_h_section_render_is_allow_listed_and_traceable():
    claim = _claim()
    plan = SectionPlan(section_id="s", title="決議", required_claim_ids=(claim.claim_id,))
    rendered = render_section(plan, {claim.claim_id: claim})
    assert "團隊決定完成" in rendered
    assert "span-1" in rendered
    assert "not-allowed" not in rendered
    assert fidelity_firewall(plan, rendered, {claim.claim_id: claim}, {"span-1": EvidenceSpan.from_source("span-1", "團隊決定完成")}).accepted


def test_i_patch_rolls_back_when_quality_regresses_and_version_is_explicit():
    claim = _claim()
    plan = SectionPlan(section_id="s", title="決議", required_claim_ids=(claim.claim_id,))
    evidence = {"span-1": EvidenceSpan.from_source("span-1", "來源")}
    before = snapshot_section(plan, render_section(plan, {"c1": claim}), {"c1": claim}, evidence, policy=QualityPolicy())
    after = before.model_copy(update={"covered_claim_ids": (), "source_trace_complete": False})
    result = guarded_section_patch("old", "unsafe", before, after)
    assert result.rolled_back and result.text == "old"
    assert explicit_pipeline_version(None) == "v1"
    with pytest.raises(ValueError):
        explicit_pipeline_version("automatic")


def test_template_plans_and_runtime_controls_are_explicit():
    titles = template_section_titles()
    assert tuple(titles)[:7] == tuple(f"header-{i}" for i in range(1, 8))
    assert "required_section_patterns" not in titles
    profile = candidate_runtime_profiles("Qwen", "qwen3.8-27b-splash", "lmstudio")[0]
    checked = validate_runtime_profile(profile, {"temperature": True, "top_p": True, "top_k": False})
    assert "top_k" in checked.unsupported_controls
    assert "top_p" in checked.supported_controls
    assert summarize_profile_samples([{"score": 0.8}, {"score": 0.9}, {"score": 0.7, "hard_fail": 1}])["worst"] == 0.7


def test_template_plan_follows_header_section_subfield_topology_and_assigns_claim_once():
    template = get_template("general")
    evidence = {"span-1": EvidenceSpan.from_source("span-1", "未能提供簽到人員，故延後。")}
    claim = _claim("c1", subject="簽到人員", predicate="導致", object="延後",
                   relation_type="causal")
    ledger = FactLedger(source_sha256="a" * 64, claims=(claim,))
    plans = template_section_plans(template, ledger, evidence)
    assert plans[0].template_kind == "header"
    assert plans[0].template_path == "record_header_fields[0]"
    assert plans[7].template_path == "record_sections[0]"
    discussion = next(p for p in plans if p.template_path == "record_sections[1]")
    subfields = [p for p in plans if p.template_kind == "subfield" and p.parent_section_id == discussion.section_id]
    assert [p.parent_section_id for p in subfields] == [discussion.section_id] * len(subfields)
    assert sum("c1" in p.required_claim_ids for p in plans) == 1
    assert plans == tuple(sorted(plans, key=lambda p: p.template_order))


def test_section_render_envelope_keeps_identity_outside_prose():
    plan = SectionPlan(section_id="s", title="決議", required_claim_ids=("c1",))
    relation = {"subject": "甲", "predicate": "導致", "object": "延後",
                "direction": "subject_to_object", "polarity": "positive",
                "condition": None, "relation_type": "causal"}
    text, ids, metadata = parse_section_render_payload(
        json.dumps({"text": "決議", "claim_ids": ["c1"], "relation_metadata": {"c1": relation}}),
        plan=plan,
    )
    assert text == "決議" and ids == ("c1",) and metadata["c1"].predicate == "導致"


def test_high_risk_asserted_fields_require_ordered_raw_source():
    claim = _claim(relation_type="causal", predicate="導致", object="延後", number=12, unit="件")
    evidence = {"span-1": EvidenceSpan.from_source("span-1", "團隊導致延後。")}
    with pytest.raises(ValueError, match="source-grounded"):
        validate_asserted_claims_against_source((claim,), evidence)


def test_core_relation_metadata_requires_exact_claim_and_predicate():
    claim = _claim(relation_type="causal", predicate="導致", object="完成")
    plan = SectionPlan(section_id="s", title="決議", required_claim_ids=("c1",))
    expected = RelationMetadata(subject=claim.subject, predicate=claim.predicate,
                                object=claim.object, direction=claim.direction,
                                polarity=claim.polarity, condition=claim.condition,
                                relation_type=claim.relation_type)
    with pytest.raises(ValueError, match="relation metadata"):
        validate_relation_metadata(plan, {"c1": claim}, {})
    with pytest.raises(ValueError, match="relation metadata"):
        validate_relation_metadata(plan, {"c1": claim}, {"wrong": expected})
    validate_relation_metadata(plan, {"c1": claim}, {"c1": expected})
    with pytest.raises(ValueError, match="relation metadata"):
        validate_relation_metadata(plan, {"c1": claim}, {"c1": expected.model_copy(update={"direction": "object_to_subject"})})


def test_firewall_checks_every_required_relation_not_only_selected_claim():
    c1 = _claim("c1", subject="預算", predicate="導致", object="延後",
                relation_type="causal", refs=("span-1",))
    c2 = _claim("c2", subject="人力", predicate="造成", object="延期",
                relation_type="causal", refs=("span-2",))
    plan = SectionPlan(section_id="s", title="決議", required_claim_ids=("c1", "c2"))
    claims = {claim.claim_id: claim for claim in (c1, c2)}
    evidence = {
        "span-1": EvidenceSpan.from_source("span-1", "預算導致延後", start_offset=0, end_offset=6),
        "span-2": EvidenceSpan.from_source("span-2", "人力造成延期", start_offset=7, end_offset=13),
    }
    metadata = {
        cid: RelationMetadata(subject=claim.subject, predicate=claim.predicate,
                              object=claim.object, direction=claim.direction,
                              polarity=claim.polarity, condition=claim.condition,
                              relation_type=claim.relation_type)
        for cid, claim in claims.items()
    }
    metadata["c2"] = metadata["c2"].model_copy(update={"predicate": "避免"})
    rendered = "預算導致延後〔span-1〕；人力避免延期〔span-2〕"
    snapshot = fidelity_firewall(plan, rendered, claims, evidence,
                                 selected_claim_id="c1", relation_metadata=metadata)
    assert "c2" in snapshot.relation_issues
    assert not snapshot.accepted


def test_relation_source_order_uses_ordered_offsets_not_reference_sorting():
    left = EvidenceSpan.from_source("left", "預算", start_offset=10, end_offset=12)
    right = EvidenceSpan.from_source("right", "導致延後", start_offset=12, end_offset=16)
    claim = _claim(subject="預算", predicate="導致", object="延後", relation_type="causal",
                   refs=("left", "right"))
    assert relation_is_supported_in_order(claim, (left, right))
    assert not relation_is_supported_in_order(claim, (right, left))


@pytest.mark.asyncio
async def test_live_c1_inverted_predicate_is_rejected_at_v2_boundary(monkeypatch):
    """Stage05 C1 regression: the live V2 gate must reject predicate flips."""
    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_PIPELINE_VERSION", "v2")
    monkeypatch.setattr(service, "_select_local_engine", lambda: _async_value("fake"))

    async def inverted_generation(*_args, **_kwargs):
        return json.dumps({
            "claims": [{
                "claim_id": "selected-causal",
                "subject": "預算",
                "predicate": "避免",
                "object": "延後",
                "relation_type": "causal",
                "evidence_refs": ["span-1"],
            }]
        })

    monkeypatch.setattr(service, "_generate_with_local_engine", inverted_generation)
    with pytest.raises(LocalPipelineV2Error, match="fidelity firewall"):
        await service._summarize_with_local_pipeline_v2(
            "預算導致延後。", "system", template=None
        )


@pytest.mark.parametrize("candidate_mode", ("inversion", "omission"))
@pytest.mark.asyncio
async def test_live_c1_unsafe_render_rolls_back_to_source_grounded_baseline(monkeypatch, candidate_mode):
    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_PIPELINE_VERSION", "v2")
    monkeypatch.setattr(service, "_select_local_engine", lambda: _async_value("fake"))
    async def generation(_engine, _system, message, **_kwargs):
        if "SOURCE CHUNK" in message:
            return json.dumps({"claims": [{
                "claim_id": "c1", "subject": "預算", "predicate": "導致", "object": "延後",
                "relation_type": "causal", "evidence_refs": ["span-1"],
            }]})
        ids_match = __import__("re").search(r'REQUIRED_CLAIM_IDS: (\[[^\n]*\])', message)
        ids = json.loads(ids_match.group(1)) if ids_match else []
        if candidate_mode == "omission" and "c1" in ids:
            return json.dumps({"text": "決議未列該關係", "claim_ids": [], "relation_metadata": {}})
        relation_metadata = {"c1": {"subject": "預算", "predicate": "避免", "object": "延後",
                                     "direction": "subject_to_object", "polarity": "positive",
                                     "condition": None, "relation_type": "causal"}} if "c1" in ids else {}
        return json.dumps({"text": "預算避免延後〔span-1〕", "claim_ids": ids,
                           "relation_metadata": relation_metadata})
    monkeypatch.setattr(service, "_generate_with_local_engine", generation)
    result = await service._summarize_with_local_pipeline_v2("預算導致延後。", "system", template=None)
    assert "預算導致延後" in result
    assert "預算避免延後" not in result


@pytest.mark.parametrize("candidate_fault", ("wrong_predicate", "missing_id", "reordered_ids"))
@pytest.mark.asyncio
async def test_live_required_relation_metadata_and_ids_are_complete_for_every_claim(monkeypatch, candidate_fault):
    from backend.services import local_pipeline_v2 as v2

    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_PIPELINE_VERSION", "v2")
    monkeypatch.setattr(service, "_select_local_engine", lambda: _async_value("fake"))
    monkeypatch.setattr(v2, "template_section_plans", lambda _template, _ledger, _evidence: (
        SectionPlan(section_id="relations", title="關係", required_claim_ids=("c1", "c2")),
    ))

    async def generation(_engine, _system, message, **_kwargs):
        if "SOURCE CHUNK" in message:
            return json.dumps({"claims": [
                {"claim_id": "c1", "subject": "預算", "predicate": "導致", "object": "延後",
                 "relation_type": "causal", "evidence_refs": ["span-1"]},
                {"claim_id": "c2", "subject": "人力", "predicate": "造成", "object": "延期",
                 "relation_type": "causal", "evidence_refs": ["span-1"]},
            ]})
        ids_match = __import__("re").search(r'REQUIRED_CLAIM_IDS: (\[[^\n]*\])', message)
        ids = json.loads(ids_match.group(1)) if ids_match else []
        if candidate_fault == "missing_id":
            ids = ["c1"]
        elif candidate_fault == "reordered_ids":
            ids = ["c2", "c1"]
        relation_metadata = {
            "c1": {"subject": "預算", "predicate": "導致", "object": "延後",
                   "direction": "subject_to_object", "polarity": "positive",
                   "condition": None, "relation_type": "causal"},
            "c2": {"subject": "人力", "predicate": "避免" if candidate_fault == "wrong_predicate" else "造成", "object": "延期",
                   "direction": "subject_to_object", "polarity": "positive",
                   "condition": None, "relation_type": "causal"},
        }
        return json.dumps({"text": "預算導致延後〔span-1〕；人力避免延期〔span-1〕",
                           "claim_ids": ids, "relation_metadata": relation_metadata})

    monkeypatch.setattr(service, "_generate_with_local_engine", generation)
    result = await service._summarize_with_local_pipeline_v2("預算導致延後；人力造成延期。", "system")
    assert "預算導致延後" in result
    assert "人力造成延期" in result
    assert "人力避免延期" not in result


@pytest.mark.asyncio
async def test_live_final_firewall_rejects_relation_moved_to_another_section(monkeypatch):
    from backend.services import local_pipeline_v2 as v2

    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_PIPELINE_VERSION", "v2")
    monkeypatch.setattr(service, "_select_local_engine", lambda: _async_value("fake"))
    monkeypatch.setattr(v2, "template_section_plans", lambda _template, _ledger, _evidence: (
        SectionPlan(section_id="s0", title="第一節", required_claim_ids=("c1",), template_order=0),
        SectionPlan(section_id="s1", title="第二節", required_claim_ids=("c2",), template_order=1),
    ))
    original = "預算導致延後〔span-1〕"

    async def generation(_engine, _system, message, **_kwargs):
        if "SOURCE CHUNK" in message:
            return json.dumps({"claims": [
                {"claim_id": "c1", "subject": "預算", "predicate": "導致", "object": "延後",
                 "relation_type": "causal", "evidence_refs": ["span-1"]},
                {"claim_id": "c2", "subject": "人力", "predicate": "造成", "object": "延期",
                 "relation_type": "causal", "evidence_refs": ["span-1"]},
            ]})
        ids_match = __import__("re").search(r'REQUIRED_CLAIM_IDS: (\[[^\n]*\])', message)
        ids = json.loads(ids_match.group(1)) if ids_match else []
        relation_metadata = {
            "c1": {"subject": "預算", "predicate": "導致", "object": "延後",
                   "direction": "subject_to_object", "polarity": "positive", "condition": None, "relation_type": "causal"},
            "c2": {"subject": "人力", "predicate": "造成", "object": "延期",
                   "direction": "subject_to_object", "polarity": "positive", "condition": None, "relation_type": "causal"},
        }
        text = original if "c1" in ids else "人力造成延期〔span-1〕"
        return json.dumps({"text": text, "claim_ids": ids, "relation_metadata": relation_metadata})

    def move_first_section_relation(marked_text, template=None):
        first_start = marked_text.index(":0:開始】")
        first_end = marked_text.index(":0:結束】", first_start)
        first_body_start = marked_text.index("\n", first_start) + 1
        moved = marked_text[first_body_start:first_end].strip()
        without_first = marked_text[:first_body_start] + marked_text[first_end:]
        second_start = without_first.index(":1:開始】")
        insertion = without_first.index("\n", second_start) + 1
        return without_first[:insertion] + moved + "；" + without_first[insertion:]

    monkeypatch.setattr(service, "_generate_with_local_engine", generation)
    monkeypatch.setattr(service, "_finalize_record_text", move_first_section_relation)
    with pytest.raises(LocalPipelineV2Error, match="final assembly"):
        await service._summarize_with_local_pipeline_v2("預算導致延後；人力造成延期。", "system")


@pytest.mark.parametrize("mutation", ("delete", "duplicate", "reorder", "interleaved"))
@pytest.mark.asyncio
async def test_live_final_firewall_fails_closed_on_corrupt_section_markers(monkeypatch, mutation):
    from backend.services import local_pipeline_v2 as v2

    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_PIPELINE_VERSION", "v2")
    monkeypatch.setattr(service, "_select_local_engine", lambda: _async_value("fake"))
    monkeypatch.setattr(v2, "template_section_plans", lambda _template, _ledger, _evidence: (
        SectionPlan(section_id="s0", title="第一節", template_order=0),
        SectionPlan(section_id="s1", title="第二節", template_order=1),
    ))

    async def generation(_engine, _system, message, **_kwargs):
        if "SOURCE CHUNK" in message:
            return json.dumps({"claims": []})
        return json.dumps({"text": "section", "claim_ids": [], "relation_metadata": {}})

    def corrupt_markers(marked_text, template=None):
        if mutation == "delete":
            return marked_text.replace(":0:結束】", "", 1)
        if mutation == "duplicate":
            marker = marked_text.splitlines()[0]
            return marked_text + "\n" + marker
        if mutation == "interleaved":
            markers = __import__("re").findall(r"【V2段界:[^】]+】", marked_text)
            _start0, end0, start1, _end1 = markers
            placeholder = "【V2段界:TEMP:結束】"
            return (marked_text.replace(end0, placeholder, 1)
                    .replace(start1, end0, 1)
                    .replace(placeholder, start1, 1))
        return (marked_text.replace(":0:開始】", ":tmp:開始】")
                .replace(":0:結束】", ":tmp:結束】")
                .replace(":1:開始】", ":0:開始】")
                .replace(":1:結束】", ":0:結束】")
                .replace(":tmp:開始】", ":1:開始】")
                .replace(":tmp:結束】", ":1:結束】"))

    monkeypatch.setattr(service, "_generate_with_local_engine", generation)
    monkeypatch.setattr(service, "_finalize_record_text", corrupt_markers)
    with pytest.raises(LocalPipelineV2Error, match="final assembly"):
        await service._summarize_with_local_pipeline_v2("來源", "system")


@pytest.mark.asyncio
async def test_direct_v2_entry_requires_explicit_v2_pipeline_version(monkeypatch):
    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_PIPELINE_VERSION", "v1")
    monkeypatch.setattr(service, "_select_local_engine", lambda: pytest.fail("engine must not be selected"))
    with pytest.raises(LocalPipelineV2Error, match="requires LOCAL_PIPELINE_VERSION=v2"):
        await service._summarize_with_local_pipeline_v2("source", "system")


@pytest.mark.asyncio
async def test_qwen_live_v2_uses_w7_production_baseline_temperature(monkeypatch):
    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_PIPELINE_VERSION", "v2")
    monkeypatch.setattr(service, "_select_local_engine", lambda: _async_value("lmstudio"))
    service._active_lmstudio_selection = SimpleNamespace(
        model_identifier="qwen3.8-27b", provider="lmstudio", loaded_instance_id="instance-1",
        context_length=8192,
    )
    temperatures = []

    async def generation(_engine, _system, message, **kwargs):
        temperatures.append(kwargs["temperature"])
        if "SOURCE CHUNK" in message:
            return json.dumps({"claims": []})
        return json.dumps({"text": "section", "claim_ids": [], "relation_metadata": {}})

    monkeypatch.setattr(service, "_generate_with_local_engine", generation)
    await service._summarize_with_local_pipeline_v2("短來源", "system", template=get_template("general"))
    assert temperatures
    assert set(temperatures) == {0.7}


@pytest.mark.asyncio
async def test_schema_repair_records_its_actual_request_temperature(monkeypatch):
    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_PIPELINE_VERSION", "v2")
    monkeypatch.setattr(service, "_select_local_engine", lambda: _async_value("fake"))
    extraction_calls = 0
    temperatures = []

    async def generation(_engine, _system, message, **kwargs):
        nonlocal extraction_calls
        temperatures.append(kwargs["temperature"])
        if "SOURCE CHUNK" in message:
            extraction_calls += 1
            if "SCHEMA REPAIR" not in message:
                return "not-json"
            return json.dumps({"claims": []})
        return json.dumps({"text": "section", "claim_ids": [], "relation_metadata": {}})

    monkeypatch.setattr(service, "_generate_with_local_engine", generation)
    recorder = LocalPipelineDiagnosticRecorder(run_id="repair-temperature-test")
    await service._summarize_with_local_pipeline_v2(
        "來源", "system", template=get_template("general"), diagnostic_recorder=recorder,
    )
    repair = next(event for event in recorder.events if event["stage_id"] == "v2.extraction.chunk.1.repair")
    assert repair["temperature"] == 1.0
    assert temperatures and set(temperatures) == {1.0}


@pytest.mark.parametrize("snapshots_enabled", (False, True))
@pytest.mark.asyncio
async def test_v2_generation_outputs_are_opt_in_snapshots_and_manifest_redacted(
    monkeypatch, tmp_path, snapshots_enabled,
):
    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_PIPELINE_VERSION", "v2")
    monkeypatch.setattr(service, "_select_local_engine", lambda: _async_value("fake"))
    generated_sentinel = "PRIVATE_OUTPUT_SENTINEL"

    async def generation(_engine, _system, message, **_kwargs):
        if "SOURCE CHUNK" in message:
            if "SCHEMA REPAIR" not in message:
                return "PRIVATE_BAD_JSON_OUTPUT"
            return json.dumps({"claims": []})
        return json.dumps({"text": generated_sentinel, "claim_ids": [], "relation_metadata": {}})

    monkeypatch.setattr(service, "_generate_with_local_engine", generation)
    raw_dir = tmp_path / "raw"
    recorder = LocalPipelineDiagnosticRecorder(
        run_id=f"generation-output-{snapshots_enabled}", raw_snapshot_dir=raw_dir,
        raw_snapshots_enabled=snapshots_enabled,
    )
    await service._summarize_with_local_pipeline_v2(
        "safe synthetic source", "system", template=get_template("general"), diagnostic_recorder=recorder,
    )

    events = recorder.events
    failed_first_parse = next(event for event in events if event["stage_id"] == "v2.extraction.chunk.1.outcome")
    assert failed_first_parse["status"] == "failed:ValueError"
    assert any(event["stage_id"] == "v2.extraction.chunk.1.repair.output" for event in events)
    assert any(event["stage_id"].startswith("v2.section.") and event["stage_id"].endswith(".output") for event in events)
    assert any(event["stage_id"].startswith("v2.patch.") and event["stage_id"].endswith(".output") for event in events)
    assert any(event["stage_id"] == "v2.selection.final" and "output_sha256" in event for event in events)
    manifest_text = json.dumps(recorder.redacted_manifest(), ensure_ascii=False)
    assert generated_sentinel not in manifest_text
    assert "PRIVATE_BAD_JSON_OUTPUT" not in manifest_text
    if snapshots_enabled:
        assert (raw_dir / "v2.extraction.chunk.1.output.txt").read_text() == "PRIVATE_BAD_JSON_OUTPUT"
        assert (raw_dir / "v2.extraction.chunk.1.repair.output.txt").is_file()
        assert list(raw_dir.glob("v2.section.*.output.txt"))
        assert list(raw_dir.glob("v2.patch.*.output.txt"))
        assert (raw_dir / "v2.selection.final.txt").is_file()
        assert any(generated_sentinel in path.read_text() for path in raw_dir.glob("v2.section.*.output.txt"))
    else:
        assert not raw_dir.exists()


@pytest.mark.asyncio
async def test_v2_failure_diagnostics_keep_error_class_not_message(monkeypatch, tmp_path):
    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_PIPELINE_VERSION", "v2")
    monkeypatch.setattr(service, "_select_local_engine", lambda: _async_value("fake"))

    async def failing_generation(*_args, **_kwargs):
        raise ValueError("PRIVATE_EXCEPTION_MESSAGE")

    monkeypatch.setattr(service, "_generate_with_local_engine", failing_generation)
    recorder = LocalPipelineDiagnosticRecorder(run_id="safe-error-class", raw_snapshot_dir=tmp_path / "raw")
    with pytest.raises(LocalPipelineV2Error):
        await service._summarize_with_local_pipeline_v2(
            "safe synthetic source", "system", template=get_template("general"), diagnostic_recorder=recorder,
        )
    outcomes = [event for event in recorder.events if event["stage_id"].endswith(".outcome")]
    assert [event["status"] for event in outcomes] == ["failed:ValueError", "failed:ValueError"]
    manifest_text = json.dumps(recorder.redacted_manifest(), ensure_ascii=False)
    assert "PRIVATE_EXCEPTION_MESSAGE" not in manifest_text
    assert not (tmp_path / "raw").exists()


@pytest.mark.asyncio
async def test_live_v2_uses_immutable_raw_source_when_corrected_view_is_unaligned(monkeypatch):
    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_PIPELINE_VERSION", "v2")
    monkeypatch.setattr(service, "_select_local_engine", lambda: _async_value("fake"))
    captured = {"extraction": []}
    captured_temperatures = []
    async def generation(_engine, _system, message, **_kwargs):
        captured_temperatures.append((_kwargs.get("temperature"), "SOURCE CHUNK" in message))
        if "SOURCE CHUNK" in message:
            captured["extraction"].append(message)
            return json.dumps({"claims": []})
        return json.dumps({"text": "slot", "claim_ids": [], "relation_metadata": {}})
    monkeypatch.setattr(service, "_generate_with_local_engine", generation)
    recorder = LocalPipelineDiagnosticRecorder(run_id="raw-source-test")
    raw = "原始ASR權威詞"
    corrected = "校正理解替代詞"
    await service._summarize_with_local_pipeline_v2(
        corrected, "system", template=get_template("general"),
        raw_source_transcript=raw, diagnostic_recorder=recorder,
    )
    assert raw in captured["extraction"][0]
    assert corrected not in captured["extraction"][0]
    source_event = next(event for event in recorder.events if event["stage_id"] == "v2.source")
    assert source_event["raw_source_sha256"] == hashlib.sha256(raw.encode()).hexdigest()
    assert source_event["corrected_alignment"] == "unavailable_not_mapped"
    profile_event = next(event for event in recorder.events if event["stage_id"] == "v2.runtime.profile")
    assert profile_event["baseline_temperature"] == 1.0
    assert "temperature" not in profile_event
    extraction_events = [event for event in recorder.events if event["stage_id"].startswith("v2.extraction.chunk.") and event["stage_id"].endswith(".input")]
    section_events = [event for event in recorder.events if event["stage_id"].startswith("v2.section.") and event["stage_id"].endswith(".input")]
    assert extraction_events and all(event["temperature"] == 1.0 for event in extraction_events)
    assert section_events and all(event["temperature"] == 1.0 for event in section_events)
    assert captured_temperatures and {value for value, _ in captured_temperatures} == {1.0}


@pytest.mark.asyncio
async def test_profile_sampler_runs_only_observed_valid_profiles_and_selector_is_fidelity_first():
    candidates = candidate_runtime_profiles("Qwen", "qwen-key", "lmstudio")
    candidates = tuple(validate_runtime_profile(candidate, {
        "temperature": True, "top_p": True, "top_k": True, "thinking": True,
    }) for candidate in candidates)
    calls = []
    async def run_sample(candidate):
        calls.append(candidate.temperature)
        return {"score": candidate.temperature, "hard_fail": 0,
                "causal_errors": 0, "attribution_errors": 0,
                "faithfulness": candidate.temperature, "traceability": 1,
                "completeness": 1, "usability": 1}
    samples = await sample_candidate_profiles(candidates, run_sample, repeats=2)
    assert len(calls) == 6
    selected = select_profile_candidate(candidates, samples)
    assert selected.temperature == 0.7


@pytest.mark.asyncio
async def test_lmstudio_profile_controls_are_transmitted_only_when_supported(monkeypatch):
    service = SummarizationService()
    captured = {}
    class Completion:
        async def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace()
    client = SimpleNamespace(chat=SimpleNamespace(completions=Completion()))
    selection = SimpleNamespace(model_identifier="loaded-key")
    profile = ModelRuntimeProfile(family="Qwen", model_key="loaded-key", provider="lmstudio",
                                  temperature=0.7, top_p=0.8, top_k=20,
                                  supported_controls=("temperature", "top_p", "top_k"),
                                  unsupported_controls=("thinking", "context_length"))
    monkeypatch.setattr(settings, "LOCAL_LLM_TRANSIENT_RETRIES", 0)
    monkeypatch.setattr(settings, "LOCAL_LLM_DISABLE_THINKING", False)
    await service._lmstudio_chat_request(client, selection, [], 0.3, 128, runtime_profile=profile)
    assert captured["temperature"] == 0.3
    assert captured["top_p"] == 0.8
    assert captured["extra_body"]["top_k"] == 20
    assert "context_length" not in captured.get("extra_body", {})
    assert "thinking" not in captured.get("extra_body", {})


@pytest.mark.asyncio
async def test_lmstudio_400_downgrades_only_rejected_control_and_reports_it(monkeypatch):
    service = SummarizationService()
    seen = []
    rejected = []
    class Http400(Exception):
        response = SimpleNamespace(status_code=400)
    class Completion:
        async def create(self, **kwargs):
            seen.append(kwargs)
            if len(seen) == 1:
                raise Http400()
            return SimpleNamespace()
    client = SimpleNamespace(chat=SimpleNamespace(completions=Completion()))
    profile = ModelRuntimeProfile(family="Qwen", model_key="q", provider="lmstudio",
                                  top_p=0.8, top_k=20,
                                  supported_controls=("top_p", "top_k"))
    monkeypatch.setattr(settings, "LOCAL_LLM_TRANSIENT_RETRIES", 0)
    monkeypatch.setattr(settings, "LOCAL_LLM_DISABLE_THINKING", True)
    await service._lmstudio_chat_request(
        client, SimpleNamespace(model_identifier="q"), [], 0.7, 64,
        runtime_profile=profile, runtime_control_rejection_callback=rejected.append,
    )
    assert seen[0]["top_p"] == seen[1]["top_p"] == 0.8
    assert seen[0]["extra_body"] == {"reasoning_effort": "none", "top_k": 20}
    assert seen[1]["extra_body"] == {"reasoning_effort": "none"}
    assert rejected == ["top_k"]


async def _async_value(value):
    return value
