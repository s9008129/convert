"""Opt-in, deterministic local meeting-record V2 primitives.

The module deliberately contains no provider-specific policy.  Model output is
untrusted input at the JSON boundary; raw evidence remains immutable and every
rendered claim carries an evidence reference.  The existing local pipeline is
left untouched unless the caller explicitly selects ``v2``.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterable, Literal, Mapping, Sequence

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


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
    evidence_quote: str | None = Field(default=None, min_length=1)
    evidence_start_offset: int | None = Field(default=None, ge=0)
    evidence_end_offset: int | None = Field(default=None, ge=0)
    resolved_start_offset: int | None = Field(default=None, ge=0, exclude=True)
    resolved_end_offset: int | None = Field(default=None, ge=0, exclude=True)

    @field_validator("evidence_refs")
    @classmethod
    def refs_nonempty(cls, refs: tuple[str, ...]) -> tuple[str, ...]:
        refs = tuple(dict.fromkeys(refs))
        if not refs:
            raise ValueError("every claim requires evidence_refs")
        return refs

    @field_validator("evidence_end_offset")
    @classmethod
    def offsets_are_ordered(cls, end: int | None, info: Any) -> int | None:
        start = info.data.get("evidence_start_offset")
        if (start is None) != (end is None):
            raise ValueError("evidence offsets must be supplied as a pair")
        if start is not None and end <= start:
            raise ValueError("evidence offsets must identify a non-empty occurrence")
        return end

    @property
    def fingerprint(self) -> str:
        fields = (self.subject, self.predicate, self.object, self.relation_type.value,
                  self.direction, self.polarity, self.condition, self.number, self.unit,
                  self.date, self.attribution, self.status.value, self.uncertainty)
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
    coverage_issues: tuple[str, ...] = ()


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


class SelectedClaimTarget(BaseModel):
    """In-memory C1 acceptance target; never part of prompts or task data."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    source_quote: str = Field(min_length=1)
    subject: str = Field(min_length=1)
    predicate: str = Field(min_length=1)
    object: str = Field(min_length=1)
    relation_type: RelationType
    direction: str = "subject_to_object"
    polarity: str = "positive"
    condition: str | None = None

    @field_validator("relation_type")
    @classmethod
    def target_must_be_causal_or_conditional(cls, value: RelationType) -> RelationType:
        if value not in {RelationType.CAUSAL, RelationType.CONDITIONAL}:
            raise ValueError("selected acceptance target must be causal or conditional")
        return value


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
        source_spans = claim_occurrence_spans(claim, evidence)
        source = "\n".join(span.raw_text for span in source_spans)
        if claim.subject and claim.subject not in source or claim.object and claim.object not in source:
            entity_issues.append(claim_id)
            unsupported.append(claim_id)
        if claim.number is not None and not _number_value_supported(claim.number, claim.unit, source):
            numeric_issues.append(claim_id)
        if claim.number is not None and not _number_value_supported(claim.number, claim.unit, rendered):
            numeric_issues.append(claim_id)
        if claim.unit and (claim.unit not in source or claim.unit not in rendered):
            numeric_issues.append(claim_id)
        if claim.date and (claim.date not in source or claim.date not in rendered):
            date_issues.append(claim_id)
        anchored_tag = False
        for segment in re.split(r"[\n。；;！？!?]", rendered):
            claim_is_present = (
                claim.subject in segment and claim.object in segment
                and (claim.relation_type not in {RelationType.CAUSAL, RelationType.CONDITIONAL}
                     or claim.predicate in segment)
            )
            if claim_is_present and any(f"〔{ref}〕" in segment for ref in claim.evidence_refs):
                anchored_tag = True
                break
        if not anchored_tag:
            source_tag_issues.append(claim_id)
        if (claim_id in plan.required_claim_ids or claim_id == selected_claim_id) and claim.relation_type in {RelationType.CAUSAL, RelationType.CONDITIONAL}:
            meta = (relation_metadata or {}).get(claim_id)
            expected = RelationMetadata(
                subject=claim.subject, predicate=claim.predicate, object=claim.object,
                direction=claim.direction, polarity=claim.polarity,
                condition=claim.condition, relation_type=claim.relation_type,
            )
            relation_source_ok = relation_is_supported_in_order(claim, source_spans)
            relation_render_ok = (
                _relation_is_rendered(rendered, expected)
                and _relation_mentions_are_source_supported(
                    rendered, expected, plan, claims, evidence, relation_metadata or {}
                )
            )
            if not relation_source_ok or meta != expected or not relation_render_ok:
                relation_issues.append(claim_id)
        if claim.polarity and claim.polarity.casefold() in {"negative", "negated"} and (
            (relation_metadata or {}).get(claim_id) is None
            or (relation_metadata or {})[claim_id].polarity.casefold() not in {"negative", "negated"}
            or "否定" not in rendered
        ):
            polarity_issues.append(claim_id)
        if claim.condition:
            if claim.relation_type in {RelationType.CAUSAL, RelationType.CONDITIONAL}:
                meta = (relation_metadata or {}).get(claim_id)
                if (
                    meta is None
                    or meta.condition != claim.condition
                    or claim.condition not in rendered
                ):
                    condition_issues.append(claim_id)
            elif claim.condition not in rendered:
                # Non-causal/conditional claims (for example temporal facts)
                # have no relation_metadata contract. Preserve their condition
                # in user-visible text without requiring impossible metadata.
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


class FactPayloadValidationError(ValueError):
    """Model output was generated but failed strict JSON/schema validation."""


class RecoveryFactPayload(BaseModel):
    """Minimal schema for one targeted material-coverage recovery fact.

    Recovery deliberately omits server-owned IDs/references/status/offsets and
    non-essential enrichment fields. This keeps 27B/31B structured completions
    small; the server binds provenance after validation.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)
    subject: str = Field(min_length=1)
    predicate: str = Field(min_length=1)
    object: str = Field(min_length=1)
    relation_type: RelationType = RelationType.FACT
    direction: Literal["subject_to_object", "object_to_subject"] = "subject_to_object"
    polarity: Literal["positive", "negative"] = "positive"
    condition: str | None = None
    evidence_quote: str = Field(min_length=1)


class RecoveryFactEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    claims: tuple[RecoveryFactPayload, ...] = ()


def parse_recovery_fact_payload(
    payload: str | Mapping[str, Any],
    *,
    source_sha256: str,
    evidence_ref: str,
    max_claims: int,
    claim_id_prefix: str,
) -> tuple[FactClaim, ...]:
    """Validate compact fact JSON and bind server-owned provenance.

    Some structured-output providers occasionally append one empty placeholder
    object to an otherwise valid bounded claims array. A blank required text
    field cannot become a factual claim and is safe to ignore. Every other
    schema defect remains fail-closed.
    """

    if max_claims < 1:
        raise FactPayloadValidationError("V2 recovery max_claims must be >= 1")
    try:
        value = json.loads(payload) if isinstance(payload, str) else dict(payload)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise FactPayloadValidationError("V2 recovery returned invalid minimal JSON") from exc
    if not isinstance(value, Mapping) or set(value) != {"claims"}:
        raise FactPayloadValidationError("V2 recovery returned invalid minimal JSON")
    raw_claims = value.get("claims")
    if not isinstance(raw_claims, (list, tuple)):
        raise FactPayloadValidationError("V2 recovery returned invalid minimal JSON")
    if len(raw_claims) > max_claims:
        raise FactPayloadValidationError("V2 recovery exceeded bounded claim count")

    parsed: list[RecoveryFactPayload] = []
    required_text_fields = {"subject", "predicate", "object", "evidence_quote"}
    for raw_item in raw_claims:
        try:
            parsed.append(RecoveryFactPayload.model_validate(raw_item))
        except ValidationError as exc:
            errors = exc.errors()
            blank_placeholder_only = bool(errors) and all(
                error.get("type") == "string_too_short"
                and error.get("loc")
                and error["loc"][0] in required_text_fields
                for error in errors
            )
            if blank_placeholder_only:
                continue
            raise FactPayloadValidationError(
                "V2 recovery returned invalid minimal JSON"
            ) from exc

    return tuple(
        FactClaim(
            claim_id=f"{claim_id_prefix}-{index}",
            subject=item.subject,
            predicate=item.predicate,
            object=item.object,
            relation_type=item.relation_type,
            direction=item.direction,
            polarity=item.polarity,
            condition=item.condition,
            evidence_refs=(evidence_ref,),
            evidence_quote=item.evidence_quote,
        )
        for index, item in enumerate(parsed, start=1)
    )


@dataclass(frozen=True)
class NativeSchemaProbeResult:
    """Normalized capability plus a safe operational classification, never raw error text."""

    capability: str
    error_class: str | None = None
    http_status: int | None = None


def parse_fact_payload(payload: str | Mapping[str, Any], *, source_sha256: str) -> FactLedger:
    """Strict JSON + Pydantic fallback used when native structured output is absent."""
    try:
        value = json.loads(payload) if isinstance(payload, str) else dict(payload)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise FactPayloadValidationError("V2 extraction returned invalid JSON") from exc
    if not isinstance(value, Mapping):
        raise FactPayloadValidationError("V2 extraction JSON must be an object")
    value = dict(value)
    value.setdefault("source_sha256", source_sha256)
    value.setdefault("claims", ())
    try:
        return FactLedger.model_validate(value)
    except ValidationError as exc:
        raise FactPayloadValidationError("V2 extraction JSON failed schema validation") from exc


def build_evidence_spans(
    raw_transcript: str, chunks: Sequence[str], *, source_sha256: str | None = None,
    chunk_offsets: Sequence[tuple[int, int]] | None = None,
    corrected_chunks: Sequence[str | None] | None = None,
) -> tuple[EvidenceSpan, ...]:
    """Create stable spans from existing chunks without replacing raw text."""
    digest = source_sha256 or _hash(raw_transcript)
    spans: list[EvidenceSpan] = []
    cursor = 0
    for index, chunk in enumerate(chunks, 1):
        if chunk_offsets is not None:
            start, end = chunk_offsets[index - 1]
            if raw_transcript[start:end] != chunk:
                raise ValueError("chunk offset does not identify the exact raw-source slice")
        else:
            start = raw_transcript.find(chunk, cursor)
            if start < 0:
                start = raw_transcript.find(chunk)
            if start < 0:
                raise ValueError("chunk cannot be aligned to exact raw-source text")
            end = start + len(chunk)
        corrected_text = corrected_chunks[index - 1] if corrected_chunks is not None else None
        spans.append(EvidenceSpan(span_id=f"span-{index}", raw_text=raw_transcript[start:end],
                                  corrected_text=corrected_text,
                                  start_offset=start, end_offset=end, source_sha256=digest))
        cursor = start + 1
    return tuple(spans)


def align_whitespace_only_corrected_chunks(
    raw_transcript: str,
    corrected_transcript: str | None,
    chunk_offsets: Sequence[tuple[int, int]],
) -> tuple[str | None, ...]:
    """Align a corrected comprehension view only when non-whitespace text is identical.

    This deliberately conservative aligner permits layout normalization only;
    lexical corrections without explicit span alignment remain raw-only.
    """
    if not corrected_transcript or corrected_transcript == raw_transcript:
        return tuple(None for _ in chunk_offsets)
    raw_positions = [index for index, char in enumerate(raw_transcript) if not char.isspace()]
    corrected_positions = [index for index, char in enumerate(corrected_transcript) if not char.isspace()]
    if (len(raw_positions) != len(corrected_positions)
            or any(raw_transcript[raw_at] != corrected_transcript[corrected_at]
                   for raw_at, corrected_at in zip(raw_positions, corrected_positions))):
        return tuple(None for _ in chunk_offsets)

    aligned: list[str | None] = []
    for start, end in chunk_offsets:
        indices = [index for index, raw_at in enumerate(raw_positions) if start <= raw_at < end]
        if not indices:
            aligned.append(None)
            continue
        corrected_start = corrected_positions[indices[0]]
        corrected_end = corrected_positions[indices[-1]] + 1
        corrected_chunk = corrected_transcript[corrected_start:corrected_end]
        raw_chunk = raw_transcript[start:end]
        if ("".join(corrected_chunk.split()) == "".join(raw_chunk.split())
                and corrected_chunk):
            aligned.append(corrected_chunk)
        else:
            aligned.append(None)
    return tuple(aligned)


def classify_native_schema_probe(
    *,
    backend: str,
    model_identity: str,
    completed_normally: bool = False,
    schema_valid: bool = False,
    finish_reason: str | None = None,
    status_code: int | None = None,
    error_message: str | None = None,
) -> str:
    """Classify capability for one backend/model probe without relabeling generic errors."""
    backend_name = backend.strip().casefold()
    identity = model_identity.strip()
    if (backend_name in {"lmstudio", "ollama", "openrouter"} and identity
            and completed_normally and schema_valid and finish_reason == "stop"):
        return "SUPPORTED"
    if not identity or status_code != 400 or not error_message:
        return "UNKNOWN"
    message = error_message.casefold()
    if backend_name == "lmstudio":
        explicit_unsupported = (
            "response_format json_schema is not supported for this model" in message
            or "json_schema response format is not supported for this model" in message
            or "structured output is not supported for this model" in message
        )
    elif backend_name == "openrouter":
        explicit_unsupported = (
            "json_schema" in message
            and ("not supported" in message or "unsupported" in message)
        )
    elif backend_name == "ollama":
        # Ollama has no documented stable unsupported-capability code. Only accept
        # a response that explicitly names this effective model and says it does
        # not support JSON Schema structured output; generic 400s remain UNKNOWN.
        explicit_unsupported = (
            f"model {identity.casefold()} does not support json schema structured output" in message
        )
    else:
        explicit_unsupported = False
    return "UNSUPPORTED" if explicit_unsupported else "UNKNOWN"


def consolidate_claims(
    claims: Iterable[FactClaim], *, source_sha256: str,
    evidence: Mapping[str, EvidenceSpan] | None = None,
) -> FactLedger:
    """Dedupe deterministically; surface same-evidence conflicts without choosing."""
    unique: dict[str, FactClaim] = {}
    conflicts: list[ClaimConflict] = []
    for claim in claims:
        prior = unique.get(claim.fingerprint)
        if prior is None:
            unique[claim.fingerprint] = claim
            continue
        merged_refs = tuple(dict.fromkeys((*prior.evidence_refs, *claim.evidence_refs)))
        def evidence_rank(item: FactClaim) -> tuple[int, int]:
            resolved = int(
                item.resolved_start_offset is not None and item.resolved_end_offset is not None
            )
            return resolved, len(item.evidence_quote or "")
        preferred = max((prior, claim), key=evidence_rank)
        unique[claim.fingerprint] = preferred.model_copy(update={"evidence_refs": merged_refs})
    valid_claims = [claim for claim in unique.values()
                    if claim.status == ClaimStatus.ASSERTED
                    and (claim.uncertainty or "").casefold() not in {"unknown", "ambiguous"}
                    and claim.resolved_start_offset is not None
                    and claim.resolved_end_offset is not None]
    for index, left in enumerate(valid_claims):
        for right in valid_claims[index + 1:]:
            overlaps = (left.resolved_start_offset < right.resolved_end_offset
                        and right.resolved_start_offset < left.resolved_end_offset)
            conflict_type = _same_evidence_conflict_type(left, right) if overlaps else None
            if conflict_type:
                ids = tuple(sorted((left.claim_id, right.claim_id)))
                refs = tuple(sorted(set(left.evidence_refs) & set(right.evidence_refs)))
                conflicts.append(ClaimConflict(conflict_id=_hash("|".join((*ids, str(left.resolved_start_offset), str(right.resolved_start_offset))))[:16],
                                               claim_ids=ids, evidence_refs=refs or tuple(sorted(set(left.evidence_refs) | set(right.evidence_refs))),
                                               conflict_type=conflict_type))
    return FactLedger(source_sha256=source_sha256, claims=tuple(sorted(unique.values(), key=lambda c: c.claim_id)),
                      conflicts=tuple(sorted(conflicts, key=lambda c: c.conflict_id)))


def _same_evidence_conflict_type(left: FactClaim, right: FactClaim) -> str | None:
    """Classify incompatible claims over the same evidence without choosing one."""
    norm = lambda value: "" if value is None else str(value).strip().casefold()
    # Preserve the established explicit conflict for alternatives sharing the
    # same subject/predicate but asserting different objects.
    if (norm(left.subject) == norm(right.subject)
            and norm(left.predicate) == norm(right.predicate)
            and norm(left.object) != norm(right.object)):
        return "same_evidence_value"

    left_ends = frozenset((norm(left.subject), norm(left.object)))
    right_ends = frozenset((norm(right.subject), norm(right.object)))
    if len(left_ends) != 2 or left_ends != right_ends:
        return None

    def directed_ends(claim: FactClaim) -> tuple[str, str]:
        ends = (norm(claim.subject), norm(claim.object))
        if claim.direction == "subject_to_object":
            return ends
        if claim.direction == "object_to_subject":
            return ends[1], ends[0]
        return (f"invalid:{norm(claim.direction)}", *ends[:1])

    differences = []
    for field, left_value, right_value in (
        ("predicate", left.predicate, right.predicate),
        ("relation_type", left.relation_type.value, right.relation_type.value),
        ("direction", directed_ends(left), directed_ends(right)),
        ("polarity", left.polarity, right.polarity),
        ("condition", left.condition, right.condition),
        ("status", left.status.value, right.status.value),
        ("uncertainty", left.uncertainty, right.uncertainty),
        ("number", left.number, right.number),
        ("unit", left.unit, right.unit),
        ("date", left.date, right.date),
        ("attribution", left.attribution, right.attribution),
    ):
        if norm(left_value) != norm(right_value):
            differences.append(field)
    if differences:
        return "same_evidence_semantic_conflict"
    return None


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
                           evidence: Mapping[str, EvidenceSpan] | None = None,
                           raw_source: str | None = None) -> tuple[SectionPlan, ...]:
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
    coverage_issues: dict[str, list[str]] = {spec["id"]: [] for spec in specs}
    body_specs = [spec for spec in specs if spec["kind"] in {"section", "subfield"}]
    first_body = next((spec for spec in body_specs if spec["kind"] == "section"), None)
    # section_meeting's first body slot is the historical tracking table, not a
    # general catch-all. Unmatched record-worthy facts belong in the "科長轉知"
    # narrative section so they are not silently squeezed into the table.
    default_body = first_body
    if template.id == "section_meeting":
        default_body = next(
            (spec for spec in body_specs if spec["id"] == "section-2"),
            first_body,
        )
    policy = template_claim_policy(template.id)
    for claim in ledger.claims:
        if claim.status != ClaimStatus.ASSERTED:
            continue
        source = claim.evidence_quote or "\n".join(evidence_by_id[ref].raw_text for ref in claim.evidence_refs if ref in evidence_by_id)
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
        if match is None and template.id == "section_meeting":
            # Only explicit historical tracking language belongs in the tracking
            # table. Generic facts default to the narrative report section.
            if any(
                cue in source
                for cue in ("解除列管", "繼續列管", "歷次", "前次會議列管")
            ):
                match = next(
                    (spec for spec in body_specs if spec["id"] == "section-1"),
                    default_body,
                )
            elif any(
                cue in source
                for cue in ("交辦", "裁示", "科長指示", "主席指示", "提醒事項")
            ):
                match = next(
                    (spec for spec in body_specs if spec["id"] == "section-3"),
                    default_body,
                )
        if match is None:
            match = default_body
        if match is not None:
            assigned[match["id"]].append(claim.claim_id)
    plans: list[SectionPlan] = []
    if raw_source is not None:
        for kind, start, end in uncovered_material_candidates(
            template.id, raw_source, ledger.claims
        ):
            target_spec = _candidate_section_for(template.id, kind, body_specs, first_body)
            if target_spec is not None:
                coverage_issues[target_spec["id"]].append(f"{kind}@{start}:{end}")
    for order, spec in enumerate(specs):
        ids = tuple(assigned[spec["id"]])
        if template.id == "section_meeting" and spec["kind"] in {"section", "subfield"}:
            # Primary extraction is already the salience filter ("record-worthy
            # facts only"). Once a claim survives exact occurrence resolution,
            # source validation and conflict handling, treating it as optional
            # lets small render models silently drop most of the meeting. Make
            # grounded body claims lossless at the render boundary; the guarded
            # renderer may combine wording, but every claim must remain covered.
            required_ids = ids
        else:
            required_ids = tuple(
                claim_id for claim_id in ids
                if policy.is_required(next(claim.evidence_quote or "" for claim in ledger.claims
                                           if claim.claim_id == claim_id))
            )
        required_set = set(required_ids)
        optional_ids = tuple(claim_id for claim_id in ids if claim_id not in required_set)
        refs = tuple(dict.fromkeys(ref for claim in ledger.claims if claim.claim_id in ids for ref in claim.evidence_refs))
        plans.append(SectionPlan(section_id=spec["id"], title=spec["title"],
                                 required_claim_ids=required_ids, optional_claim_ids=optional_ids,
                                 evidence_span_ids=refs,
                                 template_kind=spec["kind"], template_path=spec["path"],
                                 template_order=order, parent_section_id=spec["parent"],
                                 required_terms=spec["terms"],
                                 coverage_issues=tuple(coverage_issues[spec["id"]])))
    return tuple(plans)


class TemplateClaimPolicy(BaseModel):
    """Trusted, bounded requiredness cues derived from current template prompts."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    template_id: str
    source_present_cues: tuple[str, ...]

    def is_required(self, evidence_quote: str) -> bool:
        return any(cue in evidence_quote for cue in self.source_present_cues)


_TEMPLATE_CUES: Mapping[str, tuple[str, ...]] = {
    "general": ("決議", "通過", "交辦", "裁示", "主辦", "協辦", "負責", "期限", "截止", "生效", "辦理期程", "各單位意見", "不同意見"),
    "procurement_evaluation": ("法定人數", "迴避", "評選方式", "簡報", "詢答", "廠商", "評選結果", "優勝", "序位", "總評分", "不同意見", "決議", "散會"),
    "section_meeting": ("交辦", "裁示", "指示", "列管", "解除列管", "繼續列管", "承辦", "負責", "期限", "截止", "生效", "決議"),
    "isms_monthly": ("風險", "接受", "降低", "移轉", "避免", "演練", "稽核", "驗證", "排程", "下次會議", "決議", "同意", "確認", "追蹤"),
}
_TEMPLATE_CANDIDATES: Mapping[str, tuple[tuple[str, re.Pattern[str]], ...]] = {
    template_id: tuple((cue, re.compile(re.escape(cue))) for cue in cues)
    for template_id, cues in _TEMPLATE_CUES.items()
}

# Observation vocabulary and fail-closed completeness vocabulary are not the
# same thing.  "指示" is useful to observe in section-meeting diagnostics, but
# it is too generic to make every occurrence a hard missing-fact veto (for
# example, an anaphoric phrase such as "這是現場指示的" can merely refer back
# to a fact already captured in the previous clause).
_TEMPLATE_REQUIRED_CUES: Mapping[str, tuple[str, ...]] = {
    **_TEMPLATE_CUES,
    "section_meeting": tuple(
        cue for cue in _TEMPLATE_CUES["section_meeting"] if cue != "指示"
    ),
}


def template_claim_policy(template_id: str) -> TemplateClaimPolicy:
    cues = _TEMPLATE_REQUIRED_CUES.get(template_id)
    if cues is None:
        raise ValueError(f"no trusted template claim policy for {template_id}")
    return TemplateClaimPolicy(template_id=template_id, source_present_cues=cues)


def inventory_source_candidates(template_id: str, raw_source: str) -> tuple[tuple[str, int, int], ...]:
    """Inventory enumerated template/high-risk cues using offsets, never raw values."""
    if template_id not in _TEMPLATE_CANDIDATES:
        raise ValueError(f"no candidate inventory for {template_id}")
    candidates = [
        (kind, match.start(), match.end())
        for kind, pattern in _TEMPLATE_CANDIDATES[template_id]
        for match in pattern.finditer(raw_source)
    ]
    for kind, pattern in (
        ("numeric", re.compile(r"(?<!\d)\d+(?:\.\d+)?")),
        ("numeric", re.compile(r"[零〇一二兩两三四五六七八九](?=[週周年月日天時时小時小时分鐘分钟秒件人個个位項项次份萬元元])")),
        ("date", re.compile(r"(?:\d{2,4}年\d{1,2}月\d{1,2}日|\d{1,4}[./-]\d{1,2}[./-]\d{1,2})")),
        ("relation", re.compile(r"因而|因此|導致|造成|使得|若|如果|除非|未|不|無|沒有")),
        ("speaker", re.compile(r"(?:發言者\d+|Speaker\s*\d+)\s*[:：]")),
    ):
        candidates.extend((kind, match.start(), match.end()) for match in pattern.finditer(raw_source))
    return tuple(sorted(set(candidates), key=lambda item: (item[1], item[2], item[0])))


def material_source_candidates(
    template_id: str, raw_source: str
) -> tuple[tuple[str, int, int], ...]:
    """Return source cues that are material enough to require completeness recovery.

    Only template-owned decision/action cues can create a *completeness* veto.
    Generic relation/negation tokens are intentionally diagnostic-only: spoken
    meetings contain hundreds of ordinary "不/沒有/未/如果" occurrences, and
    treating every one as a required fact turns the recovery pass into a second
    full-transcript extraction.

    Relation, polarity and condition fidelity are still fail-closed for every
    claim that enters the ledger/render path via validate_asserted_claims_against_source
    and fidelity_firewall. This separates "did we omit a required agenda fact?"
    from "did we distort a relation we chose to report?".
    """
    policy = template_claim_policy(template_id)
    material_kinds = set(policy.source_present_cues)
    return tuple(
        candidate for candidate in inventory_source_candidates(template_id, raw_source)
        if candidate[0] in material_kinds
    )


def _bounded_statement_window(
    raw_source: str, start: int, end: int, *, max_chars: int = 320
) -> tuple[int, int] | None:
    """Return a small punctuation/newline-delimited source window.

    This window is evidence context, not a new semantic assertion. It lets a
    narrowly quoted claim cover adjacent trusted cues such as "決議…負責…期限"
    when they are demonstrably in the same short source statement, while
    refusing long ASR runs where sentence boundaries are unavailable.
    """
    if start < 0 or end <= start or end > len(raw_source):
        return None
    boundaries = "\n。！？!?；;，,、"
    left = max(raw_source.rfind(char, 0, start) for char in boundaries) + 1
    right_candidates = [
        pos for char in boundaries
        if (pos := raw_source.find(char, end)) >= 0
    ]
    right = min(right_candidates) + 1 if right_candidates else len(raw_source)
    while left < right and raw_source[left].isspace():
        left += 1
    while right > left and raw_source[right - 1].isspace():
        right -= 1
    if right - left > max_chars:
        return None
    return left, right


def _claim_covers_material_candidate(
    raw_source: str,
    claim: FactClaim,
    candidate_start: int,
    candidate_end: int,
) -> bool:
    """Accept exact coverage or same-short-statement source coverage."""
    assert claim.resolved_start_offset is not None
    assert claim.resolved_end_offset is not None
    if claim.resolved_start_offset <= candidate_start and candidate_end <= claim.resolved_end_offset:
        return True
    claim_window = _bounded_statement_window(
        raw_source, claim.resolved_start_offset, claim.resolved_end_offset
    )
    candidate_window = _bounded_statement_window(
        raw_source, candidate_start, candidate_end
    )
    return claim_window is not None and claim_window == candidate_window


def uncovered_material_candidates(
    template_id: str,
    raw_source: str,
    claims: Iterable[FactClaim],
) -> tuple[tuple[str, int, int], ...]:
    """Find material source cues not covered by one grounded asserted claim."""
    # Recovery is for omitted recall, not for re-adjudicating an already
    # grounded conflict. A claim that is scoped AMBIGUOUS/CONFLICTED but still
    # has an exact resolved source occurrence represents the cue and must not
    # trigger a second model pass that could silently pick a winner. Claims
    # whose occurrence could not be resolved remain eligible for recovery.
    represented = tuple(
        claim for claim in claims
        if claim.status in {
            ClaimStatus.ASSERTED, ClaimStatus.AMBIGUOUS, ClaimStatus.CONFLICTED
        }
        and claim.resolved_start_offset is not None
        and claim.resolved_end_offset is not None
    )
    missing = []
    for kind, start, end in material_source_candidates(template_id, raw_source):
        if any(
            _claim_covers_material_candidate(raw_source, claim, start, end)
            for claim in represented
        ):
            continue
        missing.append((kind, start, end))
    return tuple(missing)


def _candidate_section_for(template_id: str, kind: str,
                           body_specs: Sequence[Mapping[str, Any]],
                           first_body: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    if not body_specs:
        return None
    desired = {
        "general": "section-3" if kind in {"裁示", "交辦", "主辦", "協辦", "辦理期程"} else "section-2",
        "procurement_evaluation": "section-14",
        "section_meeting": "section-1" if "列管" in kind else "section-3",
        "isms_monthly": "section-4" if kind in {"風險", "決議", "接受", "降低", "移轉", "演練"} else "section-3",
    }.get(template_id)
    return next((spec for spec in body_specs if spec["id"] == desired), first_body)


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
    positions: list[list[int]] = []
    for token in tokens:
        occurrences: list[int] = []
        for span in spans:
            if span.start_offset is None:
                if len(spans) != 1:
                    continue
                base = 0
            else:
                base = span.start_offset
            occurrences.extend(
                base + match.start()
                for match in re.finditer(re.escape(token), span.raw_text)
            )
        positions.append(sorted(set(occurrences)))
    if any(not token_positions for token_positions in positions):
        return False
    subject_positions, predicate_positions, object_positions = positions
    if claim.direction == "subject_to_object":
        return any(
            subject_at < predicate_at < object_at
            for subject_at in subject_positions
            for predicate_at in predicate_positions
            for object_at in object_positions
        )
    if claim.direction == "object_to_subject":
        return any(
            object_at < predicate_at < subject_at
            for subject_at in subject_positions
            for predicate_at in predicate_positions
            for object_at in object_positions
        )
    return False


def claim_occurrence_spans(claim: FactClaim, evidence: Mapping[str, EvidenceSpan]) -> list[EvidenceSpan]:
    """Return only the validated raw occurrence, never an entire coarse chunk."""
    if (not claim.evidence_quote or claim.resolved_start_offset is None
            or claim.resolved_end_offset is None):
        return []
    source = next((evidence[ref] for ref in claim.evidence_refs if ref in evidence), None)
    if source is None:
        return []
    return [EvidenceSpan(
        span_id=f"occurrence:{claim.claim_id}", raw_text=claim.evidence_quote,
        start_offset=claim.resolved_start_offset, end_offset=claim.resolved_end_offset,
        source_sha256=source.source_sha256,
    )]


def _relation_core_is_rendered(text: str, relation: RelationMetadata) -> bool:
    """Check the exact typed subject→predicate→object bytes only.

    Clause-level competing-relation detection must not require a condition to
    live in the same punctuation-delimited clause. Conditions and polarity are
    validated independently by the fidelity firewall.
    """
    return f"{relation.subject}{relation.predicate}{relation.object}" in text


def _relation_is_rendered(text: str, relation: RelationMetadata) -> bool:
    if not _relation_core_is_rendered(text, relation):
        return False
    if relation.condition and relation.condition not in text:
        return False
    if relation.polarity.casefold() in {"negative", "negated"} and "否定" not in text:
        return False
    return True


def _relation_mentions_are_source_supported(
    text: str,
    relation: RelationMetadata,
    plan: SectionPlan,
    claims: Mapping[str, FactClaim],
    evidence: Mapping[str, EvidenceSpan],
    relation_metadata: Mapping[str, RelationMetadata],
    diagnostics: dict[str, int] | None = None,
) -> bool:
    """Reject extra same-endpoint relation clauses absent from the typed ledger.

    The text is split at deterministic punctuation boundaries. Every clause
    that mentions both endpoints must contain a rendered relation whose exact
    claim and structured metadata are part of this section plan and whose raw
    evidence supports ordered subject/predicate/object. Merely including the
    expected clause elsewhere in the section cannot bless an added competing
    predicate.
    """
    target_ends = {relation.subject.strip().casefold(), relation.object.strip().casefold()}
    supported: list[RelationMetadata] = []
    supported_triples: list[tuple[str, str, str]] = []
    for claim_id in (*plan.required_claim_ids, *plan.optional_claim_ids):
        claim = claims.get(claim_id)
        if claim is None or claim.status != ClaimStatus.ASSERTED:
            continue
        candidate_ends = {claim.subject.strip().casefold(), claim.object.strip().casefold()}
        spans = claim_occurrence_spans(claim, evidence)
        if candidate_ends != target_ends or not relation_is_supported_in_order(claim, spans):
            continue

        # A section can legitimately contain more than one source-backed
        # assertion about the same endpoints.  Track every exact planned triple,
        # including ordinary FACT claims, so one valid sibling assertion is not
        # mistaken for a hallucinated competing predicate.
        supported_triples.append((claim.subject, claim.predicate, claim.object))
        if claim.relation_type not in {RelationType.CAUSAL, RelationType.CONDITIONAL}:
            continue
        candidate_metadata = relation_metadata.get(claim_id)
        expected_metadata = RelationMetadata(
            subject=claim.subject, predicate=claim.predicate, object=claim.object,
            direction=claim.direction, polarity=claim.polarity, condition=claim.condition,
            relation_type=claim.relation_type,
        )
        if candidate_metadata == expected_metadata:
            supported.append(candidate_metadata)

    if diagnostics is not None:
        diagnostics.update({
            "supported_count": len(supported),
            "clauses_with_both": 0,
            "matching_clause_count": 0,
            "assertive_without_matching": 0,
            "residual_assertive": 0,
            "contrastive_assertive": 0,
        })

    clauses = re.split(r"[，,；;。！？!?、\n]+", text)
    contrastive = re.compile(r"然而|不過|但是|可是|反而|而是|但|however|instead|but", re.IGNORECASE)
    # Mere co-mention of the two endpoints is not a second relation assertion.
    # Small models often add a harmless label/restatement such as
    # “A 與 B 均列入說明” after the exact grounded relation. Treat only a
    # nontrivial lexical bridge between the endpoints as an unsupported
    # competing predicate. This keeps the firewall fail-closed for
    # “A 避免 B” while avoiding false positives on “A 與 B”.
    safe_bridge = re.compile(
        r"^(?:\s|[:：()（）\[\]【】]|與|及|和|暨|或|以及|、|/|／|等|相關)*$"
    )

    def has_assertive_bridge(clause: str) -> bool:
        for subject_match in re.finditer(re.escape(relation.subject), clause):
            for object_match in re.finditer(re.escape(relation.object), clause):
                if subject_match.end() <= object_match.start():
                    bridge = clause[subject_match.end():object_match.start()]
                elif object_match.end() <= subject_match.start():
                    bridge = clause[object_match.end():subject_match.start()]
                else:
                    continue
                bridge = re.sub(r"〔[^〕]*〕", "", bridge)
                if not safe_bridge.fullmatch(bridge):
                    return True
        return False

    for clause in clauses:
        if relation.subject not in clause or relation.object not in clause:
            continue
        if diagnostics is not None:
            diagnostics["clauses_with_both"] += 1
        matching = [
            candidate for candidate in supported
            if _relation_core_is_rendered(clause, candidate)
        ]
        matching_triples = [
            triple for triple in supported_triples
            if "".join(triple) in clause
        ]
        if not matching_triples:
            if has_assertive_bridge(clause):
                if diagnostics is not None:
                    diagnostics["assertive_without_matching"] += 1
                return False
            continue
        if diagnostics is not None:
            diagnostics["matching_clause_count"] += 1
        residual = clause
        for subject, predicate, obj in matching_triples:
            # Remove every source-backed planned assertion sharing the target
            # endpoints. Repetition is a usability concern, not semantic drift.
            residual = residual.replace(f"{subject}{predicate}{obj}", "")
        if relation.subject in residual and relation.object in residual and has_assertive_bridge(residual):
            if diagnostics is not None:
                diagnostics["residual_assertive"] += 1
            return False
        # Chinese and English frequently omit a repeated subject in
        # contrastive continuations. Endpoint repetition by itself is not a new
        # relation (e.g. “A 導致 B，但 B 需持續追蹤”). Reject only when the
        # continuation also carries a relation predicate/connective, such as
        # “A 導致 B 但避免 B”. This preserves fail-closed competing-predicate
        # detection without treating ordinary follow-up prose as semantic drift.
        predicate_markers = {
            candidate.predicate for candidate in supported if candidate.predicate
        } | {
            "導致", "造成", "使得", "致使", "引發", "促成",
            "避免", "防止", "若", "如果", "則", "因此", "因而",
        }
        continuations = contrastive.split(residual)[1:]
        if any(
            (relation.subject in part or relation.object in part)
            and any(marker in part for marker in predicate_markers)
            for part in continuations
        ):
            if diagnostics is not None:
                diagnostics["contrastive_assertive"] += 1
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
    """Ground claims at occurrence scope; keep unsupported claims unresolved."""
    validated: list[FactClaim] = []
    for claim in claims:
        if claim.status != ClaimStatus.ASSERTED:
            validated.append(claim)
            continue
        if (not claim.evidence_quote or claim.resolved_start_offset is None
                or claim.resolved_end_offset is None):
            raise ValueError(f"claim {claim.claim_id} is not source-grounded: no unique raw-source occurrence")
        source_parts = [evidence[ref].raw_text for ref in claim.evidence_refs if ref in evidence]
        if len(source_parts) != len(claim.evidence_refs):
            raise ValueError(f"claim {claim.claim_id} references missing evidence")
        source = claim.evidence_quote
        core_values = (claim.subject, claim.predicate, claim.object, claim.condition)
        unresolved_values = any(value and value not in source for value in core_values)
        if claim.number is not None and not _number_value_supported(claim.number, claim.unit, source):
            unresolved_values = True
        if claim.unit and claim.unit not in source:
            unresolved_values = True
        if claim.date and claim.date not in source:
            unresolved_values = True
        if claim.attribution and claim.attribution not in source:
            unresolved_values = True
        occurrence = EvidenceSpan(
            span_id=f"occurrence:{claim.claim_id}", raw_text=claim.evidence_quote,
            start_offset=claim.resolved_start_offset, end_offset=claim.resolved_end_offset,
            source_sha256=evidence[claim.evidence_refs[0]].source_sha256,
        )
        if (claim.relation_type in {RelationType.CAUSAL, RelationType.CONDITIONAL}
                and not relation_is_supported_in_order(claim, [occurrence])):
            unresolved_values = True
        validated.append(
            claim.model_copy(update={"status": ClaimStatus.AMBIGUOUS,
                                     "uncertainty": "source_value_mismatch"})
            if unresolved_values else claim
        )
    return tuple(validated)


_CHINESE_SINGLE_DIGITS = {
    "零": 0, "〇": 0, "一": 1, "二": 2, "兩": 2, "两": 2,
    "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
}


def _number_value_supported(number: float, unit: str | None, text: str) -> bool:
    """Accept a complete numeric token and, when supplied, its exact unit."""
    number_text = str(int(number)) if float(number).is_integer() else str(number)
    numeric_chars = r"0-9０-９.,+\-−eE"
    arabic_variants = {number_text}
    if float(number).is_integer() and abs(int(number)) >= 1000:
        arabic_variants.add(f"{int(number):,}")
    arabic = "(?:" + "|".join(
        re.escape(value) for value in sorted(arabic_variants, key=len, reverse=True)
    ) + ")"
    if unit:
        unit_pattern = re.escape(unit)
        arabic_with_unit = (
            rf"(?<![{numeric_chars}]){arabic}(?![{numeric_chars}])"
            rf"\s*{unit_pattern}(?![0-9０-９.])"
        )
        if re.search(arabic_with_unit, text):
            return True
    elif re.search(rf"(?<![{numeric_chars}]){arabic}(?![{numeric_chars}])", text):
        return True

    if unit and float(number).is_integer():
        chinese_numerals = "零〇一二兩两三四五六七八九十百千萬万億亿兆"
        mixed_or_approximate = r"半|多|餘|余|左右|上下|以上|以下"
        for digit, value in _CHINESE_SINGLE_DIGITS.items():
            if value != int(number):
                continue
            chinese_with_unit = (
                rf"(?<![{chinese_numerals}]){re.escape(digit)}{re.escape(unit)}"
                rf"(?![{chinese_numerals}]|{mixed_or_approximate})"
            )
            if re.search(chinese_with_unit, text):
                return True
    return False


def unsupported_high_risk_additions(raw_source: str, rendered: str) -> tuple[str, ...]:
    """Return privacy-safe classes of exact, unsupported high-risk additions.

    The detector intentionally limits veto candidates to unambiguous exact
    forms: dates, numeric values paired with units, explicit speaker
    attributions, and organization/entity names with strong suffixes. It does
    not normalize aliases or fuzzy-match; uncertain variants are left to the
    blind rubric rather than rejected here.
    """
    issue_kinds: list[str] = []
    patterns = (
        ("date", re.compile(r"(?<!\d)(?:\d{4}[./-]\d{1,2}[./-]\d{1,2}|\d{2,4}年\d{1,2}月\d{1,2}日)(?!\d)")),
        ("numeric", re.compile(r"(?<![\d０-９])\d+(?:\.\d+)?\s*(?:億元|萬元|元|件|人|名|家|次|日|天|週|周|月|年|小時|分鐘|%|％)(?![\d０-９])")),
        ("attribution", re.compile(r"(?:主席|委員|承辦人|發言者\s*\d+|Speaker\s*\d+)\s*(?:表示|指出|認為|報告|提議)")),
        ("entity", re.compile(r"[\u3400-\u9fffA-Za-z0-9]{3,24}?(?:股份有限公司|有限公司|公司)")),
    )
    for kind, pattern in patterns:
        supported = {re.sub(r"\s+", "", match.group(0)) for match in pattern.finditer(raw_source)}
        for match in pattern.finditer(rendered):
            candidate = re.sub(r"\s+", "", match.group(0))
            if kind == "date":
                digits = tuple(int(value) for value in re.findall(r"\d+", candidate))
                if any(tuple(int(value) for value in re.findall(r"\d+", known)) == digits for known in supported):
                    continue
            elif kind == "numeric":
                numeric = re.match(r"([\d,.]+)(.*)", candidate)
                if numeric:
                    value = numeric.group(1).replace(",", "")
                    try:
                        number = float(value)
                    except ValueError:
                        number = float("nan")
                    unit = numeric.group(2).replace("萬", "万").replace("週", "周")
                    if any(
                        (known_match := re.match(r"([\d,.]+)(.*)", known)) is not None
                        and float(known_match.group(1).replace(",", "")) == number
                        and known_match.group(2).replace("萬", "万").replace("週", "周") == unit
                        for known in supported
                    ):
                        continue
            elif kind == "entity":
                # Same name stem with a different legal suffix is an alias or
                # normalization ambiguity, not decisive evidence of invention.
                stem = re.sub(r"(?:股份有限公司|有限公司|公司)$", "", candidate)
                if stem and stem in raw_source:
                    continue
            if candidate not in supported:
                issue_kinds.append(kind)
                break
    return tuple(issue_kinds)


def unknown_source_tag_references(rendered: str, valid_span_ids: Iterable[str]) -> tuple[str, ...]:
    """Reject only explicit citation tags that cannot resolve to validated spans."""
    valid = set(valid_span_ids)
    unknown = []
    for group in re.findall(r"〔([^〕]+)〕", rendered):
        for span_id in (part.strip() for part in group.split(",")):
            if span_id and span_id not in valid:
                unknown.append("unknown_span_reference")
    return tuple(dict.fromkeys(unknown))


def apply_template_glossary_corrections(text: str, corrections: Sequence[tuple[str, str]]) -> str:
    """Apply only explicit, template-owned exact mappings, deterministically."""
    result = text
    for _ in range(len(corrections) + 1):
        corrected = result
        for wrong, right in corrections:
            if wrong and right and wrong != right:
                corrected = corrected.replace(wrong, right)
        if corrected == result:
            return result
        result = corrected
    raise ValueError("template glossary corrections did not converge")


def _derive_unique_claim_occurrence(
    claim: FactClaim, evidence: Mapping[str, EvidenceSpan]
) -> tuple[str, int, int] | None:
    """Derive an exact raw quote when a small model fails to copy one correctly.

    This is deliberately exact-only: subject/predicate/object must appear in the
    declared direction inside one referenced raw span, and the resulting
    occurrence must be unique. No fuzzy matching or semantic guessing is used.
    """
    if not claim.subject or not claim.predicate or not claim.object:
        return None
    candidates: set[tuple[int, int, str]] = set()
    boundary = re.compile(r"[\n。！？!?；;]")
    for ref in claim.evidence_refs:
        span = evidence.get(ref)
        if span is None or span.start_offset is None:
            continue
        text = span.raw_text
        subjects = [m.start() for m in re.finditer(re.escape(claim.subject), text)]
        predicates = [m.start() for m in re.finditer(re.escape(claim.predicate), text)]
        objects = [m.start() for m in re.finditer(re.escape(claim.object), text)]
        for subject_at in subjects:
            for predicate_at in predicates:
                for object_at in objects:
                    if claim.direction == "subject_to_object":
                        ordered = subject_at < predicate_at < object_at
                    elif claim.direction == "object_to_subject":
                        ordered = object_at < predicate_at < subject_at
                    else:
                        ordered = False
                    if not ordered:
                        continue
                    left = min(subject_at, predicate_at, object_at)
                    right = max(
                        subject_at + len(claim.subject),
                        predicate_at + len(claim.predicate),
                        object_at + len(claim.object),
                    )
                    if right - left > 600:
                        continue
                    before = [m.end() for m in boundary.finditer(text[:left])]
                    after = boundary.search(text, right)
                    quote_start = before[-1] if before else 0
                    quote_end = after.end() if after else len(text)
                    if quote_end - quote_start > 800:
                        quote_start, quote_end = left, right
                    quote = text[quote_start:quote_end].strip()
                    if not quote:
                        continue
                    actual_start = text.find(quote, quote_start, quote_end + 1)
                    if actual_start < 0:
                        continue
                    absolute_start = span.start_offset + actual_start
                    candidates.add((absolute_start, absolute_start + len(quote), quote))
    if len(candidates) != 1:
        return None
    start, end, quote = next(iter(candidates))
    return quote, start, end


def resolve_claim_occurrences(
    claims: Iterable[FactClaim], evidence: Mapping[str, EvidenceSpan], *, source_sha256: str,
) -> tuple[FactClaim, ...]:
    """Resolve asserted claims to one exact raw-source occurrence.

    Model-provided exact quotes remain first priority. If the quote is absent,
    malformed, or duplicated, a deterministic subject/predicate/object fallback
    may recover only a unique exact occurrence. Otherwise the claim is scoped
    ambiguous and cannot enter the rendered record.
    """
    resolved: list[FactClaim] = []
    for claim in claims:
        if claim.status != ClaimStatus.ASSERTED:
            resolved.append(claim)
            continue
        spans = [evidence.get(ref) for ref in claim.evidence_refs]
        if (any(span is None for span in spans)
                or any(span.source_sha256 != source_sha256 for span in spans if span is not None)):
            resolved.append(claim.model_copy(update={
                "status": ClaimStatus.AMBIGUOUS,
                "uncertainty": claim.uncertainty or "unresolved_raw_source_occurrence",
                "resolved_start_offset": None, "resolved_end_offset": None,
            }))
            continue

        occurrences: set[tuple[int, int]] = set()
        unlocated_occurrence = False
        if claim.evidence_quote:
            for span in spans:
                assert span is not None
                if claim.evidence_start_offset is not None:
                    local_start = claim.evidence_start_offset
                    local_end = claim.evidence_end_offset
                    if (local_end is not None and span.start_offset is not None
                            and span.raw_text[local_start:local_end] == claim.evidence_quote):
                        occurrences.add((
                            span.start_offset + local_start,
                            span.start_offset + local_end,
                        ))
                        continue
                cursor = 0
                while True:
                    local_start = span.raw_text.find(claim.evidence_quote, cursor)
                    if local_start < 0:
                        break
                    if span.start_offset is None:
                        unlocated_occurrence = True
                        break
                    absolute_start = span.start_offset + local_start
                    occurrences.add((absolute_start, absolute_start + len(claim.evidence_quote)))
                    cursor = local_start + 1
                if unlocated_occurrence:
                    break

        if not unlocated_occurrence and len(occurrences) == 1:
            resolved_start, resolved_end = next(iter(occurrences))
            resolved.append(claim.model_copy(update={
                "resolved_start_offset": resolved_start,
                "resolved_end_offset": resolved_end,
            }))
            continue

        derived = _derive_unique_claim_occurrence(claim, evidence)
        if derived is None:
            resolved.append(claim.model_copy(update={
                "status": ClaimStatus.AMBIGUOUS,
                "uncertainty": claim.uncertainty or "unresolved_raw_source_occurrence",
                "resolved_start_offset": None, "resolved_end_offset": None,
            }))
            continue
        quote, resolved_start, resolved_end = derived
        resolved.append(claim.model_copy(update={
            "evidence_quote": quote,
            "resolved_start_offset": resolved_start,
            "resolved_end_offset": resolved_end,
        }))
    return tuple(resolved)


def bind_selected_claim_target(
    target: SelectedClaimTarget | Mapping[str, Any],
    claims: Iterable[FactClaim],
    evidence: Mapping[str, EvidenceSpan],
    raw_transcript: str,
) -> str:
    """Resolve an acceptance target by unique raw occurrence and typed relation."""
    target = target if isinstance(target, SelectedClaimTarget) else SelectedClaimTarget.model_validate(target)
    starts: list[int] = []
    cursor = 0
    while True:
        start = raw_transcript.find(target.source_quote, cursor)
        if start < 0:
            break
        starts.append(start)
        cursor = start + 1
    if len(starts) != 1:
        raise ValueError("selected target source occurrence is missing or ambiguous")
    target_start = starts[0]
    target_end = target_start + len(target.source_quote)
    matches: list[str] = []
    for claim in claims:
        if (claim.status != ClaimStatus.ASSERTED
                or (claim.subject, claim.predicate, claim.object, claim.relation_type,
                    claim.direction, claim.polarity, claim.condition)
                != (target.subject, target.predicate, target.object, target.relation_type,
                    target.direction, target.polarity, target.condition)):
            continue
        if not claim.evidence_quote or claim.evidence_quote != target.source_quote:
            continue
        spans = [evidence.get(ref) for ref in claim.evidence_refs]
        if any(span is None for span in spans):
            continue
        occurrence_in_refs = any(
            span is not None and span.start_offset is not None
            and span.start_offset <= target_start and target_end <= span.end_offset
            and span.raw_text[target_start - span.start_offset:target_end - span.start_offset] == target.source_quote
            and span.source_sha256 == _hash(raw_transcript)
            for span in spans
        )
        if occurrence_in_refs:
            matches.append(claim.claim_id)
    if len(matches) != 1:
        raise ValueError("selected target did not bind to one validated typed claim")
    return matches[0]


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
    if family.casefold().startswith("gemma"):
        return (ModelRuntimeProfile(family=family, model_key=model_key, provider=provider,
                                    context_length=context_length, thinking=False,
                                    temperature=1.0, top_p=0.95, top_k=64),)
    return ()


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
    if repeats < 3:
        raise ValueError("profile sampling requires at least three observed runs")
    results: dict[str, tuple[Mapping[str, Any], ...]] = {}
    for candidate in candidates:
        if not candidate.validated:
            continue
        samples: list[Mapping[str, Any]] = []
        for _ in range(repeats):
            observed = await run_sample(candidate)
            if not isinstance(observed, Mapping):
                raise ValueError("profile evaluator must return an observed mapping")
            unsupported = observed.get("unsupported_controls")
            if unsupported:
                names = (unsupported,) if isinstance(unsupported, str) else tuple(unsupported)
                results[_profile_key(candidate)] = ({"unsupported_controls": ",".join(sorted(map(str, names)))},)
                samples = []
                break
            if not _profile_sample_is_complete(observed):
                raise ValueError("profile evaluator must return run_id and complete finite metrics")
            samples.append({key: observed[key] for key in (
                "run_id", "score", "hard_fail", "causal_errors", "attribution_errors",
                "faithfulness", "traceability", "completeness", "usability",
            )})
        if samples:
            if len({str(sample["run_id"]) for sample in samples}) != len(samples):
                raise ValueError("profile sampling requires three distinct observed runs")
            results[_profile_key(candidate)] = tuple(samples)
    return results


_PROFILE_METRIC_KEYS = (
    "score", "hard_fail", "causal_errors", "attribution_errors",
    "faithfulness", "traceability", "completeness", "usability",
)


def _profile_sample_is_complete(sample: Mapping[str, Any]) -> bool:
    run_id = sample.get("run_id")
    if not isinstance(run_id, str) or not run_id.strip():
        return False
    if any(key not in sample for key in _PROFILE_METRIC_KEYS):
        return False
    try:
        values = {key: float(sample[key]) for key in _PROFILE_METRIC_KEYS}
    except (TypeError, ValueError):
        return False
    if any(not math.isfinite(value) for value in values.values()):
        return False
    if any(not 0 <= values[key] <= 1 for key in (
        "score", "faithfulness", "traceability", "completeness", "usability",
    )):
        return False
    return all(
        values[key] >= 0 and values[key].is_integer()
        for key in ("hard_fail", "causal_errors", "attribution_errors")
    )


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
        if (len(samples) < 3 or any("unsupported_controls" in sample for sample in samples)
                or any(not _profile_sample_is_complete(sample) for sample in samples)
                or len({str(sample["run_id"]) for sample in samples}) != len(samples)):
            continue
        hard_fails = sum(float(sample.get("hard_fail", 0)) for sample in samples)
        causal = sum(float(sample.get("causal_errors", 0)) for sample in samples)
        attribution = sum(float(sample.get("attribution_errors", 0)) for sample in samples)
        dimensions = []
        for key in ("faithfulness", "traceability", "completeness", "usability"):
            values = sorted(float(sample[key]) for sample in samples)
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
        raise ValueError("no capability-valid candidate has >=3 complete distinct observed runs (run_id required)")
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
                                 source_trace_complete=(not policy.require_source_trace or not unsupported),
                                 coverage_issues=plan.coverage_issues)


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
