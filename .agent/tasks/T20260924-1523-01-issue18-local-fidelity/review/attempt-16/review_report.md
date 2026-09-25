# Plan Review Report

## REVIEW_METADATA
- TASK_ID: T20260924-1523-01-issue18-local-fidelity
- REVIEW_ATTEMPT: 16
- REVIEWED_PLAN_REVISION: 16
- REVIEWED_PLAN_SHA256: 5a5a6663e2b1258aa9b345d7dbe08249ea6661a0849ce5ba0f82dd7ad8dbc647
- PLAN_SNAPSHOT_PATH: .agent/tasks/T20260924-1523-01-issue18-local-fidelity/review/attempt-16/plan_snapshot.md
- Repository anchor observed: HEAD 430950148cf02ece5845cc807665e0e4f35ea7e1; R16 plan is modified in the worktree; review artifacts are untracked. No product files were changed by this review.
- Reviewer runtime/model: Codex / not exposed

## OWNER_VERDICT

R16 remains aligned with the user's outcome: source-grounded local meeting records for Gemma 4 31B and Qwen 3.8 27B, zero major fidelity hard failures, and each fresh output at least 80% of the original unrounded Gemini median in every rubric dimension. The new capability contract now specifies a private, source-free, schema-constrained probe; narrow evidence required to classify support or unsupported status; and explicit handling for all other errors. The already-reported successful probe is correctly limited to the tested Qwen/runtime combination.

Decision T now separates two questions that were previously conflated: the exact original Gemini denominator numerically cross-checks to the user's displayed medians, while the validity/applicability of the scoring rubric remains unsettled because the P7-C candidate reconciliation has unresolved claim crosswalks. This distinction is evidence-based and proportionate. It does not apply P7-C's >90% rule or allow candidate local outputs into the fresh cohort. Its pending authority decision affects C10/C14 only; implementation, available Qwen E2E, and unrelated work continue.

## GOAL_BASELINE

[VERIFIED from the authoritative user attachment] PRIMARY_OUTCOME: redesign the local pipeline so Gemma 4 31B and Qwen 3.8 27B preserve important source facts and relationships through final delivery, reduce major fidelity hard failures to zero, and reliably approach Gemini 3.5 Flash-lite quality. SUCCESS_EVIDENCE: fresh blind 3×3 per local model; every output must reach at least 80% of the original unrounded Gemini median in each of Completeness, Faithfulness, Traceability, and Usability, with zero adjudicated major fidelity hard failures. MUST_NOT_BREAK includes immutable source truth, traceability/privacy, cloud/local behavior, and explicit failure/rollback. The attachment prefers native structured output when available and explicitly permits strict JSON/schema validation when native support is unavailable or incompatible.

## GOAL_ALIGNMENT

R16 preserves the user threshold and zero-hard-failure rule. It does not turn the adjacent P7-C threshold into this task's gate, does not call provisional local candidate samples fresh, and does not treat a numerical baseline match as proof that the scoring rubric is valid. Its C1 private source-context evidence remains a scheduling premise only; Stage05 must still conduct the fresh source/hash/occurrence/relation preflight before acceptance.

## NECESSITY_AND_TRACEABILITY

The ledger, occurrence-level provenance, final-byte firewall, raw-grounded corrected view, runtime identity/capability reporting, and targeted rollback repair directly support the user's source-fidelity and reproducibility goals. R16's additional exact baseline audit records model/output identity and score evidence necessary to validate the user's explicit historical denominator. Keeping the rubric applicability question separate is also necessary: the same numerical baseline can be authentic while a disputed scoring method still makes conclusions decision-invalid.

## GATE_AND_VETO_AUDIT

The capability state is scoped to the active backend/model. Only a positively supported mode uses native schema output; only a positively identified unsupported-capability response selects the strict-JSON fallback. A generic runtime/schema/provider error is not a global “unsupported” veto or silent fallback; it remains UNKNOWN/error for that candidate. Model/context/profile evidence blockers affect the relevant acceptance only, not unrelated records/cloud processing. C10/C14 remain pending only during a bounded independent applicability adjudication, then become eligible or receive a precise scoped AUTHORITY result. These gates have decision-validity rationales and do not block implementation progress.

## COUPLING_AND_FAILURE_CONTAINMENT

The synthetic capability probe contains no meeting/source data. Unknown capability is not mislabeled as unsupported, and invalid probe output, truncation, transport, timeout, cancellation, or ordinary request/schema errors cannot silently invoke fallback. Native support evidence is not generalized beyond the tested model/runtime. Rubric crosswalk uncertainty likewise does not erase the verified original denominator or stop unrelated work; it only prevents quality scoring until evaluator validity is established.

## DESIGN_ECONOMY

Decision P uses explicit runtime metadata when trustworthy or a minimal source-free probe, without introducing a new service abstraction. The narrow unsupported-response allowlist and focused cases are commensurate with the fallback risk. Decision T makes the minimum authority determination required by the user's benchmark: exact values/hashes/identity, rounding check to the authoritative displayed medians, and scoring-method applicability. No new cohort or broad rerun is required unless applicability fails.

## CRITICAL_PATH_AND_PRIORITY

R16 keeps implementation and available end-to-end work ahead of final blind scoring. C10/C14 adjudication occurs before generating the fresh blind cohort, avoiding wasted or invalid samples without holding up the architecture, regression work, or Qwen E2E. If the P7-C scoring protocol is found invalid, re-score the same original Gemini outputs under an approved frozen protocol or scope the affected acceptance as BLOCKED/AUTHORITY; do not recycle P7-C local candidates.

## REQUIREMENT_FIDELITY

The same four user-specified dimensions are present. The verified stored medians and formula-level unrounded values round exactly to the attachment's displayed `83.9286 / 89.7959 / 93.8776 / 85.0000`. The strict P7-C `<10%` acceptance formula is explicitly excluded; the user's per-output/per-dimension `≥80%` threshold remains authoritative. C10 still also requires zero major hard failures.

## GROUNDING_AND_DRIFT

The R16 snapshot hash matches the supplied plan hash. The adjacent rubric's final SHA-256 and the cited P7-C audit, reconciliation, identity-map, and three score-sheet hashes match the R16 references. The rubric pins the same canonical transcript/checklist hashes. I verified these hashes without opening the ignored raw meeting/candidate payloads or identity map contents. Execution evidence marks the candidate run `PROVISIONAL/BLOCKED_PENDING_ADJUDICATION` and its local claim reconciliation `BLOCKED`; R16 accurately preserves that limitation. Repository status is not clean because the R16 plan and prior/new review artifacts are uncommitted; HEAD itself matches the plan anchor.

## ARCHITECTURE_AND_CONTRACTS

RV-001 is resolved. Decision P requires explicit metadata or a tiny synthetic source-free schema probe; `SUPPORTED` requires normal completion and schema-valid output; the live probe is scoped to Qwen/runtime only. `UNSUPPORTED` requires a recognized backend/model-specific explicit response and narrow allowlist. Other failures retain their own class and `UNKNOWN` capability; they do not fall through to strict JSON. C2 enumerates positive, unsupported, and unrelated-error cases, and C16 excludes unsupported-capability failures from schema-repair retry. This is testable and prevents silent downgrade or error relabeling.

Decision T is internally consistent: the exact original Gemini denominator is now verified; rubric applicability is still pending because the P7-C candidate's crosswalk/reconciliation was blocked. The remaining question is appropriately whether the rubric dimensions and Gemini scores remain valid independently of the defective local-candidate reconciliation, not whether the numeric baseline is missing. The fallback path (re-score the same original Gemini outputs under an approved frozen protocol or mark only affected acceptance BLOCKED/AUTHORITY) preserves blinding and does not weaken the user's gate.

## DATA_SECURITY_RELIABILITY

No source text, names, quotes, or raw candidate payloads were opened or copied into this report. The capability probe is source-free. Both source evidence and scoring artifacts are hash-linked and privacy-bound. Failed patch/runtime paths remain explicit and rolled back/scoped as planned.

## IMPLEMENTATION_SEQUENCE

Proceed to Stage03 only for this exact R16 hash. Stage04 can implement the bounded runtime probe/classifier and its focused tests; acceptance evidence for Qwen does not stand in for Gemma. Keep the exact Gemini denominator available for the independent scoring-applicability adjudication, which must finish before a new blind cohort. Fresh C1 acceptance still requires Stage05 preflight; model/environment blockers stay scoped.

## TESTABILITY_AND_ACCEPTANCE

C2 specifies capability success and failure-classification cases; a normal schema-valid probe must establish SUPPORT only for that backend/model instance, explicit recognized unsupported responses alone permit fallback, and other errors remain UNKNOWN/error without fallback. Baseline authority can be rechecked from the hash-linked redacted artifacts; rubric applicability is a distinct adjudication step. If invalid, the plan requires either re-scoring only the same three original Gemini outputs under an approved frozen protocol or a scoped authority blocker. Fresh 3×3 local scoring continues to use the original unrounded values and the user's threshold, not P7-C's candidate gate.

## SCOPE_AND_COMPLEXITY

No unresolved BLOCKER/MAJOR remains. The remaining C10/C14 decision is a real decision-validity prerequisite, not an unnecessary gate: score validity cannot be assumed while the governing claim reconciliation is explicitly blocked. Its closure authority is confined to scoring/profile acceptance and does not stop the primary implementation path. R16 adds no unrelated scope.

## FINDINGS

None.

## REQUIRED_PLAN_CHANGES

None.

## RESIDUAL_MINOR_NOTES

- Keep the exact unrounded medians and source hashes as verified facts even if rubric applicability later fails; do not relabel the denominator itself “missing.”
- Keep the Qwen probe's successful status limited to the tested Qwen/runtime instance; repeat detection after loading Gemma.
- No raw source/candidate payload is needed in tracked artifacts or this review.

FINAL_STATUS: PLAN_APPROVED
NEXT_ACTION: Stage03 compile a fresh handoff for R16 SHA-256 `5a5a6663e2b1258aa9b345d7dbe08249ea6661a0849ce5ba0f82dd7ad8dbc647`.
