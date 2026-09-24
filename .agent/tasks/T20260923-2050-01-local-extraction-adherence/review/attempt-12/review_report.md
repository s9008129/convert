PLAN_REVISION_REQUIRED

# Stage 02 Independent Plan Review Report

## REVIEW_METADATA

- TASK_ID: `T20260923-2050-01-local-extraction-adherence`
- REVIEW_ATTEMPT: `attempt-12`
- REVIEWED_PLAN_REVISION: `12`
- REVIEWED_PLAN_SHA256: `267285a36303537fd20a7d2d380915aecf2f82fd11bd94dd02efbc856481c34b`
- PLAN_SNAPSHOT_PATH: `.agent/tasks/T20260923-2050-01-local-extraction-adherence/review/attempt-12/plan_snapshot.md`
- SNAPSHOT_STATUS: exact byte-for-byte copy made before judgment
- SNAPSHOT_TIME_UTC: `2026-09-24T00:54:00Z`
- REVIEW_SCOPE: fresh read-only Plan review; no product edits, plan edits, tests, model inference, probe, build, E2E, commit, or push

## GOAL_BASELINE

- **PRIMARY_OUTCOME:** Improve meeting-record quality so Gemma 4 31B and Qwen 3.8 27B each are strictly less than 10% worse than the project’s Gemini 3.5 Flash-lite quality, per core quality dimension.
- **SUCCESS_EVIDENCE:** Valid same-input comparisons for both local models against the verified Gemini 3.5 Flash-lite baseline, with model/input/template provenance, no material fabrication, and a final product configuration that actually uses the accepted local profile; independent Stage 05 acceptance is required.
- **MUST_NOT_BREAK:** cloud/local routing isolation, current prompt/config semantics unless deliberately reviewed, byte rollback, truthful status routing, model/input provenance, privacy boundaries, and no partial record presented as complete.
- **NON_GOALS:** Qwen 3.6, changing the `<10%` criterion, selecting only favorable samples, silently changing the rubric/checklist, cross-meeting generalization claims, Windows/Ollama実機, and unreviewed product semantic changes.
- **CRITICAL_PATH:** freeze and verify the benchmark contract → obtain 3 valid cloud, Gemma, and Qwen outputs on the same canonical transcript → independently score every local output against the cloud median on every core dimension → persist the accepted local profile in the actual product configuration and rerun the affected acceptance → run the two supporting audio-to-DOCX journeys → Stage 05 acceptance.

## OWNER_VERDICT

The Plan has the right benchmark goal and mostly sound provenance/privacy/status controls. The essential gap is that it measures a temporary profile while the actual product defaults remain off, then defers the required persistence and revalidation to an unspecified future wave. That can prove an experiment but cannot close the user’s runtime-quality goal. The scoring rubric also needs an immutable, independently reproducible artifact before outputs are inspected. Supporting E2E and historical diagnostics are not global blockers.

## GOAL_ALIGNMENT

The stated rev12 outcome matches the user-corrected Gemma 4 31B / Qwen 3.8 27B versus Gemini 3.5 Flash-lite requirement. The unresolved persistence gap is a goal-alignment/sequence defect, not a disagreement with the proposed quality dimensions.

## NECESSITY_AND_TRACEABILITY

The 3×3 same-transcript comparisons, four non-compensating quality dimensions, provenance hashes, and fabrication hard fail all directly serve the primary outcome. The two supporting audio-to-DOCX journeys, raw/cache separation, and status fixtures serve integration, privacy, and truthful closure. The missing element is the necessary product-setting persistence wave: the Plan labels it CORE in `PROFILE-PERSISTENCE` but does not schedule its implementation or remeasurement.

## GATE_AND_VETO_AUDIT

Model/input/checklist identity, fabrication, and scoring validity may block a parity conclusion because they make the comparison undefined or unsafe. ASR/helper/DOCX gates are appropriately scoped to supporting delivery evidence. No unjustified supporting global veto was found.

## COUPLING_AND_FAILURE_CONTAINMENT

Call-budget, helper, and path-collision failures are scoped to the affected summary/E2E and preserve prior evidence. The benchmark’s CORE result is not incorrectly vetoed by an integration-only failure. Persistence is instead coupled to closure without an executable path, producing a closure/rework gap.

## DESIGN_ECONOMY

Reuse of the existing summarizer, fixed transcript/checklist, and no generic benchmark framework is economical. The required addition is a small explicit persistence-and-rerun wave, not a new framework. A versioned rubric artifact is also a minimal acceptance dependency, not over-engineering.

## CRITICAL_PATH_AND_PRIORITY

The Plan correctly prioritizes parity before supporting E2E, but its current critical path terminates before the product can use the accepted profile. Persistence and final revalidation must be placed after a passing candidate benchmark and before closure/push.

## REQUIREMENT_FIDELITY

Qwen is consistently 27B and the strict `<10%` semantics are explicit. The Plan preserves the user’s requested independent acceptance and autonomous execution boundary. It must not treat candidate-profile success as the final product outcome.

## GROUNDING_AND_DRIFT

The fixed transcript/checklist and attempt-03 collision are repository-grounded and hash-checked. The replay README contains stale historical budget text, but the Plan explicitly excludes that item from current execution. The current code defaults verify the Plan’s own persistence warning.

## ARCHITECTURE_AND_CONTRACTS

The local-only flags and cloud isolation are specified, and the status/rollback contracts are detailed. The revised Plan must define which config source is changed, how local profile values are persisted without changing cloud behavior, and how the final config identity is included in the rerun evidence.

## DATA_SECURITY_RELIABILITY

The raw-cache/task-derivative split, no raw payload in task artifacts, append-only prior-attempt handling, and fail-closed runner provenance are appropriate. No new privacy or destructive-data defect was found.

## IMPLEMENTATION_SEQUENCE

Candidate benchmark → profile persistence → fresh 3×3 validation → supporting E2E → Stage 05 is the minimum sequence. The current rev12 sequence omits the second and third steps after candidate success.

## TESTABILITY_AND_ACCEPTANCE

The parity formula and status matrix are testable, but human rubric scoring is not independently reproducible without a frozen hashed rubric, scorer/blinding record, and adjudication policy. `PROFILE-PERSISTENCE` is currently a required check with no planned execution wave.

## SCOPE_AND_COMPLEXITY

The planned scope is otherwise bounded. Do not add cross-meeting generalization or a benchmark framework to fix these findings; add only the missing persistence/revalidation and scoring-evidence contracts.

## PREFLIGHT AND REPOSITORY EVIDENCE

- `[VERIFIED]` The snapshot and canonical plan both have SHA-256 `267285a36303537fd20a7d2d380915aecf2f82fd11bd94dd02efbc856481c34b`; the snapshot records revision 12 at its header (snapshot lines 1–6).
- `[VERIFIED]` The canonical transcript exists and hashes to the plan’s value `b7b9e5e05be5a560101312d9fb954d2e6aa10044febb8d3fca5a79f3931d9db0` (plan snapshot line 374; repository `data/cache/e2e/p7b-qwen27b-e8/transcript.txt`). The checklist exists at the plan’s task-artifact path and hashes to `cf012d1f6983f67ecb47cc7a6486e48c110a6b2782ad94cccf0332a4ec6ec001` (plan snapshot line 374; `.agent/tasks/T20260922-2037-02-local-model-quality-parity/quality/fact_checklist.json`).
- `[VERIFIED]` The actual code defaults match the plan’s persistence warning: `LOCAL_LLM_MAX_LOCAL_REFINEMENT_ROUNDS=0`, refinement budget `0`, fact coverage `false`, adherence `false`, and extraction ceiling `6000`/call budget `0` (`backend/core/config.py:280-309`, `:671-685`). The accepted benchmark profile instead requires ceiling `4500`, extraction budget `4`, both flags `true`, and local refinement settings `3` (snapshot line 376).
- `[VERIFIED]` `scripts/e2e/rerun_local_summarize.py` supports `--mode cloud` and `--mode local` (lines 82–86) but has no explicit profile/model/seed arguments; profile application and per-run isolation therefore must be specified by the Plan’s execution procedure, not inferred from the script.
- `[VERIFIED]` The attempt-03 historical record preserves the path-collision failure as non-quality evidence: runner exit `1`, zero artifacts/runtime, inference `UNPROVEN`, and no remaining runs counted (task `e2e/attempt-03/result.md:46-76`). The runner itself creates `artifacts_dir` with `exist_ok=False` (`scripts/e2e/run_owned_e2e.py:1874-1880`), so the rev12 recovery rule is grounded.
- `[VERIFIED]` The chunk replay evidence supports the 4,500-token prediction but explicitly labels the outcome as unverified and says it cannot prove improved model completeness (`evidence/chunk-replay-p7c/README.md:45-64`). It is suitable as preregistration evidence, not as quality acceptance evidence.

## PASS A — TOP-DOWN GOAL ALIGNMENT AND DESIGN ECONOMY

### RV-001 — goal attainment is deferred beyond this Plan (BLOCKER; GOAL_MISALIGNMENT / SEQUENCING)

- **Affected plan:** snapshot lines 224–232, 376, 455–462, and verification matrix line 500 (`PROFILE-PERSISTENCE`).
- **Evidence:** The plan explicitly says the benchmark flags default to `false`; even if the temporary profile passes, a later reviewed implementation must make the settings effective and rerun before the goal may be claimed (snapshot lines 224–225 and 376). Repository defaults confirm this (`backend/core/config.py:280-309,671-685`).
- **Failure/rework mechanism:** The current critical path can end after 9 successful temporary-profile comparisons plus two supporting E2Es, while the actual product continues using different defaults. That proves a candidate experiment, not the user’s requested improved runtime outcome. The matrix correctly marks `PROFILE-PERSISTENCE` CORE, but no rev12 implementation wave, setting mutation, commit target, or post-persistence 3×3 revalidation is scheduled. This creates an acceptance dead end: a passing benchmark still cannot close the task, and a later unplanned wave would require a new design/review cycle.
- **Minimum required correction:** Add an explicit CORE implementation wave after benchmark evidence (or make the task explicitly measurement-only, which would no longer satisfy the stated user goal). The wave must define the exact persisted settings/config source, local/cloud isolation, required focused/rollback checks, the product commit, and a fresh 3×3 comparison plus Stage 05 acceptance using the persisted configuration. Update the critical path, sequencing, status matrix, and push/closure condition consistently.

### RV-002 — independent scoring contract is not sufficiently frozen/reproducible (MAJOR; TEST / ACCEPTANCE)

- **Affected plan:** snapshot lines 380–389, 391, 460–462, and `PARITY-*` rows in the matrix around lines 496–504.
- **Evidence:** The Plan defines four dimensions and says the rubric must be frozen before reading outputs (line 387), but names no checked-in rubric artifact, revision/hash, scorer count, adjudication rule, or blinded assignment record. It also requires Stage 05 to score local raw outputs independently (line 380) while Stage 04 is to retain only allowlisted derivatives (line 460), leaving no explicit immutable link proving which frozen rubric and scoring decisions produced the reported numbers.
- **Failure/rework mechanism:** Subjective `FAITHFULNESS`, `TRACEABILITY`, and especially the five-part `USABILITY` score can vary between raters or be tuned after seeing outputs. Without a frozen, hashed rubric and an adjudication/independent-scoring record, the `<10%` result is not independently reproducible and can be challenged as measurement noise or post-hoc scoring.
- **Minimum required correction:** Add a versioned rubric artifact (or an immutable task-scoped redacted derivative) with SHA-256, freeze timestamp/owner before first output inspection, blinded run assignment, scorer count, and disagreement/adjudication policy. Specify which score artifact Stage 05 independently recomputes and how its hash is linked to each output/run alias without copying raw payloads.

### Top-down strengths

- `[VERIFIED]` The Plan correctly makes the user’s corrected Qwen identity explicit as `qwen3.8-27b-splash` / Qwen 3.8 27B and compares each local output separately to Gemini’s median, with strict `<10%` per dimension and no cross-dimension compensation (snapshot lines 224–225, 374–395).
- `[VERIFIED]` Core quality is not replaced by historical byte coverage, item counts, density, or E2E convenience metrics (lines 382–395). Supporting E2E is correctly sequenced after parity and does not veto already-valid same-transcript parity (lines 391, 462).
- `[VERIFIED]` Global gates are mostly proportionate: model/input/checklist provenance and fabrication are decision-validity gates; ASR/helper and DOCX gates are scoped to supporting integration. Partial-summary behavior and call-budget failure are local rather than global (lines 229–230, 302–306, 431–443).
- `[VERIFIED]` Complexity is bounded by reuse of the existing summarization path, fixed transcript/checklist, and no new benchmark framework (line 231). The attempt-03 recovery preserves old cache/result and delegates creation of runner-owned directories to the runner (lines 458, 462).

## PASS B — BOTTOM-UP ENGINEERING / ACCEPTANCE REVIEW

### Evidence and contracts

- `[VERIFIED]` Model/provider identity checks are required before running, including Gemini model, both local keys, template, settings, input hash, and checklist hash; invalid identity is scoped `BLOCKED` rather than silently substituted (snapshot lines 374–376, 459).
- `[VERIFIED]` The runner path-collision recovery is concrete and preserves append-only history: old attempt/cache is not reused or counted, and new raw/runtime directories must not be pre-created (lines 219, 458, 462; attempt-03 result lines 68–76).
- `[VERIFIED]` Privacy handling correctly treats full artifacts/runtime as raw and limits task evidence to allowlisted hashes/booleans/IDs (snapshot lines 391, 460, 481–485). The planned detached-worktree provenance and clean-HEAD checks are consistent with the runner’s fail-closed behavior.
- `[VERIFIED]` Status semantics are unusually explicit: the six orthogonal fields, per-check evidence roles, scoped blockers, baseline-delta handling, immutable Stage 04 snapshot, and Stage 05 routing are specified (snapshot lines 490–560). Supporting `FULL-SUITE` is `BASELINE_DELTA`, not an unjustified quality veto.

### Bottom-up residual risks (covered after revision)

- `[MINOR]` The fixed transcript is sourced from a prior Qwen E8 cache while the replay evidence uses the prior Gemma E8 transcript (snapshot lines 374 and 291–296). The Plan does pin and re-hash the actual benchmark input, so this is not a correctness defect; Stage 04 should retain the source/cache provenance and not imply the replay input is the benchmark input.
- `[MINOR]` The replay README retains an old prediction mentioning `CALL_BUDGET` default `2` and an obsolete cost reference (`evidence/chunk-replay-p7c/README.md:56-57`), while the rev12 Plan explicitly disallows using that prediction (snapshot lines 291–302). The Plan should continue to exclude it from execution evidence; no gate change is needed.

## REQUIRED_PLAN_CHANGES

1. Resolve **RV-001** by adding a reviewed, executable profile-persistence/product-configuration wave and mandatory post-persistence revalidation. Do not allow `PROFILE-PERSISTENCE` to remain a required CORE check with no scheduled path to satisfy it.
2. Resolve **RV-002** by freezing and hashing the scoring rubric and specifying independent scorer/blinding/adjudication evidence before any output is inspected.
3. Keep the existing rev12 parity rules, model identities, path-collision recovery, privacy boundaries, and scoped E2E/status semantics intact while updating dependent sequencing and acceptance rows.

## RESIDUAL_RISK

`[UNVERIFIED]` No model inference, benchmark output, scoring, helper probe, E2E, or Stage 05 acceptance was run in this review. The gate is about Plan readiness and does not claim any quality result. A single fixed transcript remains insufficient for broad cross-meeting generalization; the Plan correctly keeps that claim out of scope.

FINAL_STATUS: PLAN_REVISION_REQUIRED
NEXT_ACTION: Stage 01 revise the same task to add the persistence/revalidation critical path and frozen scoring artifact, increment to revision 13, then obtain a fresh Stage 02 review against the new snapshot/hash. Do not generate a rev12 handoff or run implementation/E2E from this revision.
