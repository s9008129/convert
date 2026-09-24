"""Opt-in, deterministic local meeting-record V2 primitives.

The module deliberately contains no provider-specific policy.  Model output is
untrusted input at the JSON boundary; raw evidence remains immutable and every
rendered claim carries an evidence reference.  The existing local pipeline is
left untouched unless the caller explicitly selects ``v2``.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class RelationType(str, Enum):
    FACT = "fact"
    CAUSAL = "causal"
    CONDITIONAL = "conditional"
    TEMPORAL = "temporal"


class ClaimStatus(str, Enum):
    ASSERTED = "asserted"
    UNKNOWN = "unknown"
    AMBIGUOUS = "ambiguous"
    CONFLICTED = "conflicted"


class EvidenceSpan(BaseModel):
    """Immutable source span.  ``corrected_text`` is comprehension-only."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    span_id: str = Field(min_length=1, max_length=160)
    raw_text: str
    corrected_text: str | None = None
    start_offset: int | None = Field(default=None, ge=0)
    end_offset: int | None = Field(default=None, ge=0)
    speaker_key: str | None = None
    source_sha256: str

    @field_validator("source_sha256")
    @classmethod
    def valid_hash(cls, value: str) -> str:
        if not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError("source_sha256 must be a lowercase SHA-256")
        return value

    @classmethod
    def from_source(cls, span_id: str, raw_text: str, **kwargs: Any) -> "EvidenceSpan":
        return cls(span_id=span_id, raw_text=raw_text, source_sha256=_hash(raw_text), **kwargs)


class FactClaim(BaseModel):
    """Typed claim with explicit uncertainty and source references."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    claim_id: str = Field(min_length=1, max_length=160)
    subject: str
    predicate: str
    object: str
    relation_type: RelationType = RelationType.FACT
    direction: str = "subject_to_object"
    polarity: str = "positive"
    condition: str | None = None
    number: float | None = None
    unit: str | None = None
    date: str | None = None
    attribution: str | None = None
    status: ClaimStatus = ClaimStatus.ASSERTED
    uncertainty: str | None = None
    evidence_refs: tuple[str, ...] = Field(min_length=1)

    @field_validator("evidence_refs")
    @classmethod
    def refs_nonempty(cls, refs: tuple[str, ...]) -> tuple[str, ...]:
        refs = tuple(dict.fromkeys(refs))
        if not refs:
            raise ValueError("every claim requires evidence_refs")
        return refs

    @property
    def fingerprint(self) -> str:
        fields = (self.subject, self.predicate, self.object, self.relation_type.value,
                  self.polarity, self.condition, self.number, self.unit, self.date,
                  self.attribution)
        return _hash("\x1f".join("" if v is None else str(v).strip().casefold() for v in fields))


class ClaimConflict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    conflict_id: str
    claim_ids: tuple[str, ...] = Field(min_length=2)
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    conflict_type: str


class FactLedger(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    source_sha256: str
    claims: tuple[FactClaim, ...] = ()
    conflicts: tuple[ClaimConflict, ...] = ()
    schema_status: str = "valid"


class SectionPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    section_id: str
    title: str
    required_claim_ids: tuple[str, ...] = ()
    optional_claim_ids: tuple[str, ...] = ()
    evidence_span_ids: tuple[str, ...] = ()
    template_kind: str = "content"
    template_path: str = ""
    template_order: int = 0
    parent_section_id: str | None = None
    required_terms: tuple[str, ...] = ()


class RelationMetadata(BaseModel):
    """Structured relation carried outside generated prose."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    subject: str
    predicate: str
    object: str
    direction: str = "subject_to_object"
    polarity: str = "positive"
    condition: str | None = None
    relation_type: RelationType


class SectionQualitySnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    section_id: str
    required_claim_ids: tuple[str, ...] = ()
    covered_claim_ids: tuple[str, ...] = ()
    unsupported_high_risk_values: tuple[str, ...] = ()
    relation_issues: tuple[str, ...] = ()
    polarity_issues: tuple[str, ...] = ()
    condition_issues: tuple[str, ...] = ()
    attribution_issues: tuple[str, ...] = ()
    duplicate_items: tuple[str, ...] = ()
    source_trace_complete: bool = True
    numeric_issues: tuple[str, ...] = ()
    date_issues: tuple[str, ...] = ()
    entity_issues: tuple[str, ...] = ()
    source_tag_issues: tuple[str, ...] = ()
    coverage_issues: tuple[str, ...] = ()
    cross_section_duplicates: tuple[str, ...] = ()
    template_term_issues: tuple[str, ...] = ()

    @property
    def accepted(self) -> bool:
        return (self.source_trace_complete and not self.unsupported_high_risk_values
                and not self.relation_issues and not self.attribution_issues
                and not self.polarity_issues and not self.condition_issues
                and not self.duplicate_items
                and not self.numeric_issues and not self.date_issues
                and not self.entity_issues and not self.source_tag_issues
                and not self.coverage_issues
                and set(self.required_claim_ids) <= set(self.covered_claim_ids))


def fidelity_firewall(
    plan: SectionPlan,
    rendered: str,
    claims: Mapping[str, FactClaim],
    evidence: Mapping[str, EvidenceSpan],
    *,
    selected_claim_id: str | None = None,
    policy: "QualityPolicy | None" = None,
    relation_metadata: Mapping[str, RelationMetadata] | None = None,
) -> SectionQualitySnapshot:
    """Run deterministic, source-grounded checks for one rendered section.

    This is intentionally conservative: a value is reported unsupported when
    its source span does not contain it; uncertain optional claims remain local.
    Every required relation is validated in its section; selected/core severity
    is applied by the caller without exempting other required relations.
    """
    policy = policy or QualityPolicy()
    base = snapshot_section(plan, rendered, claims, evidence, policy=policy)
    relation_issues: list[str] = []
    polarity_issues: list[str] = []
    condition_issues: list[str] = []
    attribution_issues: list[str] = []
    numeric_issues: list[str] = []
    date_issues: list[str] = []
    entity_issues: list[str] = []
    source_tag_issues: list[str] = []
    unsupported = list(base.unsupported_high_risk_values)
    planned_ids = set(plan.required_claim_ids) | set(plan.optional_claim_ids)
    for other_id, other_claim in claims.items():
        if other_id in planned_ids or other_claim.status != ClaimStatus.ASSERTED:
            continue
        if other_claim.subject and other_claim.object and other_claim.subject in rendered and other_claim.object in rendered:
            unsupported.append(f"unplanned:{other_id}")
    for claim_id in (*plan.required_claim_ids, *plan.optional_claim_ids):
        claim = claims.get(claim_id)
        # Claim identity is carried in the structured render contract, not
        # required to appear verbatim in user prose. Never skip source
        # alignment merely because an opaque ID is absent from ``rendered``.
        if claim is None or claim.status != ClaimStatus.ASSERTED:
            continue
        source_spans = [evidence[ref] for ref in claim.evidence_refs if ref in evidence]
        source = "\n".join(span.raw_text for span in source_spans)
        if claim.subject and claim.subject not in source or claim.object and claim.object not in source:
            entity_issues.append(claim_id)
            unsupported.append(claim_id)
        number_text = None if claim.number is None else str(int(claim.number)) if float(claim.number).is_integer() else str(claim.number)
        if number_text and (number_text not in source or number_text not in rendered):
            numeric_issues.append(claim_id)
        if claim.unit and (claim.unit not in source or claim.unit not in rendered):
            numeric_issues.append(claim_id)
        if claim.date and (claim.date not in source or claim.date not in rendered):
            date_issues.append(claim_id)
        if not any(f"〔{ref}〕" in rendered for ref in claim.evidence_refs):
            source_tag_issues.append(claim_id)
        if claim_id in plan.required_claim_ids and claim.relation_type in {RelationType.CAUSAL, RelationType.CONDITIONAL}:
            meta = (relation_metadata or {}).get(claim_id)
            expected = RelationMetadata(
                subject=claim.subject, predicate=claim.predicate, object=claim.object,
                direction=claim.direction, polarity=claim.polarity,
                condition=claim.condition, relation_type=claim.relation_type,
            )
            relation_source_ok = relation_is_supported_in_order(claim, source_spans)
            if not relation_source_ok or meta != expected or not _relation_is_rendered(rendered, expected):
                relation_issues.append(claim_id)
        if claim.polarity and claim.polarity.casefold() in {"negative", "negated"} and (
            (relation_metadata or {}).get(claim_id) is None
            or (relation_metadata or {})[claim_id].polarity.casefold() not in {"negative", "negated"}
            or "否定" not in rendered
        ):
            polarity_issues.append(claim_id)
        if claim.condition and (
            (relation_metadata or {}).get(claim_id) is None
            or (relation_metadata or {})[claim_id].condition != claim.condition
            or claim.condition not in rendered
        ):
            condition_issues.append(claim_id)
        if claim.attribution and (claim.attribution not in source or claim.attribution not in rendered):
            attribution_issues.append(claim_id)
    return base.model_copy(update={
        "unsupported_high_risk_values": tuple(dict.fromkeys(unsupported)),
        "relation_issues": tuple(dict.fromkeys(relation_issues)),
        "polarity_issues": tuple(dict.fromkeys(polarity_issues)),
        "condition_issues": tuple(dict.fromkeys(condition_issues)),
        "attribution_issues": tuple(dict.fromkeys(attribution_issues)),
        "numeric_issues": tuple(dict.fromkeys(numeric_issues)),
        "date_issues": tuple(dict.fromkeys(date_issues)),
        "entity_issues": tuple(dict.fromkeys(entity_issues)),
        "source_tag_issues": tuple(dict.fromkeys(source_tag_issues)),
        "source_trace_complete": base.source_trace_complete and not unsupported,
    })


class QualityPolicy(BaseModel):
    """Model-independent fidelity rules."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    require_source_trace: bool = True
    reject_selected_relation_failure: bool = True
    reject_unsupported_high_risk: bool = True
    allow_ambiguous_optional: bool = True


class ModelRuntimeProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, protected_namespaces=())
    family: str
    model_key: str
    provider: str
    loaded_instance_id: str | None = None
    context_length: int | None = Field(default=None, ge=1)
    thinking: bool | None = None
    temperature: float | None = Field(default=None, ge=0, le=2)
    top_p: float | None = Field(default=None, gt=0, le=1)
    top_k: int | None = Field(default=None, ge=1)
    unsupported_controls: tuple[str, ...] = ()
    supported_controls: tuple[str, ...] = ()

    @property
    def validated(self) -> bool:
        return not self.unsupported_controls


def parse_fact_payload(payload: str | Mapping[str, Any], *, source_sha256: str) -> FactLedger:
    """Strict JSON + Pydantic fallback used when native structured output is absent."""
    try:
        value = json.loads(payload) if isinstance(payload, str) else dict(payload)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError("V2 extraction returned invalid JSON") from exc
    if not isinstance(value, Mapping):
        raise ValueError("V2 extraction JSON must be an object")
    value = dict(value)
    value.setdefault("source_sha256", source_sha256)
    value.setdefault("claims", ())
    return FactLedger.model_validate(value)


def build_evidence_spans(raw_transcript: str, chunks: Sequence[str], *, source_sha256: str | None = None) -> tuple[EvidenceSpan, ...]:
    """Create stable spans from existing chunks without replacing raw text."""
    digest = source_sha256 or _hash(raw_transcript)
    spans: list[EvidenceSpan] = []
    cursor = 0
    for index, chunk in enumerate(chunks, 1):
        start = raw_transcript.find(chunk, cursor)
        if start < 0:
            start = cursor
        end = min(len(raw_transcript), start + len(chunk))
        spans.append(EvidenceSpan(span_id=f"span-{index}", raw_text=raw_transcript[start:end],
                                  start_offset=start, end_offset=end, source_sha256=digest))
        cursor = end
    return tuple(spans)


def consolidate_claims(claims: Iterable[FactClaim], *, source_sha256: str) -> FactLedger:
    """Dedupe deterministically; surface same-evidence conflicts without choosing."""
    unique: dict[str, FactClaim] = {}
    conflicts: list[ClaimConflict] = []
    for claim in claims:
        prior = unique.get(claim.fingerprint)
        if prior is None:
            unique[claim.fingerprint] = claim
            continue
        merged_refs = tuple(dict.fromkeys((*prior.evidence_refs, *claim.evidence_refs)))
        unique[claim.fingerprint] = prior.model_copy(update={"evidence_refs": merged_refs})
    by_evidence: dict[tuple[str, ...], list[FactClaim]] = {}
    for claim in unique.values():
        by_evidence.setdefault(tuple(sorted(claim.evidence_refs)), []).append(claim)
    for refs, group in by_evidence.items():
        for i, left in enumerate(group):
            for right in group[i + 1:]:
                if left.subject == right.subject and left.predicate == right.predicate and left.object != right.object:
                    ids = tuple(sorted((left.claim_id, right.claim_id)))
                    conflicts.append(ClaimConflict(conflict_id=_hash("|".join(ids))[:16], claim_ids=ids,
                                                   evidence_refs=refs, conflict_type="same_evidence_value"))
    return FactLedger(source_sha256=source_sha256, claims=tuple(sorted(unique.values(), key=lambda c: c.claim_id)),
                      conflicts=tuple(sorted(conflicts, key=lambda c: c.conflict_id)))


def plan_sections(ledger: FactLedger, section_titles: Mapping[str, str] | None = None) -> tuple[SectionPlan, ...]:
    titles = section_titles or {"general": "會議摘要", "decisions": "決議事項", "actions": "待辦事項"}
    ids = [claim.claim_id for claim in ledger.claims if claim.status == ClaimStatus.ASSERTED]
    plans = []
    for section_id, title in titles.items():
        if section_id in {"decisions", "resolution"}:
            selected = [c.claim_id for c in ledger.claims if c.status == ClaimStatus.ASSERTED and c.relation_type in {RelationType.CAUSAL, RelationType.CONDITIONAL}]
        elif section_id in {"actions", "action_items"}:
            selected = [c.claim_id for c in ledger.claims if c.status == ClaimStatus.ASSERTED and any(k in f"{c.predicate}{c.object}" for k in ("負責", "完成", "辦理", "追蹤", "提交"))]
        else:
            selected = ids
        plans.append(SectionPlan(section_id=section_id, title=title,
                                 required_claim_ids=tuple(selected),
                                 evidence_span_ids=tuple(ref for c in ledger.claims if c.claim_id in selected for ref in c.evidence_refs)))
    return tuple(plans)


_HEADER_SLOT_LABELS: Mapping[str, tuple[str, ...]] = {
    "general": ("會議名稱", "會議時間", "會議地點", "主席", "出席人員", "列席人員", "記錄"),
    "procurement_evaluation": ("會議標題",),
    "section_meeting": ("會議紀錄標題", "時間", "地點", "主持人／紀錄", "出席人員", "歷次決議列管案件"),
    "isms_monthly": ("機關名稱", "專案名稱", "會議議題", "地點", "主席", "日期", "記錄", "機關單位", "廠商單位"),
}


def _title_from_template_lines(lines: Sequence[str], fallback: str) -> str:
    if not lines:
        return fallback
    line = lines[0].strip().lstrip("#*- ")
    return re.split(r"[：:]", line, maxsplit=1)[0].strip() or fallback


def _header_label_from_skeleton(line: str, index: int) -> str:
    """Fallback from the formatter-owned skeleton, never from regex semantics."""
    label = re.split(r"[：:]", line.strip(), maxsplit=1)[0]
    label = re.sub(r"（待確認）|逐字稿未提及|（年）|（月）|（日）", "", label).strip()
    return label or f"欄位{index + 1}"


def template_section_titles(template: Any | None = None) -> dict[str, str]:
    """Return complete ordered slots from the production header/section contract.

    This compatibility view intentionally no longer derives from validation-only
    ``required_section_patterns``; use ``template_section_plans`` for hierarchy.
    """
    plans = template_section_plans(template, FactLedger(source_sha256="0" * 64), {})
    return {plan.section_id: plan.title for plan in plans}


def template_section_plans(template: Any | None, ledger: FactLedger,
                           evidence: Mapping[str, EvidenceSpan] | None = None) -> tuple[SectionPlan, ...]:
    """Map claims once into the real ordered MeetingTemplate record topology.

    Headers receive claims only through the explicit template-id slot contract.
    Body claims route by matching the raw evidence against section/subfield
    patterns; unmatched facts go to the first body section, never copied to all.
    """
    if template is None:
        from backend.core.templates import get_template
        template = get_template(None)
    specs: list[dict[str, Any]] = []
    header_labels = _HEADER_SLOT_LABELS.get(template.id)
    for index, field_spec in enumerate(template.record_header_fields):
        label = (header_labels[index] if header_labels is not None and index < len(header_labels)
                 else _header_label_from_skeleton(field_spec.line, index))
        specs.append({"id": f"header-{index + 1}", "title": label, "kind": "header",
                      "path": f"record_header_fields[{index}]", "pattern": field_spec.pattern,
                      "parent": None, "terms": (label,)})
    for section_index, section in enumerate(template.record_sections):
        title = _title_from_template_lines(section.skeleton_lines, f"章節{section_index + 1}")
        parent_id = f"section-{section_index + 1}"
        specs.append({"id": parent_id, "title": title, "kind": "section",
                      "path": f"record_sections[{section_index}]", "pattern": section.presence_pattern,
                      "parent": None, "terms": (title,)})
        for sub_index, (pattern, lines) in enumerate(section.subfields):
            sub_title = _title_from_template_lines(lines, f"子欄位{sub_index + 1}")
            specs.append({"id": f"{parent_id}-subfield-{sub_index + 1}", "title": sub_title,
                          "kind": "subfield", "path": f"record_sections[{section_index}].subfields[{sub_index}]",
                          "pattern": pattern, "parent": parent_id, "terms": (sub_title,)})
    evidence_by_id = evidence or {}
    assigned: dict[str, list[str]] = {spec["id"]: [] for spec in specs}
    body_specs = [spec for spec in specs if spec["kind"] in {"section", "subfield"}]
    first_body = next((spec for spec in body_specs if spec["kind"] == "section"), None)
    for claim in ledger.claims:
        if claim.status != ClaimStatus.ASSERTED:
            continue
        source = "\n".join(evidence_by_id[ref].raw_text for ref in claim.evidence_refs if ref in evidence_by_id)
        semantic_text = " ".join((claim.subject, claim.predicate, claim.object))
        header_match = next((spec for spec in specs if spec["kind"] == "header" and
                             any(term in semantic_text for term in spec["terms"])), None)
        match = header_match
        if match is None:
            match = next((spec for spec in body_specs if spec["kind"] == "subfield" and
                          spec["pattern"].search(source)), None)
        if match is None:
            match = next((spec for spec in body_specs if spec["kind"] == "section" and
                          spec["pattern"].search(source)), None)
        if match is None:
            match = first_body
        if match is not None:
            assigned[match["id"]].append(claim.claim_id)
    plans: list[SectionPlan] = []
    for order, spec in enumerate(specs):
        ids = tuple(assigned[spec["id"]])
        refs = tuple(dict.fromkeys(ref for claim in ledger.claims if claim.claim_id in ids for ref in claim.evidence_refs))
        plans.append(SectionPlan(section_id=spec["id"], title=spec["title"],
                                 required_claim_ids=ids, evidence_span_ids=refs,
                                 template_kind=spec["kind"], template_path=spec["path"],
                                 template_order=order, parent_section_id=spec["parent"],
                                 required_terms=spec["terms"]))
    return tuple(plans)


def relation_is_supported_in_order(claim: FactClaim, spans: Sequence[EvidenceSpan]) -> bool:
    """Require ordered evidence references and subject/predicate/object order."""
    if not spans or any(not s.raw_text for s in spans):
        return False
    offsets = [s.start_offset for s in spans]
    if len(spans) > 1 and any(offset is None for offset in offsets):
        return False
    if all(offset is not None for offset in offsets) and offsets != sorted(offsets):
        return False
    tokens = (claim.subject, claim.predicate, claim.object)
    positions: list[int] = []
    for token in tokens:
        occurrences = [span.start_offset + pos for span in spans
                       if span.start_offset is not None
                       for pos in [span.raw_text.find(token)] if pos >= 0]
        if not occurrences and len(spans) == 1 and spans[0].start_offset is None:
            local = spans[0].raw_text.find(token)
            occurrences = [local] if local >= 0 else []
        positions.append(min(occurrences) if occurrences else -1)
    if any(position < 0 for position in positions):
        return False
    if claim.direction == "subject_to_object":
        return positions[0] < positions[1] < positions[2]
    if claim.direction == "object_to_subject":
        return positions[2] < positions[1] < positions[0]
    return False


def _relation_is_rendered(text: str, relation: RelationMetadata) -> bool:
    expected = f"{relation.subject}{relation.predicate}{relation.object}"
    if expected not in text:
        return False
    if relation.condition and relation.condition not in text:
        return False
    if relation.polarity.casefold() in {"negative", "negated"} and "否定" not in text:
        return False
    return True


def validate_runtime_profile(profile: ModelRuntimeProfile, capabilities: Mapping[str, Any]) -> ModelRuntimeProfile:
    """Validate requested controls against the active runtime, never by name guessing."""
    unsupported = list(profile.unsupported_controls)
    supported_controls: list[str] = []
    for key in ("context_length", "thinking", "temperature", "top_p", "top_k"):
        supported = capabilities.get(key, True)
        if isinstance(supported, (list, tuple, set)):
            supported = getattr(profile, key) in supported
        if getattr(profile, key) is None:
            continue
        if supported is False:
            if key not in unsupported:
                unsupported.append(key)
        else:
            supported_controls.append(key)
    return profile.model_copy(update={
        "unsupported_controls": tuple(sorted(set(unsupported))),
        "supported_controls": tuple(sorted(set(supported_controls))),
    })


def validate_asserted_claims_against_source(
    claims: Iterable[FactClaim], evidence: Mapping[str, EvidenceSpan]
) -> tuple[FactClaim, ...]:
    """Reject asserted high-risk values absent from their ordered raw spans."""
    validated: list[FactClaim] = []
    for claim in claims:
        if claim.status != ClaimStatus.ASSERTED:
            validated.append(claim)
            continue
        source_parts = [evidence[ref].raw_text for ref in claim.evidence_refs if ref in evidence]
        if len(source_parts) != len(claim.evidence_refs):
            raise ValueError(f"claim {claim.claim_id} references missing evidence")
        source = "\n".join(source_parts)
        values = (claim.subject, claim.predicate, claim.object, claim.condition,
                  None if claim.number is None else str(claim.number), claim.unit,
                  claim.date, claim.attribution)
        missing = tuple(value for value in values if value and value not in source)
        if missing:
            raise ValueError(f"claim {claim.claim_id} is not source-grounded")
        if claim.relation_type in {RelationType.CAUSAL, RelationType.CONDITIONAL} and not relation_is_supported_in_order(
            claim, [evidence[ref] for ref in claim.evidence_refs]
        ):
            raise ValueError(f"claim {claim.claim_id} relation order is not source-grounded")
        validated.append(claim)
    return tuple(validated)


def validate_relation_metadata(
    plan: SectionPlan, claims: Mapping[str, FactClaim], metadata: Mapping[str, RelationMetadata]
) -> None:
    """Require complete structured relation metadata for required relations."""
    allowed = set(plan.required_claim_ids) | set(plan.optional_claim_ids)
    if not set(metadata) <= allowed:
        raise ValueError("relation metadata contains an unknown claim ID")
    for claim_id in plan.required_claim_ids:
        claim = claims.get(claim_id)
        if claim is None or claim.relation_type not in {RelationType.CAUSAL, RelationType.CONDITIONAL}:
            continue
        value = metadata.get(claim_id)
        expected = RelationMetadata(subject=claim.subject, predicate=claim.predicate,
                                    object=claim.object, direction=claim.direction,
                                    polarity=claim.polarity, condition=claim.condition,
                                    relation_type=claim.relation_type)
        if value != expected:
            raise ValueError("required relation metadata is missing or incorrect")


def candidate_runtime_profiles(family: str, model_key: str, provider: str, *, context_length: int | None = None) -> tuple[ModelRuntimeProfile, ...]:
    """Return the approved family candidates; controls are checked separately."""
    if family.casefold().startswith("qwen"):
        temperatures = (0.3, 0.5, 0.7)
        return tuple(ModelRuntimeProfile(family=family, model_key=model_key, provider=provider,
                                         context_length=context_length, thinking=False,
                                         temperature=t, top_p=0.8, top_k=20) for t in temperatures)
    return (ModelRuntimeProfile(family=family, model_key=model_key, provider=provider,
                                context_length=context_length, thinking=False,
                                temperature=1.0, top_p=0.95, top_k=64),)


def summarize_profile_samples(samples: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Privacy-safe median/worst/range/hard-fail summary for profile selection."""
    scores = sorted(float(s["score"]) for s in samples if "score" in s)
    failures = sum(int(s.get("hard_fail", 0)) for s in samples)
    if not scores:
        return {"sample_count": 0, "hard_fail_count": failures}
    mid = scores[len(scores) // 2] if len(scores) % 2 else (scores[len(scores)//2-1] + scores[len(scores)//2]) / 2
    return {"sample_count": len(scores), "median": mid, "worst": scores[0],
            "range": scores[-1] - scores[0], "hard_fail_count": failures}


async def sample_candidate_profiles(
    candidates: Sequence[ModelRuntimeProfile],
    run_sample: Any,
    *,
    repeats: int = 3,
) -> Mapping[str, tuple[Mapping[str, Any], ...]]:
    """Execute only caller-supplied runtime/evaluator samples; never fabricate data."""
    if repeats < 1:
        raise ValueError("repeats must be positive")
    results: dict[str, tuple[Mapping[str, Any], ...]] = {}
    for candidate in candidates:
        if not candidate.validated:
            continue
        samples: list[Mapping[str, Any]] = []
        for _ in range(repeats):
            observed = await run_sample(candidate)
            if not isinstance(observed, Mapping) or "score" not in observed:
                raise ValueError("profile evaluator must return an observed score mapping")
            unsupported = observed.get("unsupported_controls")
            if unsupported:
                names = (unsupported,) if isinstance(unsupported, str) else tuple(unsupported)
                results[_profile_key(candidate)] = ({"unsupported_controls": ",".join(sorted(map(str, names)))},)
                samples = []
                break
            samples.append({key: value for key, value in observed.items()
                            if key in {"score", "hard_fail", "causal_errors", "attribution_errors",
                                       "faithfulness", "traceability", "completeness", "usability"}})
        if samples:
            results[_profile_key(candidate)] = tuple(samples)
    return results


def select_profile_candidate(
    candidates: Sequence[ModelRuntimeProfile],
    samples_by_profile: Mapping[str, Sequence[Mapping[str, Any]]],
) -> ModelRuntimeProfile:
    """Choose observed candidates fidelity-first; unsupported/unsampled are ineligible."""
    eligible: list[tuple[tuple[float, ...], ModelRuntimeProfile]] = []
    for candidate in candidates:
        if not candidate.validated:
            continue
        samples = samples_by_profile.get(_profile_key(candidate), ())
        if (not samples or any("unsupported_controls" in sample for sample in samples)
                or any("score" not in sample for sample in samples)):
            continue
        hard_fails = sum(float(sample.get("hard_fail", 0)) for sample in samples)
        causal = sum(float(sample.get("causal_errors", 0)) for sample in samples)
        attribution = sum(float(sample.get("attribution_errors", 0)) for sample in samples)
        dimensions = []
        for key in ("faithfulness", "traceability", "completeness", "usability"):
            values = sorted(float(sample.get(key, 0)) for sample in samples)
            median = values[len(values) // 2] if len(values) % 2 else (values[len(values)//2 - 1] + values[len(values)//2]) / 2
            dimensions.append((values[0], median, values[-1] - values[0]))
        score = sum(float(sample["score"]) for sample in samples) / len(samples)
        # Minimize hard failures/errors first; then maximize each dimension's
        # worst case/median and prefer a smaller run-to-run range.
        rank_parts: list[float] = [hard_fails, causal, attribution]
        for worst, median, value_range in dimensions:
            rank_parts.extend((-worst, -median, value_range))
        rank = (*rank_parts, -score)
        eligible.append((rank, candidate))
    if not eligible:
        raise ValueError("no capability-valid candidate has observed evaluator samples")
    return min(eligible, key=lambda item: item[0])[1]


def _profile_key(profile: ModelRuntimeProfile) -> str:
    return f"{profile.model_key}|{profile.temperature}|{profile.top_p}|{profile.top_k}|{profile.thinking}"


def cross_section_claim_duplicates(plans: Sequence[SectionPlan]) -> tuple[str, ...]:
    """Return claim IDs assigned to more than one section (diagnostic, not veto)."""
    seen: dict[str, int] = {}
    for plan in plans:
        for claim_id in (*plan.required_claim_ids, *plan.optional_claim_ids):
            seen[claim_id] = seen.get(claim_id, 0) + 1
    return tuple(sorted(cid for cid, count in seen.items() if count > 1))


def validate_template_terms(text: str, terms: Sequence[str]) -> tuple[str, ...]:
    """Find declared template terms absent from assembled text without inventing them."""
    return tuple(term for term in terms if term and term not in text)


def parse_section_render_payload(payload: str | Mapping[str, Any], *, plan: SectionPlan) -> tuple[str, tuple[str, ...], Mapping[str, RelationMetadata]]:
    """Parse the per-section model envelope; identity stays outside prose."""
    value = json.loads(payload) if isinstance(payload, str) else dict(payload)
    if not isinstance(value, Mapping) or not isinstance(value.get("text"), str):
        raise ValueError("section render must be a JSON object with text")
    claim_ids = tuple(value.get("claim_ids", ()))
    allowed = set(plan.required_claim_ids) | set(plan.optional_claim_ids)
    if not set(claim_ids) <= allowed:
        raise ValueError("section render contains claim outside plan")
    metadata = value.get("relation_metadata", {})
    if not isinstance(metadata, Mapping):
        raise ValueError("relation_metadata must be an object")
    try:
        parsed_metadata = {str(k): RelationMetadata.model_validate(v) for k, v in metadata.items()}
    except Exception as exc:
        raise ValueError("relation_metadata entries must be structured relation objects") from exc
    return value["text"], claim_ids, parsed_metadata


def render_section(plan: SectionPlan, claims: Mapping[str, FactClaim]) -> str:
    """Render only claims explicitly allowed by a section plan."""
    allowed = (*plan.required_claim_ids, *plan.optional_claim_ids)
    lines = [f"{plan.title}："]
    for claim_id in allowed:
        claim = claims.get(claim_id)
        if claim is None or claim.status != ClaimStatus.ASSERTED:
            continue
        relation = f"{claim.subject}{claim.predicate}{claim.object}"
        if claim.condition:
            relation = f"{claim.condition}時，{relation}"
        if claim.polarity.casefold() in {"negative", "negated"}:
            relation = f"{relation}（否定）"
        lines.append(f"- {relation}〔{','.join(claim.evidence_refs)}〕")
    return "\n".join(lines)


def assemble_sections(rendered: Mapping[str, str], order: Sequence[str]) -> str:
    return "\n\n".join(rendered[key].rstrip() for key in order if key in rendered)


def snapshot_section(plan: SectionPlan, rendered: str, claims: Mapping[str, FactClaim], evidence: Mapping[str, EvidenceSpan], *, policy: QualityPolicy | None = None) -> SectionQualitySnapshot:
    policy = policy or QualityPolicy()
    required = tuple(plan.required_claim_ids)
    covered = tuple(cid for cid in required if cid in claims and claims[cid].evidence_refs
                    and all(ref in evidence for ref in claims[cid].evidence_refs)
                    and all(part in rendered for part in (claims[cid].subject, claims[cid].object)))
    unsupported = tuple(cid for cid in (*plan.required_claim_ids, *plan.optional_claim_ids) if cid in rendered and cid in claims and any(ref not in evidence for ref in claims[cid].evidence_refs))
    duplicates = tuple(sorted({line for line in rendered.splitlines() if line.startswith("-")}))
    duplicate_items = tuple(item for item in duplicates if sum(line == item for line in rendered.splitlines()) > 1)
    return SectionQualitySnapshot(section_id=plan.section_id, required_claim_ids=required,
                                 covered_claim_ids=covered, unsupported_high_risk_values=unsupported,
                                 duplicate_items=duplicate_items,
                                 source_trace_complete=(not policy.require_source_trace or not unsupported))


@dataclass(frozen=True)
class PatchResult:
    text: str
    accepted: bool
    rolled_back: bool
    before: SectionQualitySnapshot
    after: SectionQualitySnapshot


def guarded_section_patch(original: str, candidate: str, before: SectionQualitySnapshot, after: SectionQualitySnapshot) -> PatchResult:
    """Accept only non-regressive patches; rejected patches return original bytes."""
    before_score = (len(before.covered_claim_ids), -len(before.unsupported_high_risk_values), before.accepted)
    after_score = (len(after.covered_claim_ids), -len(after.unsupported_high_risk_values), after.accepted)
    accepted = after.accepted and after_score >= before_score
    return PatchResult(candidate if accepted else original, accepted, not accepted, before, after)


def explicit_pipeline_version(value: str | None) -> str:
    normalized = (value or "v1").strip().lower()
    if normalized not in {"v1", "v2"}:
        raise ValueError("LOCAL_PIPELINE_VERSION must be explicitly v1 or v2")
    return normalized


class LocalPipelineV2Error(RuntimeError):
    """Explicit V2 failure; callers must not silently turn this into V1."""
