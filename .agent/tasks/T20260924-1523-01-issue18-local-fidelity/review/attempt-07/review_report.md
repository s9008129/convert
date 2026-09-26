# Plan Review Report

## REVIEW_METADATA
- TASK_ID: T20260924-1523-01-issue18-local-fidelity
- REVIEW_ATTEMPT: 07
- REVIEWED_PLAN_REVISION: 8
- REVIEWED_PLAN_SHA256: 5001ef3e1b5bdfc041d4dff1c97a05aab0f2858f68b9dfb673204dbcf243ec6b
- PLAN_SNAPSHOT_PATH: `.agent/tasks/T20260924-1523-01-issue18-local-fidelity/review/attempt-07/plan_snapshot.md`
- Repository anchor observed: branch `issue-18-first-divergence-diagnostic`, HEAD `eb3ca049cc72d21d2f4db974db5314b5f399d736` (`eb3ca04`)
- Working tree observed: dirty with the expected Stage 04 candidate and task artifacts; no reset, clean, stash, or overwrite was performed.
- Reviewer runtime/model: Codex GPT-5
- Review mode: read-only for product code and canonical `plan.md`; only attempt-07 artifacts were written.

## OWNER_VERDICT

The plan remains aligned with the requested Local Meeting Record Architecture V2: immutable raw evidence, typed claims and provenance, deterministic consolidation and source alignment, section-scoped generation, guarded repair/rollback, controlled Gemma/Qwen execution, and fresh blind quality acceptance. The essential path is clear, and optional enrichment/held-out/performance work remains non-gating.

Revision 8 resolves RV7-001 for the Stage 04 cases: C9/C10/C14 are explicitly CORE acceptance inputs and required HARD_CLEAN verification items, but never per-record vetoes; known authority/environment blockers preserve implementation, map CORE acceptance to `BLOCKED`, map aggregate verification to `INCOMPLETE` or phase `BLOCKED`, keep independent acceptance `PENDING`, and route to `CORE_ACCEPTANCE_BLOCKED`; not-run checks route to `NOT_RUN`/`PENDING_CORE_ACCEPTANCE`; and Stage 05 has an `ACCEPTANCE_BLOCKED` route with an immutable Stage 04 snapshot.

One material preservation ambiguity remains in the Stage 05 row: it says to set the current `CORE_ACCEPTANCE_STATUS` to `BLOCKED` whenever Stage 05 cannot obtain C9/C10/C14 acceptance, while v4.2 §7.8 requires Stage 05 to preserve the Stage 04 implementation/core/required-verification facts. The plan should state the condition under which Stage 05 may newly mark current CORE acceptance blocked (for example, when the Stage 04 value was already `BLOCKED` or `NOT_RUN`) and otherwise preserve a Stage 04 `PASS` value while setting independent acceptance `BLOCKED`. Until that is explicit, I cannot approve this semantic routing revision.

## GOAL_BASELINE

- **Primary outcome:** redesign the local Gemma 4 31B/Qwen 3.8 27B meeting-record pipeline around immutable raw-source evidence, structured fact/evidence architecture, deterministic validation, and controlled generation, reaching the fresh blind quality target with zero major fidelity hard fails.
- **Success evidence:** selected causal claim correctness source→facts→render→delivery; regression coverage; cloud/template/privacy invariants; fresh Gemma/Qwen E2E; and blind 3+3 where every output/dimension reaches at least 0.80 of the original unrounded Gemini median with zero adjudicated major hard fails.
- **Must not break:** cloud semantics, v4.7.4 invariants, template/output contracts, privacy/provenance, retry/runtime-selection safety, and explicit V1 rollback.
- **Non-goals:** direct experimental-branch merge, hard-coded private facts, tracked raw content, a second LLM truth oracle, lowered quality threshold, and broad ASR/UI work.
- **Smallest safe critical path:** evidence/schema → validated structured extraction → deterministic ledger/conflict handling → raw-evidence source-alignment firewall → template-derived section render/assembly → guarded targeted patch/rollback → selected-claim live E2E → fresh model and blind acceptance.

## GOAL_ALIGNMENT

The plan's primary outcome, success evidence, and critical path match the authoritative user attachment. R1–R7, R9–R10, and R12 directly serve source fidelity, semantic preservation, rollback, requested model acceptance, privacy, and durable delivery. R8 and C14 are justified by the explicit controlled-runtime and repeated-sampling requirement. Supporting diagnostics and held-out evaluation remain non-gating.

## NECESSITY_AND_TRACEABILITY

Immutable evidence spans, typed fields, ledger consolidation, section plans, rendered relation metadata, source alignment, targeted rollback, runtime controls, diagnostics, and the listed acceptance checks each trace to a fidelity, provenance, rollback, reproducibility, or explicit acceptance obligation. Experimental branches are used as read-only mechanism references, not merge targets. Unknown/ambiguous values remain representable rather than silently becoming facts.

## GATE_AND_VETO_AUDIT

The plan correctly separates outcome criticality, closure gating, and per-record veto authority. C9/C10/C14 are `CORE` + `OUTCOME` + `HARD_CLEAN` and required for task closure, but are explicitly not per-record gates. Selected/core source-fidelity failures can stop the affected acceptance because they invalidate decision correctness; optional enrichment, diagnostics, runtime unavailability, and evaluator authority gaps do not veto unrelated records. No waiver is permitted.

The canonical six-field table covers the requested cases: implementation remains `COMPLETE` when acceptance inputs are unavailable; CORE acceptance is `NOT_RUN` when not yet run and `BLOCKED` for scoped authority/environment blockers; required verification is `INCOMPLETE` when other evidence exists and `BLOCKED` only when its phase cannot reach a valid conclusion; independent acceptance is `PENDING` at Stage 04 and `BLOCKED` at Stage 05 when valid independent evidence cannot be obtained; closure is `PENDING_CORE_ACCEPTANCE`, `CORE_ACCEPTANCE_BLOCKED`, or `ACCEPTANCE_BLOCKED` respectively. The Stage 05 preservation wording needs the clarification recorded in RV8-001 below.

## COUPLING_AND_FAILURE_CONTAINMENT

Failure scope is otherwise narrow: optional evidence and enrichment degrade locally; selected/core relation failures affect the relevant acceptance; runtime/model/evaluator blockers affect scoped E2E/profile/quality acceptance and task closure; implementation is not downgraded solely because acceptance prerequisites are unavailable. The remaining ambiguity is whether a Stage 05 blocker can overwrite a previously proven Stage 04 CORE status.

## DESIGN_ECONOMY

The architecture passes the deletion test. The additional boundaries address the observed extraction/firewall information-integrity defect or explicit user acceptance obligations. W0–W6 prioritize source-fidelity correctness before runtime/profile and blind-quality work. No unnecessary dependency, second truth oracle, or wholesale experiment-branch port is authorized.

## CRITICAL_PATH_AND_PRIORITY

W0 protection/baseline, W1–W6 source-fidelity implementation, and W7–W9 controlled runtime acceptance/delivery are sequenced appropriately. Quality and runtime prerequisites cannot fabricate a result or block unrelated implementation. The remaining status-preservation ambiguity must be resolved before Handoff because it affects acceptance routing and evidence integrity.

## REQUIREMENT_FIDELITY

The plan retains full typed extraction fields, immutable raw evidence, deterministic conflicts, template-derived per-section rendering, live source alignment, guarded patch rollback, Qwen/Gemma controls, repeated samples, the blind 3+3 threshold, privacy, and Draft PR continuity. It does not lower the 80%/zero-major-fail requirement or revive the disproven prompt-only recovery approach.

## GROUNDING_AND_DRIFT

The current branch/HEAD, prior Stage 05 defect, dirty-tree facts, safety branches, and missing frozen-evaluator uncertainty are grounded in observed repository/task evidence. The revision-8 hash was independently computed and matches the requested hash. Existing Stage 04/05 artifacts are historical evidence and are not treated as acceptance for this revision. W0 correctly delegates the timestamped redacted path classification to Stage 04 before mutation.

## ARCHITECTURE_AND_CONTRACTS

The source→structured→ledger→section-render contract is explicit, including relation metadata outside prose so validation cannot depend on claim-ID substring presence. V1 remains an explicit development rollback, cloud behavior is protected by a focused baseline, and live-boundary evidence is required. The C9/C10/C14 aggregation table now defines the previously missing Stage 04 routing. Stage 05 must additionally distinguish preserving the Stage 04 status snapshot from deriving current status after a newly encountered blocker.

## DATA_SECURITY_RELIABILITY

Raw transcript/full prompts/outputs remain runtime-local and ignored; tracked diagnostics are limited to metadata. The plan preserves fail-loud schema handling, deterministic conflicts, loaded-instance authority, retry safety, no silent V1 fallback, and privacy audit requirements. No migration or destructive operation is proposed.

## IMPLEMENTATION_SEQUENCE

W0 requires classification and baseline capture before product mutation. W1–W6 prove the source-fidelity path before W7–W9 runtime/quality selection. Handoff and Stage 04 remain correctly deferred until this review gate is resolved.

## TESTABILITY_AND_ACCEPTANCE

C1/C2 require the live causal inversion regression rather than helper-only tests. C3–C8 cover cloud, privacy, focused/full/docs, and diff checks. C9 covers fresh loaded-model E2E; C10/C14 prohibit rounded-baseline substitution and self-waiver, and retain the exact frozen-evaluator blocker label. The six-field table is testable for not-run, blocked, pending, incomplete, and acceptance-blocked paths. Add the Stage 05 preservation condition in RV8-001 before implementation.

## SCOPE_AND_COMPLEXITY

Scope is large but justified by the requested architecture-level redesign and proven live-boundary defect. Runtime/profile work is bounded to controlled acceptance/task closure, and held-out/performance work remains diagnostic. No unrelated product scope is introduced.

## FINDINGS

### RV8-001 — MAJOR — STAGE 05 CURRENT CORE STATUS MUST PRESERVE STAGE 04 PROVEN FACTS

- **Category:** SEMANTIC_CONTRACT / TEST
- **Affected plan sections:** `C9/C10/C14 STATUS AGGREGATION — CANONICAL`; W7; W8; C9, C10, and C14 matrix rows; `BLOCKING_AND_NON_BLOCKING_UNKNOWNS`.
- **Evidence:** v4.2 `workflow-routing.md` §7.8 requires Stage 05 to read the durable Stage 04 record, preserve `STAGE_04_REPORTED_IMPLEMENTATION_STATUS`, `STAGE_04_REPORTED_CORE_ACCEPTANCE_STATUS`, and `STAGE_04_REPORTED_REQUIRED_VERIFICATION_STATUS`, and not downgrade current implementation/core/required-verification solely because acceptance is blocked. Revision 8's Stage 05 table row and W7/W8 prose instead say: “If Stage05 cannot obtain valid quality/E2E acceptance ... set current `CORE_ACCEPTANCE_STATUS: BLOCKED`,” while only explicitly preserving the immutable snapshot and its required-verification value.
- **Failure/rework mechanism:** If Stage 04 has validly proven `CORE_ACCEPTANCE_STATUS: PASS` (or another non-blocked value) and Stage 05 later encounters an authority/environment blocker, the plan permits overwriting that fact with `BLOCKED`, conflating the independent-acceptance blocker with the prior CORE result. This violates orthogonal-status preservation and can produce a contradictory report or erase evidence needed for closure routing.
- **Smallest required correction:** Define the exact Stage 05 condition: preserve the Stage 04 current implementation/core/required-verification values and always retain the immutable snapshot; set current `INDEPENDENT_ACCEPTANCE_STATUS: BLOCKED` and `TASK_CLOSURE_STATUS: ACCEPTANCE_BLOCKED`. If Stage 04 C9/C10/C14 was `BLOCKED` or `NOT_RUN`, state whether current CORE remains that value or is newly marked `BLOCKED` based on Stage 05 evidence; if Stage 04 was `PASS`, do not overwrite it solely due to an independent acceptance environment/authority blocker. Align the C9/C10/C14 table, W7, W8, and blocker section consistently, then increment the plan revision.

## REQUIRED_PLAN_CHANGES

1. Resolve RV8-001 by specifying Stage 05 preservation/transition rules for the current CORE status versus the immutable Stage 04 snapshot; keep the requested C9/C10/C14 CORE + required-verification classification and no per-record veto.
2. Increment `PLAN_REVISION` by exactly one on the same TASK_ID and obtain a fresh Stage 02 review. Do not regenerate Handoff or implement product changes from this unapproved revision.

## RESIDUAL_MINOR_NOTES

- The plan contains a duplicated “Before each implementation wave...” sentence in `MIGRATION_COMPATIBILITY_ROLLBACK`; harmless but can be removed during the required revision.
- C1's phrase “invalidates implementation” should be interpreted through v4.2's explicit CORE-failure routing so prior implementation evidence is not retroactively erased; the handoff/execution artifacts should retain the six orthogonal fields.
- Profile settings, sampling counts, frozen-evaluator handling, and dirty-worktree W0 rules are otherwise explicit and internally consistent.

FINAL_STATUS: PLAN_REVISION_REQUIRED
NEXT_ACTION: Stage 01 revision mode on the same TASK_ID; clarify Stage 05 preservation/transition for current CORE status versus the immutable Stage 04 snapshot, increment to PLAN_REVISION 9, then obtain a fresh Stage 02 review.
