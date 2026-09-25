"""Fail-first synthetic A-I coverage for the opt-in V2 contract."""

import hashlib
import json
from types import SimpleNamespace

import httpx
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
    resolve_claim_occurrences,
    template_claim_policy, inventory_source_candidates,
    cross_section_claim_duplicates, validate_template_terms,
    _number_value_supported,
)
from backend.core.templates import get_template
from backend.services.local_pipeline_diagnostics import LocalPipelineDiagnosticRecorder
from backend.services import local_pipeline_v2 as local_v2


@pytest.fixture(autouse=True)
def _fake_v2_runtime_has_explicit_json_fallback(monkeypatch, request):
    """Keep unit tests source-free; live capability probing has its own contracts."""
    if request.node.originalname in {
        "test_native_schema_probe_uses_exact_fact_schema_and_source_free_active_selection",
        "test_native_schema_probe_only_explicit_unsupported_allows_fallback",
        "test_ollama_native_schema_probe_uses_source_free_native_format_and_effective_model",
        "test_ollama_unknown_schema_probe_stops_before_user_source_and_redacts_diagnostics",
    }:
        return
    async def unsupported_for_fake_runtime(self, _engine, _selection, _profile=None):
        return "UNSUPPORTED"

    monkeypatch.setattr(
        SummarizationService, "_probe_native_schema_capability",
        unsupported_for_fake_runtime, raising=False,
    )


def _claim(cid="c1", *, object="完成", refs=("span-1",), **kwargs):
    subject = kwargs.get("subject", "團隊")
    predicate = kwargs.get("predicate", "決定")
    condition = kwargs.get("condition")
    quote = kwargs.get("evidence_quote", f"{condition or ''}{subject}{predicate}{object}")
    values = {"subject": subject, "predicate": predicate, "object": object,
              "evidence_refs": refs, "evidence_quote": quote,
              "resolved_start_offset": 0, "resolved_end_offset": len(quote), **kwargs}
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


@pytest.mark.parametrize("change", (
    {"direction": "object_to_subject"},
    {"status": ClaimStatus.AMBIGUOUS},
    {"uncertainty": "ambiguous"},
    {"polarity": "negative"},
    {"condition": "若未核准"},
))
def test_ledger_preserves_and_conflicts_semantically_distinct_same_evidence_claims(change):
    first = _claim("c1", subject="預算", predicate="導致", object="延後",
                   relation_type="causal", refs=("span-1",), condition="若核准")
    second = first.model_copy(update={"claim_id": "c2", **change})
    ledger = consolidate_claims((first, second), source_sha256="a" * 64)
    assert len(ledger.claims) == 2
    expected_conflicts = 0 if change.get("status") == ClaimStatus.AMBIGUOUS or change.get("uncertainty") == "ambiguous" else 1
    assert len(ledger.conflicts) == expected_conflicts
    if not expected_conflicts:
        return
    assert ledger.conflicts[0].claim_ids == ("c1", "c2")
    assert ledger.conflicts[0].conflict_type == "same_evidence_semantic_conflict"


def test_ledger_flags_reversed_endpoint_assertions_as_conflict():
    forward = _claim("c1", subject="預算", predicate="導致", object="延後",
                     relation_type="causal", refs=("span-1",))
    reverse = _claim("c2", subject="延後", predicate="導致", object="預算",
                     relation_type="causal", refs=("span-1",))
    ledger = consolidate_claims((forward, reverse), source_sha256="a" * 64)
    assert len(ledger.claims) == 2
    assert len(ledger.conflicts) == 1
    assert ledger.conflicts[0].conflict_type == "same_evidence_semantic_conflict"


def test_occurrence_resolution_and_conflict_identity_use_exact_raw_intervals():
    raw = "甲導致乙；丙造成丁。"
    digest = hashlib.sha256(raw.encode()).hexdigest()
    spans = build_evidence_spans(raw, [raw[:5], raw[5:]], source_sha256=digest,
                                 chunk_offsets=[(0, 5), (5, len(raw))])
    evidence = {span.span_id: span for span in spans}
    left = _claim("left", subject="甲", predicate="導致", object="乙", relation_type="causal",
                  refs=("span-1",), evidence_quote="甲導致乙")
    right = _claim("right", subject="丙", predicate="造成", object="丁", relation_type="causal",
                   refs=("span-2",), evidence_quote="丙造成丁")
    resolved = resolve_claim_occurrences((left, right), evidence, source_sha256=digest)
    assert [(claim.resolved_start_offset, claim.resolved_end_offset) for claim in resolved] == [(0, 4), (5, 9)]
    ledger = consolidate_claims(resolved, source_sha256=digest, evidence=evidence)
    assert not ledger.conflicts

    invalid = _claim("invalid", refs=("missing-span",), evidence_quote="甲導致乙")
    unresolved = resolve_claim_occurrences((invalid,), evidence, source_sha256=digest)[0]
    assert unresolved.status == ClaimStatus.AMBIGUOUS
    assert unresolved.resolved_start_offset is None


def test_repeated_exact_quote_is_ambiguous_not_arbitrarily_resolved():
    raw = "甲導致乙；甲導致乙。"
    span = EvidenceSpan.from_source("span-1", raw, start_offset=0, end_offset=len(raw))
    claim = _claim("repeat", subject="甲", predicate="導致", object="乙", relation_type="causal",
                   evidence_quote="甲導致乙")
    resolved = resolve_claim_occurrences((claim,), {"span-1": span}, source_sha256=span.source_sha256)[0]
    assert resolved.status == ClaimStatus.AMBIGUOUS
    assert resolved.uncertainty == "unresolved_raw_source_occurrence"


def test_unique_exact_relation_recovers_when_small_model_omits_quote():
    raw = "前言。主管裁示資訊科辦理盤點，並於下次會議報告。結尾。"
    span = EvidenceSpan.from_source("span-1", raw, start_offset=0, end_offset=len(raw))
    claim = _claim(
        "recover", subject="資訊科", predicate="辦理", object="盤點",
        refs=("span-1",), evidence_quote=None,
        resolved_start_offset=None, resolved_end_offset=None,
    )
    resolved = resolve_claim_occurrences(
        (claim,), {"span-1": span}, source_sha256=span.source_sha256,
    )[0]
    assert resolved.status == ClaimStatus.ASSERTED
    assert resolved.evidence_quote in raw
    assert resolved.resolved_start_offset is not None
    assert raw[resolved.resolved_start_offset:resolved.resolved_end_offset] == resolved.evidence_quote


def test_unique_occurrence_fallback_refuses_repeated_relation():
    raw = "資訊科辦理盤點。資訊科辦理盤點。"
    span = EvidenceSpan.from_source("span-1", raw, start_offset=0, end_offset=len(raw))
    claim = _claim(
        "repeat-fallback", subject="資訊科", predicate="辦理", object="盤點",
        refs=("span-1",), evidence_quote=None,
        resolved_start_offset=None, resolved_end_offset=None,
    )
    resolved = resolve_claim_occurrences(
        (claim,), {"span-1": span}, source_sha256=span.source_sha256,
    )[0]
    assert resolved.status == ClaimStatus.AMBIGUOUS


def test_materiality_gate_ignores_incidental_numbers_dates_relations_and_speakers():
    raw = "發言者1：閒聊 17 個人、2026-09-25，沒有其他事項。"
    candidates = inventory_source_candidates("general", raw)
    kinds = {kind for kind, _start, _end in candidates}
    assert {"numeric", "date", "speaker", "relation"} <= kinds

    plans = template_section_plans(
        get_template("general"),
        FactLedger(source_sha256=hashlib.sha256(raw.encode()).hexdigest(), claims=()),
        evidence={},
        raw_source=raw,
    )
    assert not any(plan.coverage_issues for plan in plans)


def test_occurrence_resolution_returns_ambiguous_for_offsetless_span():
    raw = "甲導致乙"
    digest = hashlib.sha256(raw.encode()).hexdigest()
    span = EvidenceSpan(span_id="span-offsetless", raw_text=raw, source_sha256=digest)
    claim = _claim("offsetless", subject="甲", predicate="導致", object="乙",
                   relation_type="causal", refs=(span.span_id,), evidence_quote=raw)

    resolved = resolve_claim_occurrences(
        (claim,), {span.span_id: span}, source_sha256=digest,
    )[0]

    assert resolved.status == ClaimStatus.AMBIGUOUS
    assert resolved.resolved_start_offset is None
    assert resolved.resolved_end_offset is None


@pytest.mark.parametrize(("number", "unit", "source", "expected"), (
    (2, "週", "12週", False),
    (1, "週", "10週", False),
    (1, "週", "1.5週", False),
    (2, "週", "2週", True),
    (1, "週", "一週", True),
    (1, "天", "一週", False),
    (1, "週", "一二週", False),
    (1, "週", "一週半", False),
))
def test_numeric_grounding_requires_exact_value_unit_and_unmodified_token(
    number, unit, source, expected,
):
    assert _number_value_supported(number, unit, source) is expected


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
    assert sum("c1" in (*p.required_claim_ids, *p.optional_claim_ids) for p in plans) == 1
    assert plans == tuple(sorted(plans, key=lambda p: p.template_order))


def test_trusted_template_policies_are_source_present_and_candidate_gaps_are_scoped():
    cues = {
        "general": "決議事項",
        "procurement_evaluation": "評選結果",
        "section_meeting": "解除列管",
        "isms_monthly": "風險處理",
    }
    for template_id, cue in cues.items():
        policy = template_claim_policy(template_id)
        assert policy.is_required(f"原文提及{cue}並記錄具體內容")
        assert not policy.is_required("一般背景敘述")
        assert inventory_source_candidates(template_id, f"原文{cue}")

    template = get_template("general")
    raw = "預算導致延後，會議並確認決議事項。"
    digest = hashlib.sha256(raw.encode()).hexdigest()
    span = EvidenceSpan(span_id="span-1", raw_text=raw, start_offset=0,
                        end_offset=len(raw), source_sha256=digest)
    claim = _claim("c1", subject="預算", predicate="導致", object="延後", relation_type="causal",
                   evidence_quote="預算導致延後", resolved_start_offset=0, resolved_end_offset=6)
    plans = template_section_plans(template, FactLedger(source_sha256=digest, claims=(claim,)),
                                   {"span-1": span}, raw_source=raw)
    discussion = next(plan for plan in plans if plan.section_id == "section-2")
    assert discussion.coverage_issues
    assert all("確認決議事項" not in issue for issue in discussion.coverage_issues)


def test_w5_firewall_checks_occurrence_numeric_date_entity_attribution_and_source_tags():
    quote = "主席表示團隊於2026-09-24以12件完成決議"
    claim = _claim("c1", subject="團隊", predicate="完成", object="決議",
                   number=12, unit="件", date="2026-09-24", attribution="主席",
                   evidence_quote=quote, resolved_start_offset=0,
                   resolved_end_offset=len(quote))
    evidence = {"span-1": EvidenceSpan.from_source("span-1", quote)}
    plan = SectionPlan(section_id="s", title="決議", optional_claim_ids=("c1",))

    complete = fidelity_firewall(
        plan, "主席表示團隊於2026-09-24以12件完成決議〔span-1〕",
        {"c1": claim}, evidence,
    )
    assert complete.accepted

    incomplete = fidelity_firewall(
        plan, "團隊完成決議",
        {"c1": claim}, evidence,
    )
    assert incomplete.numeric_issues == ("c1",)
    assert incomplete.date_issues == ("c1",)
    assert incomplete.attribution_issues == ("c1",)
    assert incomplete.source_tag_issues == ("c1",)

    mismatched_entity = claim.model_copy(update={"subject": "廠商"})
    entity_snapshot = fidelity_firewall(
        plan, "廠商完成決議〔span-1〕", {"c1": mismatched_entity}, evidence,
    )
    assert entity_snapshot.entity_issues == ("c1",)

    unanchored = fidelity_firewall(
        plan, "團隊完成決議\n補充〔span-1〕", {"c1": claim}, evidence,
    )
    assert unanchored.source_tag_issues == ("c1",)


def test_w5_source_candidate_offsets_and_record_term_checks_are_deterministic():
    raw = "主席：於2026-09-24決議12件並延後一週"
    candidates = inventory_source_candidates("general", raw)
    assert ("date", raw.index("2026-09-24"), raw.index("2026-09-24") + len("2026-09-24")) in candidates
    assert ("numeric", raw.index("12件"), raw.index("12件") + 2) in candidates
    assert ("numeric", raw.index("一週"), raw.index("一週") + 1) in candidates

    duplicated = cross_section_claim_duplicates((
        SectionPlan(section_id="s1", title="一", optional_claim_ids=("c1",)),
        SectionPlan(section_id="s2", title="二", required_claim_ids=("c1",)),
    ))
    assert duplicated == ("c1",)
    assert validate_template_terms("會議決議事項", ("決議事項", "散會")) == ("散會",)


def test_source_tags_diversify_over_independent_validated_spans():
    c1 = _claim("c1", subject="預算", predicate="導致", object="延後",
                relation_type="causal", evidence_refs=("span-1",), evidence_quote="預算導致延後",
                resolved_start_offset=0, resolved_end_offset=6)
    c2 = _claim("c2", subject="人力", predicate="造成", object="延期",
                relation_type="causal", evidence_refs=("span-2",), evidence_quote="人力造成延期",
                resolved_start_offset=10, resolved_end_offset=16)
    evidence = {
        "span-1": EvidenceSpan.from_source("span-1", "預算導致延後", start_offset=0, end_offset=6),
        "span-2": EvidenceSpan.from_source("span-2", "人力造成延期", start_offset=10, end_offset=16),
    }
    plan = SectionPlan(section_id="s", title="決議", required_claim_ids=("c1", "c2"))
    relations = {
        claim.claim_id: RelationMetadata(
            subject=claim.subject, predicate=claim.predicate, object=claim.object,
            direction=claim.direction, polarity=claim.polarity,
            condition=claim.condition, relation_type=claim.relation_type,
        )
        for claim in (c1, c2)
    }
    snapshot = fidelity_firewall(
        plan, "預算導致延後〔span-1〕；人力造成延期〔span-2〕",
        {"c1": c1, "c2": c2}, evidence, relation_metadata=relations,
    )
    assert snapshot.accepted
    unanchored = fidelity_firewall(
        plan, "預算導致延後〔span-2〕；人力造成延期〔span-1〕",
        {"c1": c1, "c2": c2}, evidence, relation_metadata=relations,
    )
    assert unanchored.source_tag_issues == ("c1", "c2")


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
    claim = _claim(relation_type="causal", predicate="導致", object="延後", number=12, unit="件",
                   evidence_quote="團隊導致延後", resolved_end_offset=6)
    evidence = {"span-1": EvidenceSpan.from_source("span-1", "團隊導致延後。", start_offset=0, end_offset=7)}
    validated = validate_asserted_claims_against_source((claim,), evidence)
    assert validated[0].status == ClaimStatus.AMBIGUOUS
    with pytest.raises(ValueError, match="no unique raw-source occurrence"):
        validate_asserted_claims_against_source(
            (claim.model_copy(update={"resolved_start_offset": None, "resolved_end_offset": None}),), evidence
        )


def test_chinese_single_digit_plus_unit_is_losslessly_grounded_and_rendered():
    quote = "預算增加導致工程延後一週"
    digest = hashlib.sha256(quote.encode()).hexdigest()
    claim = _claim("c1", subject="預算增加", predicate="導致", object="工程延後一週",
                   relation_type="causal", number=1, unit="週", evidence_quote=quote,
                   resolved_start_offset=0, resolved_end_offset=len(quote))
    evidence = {"span-1": EvidenceSpan(span_id="span-1", raw_text=quote, start_offset=0,
                                       end_offset=len(quote), source_sha256=digest)}
    validated = validate_asserted_claims_against_source((claim,), evidence)
    assert validated[0].status == ClaimStatus.ASSERTED
    plan = SectionPlan(section_id="s", title="決議", required_claim_ids=("c1",))
    rendered = "預算增加導致工程延後一週〔span-1〕"
    snapshot = fidelity_firewall(
        plan, rendered, {"c1": validated[0]}, evidence,
        relation_metadata={"c1": RelationMetadata(subject="預算增加", predicate="導致",
            object="工程延後一週", direction="subject_to_object", polarity="positive",
            relation_type="causal")},
    )
    assert snapshot.numeric_issues == ()
    assert snapshot.accepted

    for number, unit in ((2, "週"), (1, "天")):
        changed = claim.model_copy(update={"number": number, "unit": unit})
        unresolved = validate_asserted_claims_against_source((changed,), evidence)
        assert unresolved[0].status == ClaimStatus.AMBIGUOUS
        changed_snapshot = fidelity_firewall(
            plan, rendered, {"c1": changed}, evidence,
            relation_metadata={"c1": RelationMetadata(subject="預算增加", predicate="導致",
                object="工程延後一週", direction="subject_to_object", polarity="positive",
                relation_type="causal")},
        )
        assert "c1" in changed_snapshot.numeric_issues


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


@pytest.mark.parametrize("rendered", (
    "預算導致延後〔span-1〕，另有紀錄稱預算避免延後。",
    "預算導致延後〔span-1〕但避免延後。",
))
def test_firewall_rejects_competing_same_endpoints_predicate_even_with_valid_expected_clause(rendered):
    claim = _claim("c1", subject="預算", predicate="導致", object="延後",
                   relation_type="causal", refs=("span-1",))
    plan = SectionPlan(section_id="s", title="決議", required_claim_ids=("c1",))
    evidence = {"span-1": EvidenceSpan.from_source("span-1", "預算導致延後。")}
    metadata = RelationMetadata(subject=claim.subject, predicate=claim.predicate,
                                object=claim.object, direction=claim.direction,
                                polarity=claim.polarity, condition=claim.condition,
                                relation_type=claim.relation_type)
    snapshot = fidelity_firewall(plan, rendered, {"c1": claim}, evidence,
                                 relation_metadata={"c1": metadata})
    assert snapshot.relation_issues == ("c1",)
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
                "evidence_quote": "預算導致延後",
            }]
        })

    monkeypatch.setattr(service, "_generate_with_local_engine", inverted_generation)
    with pytest.raises(LocalPipelineV2Error, match="fidelity firewall"):
        await service._summarize_with_local_pipeline_v2(
            "預算導致延後。", "system", template=None
        )


@pytest.mark.parametrize("candidate_mode", (
    "inversion", "omission", "competing_predicate", "competing_predicate_no_comma",
))
@pytest.mark.asyncio
async def test_live_c1_unsafe_render_rolls_back_to_source_grounded_baseline(monkeypatch, candidate_mode):
    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_PIPELINE_VERSION", "v2")
    monkeypatch.setattr(service, "_select_local_engine", lambda: _async_value("fake"))
    async def generation(_engine, _system, message, **_kwargs):
        if "SOURCE CHUNK" in message:
            return json.dumps({"claims": [{
                "claim_id": "c1", "subject": "預算", "predicate": "導致", "object": "延後",
                "relation_type": "causal", "evidence_refs": ["span-1"], "evidence_quote": "預算導致延後",
            }]})
        allowed_match = __import__("re").search(r'ALLOWED_CLAIMS: (\[[^\n]*\])', message)
        allowed = json.loads(allowed_match.group(1)) if allowed_match else []
        ids = [claim["claim_id"] for claim in allowed]
        if candidate_mode == "omission" and "c1" in ids:
            return json.dumps({"text": "決議未列該關係", "claim_ids": [], "relation_metadata": {}})
        relation_metadata = {"c1": {"subject": "預算", "predicate": "避免", "object": "延後",
                                     "direction": "subject_to_object", "polarity": "positive",
                                     "condition": None, "relation_type": "causal"}} if "c1" in ids else {}
        text = {
            "competing_predicate": "預算導致延後〔span-1〕，另有紀錄稱預算避免延後",
            "competing_predicate_no_comma": "預算導致延後〔span-1〕但避免延後",
        }.get(candidate_mode, "預算避免延後〔span-1〕")
        return json.dumps({"text": text, "claim_ids": ids,
                           "relation_metadata": relation_metadata})
    monkeypatch.setattr(service, "_generate_with_local_engine", generation)
    result = await service._summarize_with_local_pipeline_v2(
        "預算導致延後。", "system", template=None,
        selected_claim_target={"source_quote": "預算導致延後", "subject": "預算",
                               "predicate": "導致", "object": "延後", "relation_type": "causal"},
    )
    assert "預算導致延後" in result
    assert "預算避免延後" not in result


@pytest.mark.parametrize("candidate_fault", ("wrong_predicate", "missing_id", "reordered_ids"))
@pytest.mark.asyncio
async def test_live_required_relation_metadata_and_ids_are_complete_for_every_claim(monkeypatch, candidate_fault):
    from backend.services import local_pipeline_v2 as v2

    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_PIPELINE_VERSION", "v2")
    monkeypatch.setattr(service, "_select_local_engine", lambda: _async_value("fake"))
    monkeypatch.setattr(v2, "template_section_plans", lambda *_args, **_kwargs: (
        SectionPlan(section_id="relations", title="關係", required_claim_ids=("c1", "c2")),
    ))

    async def generation(_engine, _system, message, **_kwargs):
        if "SOURCE CHUNK" in message:
            return json.dumps({"claims": [
                    {"claim_id": "c1", "subject": "預算", "predicate": "導致", "object": "延後",
                     "relation_type": "causal", "evidence_refs": ["span-1"], "evidence_quote": "預算導致延後"},
                    {"claim_id": "c2", "subject": "人力", "predicate": "造成", "object": "延期",
                     "relation_type": "causal", "evidence_refs": ["span-1"], "evidence_quote": "人力造成延期"},
            ]})
        allowed_match = __import__("re").search(r'ALLOWED_CLAIMS: (\[[^\n]*\])', message)
        allowed = json.loads(allowed_match.group(1)) if allowed_match else []
        ids = [claim["claim_id"] for claim in allowed]
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
    monkeypatch.setattr(v2, "template_section_plans", lambda *_args, **_kwargs: (
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
    monkeypatch.setattr(v2, "template_section_plans", lambda *_args, **_kwargs: (
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


@pytest.mark.parametrize("mutation", (
    "drop_required", "add_unsupported_number", "add_unsupported_entity", "add_unsupported_attribution",
))
@pytest.mark.asyncio
async def test_post_finalizer_bytes_fail_closed_on_required_loss_or_unsupported_value(monkeypatch, mutation):
    from backend.services import local_pipeline_v2 as v2

    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_PIPELINE_VERSION", "v2")
    monkeypatch.setattr(service, "_select_local_engine", lambda: _async_value("fake"))
    monkeypatch.setattr(v2, "template_section_plans", lambda *_args, **_kwargs: (
        SectionPlan(section_id="s", title="決議", required_claim_ids=("c1",)),
    ))

    async def generation(_engine, _system, message, **_kwargs):
        if "SOURCE CHUNK" in message:
            return json.dumps({"claims": [{
                "claim_id": "c1", "subject": "預算", "predicate": "導致", "object": "延後",
                "relation_type": "causal", "evidence_refs": ["span-1"],
                "evidence_quote": "預算導致延後",
            }]})
        additions = {
            "add_unsupported_number": "；另增列99萬元",
            "add_unsupported_entity": "；新增星河能源股份有限公司",
            "add_unsupported_attribution": "；主席表示另增列措施",
        }
        return json.dumps({
            "text": "已移除〔span-1〕" if mutation == "drop_required"
            else "預算導致延後〔span-1〕" + additions.get(mutation, ""),
            "claim_ids": ["c1"],
            "relation_metadata": {"c1": {
                "subject": "預算", "predicate": "導致", "object": "延後",
                "direction": "subject_to_object", "polarity": "positive",
                "condition": None, "relation_type": "causal",
            }},
        })

    def finalizer(marked_text, template=None):
        if mutation == "drop_required":
            return marked_text.replace("預算導致延後", "已移除")
        finalizer_additions = {
            "add_unsupported_number": "；另增列99萬元",
            "add_unsupported_entity": "；新增星河能源股份有限公司",
            "add_unsupported_attribution": "；主席表示另增列措施",
        }
        return marked_text + finalizer_additions.get(mutation, "")

    monkeypatch.setattr(service, "_generate_with_local_engine", generation)
    monkeypatch.setattr(service, "_finalize_record_text", finalizer)
    with pytest.raises(LocalPipelineV2Error, match="final assembly"):
        await service._summarize_with_local_pipeline_v2("預算導致延後。", "system")


def test_high_risk_novelty_detector_is_exact_and_ambiguity_tolerant():
    from backend.services.local_pipeline_v2 import (
        apply_template_glossary_corrections, unsupported_high_risk_additions,
    )

    source = "2026年9月24日，新增12萬元，由星河公司提出。"
    equivalent = "2026-09-24，新增12 萬元，由星河股份有限公司提出。"
    assert unsupported_high_risk_additions(source, equivalent) == ()
    assert unsupported_high_risk_additions(source, "2026-09-24，新增99萬元，由星河公司提出。") == ("numeric",)
    assert unsupported_high_risk_additions(source, "2026-09-24，新增12萬元，由另一家公司提出。") == ("entity",)
    alias_source = "星河能源有限公司提出建議。"
    assert unsupported_high_risk_additions(
        alias_source, "星河能源股份有限公司提出建議。"
    ) == ()
    corrected = apply_template_glossary_corrections("本週列冠二案", (("列冠", "列管"),))
    assert corrected == "本週列管二案"
    assert apply_template_glossary_corrections(corrected, (("列冠", "列管"),)) == corrected
    from backend.core.templates import get_template as load_template
    template_corrections = load_template("section_meeting").glossary_corrections
    fixture = "、".join(wrong for wrong, _right in template_corrections)
    once = apply_template_glossary_corrections(fixture, template_corrections)
    assert apply_template_glossary_corrections(once, template_corrections) == once


@pytest.mark.asyncio
async def test_live_finalizer_rejects_required_fact_duplicated_across_sections(monkeypatch):
    from backend.services import local_pipeline_v2 as v2

    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_PIPELINE_VERSION", "v2")
    monkeypatch.setattr(service, "_select_local_engine", lambda: _async_value("fake"))
    monkeypatch.setattr(v2, "template_section_plans", lambda *_args, **_kwargs: (
        SectionPlan(section_id="s0", title="決議", required_claim_ids=("c1",), template_order=0),
        SectionPlan(section_id="s1", title="補充", template_order=1),
    ))

    async def generation(_engine, _system, message, **_kwargs):
        if "SOURCE CHUNK" in message:
            return json.dumps({"claims": [{
                "claim_id": "c1", "subject": "預算", "predicate": "導致", "object": "延後",
                "relation_type": "causal", "evidence_refs": ["span-1"],
                "evidence_quote": "預算導致延後",
            }]})
        if '"c1"' in message:
            return json.dumps({"text": "預算導致延後〔span-1〕", "claim_ids": ["c1"],
                "relation_metadata": {"c1": {
                    "subject": "預算", "predicate": "導致", "object": "延後",
                    "direction": "subject_to_object", "polarity": "positive",
                    "condition": None, "relation_type": "causal",
                }}})
        return json.dumps({"text": "補充說明", "claim_ids": [], "relation_metadata": {}})

    def duplicate_into_second_section(marked_text, template=None):
        marker = __import__("re").search(r"(【V2段界:[^】]+:1:開始】\n)", marked_text)
        assert marker
        return (marked_text[:marker.end()] + "預算導致延後〔span-1〕\n"
                + marked_text[marker.end():])

    monkeypatch.setattr(service, "_generate_with_local_engine", generation)
    monkeypatch.setattr(service, "_finalize_record_text", duplicate_into_second_section)
    with pytest.raises(LocalPipelineV2Error, match="final assembly"):
        await service._summarize_with_local_pipeline_v2("預算導致延後。", "system")


@pytest.mark.asyncio
async def test_live_final_bytes_reject_omitted_source_inventory_candidates(monkeypatch):
    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_PIPELINE_VERSION", "v2")
    monkeypatch.setattr(service, "_select_local_engine", lambda: _async_value("fake"))

    async def generation(_engine, _system, message, **_kwargs):
        if "SOURCE CHUNK" in message:
            return json.dumps({"claims": []})
        return json.dumps({"text": "會議完成", "claim_ids": [], "relation_metadata": {}})

    monkeypatch.setattr(service, "_generate_with_local_engine", generation)
    with pytest.raises(LocalPipelineV2Error, match="final assembly"):
        await service._summarize_with_local_pipeline_v2("預算因此延後。", "system")


@pytest.mark.asyncio
async def test_live_v2_applies_only_the_selected_templates_verified_glossary_mapping(monkeypatch):
    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_PIPELINE_VERSION", "v2")
    monkeypatch.setattr(service, "_select_local_engine", lambda: _async_value("fake"))

    async def generation(_engine, _system, message, **_kwargs):
        if "SOURCE CHUNK" in message:
            return json.dumps({"claims": []})
        return json.dumps({"text": "列冠", "claim_ids": [], "relation_metadata": {}})

    monkeypatch.setattr(service, "_generate_with_local_engine", generation)
    result = await service._summarize_with_local_pipeline_v2(
        "列冠", "system", template=get_template("section_meeting"),
    )
    assert "列管" in result
    assert "列冠" not in result


def test_final_source_tags_must_resolve_to_validated_spans():
    from backend.services.local_pipeline_v2 import unknown_source_tag_references

    assert unknown_source_tag_references("完成〔span-1〕", ("span-1",)) == ()
    assert unknown_source_tag_references("完成〔invented-span〕", ("span-1",)) == ("unknown_span_reference",)


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
    calls = []

    async def generation(_engine, call_system, message, **kwargs):
        calls.append(("SOURCE CHUNK" in message, kwargs["temperature"], call_system))
        if "SOURCE CHUNK" in message:
            return json.dumps({"claims": []})
        return json.dumps({"text": "section", "claim_ids": [], "relation_metadata": {}})

    monkeypatch.setattr(service, "_generate_with_local_engine", generation)
    await service._summarize_with_local_pipeline_v2("短來源", "system", template=get_template("general"))
    extraction = [(temperature, system) for is_extraction, temperature, system in calls if is_extraction]
    rendering = [(temperature, system) for is_extraction, temperature, system in calls if not is_extraction]
    assert extraction and {temperature for temperature, _ in extraction} == {0.7}
    assert rendering and {temperature for temperature, _ in rendering} == {0.7}
    assert all(system == service.LOCAL_V2_EXTRACTION_SYSTEM_PROMPT for _, system in extraction)
    assert all(system == service.LOCAL_V2_SECTION_SYSTEM_PROMPT for _, system in rendering)


@pytest.mark.asyncio
async def test_qwen_candidate_temperature_varies_extraction_only(monkeypatch):
    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_PIPELINE_VERSION", "v2")
    monkeypatch.setattr(service, "_select_local_engine", lambda: _async_value("lmstudio"))
    service._active_lmstudio_selection = SimpleNamespace(
        model_identifier="qwen3.8-27b", provider="lmstudio", loaded_instance_id="instance-1",
        context_length=8192,
    )
    observed = []

    async def generation(_engine, _system, message, **kwargs):
        observed.append(("SOURCE CHUNK" in message, kwargs["temperature"]))
        if "SOURCE CHUNK" in message:
            return json.dumps({"claims": []})
        return json.dumps({"text": "section", "claim_ids": [], "relation_metadata": {}})

    monkeypatch.setattr(service, "_generate_with_local_engine", generation)
    await service._summarize_with_local_pipeline_v2(
        "短來源", "system", template=get_template("general"),
        extraction_temperature_candidate=0.3,
    )
    extraction = [temperature for is_extraction, temperature in observed if is_extraction]
    rendering = [temperature for is_extraction, temperature in observed if not is_extraction]
    assert extraction and set(extraction) == {0.3}
    assert rendering and set(rendering) == {0.7}


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
    assert extraction_calls == 2
    repair = next(event for event in recorder.events if event["stage_id"] == "v2.extraction.chunk.1.repair")
    assert repair["temperature"] == 0.2
    assert temperatures and set(temperatures) == {0.2}


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
    assert failed_first_parse["status"] == "schema_failed:FactPayloadValidationError"
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
    assert [event["status"] for event in outcomes] == ["generation_failed:ValueError"]
    assert not any(".repair" in event["stage_id"] for event in recorder.events)
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
    assert source_event["corrected_alignment"] == "not_aligned"
    profile_event = next(event for event in recorder.events if event["stage_id"] == "v2.runtime.profile")
    assert profile_event["family"] == "UNKNOWN"
    assert "baseline_temperature" not in profile_event
    assert "temperature" not in profile_event
    extraction_events = [event for event in recorder.events if event["stage_id"].startswith("v2.extraction.chunk.") and event["stage_id"].endswith(".input")]
    section_events = [event for event in recorder.events if event["stage_id"].startswith("v2.section.") and event["stage_id"].endswith(".input")]
    assert extraction_events and all(event["temperature"] == 0.2 for event in extraction_events)
    assert section_events and all(event["temperature"] == 0.2 for event in section_events)
    assert captured_temperatures and {value for value, _ in captured_temperatures} == {0.2}


@pytest.mark.asyncio
async def test_unknown_lmstudio_identity_and_missing_loaded_context_stay_unknown(monkeypatch):
    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_PIPELINE_VERSION", "v2")
    monkeypatch.setattr(service, "_select_local_engine", lambda: _async_value("fake"))
    monkeypatch.setattr(service, "_effective_context_tokens", lambda *_args, **_kwargs: 8192)
    service._active_lmstudio_selection = SimpleNamespace(
        provider="lmstudio", model_identifier="unrecognized-local-model",
        loaded_instance_id=None, context_length=None,
    )

    async def generation(_engine, _system, message, **_kwargs):
        if "SOURCE CHUNK" in message:
            return json.dumps({"claims": []})
        return json.dumps({"text": "safe synthetic section", "claim_ids": [], "relation_metadata": {}})

    monkeypatch.setattr(service, "_generate_with_local_engine", generation)
    recorder = LocalPipelineDiagnosticRecorder(run_id="unknown-runtime-identity")
    await service._summarize_with_local_pipeline_v2(
        "safe synthetic source", "system", template=get_template("general"),
        diagnostic_recorder=recorder,
    )

    profile = next(event for event in recorder.events if event["stage_id"] == "v2.runtime.profile")
    assert profile["family"] == "UNKNOWN"
    assert profile.get("context_length") is None
    assert profile["planner_context_length"] == 8192


def test_lmstudio_context_parser_does_not_substitute_advertised_model_maximum():
    instances = SummarizationService._parse_lmstudio_loaded_instances({
        "models": [{
            "type": "llm", "key": "qwen-model", "max_context_length": 65536,
            "loaded_instances": [{"id": "active-instance", "config": {}}],
        }],
    })
    assert len(instances) == 1
    assert instances[0].context_length is None


@pytest.mark.asyncio
async def test_v2_consumes_only_safely_aligned_corrected_view_while_grounding_raw(monkeypatch):
    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_PIPELINE_VERSION", "v2")
    monkeypatch.setattr(service, "_select_local_engine", lambda: _async_value("fake"))
    captured_extraction = []

    async def generation(_engine, _system, message, **_kwargs):
        if "SOURCE CHUNK" in message:
            captured_extraction.append(message)
            return json.dumps({"claims": []})
        return json.dumps({"text": "安全的測試段落", "claim_ids": [], "relation_metadata": {}})

    monkeypatch.setattr(service, "_generate_with_local_engine", generation)
    raw = "預算導致延後。"
    corrected = "預算 導致 延後。"
    with pytest.raises(LocalPipelineV2Error, match="final assembly"):
        await service._summarize_with_local_pipeline_v2(
            corrected, "system", template=get_template("general"), raw_source_transcript=raw,
        )

    assert captured_extraction
    message = captured_extraction[0]
    assert "CORRECTED COMPREHENSION VIEW" in message
    assert corrected in message
    assert "RAW EVIDENCE SOURCE" in message
    assert raw in message


@pytest.mark.parametrize(("candidate_mode", "expected_patch_calls"), (("missing", 1), ("valid", 0)))
@pytest.mark.asyncio
async def test_v2_requests_at_most_one_targeted_patch_only_for_section_validation_issue(
    monkeypatch, candidate_mode, expected_patch_calls,
):
    from backend.services import local_pipeline_v2 as v2

    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_PIPELINE_VERSION", "v2")
    monkeypatch.setattr(service, "_select_local_engine", lambda: _async_value("fake"))
    monkeypatch.setattr(v2, "template_section_plans", lambda *_args, **_kwargs: (
        SectionPlan(section_id="decision", title="決議", required_claim_ids=("c1",)),
    ))
    patch_messages = []

    async def generation(_engine, _system, message, **_kwargs):
        if "SOURCE CHUNK" in message:
            return json.dumps({"claims": [{
                "claim_id": "c1", "subject": "預算", "predicate": "導致", "object": "延後",
                "relation_type": "fact", "evidence_refs": ["span-1"], "evidence_quote": "預算導致延後",
            }]})
        if "TARGETED SECTION PATCH" in message:
            patch_messages.append(message)
            return json.dumps({"text": "預算導致延後〔span-1〕", "claim_ids": ["c1"], "relation_metadata": {}})
        if candidate_mode == "missing":
            return json.dumps({"text": "尚未確認", "claim_ids": [], "relation_metadata": {}})
        return json.dumps({"text": "預算導致延後〔span-1〕", "claim_ids": ["c1"], "relation_metadata": {}})

    monkeypatch.setattr(service, "_generate_with_local_engine", generation)
    result = await service._summarize_with_local_pipeline_v2("預算導致延後", "system")
    assert "預算導致延後" in result
    assert len(patch_messages) == expected_patch_calls
    if expected_patch_calls:
        assert len(patch_messages) == 1
        assert "decision" in patch_messages[0]


def test_native_schema_probe_classification_requires_valid_completion_or_explicit_unsupported():
    classify = getattr(local_v2, "classify_native_schema_probe", lambda **_kwargs: "UNKNOWN")
    common = {"backend": "lmstudio", "model_identity": "active-model-instance"}
    assert classify(**common, completed_normally=True, schema_valid=True,
                    finish_reason="stop") == "SUPPORTED"
    assert classify(**common, status_code=400,
                    error_message="response_format json_schema is not supported for this model") == "UNSUPPORTED"
    assert classify(**common, status_code=400,
                    error_message="invalid request schema: missing property") == "UNKNOWN"
    assert classify(**common, status_code=503,
                    error_message="server error") == "UNKNOWN"
    assert classify(**common, completed_normally=True, schema_valid=False,
                    finish_reason="length") == "UNKNOWN"
    assert classify(backend="ollama", model_identity="active-model-instance",
                    completed_normally=True, schema_valid=True,
                    finish_reason="stop") == "SUPPORTED"


def test_ollama_native_schema_probe_classification_is_narrow_and_model_specific():
    classify = local_v2.classify_native_schema_probe
    assert classify(backend="ollama", model_identity="qwen3.8:27b",
                    completed_normally=True, schema_valid=True,
                    finish_reason="stop") == "SUPPORTED"
    assert classify(backend="ollama", model_identity="qwen3.8:27b", status_code=400,
                    error_message="model qwen3.8:27b does not support JSON Schema structured output") == "UNSUPPORTED"
    assert classify(backend="ollama", model_identity="qwen3.8:27b", status_code=400,
                    error_message="invalid request schema: missing property") == "UNKNOWN"
    assert classify(backend="ollama", model_identity="qwen3.8:27b", status_code=400,
                    error_message="structured output is not supported by this model") == "UNKNOWN"
    assert classify(backend="ollama", model_identity="qwen3.8:27b", status_code=400,
                    error_message="model gemma4:31b does not support JSON Schema structured output") == "UNKNOWN"
    assert classify(backend="ollama", model_identity="qwen3.8:27b", status_code=503,
                    error_message="model qwen3.8:27b does not support JSON Schema structured output") == "UNKNOWN"


@pytest.mark.asyncio
async def test_ollama_native_schema_probe_uses_source_free_native_format_and_effective_model(monkeypatch):
    service = SummarizationService()
    captured = {}

    async def get_client():
        return object()

    async def post(_client, payload, send_think_field):
        captured.update(payload=payload, send_think_field=send_think_field)
        return '{"claims":[]}', {"done_reason": "stop"}, False

    monkeypatch.setattr(service, "_get_ollama_client", get_client)
    monkeypatch.setattr(service, "_get_effective_model", lambda: "qwen3.8:27b")
    monkeypatch.setattr(service, "_post_ollama_chat", post)

    result = await service._probe_native_schema_capability("ollama", None)

    assert result.capability == "SUPPORTED"
    assert result.error_class is None
    payload = captured["payload"]
    assert payload["model"] == "qwen3.8:27b"
    assert payload["format"] == service._v2_fact_response_format(fact_payload=True)["json_schema"]["schema"]
    assert payload["messages"][-1]["content"] == 'Return {"claims":[]}.'
    assert "PRIVATE_SOURCE_SENTINEL" not in json.dumps(payload)


@pytest.mark.parametrize(("failure_kind", "expected_error_class", "expected_status"), (
    ("http_400", "http_error", 400),
    ("transport", "transport_or_stream_error", None),
))
@pytest.mark.asyncio
async def test_ollama_unknown_schema_probe_stops_before_user_source_and_redacts_diagnostics(
    monkeypatch, failure_kind, expected_error_class, expected_status,
):
    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_PIPELINE_VERSION", "v2")
    monkeypatch.setattr(service, "_select_local_engine", lambda: _async_value("ollama"))
    monkeypatch.setattr(service, "_get_effective_model", lambda: "qwen3.8:27b")

    async def failed_post(*_args, **_kwargs):
        if failure_kind == "http_400":
            class ProbeError(Exception):
                response = SimpleNamespace(status_code=400, text="invalid request schema: missing property")
            raise ProbeError()
        raise httpx.ConnectError("PRIVATE_EXCEPTION_MESSAGE")

    async def get_client():
        return object()

    monkeypatch.setattr(service, "_get_ollama_client", get_client)
    monkeypatch.setattr(service, "_post_ollama_chat", failed_post)
    source_calls = []

    async def generation(*_args, **_kwargs):
        source_calls.append(True)
        return json.dumps({"claims": []})

    monkeypatch.setattr(service, "_generate_with_local_engine", generation)
    recorder = LocalPipelineDiagnosticRecorder(run_id="ollama-schema-probe")
    with pytest.raises(LocalPipelineV2Error, match="capability"):
        await service._summarize_with_local_pipeline_v2(
            "PRIVATE_SOURCE_SENTINEL", "system", diagnostic_recorder=recorder,
        )

    assert source_calls == []
    manifest = json.dumps(recorder.redacted_manifest(), ensure_ascii=False)
    assert "PRIVATE_SOURCE_SENTINEL" not in manifest
    capability_events = [event for event in recorder.events
                         if event["stage_id"] == "v2.native-schema-capability"]
    assert capability_events[0]["status"] == "UNKNOWN"
    assert capability_events[0]["backend"] == "ollama"
    assert capability_events[0]["model_identity"] == "qwen3.8:27b"
    assert capability_events[0]["error_class"] == expected_error_class
    assert capability_events[0].get("http_status") == expected_status
    assert "PRIVATE_EXCEPTION_MESSAGE" not in manifest
    assert not any("repair" in event["stage_id"] for event in recorder.events)


@pytest.mark.asyncio
async def test_ollama_explicit_unsupported_uses_strict_json_generation_without_native_format(monkeypatch):
    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_PIPELINE_VERSION", "v2")
    monkeypatch.setattr(service, "_select_local_engine", lambda: _async_value("ollama"))
    monkeypatch.setattr(service, "_get_effective_model", lambda: "qwen3.8:27b")

    class UnsupportedSchemaError(Exception):
        response = SimpleNamespace(
            status_code=400,
            text="model qwen3.8:27b does not support JSON Schema structured output",
        )

    async def get_client():
        return object()

    async def unsupported_probe(*_args, **_kwargs):
        raise UnsupportedSchemaError()

    monkeypatch.setattr(service, "_get_ollama_client", get_client)
    monkeypatch.setattr(service, "_post_ollama_chat", unsupported_probe)
    generation_formats = []
    recorder = LocalPipelineDiagnosticRecorder(run_id="ollama-explicit-unsupported")

    async def generation(_engine, _system, message, **kwargs):
        generation_formats.append(kwargs.get("response_format"))
        if "SOURCE CHUNK" in message:
            return json.dumps({"claims": []})
        return json.dumps({"text": "safe synthetic section", "claim_ids": [], "relation_metadata": {}})

    monkeypatch.setattr(service, "_generate_with_local_engine", generation)
    await service._summarize_with_local_pipeline_v2(
        "safe synthetic source", "system", template=get_template("general"),
        diagnostic_recorder=recorder,
    )

    assert generation_formats
    assert all(response_format is None for response_format in generation_formats)
    capability_event = next(event for event in recorder.events
                            if event["stage_id"] == "v2.native-schema-capability")
    assert capability_event["status"] == "UNSUPPORTED"
    assert capability_event["backend"] == "ollama"
    assert capability_event["model_identity"] == "qwen3.8:27b"


@pytest.mark.asyncio
async def test_v2_unknown_native_schema_capability_stops_before_user_source_generation(monkeypatch):
    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_PIPELINE_VERSION", "v2")
    monkeypatch.setattr(service, "_select_local_engine", lambda: _async_value("fake"))
    calls = []

    async def unknown_probe(_engine, _selection, _profile=None):
        return "UNKNOWN"

    async def generation(*_args, **_kwargs):
        calls.append("user-generation")
        return json.dumps({"claims": []})

    monkeypatch.setattr(service, "_probe_native_schema_capability", unknown_probe, raising=False)
    monkeypatch.setattr(service, "_generate_with_local_engine", generation)
    with pytest.raises(LocalPipelineV2Error, match="capability"):
        await service._summarize_with_local_pipeline_v2("PRIVATE_SOURCE_SENTINEL", "system")
    assert calls == []


@pytest.mark.asyncio
async def test_native_schema_probe_uses_exact_fact_schema_and_source_free_active_selection(monkeypatch):
    service = SummarizationService()
    captured = {}
    monkeypatch.setattr(service, "_get_lmstudio_client", lambda: object())
    async def chat(client, selection, messages, temperature, max_tokens, **kwargs):
        captured.update(client=client, selection=selection, messages=messages,
                        temperature=temperature, max_tokens=max_tokens, **kwargs)
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"claims":[]}', reasoning_content=None),
                                     finish_reason="stop")],
            usage=None,
        )
    monkeypatch.setattr(service, "_lmstudio_chat_request", chat)
    selection = SimpleNamespace(model_identifier="active-key", loaded_instance_id="active-instance")
    result = await service._probe_native_schema_capability("lmstudio", selection)
    assert result.capability == "SUPPORTED"
    assert captured["selection"] is selection
    assert captured["response_format"]["json_schema"]["name"] == "v2_fact_payload"
    assert captured["messages"][-1]["content"] == 'Return {"claims":[]}.'


@pytest.mark.parametrize(("status", "message", "expected"), (
    (400, "response_format json_schema is not supported for this model", "UNSUPPORTED"),
    (400, "invalid request schema: missing property", "UNKNOWN"),
    (503, "server error", "UNKNOWN"),
))
@pytest.mark.asyncio
async def test_native_schema_probe_only_explicit_unsupported_allows_fallback(
    monkeypatch, status, message, expected,
):
    service = SummarizationService()
    monkeypatch.setattr(service, "_get_lmstudio_client", lambda: object())
    class ProbeError(Exception):
        response = SimpleNamespace(status_code=status, text=message)
    async def failed_chat(*_args, **_kwargs):
        raise ProbeError()
    monkeypatch.setattr(service, "_lmstudio_chat_request", failed_chat)
    selection = SimpleNamespace(model_identifier="active-key", loaded_instance_id="active-instance")
    result = await service._probe_native_schema_capability("lmstudio", selection)
    assert result.capability == expected


@pytest.mark.asyncio
async def test_profile_sampler_runs_only_observed_valid_profiles_and_selector_is_fidelity_first():
    candidates = candidate_runtime_profiles("Qwen", "qwen-key", "lmstudio")
    candidates = tuple(validate_runtime_profile(candidate, {
        "temperature": True, "top_p": True, "top_k": True, "thinking": True,
    }) for candidate in candidates)
    calls = []
    sample_index = 0
    async def run_sample(candidate):
        nonlocal sample_index
        sample_index += 1
        calls.append(candidate.temperature)
        return {"run_id": f"run-{sample_index}", "score": candidate.temperature, "hard_fail": 0,
                "causal_errors": 0, "attribution_errors": 0,
                "faithfulness": candidate.temperature, "traceability": 1,
                "completeness": 1, "usability": 1}
    samples = await sample_candidate_profiles(candidates, run_sample, repeats=3)
    assert len(calls) == 9
    selected = select_profile_candidate(candidates, samples)
    assert selected.temperature == 0.7


@pytest.mark.asyncio
async def test_profile_sampling_rejects_under_repeats_replayed_runs_and_incomplete_metrics():
    candidates = candidate_runtime_profiles("Qwen", "qwen-key", "lmstudio")
    async def unused(_candidate):
        return None
    with pytest.raises(ValueError, match="at least three"):
        await sample_candidate_profiles(candidates, unused, repeats=2)

    candidate = validate_runtime_profile(candidates[0], {
        "temperature": True, "top_p": True, "top_k": True, "thinking": True,
    })
    async def replayed(_candidate):
        return {"run_id": "same-run", "score": 0.9, "hard_fail": 0,
                "causal_errors": 0, "attribution_errors": 0,
                "faithfulness": 0.9, "traceability": 0.9,
                "completeness": 0.9, "usability": 0.9}
    with pytest.raises(ValueError, match="distinct observed runs"):
        await sample_candidate_profiles((candidate,), replayed, repeats=3)

    incomplete = {"score": 0.9, "hard_fail": 0, "causal_errors": 0,
                  "attribution_errors": 0, "faithfulness": 0.9,
                  "traceability": 0.9, "completeness": 0.9, "usability": 0.9}
    with pytest.raises(ValueError, match="run_id"):
        select_profile_candidate((candidate,), {_profile_key_for_test(candidate): (incomplete,) * 3})

    complete_replays = tuple({
        "run_id": f"run-{index}", "score": 0.9, "hard_fail": 0,
        "causal_errors": 0, "attribution_errors": 0,
        "faithfulness": 0.9, "traceability": 0.9,
        "completeness": 0.9, "usability": 0.9,
    } for index in range(3))
    incomplete_dimension = tuple({key: value for key, value in sample.items()
                                  if key != "traceability"}
                                 for sample in complete_replays)
    with pytest.raises(ValueError, match="run_id"):
        select_profile_candidate((candidate,), {
            _profile_key_for_test(candidate): incomplete_dimension,
        })
    out_of_range = tuple({**sample, "score": 1.2} for sample in complete_replays)
    with pytest.raises(ValueError, match="run_id"):
        select_profile_candidate((candidate,), {
            _profile_key_for_test(candidate): out_of_range,
        })


def _profile_key_for_test(profile):
    return f"{profile.model_key}|{profile.temperature}|{profile.top_p}|{profile.top_k}|{profile.thinking}"


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


def test_b_negated_claim_rejects_affirmative_rendering():
    source = "目前不需要執行方案甲"
    span = EvidenceSpan.from_source("span-negation", source, start_offset=0, end_offset=len(source))
    claim = FactClaim(
        claim_id="negative-action", subject="目前", predicate="需要",
        object="執行方案甲", polarity="negative", evidence_refs=(span.span_id,),
        evidence_quote=source, resolved_start_offset=0, resolved_end_offset=len(source),
    )
    plan = SectionPlan(section_id="decision", title="決議", required_claim_ids=(claim.claim_id,))
    negative_meta = RelationMetadata(
        subject=claim.subject, predicate=claim.predicate, object=claim.object,
        polarity="negative", relation_type=claim.relation_type,
    )

    affirmative = fidelity_firewall(
        plan, "目前需要執行方案甲〔span-negation〕", {claim.claim_id: claim},
        {span.span_id: span}, relation_metadata={claim.claim_id: negative_meta},
    )
    faithful = fidelity_firewall(
        plan, "目前需要執行方案甲（否定）〔span-negation〕", {claim.claim_id: claim},
        {span.span_id: span}, relation_metadata={claim.claim_id: negative_meta},
    )

    assert affirmative.polarity_issues == (claim.claim_id,)
    assert not affirmative.accepted
    assert faithful.accepted


@pytest.mark.parametrize(("wrong_render", "condition_is_missing"), (
    ("A與B可同步進行〔span-condition〕", True),
    ("B先完成才能做A〔span-condition〕", False),
))
def test_c_conditional_dependency_and_direction_flip_are_rejected(wrong_render, condition_is_missing):
    source = "A先完成才能做B"
    span = EvidenceSpan.from_source("span-condition", source, start_offset=0, end_offset=len(source))
    claim = FactClaim(
        claim_id="conditional-dependency", subject="A先完成", predicate="才能做",
        object="B", relation_type=local_v2.RelationType.CONDITIONAL,
        condition="先完成", evidence_refs=(span.span_id,), evidence_quote=source,
        resolved_start_offset=0, resolved_end_offset=len(source),
    )
    plan = SectionPlan(section_id="actions", title="待辦", required_claim_ids=(claim.claim_id,))
    metadata = RelationMetadata(
        subject=claim.subject, predicate=claim.predicate, object=claim.object,
        condition=claim.condition, relation_type=claim.relation_type,
    )

    result = fidelity_firewall(
        plan, wrong_render, {claim.claim_id: claim}, {span.span_id: span},
        relation_metadata={claim.claim_id: metadata},
    )

    assert claim.claim_id in result.relation_issues
    assert (claim.claim_id in result.condition_issues) is condition_is_missing
    assert not result.accepted


def test_d_linked_numeric_relation_preserves_people_unit_price_and_total():
    source = "17人乘每人800元等於13,600元"
    span = EvidenceSpan.from_source("span-linked-numbers", source, start_offset=0, end_offset=len(source))
    claims = (
        FactClaim(
            claim_id="headcount-times-unit-price", subject="17人", predicate="乘",
            object="每人800元", number=17, unit="人", evidence_refs=(span.span_id,),
            evidence_quote=source, resolved_start_offset=0, resolved_end_offset=len(source),
        ),
        FactClaim(
            claim_id="unit-price", subject="每人", predicate="金額", object="800元",
            number=800, unit="元", evidence_refs=(span.span_id,), evidence_quote=source,
            resolved_start_offset=0, resolved_end_offset=len(source),
        ),
        FactClaim(
            claim_id="linked-total", subject="17人乘每人800元", predicate="等於",
            object="13,600元", number=13600, unit="元", evidence_refs=(span.span_id,),
            evidence_quote=source, resolved_start_offset=0, resolved_end_offset=len(source),
        ),
    )
    plan = SectionPlan(
        section_id="budget", title="經費", required_claim_ids=tuple(c.claim_id for c in claims),
    )
    by_id = {claim.claim_id: claim for claim in claims}
    rendered = render_section(plan, by_id)
    result = fidelity_firewall(plan, rendered, by_id, {span.span_id: span})

    assert "17人乘每人800元等於13,600元" in rendered
    assert result.accepted
    assert not result.numeric_issues


def test_e_corrected_only_entity_cannot_become_a_raw_grounded_claim():
    raw = "待確認公司提出建議"
    corrected = "星河能源有限公司提出建議"
    span = EvidenceSpan.from_source(
        "span-corrected-entity", raw, corrected_text=corrected,
        start_offset=0, end_offset=len(raw),
    )
    claim = FactClaim(
        claim_id="corrected-only-entity", subject="星河能源有限公司",
        predicate="提出", object="建議", evidence_refs=(span.span_id,),
        evidence_quote=corrected,
    )

    resolved = resolve_claim_occurrences(
        (claim,), {span.span_id: span}, source_sha256=span.source_sha256,
    )
    validated = validate_asserted_claims_against_source(resolved, {span.span_id: span})
    plan = SectionPlan(section_id="discussion", title="討論", required_claim_ids=(claim.claim_id,))
    rendered = render_section(plan, {claim.claim_id: validated[0]})

    assert validated[0].status == ClaimStatus.AMBIGUOUS
    assert "星河能源有限公司" not in raw
    assert "星河能源有限公司" not in rendered


def test_f_unverified_speaker_mapping_cannot_become_official_attribution():
    raw = "發言者3報告已完成"
    span = EvidenceSpan.from_source(
        "span-speaker", raw, start_offset=0, end_offset=len(raw),
    )
    claim = FactClaim(
        claim_id="unverified-speaker", subject="發言者3", predicate="報告",
        object="已完成", attribution="科長", evidence_refs=(span.span_id,),
        evidence_quote=raw,
    )
    resolved = resolve_claim_occurrences(
        (claim,), {span.span_id: span}, source_sha256=span.source_sha256,
    )
    validated = validate_asserted_claims_against_source(resolved, {span.span_id: span})
    plan = SectionPlan(section_id="report", title="報告", required_claim_ids=(claim.claim_id,))
    rendered = render_section(plan, {claim.claim_id: validated[0]})

    assert validated[0].status == ClaimStatus.AMBIGUOUS
    assert "科長" not in raw
    assert "科長" not in rendered


@pytest.mark.asyncio
async def test_i_targeted_patch_with_unsupported_number_rolls_back_to_baseline(monkeypatch):
    from backend.services import local_pipeline_v2 as v2

    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_PIPELINE_VERSION", "v2")
    monkeypatch.setattr(service, "_select_local_engine", lambda: _async_value("fake"))
    monkeypatch.setattr(v2, "template_section_plans", lambda *_args, **_kwargs: (
        SectionPlan(section_id="decision", title="決議", required_claim_ids=("c1",)),
    ))
    patch_calls = []

    async def generation(_engine, _system, message, **_kwargs):
        if "SOURCE CHUNK" in message:
            return json.dumps({"claims": [{
                "claim_id": "c1", "subject": "預算", "predicate": "導致", "object": "延後",
                "evidence_refs": ["span-1"], "evidence_quote": "預算導致延後",
            }]})
        if "TARGETED SECTION PATCH" in message:
            patch_calls.append(message)
            return json.dumps({
                "text": "預算導致延後〔span-1〕；另增列1000元",
                "claim_ids": ["c1"], "relation_metadata": {},
            })
        return json.dumps({
            "text": "預算導致延後〔unresolved-span〕",
            "claim_ids": ["c1"], "relation_metadata": {},
        })

    monkeypatch.setattr(service, "_generate_with_local_engine", generation)
    result = await service._summarize_with_local_pipeline_v2("預算導致延後。", "system")

    assert len(patch_calls) == 1
    assert "預算導致延後" in result
    assert "unresolved-span" not in result
    assert "1000元" not in result


def test_unique_exact_quote_resolves_when_model_offsets_are_wrong_but_duplicate_stays_ambiguous():
    unique = EvidenceSpan.from_source(
        "span-quote-unique", "前綴預算導致延後後綴", start_offset=0,
        end_offset=len("前綴預算導致延後後綴"),
    )
    unique_claim = FactClaim(
        claim_id="unique-quote", subject="預算", predicate="導致", object="延後",
        relation_type=local_v2.RelationType.CAUSAL, evidence_refs=(unique.span_id,),
        evidence_quote="預算導致延後", evidence_start_offset=0, evidence_end_offset=6,
    )
    resolved = resolve_claim_occurrences(
        (unique_claim,), {unique.span_id: unique}, source_sha256=unique.source_sha256,
    )[0]
    assert resolved.status == ClaimStatus.ASSERTED
    assert (resolved.resolved_start_offset, resolved.resolved_end_offset) == (2, 8)

    duplicate = EvidenceSpan.from_source(
        "span-quote-duplicate", "預算導致延後；預算導致延後", start_offset=0, end_offset=13,
    )
    duplicate_claim = unique_claim.model_copy(update={
        "claim_id": "duplicate-quote", "evidence_refs": (duplicate.span_id,),
        "evidence_start_offset": 1, "evidence_end_offset": 7,
    })
    ambiguous = resolve_claim_occurrences(
        (duplicate_claim,), {duplicate.span_id: duplicate}, source_sha256=duplicate.source_sha256,
    )[0]
    assert ambiguous.status == ClaimStatus.AMBIGUOUS
    assert ambiguous.resolved_start_offset is None


def test_unknown_runtime_family_has_no_default_candidate_profile():
    assert candidate_runtime_profiles("Unclassified", "opaque-model-key", "ollama") == ()


@pytest.mark.asyncio
async def test_optional_conflict_stays_local_and_unrelated_section_continues(monkeypatch):
    from backend.services import local_pipeline_v2 as v2

    service = SummarizationService()
    source = "預算導致延後或提前。設備採購取消。"
    span = EvidenceSpan.from_source("span-1", source, start_offset=0, end_offset=len(source))
    monkeypatch.setattr(settings, "LOCAL_PIPELINE_VERSION", "v2")
    monkeypatch.setattr(service, "_select_local_engine", lambda: _async_value("fake"))
    monkeypatch.setattr(service, "_finalize_record_text", lambda text, **_kwargs: text)
    monkeypatch.setattr(v2, "build_evidence_spans", lambda *_args, **_kwargs: [span])
    monkeypatch.setattr(v2, "template_section_plans", lambda *_args, **_kwargs: (
        SectionPlan(section_id="conflicted", title="衝突候選", optional_claim_ids=("c1", "c2"), template_order=0),
        SectionPlan(section_id="unrelated", title="其他事項", required_claim_ids=("c3",), template_order=1),
    ))
    section_calls = []

    async def generation(_engine, _system, message, **_kwargs):
        if "SOURCE CHUNK" in message:
            return json.dumps({"claims": [
                {"claim_id": "c1", "subject": "預算", "predicate": "導致", "object": "延後",
                 "relation_type": "causal", "evidence_refs": ["span-1"],
                 "evidence_quote": "預算導致延後或提前"},
                {"claim_id": "c2", "subject": "預算", "predicate": "導致", "object": "提前",
                 "relation_type": "causal", "evidence_refs": ["span-1"],
                 "evidence_quote": "預算導致延後或提前"},
                {"claim_id": "c3", "subject": "設備", "predicate": "採購", "object": "取消",
                 "evidence_refs": ["span-1"], "evidence_quote": "設備採購取消"},
            ]})
        section_calls.append(message)
        if "SECTION unrelated:" in message:
            return json.dumps({"text": "設備採購取消〔span-1〕", "claim_ids": ["c3"],
                               "relation_metadata": {}})
        return json.dumps({"text": "", "claim_ids": [], "relation_metadata": {}})

    monkeypatch.setattr(service, "_generate_with_local_engine", generation)
    result = await service._summarize_with_local_pipeline_v2(source, "system")

    assert any("SECTION unrelated:" in call for call in section_calls)
    assert "設備採購取消" in result
    assert "預算導致延後" not in result
    assert "預算導致提前" not in result


@pytest.mark.parametrize(("model_key", "expected_family", "expected_temperature"), (
    ("qwen3.8:27b", "Qwen", 0.7),
    ("gemma4:31b", "Gemma", 1.0),
))
@pytest.mark.asyncio
async def test_ollama_v2_uses_effective_model_family_for_baseline_temperature(
    monkeypatch, model_key, expected_family, expected_temperature,
):
    from backend.services import local_pipeline_v2 as v2

    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_PIPELINE_VERSION", "v2")
    monkeypatch.setattr(service, "_select_local_engine", lambda: _async_value("ollama"))
    monkeypatch.setattr(service, "_get_effective_model", lambda: model_key)
    monkeypatch.setattr(service, "_finalize_record_text", lambda text, **_kwargs: text)
    monkeypatch.setattr(v2, "template_section_plans", lambda *_args, **_kwargs: (
        SectionPlan(section_id="one", title="一", template_order=0),
    ))
    captured = []

    async def generation(_engine, _system, message, *, temperature, runtime_profile=None, **_kwargs):
        captured.append((temperature, runtime_profile))
        if "SOURCE CHUNK" in message:
            return json.dumps({"claims": []})
        return json.dumps({"text": "合成測試完成", "claim_ids": [], "relation_metadata": {}})

    monkeypatch.setattr(service, "_generate_with_local_engine", generation)
    result = await service._summarize_with_local_pipeline_v2("合成來源", "system")

    assert "合成測試完成" in result
    assert captured
    temperature, profile = captured[0]
    assert temperature == expected_temperature
    assert profile.family == expected_family
    assert profile.model_key == model_key
    assert "temperature" in profile.supported_controls


async def _async_value(value):
    return value
