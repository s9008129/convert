# Plan Review Report

## REVIEW_METADATA
- TASK_ID: T20260924-1523-01-issue18-local-fidelity
- REVIEW_ATTEMPT: 01
- REVIEWED_PLAN_REVISION: 2
- REVIEWED_PLAN_SHA256: 84f3ab24b14dd76e6d9f864ec95d13df2a04877b97f138a8b8fef9fa781fe8cd
- PLAN_SNAPSHOT_PATH: .agent/tasks/T20260924-1523-01-issue18-local-fidelity/review/attempt-01/plan_snapshot.md
- Repository anchor observed: branch `issue-18-first-divergence-diagnostic`, HEAD `eb3ca049cc72d21d2f4db974db5314b5f399d736` (`eb3ca04`); worktree has a pre-existing modification to canonical `plan.md` at review start
- Reviewer runtime/model: Codex GPT-5

## OWNER_VERDICT
The plan targets the stated outcome: an evidence-grounded local V2 path that preserves source facts and proves selected-claim and blind-quality acceptance. Structured provenance, deterministic consolidation/firewall, section rendering, guarded patching, and local/E2E acceptance are essential; runtime tuning, performance metrics, and held-out data are correctly supporting or best-effort. The selected-claim and schema gates are scoped appropriately, and the plan keeps cloud behavior and private content protected. However, the verification matrix does not instantiate the required v4.2 status/waiver fields, and the cloud must-not-break baseline is not concretely identified. Those gaps can make Stage 04/05 classification and regression decisions non-reproducible, so revision is required before handoff.

## GOAL_BASELINE
- **Primary outcome:** redesign the local Gemma 4 31B/Qwen 3.8 27B meeting-record path around immutable source evidence, structured facts, deterministic validation, and controlled generation, reaching the stated fresh blind quality threshold with zero major fidelity hard fails.
- **Essential evidence:** selected causal claim remains correct source→extraction→ledger→render→delivery; fail-first coverage for causal/negation/condition/numbers/entities/attribution/overlap/patch regression; local E2E and blind 3+3 acceptance; privacy and cloud/template invariants.
- **Optional/deferred:** richer unverified transcript correction/glossary enrichment, runtime/performance diagnostics, and held-out data where no privacy-safe source exists; these must not become global blockers.
- **Global blockers justified by the goal:** selected/core provenance or causal correctness and schema-valid core facts may block that record/CORE acceptance; missing frozen evaluator blocks quality acceptance/closure only, not implementation. Optional enrichment must degrade locally.

## GOAL_ALIGNMENT
The PRIMARY_OUTCOME and CRITICAL_PATH match the authority source. The plan does not replace the architecture goal with prompt tuning, and it explicitly rejects direct experiment-branch merges, hard-coded issue claims, and an LLM judge as truth oracle. CORE/SUPPORTING/BEST_EFFORT distinctions are present and generally aligned.

## NECESSITY_AND_TRACEABILITY
R1–R7, R9–R10 and R12 trace to source integrity, fidelity, rollback, acceptance, or privacy/audit obligations. R8 and R11 are supporting and are explicitly non-vetoing. The selective experiment-mechanism port is constrained by concrete acceptance obligations. No untraceable material requirement was found.

## GATE_AND_VETO_AUDIT
Selected/core evidence, schema-valid core facts, and selected causal correctness have explicit scoped blocking rationale. Optional categories, runtime probes, performance, and held-out data do not veto unrelated work. The frozen evaluator is correctly scoped to quality acceptance/task closure. The plan also separates goal criticality from closure gating, but its verification rows do not fully encode the v4.2 status contract (RV-001).

## COUPLING_AND_FAILURE_CONTAINMENT
The plan contains evidence conflicts at claim/section scope, rejects only the selected/core causal failure globally for the record candidate, and rolls back failed patches byte-for-byte. V1 rollback is explicit rather than silent. Cloud/local paths remain separate. This is proportionate to the stated fidelity invariant.

## DESIGN_ECONOMY
The fact/evidence/ledger/section/firewall/patch abstractions each pay for a named fidelity or rollback obligation. The plan defers broad enrichment and wholesale experiment-branch imports. The design is large, but the authority explicitly calls for architecture-level remediation; no removable major component was identified.

## CRITICAL_PATH_AND_PRIORITY
W0–W6 and selected-claim E2E precede runtime tuning and blind acceptance. Supporting profiling and held-out validation are later and non-gating. The ordering is appropriate.

## REQUIREMENT_FIDELITY
The plan preserves raw transcript as sole truth, treats corrected text as advisory, makes causal/conditional/negated relations first-class, requires provenance, and retains explicit uncertainty. It preserves cloud semantics, v4.7.4 invariants, template/output compatibility, privacy, retry safety, and explicit degradation.

## GROUNDING_AND_DRIFT
Current repo evidence supports the stated HEAD/branch, the existing `claim-attempt-3-baseline.json` first divergence at `extraction.chunk.3.raw`, and the current free-text extraction→merge→whole-record→refinement path. The two named experimental branches exist locally. The prior revision-1 handoff/execution artifacts are stale by design and must be regenerated only after this revision is approved; the plan states that requirement.

## ARCHITECTURE_AND_CONTRACTS
The additive opt-in V2 path, explicit V1 selection, strict JSON fallback, one schema-only repair, deterministic conflict preservation, and model-independent quality policy are coherent. The stale revision-1 handoff must not be consumed for implementation; Stage 03 freshness checking is required after approval.

## DATA_SECURITY_RELIABILITY
The source hash/span model, ignored runtime raw storage, redacted tracked diagnostics, privacy audit, no raw private data in GitHub, explicit rollback, and no silent fallback address the relevant risks. No new security or persistent-data migration defect was found.

## IMPLEMENTATION_SEQUENCE
Fail-first contracts precede behavior changes; data model and extraction precede deterministic ledger/rendering; selected-claim E2E precedes blind cohort. The sequence is sound, subject to the verification-baseline corrections below.

## TESTABILITY_AND_ACCEPTANCE
The A–I synthetic classes and selected-claim chain are concrete and outcome-oriented. The 3+3 blind gate preserves per-output/per-dimension thresholds and zero major hard fails. C6/C7 correctly remain SUPPORTING repository-health checks even though the user DoD makes them HARD_CLEAN closure gates. The matrix is missing the required per-check status/waiver fields and lacks a concrete cloud golden baseline (RV-001, RV-002).

## SCOPE_AND_COMPLEXITY
Scope is broad but directly authorized by the architecture-v2 goal. No direct merge, unrelated ASR/UI work, raw-data retention, or model-specific fidelity policy is introduced. V1 remains a bounded rollback path.

## FINDINGS

### RV-001
- severity: MAJOR
- category: TEST
- affected plan: `VERIFICATION_AND_CLOSURE_MATRIX` (C1–C13), `HANDOFF_HINTS`
- evidence: `/Users/hsiaojohnny/.codex/policies/workflow-routing.md` §7.3 requires each material check to declare `WAIVER_ALLOWED`, `WAIVER_AUTHORITY`, `CHECK_RESULT`, and `WAIVER_STATUS` in addition to criticality, evidence role, closure gate, baseline rule, and failure classification. The plan supplies a combined `WAIVER` column (`NO / NONE`) but omits those required fields and initial states.
- failure/rework mechanism: Stage 04/05 cannot unambiguously route `NOT_RUN`, `BLOCKED`, `INCOMPLETE`, or formally waived verification, and an implementer/verifier could infer or self-waive a closure gate differently from the approved plan. This is especially consequential for the blind evaluator/environment blockers and HARD_CLEAN repository checks.
- smallest required correction: add the v4.2 fields to every C1–C13 row, initially `CHECK_RESULT: NOT_RUN`, `WAIVER_STATUS: NOT_REQUESTED` (or `NOT_ALLOWED` where applicable), with explicit `WAIVER_ALLOWED` and `WAIVER_AUTHORITY` (`NONE` unless the authoritative owner grants one); preserve original results when a waiver is later used.

### RV-002
- severity: MAJOR
- category: TEST
- affected plan: `W0 — Re-baseline / protect`, C3 in `VERIFICATION_AND_CLOSURE_MATRIX`, `RISKS_AND_UNKNOWNS`
- evidence: C3 declares `BASELINE_REQUIRED: YES` and a `HARD_CLEAN` gate for cloud semantics/golden regression and v4.7.4 invariants, but W0 only names focused/full/docs baselines and does not identify the cloud golden fixture/command, artifact path, or exact missing-baseline classification. The current repository call path has separate cloud builders, so this is a load-bearing must-not-break boundary.
- failure/rework mechanism: After mutation, a cloud regression cannot be reproducibly separated from pre-existing debt or environment/tooling absence. The implementer may either overclaim unchanged cloud behavior or discover too late that the required baseline was unavailable, invalidating acceptance and forcing rework.
- smallest required correction: define the exact pre-change cloud contract/golden command and redacted artifact (or equivalent fixture/hash), the same-environment rerun, and the explicit `BLOCKED`/`INCOMPLETE` routing when that baseline cannot be established; retain baseline-vs-task-regression evidence.

## REQUIRED_PLAN_CHANGES
1. Revise the verification matrix so every material check has the complete v4.2 status/waiver schema and initial `NOT_RUN`/`NOT_REQUESTED` values, including explicit waiver authority.
2. Specify the C3 cloud golden/contract baseline command or fixture, stored redacted evidence, and missing-baseline routing before mutation.
3. Increment `PLAN_REVISION`, then obtain a fresh Stage 02 review before Stage 03 handoff.

## RESIDUAL_MINOR_NOTES
- The current canonical plan was modified in the worktree at review start; this review is bound to the captured SHA-256 snapshot only.
- The existing handoff is revision 1 and must remain unused; Stage 03 should archive/regenerate it for approved revision 2 (or the subsequent revision).
- The frozen evaluator and unrounded Gemini baseline remain an explicit quality-acceptance dependency; the plan correctly does not infer quality when unavailable.

FINAL_STATUS: PLAN_REVISION_REQUIRED
NEXT_ACTION: Stage 01 revision mode on the same TASK_ID; apply RV-001 and RV-002, increment PLAN_REVISION, and request a fresh Stage 02 review.
