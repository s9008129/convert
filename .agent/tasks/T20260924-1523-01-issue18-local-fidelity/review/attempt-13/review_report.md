# Plan Review Report

## REVIEW_METADATA
- TASK_ID: T20260924-1523-01-issue18-local-fidelity
- REVIEW_ATTEMPT: 13
- REVIEWED_PLAN_REVISION: 14
- REVIEWED_PLAN_SHA256: 77b1c5be87d23e977d4725661c7dddfcff0577e21ceb833aa25543e2764c1af5
- PLAN_SNAPSHOT_PATH: .agent/tasks/T20260924-1523-01-issue18-local-fidelity/review/attempt-13/plan_snapshot.md
- Repository anchor observed: HEAD 430950148cf02ece5845cc807665e0e4f35ea7e1; R14 plan is modified in worktree, matching the reviewed snapshot; no product-file edits were made by this review.
- Reviewer runtime/model: Codex / not exposed

## OWNER_VERDICT

The plan remains directed at the user's main outcome: make local Gemma 4 31B and Qwen 3.8 27B meeting records preserve source-backed facts, eliminate major fidelity hard failures, and reach at least 80% of the original unrounded Gemini median in each dimension for every fresh output. The core architecture and localized failure behavior are aligned. Runtime truth reporting, raw-grounded corrected views, and one-section non-regressive repair are justified by identified current-path gaps.

One material design detail needs revision before handoff: native structured-output capability detection has statuses and a fallback, but no safe positive detection or precise error-classification contract. A generic structured-output/schema/runtime failure must not be misread as “unsupported” and silently switch output modes. Optional enrichment and the P7-C candidate cohort do not block unrelated implementation. The P7-C medians are not authorized as this task’s denominator on current evidence; use only the original unrounded Gemini baseline validated against the user's disclosed benchmark, while retaining the user's ≥80% rule and zero-major-hard-fail requirement.

## GOAL_BASELINE

[VERIFIED from the authoritative user attachment] PRIMARY_OUTCOME: redesign the local meeting-record pipeline so Gemma 4 31B and Qwen 3.8 27B preserve important source facts and relationships through delivery, reduce major fidelity hard fails to zero, and reliably approach Gemini 3.5 Flash-lite quality. SUCCESS_EVIDENCE includes fresh blind 3×3 outputs per local model, each output scoring at least 80% of the original unrounded Gemini median in each of Completeness, Faithfulness, Traceability, and Usability, with zero adjudicated major fidelity hard fails. MUST_NOT_BREAK includes immutable source truth, privacy, local/cloud isolation, explicit failure/rollback, and traceability. The user's attachment recommends structured output with strict JSON/schema validation fallback, supports raw/corrected dual views, targeted repair and source-backed checks; these are means, not immutable APIs.

## GOAL_ALIGNMENT

R14 preserves the primary outcome and explicit ≥80% gate. It does not elevate the adjacent P7-C task's >90% bar, reuse its local candidates as fresh samples, or make a missing model/evaluator a per-record veto. The selected causal claim's expected relation is recorded only as a redacted adjudication outcome with the stated speaker-context caveat; fresh independent source preflight remains mandatory before acceptance. This appropriately separates scheduling evidence from acceptance evidence.

## NECESSITY_AND_TRACEABILITY

The ledger, raw occurrence provenance, final-byte checks, corrected comprehension view with raw-only grounding, runtime truth reporting, and targeted patch/rollback each map to source fidelity, requested reproducibility, or a must-not-break invariant. Reusing the request-scoped API instead of introducing an EvidenceStore is economical. Verified-only template correction and local handling of unresolved optional claims are appropriately bounded.

The adjacent-task rubric is frozen before that cohort's outputs and hash-linked to the same canonical transcript and checklist as cited by R14. Its four dimensions match the user's dimensions. However, it prescribes a strict <10% gap and its execution labels the candidate cohort provisional/blocked, with unresolved claim crosswalks. Those candidate outputs and their gate cannot be imported. The user attachment explicitly keeps the denominator as the original unrounded Gemini median and gives displayed historical medians; the available redacted evidence does not establish that the adjacent task's candidate medians are those original denominators. Therefore, do not authorize those candidate medians as denominators now. R14 correctly keeps C10/C14 pending authority adjudication; that adjudication must validate exact historical baseline score/model/config/rubric identity and the crosswalk to the user's disclosed benchmark, or report a scoped AUTHORITY blocker. Preserve the user's ≥80% threshold and zero-hard-fail criterion.

## GATE_AND_VETO_AUDIT

Record rejection is narrowly limited to decisive selected/required fidelity defects and final-byte postcondition failures. Unknown/ambiguous optional evidence, unavailable corrected alignment, and glossary enrichment remain local. Gemma runtime unavailability affects Gemma acceptance only. C10/C14 are system-level acceptance/closure inputs, not per-record vetoes. These scopes are proportionate and explicit.

## COUPLING_AND_FAILURE_CONTAINMENT

Raw remains the only evidence authority; corrected text may aid comprehension only through safe alignment, and corrected-only support cannot ground claims. Unavailable/ambiguous alignment degrades to raw for that segment. Targeted repair is scoped to one affected section, bounded to one candidate attempt, and guarded by validation plus rollback. Failure does not silently fall back to V1 or impair unrelated records/cloud work.

## DESIGN_ECONOMY

Decisions P–R reuse current request/runtime structures, existing snapshots, and rollback machinery. No new EvidenceStore is mandated absent proof of insufficiency. Capability probing is necessary only to honor the user's supported-native-output preference without false claims; it needs a narrow mechanism and must not become a broad provider abstraction.

## CRITICAL_PATH_AND_PRIORITY

W2/W6 integration corrections and fail-first contracts precede live E2E and blind cohorts. Candidate evaluator applicability is independently adjudicated before a new blind cohort, while implementation and other valid evidence can proceed. This is correct priority and avoids letting an unresolved benchmark input stall unrelated architecture work.

## REQUIREMENT_FIDELITY

R14 retains all major user requirements, preserves the ≥80% gate, and keeps privacy-safe/redacted artifacts. Its C10/C14 plan correctly distinguishes candidate rubric evidence from authority and prevents importing the adjacent rubric's stricter threshold.

## GROUNDING_AND_DRIFT

The reviewed plan snapshot hash matches the requested R14 hash. The plan records HEAD/origin at R14 planning; observed HEAD matches. Worktree status shows the reviewed R14 plan itself is modified; this review did not modify it. Cited P7-C rubric SHA-256 verifies as ecdf138bc3e957d0747ed3e95f87205be384c35959b716d1ea61cc3a419c64eb. The rubric links to the same transcript/checklist hashes reported by R14. The adjacent execution evidence distinguishes the candidate gate failure from unresolved crosswalks; neither is fresh acceptance for this task.

## ARCHITECTURE_AND_CONTRACTS

The architecture and new runtime contracts are otherwise sound. One API-detection contract remains underspecified (RV-001 below): active-backend/model detection is required, but the plan does not state what evidence constitutes SUPPORTED or UNSUPPORTED, nor distinguish an explicit unsupported-capability response from ordinary request, schema, or generation failures. This is material because LM Studio documents JSON Schema via `/v1/chat/completions` and warns that not all models support it ([Structured Output docs](https://lmstudio.ai/docs/developer/openai-compat/structured-output)); the model-info endpoint documents fields such as state/context but does not declare structured-output support ([REST API endpoints](https://lmstudio.ai/docs/developer/rest/endpoints)). A synthetic, source-free probe reported during this review established schema-valid `json_schema` support for the currently loaded Qwen/runtime when a second probe used adequate token budget; the first low-budget attempt ended at `finish_reason=length` and is a token-cap limitation, not evidence of unsupported capability. This shows a safe positive probe is feasible for Qwen, but R14 does not define that detection or classify other failures. A generic failure cannot safely establish “unsupported.”

## DATA_SECURITY_RELIABILITY

Privacy remains fail-closed; no raw source/context payload is included in this review. Source occurrence resolution and corrected-view alignment are conservative. The R14 source-context adjudication is redacted and caveated, and Stage05 repeats verification. Repair rollback and operational-error classification are explicitly retained.

## IMPLEMENTATION_SEQUENCE

Require the capability detection/error-classification detail and corresponding acceptance cases in the same-plan revision before Stage03. Keep existing order: implementation/contracts, fresh C1 source preflight and E2E when ready, baseline applicability decision before fresh blind scoring, then closure checks. No new branch, runtime abstraction, or broad rewrite is needed.

## TESTABILITY_AND_ACCEPTANCE

C2 requires live runtime capability reporting; C16 separately protects schema-repair classification. Extend the acceptance contract to demonstrate (1) positive native support from a safe probe or trustworthy active-runtime metadata, (2) fallback only after a specifically classified unsupported-capability response, and (3) unrelated schema-invalid, provider/runtime, timeout, transport, or cancellation errors are not converted into “unsupported” or a silent fallback. If detection is inconclusive, record UNKNOWN and use only the explicitly approved handling for that state; do not claim support. Keep C10 blocked/not-run until the original denominator's identity and applicability are proven; do not score with candidate local cohort outputs.

## SCOPE_AND_COMPLEXITY

The architecture work is broad but directly requested; R14's delta is limited to four concrete integration gaps and does not replace the design. The candidate cohort and Gemma environment issue are correctly scoped and non-blocking to unrelated implementation. No additional moving part is requested beyond a bounded capability probe/classifier.

## FINDINGS

- ID: RV-001
- severity: MAJOR
- category: ARCHITECTURE
- affected plan: Decision P; W2; C2 and C16
- evidence: R14 requires native structured-output detection with SUPPORTED/UNSUPPORTED/UNKNOWN diagnostics, but does not specify a positive detection source/probe or the exact boundary for classifying UNSUPPORTED. LM Studio documents JSON Schema via `/v1/chat/completions` and warns that not all models support it ([Structured Output docs](https://lmstudio.ai/docs/developer/openai-compat/structured-output)); the model-info endpoint documents fields such as state/context but does not declare structured-output support ([REST API endpoints](https://lmstudio.ai/docs/developer/rest/endpoints)). A source-free runtime probe succeeded for the currently loaded Qwen/model combination only; it does not establish Gemma or all-model support and does not define the product detection/error-classification contract.
- concrete failure/rework mechanism: An implementation may infer “unsupported” from a generic HTTP/request/schema/runtime failure and silently fall back to strict JSON, masking a product/runtime defect and losing the user-requested native mode; conversely it may report support without evidence. The current plan cannot produce a deterministic fail-first test for that boundary.
- smallest required correction: Specify a safe positive mechanism (e.g. a minimal schema-constrained probe against the active backend/model, or trustworthy runtime metadata if available) and classify only explicit, recognized unsupported-capability evidence as UNSUPPORTED/fallback. Other probe/runtime/schema/generation errors retain their own failure class and cannot be relabeled as unsupported; UNKNOWN remains truthful. Add focused tests for supported, explicitly unsupported, and unrelated-error cases.

## REQUIRED_PLAN_CHANGES

1. Revise Decision P/W2 and C2 (and align C16 if needed) with the bounded positive-detection and exact unsupported-error classification contract described in RV-001. Do not broaden to a new abstraction.
2. Preserve C10/C14's current pending authority status. Do not authorize P7-C's provisional candidate medians/local outputs as this task's denominator; use only verified original unrounded Gemini baselines corresponding to the user's benchmark. If the original identity/crosswalk cannot be established, retain scoped AUTHORITY blocker and do not start/count a fresh blind cohort.

## RESIDUAL_MINOR_NOTES

- User-requested C1 relation adjudication may schedule the test, but does not prove acceptance; the plan already retains the fresh Stage05 source/hash/occurrence/relation check.
- The candidate rubric's strict >90% bar and candidate local outputs remain strictly out of scope for this task's pass calculation.

FINAL_STATUS: PLAN_REVISION_REQUIRED
NEXT_ACTION: Stage 01 update this same task's R14 plan with a narrowly specified structured-output capability probe/error-classification contract, increment PLAN_REVISION, and submit the new hash for fresh independent Review before Stage03.
