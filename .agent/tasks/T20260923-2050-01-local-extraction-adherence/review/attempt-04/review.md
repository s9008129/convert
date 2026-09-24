# Plan Review Report

## REVIEW_METADATA
- TASK_ID: T20260923-2050-01-local-extraction-adherence
- REVIEW_ATTEMPT: 04
- REVIEWED_PLAN_REVISION: 4
- REVIEWED_PLAN_SHA256: 355e0bf8fffc79fb4e8d4f973b48da2b594666bbff1a2e99db86c5425a12f920
- PLAN_SNAPSHOT_PATH: .agent/tasks/T20260923-2050-01-local-extraction-adherence/review/attempt-04/plan_snapshot.md
- Repository anchor observed: `/Users/hsiaojohnny/dev/convert`, branch `fix/qwen-local-quality-parity`, HEAD `ab2528b718e8c91557fd72db174b0f9bb78d3a68`; task directory is the only untracked worktree path observed.
- Reviewer runtime/model: Codex fresh review context; no tests, backend, model inference, or E2E executed.

## OWNER_VERDICT
The plan remains aligned with the user’s actual goal: improve local-model meeting-record fidelity without claiming cloud parity, preserve prior density/coverage gains, remain model/platform independent, and report numeric results honestly. The essential path is now defined and gated: extraction coverage, local generation adherence, density/coverage floors, cost, DOCX validity, anti-gaming evidence, rollback, and independent acceptance. C3 and S1–S5 remain explicitly supporting or best-effort and do not block the core four-run acceptance path. Rev4 closes the two prior MAJOR findings: the refinement-round override is local-only with cloud-preservation tests, and the status-contract fixture inventory is explicit and independently reviewable. No global blocker is introduced without a stated correctness rationale. Complexity is proportionate to the two observed failure modes and the required closure semantics.

## GOAL_BASELINE
From the authoritative current task source `/Users/hsiaojohnny/.codex/attachments/bbb6190c-103e-4a0f-afca-3142aa462bb0/pasted-text-1.txt`:
- Primary outcome: local-model meeting records should be not much worse than the user’s cloud Gemini records; report the gap and numeric improvement honestly.
- Core constraints: model/platform independence; one code path across macOS/LM Studio and Windows/Ollama; prohibited Qwen model must not be tested; no claim of cloud equivalence; preserve P7-B gains.
- The plan must address both known gaps: facts omitted during extraction and facts present in notes but omitted in delivery, while protecting coverage, density, cost, and valid DOCX output.
- Implementation, commit/push, and independent acceptance are later stages; this review judges only the persisted plan.

## GOAL_ALIGNMENT
The plan’s PRIMARY_OUTCOME and Goal Contract match the baseline. CORE-1 targets extraction omissions; CORE-2 separately targets delivery/adherence omissions; CORE-B/C/D/E/F protect user-visible quality, density, cost, and deliverability. The plan explicitly rejects a cloud-parity claim and preserves Windows/Ollama as unverified rather than overstating acceptance.

## NECESSITY_AND_TRACEABILITY
Each material CORE item has a direct goal or must-not-break rationale. C1b/C1c address the verified chunk-level extraction failure; C2a/C2c address fact-level and adherence failures; CORE-B/C/D protect prior quality; CORE-E controls the cost trade-off; CORE-F and ANTI-GAMING protect deliverable validity and measurement validity. `LOCAL-CONTRACTS`, `BYTE-ROLLBACK`, and `PLATFORM-INDEPENDENCE` are explicit compatibility invariants. C3 and S1–S5 are labeled supporting/best-effort and are not required for the primary four-run gate.

## GATE_AND_VETO_AUDIT
The quality gates have explicit collection semantics: two runs must meet the floor and at least one must meet the target, with the ±10pp/n=2 limitation stated. CORE-E uses fixed pre-registered absolute caps and a named wall-clock source; unavailable or non-equivalent evidence is BLOCKED rather than estimated. C1c over-budget behavior is fail-closed for the affected summary, scoped to one meeting, and explicitly not a global service veto. The supporting FULL-SUITE gate is BASELINE_DELTA, not a CORE veto; the plan explains why unresolved baseline evidence keeps closure pending without invalidating proven implementation/CORE state. STATUS-CONTRACT-FIXTURES is SUPPORTING but HARD_CLEAN with an explicit rationale: preventing false DONE claims is a closure-correctness obligation.

## COUPLING_AND_FAILURE_CONTAINMENT
C2b now introduces `LOCAL_LLM_MAX_LOCAL_REFINEMENT_ROUNDS` and keeps the shared `LOCAL_LLM_MAX_REFINEMENT_ROUNDS` unchanged for cloud. The plan explicitly requires tests for local max 0/3, local budget exhaustion, and cloud round/prompt/output invariance. C1c preflights the complete chunk list before provider I/O and returns the existing transcript-only degradation path without accepting a partial summary. C3 preserves the original text unless a unique, registry-grounded candidate exists. These boundaries contain supporting failures at the narrowest stated scope.

## DESIGN_ECONOMY
The core changes reuse existing local extraction/refinement paths, add no model calls for C2c/C3, and use deterministic tests for new switches and rollback. The separate local-only round setting is necessary to preserve the cloud contract; the fixture inventory is necessary to make §7 closure semantics reproducible. Optional attribution and ablation work is deferred and non-gating. No avoidable new dependency or architecture is required by the plan.

## CRITICAL_PATH_AND_PRIORITY
The sequence performs baseline acquisition, zero-call/unit/contract checks, implementation, commit-before-E2E, then the four required E2E runs and Stage 05 independent acceptance. Supporting S3/S5 work is explicitly after CORE. The plan does not make C3 part of the four gating runs, avoiding attribution contamination.

## REQUIREMENT_FIDELITY
The fixed audio/template/mode, prohibited model, no-parity language, cross-platform requirement, preservation of P7-B gains, later commit/push, and independent acceptance requirements are retained. Rev4’s C2b correction honors the cloud-preservation requirement rather than silently changing the shared setting.

## GROUNDING_AND_DRIFT
The current plan hash and exact snapshot match the requested revision. Prior continuity is consistent: rev2 addressed I1–I5; rev3 addressed RV-001–RV-004; rev4 is explicitly scoped to RV-005/RV-006 and direct dependencies.

Earlier findings rechecked as relevant:
- I1: resolved by fixed wall-clock source and arithmetic in CORE-E.
- I2: resolved by collection semantics and explicit n=2 noise-band limitation.
- I3: resolved by separating fact-level C2a from adherence-focused C2c.
- I4: resolved by pinned E2E values, explicit total-budget semantics, and default `0` rollback behavior.
- I5: resolved by the gemma whole-record CORE-B floor.
- RV-001: resolved in substance by the §8.1 verification matrix, orthogonal statuses, baseline/waiver declarations, and Stage 04/05 snapshot rules.
- RV-002: resolved by excluding the stale replay prediction from the authoritative citation.
- RV-003: resolved by the same-path Qwen evidence and fixed `2,650 s` conservative allowance, with unavailable evidence classified BLOCKED.
- RV-004: resolved by full-list preflight, zero provider calls on over-budget input, no partial summary, transcript-only warning, and explicit routing.

## ARCHITECTURE_AND_CONTRACTS
RV-005 is closed. Rev4 states that the existing shared refinement limit remains unchanged for cloud, adds a distinct local-only setting, defines `0` as compatibility inheritance, and requires deterministic tests proving local three-round behavior does not change cloud rounds, prompts, or output bytes. This is the smallest correction to the prior shared-setting defect.

## DATA_SECURITY_RELIABILITY
No auth, privacy, migration, or new external dependency is implicated. C3’s registry-first and unique-candidate-only rules avoid fabrication; logs and skipped reasons are required for auditability. The plan preserves original transcript/chunk material on budget exhaustion and never treats partial output as a valid meeting record.

## IMPLEMENTATION_SEQUENCE
The sequence is executable without requiring the implementer to invent semantic policy: baseline before mutation, zero-call checks before E2E, commit before runner invocation, fixed four-run budgets, then independent acceptance. The plan also provides explicit stop/replan routes when fixed-chunk or load-bearing assumptions fail.

## TESTABILITY_AND_ACCEPTANCE
RV-006 is closed. §8.2 enumerates deterministic fixtures for canonical incidents, true implementation blockers, CORE FAIL/BLOCKED/NOT_RUN/NOT_REQUIRED, replan, baseline unavailable/delta, hard-clean debt, formal waiver with original result preserved, unauthorized waiver, independent acceptance pending/environment/product defect, contradictory states, evidence-backed legacy normalization, and every DONE prerequisite. Stage 04 records fixture results; Stage 05 independently rechecks them without rewriting the Stage 04 snapshot. The matrix and fixtures are consistent with workflow-routing.md §7’s orthogonal status, waiver, blocker, and closure rules.

## SCOPE_AND_COMPLEXITY
The plan is STANDARD in scope and does not add untraceable requirements. CORE gates are justified by the user-visible quality outcome or explicit must-not-break/closure correctness. Supporting and best-effort elements are non-gating. E2E budgets are explicit: two gemma runs at 2,750 s and two Qwen runs at 2,650 s, with the Qwen formula and evidence boundary stated; optional S3/S5 work is outside the required four-run gate.

## FINDINGS
No unresolved BLOCKER or MAJOR finding remains for revision 4.

### RV-005 — RESOLVED
The prior semantic-contract defect was that a shared refinement setting would affect cloud and local loops. Rev4 replaces that with a local-only setting and requires contract tests for cloud invariance (`plan.md:154-160`, `plan.md:250-252`).

### RV-006 — RESOLVED
The prior test/closure defect was missing executable status-contract coverage. Rev4 adds the full fixture inventory and immutable Stage 04→05 evidence rule (`plan.md:285-319`), matching the required §7 cases.

## REQUIRED_PLAN_CHANGES
None for revision 4. Stage 03 may compile a handoff for this exact plan revision and hash.

## RESIDUAL_MINOR_NOTES
- Windows/Ollama real-machine behavior remains correctly `[UNVERIFIED]`; static same-path checks must not be reported as real-machine acceptance.
- The four E2E runs are the required core budget; optional S3/S5 runs may consume additional resources and should remain explicitly subordinate to CORE acceptance.
- The review did not execute tests, backend code, model inference, or E2E, per instruction; those remain Stage 04/05 evidence obligations.

FINAL_STATUS: PLAN_APPROVED
NEXT_ACTION: Stage 03 Handoff for PLAN_REVISION 4 with SHA-256 355e0bf8fffc79fb4e8d4f973b48da2b594666bbff1a2e99db86c5425a12f920.
