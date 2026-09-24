# Plan Review Report

## REVIEW_METADATA
- TASK_ID: T20260923-2050-01-local-extraction-adherence
- REVIEW_ATTEMPT: 03
- REVIEWED_PLAN_REVISION: 3
- REVIEWED_PLAN_SHA256: 9d653b5c335dc4aaace45f65df37e83193411b9545413b7271d49125c66971c8
- PLAN_SNAPSHOT_PATH: .agent/tasks/T20260923-2050-01-local-extraction-adherence/review/attempt-03/plan_snapshot.md
- Repository anchor observed: `/Users/hsiaojohnny/dev/convert`, branch `fix/qwen-local-quality-parity`, HEAD `ab2528b718e8c91557fd72db174b0f9bb78d3a68`; only the task directory is untracked.
- Reviewer runtime/model: Codex fresh review context; zero model/backend/E2E/test calls.

## OWNER_VERDICT
The plan is aimed at the correct outcome: improve local meeting-record coverage and density, preserve prior gains, remain model/platform independent, and report numeric results honestly. C1b/C1c, C2a/C2c, the collection-style CORE thresholds, Qwen same-path cost evidence, and the C1c transcript-only degradation path are materially improved and the RV-001–RV-004 corrections are mostly addressed. The essential path is still not ready for handoff because C2b raises a setting shared by the local and cloud refinement loops while the plan requires cloud behavior to remain unchanged, and the status-contract section lacks explicit fixtures for the required contradictory/legacy/waiver/DONE states. Both are load-bearing contract/acceptance gaps. C3 and S1–S5 remain appropriately non-gating/deferred.

## GOAL_BASELINE
From `/Users/hsiaojohnny/.codex/attachments/bbb6190c-103e-4a0f-afca-3142aa462bb0/pasted-text-1.txt`:
- Primary outcome: local-model meeting records should be not much worse than the user’s cloud Gemini records; report the gap and numeric improvement honestly.
- CORE constraints: model/platform independent; same path across macOS/LM Studio and Windows/Ollama; do not test the prohibited Qwen model; do not claim cloud parity; preserve P7-B quality gains.
- The plan must separately address extraction omissions and delivery/adherence omissions, while guarding coverage, density, cost, and valid DOCX output.
- Implementation, commit/push, and independent acceptance are later stages; this review only judges the persisted plan.

## GOAL_ALIGNMENT
The primary outcome, the extraction-vs-generation split, and the non-parity claim remain aligned. The plan correctly makes C1b/C2a/C2c and the quality/cost/DOCX gates CORE, while C3 and supporting ablations do not block the four required gating runs. No supporting source has become the de facto goal.

## NECESSITY_AND_TRACEABILITY
C1b addresses the verified gemma extraction omission (`plan.md:74-83`); C2a/C2c address distinct fact-level and adherence failures (`plan.md:129-145`); CORE-B/C/D/E/F protect whole-record quality, density, cost, and delivery (`plan.md:187-195`). The status matrix ties each material check to a goal or must-not-break invariant (`plan.md:242-255`). C3 and S1–S5 are explicitly non-gating (`plan.md:164-177`).

## GATE_AND_VETO_AUDIT
The quality gates have explicit two-run set semantics and a stated ±10pp interpretation (`plan.md:179-199`). CORE-E uses fixed absolute caps and marks missing/non-equivalent timing evidence BLOCKED rather than estimating (`plan.md:193,204-207`). C1c is scoped to one summary and does not become a global service veto (`plan.md:125,215`). The remaining gate issue is not the quality rationale; it is whether the planned status evidence is sufficiently executable and whether the implementation preserves the cloud contract.

## COUPLING_AND_FAILURE_CONTAINMENT
C1c’s preflight contract is well contained: the existing path re-raises pipeline exceptions at `backend/services/summarization.py:552-564`, and `backend/services/task_processor.py:330-367` sets `summary_failed`, formats the explicit transcript-only warning, saves the result, and completes the task. The plan’s prohibition on changing `task_processor.py:259/262` is therefore grounded (`plan.md:125,215`).

## DESIGN_ECONOMY
C1b/C2c reuse existing paths and add no model calls; C3 is deterministic and registry-first. The main economy defect is contract reuse in C2b: reusing a setting that is not local-only creates an avoidable cloud compatibility risk.

## CRITICAL_PATH_AND_PRIORITY
The sequence S1 → C3 → C2 → C1 → E2E is coherent and keeps optional work after CORE. Before handoff, the plan must make C2b local-only and make status-contract fixture coverage explicit; otherwise Stage 04/05 would have to invent behavior after mutation.

## REQUIREMENT_FIDELITY
The fixed audio/template/mode, prohibited model, cross-platform requirement, no-parity language, and later commit/push requirement are retained (`plan.md:15-19,57-70,221-227,231-236`). The cloud-preservation requirement is not fully honored by the C2b configuration as currently specified (RV-005).

## GROUNDING_AND_DRIFT
RV-002 is resolved: C1b narrows the replay citation to §1–2 and §3 items 1–3,5 and explicitly rejects stale §3 item 4 (`plan.md:110-124`). The replay file itself still contains the old prediction at `evidence/chunk-replay-p7c/README.md:45-59`, but rev3 now identifies it as non-authoritative rather than silently relying on it.

RV-003 is substantively resolved: the P7-B Qwen artifact records wall-clock `1814.937858 s` in `.agent/tasks/T20260923-1810-01-local-record-fidelity-density/e2e/attempt-P7B-qwen27b-e8/run_summary.json:5-6`, and the same-path backend log records extraction `427.6 s` and the two refinement timings (`data/cache/e2e/p7b-qwen27b-e8/backend.log:473`; corroborated by `.../e2e/attempt-P7B-stage05/verification-report.md:86,94`). The arithmetic in `plan.md:204-207` is correct: `1814.937858 + 427.6 + 381 = 2623.537858`, then a fixed cap of `2650 s`. The added 427.6 s is an explicitly conservative allowance, not a claim that the new third chunk was measured.

## ARCHITECTURE_AND_CONTRACTS
### RV-005
- severity: MAJOR
- category: SEMANTIC_CONTRACT
- affected plan: CORE-2 C2b (`plan.md:141-145`), cross-platform/cloud invariants (`plan.md:216-227`), verification matrix `LOCAL-CONTRACTS` (`plan.md:251`)
- evidence: `backend/core/config.py:280-283` defines one shared `LOCAL_LLM_MAX_REFINEMENT_ROUNDS` setting. The local loop consumes it at `backend/services/summarization.py:3564`, but the cloud loop also consumes the same setting at `backend/services/summarization.py:4778-4822`, specifically line 4821. The plan says to change that setting from 2 to 3 while placing all new mechanisms after the local engine dispatch (`plan.md:141,221-226`) and requires cloud behavior/prompt contracts to remain unchanged.
- failure/rework mechanism: implementing the stated 2→3 change increases the cloud refinement loop as well as the local loop. That changes cloud call count, latency, and potentially output, violating the stated cloud-preservation/model-comparison invariant. A Stage 04 implementer cannot satisfy both the named setting change and the no-cloud-change contract without inventing a new configuration split or changing the plan.
- smallest required correction: make the refinement-round limit explicitly local-only (for example, introduce a separately named local setting or pass a local-only limit) and preserve the cloud loop at its existing value/behavior. Add a contract test proving the cloud refinement limit/prompt/output path is unchanged while local C2b can reach three rounds. Do not treat this as a bounded executor fix; it is a plan-level semantic/config contract decision.

## DATA_SECURITY_RELIABILITY
No new dependency, auth boundary, or persistent-data migration is proposed. C3’s registry-first, unique-candidate-only, preserve-original behavior and audit logging are appropriately conservative (`plan.md:147-162`). C1c’s atomic preflight avoids silently dropping transcript chunks, and its expected fallback is consistent with the existing task-processing path.

## IMPLEMENTATION_SEQUENCE
The sequence is otherwise sound: acquire a complete test baseline before mutation (`plan.md:231-234`), perform zero-call checks first, commit before E2E, then run four fixed gating cases. C2b must be corrected before Stage 03 because its current shared setting crosses the local/cloud boundary.

## TESTABILITY_AND_ACCEPTANCE
The matrix now declares the required item schema, baseline policy, non-waiver policy, and Stage 04/05 snapshot fields (`plan.md:238-261`). This resolves the substantive schema/routing portion of RV-001, and the C1c route is explicitly tied to the existing fallback path. However, the plan does not name deterministic fixtures or contract-test cases for the status contract’s required edge states.

### RV-006
- severity: MAJOR
- category: TEST
- affected plan: §8.1 status-aware verification and Stage 04→05 routing (`plan.md:238-261`)
- evidence: `workflow-routing.md:166-227,249-347` requires explicit handling of the verification-item schema, baseline/waiver semantics, exhaustive Stage 04/05 routing, contradictory-state rejection, legacy normalization, and every `DONE` prerequisite. Rev3 defines the fields and prose routes, but §8.1 only says Stage 04/05 “must” record/read them; it does not specify fixtures/assertions for canonical incident, true implementation blocker, CORE FAIL/BLOCKED/NOT_RUN/NOT_REQUIRED, replan, unavailable baseline, baseline delta, hard-clean debt, formal waiver preserving the original result, independent-acceptance pending/environment/product-defect cases, contradictory states, legacy normalization, or each DONE prerequisite.
- failure/rework mechanism: Stage 04/05 can implement a superficially complete matrix while still accepting illegal combinations or rewriting legacy/waived results. This leaves closure semantics to post-result invention and makes the required independent acceptance non-reproducible.
- smallest required correction: add a compact status-contract fixture table or deterministic test inventory to §8.1, covering every required state above, including rejection of contradictory combinations, evidence-backed legacy normalization, preservation of original `CHECK_RESULT` under any formal waiver fixture, and one negative fixture for each `DONE` prerequisite. State that Stage 05 must execute or inspect these fixtures without rewriting Stage 04 snapshots.

## SCOPE_AND_COMPLEXITY
Scope is mostly economical and the optional work is correctly deferred. The shared setting in RV-005 and unspecified status fixtures in RV-006 are not reviewer preference; both can change externally visible behavior or closure validity.

## FINDINGS
- RV-001 — **RESOLVED in substance, with RV-006 remaining**: rev3 adds the required fields, baseline/waiver declarations, immutable Stage 04 snapshot, and Stage 05 preservation/routing (`plan.md:238-261`). Explicit fixture coverage is still absent.
- RV-002 — **RESOLVED**: stale replay §3 item 4 is explicitly excluded (`plan.md:110-124`).
- RV-003 — **RESOLVED in substance**: Qwen same-path wall-clock/extraction evidence and arithmetic are grounded and frozen (`plan.md:204-207`; artifacts cited above). The extra allowance remains a stated conservative budget, not a measured third-chunk time.
- RV-004 — **RESOLVED**: pre-provider full-list validation, zero-call over-budget behavior, transcript-only degradation, and routing are explicit (`plan.md:121-127,212-219`). The existing code path supports the required exception-to-fallback behavior (`summarization.py:552-564`; `task_processor.py:330-367`).
- I1–I5 — **RESOLVED**: rev3 retains wall-clock arithmetic, collection semantics/noise-band limitation, C2a/C2c separation, pinned `4500`/budget `4` with default `0`, and the gemma whole-record floor (`plan.md:27-31,110-145,179-207`).
- RV-005 — **OPEN / MAJOR**: shared refinement setting crosses into the cloud loop.
- RV-006 — **OPEN / MAJOR**: status-contract fixture inventory is missing.

## REQUIRED_PLAN_CHANGES
1. Resolve RV-005 by making the C2b round limit local-only and proving cloud behavior remains unchanged.
2. Resolve RV-006 by adding explicit deterministic status-contract fixtures/assertions for the required Stage 04/05 states, including contradictory-state rejection, legacy normalization, waiver-result preservation, and all DONE prerequisites.
3. Increment `PLAN_REVISION`, recompute the plan SHA-256, and submit the new revision to a fresh independent review; do not reuse this gate.

## RESIDUAL_MINOR_NOTES
- The `run_summary.json` artifact is under `.agent/tasks/T20260923-1810-01-local-record-fidelity-density/e2e/attempt-P7B-qwen27b-e8/`; the plan’s `e2e/attempt-P7B-qwen27b-e8/run_summary.json` shorthand should be expanded to that exact repository path during revision for handoff clarity.
- The plan’s refinement-budget exhaustion behavior is less explicit than C1c (`plan.md:141-143`); it should state that stopping after the budget preserves the latest valid summary and does not silently discard transcript material. This is secondary to RV-005.

FINAL_STATUS: PLAN_REVISION_REQUIRED
NEXT_ACTION: Stage 01 revision mode on the same TASK_ID: split C2b from the shared cloud refinement setting, add the explicit status-contract fixture inventory, increment/re-hash the plan, and resubmit for fresh Stage 02 review.

GATE: PLAN_REVISION_REQUIRED
