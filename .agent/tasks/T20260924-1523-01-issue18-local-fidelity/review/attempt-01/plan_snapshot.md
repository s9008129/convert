# Issue #18 Local Meeting Record Architecture V2 — Plan Revision 2

## META

- TASK_ID: T20260924-1523-01-issue18-local-fidelity
- ISSUE: #18; continue Draft PR #19
- STATUS: READY_FOR_REVIEW
- TASK_MODE: REVIEW_REVISION
- PLAN_REVISION: 2
- TASK_CLASS: CRITICAL
- REVIEW_REQUIRED: YES
- INDEPENDENT_ACCEPTANCE_REQUIRED: YES
- E2E_REQUIRED: YES
- ACCEPTANCE_MODE: CONTRACT + INTEGRATION + E2E + BLIND_RUBRIC
- BASE_BRANCH: main
- IMPLEMENTATION_BRANCH: issue-18-first-divergence-diagnostic
- ANCHOR_HEAD: eb3ca049cc72d21d2f4db974db5314b5f399d736
- PR: #19, open and Draft
- WORKTREE_AT_PLANNING: clean
- SAFETY_BRANCHES_PRESENT: backup/issue-18-before-gpt6-20260924-074037; backup/issue-18-before-gpt6-20260924-153522
- AUTHORITATIVE_GOAL: user-provided Local Meeting Record Architecture V2 attachment, read 2026-09-24
- SUPERSEDES: revision 1's “smallest evidence-branch repair / do not redesign” scope. Revision 1 execution evidence is retained and remains authoritative where not changed below.

## OWNER_CHECK

- **Primary goal:** make the local Gemma 4 31B and Qwen 3.8 27B pipeline preserve source facts through an evidence-grounded, structured, deterministically checked process, and bring every fresh blind output to at least 80% of the frozen Gemini median in every rubric dimension with zero major fidelity hard fails.
- **Essential:** structured facts with source provenance; deterministic consolidation; section-scoped generation; source-backed fidelity checks; non-regressive targeted repair; local E2E and blind acceptance.
- **Supporting:** model runtime profiles/capability reporting, performance diagnostics, broader held-out examples, and selected reusable mechanisms from prior experiments. These improve controlled operation but cannot veto unrelated valid sections.
- **Best effort/deferred:** richer transcript correction and glossary enrichment where no verified mapping exists; they must remain explicitly uncertain and may not become source truth.
- **What can stop an individual record:** failure to obtain a schema-valid CORE fact set after one schema-only repair attempt, or an unresolved selected-claim causal-direction failure. These make the record's core source fidelity untrustworthy. Optional enrichment or one unsupported non-core field must be contained locally and cannot globally veto the record.
- **Biggest risk:** deterministic checks cannot prove semantic truth for every Chinese relation; the frozen unrounded blind evaluator may also be unavailable. Architecture work must continue if the evaluator is missing, but quality acceptance remains pending/blocked rather than inferred.

## GOAL_CONTRACT

- PRIMARY_OUTCOME: an operational local V2 meeting-record path that preserves the source as immutable truth, carries structured claims and evidence references, catches or contains major fidelity errors, and produces fresh Gemma/Qwen outputs satisfying the frozen blind quality gate.
- SUCCESS_EVIDENCE: selected claim `C-R03-F056-CAUSAL-DIRECTION` is correct from source through structured extraction, ledger, rendering, and final delivery; regression suite covers the specified failure classes; full repository and docs checks pass; fresh local E2E and blind 3+3 cohort meet every per-output/per-dimension threshold with zero adjudicated major fidelity hard fails; privacy audit and PR update are recorded.
- MUST_NOT_BREAK: cloud output semantics; v4.7.4 no-hard-truncation, fail-loud merge, loaded LM Studio instance as context authority, thinking-disable compatibility, immutable per-task model selection, retry safety, explicit degradation; templates/record output contract; privacy and provenance; existing deterministic post-processing.
- NON_GOALS: direct merge of either experimental branch; hard-coded Issue #18 claims/timestamps; model-family-specific definitions of fidelity; production transcript/raw prompt/raw output retention; a second LLM judge as truth oracle; lowering the frozen gate; broad ASR or unrelated UI rework.
- CRITICAL_PATH: evidence/schema types → structured extraction with validated provenance → deterministic ledger consolidation/conflicts → selected-claim end-to-end correctness → section planning/rendering/assembly → deterministic fidelity firewall → targeted patch with rollback → local E2E → blind cohort.

## SOURCE_OF_TRUTH_AND_BASELINE

- Raw transcript is the sole immutable source of truth. Corrected transcript is a comprehension view only. Ledger, evidence spans, notes, and records are derived data.
- Existing `claim-attempt-3-baseline.json` verifies source and chunk 3 input as correct, first divergence at `extraction.chunk.3.raw`, downstream consolidation/final delivery missing the claim. Existing post-repair attempts document that prompt-only/source-in-final recovery did not recover it. Do not re-diagnose this result or treat those candidates as accepted.
- Current branch head is `eb3ca049cc72d21d2f4db974db5314b5f399d736`; PR #19 is open Draft. Worktree was clean at planning.
- Current call path is `SummarizationService._summarize_with_local_pipeline`: free-text chunk extraction → note consolidation/optional LLM merge → whole-record generation → whole-record validation against notes → full-record refinement. Cloud has separate transcript-aware builders and must remain behaviorally unchanged.
- Experimental branches are read-only evidence libraries. Initial inspection found candidate coverage/fidelity, glossary/term, source-tag, number/date/entity/attribution, dedupe, and refinement rollback mechanisms; each must be isolated, checked against the present repository contract, and ported only where a concrete acceptance obligation is served.

## REQUIREMENTS_AND_CRITICALITY

| ID | Requirement | Class | Decision contribution / failure behavior |
|---|---|---|---|
| R1 | Runtime evidence spans with immutable raw text, optional corrected view, source hash and stable span identity; raw content stays in ignored local runtime storage | CORE | Provenance is necessary to establish the source for every rendered claim. Missing span for an optional claim degrades that claim; missing evidence for the selected/core claim blocks acceptance. |
| R2 | Typed FactClaim/FactLedger including relation direction, condition/dependency, polarity/negation, number/unit, date, attribution/uncertainty, and evidence refs | CORE | Prevents natural-language-only contracts and makes hard-fail classes observable. Unknown/ambiguous is a valid value, not schema failure. |
| R3 | Strict structured extraction, native schema capability when supported, strict JSON+Pydantic otherwise, exactly one schema-only repair, then explicit failure | CORE | Invalid core ledger cannot safely feed rendering; never silently accept or masquerade fallback as V2 success. |
| R4 | Deterministic dedupe by normalized claim/evidence identity and overlap; detect same-evidence conflicts without choosing a winner | CORE | Prevents duplicate and contradictory facts from being silently propagated; conflicts stay explicit/locally unresolved. |
| R5 | Deterministic section plan and per-section render from allowed claims plus resolved evidence; deterministic assembler | CORE | Limits unsupported content and isolates failures to relevant sections. Cloud generation remains untouched. |
| R6 | Source-grounded fidelity/coverage firewall for selected core relation, numbers/dates, entities, attribution, source tags, duplication, and template coverage; reuse proven mechanisms selectively | CORE | Detects known high-risk mismatches. A check that cannot establish certainty reports unknown/ambiguous; no speculative global veto. Selected causal inversion/missing relation rejects the record candidate. |
| R7 | Targeted section patch with before/after quality snapshot and rollback; never default full-document rewrite | CORE | Prevents fixing one issue from silently damaging other sections. Reject if required claim coverage falls or unsupported high-risk facts increase. |
| R8 | Separate model-independent QualityPolicy from runtime profiles/capability detection for Qwen/Gemma; evidence-based context strategy and explicit unsupported-param diagnostics | SUPPORTING | Allows model-specific controls without changing fidelity criteria. Unsupported sampler capability downgrades explicitly; does not silently redefine quality or cloud behavior. |
| R9 | Expanded privacy-safe stage diagnostics and explicit v1/v2 selection | CORE | Enables first-divergence evidence and safe rollback. Explicit v1 selection is an operator choice; no hidden automatic fallback after V2 failure. |
| R10 | Synthetic fail-first cases A–I; focused/full/docs checks; selected-claim E2E; Gemma/Qwen fresh E2E; blind fresh 3+3 gate | CORE | Direct evidence of functional and requested quality outcome; diagnostic runs excluded from cohort. |
| R11 | Measure calls, time, input/output tokens, context and patch count; held-out validation if safe repository data exists | SUPPORTING | Operational trade-off and overfit visibility; absence does not veto the core path unless it reveals a correctness risk. |
| R12 | Update execution record/docs and PR #19; no private source data in tracked/GitHub artifacts | CORE | Durable, auditable delivery and privacy invariant. |

## DECISION_CONTRIBUTION_MATRIX

| Element | Contribution | Criticality | Influence | Global veto? | Failure behavior |
|---|---|---|---|---|---|
| Raw source hash + evidence refs for selected/core claim | Establishes traceability and truth anchor | CORE | N/A | Yes, selected/core claim only | Stop CORE acceptance if absent/mismatched; unrelated evidence gaps remain local. |
| Corrected transcript/glossary | Improves comprehension | SUPPORTING | N/A | No | Continue from raw source; retain uncertainty and never promote conjecture to fact. |
| Schema-valid extraction | Supplies parseable typed facts | CORE | N/A | Per required chunk/section | One repair retry; then explicit V2 failure, no silent v1 fallback. |
| Optional claim/entity enrichment | Improves completeness | BEST_EFFORT | N/A | No | Omit/mark unknown; do not block unrelated sections. |
| Causal/negation/condition validators | Protects decision meaning | CORE | N/A | Selected claim / affected section | Reject candidate or mark unresolved; never choose conflicting claim arbitrarily. |
| Number/date/entity/attribution checks | Prevent high-risk fabrication/distortion | CORE checks; individual enrichment SUPPORTING | N/A | Only when the fact is material and source comparison is decisive | Local issue + patch/rollback; ambiguous evidence stays unresolved, not a whole-pipeline veto. |
| Runtime profile/capability probes | Stable execution and diagnostics | SUPPORTING | N/A | No | Report unsupported parameter and explicit downgrade; preserve baseline controls. |
| Blind evaluator and frozen baseline | Proves external quality target | CORE acceptance | N/A | Blocks quality/task closure, not implementation progress | If genuinely missing, report `QUALITY_ACCEPTANCE_BLOCKED_BY_MISSING_FROZEN_EVALUATOR`; finish all other work. |
| Full repository/docs checks | Regressions/repo health | SUPPORTING outcome evidence; required closure check | N/A | HARD_CLEAN closure gate by user DoD | Report scoped check failure; do not call it product CORE failure unless task regression evidence shows it. |

## SEMANTIC_CONTRACT_AND_FAILURE_CONTAINMENT

- V2 is additive and opt-in behind a repository-conventional local pipeline selector (exact key to be selected after config inspection); default remains v1 until architecture and acceptance pass. No data migration is planned.
- V2 schema failure after one repair is explicit failure for that V2 run. It cannot be converted to a successful V1 result invisibly. Operator can explicitly choose V1 for rollback.
- Evidence absence/conflict is scoped to affected claim/section except the selected CORE claim and its acceptance. Optional categories do not gate unrelated sections.
- A failed targeted patch is rolled back byte-for-byte to the last accepted section. No semantic validator failure is “fixed” by weakening policy.
- Cloud path and shared semantics are frozen; any unavoidable shared helper change requires a cloud golden/contract regression demonstrating unchanged behavior.

## TARGET_CONTRACT

1. `EvidenceSpan`: stable span ID, optional offsets/speaker key, raw text, optional corrected text, source SHA-256. Full text is runtime/local-cache only and gitignored.
2. `FactClaim`/`FactLedger`: normalized typed claims, explicit status/uncertainty, explicit subject-predicate-object and polarity; relation type includes causal/conditional/temporal; numeric/date/attribution fields; one or more evidence refs. Validate structure without treating uncertain optional facts as globally invalid.
3. `ClaimConflict`: stable IDs, conflicting claim IDs and evidence references/type; deterministic detection; no automatic winner.
4. `SectionPlan`: section ID/title, required/optional claim IDs and evidence span IDs; template maps requirements to sections without inventing facts.
5. `SectionQualitySnapshot`: required/covered claims, unsupported high-risk values, relation/attribution issues, duplicate items and source-trace completeness. Candidate acceptance is non-regressive on all CORE dimensions.
6. `QualityPolicy` is model-independent. `ModelRuntimeProfile` is separate from policy. Runtime capability is detected from the active backend/loaded instance, not guessed from model-name substring.
7. Diagnostics add source raw/corrected metadata, structured extraction/schema status, ledger pre/post-consolidation, section planning/render/validation, patch/rollback, assembly/final validation/selection; tracked values are IDs, hashes, counts, safe profile metadata, status and verdict only.

## CHANGE_MAP_AND_WAVES

### W0 — Re-baseline / protect

Verify branch/HEAD/status, create a timestamped backup branch only if current HEAD is not already protected by a current-session backup, record current focused/full/docs baseline, current local runtime/model inventory without exposing sensitive paths, v1/v2 config conventions, PR state and frozen evaluator availability. Never overwrite existing safety branches. Inspect same evidence again only if HEAD changed.

### W1 — Fail-first contracts and data model

Add synthetic tests A–I before behavior changes, including causal direction, negation, condition, number relations, corrected-only guessed entity, unverified speaker mapping, overlap dedupe, patch coverage rollback, fabricated number rejection. Implement typed evidence/fact/conflict/section/snapshot models in repository-consistent modules; choose Pydantic version already installed. Include serialization/schema compatibility tests and privacy assertions.

### W2 — Structured local extraction and provenance

Preserve immutable raw transcript; make evidence spans from existing chunk/source boundaries; corrected view is advisory only. Detect native structured-output support from actual runtime capability; otherwise strict JSON parse/validation. Permit exactly one schema-only repair. Fail explicitly after second invalid result. Record schema status/hash/count diagnostics only. Cloud extraction unchanged.

### W3 — Deterministic ledger/consolidation

Normalize fingerprints; dedupe same evidence/fact and chunk overlap; preserve distinct supporting evidence refs; material same-evidence conflict becomes `ClaimConflict`. No LLM summary-of-summary as required fact contract. Keep legacy path behind explicit v1 selection.

### W4 — Section plan/render/assembly

Map existing `general`, `section_meeting`, `procurement`, speaker and action-item/template requirements into plans. Render one section from its allowed claim IDs and evidence only; assemble deterministically. Preserve output/template contract. CORE selected causal claim must render with original direction or the candidate is rejected. Keep cloud path and output semantics unchanged.

### W5 — Fidelity firewall

Audit the two experiment branches by mechanism and focused synthetic tests. Selectively adapt coverage, number/date, entity provenance, attribution/source-tag, glossary/term correction, and cross-section duplicate checks; do not import wholesale or create duplicate validator policy. Add cloud unchanged regression if any helper is shared. Separate detection from veto and keep optional uncertainty local.

### W6 — Targeted patch/rollback and pipeline flag

Replace default whole-record refinement only on V2 path with section-only patch. Compare old/candidate snapshots; accept only non-regressive candidate, else restore old bytes. Add explicit `v1|v2` configuration consistent with current config patterns; v1 remains default until acceptance. No silent fallback. Add stage diagnostics and safe metadata coverage.

### W7 — Runtime profiles and context

Add separate Qwen/Gemma controls only after inspecting backend/loaded model capabilities. Start from user-provided controls as candidates, not truth; verify accepted parameters and record explicit downgrade. Determine context from active loaded instance; use relevant evidence retrieval before increasing context. Quality policy cannot branch by family. No greedy temp=0 default.

### W8 — Verification, E2E, acceptance

Run focused synthetic suite and v4.7.4 regression set; full `pytest tests/ -q`, `bash scripts/check_docs.sh`, `git diff --check`. Run selected-claim end-to-end first and follow complete evidence chain. Then fresh Gemma and Qwen E2E. Run blind 3+3 with frozen rubric and original unrounded Gemini baseline; diagnostic outputs excluded. Show per-output/per-dimension minimum, median, worst, range and hard-fail count. If evaluator/baseline missing, preserve all implementation/E2E evidence and record exact scoped quality blocker. Add held-out different-template/meeting evidence only if an approved privacy-safe source exists; never use private data in tracked artifacts.

### W9 — Docs, audit, PR and delivery

Complete execution.md, architecture/operational docs and changelog if conventions require; privacy scan tracked diff; atomic commits; fetch/recheck before push; no force push; update existing Draft PR #19 with redacted evidence. Keep Draft if any required acceptance is pending/blocked/failing.

## VERIFICATION_AND_CLOSURE_MATRIX

Every item has independent goal criticality, evidence role and closure gate. No waiver is planned/allowed by this plan.

| CHECK_ID | GOAL_CRITICALITY | EVIDENCE_ROLE | CLOSURE_GATE | BASELINE_REQUIRED | FAILURE_CLASSIFICATION | WAIVER |
|---|---|---|---|---|---|---|
| C1 selected causal claim through source→facts→render→delivery | CORE | OUTCOME | HARD_CLEAN | NO | Any inversion/omission/conflict acceptance is CORE FAIL; test fixture defect separated | NO / NONE |
| C2 synthetic A–I and structured ledger/patch contract | CORE | OUTCOME | HARD_CLEAN | NO | Failure in changed contract is TASK_REGRESSION | NO / NONE |
| C3 cloud semantics/golden regression and v4.7.4 invariants | CORE | MUST_NOT_BREAK | HARD_CLEAN | YES | Changed behavior is TASK_REGRESSION; pre-existing failures need exact baseline evidence | NO / NONE |
| C4 privacy/tracked-artifact audit | CORE | MUST_NOT_BREAK | HARD_CLEAN | NO | Any private transcript/prompt/raw output/name/path in tracked/GitHub content is must-not-break violation | NO / NONE |
| C5 focused contract/integration checks | CORE | OUTCOME | HARD_CLEAN | NO | Changed-path failure is TASK_REGRESSION | NO / NONE |
| C6 full `pytest tests/ -q` | SUPPORTING | REPOSITORY_HEALTH | HARD_CLEAN | YES | Baseline failure remains repository debt; new/worsened relevant signature is TASK_REGRESSION | NO / NONE |
| C7 `bash scripts/check_docs.sh` | SUPPORTING | REPOSITORY_HEALTH | HARD_CLEAN | YES | Same baseline-vs-new rule; must finish clean per explicit DoD | NO / NONE |
| C8 `git diff --check` | SUPPORTING | REPOSITORY_HEALTH | HARD_CLEAN | NO | Current diff whitespace issue attributable to task | NO / NONE |
| C9 Gemma/Qwen fresh E2E | CORE | OUTCOME | HARD_CLEAN | NO | Any selected-claim failure or hidden fallback is FAIL; missing model/backend is scoped environment BLOCKED | NO / NONE |
| C10 blind 3+3 frozen rubric + zero major hard-fails | CORE | OUTCOME | HARD_CLEAN | NO | Per-model each-output each-dimension ≥ frozen Gemini median×0.80 and zero major failures; evaluator absence is scoped BLOCKED, not guessed | NO / NONE |
| C11 performance/runtime metrics | SUPPORTING | DIAGNOSTIC | NON_GATING | NO | Record observed overhead; explain material increase; does not veto fidelity result absent a correctness risk | NO / NONE |
| C12 held-out different meeting/template | SUPPORTING | DIAGNOSTIC | NON_GATING | NO | Run if privacy-safe source exists; otherwise disclose lack without blocking core acceptance | NO / NONE |
| C13 execution record, docs and PR #19 update | CORE | MUST_NOT_BREAK | HARD_CLEAN | NO | Missing durable redacted artifacts or wrong PR update leaves closure incomplete | NO / NONE |

## MIGRATION_COMPATIBILITY_ROLLBACK

- Additive code path only; no persistent transcript/fact schema migration. Runtime evidence objects live only for the task/request and optional ignored local cache.
- V1 stays selectable and default through development. Rollback means explicitly selecting V1; never automatic fallback on a bad V2 run.
- Keep cloud/local paths separate. Any shared change requires contract/golden evidence.
- Before each implementation wave, inspect status and current backup. Keep unrelated changes. Logical units are separate atomic commits. No reset, rebase of evidence commits, or force push.

## DEFERRED_OR_BEST_EFFORT

- Automatic entity disambiguation, role resolution, inferred dates, and any correction absent verified source/mapping: leave unknown/ambiguous.
- Enriching all possible template/domain vocabularies: only current production templates and proven needed safety mechanisms.
- Performance optimization beyond measuring significant cost; correctness first.
- Held-out data where no privacy-safe artifact is available.
- Any additional LLM-as-judge or wholesale experiment-branch port.

## RISKS_AND_UNKNOWNS

1. The latest post-repair source-first selected-claim adjudication is pending in prior execution record; current authoritative historical baseline remains valid, but no candidate is accepted yet.
2. LM Studio native JSON schema support may vary; strict JSON + validation is the prescribed compatibility path, not a blocker.
3. Existing fidelity validators may produce false positives for Chinese source tags, names, dates and number formatting; use synthetic boundary cases and keep uncertainty scoped.
4. Exact frozen rubric, evaluator protocol, and unrounded Gemini baselines have not yet been located from current task evidence; do not use rounded displayed medians for final decision.
5. A full multi-template renderer risks compatibility drift; map current template contracts and preserve deterministic assembly/output checks.

## BLOCKING_AND_NON_BLOCKING_UNKNOWNS

- Blocking to quality acceptance only: missing frozen evaluator or original unrounded baseline; record exact label `QUALITY_ACCEPTANCE_BLOCKED_BY_MISSING_FROZEN_EVALUATOR`. This does not block implementation, regression, or available local E2E.
- Environment-scoped acceptance blockers: requested model not loaded/available or hardware unavailable. Complete all unrelated work and preserve prior implementation/CORE evidence.
- Non-blocking: native structured-output support absent; use strict JSON validation. Optional glossary/registry item absent; degrade locally. Held-out data absent; state limitation.

## DEFINITION_OF_DONE

Architecture implementation is complete only when: fact ledger with provenance replaces Markdown as V2's core contract; causal/conditional/negation/numeric/date/attribution facts are represented; deterministic consolidation and explicit conflicts work; section-by-section render/assembly is live; firewall is connected; raw/corrected source roles are explicit; targeted patch is guarded and rollback demonstrated; Qwen/Gemma profiles are separate from model-independent quality rules; diagnostics are expanded; V1 rollback remains available; cloud/v4.7.4/privacy invariants hold.

Task closure additionally requires: selected causal claim correct end-to-end; focused and full tests/docs pass; fresh Gemma and Qwen E2E pass; fresh blind 3+3 meets every per-output/per-dimension 80% gate against original unrounded baseline with zero adjudicated major fidelity hard fails; privacy audit passes; execution.md complete; Draft PR #19 updated. If the frozen evaluator/baseline cannot be found, report the exact scoped blocker and keep task closure pending while preserving completed implementation evidence.

## HANDOFF_HINTS

- Revision 1's first-divergence result and attempts are evidence; do not repeat the failed “put more transcript in final prompt” hypothesis.
- Do not implement until this revision's independent review gate is `PLAN_APPROVED`, then regenerate Handoff and use a fresh Stage 04 context.
- The review must specifically challenge veto scope, schema-failure behavior, test gate baselines, template coverage complexity, and whether experiment mechanisms are selected rather than copied.
- Execution/reporting uses orthogonal status fields from workflow-routing v2. `DONE` is only overall closure; missing blind evaluator preserves implementation/CORE facts and produces pending required/independent acceptance.
