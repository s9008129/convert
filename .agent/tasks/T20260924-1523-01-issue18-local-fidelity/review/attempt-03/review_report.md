# Plan Review Report

## REVIEW_METADATA
- TASK_ID: T20260924-1523-01-issue18-local-fidelity
- REVIEW_ATTEMPT: 03
- REVIEWED_PLAN_REVISION: 4
- REVIEWED_PLAN_SHA256: 72d23f2facf0a88b12ec2f18a6850db011a2ff0dd9e15cefa1037bc230220c89
- PLAN_SNAPSHOT_PATH: .agent/tasks/T20260924-1523-01-issue18-local-fidelity/review/attempt-03/plan_snapshot.md
- Repository anchor observed: branch `issue-18-first-divergence-diagnostic`, HEAD `eb3ca049cc72d21d2f4db974db5314b5f399d736` (`eb3ca04`); canonical plan was not modified by this review
- Reviewer runtime/model: Codex GPT-5

## OWNER_VERDICT
The plan now addresses the requested local V2 architecture and the prior review gaps. Essential work is source-anchored typed extraction, deterministic ledger/consolidation, section-scoped rendering, fidelity firewall, guarded repair, rollback, local E2E, and blind quality acceptance. Runtime profile controls and repeated candidate selection are explicitly required and remain bounded by capability detection; optional glossary enrichment, held-out data, and performance diagnostics remain non-gating. The only whole-record blockers are scoped CORE source/schema/selected-claim failures. The largest residual risk is that the frozen blind evaluator/baseline or local model runtime may remain unavailable; the plan correctly preserves implementation evidence and routes that as scoped acceptance/environment blocking rather than inferring quality.

## GOAL_BASELINE
- **Primary outcome:** redesign the local Gemma 4 31B/Qwen 3.8 27B meeting-record pipeline around immutable raw-source evidence, structured fact/evidence architecture, deterministic validation, and controlled generation, reaching the requested fresh blind quality target with zero major fidelity hard fails.
- **Success evidence:** selected causal claim correctness from source through delivery; regression coverage for specified fidelity failures; cloud/privacy/template invariants; fresh Gemma/Qwen E2E; and fresh blind 3+3 meeting every per-output/per-dimension 80% threshold against the original unrounded Gemini baseline with zero major hard fails.
- **Explicit runtime requirement:** Qwen controls `thinking=OFF, temperature=0.7, top_p=0.8, top_k=20`; Qwen extraction A/B temperatures `0.3, 0.5, 0.7`; independent Gemma controls `thinking=OFF, temperature=1.0, top_p=0.95, top_k=64`; repeated candidate comparison at N>=5 preferred/N>=3 minimum using median, worst case, range, and hard-fail count.
- **Must-not-break:** cloud semantics, v4.7.4 invariants, output/template contracts, privacy/provenance, retry and runtime-selection safety, and explicit rollback/degradation.
- **Non-goals:** wholesale experiment-branch merge, hard-coded private/source facts, raw-content retention in tracked artifacts, a second LLM truth oracle, broad ASR/UI work, or lowering the frozen quality gate.

## GOAL_ALIGNMENT
The plan's primary outcome, goal contract, critical path, and CORE/SUPPORTING/BEST_EFFORT classifications align with the authoritative attachment. Revision 4 explicitly carries the runtime-control and variance-reduction requirement instead of reducing acceptance to a single blind cohort. No supporting tool or repository-health check has become the product goal.

## NECESSITY_AND_TRACEABILITY
R1–R10 and R12 trace to source fidelity, semantic preservation, controlled generation, rollback, acceptance, or privacy/audit obligations. R11 performance/held-out work is correctly SUPPORTING and non-vetoing. W7/C14 are necessary for the explicit run-to-run variance and candidate-selection requirement; the diagnostics are separate from the blind 3+3 outcome cohort.

## GATE_AND_VETO_AUDIT
Selected/core evidence, schema validity, and selected causal correctness have scoped veto rationales. Optional enrichment, unsupported runtime parameters, performance, and held-out data degrade locally or remain non-gating. The frozen evaluator/baseline is scoped to quality acceptance/closure. Every C1–C14 row includes the v4.2 fields: `CHECK_ID`, `GOAL_CRITICALITY`, `EVIDENCE_ROLE`, `CLOSURE_GATE`, `BASELINE_REQUIRED`, `FAILURE_CLASSIFICATION_RULE`, `WAIVER_ALLOWED`, `WAIVER_AUTHORITY`, `CHECK_RESULT`, and `WAIVER_STATUS`. No self-waiver path is specified; all rows are initially `NOT_RUN`, with `NOT_ALLOWED` waivers.

## COUPLING_AND_FAILURE_CONTAINMENT
Evidence gaps and conflicts are contained to the affected claim/section except for the selected CORE claim. Schema failure permits exactly one schema-only repair and then explicit V2 failure; there is no silent V1 fallback. Targeted patch rejection restores the prior section bytes. Runtime diagnostics cannot veto unrelated valid sections. Cloud and local paths remain separate, with a golden requirement for unavoidable shared-helper changes.

## DESIGN_ECONOMY
The evidence/fact/ledger/section/firewall/patch abstractions each pay for a concrete fidelity, traceability, or rollback obligation. The profile matrix and C14 are a bounded acceptance mechanism required by the authoritative request, not a new production architecture. The deletion test does not identify material untraceable scope.

## CRITICAL_PATH_AND_PRIORITY
W0–W6 establish contracts, data flow, deterministic generation, and selected-claim protection before W7 profile tuning and W8 blind acceptance. C14 profile sampling precedes final profile selection and is explicitly excluded from the blind 3+3 cohort. Optional held-out/performance work remains after the core path and non-gating.

## REQUIREMENT_FIDELITY
Revision 4 resolves prior RV-003: W7 contains the explicit Qwen/Gemma candidate controls, Qwen extraction A/B values, capability validation/downgrade behavior, N>=5 preferred/N>=3 minimum protocol, required statistics, and ordered fidelity-first selection priorities. W8 and C14 require reporting the sample counts and metrics and keep diagnostic samples separate from blind acceptance. Prior RV-001 (v4.2 check-row fields) and RV-002 (C3 baseline command/artifact/routing) are also resolved.

## GROUNDING_AND_DRIFT
The plan is anchored to the observed branch and HEAD and preserves the established first-divergence evidence. Title `Plan Revision 4` matches `META PLAN_REVISION: 4`. C3/W0 uses the repository-standard command:
`uv run pytest -q tests/test_summarization_service.py -k "cloud_pipeline or cloud_generation or validate_cloud or cloud_finalize or gemini_chat"`.
Running that command in this review environment produced collection failure before tests because logger setup attempts `/app/data/logs`, then `/app/data`, and the environment is read-only (`OSError: [Errno 30] Read-only file system`). The plan correctly requires recording the exact signature, marking C3 `BLOCKED` when the baseline cannot be established, and forbids inferring cloud preservation. This is scoped baseline/environment evidence, not a product-regression claim.

## ARCHITECTURE_AND_CONTRACTS
The additive opt-in V2 path, strict JSON compatibility path, one schema-only repair, deterministic ledger/conflict handling, section rendering, model-independent QualityPolicy, explicit V1 rollback, and cloud golden guard are coherent. No unresolved semantic-contract defect was found.

## DATA_SECURITY_RELIABILITY
Raw/source hash-span provenance, ignored runtime storage, redacted diagnostics, no private tracked artifacts, explicit rollback, and no silent fallback address the relevant data and reliability risks. Candidate-profile diagnostics must continue to record only safe metadata, as required by the plan.

## IMPLEMENTATION_SEQUENCE
The sequence is appropriate: fail-first models/tests, extraction/provenance, ledger, section rendering, firewall, guarded patch, then capability-validated runtime profiles and acceptance. C14 occurs before profile selection and before final quality claims.

## TESTABILITY_AND_ACCEPTANCE
C1–C14 map the selected-claim path, synthetic A–I cases, cloud contract, privacy, focused/full/docs checks, local E2E, blind 3+3, diagnostics, and repeated candidate-profile selection. C3 has a reproducible command, artifact, same-command rerun requirement, and scoped unavailable-baseline route. C14 captures N>=5 preferred/N>=3 minimum, limitation recording, median/worst/range/hard-fail metrics, and the W7 selection order. Missing evaluator/baseline and unavailable model/hardware remain explicit scoped blockers rather than silent passes.

## SCOPE_AND_COMPLEXITY
Scope remains the authorized Issue #18 architecture redesign. Experimental branches are evidence libraries only; W5 requires selective, contract-checked reuse. No unrelated ASR/UI or wholesale branch integration is introduced. The plan title/revision bookkeeping is consistent.

## FINDINGS
No unresolved BLOCKER, MAJOR, or MINOR finding capable of invalidating goal alignment, implementation, safety, compatibility, rollback, or acceptance was identified. Attempt-02 RV-003 is resolved by W7, W8, C14, and the updated Definition of Done. Attempt-02 RV-001 and RV-002 are also resolved.

## REQUIRED_PLAN_CHANGES
None for this revision.

## RESIDUAL_MINOR_NOTES
- W8 names bare `pytest tests/ -q` for the broad repository run while W0 correctly uses `uv run pytest` for the load-bearing C3 cloud baseline; implementers should use the repository’s reproducible `uv` entrypoint for broad checks as well where applicable.
- The observed `/app/data/logs` read-only failure must be preserved verbatim/redacted in the W0 C3 baseline artifact and reported as scoped `BLOCKED`/verification `INCOMPLETE` downstream; it must not be called a cloud semantic regression or silently converted to PASS.
- The existing revision-1 handoff remains stale and must be regenerated only after this exact revision is approved.

FINAL_STATUS: PLAN_APPROVED
NEXT_ACTION: Stage 03 Handoff for PLAN_REVISION 4 and SHA-256 72d23f2facf0a88b12ec2f18a6850db011a2ff0dd9e15cefa1037bc230220c89.
