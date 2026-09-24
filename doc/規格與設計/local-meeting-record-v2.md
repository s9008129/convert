# Local Meeting Record V2

V2 is an explicit opt-in local pipeline selected with `LOCAL_PIPELINE_VERSION=v2`.
The default remains `v1` until local-model and frozen blind acceptance evidence is
available. A V2 failure raises an explicit error; it never silently falls back.

## Data flow

```text
raw transcript (immutable)
  -> raw-only EvidenceSpan when corrected text cannot be verified/aligned
  -> strict JSON / Pydantic FactLedger
  -> deterministic dedupe + explicit conflicts
  -> ordered MeetingTemplate header/section/subfield plan
  -> one allow-listed render per planned slot
  -> deterministic assembly + existing local template finalizer
  -> final source/relation firewall
  -> guarded section patch / byte rollback
```

`corrected_text` is an advisory comprehension view. It cannot replace
`raw_text` or the source hash. Every asserted claim requires one or more
evidence references. Unknown and ambiguous values remain explicit values.

The production `MeetingTemplate.record_header_fields` sequence precedes its
`record_sections` sequence; subfields are child slots in their parent's order.
Header slots use an explicit template-id contract rather than deriving field
meaning from validation regexes. Each claim is assigned once, and every final
causal/conditional relation is checked as structured subject/predicate/object,
direction, polarity, condition and type against ordered raw evidence spans and
the rendered clause. Candidate render failures roll back to the deterministic
source-backed section.

The quality policy is model-independent. Runtime profiles describe the active
provider/model instance and unsupported controls; they do not redefine fidelity
or acceptance. Native structured-output capability may be used by a future
provider adapter, while strict JSON plus Pydantic validation is the compatibility
path. Exactly one schema-only repair is allowed.

The LM Studio Chat Completions adapter sends only validated API controls. The
loaded instance's reported context length remains the planning authority, not a
per-request override. Controls absent from this adapter (including native
thinking control) remain explicitly unsupported; no profile samples are
counted without both a loaded compatible runtime and evaluator output.

Diagnostics are privacy-safe: tracked manifests contain IDs, hashes, counts,
safe profile metadata, statuses and verdicts only. Raw spans/prompts/model
outputs are runtime-local and are never required for the V2 contract.
