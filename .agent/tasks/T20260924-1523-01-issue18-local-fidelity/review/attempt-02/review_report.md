# Plan Review Report

## REVIEW_METADATA
- TASK_ID: T20260924-1523-01-issue18-local-fidelity
- REVIEW_ATTEMPT: 02
- REVIEWED_PLAN_REVISION: 3
- REVIEWED_PLAN_SHA256: 6ec180cfa6a1d1e4cec0b057ecf7662ccd1a03961e9c15efff98d532d810fa79
- PLAN_SNAPSHOT_PATH: .agent/tasks/T20260924-1523-01-issue18-local-fidelity/review/attempt-02/plan_snapshot.md
- Repository anchor observed: branch `issue-18-first-divergence-diagnostic`, HEAD `eb3ca049cc72d21d2f4db974db5314b5f399d736` (`eb3ca04`); canonical `plan.md` was pre-existing modified work and was not edited by this review
- Reviewer runtime/model: Codex GPT-5

## OWNER_VERDICT
The revision still targets the requested local V2 architecture and correctly treats immutable source evidence, typed claims, deterministic consolidation, scoped rendering, fidelity firewalls, guarded repair, and local/blind acceptance as essential. RV-001 and RV-002 from attempt 01 are corrected: every C1–C13 row now has the v4.2 fields and C3 names a reproducible pre/post command, artifact, and missing-baseline route. However, the authoritative request explicitly requires model-specific candidate controls and repeated profile sampling to address run-to-run variance. Revision 3 only says to add generic Qwen/Gemma controls and runs a blind 3+3 quality cohort; it does not preserve the explicit candidate values, extraction A/B values, or N≥3 (prefer N≥5) profile-comparison protocol and statistics. This leaves profile selection and variance control unverifiable, so revision is required. The focused C3 command is repository-executable via the project’s `uv` environment, but the current review environment cannot establish its baseline because collection fails at the pre-existing `/app/data` logging-path environment error; the plan’s scoped BLOCKED routing is appropriate.

## GOAL_BASELINE
- **Primary outcome:** redesign the local Gemma 4 31B/Qwen 3.8 27B meeting-record pipeline around immutable raw-source evidence, structured fact/evidence architecture, deterministic validation, and controlled generation, reaching the requested fresh blind quality target with zero major fidelity hard fails.
- **Essential:** source-to-delivery selected-claim fidelity; structured extraction/provenance; deterministic ledger/consolidation and section rendering; source-grounded checks; non-regressive targeted repair; local E2E and blind acceptance; cloud/privacy/template invariants.
- **Explicit runtime-control requirement:** separate Qwen and Gemma runtime profiles, preserve the attachment’s starting controls and extraction A/B candidates, and compare candidate profiles with repeated samples (N>=5 preferred, N>=3 minimum) using median, worst case, range, and hard-fail count.
- **Optional/deferred:** unverified correction/glossary enrichment, held-out privacy-safe data, and performance diagnostics; these must not globally veto the core path.
- **Global blockers:** only source/schema/selected-core fidelity failures may block the affected CORE acceptance; missing evaluator/baseline or unavailable runtime is scoped to quality/acceptance and must not erase independently proven implementation evidence.

## GOAL_ALIGNMENT
The primary outcome, source-of-truth contract, critical path, and CORE/supporting/best-effort classifications align with the authoritative request. The plan does not collapse the task into prompt tuning or direct experimental-branch merging. The runtime-control and variance requirements are under-specified relative to the authoritative request (RV-003).

## NECESSITY_AND_TRACEABILITY
R1–R7, R9–R10, and R12 trace to source fidelity, safe generation, rollback, acceptance, or privacy/audit obligations. R8/R11 are correctly supporting, but R8’s concrete controls and R10’s acceptance wave do not trace all explicit runtime/profile-sampling obligations: a generic profile hook and blind 3+3 cohort do not establish candidate-profile selection under run-to-run variance (RV-003).

## GATE_AND_VETO_AUDIT
Selected/core provenance, schema validity, and selected causal correctness have scoped veto rationale. Optional enrichment, runtime probes, performance, and held-out data remain locally degrading/non-vetoing. The frozen evaluator is correctly limited to quality acceptance/closure. Every C1–C13 row now declares independent criticality, evidence role, closure gate, baseline rule, failure classification, waiver allowance/authority, check result, and waiver status. No new unjustified global gate was found.

## COUPLING_AND_FAILURE_CONTAINMENT
Conflicts and evidence gaps are scoped to the claim/section except for the selected CORE claim. Failed patches roll back byte-for-byte; V1 remains explicit rather than silent fallback; cloud/local paths remain separate. Runtime profile diagnostics are supporting and are not allowed to veto unrelated valid sections. The missing repeated profile comparison weakens selection evidence but does not introduce an over-broad veto.

## DESIGN_ECONOMY
The evidence/fact/ledger/section/firewall/patch abstractions each pay for stated fidelity or rollback obligations. The requested architecture warrants this scope. Adding a compact profile-sampling matrix is necessary to prove the explicit runtime-control requirement; it need not add a new production abstraction beyond the planned profile/acceptance diagnostics.

## CRITICAL_PATH_AND_PRIORITY
W0–W6 and selected-claim E2E precede runtime tuning and blind acceptance, which is appropriate. W7/W8 must include the explicit candidate-profile sampling comparison before final profile selection and before claiming controlled quality; otherwise a single chosen setting can hide the documented run-to-run variance (RV-003).

## REQUIREMENT_FIDELITY
The plan preserves raw transcript as truth, corrected text as advisory, typed causal/conditional/negated/numeric/date/attribution relations, strict schema failure, deterministic conflict handling, selected-claim protection, scoped patch rollback, cloud separation, and privacy. It preserves generic Qwen/Gemma separation, but omits the authoritative explicit initial controls and extraction A/B candidate values and omits the N>=3 repeated candidate-profile comparison protocol (RV-003).

## GROUNDING_AND_DRIFT
Repository evidence confirms HEAD/branch, the existing first-divergence baseline, separate cloud builders, and the current pytest fixtures. The C3 command names existing cloud tests and an artifact path and is rerun after changes. In this review environment, `pytest` is not on the shell PATH; the repository-standard `uv run pytest ...` reaches collection but fails before tests because the existing logger attempts to create `/app/data/logs` on a read-only filesystem. This is a baseline/environment result, not a product-plan defect; W0 explicitly routes an unavailable baseline to C3 `BLOCKED` and forbids inference. The plan’s C3 text is otherwise reproducible, though it should use the repository-standard `uv run pytest` spelling in the next revision for deterministic environment selection (minor note).

## ARCHITECTURE_AND_CONTRACTS
The additive opt-in V2 path, strict JSON fallback, one schema-only repair, deterministic ledger, scoped rendering, model-independent QualityPolicy, explicit V1 rollback, and cloud golden requirement are coherent. No semantic contract defect was found beyond the missing profile-sampling acceptance detail.

## DATA_SECURITY_RELIABILITY
The raw/source hash-span model, ignored runtime storage, redacted diagnostics, privacy audit, explicit rollback, and no silent fallback address the relevant data/security/reliability risks. Repeated profile runs must continue to exclude raw private content from tracked artifacts, consistent with the existing privacy contract.

## IMPLEMENTATION_SEQUENCE
Fail-first contracts and data model precede behavior changes; ledger/render/firewall precede runtime tuning; selected-claim E2E precedes blind acceptance. Add candidate profile sampling after capability validation and before final profile selection/quality claims, recording sample limits and the required statistics.

## TESTABILITY_AND_ACCEPTANCE
The A–I synthetic classes, selected-claim chain, cloud baseline, and blind 3+3 gate are concrete. RV-001 is resolved: all C1–C13 rows have the complete v4.2 schema with initial `NOT_RUN`/`NOT_ALLOWED` states. RV-002 is resolved: W0 specifies the exact focused command, redacted artifact, same-command post rerun, shared-helper golden requirement, and explicit C3 `BLOCKED` routing when the baseline cannot be established. The remaining gap is that no check/wave requires repeated candidate-profile samples or the attachment’s required comparison metrics (RV-003).

## SCOPE_AND_COMPLEXITY
The architecture scope remains authorized and no wholesale experimental merge or unrelated ASR/UI work is introduced. The requested profile comparison is a bounded acceptance/selection obligation, not unnecessary expansion. The plan’s title says “Plan Revision 2” while META says `PLAN_REVISION: 3`; this is a minor bookkeeping inconsistency and must be corrected before handoff.

## FINDINGS

### RV-003
- severity: MAJOR
- category: TEST
- affected plan: `R8`, `R10`, `W7 — Runtime profiles and context`, `W8 — Verification, E2E, acceptance`, `VERIFICATION_AND_CLOSURE_MATRIX` (C9/C10), `DEFINITION_OF_DONE`
- evidence: The authoritative request specifies Qwen starting controls `thinking=OFF`, `temperature=0.7`, `top_p=0.8`, `top_k=20`, extraction A/B temperatures `0.3/0.5/0.7`, independent Gemma starting controls `temperature=1.0`, `top_p=0.95`, `top_k=64`, `thinking=OFF`, and candidate-profile sampling of N>=5 (N>=3 minimum) compared by median, worst case, range, and hard-fail count. Revision 3 only says “Add separate Qwen/Gemma controls” and runs a fresh blind 3+3 cohort; no candidate values, extraction A/B, repeated profile comparison, or associated check is specified.
- failure/rework mechanism: A profile can be selected from a single run or an unrecorded setting, masking the known run-to-run variance and making it impossible to show that the chosen Qwen/Gemma controls are stable or that extraction A/B was evaluated. The final blind 3+3 cohort then conflates profile choice with acceptance and cannot reproduce the requested selection evidence, likely causing late rework or unsupported quality claims.
- smallest required correction: Add the explicit Qwen/Gemma candidate controls and extraction A/B values as candidates (subject to capability validation, not hard-coded truth); add a non-private profile-sampling acceptance row or expand C9/C10 requiring N>=3 per candidate profile (prefer N>=5), diagnostic runs excluded from the blind cohort, and recording median, worst case, range, and hard-fail count with the selection priority (hard fails, causal/attribution correctness, faithfulness, traceability, completeness, usability). Preserve scoped environment-blocked routing and state sample limitations when N=3 is used.

## REQUIRED_PLAN_CHANGES
1. Add the attachment’s explicit Qwen and Gemma starting candidate controls, Qwen extraction A/B candidates, capability-validation/downgrade rule, and the profile-selection priority.
2. Add an executable acceptance/diagnostic protocol requiring repeated candidate-profile samples (N>=5 preferred, N>=3 minimum), with median, worst case, range, and hard-fail count; distinguish these diagnostic samples from the final blind 3+3 cohort and route unavailable model/hardware as scoped environment BLOCKED.
3. Correct the plan title’s “Plan Revision 2” bookkeeping to match `PLAN_REVISION: 3`, and use repository-standard `uv run pytest` wording for C3 while preserving the existing exact command/artifact/missing-baseline routing.
4. Increment `PLAN_REVISION` and obtain a fresh Stage 02 review before Stage 03 handoff.

## RESIDUAL_MINOR_NOTES
- Current canonical `plan.md` is a pre-existing worktree modification; this review is bound to the captured snapshot/hash only.
- C3’s focused test expression matches existing cloud tests, but the plan should spell it with `uv run pytest` because that is the repository’s documented reproducible test entrypoint. The observed review environment could not establish the baseline due to the `/app/data/logs` read-only environment failure; the plan’s BLOCKED route is correct.
- The plan’s title says “Plan Revision 2” although META declares revision 3.
- The existing revision-1 handoff remains stale and must not be consumed; Stage 03 must regenerate it only after the approved revision.

FINAL_STATUS: PLAN_REVISION_REQUIRED
NEXT_ACTION: Stage 01 revision mode on the same TASK_ID; add explicit profile controls and repeated candidate-profile sampling acceptance, then increment PLAN_REVISION for a fresh Stage 02 review.
