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
