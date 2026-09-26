# Plan Review Report

## REVIEW_METADATA

- TASK_ID: T20260924-1523-01-issue18-local-fidelity
- REVIEW_ATTEMPT: 17
- REVIEWED_PLAN_REVISION: 17
- REVIEWED_PLAN_SHA256: 835a2888be6b593a35dc1d59ff53b714b11371d8bd37b8cd5b373aa8d14896a5
- PLAN_SNAPSHOT_PATH: .agent/tasks/T20260924-1523-01-issue18-local-fidelity/review/attempt-17/plan_snapshot.md
- SNAPSHOT_SHA256: 835a2888be6b593a35dc1d59ff53b714b11371d8bd37b8cd5b373aa8d14896a5
- Repository evidence read-only; worktree contains preserved Stage04 product/test/docs diff and task artifacts. No product files or Plan were changed.
- No tests were run, per instruction.

## OWNER_VERDICT

R17 remains aligned with the user's outcome: a reliable local V2 meeting-record pipeline for Gemma 4 31B and Qwen 3.8 27B, with immutable source truth, structured evidence-grounded facts, major fidelity hard failures reduced to zero, and fresh outputs measured against the authoritative Gemini baseline. Decision U preserves compatibility across the repository's two already-selectable local provider paths; it does not add a new provider, model family, quality cohort, or cloud scope. The added Ollama path is explicitly local-only, while all original quality acceptance remains Qwen/Gemma and the user-specified rubric.

## GOAL_BASELINE

[VERIFIED from the authoritative attachment] PRIMARY_OUTCOME: make Gemma 4 31B and Qwen 3.8 27B produce reliable, source-faithful local meeting records approaching Gemini 3.5 Flash-lite quality, with zero adjudicated major fidelity hard failures. SUCCESS_EVIDENCE: selected causal claim correct end-to-end; regression/live-boundary checks; fresh blind 3×3 per local model; every output at least 80% of original unrounded Gemini median on Completeness, Faithfulness, Traceability, and Usability; privacy and delivery evidence. MUST_NOT_BREAK: raw transcript remains source of truth, cloud semantics, v4.7.4 invariants, privacy, provider/retry safety, explicit degradation/rollback. NON_GOALS: broad unrelated provider/model/cloud changes, hard-coded Issue #18 facts, lowering quality threshold, raw private payload in tracked artifacts. CRITICAL_PATH: source-aligned structured extraction → validated evidence/ledger → bounded section rendering and final-byte validation → targeted rollback-safe repair → real local E2E and authorized blind acceptance.

## TOP_DOWN_REVIEW

- **Alignment/Decision U:** The attachment's §9 explicitly branches on current runtime/model/backend support: use native schema when available; otherwise use strict JSON, parse, and Pydantic validation with exactly one schema-repair attempt. §10 calls for capability detection on the loaded model/LM Studio instance and forbids model-specific definitions of fidelity. §33 says capability detection should lead to strict-JSON fallback for a genuinely unsupported runtime. Given the verified existing Ollama local selection/dispatch path, extending the same V2 capability/fallback contract to that path preserves an existing configurable backend contract rather than broadening the outcome. Decision U limits itself to the existing local Ollama `/api/chat` route and explicitly excludes Ollama Cloud. The goal's target models, benchmark cohort, acceptance rubric, and cloud behavior remain unchanged.
- **Criticality and veto:** Both-provider native-schema wiring and runtime detection are CORE compatibility/correctness work for V2; capability is tested before source-bearing extraction. UNKNOWN is a scoped pre-source failure, not a per-record or global quality veto. Strict-JSON fallback is authorized only for recognized explicit unsupported-capability evidence; ambiguous failure cannot silently weaken the schema contract.
- **Complexity/priority:** U adds one backend-specific wire adapter plus focused contract coverage to existing dispatch; it does not introduce a new service abstraction or change the main fact pipeline. This is proportional to preserving V2 on a backend the app already selects. Cloud and Ollama Cloud are out of scope.
- **Degradation:** Optional/ambiguous fact evidence remains local; required/selected errors remain scoped. Generic backend errors remain UNKNOWN and retain their original classification, which prevents mislabeling an operational failure as unsupported.

## BOTTOM_UP_REVIEW

- **Repository grounding:** Existing service dispatch supports `lmstudio` and `ollama` through `_select_local_engine` / `_generate_with_local_engine`; current modified R16 code probes only LM Studio and routes `response_format` only there, while Ollama selection returns UNKNOWN and stops before source extraction. The escalation records this exact unimplemented backend contract. R17's Ollama adapter scope matches the existing `/api/chat` provider route, not a newly added provider.
- **Official Ollama contract:** Current official Ollama docs document local `/api/chat` `format` as either `json` or a JSON Schema, and demonstrate client-side Pydantic validation. The structured-output guide explicitly states Ollama Cloud does not currently support this feature. The official API errors page lists generic HTTP classes (including 400 for broad bad-request causes), not a stable structured-output unsupported code. Thus the plan is grounded in documented local wire shape and client validation, correctly excludes Cloud, and correctly does **not** infer unsupported capability from generic 400s. Sources: [Ollama Structured Outputs](https://docs.ollama.com/capabilities/structured-outputs), [Ollama Chat API](https://docs.ollama.com/api/chat), [Ollama API Errors](https://docs.ollama.com/api/errors).
- **SUPPORTED / UNSUPPORTED / UNKNOWN:** `SUPPORTED` requires normal completion plus exact synthetic fact-payload schema validation; probe data is source-free. `UNSUPPORTED` requires a narrow recognized backend/model-specific explicit response and alone allows strict JSON/Pydantic fallback. Invalid output, generic/unknown error text, generic 400, timeout, cancellation, transport/runtime failures, and truncation remain UNKNOWN/original error and stop before source use. This is fail-safe and testable. The absence of a stable public Ollama unsupported code is acknowledged; the design does not presume a broad classifier or promise fallback for ambiguous failures.
- **Changed-scope review:** The R17 changes are confined to the R16 Ollama gap: Decision U, W2 backend integration/fail-first coverage, and corresponding C2/C16/Definition-of-Done clauses. Earlier decisions/evidence—including strict P capability semantics, R/Q/S/T, the benchmark threshold, and status semantics—remain intact. No unrelated plan expansion was found.
- **Resume sequencing:** The R16 product diff is explicitly preserved; Stage04 stopped at the semantic boundary. After this exact revision is approved, Stage03 must compile a fresh matching handoff, then a fresh Stage04 session must re-inventory the dirty worktree and continue the preserved diff. No reset/stash/cleanup/recommit before the new review/handoff. This is a necessary consistency gate, not permission to redo or discard completed work.
- **Verification:** Plan requires backend fail-first/integration coverage for both probe and user-source schema wire requests, scoped diagnostics with no payload, the strict fallback/UNKNOWN distinction, and broader acceptance already specified. No tests were executed as reviewer.

## FINDINGS

None. Minor implementation note: since official Ollama documentation does not define a stable unsupported-capability code, keep any allowlist evidence narrow and independently test its exact signal; leave every undocumented or ambiguous response as UNKNOWN as Decision U already requires.

## REQUIRED_PLAN_CHANGES

None.

FINAL_STATUS: PLAN_APPROVED
NEXT_ACTION: Stage03 compile a fresh handoff bound to Plan Revision 17 SHA-256 `835a2888be6b593a35dc1d59ff53b714b11371d8bd37b8cd5b373aa8d14896a5`; then fresh Stage04 resumes the preserved diff after W0 re-inventory.
