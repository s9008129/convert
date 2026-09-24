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

Requiredness comes only from trusted source-present cues for the active
template; other asserted claims are optional candidates. An explicit selected
claim target is acceptance-only data passed in memory through the local task
path, used by deterministic validation, and excluded from model prompts and
persisted task data. Quotes must resolve to a unique raw occurrence using exact
chunk-origin offsets. Unresolved optional claims stay out of prompts and
rendering and cannot veto unrelated sections or records; required/template
coverage and explicit selected-target checks retain their mapped gates. Conflicts
require overlapping validated occurrence intervals plus typed incompatibility
and have no automatic winner. Candidate inventory is a bounded lexical list,
not a completeness claim for arbitrary meeting semantics.

High-risk enrichment is checked at the claim's resolved occurrence. Arabic
numeric literals are exact-match only; the narrow locale equivalence accepted
for numbers is one Chinese digit immediately followed by its exact unit (for
example, `1` + `週` matches `一週`). Different values or units remain
unresolved. This does not enable broader numeral, date, or unit conversion.

The quality policy is model-independent. Runtime profiles describe the active
provider/model instance and unsupported controls; they do not redefine fidelity
or acceptance. Native structured-output capability may be used by a future
provider adapter, while strict JSON plus Pydantic validation is the compatibility
path. Exactly one schema-only repair is allowed.

Qwen's production profile is `temperature=0.7`, `top_p=0.8`, `top_k=20`, with
thinking off. Approved Qwen extraction comparisons may vary extraction
temperature (`0.3`, `0.5`, `0.7`) only; all section/render calls remain at
`0.7`. Gemma's starting profile is `temperature=1.0`, `top_p=0.95`, `top_k=64`,
with thinking off. Candidate selection requires scored evaluator samples; a
missing frozen evaluator blocks selection and does not change production
settings.

The LM Studio Chat Completions adapter sends only validated API controls. The
loaded instance's reported context length remains the planning authority, not a
per-request override. Controls absent from this adapter (including native
thinking control) remain explicitly unsupported; no profile samples are
counted without both a loaded compatible runtime and evaluator output.

Diagnostics are privacy-safe: tracked manifests contain IDs, hashes, counts,
safe profile metadata, statuses and verdicts only. Raw spans/prompts/model
outputs are runtime-local and are never required for the V2 contract.
