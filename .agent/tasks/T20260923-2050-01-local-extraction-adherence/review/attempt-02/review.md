# Plan Review Report

## REVIEW_METADATA
- TASK_ID: T20260923-2050-01-local-extraction-adherence
- REVIEW_ATTEMPT: 02
- REVIEWED_PLAN_REVISION: 2
- REVIEWED_PLAN_SHA256: 32e6ac0fe2473a951cc8d1e8217ffa1385722bdb5b59f302f726bf608390b1d2
- PLAN_SNAPSHOT_PATH: .agent/tasks/T20260923-2050-01-local-extraction-adherence/review/attempt-02/plan_snapshot.md
- Repository anchor observed: /Users/hsiaojohnny/dev/convert, branch fix/qwen-local-quality-parity, HEAD ab2528b718e8c91557fd72db174b0f9bb78d3a68 as recorded in the authoritative handoff; working tree contains the task directory only as an untracked tree.
- Reviewer runtime/model: Codex fresh review context; no model/backend calls.

## OWNER_VERDICT
The plan remains aligned with the owner’s goal: improve local meeting-record fidelity and density without claiming cloud parity, while preserving model/platform independence and the P7-B gains. The essential path is C1b extraction chunking, C2a/C2c generation adherence, the gemma/qwen CORE acceptance bars, cost limits, and DOCX/anti-gaming checks. C3, projection, tag diagnostics, and ablation work are correctly non-gating or deferred. The four original blocking findings I1–I5 are substantively addressed. However, the plan still needs a status-aware verification/closure contract for the required E2E and broad acceptance gates, and its qwen cost cap relies on a measurement that is not the same change being gated. There is also a stale cited prediction in the replay evidence. These create avoidable Stage 04/05 ambiguity and can invalidate the cost or closure decision.

## GOAL_BASELINE
From the authoritative user handoff (`/Users/hsiaojohnny/.codex/attachments/bbb6190c-103e-4a0f-afca-3142aa462bb0/pasted-text-1.txt`):
- Primary outcome: local-model meeting records should be not much worse than the user’s cloud Gemini records; provide a deep optimization plan and report numeric improvement honestly.
- CORE constraints: model/platform independent; same code path across macOS LM Studio and Windows/Ollama; fixed audio/template/mode; prohibited model must not be tested; no claim of cloud equivalence; preserve prior quality gains.
- Acceptance must distinguish the two known gaps: missing facts in extraction and facts present in notes but omitted in delivery, while also guarding density, coverage, cost, and valid DOCX output.
- Required process outcome: implementation, commit/push, and independent acceptance are later workflow stages; this review must only judge the plan.

## GOAL_ALIGNMENT
The primary outcome and critical path match the baseline. The plan correctly treats extraction coverage and generation adherence as separate mechanisms and does not make C3 proper-noun normalization a prerequisite. The model/platform restriction is explicitly preserved in §7, and the plan does not substitute “passing internal checks” for the user-visible record-quality goal.

## NECESSITY_AND_TRACEABILITY
CORE-1 maps to extraction omissions; CORE-2 maps to facts present in notes but absent from delivery; CORE-B/C/D protect whole-record coverage and density; CORE-E protects the cost trade-off; CORE-F protects the deliverable. S1–S5 are explicitly supporting or best-effort. The deletion test is mostly satisfied. The remaining gap is not untraceable feature scope but incomplete traceability of the required verification and closure semantics noted in RV-001.

## GATE_AND_VETO_AUDIT
The four quality/cost bars are explicitly blocking and their rationale is stated. The n=2 set semantics and ±10pp limitation improve decision validity. C3 is explicitly disabled on the four gating runs, avoiding attribution contamination. The new call budgets are intended as safeguards, but the over-budget behavior (“stop adding chunks”) can produce partial extraction while being described as observation-only; the plan does not state whether that partial result is a local degraded observation, a CORE failure, or a fail-closed stop. This is a material semantic contract gap (RV-004).

## COUPLING_AND_FAILURE_CONTAINMENT
C2c is zero-call and local to the existing refinement prompt. C3 is deterministic, registry-first, unique-candidate-only, fail-soft, and separately evaluated. The main remaining coupling is the extraction call budget: a global total-call cap can truncate independent transcript chunks, and the plan has not specified a product-level status/rollback behavior for that case (RV-004). The qwen cost cap also couples a blocking decision to a non-equivalent probe measurement (RV-003).

## DESIGN_ECONOMY
The revised design is economical relative to the stated defects: C1b and C2c reuse existing paths, and C3 is zero-model-call. The optional work is correctly deferred. No additional abstraction is required by this review; the needed changes are contract and evidence clarifications.

## CRITICAL_PATH_AND_PRIORITY
The plan prioritizes zero-cost/zero-call work before the four required E2E runs and keeps C3 out of the gating runs. That sequencing is sound. The plan should add the status/verification matrix before implementation so Stage 04 and Stage 05 cannot invent closure policy after results exist.

## REQUIREMENT_FIDELITY
The rev2 plan preserves the authoritative constraints and does not claim cloud parity. It explicitly records Windows/Ollama as unverified. The fixed material and prohibited model are retained. Later commit/push is acknowledged by the user goal but is not a Stage 02 implementation requirement.

## GROUNDING_AND_DRIFT
Repository anchors for the existing settings, tag constants, homophone helper, registry, pypinyin dependency, five existing quality thresholds, and projection function are grounded in the current tree. The plan correctly labels new switches as new rather than existing. However, the plan cites `evidence/chunk-replay-p7c/README.md §3` as the prediction source while that file’s line 57 still says the qwen call-budget default is `2`; rev2 §3 C1c says the default is `0` and the E2E value is `4`. This stale contradiction must be removed before handoff (RV-002).

## ARCHITECTURE_AND_CONTRACTS
The proposed locations and byte-level rollback invariant are repository-consistent. The new configuration keys and behavior are load-bearing internal contracts, so their defaults, total-vs-additional semantics, over-budget behavior, and disabled behavior need explicit contract tests. The plan covers most of these, but does not define the status of a partially extracted record after a budget stop (RV-004).

## DATA_SECURITY_RELIABILITY
No new external dependency is proposed. C3’s registry-first, unique-candidate-only, no-candidate-preserve-original, logging, and anti-gaming rules are appropriate safety controls. No auth/privacy boundary is implicated. Reliability risk remains in the qwen cost formula: the cited replay is explicitly for the gemma transcript and says it cannot establish qwen behavior, while the blocking qwen cap uses `+150 s` from a tail-half extraction probe rather than a measured extra C1b chunk on the qwen path (RV-003).

## IMPLEMENTATION_SEQUENCE
The sequence is coherent: unit/zero-call checks, commit before E2E, then four gating runs and optional supporting runs. Before Stage 03/04, add the verification/closure contract and resolve the cited evidence mismatch. No product implementation is authorized by this review.

## TESTABILITY_AND_ACCEPTANCE
The quality instruments and manual/`rg` checks are named, and the four-run set semantics are observable. The plan does not yet specify the status-aware verification schema required for each material check: `CHECK_ID`, `GOAL_CRITICALITY`, `EVIDENCE_ROLE`, `CLOSURE_GATE`, baseline rule, failure classification, waiver policy/authority, and separate check/waiver results. It also does not state how Stage 04 `execution.md` evidence is snapshotted and preserved by Stage 05, or how environment-blocked/not-run CORE and required-verification states route to closure. This is a required plan-level correction (RV-001).

## FINDINGS

### RV-001
- severity: MAJOR
- category: TEST
- affected plan: §5, §8, metadata `INDEPENDENT_ACCEPTANCE_REQUIRED: YES`, `E2E_REQUIRED: YES`
- evidence: The plan lists blocking CORE-A–F checks and Stage 05/result.md, but does not define the v4.2 verification-item fields, baseline policy (`HARD_CLEAN`/`BASELINE_DELTA`/`NON_GATING`), waiver allowed/authority, or Stage 04-to-Stage 05 immutable outcome handoff. Workflow policy §7.3–§7.11 requires these distinctions for material verification and closure.
- failure/rework mechanism: A CORE failure, pre-existing broad-test failure, environment-blocked E2E, not-run check, or authorized waiver can be routed inconsistently or have its original result rewritten. Stage 05 may need to invent closure semantics after implementation, invalidating the acceptance decision.
- smallest required correction: Add a compact verification matrix and routing section to the plan covering every material check’s criticality, evidence role, closure gate, baseline rule, waiver status/authority, and the required Stage 04 execution snapshot fields that Stage 05 must preserve. Explicitly cover CORE PASS/FAIL/BLOCKED/NOT_RUN, required verification incomplete/blocked, independent acceptance blocked, replan, and final closure routing.

### RV-002
- severity: MAJOR
- category: GROUNDING
- affected plan: §0 I4, §3 CORE-1 C1c, §5 pre-registration, cited `evidence/chunk-replay-p7c/README.md §3`
- evidence: The cited replay README line 57 says the qwen side is guarded by a call-budget default of `2`; rev2 plan §3 lines 105–107 defines the new budget default as `0` and E2E value as `4`.
- failure/rework mechanism: Stage 04 can follow stale cited evidence and implement/test the wrong default or interpret the pre-registration inconsistently. The exact evidence chain for the cost/guard decision is therefore not self-consistent.
- smallest required correction: Update the cited evidence or narrow the plan citation to the applicable gemma prediction lines and explicitly remove the stale qwen-default statement; then re-hash/re-review the revised plan.

### RV-003
- severity: MAJOR
- category: TEST
- affected plan: §5 CORE-E qwen wall-clock limit and §11 decision table
- evidence: The plan sets qwen `≤2,400 s` as `1,814.9 + 360 + 150`, treating `+150 s` as the added extraction cost. The cited replay README §3 is for the gemma P7-B transcript and explicitly says it cannot extrapolate qwen; the `150.5 s` measurement cited in the prior evidence is a tail-half extraction probe, not an observed additional 4,500-token C1b chunk on the qwen E2E path.
- failure/rework mechanism: The qwen cost gate can be either unrealistically tight or unjustifiably loose. Because CORE-E is blocking, the plan may stop a successful quality run or accept an unsupported cost result without a valid baseline/delta comparison.
- smallest required correction: Make the qwen cost model explicit as a provisional prediction and pre-register the same-path baseline/delta measurement needed before applying the blocking cap, or derive a conservative cap from an equivalent qwen full/chunk extraction measurement. State how an unavailable baseline is classified under the verification contract.

### RV-004
- severity: MAJOR
- category: SEMANTIC_CONTRACT
- affected plan: §3 CORE-1 C1c, §5 CORE-E, §6 rollback
- evidence: On `CALL_BUDGET` exhaustion the plan says “stop adding chunks” and record `skipped_reason=extraction_call_budget_exceeded`, but calls this observation-only and does not define the resulting record/notes completeness or whether the run is locally degraded, CORE-invalid, or fail-closed.
- failure/rework mechanism: A guard intended to contain cost can silently discard later transcript material and still permit downstream generation. This can make the record invalid while the acceptance artifact treats the event as a non-gating observation, and the behavior differs from the stated preservation goal for other transcript lengths.
- smallest required correction: Define the over-budget contract: either never truncate required extraction (make the cap diagnostic/non-gating), or fail/mark the run explicitly with a scoped CORE/verification status and prevent it from being accepted as a complete record. Add a deterministic over-budget test and its expected Stage 04/05 routing.

## REQUIRED_PLAN_CHANGES
1. Add the status-aware verification, baseline, waiver, and Stage 04/Stage 05 preservation/routing matrix required by RV-001.
2. Resolve the stale qwen-default citation in the replay evidence chain (RV-002).
3. Make the qwen CORE-E cost cap evidence-valid and pre-register the same-path measurement or a conservative equivalent (RV-003).
4. Specify and test the semantic outcome of extraction-budget exhaustion (RV-004).

## RESIDUAL_MINOR_NOTES
- The original I1–I5 findings are substantively resolved: wall-clock source and cost formulas are explicit; n=2 uses set semantics with the noise-band caveat; C2a targets fact-level F048 behavior and C2c targets adherence; C1b is pinned to 4500 with total-call budget semantics/defaults; and gemma has a whole-record coverage floor plus a no-regression observation list.
- CORE-B’s `22/28` floor permits one run to be below the prior 25/28 result; this is a deliberate approximately-noise-band floor, but the final report must not describe it as strict non-regression.
- Windows/Ollama remains correctly marked `[UNVERIFIED]`; no Stage 02 review evidence should imply cross-platform acceptance.

FINAL_STATUS: PLAN_REVISION_REQUIRED
NEXT_ACTION: Stage 01 revision mode on the same TASK_ID to add the status-aware verification contract and resolve RV-002–RV-004, then submit the resulting plan revision for a new independent review.

GATE: PLAN_REVISION_REQUIRED
