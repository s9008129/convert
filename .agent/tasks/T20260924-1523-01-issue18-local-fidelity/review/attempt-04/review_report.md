# Plan Review Report

## REVIEW_METADATA

- TASK_ID: T20260924-1523-01-issue18-local-fidelity
- REVIEW_ATTEMPT: 04
- REVIEWED_PLAN_REVISION: 5
- REVIEWED_PLAN_SHA256: 87dab761f915514a83000918a95a64b3dba4a55f3e97813ea6d48ccf0ea36727
- PLAN_SNAPSHOT_PATH: `.agent/tasks/T20260924-1523-01-issue18-local-fidelity/review/attempt-04/plan_snapshot.md`
- Repository anchor observed: branch `issue-18-first-divergence-diagnostic`, HEAD `eb3ca049cc72d21d2f4db974db5314b5f399d736` (`eb3ca04`)
- Working tree observed during review: dirty with the expected Stage 04/task artifacts plus modified `backend/core/config.py` and `backend/services/summarization.py`; no unrelated owner change could be independently established from the plan alone.
- Reviewer runtime/model: Codex GPT-5
- Review mode: read-only for product code and canonical `plan.md`; only attempt-04 review artifacts were written.

## OWNER_VERDICT

Revision 5 is materially responsive to the Stage 05 replan trigger. It preserves the requested raw-source/evidence architecture and explicitly requires structured high-risk extraction fields, raw-evidence predicate validation, claim identity at the live gate, template-derived section plans, one LLM call per planned section, deterministic assembly, live coverage/provenance/source-tag/deduplication checks, targeted patch rollback, and capability-validated Qwen/Gemma candidate controls. The critical path is generally proportionate and optional enrichment/held-out/performance work remains locally degrading or non-gating.

The plan is not yet review-approvable because its durable safety facts and criticality/gating semantics are internally inconsistent. These are small textual corrections, but they affect the Stage 04 precondition and whether profile acceptance is a supporting diagnostic or an unconditional CORE closure gate. A fresh revision is required before Handoff.

## GOAL_BASELINE

- **Primary outcome:** redesign the local Gemma 4 31B/Qwen 3.8 27B meeting-record pipeline around immutable raw-source evidence, structured fact/evidence architecture, deterministic validation, and controlled generation, reaching the fresh blind quality target with zero major fidelity hard fails.
- **Success evidence:** selected causal claim correctness source→facts→render→delivery; regression coverage; cloud/template/privacy invariants; fresh Gemma/Qwen E2E; and blind 3+3 where every output/dimension reaches at least 0.80 of the original unrounded Gemini median with zero adjudicated major hard fails.
- **Must not break:** cloud semantics, v4.7.4 invariants, template/output contracts, privacy/provenance, retry/runtime-selection safety, explicit degradation and V1 rollback.
- **Non-goals:** direct experimental-branch merge, hard-coded private facts, tracked raw content, a second LLM truth oracle, lowered quality threshold, broad ASR/UI work.
- **Smallest safe critical path:** evidence/schema → validated structured extraction → deterministic ledger/conflict handling → raw-evidence source-alignment firewall → template-derived section render/assembly → guarded targeted patch/rollback → selected-claim live E2E → fresh model and blind acceptance.

## TOP_DOWN_REVIEW

### GOAL_ALIGNMENT

R1–R7, R9–R10, and R12 trace directly to source fidelity, semantic preservation, rollback, acceptance, or privacy/audit invariants. R8 and C14 preserve the authority source's explicit runtime-control and run-to-run-variance requirement, rather than treating one blind cohort as profile selection. R11/C11/C12 remain supporting or diagnostic. No unrelated product scope was introduced.

### PREDICATE_DIRECTION_AND_RAW_EVIDENCE

The replan correctly changes the firewall contract from prose claim-ID presence to structured claim metadata plus ordered raw evidence and rendered relation metadata (TARGET_CONTRACT §5; R6; W4–W6; C1). It explicitly forbids silently skipping a required relation when an opaque claim ID is absent from prose and requires the Stage 05 inverted-predicate probe at the live boundary. This directly addresses the confirmed defect in `escalation.md` and `e2e/attempt-01/e2e_report.md`.

### EXTRACTION_SCHEMA_AND_FAILURE_CONTAINMENT

W2 now requests relation direction, polarity, condition/dependency, number/unit, date, attribution, uncertainty/status, and evidence references; strict JSON/Pydantic is a valid compatibility path when native schema output is unavailable. Exactly one schema-only repair followed by explicit V2 failure and no hidden V1 fallback is proportionate. Unknown/ambiguous optional facts are not globally invalidated, while selected/core evidence has an explicit veto rationale. The plan should retain this per-claim/per-section containment when defining implementation details; the current text is sufficient at plan level.

### TEMPLATE_RENDERING_AND_LIVE_VALIDATORS

W4 and TARGET_CONTRACT §4 require plans derived from existing production templates, allowed claim/evidence inputs, one section-scoped model call, structured relation metadata outside user prose, and deterministic template-order assembly. W5 names the missing live mechanisms: source-derived number/date checks, entity provenance, attribution, source-tag↔span validation, cross-section claim-ID dedupe, coverage, and template-scoped term correction. This is goal-aligned and bounded by “selective mechanisms only”; it does not authorize wholesale branch copying. W8 correctly requires live-boundary evidence rather than helper-only tests.

### GATES_AND_SCOPE

Selected/core evidence, schema validity, and selected causal correctness have explicit scoped veto rationales. Optional enrichment, unsupported parameters, held-out data, and performance diagnostics do not globally veto unrelated sections. C10 and C14 correctly preserve missing evaluator/baseline and unavailable model/hardware as named scoped blockers, not fabricated passes. The remaining inconsistency is the profile criticality finding below.

### DESIGN_ECONOMY_AND_PRIORITY

The evidence/fact/ledger/section/firewall/patch abstractions each pay rent against a documented fidelity or rollback failure. W0–W6 precede profile tuning and blind acceptance; optional work is deferred. The plan does not repeat the disproven “put more transcript in final prompt” strategy.

## BOTTOM_UP_REVIEW

### REPOSITORY_GROUNDING

Branch and HEAD match the authority/plan anchor. The observed dirty tree contains Stage 04/task artifacts and product changes; no unrelated owner change was established by this review. `execution.md` is still bound to revision 4, as expected for the prior implementation snapshot; the plan correctly requires a fresh Handoff and Stage 04 after approval. W0's focused cloud baseline and safe-environment routing are reproducible and preserve the `/app/data/logs` baseline distinction.

### FINDING RV5-001 — MAJOR — STALE/CONTRADICTORY DIRTY-WORKTREE FACTS

- **Category:** repository grounding / safety precondition.
- **Affected sections:** `META.WORKTREE_AT_PLANNING`; `SOURCE_OF_TRUTH_AND_BASELINE`; W0; `MIGRATION_COMPATIBILITY_ROLLBACK`.
- **Evidence:** the plan says `WORKTREE_AT_PLANNING` contained the Stage 04 implementation and task artifacts, but later says “Worktree was clean at planning.” Current `git status --short` is dirty with exactly those task/product artifacts (including the canonical plan), and no timestamped status snapshot or explicit baseline separates expected task changes from owner changes.
- **Failure/rework mechanism:** Stage 04 could treat a dirty tree as a clean safety baseline, accidentally overwrite unrelated owner work, or misattribute current changes to the new replan. This undermines the required W0 status/backup precondition and makes the “no unrelated owner changes observed” assertion non-reproducible.
- **Smallest correction:** replace the contradictory “clean at planning” statement with the observed scoped dirty-state fact; record a redacted, timestamped status/path classification (expected task artifacts vs pre-existing owner changes), current HEAD, and backup relation. State that Stage 04 must re-check status and stop/escalate if unclassified owner changes appear. Do not clean, reset, stash, or overwrite the tree.

### FINDING RV5-002 — MAJOR — PROFILE CRITICALITY/CONTRIBUTION MATRIX CONTRADICTION

- **Category:** semantic contract / acceptance gating.
- **Affected sections:** R8; `DECISION_CONTRIBUTION_MATRIX` runtime profile row; W7; C14; `DEFINITION_OF_DONE`; OWNER_CHECK.
- **Evidence:** R8 classifies runtime profile/capability control and repeated Qwen/Gemma selection as `CORE`, and C14 is `CORE` with `HARD_CLEAN`; however, the contribution matrix labels “Runtime profile/capability probes” `SUPPORTING` with `Global veto? No`, while OWNER_CHECK says supporting profile controls “cannot veto unrelated valid sections.”
- **Failure/rework mechanism:** Implementers/verifiers cannot determine whether C14/profile selection is a required product-outcome gate, a closure-only quality gate, or a non-vetoing supporting diagnostic. They may either block valid core records on unavailable runtime/profile evidence or incorrectly close without the explicit variance-control requirement. This changes requiredness and closure semantics.
- **Smallest correction:** split the row into (a) model-independent runtime capability/profile wiring needed to execute the requested controlled path and (b) candidate sampling/selection evidence. State one consistent rule: unavailable model/evaluator remains scoped `CORE_ACCEPTANCE`/`INDEPENDENT_ACCEPTANCE` blocked; profile diagnostics do not veto unrelated records; C14 is required for task closure only if the authority's profile-selection obligation is retained as CORE. Align R8, the matrix, C14, W7/W8, and Definition of Done, including the exact status/waiver behavior.

## STATUS / BASELINE / WAIVER AUDIT

- The plan's C1–C14 rows include the required v4.2 dimensions: goal criticality, evidence role, closure gate, baseline requirement, failure classification, waiver allowance/authority, check result, and waiver status.
- `WAIVER_ALLOWED: NO` / `WAIVER_AUTHORITY: NONE` is coherent for unresolved CORE fidelity, privacy, and acceptance obligations; the plan does not self-waive them.
- C10 correctly uses `BASELINE_REQUIRED: YES` and routes a missing frozen evaluator/original unrounded Gemini baseline to a scoped quality blocker rather than a fabricated PASS. C14 similarly names the missing evaluator and unavailable model/hardware blockers, but must be reconciled with RV5-002's criticality decision.
- C3 correctly distinguishes safe-environment PASS from default logger-path environment BLOCKED and requires same-command rerun/golden evidence for shared-helper changes.
- Current observed status is not a new acceptance result: Stage 04 `execution.md` remains revision-4 `IMPLEMENTATION_STATUS: COMPLETE`, `CORE_ACCEPTANCE_STATUS: BLOCKED`, `REQUIRED_VERIFICATION_STATUS: INCOMPLETE`, `TASK_CLOSURE_STATUS: PENDING_REQUIRED_VERIFICATION`; Stage 05 attempt-01 remains revision-4 and routed the semantic defect to replan. Revision 5 must not inherit those results as approval or rewrite them.

## REQUIRED_PLAN_CHANGES

1. Correct the contradictory worktree statements and persist a scoped status/classification snapshot or explicit equivalent before the next implementation wave.
2. Resolve the runtime-profile criticality/closure contradiction across R8, the contribution matrix, C14, W7/W8, OWNER_CHECK, and Definition of Done. Preserve the authority's explicit profile controls and repeated-sampling requirement while keeping unavailable runtime/evaluator blockers scoped and status-aware.
3. Increment `PLAN_REVISION` by exactly one and obtain a fresh Stage 02 review; do not regenerate Handoff or implement product changes from this unapproved revision.

## RESIDUAL_MINOR_NOTES

- The plan's current runtime profile details otherwise match the authority: Qwen `thinking=OFF, temperature=0.7, top_p=0.8, top_k=20`; extraction candidates `0.3/0.5/0.7`; Gemma `thinking=OFF, temperature=1.0, top_p=0.95, top_k=64`; N≥5 preferred/N=3 minimum; median/worst/range/hard-fail reporting and fidelity-first selection.
- Native structured output absence is correctly treated as a compatibility path, not a blocker.
- The prior attempt-03 approval is correctly not inherited: it binds only to revision 4/hash `72d23f2f...`; this review binds to revision 5/hash recorded above.

FINAL_STATUS: PLAN_REVISION_REQUIRED
NEXT_ACTION: Stage 01 revision mode on the same TASK_ID; correct RV5-001/RV5-002, increment to PLAN_REVISION 6, then obtain a fresh Stage 02 review.
