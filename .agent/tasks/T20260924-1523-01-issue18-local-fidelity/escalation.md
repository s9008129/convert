# Stage 04 Escalation — Issue #18 Local V2

TASK_ID: T20260924-1523-01-issue18-local-fidelity
PLAN_REVISION: 4

## Affected approved items

- GOAL/REQ: `GOAL_CONTRACT.PRIMARY_OUTCOME`, `R2`, `R5`, `R6`, `R7`, `R8`, `R10`, and `R12`.
- DEC: `DECISION_CONTRIBUTION_MATRIX` selected/core relation veto; `SEMANTIC_CONTRACT_AND_FAILURE_CONTAINMENT` selected causal claim rejection rule.
- WAVE: `W4`, `W5`, `W6`, `W7`, and `W8`.
- H-* contract anchors: `H-C1-selected-causal-source-to-delivery`, `H-FIDELITY-FIREWALL`, `H-PROFILE-CONTROLS` (the approved handoff’s selected-claim, firewall, and runtime-profile acceptance obligations).

## New fact

Independent acceptance found a conclusive semantic gate defect: an inverted
causal predicate can be accepted by the V2 fidelity firewall. The live V2 path
also does not pass `selected_claim_id`, so the required record-level causal
veto is not wired. The approved C1 source→facts→render→delivery contract is
therefore not enforced.

Additional implementation gaps found in the same acceptance run are: live
extraction does not request number/date/attribution/condition fields; the live
path lacks template coverage maps, source-tag/entity provenance checks, and
cross-section duplicate auditing; and approved Qwen/Gemma candidate profile
controls and A/B selection are not wired (extraction temperature is fixed at
0.3).

## Decisive evidence

- Independent report: `.agent/tasks/T20260924-1523-01-issue18-local-fidelity/e2e/attempt-01/e2e_report.md`.
- Report SHA-256: `d83a6197756894b5bb294cf31ff322a3ea085c6261751c32ed8409d7ba8c2d99`.
- C1 result in that report: `FAIL`; the deterministic probe supplied a causal
  claim whose source contained the expected predicate while rendered output
  used a different predicate, yet `fidelity_firewall(..., selected_claim_id=...)`
  returned `accepted=True` and no relation issue.
- Code evidence: `backend/services/local_pipeline_v2.py:162-171` skips checks
  when `claim_id not in rendered`, although `render_section` emits no claim ID;
  `backend/services/summarization.py:2311-2313` invokes the firewall without
  `selected_claim_id`.

## Why the approved contract is invalid

The current implementation’s acceptance behavior contradicts the approved
semantic invariant that selected causal inversion/omission rejects the record
candidate. This changes validity, gate/veto behavior, and failure propagation;
it is not a mechanical implementer repair. The isolated A–I suite passing does
not establish live selected-claim correctness because its claims are directly
constructed and do not exercise the broken integration wiring.

## Safe repository state

No product code, canonical plan, handoff, or existing E2E attempt was modified
for this escalation. The Stage 04 execution status snapshot remains unchanged.
The repository remains on `issue-18-first-divergence-diagnostic` at the
approved anchor HEAD `eb3ca049cc72d21d2f4db974db5314b5f399d736`; all current
product and task changes remain recoverable in the working tree and existing
backup branches.

## Decision required from Stage 01

Replan and independently review a revised architecture that makes selected
claim identity explicit through section rendering/firewall evaluation and
enforces predicate direction before delivery. The revision must also decide
the minimum live contract for numeric/date/attribution extraction, template
coverage and cross-section dedupe, and the runtime capability/profile
selection controls required by `W7`/`C14`. Preserve the no-hidden-fallback,
local uncertainty, cloud-invariance, and privacy invariants.

## Verification already run

Stage05 attempt-01 observed: C2 `9 passed`; C3 safe-env `13 passed, 41
deselected`; full suite `826 passed, 2 skipped`; docs check exit 0 with two
pre-existing version warnings; diff check clean; C1 `FAIL`; Qwen live V2
invocation completed; Gemma was not loaded; C10 frozen evaluator/baseline and
C14 candidate controls remained unavailable. Full evidence is retained in the
referenced append-only E2E report.

## Stage 04 escalation — attempt06 invalid evidence and conflict containment

Date: 2026-09-25. Current approved identity remains Plan R9 SHA-256
`63b30bcae58abbba98e15a9d3b62ef23da391cbcbded19d6e22e494b29f1ba67` and
handoff SHA-256
`78ffbdec979529e0e1648054cda32abe86cc94f596d1ecdd08a763d23d0beb71`.
The immutable Stage05 attempt06 report and evidence are preserved.

### New safe evidence

- Parent-provided aggregate of the controlled Qwen output: 4 extraction chunks
  parsed, 87 claims, 7 `same_evidence_value` conflicts, valid span IDs
  `span-1..span-4`, 54 claims with valid references, and 33 claims containing
  unknown references (17 unique unknown IDs). Five of seven detected conflicts
  include unknown references. No raw transcript/model output was read or
  copied into this artifact.
- Attempt06 reports the failure occurs before the `v2.ledger` diagnostic event.
  Current production order consolidates claims and raises on conflicts before
  validating asserted claims against the evidence-span map. Current R4 grouping
  uses the sorted evidence-reference tuple, so a chunk-wide span ID can be
  treated as proof that distinct statements in that chunk are the same evidence.

### Load-bearing ambiguity requiring Stage01 decision

- R1 explicitly requires missing evidence for an optional claim to degrade
  locally and missing evidence for the selected/core claim to block acceptance.
  But the current approved implementation has no optional/core claim mapping:
  `template_section_plans` assigns every asserted claim to a required slot and
  leaves `optional_claim_ids` empty; the live `selected_claim_id` is inferred as
  the first causal/conditional assertion and is not mapped to the diagnostic
  target claim specification.
- Downgrading every non-first claim with invalid references would invent
  optionality and could silently drop a required claim. Failing the entire run
  for every unknown reference would violate R1's local-degradation contract.
  Keeping an invalid-reference claim asserted would allow it to enter conflict
  analysis, section planning, or prompts, violating provenance safety.
- W3 requires normalized claim/evidence identity and overlap, and the parent has
  confirmed that a coarse chunk span alone is not proof of same evidence. The
  plan does not currently define a source-occurrence anchor/overlap rule for
  when two distinct propositions within one chunk constitute a same-evidence
  conflict versus separate supported statements. Changing this classification
  affects whether V2 stops before rendering and how claims are omitted, so it is
  not safe to invent as a bounded mechanical repair.

### Stop condition and requested planner decisions

No product code or tests were changed for this follow-up. Stop before changing
claim status, requiredness, conflict eligibility, or run gating. Stage01 must
decide (a) the authoritative selected/core-claim identity available to the live
pipeline, (b) which claims are optional versus required/core when evidence refs
are missing, and (c) the deterministic source-occurrence/overlap criterion for
R4 conflict identity within a chunk. Then re-review/recompile if the decisions
change semantic behavior. Existing Stage05 attempt06 files remain untouched.

IMPLEMENTATION_STATUS: BLOCKED (unfinished R1/R4 handling cannot safely proceed
without the planner's claim-classification/evidence-identity decision)
CORE_ACCEPTANCE_STATUS: BLOCKED
REQUIRED_VERIFICATION_STATUS: INCOMPLETE
INDEPENDENT_ACCEPTANCE_STATUS: PENDING planner-directed Stage04 repair and fresh
Stage05 acceptance
TASK_CLOSURE_STATUS: CORE_ACCEPTANCE_BLOCKED
NEXT_ACTION: Stage01 resolves the three decisions above; do not use a blanket
unknown-reference veto, silently drop claims, fabricate statement offsets, or
read/expose private payloads.

## Stage 04 escalation — R16 backend capability scope gap

Date: 2026-09-24 UTC (2026-09-25 Asia/Taipei). Current approved identity is
Plan revision 16 SHA-256
`5a5a6663e2b1258aa9b345d7dbe08249ea6661a0849ce5ba0f82dd7ad8dbc647`, Review
attempt16 report SHA-256
`161931f6cd3ef3f92a10399cc2a4c3452885a491d95dd16cacb88b119cc8ce62`, and
handoff SHA-256
`6a242ddbc7f55e5c2cc0979a7678dc989c86768355f95794f4e65b9d8cbb55fa`.
Review attempt16 approved the cited Plan revision. This entry records a new
implementation-scope discovery after the approved R16 handoff; do not treat the
existing approval as covering the missing Ollama decision.

### Affected approved requirements

- **Decision P / W2:** native structured-output capability is required per
  active backend and loaded model/instance; `SUPPORTED` requires a normal,
  schema-valid source-free probe; only a narrow explicit unsupported-capability
  result permits strict-JSON/Pydantic fallback. Unknown capability must stop
  before source-bearing generation.
- **C2:** capability classification is a CORE integration contract; missing or
  false backend capability coverage is a task regression.
- **C16:** schema/runtime retry classification is CORE; provider/runtime errors
  must not be reclassified or silently routed into fallback/repair.

### New read-only review evidence

- The newly added `_probe_native_schema_capability` implementation in
  `backend/services/summarization.py` currently recognizes only `engine ==
  "lmstudio"` and requires an LM Studio `selection.loaded_instance_id`;
  otherwise it returns `UNKNOWN`.
- `_select_local_engine` and `_generate_with_local_engine` also support the
  existing `ollama` engine. For an Ollama-selected V2 invocation, the current
  capability probe therefore returns `UNKNOWN`, and the V2 path raises before
  sending any user source. This is fail-loud, but leaves V2 unavailable on an
  existing backend path.
- The generation dispatcher has no native schema-probe/strict-schema support
  for Ollama: the Ollama branch ignores `response_format`, which is currently
  passed only through the LM Studio adapter. Therefore LM Studio success does
  not establish the per-backend contract for Ollama.
- The R16 plan requires a per-backend contract; it does not specify whether
  Ollama can produce the exact fact-payload schema, how its source-free
  capability probe should be represented, or whether V2 is intentionally
  scoped to LM Studio. Choosing a JSON mode, unsupported-response allowlist,
  fallback, or backend exclusion changes eligibility/fallback behavior and is
  not a bounded implementation detail.
- This gap was identified by the Stage 04 parent’s read-only contract review;
  it was not discovered by the passing LM Studio-focused tests. The existing
  tests verify the LM Studio probe/classifier and fake-runtime fallback, but do
  not prove Ollama capability semantics.

### Required Stage 01 decision

Define V2 behavior for Ollama against the user's per-backend capability and
strict-JSON fallback requirement. Choose and specify either (a) an Ollama
source-free probe that tests the exact fact-payload schema plus a narrow,
provider-specific explicit-unsupported classification and correctly wired
schema-constrained extraction, or (b) a deliberate, documented V2 backend
scope/exclusion with fail-loud behavior before user-source generation. The
decision must state what counts as `SUPPORTED`, `UNSUPPORTED`, and `UNKNOWN`,
whether fallback is authorized for that backend, and its focused contract tests.
Do not choose either option in Stage 04. Re-review the revised plan and compile
a fresh handoff before resuming implementation.

### Safe state and verification already observed

- All current working-tree changes are uncommitted and preserved. No reset,
  stash, rebase, force-push, or cleanup was performed. No commit or push was
  made. The product diff, tests, documentation change, R16 W0 snapshots, and
  test outputs remain available for the replanned implementer.
- No live-source, meeting-data, C1 acceptance, or user-content model call was
  made during this Stage 04 work. The existing Qwen runtime audit was read-only;
  no model was loaded or unloaded.
- Before this Ollama gap was discovered, focused tests observed `157 passed`;
  full `tests/` observed `904 passed, 2 skipped`; the cloud contract selection
  observed `13 passed, 41 deselected`; `scripts/check_docs.sh` exited 0 with the
  same two README version warnings recorded at W0; `git diff --check` exited 0.
  These results do not close the uncovered Ollama capability contract or C2/
  C16 for that backend.
- Stage 04 must stop product edits and additional implementation verification
  at this semantic boundary pending R17 review and fresh handoff. Preserve the
  current diff unchanged until then.

IMPLEMENTATION_STATUS: BLOCKED (unfinished Ollama capability/fallback contract
cannot safely continue without Stage 01's per-backend scope decision)
CORE_ACCEPTANCE_STATUS: BLOCKED (Decision P/C2/C16 capability coverage remains
incomplete for an existing supported local backend)
REQUIRED_VERIFICATION_STATUS: INCOMPLETE
INDEPENDENT_ACCEPTANCE_STATUS: PENDING replanned Stage 04 and fresh Stage 05
TASK_CLOSURE_STATUS: CORE_ACCEPTANCE_BLOCKED
NEXT_ACTION: Stage 01 decides the V2 Ollama capability/probe/fallback contract;
  then obtain independent R17 review and a matching fresh handoff. Do not infer
  Ollama support, silently fall back, or send user source while capability is
  UNKNOWN.
