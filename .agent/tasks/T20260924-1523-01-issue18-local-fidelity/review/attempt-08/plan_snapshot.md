# Issue #18 Local Meeting Record Architecture V2 — Plan Revision 9

## META

- TASK_ID: T20260924-1523-01-issue18-local-fidelity
- ISSUE: #18; continue Draft PR #19
- STATUS: READY_FOR_REVIEW
- TASK_MODE: ESCALATION_REPLAN
- PLAN_REVISION: 9
- TASK_CLASS: CRITICAL
- REVIEW_REQUIRED: YES
- INDEPENDENT_ACCEPTANCE_REQUIRED: YES
- E2E_REQUIRED: YES
- ACCEPTANCE_MODE: CONTRACT + INTEGRATION + E2E + BLIND_RUBRIC
- BASE_BRANCH: main
- IMPLEMENTATION_BRANCH: issue-18-first-divergence-diagnostic
- ANCHOR_HEAD: eb3ca049cc72d21d2f4db974db5314b5f399d736
- PR: #19, open and Draft
- WORKTREE_AT_REPLAN: dirty; contains the uncommitted Stage 04 V2 candidate (backend/core/config.py, backend/services/summarization.py, backend/services/local_pipeline_v2.py, tests/test_local_pipeline_v2.py, and doc/規格與設計/local-meeting-record-v2.md) plus task plan, handoff, execution, baseline, escalation, review, and E2E artifacts. These are expected task/Stage04 paths, not a clean baseline. No unrelated owner change has been classified from current evidence; Stage04 must inventory and classify every current path before mutation and stop/escalate if any path remains unclassified.
- WORKTREE_STATUS_SNAPSHOT: Stage04 W0 must persist a timestamped, redacted `git status --short`/path-classification snapshot, current HEAD, and relation to the two listed safety branches before product mutation. Stage01 does not create that Stage04-owned artifact. Preserve all paths; never reset, stash, clean, or overwrite unexplained work.
- SAFETY_BRANCHES_PRESENT: backup/issue-18-before-gpt6-20260924-074037; backup/issue-18-before-gpt6-20260924-153522
- AUTHORITATIVE_GOAL: user-provided Local Meeting Record Architecture V2 attachment, read 2026-09-24
- SUPERSEDES: revision 1's “smallest evidence-branch repair / do not redesign” scope. Revision 1 execution evidence is retained and remains authoritative where not changed below.

## ESCALATION_REPLAN_EVIDENCE

- Stage 05 attempt 01 is bound to revision 4 and reports `CORE_ACCEPTANCE_STATUS: FAIL`, `IMPLEMENTATION_STATUS: ESCALATED`, `TASK_CLOSURE_STATUS: REPLAN_REQUIRED`; report `.agent/tasks/T20260924-1523-01-issue18-local-fidelity/e2e/attempt-01/e2e_report.md`, SHA-256 `d83a6197756894b5bb294cf31ff322a3ea085c6261751c32ed8409d7ba8c2d99`.
- Decisive fact: current `fidelity_firewall` accepts a changed causal predicate; relation checks are unreachable because they require `claim_id in rendered`, while renderer output has no claim ID. The live path also omits `selected_claim_id`. The independent inversion probe falsifies the C1 gate; a synthetic Qwen run alone does not prove source relation correctness.
- Additional gaps: live extraction does not request the full typed high-risk fields; template-required coverage and section mapping are not wired; number/date/entity/attribution/source-tag checks are absent or ineffective; duplicate checking is intra-section text-only; candidate profile A/B controls are not live. Latest runtime probe showed Qwen loaded and Gemma listed but not loaded (`LMSTUDIO_MODEL_NOT_LOADED`).
- This revision retains the approved fidelity goal and narrows the correction: source alignment must inspect structured claim metadata and raw evidence, section rendering must actually be one LLM call per planned section, and acceptance must exercise live boundaries. No issue-specific claim/timestamp may be hard-coded.

## OWNER_CHECK

- **Primary goal:** make the local Gemma 4 31B and Qwen 3.8 27B pipeline preserve source facts through an evidence-grounded, structured, deterministically checked process, and bring every fresh blind output to at least 80% of the frozen Gemini median in every rubric dimension with zero major fidelity hard fails.
- **Essential:** structured facts with source provenance; deterministic consolidation; section-scoped generation; source-backed fidelity checks; non-regressive targeted repair; local E2E and blind acceptance.
- **Essential:** model runtime profile wiring/capability validation and repeated candidate-profile sampling are required to execute and close the user's controlled, reproducible quality-selection obligation. Profile/model/evaluator unavailability can block the scoped E2E or independent acceptance and therefore task closure, but never vetoes an unrelated valid record or section.
- **Supporting:** performance diagnostics, broader held-out examples, and selected reusable mechanisms from prior experiments. These improve operational understanding but cannot veto unrelated valid sections or task closure absent a demonstrated correctness risk.
- **Best effort/deferred:** richer transcript correction and glossary enrichment where no verified mapping exists; they must remain explicitly uncertain and may not become source truth.
- **What can stop an individual record:** failure to obtain a schema-valid CORE fact set after one schema-only repair attempt, or an unresolved selected-claim causal-direction failure. These make the record's core source fidelity untrustworthy. Optional enrichment or one unsupported non-core field must be contained locally and cannot globally veto the record.
- **Biggest risk:** Stage 05 proved the initial firewall misses a causal predicate flip at the acceptance boundary; another helper-only test pass must not masquerade as live correctness. The frozen unrounded evaluator is also missing, and Gemma is listed but not loaded. Architecture work continues; those quality/runtime gates remain scoped pending/blocked unless evidence is obtained.

## GOAL_CONTRACT

- PRIMARY_OUTCOME: an operational local V2 meeting-record path that preserves the source as immutable truth, carries structured claims and evidence references, catches or contains major fidelity errors, and produces fresh Gemma/Qwen outputs satisfying the frozen blind quality gate.
- SUCCESS_EVIDENCE: selected claim `C-R03-F056-CAUSAL-DIRECTION` is correct from source through structured extraction, ledger, rendering, and final delivery; regression suite covers the specified failure classes; full repository and docs checks pass; fresh local E2E and blind 3+3 cohort meet every per-output/per-dimension threshold with zero adjudicated major fidelity hard fails; privacy audit and PR update are recorded.
- MUST_NOT_BREAK: cloud output semantics; v4.7.4 no-hard-truncation, fail-loud merge, loaded LM Studio instance as context authority, thinking-disable compatibility, immutable per-task model selection, retry safety, explicit degradation; templates/record output contract; privacy and provenance; existing deterministic post-processing.
- NON_GOALS: direct merge of either experimental branch; hard-coded Issue #18 claims/timestamps; model-family-specific definitions of fidelity; production transcript/raw prompt/raw output retention; a second LLM judge as truth oracle; lowering the frozen gate; broad ASR or unrelated UI rework.
- CRITICAL_PATH: evidence/schema types → structured extraction with validated provenance → deterministic ledger consolidation/conflicts → source-alignment firewall that rejects Stage05 causal inversion → template section planning/LLM rendering/deterministic assembly → targeted patch with rollback → local E2E → blind cohort.

## SOURCE_OF_TRUTH_AND_BASELINE

- Raw transcript is the sole immutable source of truth. Corrected transcript is a comprehension view only. Ledger, evidence spans, notes, and records are derived data.
- Existing `claim-attempt-3-baseline.json` verifies source and chunk 3 input as correct, first divergence at `extraction.chunk.3.raw`, downstream consolidation/final delivery missing the claim. Existing post-repair attempts document that prompt-only/source-in-final recovery did not recover it. Do not re-diagnose this result or treat those candidates as accepted.
- Stage 05 attempt 01's synthetic causal-inversion probe returned `accepted=True` with no relation issue despite a different predicate in rendered text; this is a confirmed V2 firewall integration defect, not a reinterpretation of the historical first divergence.
- Current branch head is `eb3ca049cc72d21d2f4db974db5314b5f399d736`; PR #19 is open Draft. At this replan the worktree is dirty with the Stage04 candidate and task artifacts listed in META; this is not a clean baseline. No unrelated owner change is established, but Stage04 must not assume that means none exists: W0 records a timestamped redacted status/path classification and stops if any path is unclassified.
- Current call path is `SummarizationService._summarize_with_local_pipeline`: free-text chunk extraction → note consolidation/optional LLM merge → whole-record generation → whole-record validation against notes → full-record refinement. Cloud has separate transcript-aware builders and must remain behaviorally unchanged.
- Experimental branches are read-only evidence libraries. Initial inspection found candidate coverage/fidelity, glossary/term, source-tag, number/date/entity/attribution, dedupe, and refinement rollback mechanisms; each must be isolated, checked against the present repository contract, and ported only where a concrete acceptance obligation is served.

## REQUIREMENTS_AND_CRITICALITY

| ID | Requirement | Class | Decision contribution / failure behavior |
|---|---|---|---|
| R1 | Runtime evidence spans with immutable raw text, optional corrected view, source hash and stable span identity; raw content stays in ignored local runtime storage | CORE | Provenance is necessary to establish the source for every rendered claim. Missing span for an optional claim degrades that claim; missing evidence for the selected/core claim blocks acceptance. |
| R2 | Typed FactClaim/FactLedger including relation direction, condition/dependency, polarity/negation, number/unit, date, attribution/uncertainty, and evidence refs | CORE | Prevents natural-language-only contracts and makes hard-fail classes observable. Unknown/ambiguous is a valid value, not schema failure. |
| R3 | Strict structured extraction, native schema capability when supported, strict JSON+Pydantic otherwise, exactly one schema-only repair, then explicit failure | CORE | Invalid core ledger cannot safely feed rendering; never silently accept or masquerade fallback as V2 success. |
| R4 | Deterministic dedupe by normalized claim/evidence identity and overlap; detect same-evidence conflicts without choosing a winner | CORE | Prevents duplicate and contradictory facts from being silently propagated; conflicts stay explicit/locally unresolved. |
| R5 | Template-derived section plan and LLM render of one section at a time from allowed claims plus resolved evidence; deterministic assembler | CORE | Limits unsupported content and isolates failures to relevant sections. Cloud generation remains untouched. |
| R6 | Live source-alignment firewall for every required relation/number/date/attribution claim; selected CORE causal direction is checked against ordered raw evidence and rendered relation metadata. Include scoped number/date/entity/attribution/source-tag/coverage/duplicate checks and selected template-scoped corrections | CORE | Detects high-risk mismatches at source→claim and claim→render boundaries. Unknown/ambiguous stays explicit. Predicate flip/negation/condition loss or missing selected claim rejects candidate. No check may silently skip because claim ID is absent from rendered prose. |
| R7 | Targeted section patch with before/after quality snapshot and rollback; never default full-document rewrite | CORE | Prevents fixing one issue from silently damaging other sections. Reject if required claim coverage falls or unsupported high-risk facts increase. |
| R8 | Separate model-independent QualityPolicy from runtime profiles/capability detection for Qwen/Gemma; evaluate explicit initial Qwen/Gemma controls and Qwen extraction-temperature A/B candidates with repeated runs | CORE for controlled acceptance/task closure; not an individual-record gate | Profile stability is required for reproducible quality. Capability-invalid parameters are explicitly reported; unsupported controls cannot be counted as a valid candidate sample. Unavailable runtime blocks only the affected E2E/profile acceptance, not unrelated valid records. No model-specific fidelity criteria. |
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
| Runtime profile wiring and capability validation | Enables the user's controlled Qwen/Gemma execution path and reproducible comparisons | CORE for acceptance/task closure; not an individual-record gate | N/A | No per-record veto | Unsupported/unavailable controls are explicitly reported; affected E2E/profile acceptance is scoped BLOCKED or downgraded only where the planned candidate remains valid. Do not invalidate unrelated records. |
| Repeated candidate-profile sampling and selection | Establishes run-to-run stability and selects the requested candidate settings | CORE closure evidence | N/A | No per-record veto | Complete W7/C14 samples and report median/worst/range/hard-fail count; unavailable evaluator/model/hardware blocks only the applicable independent/E2E acceptance and task closure, never an unrelated record. |
| Blind evaluator and frozen baseline | Proves external quality target | CORE acceptance | N/A | Blocks quality/task closure, not implementation progress | If genuinely missing, report `QUALITY_ACCEPTANCE_BLOCKED_BY_MISSING_FROZEN_EVALUATOR`; finish all other work. |
| Full repository/docs checks | Regressions/repo health | SUPPORTING outcome evidence; required closure check | N/A | HARD_CLEAN closure gate by user DoD | Report scoped check failure; do not call it product CORE failure unless task regression evidence shows it. |

## SEMANTIC_CONTRACT_AND_FAILURE_CONTAINMENT

- V2 is additive and opt-in behind a repository-conventional local pipeline selector (exact key to be selected after config inspection); default remains v1 until architecture and acceptance pass. No data migration is planned.
- V2 schema failure after one repair is explicit failure for that V2 run. It cannot be converted to a successful V1 result invisibly. Operator can explicitly choose V1 for rollback.
- Evidence absence/conflict is scoped to affected claim/section except required CORE claims and their acceptance. Every required causal/conditional claim is checked independent of whether its opaque claim ID is included in prose. Optional categories do not gate unrelated sections.
- A failed targeted patch is rolled back byte-for-byte to the last accepted section. No semantic validator failure is “fixed” by weakening policy.
- Cloud path and shared semantics are frozen; any unavoidable shared helper change requires a cloud golden/contract regression demonstrating unchanged behavior.

## TARGET_CONTRACT

1. `EvidenceSpan`: stable span ID, optional offsets/speaker key, raw text, optional corrected text, source SHA-256. Full text is runtime/local-cache only and gitignored.
2. `FactClaim`/`FactLedger`: normalized typed claims, explicit status/uncertainty, explicit subject-predicate-object and polarity; relation type includes causal/conditional/temporal; numeric/date/attribution fields; one or more evidence refs. Validate structure without treating uncertain optional facts as globally invalid.
3. `ClaimConflict`: stable IDs, conflicting claim IDs and evidence references/type; deterministic detection; no automatic winner.
4. `SectionPlan`: section ID/title, required/optional claim IDs and evidence span IDs; derive requirements from each existing production template, render only that section with allowed claim IDs plus resolved spans, and assemble in template order.
5. `SectionQualitySnapshot`: required/covered claims, unsupported high-risk values, relation/attribution issues, duplicate claim IDs and source-trace completeness. Compare structured expected relation (subject/predicate/object/polarity/condition) with raw evidence ordering and rendered relation metadata; do not test opaque claim-ID substring membership in prose. Candidate acceptance is non-regressive on all CORE dimensions.
6. `QualityPolicy` is model-independent. `ModelRuntimeProfile` is separate from policy. Runtime capability is detected from the active backend/loaded instance, not guessed from model-name substring.
7. Diagnostics add source raw/corrected metadata, structured extraction/schema status, ledger pre/post-consolidation, section planning/render/validation, patch/rollback, assembly/final validation/selection; tracked values are IDs, hashes, counts, safe profile metadata, status and verdict only.

## CHANGE_MAP_AND_WAVES

### W0 — Re-baseline / protect

Before any mutation, persist a timestamped, redacted `git status --short` and path classification in the task baseline area, separating the known Stage04 candidate paths and task evidence from any owner/unclassified changes; include current HEAD and whether it is protected by the listed backup branches. Preserve all paths. Stop/escalate before mutation if any path cannot be classified; do not reset, stash, clean, or overwrite. Then verify branch/HEAD/status, create a timestamped backup branch only if current HEAD is not already protected by a current-session backup, record current focused/full/docs baseline, current local runtime/model inventory without exposing sensitive paths, v1/v2 config conventions, PR state and frozen evaluator availability. Before any product mutation, establish the cloud behavior baseline using `uv run pytest -q tests/test_summarization_service.py -k "cloud_pipeline or cloud_generation or validate_cloud or cloud_finalize or gemini_chat"`; preserve the exact command, exit status, test count and redacted output in `.agent/tasks/T20260924-1523-01-issue18-local-fidelity/baseline/cloud-contract-focused.txt`. Rerun the same command after changes. Existing contract coverage includes `test_cloud_pipeline_chunked_extraction_and_transcript_in_generation`, `test_cloud_pipeline_single_pass_extraction_by_default`, `test_cloud_pipeline_refines_when_summary_below_dynamic_floor`, `test_cloud_generation_message_requires_speaker_traceability`, cloud speaker/date validation and finalization cases, and Gemini transient/non-transient retry behavior. If any shared helper changes, add a synthetic byte-level golden request/message fixture for that affected boundary and record its hash alongside the focused baseline. If the baseline command cannot run or has no selected tests, mark C3 `BLOCKED` before mutation and do not infer cloud preservation. Never overwrite existing safety branches. Inspect same evidence again only if HEAD changed.

### W1 — Fail-first contracts and data model

Add synthetic tests A–I before behavior changes, including causal direction, negation, condition, number relations, corrected-only guessed entity, unverified speaker mapping, overlap dedupe, patch coverage rollback, fabricated number rejection. Add live-boundary cases that exercise extraction schema→source alignment→section rendering→firewall; helper-only object construction is insufficient. One regression must feed the Stage05 inverted predicate and prove rejection before repair. Implement typed evidence/fact/conflict/section/snapshot models in repository-consistent modules; choose installed Pydantic version. Include schema compatibility/privacy assertions.

### W2 — Structured local extraction and provenance

Preserve immutable raw transcript; make evidence spans from existing chunk/source boundaries; corrected view is advisory only. Structured prompt/schema requests subject, predicate, object, relation kind/direction, polarity/negation, condition/dependency, number/unit, date, attribution, uncertainty/status and evidence refs (explicit null/unknown where unsupported). Detect native structured-output support from actual runtime capability; otherwise strict JSON parse/validation. Permit exactly one schema-only repair. Fail explicitly after second invalid result. Validate asserted claim fields against raw evidence before they become required/asserted; corrected-only guessed entity or unverified speaker mapping stays uncertain. Record schema status/hash/count only. Cloud extraction unchanged.

### W3 — Deterministic ledger/consolidation

Normalize fingerprints; dedupe same evidence/fact and chunk overlap; preserve distinct supporting evidence refs; material same-evidence conflict becomes `ClaimConflict`. No LLM summary-of-summary as required fact contract. Keep legacy path behind explicit v1 selection.

### W4 — Section plan/render/assembly

Map existing `general`, `section_meeting`, `procurement`, speaker and action-item/template requirements into plans. Render each section with a separate model call from its allowed claim IDs and only resolved corresponding spans; do not duplicate the whole transcript/ledger into every section prompt. Keep claim/evidence identity outside user prose available to the validator and retain relation metadata in a validated intermediate render contract. Assemble deterministically in template order. Preserve output/template contract. Every required causal claim must render with source-supported direction or candidate is rejected. Keep cloud path and output semantics unchanged.

### W5 — Fidelity firewall

Audit the two experiment branches by mechanism and focused synthetic tests. Stage05 attempt 01 and the read-only mechanism audit show helper/schema presence is not live wiring. Wire and test: (a) source-derived numeric/date candidates and coverage, (b) entity provenance against raw source/verified mapping, (c) attribution against verified speaker/span provenance, (d) source-tag↔span validation with conservative boundaries, (e) claim-ID cross-section dedupe, and (f) template-scoped record-term/glossary correction at finalization. Reuse focused mechanisms only; avoid global substitutions, arbitrary text dedupe, unbounded similarity, or an unproven veto. Compare high-risk fields to referenced raw source, not notes/final agreement. Any shared helper edit requires cloud unchanged regression. Separate detection from veto and keep optional uncertainty local.

### W6 — Targeted patch/rollback and pipeline flag

Replace default whole-record refinement only on V2 path with section-only patch. Compare old/candidate snapshots; accept only non-regressive candidate, else restore old bytes. Wire required-claim identity into the live gate; compare required causal/conditional relations against ordered raw evidence and rendered relation metadata before final selection. Add explicit `v1|v2` configuration; v1 remains default until acceptance. No silent fallback. Emit source/schema/ledger/section/validation/patch/rollback/assembly diagnostics; tracked metadata only.

### W7 — Runtime profiles and context

Add separate Qwen/Gemma controls only after inspecting backend/loaded model capabilities. This wiring and candidate comparison is required for CORE acceptance/task closure, not for accepting an unrelated record. Treat these as starting candidates, not presumed truths: Qwen production baseline `thinking=OFF, temperature=0.7, top_p=0.8, top_k=20`; Qwen extraction A/B temperatures `0.3, 0.5, 0.7` with all other conditions fixed; Gemma independent baseline `thinking=OFF, temperature=1.0, top_p=0.95, top_k=64`. Verify accepted parameters from the active runtime and record explicit unsupported-setting diagnostics; an unsupported control is not a valid candidate sample and may not be silently counted as matching the requested profile. If model/runtime is unavailable, set the affected C9/C14 `CHECK_RESULT: BLOCKED` with `ENVIRONMENT` scope; do not count it as a failure or pass. If frozen evaluator/rubric/original unrounded baseline is unavailable, set affected C10/C14 `CHECK_RESULT: BLOCKED` with `AUTHORITY` scope and the exact quality blocker label; do not substitute rounded baselines or self-waive. C9/C10/C14 are CORE acceptance inputs as well as required HARD_CLEAN verification items; they are not per-record gates. When Stage04 discovers any of these blocked, preserve implementation/other CORE results, set aggregate `CORE_ACCEPTANCE_STATUS: BLOCKED`, set `REQUIRED_VERIFICATION_STATUS: INCOMPLETE` if other required checks have valid evidence (otherwise `BLOCKED` only if the verification phase as a whole cannot reach a valid conclusion), keep `INDEPENDENT_ACCEPTANCE_STATUS: PENDING`, and route `TASK_CLOSURE_STATUS: CORE_ACCEPTANCE_BLOCKED` per v4.2 precedence. If the relevant core acceptance items are merely not yet run and no blocker is known, use `CORE_ACCEPTANCE_STATUS: NOT_RUN` and `TASK_CLOSURE_STATUS: PENDING_CORE_ACCEPTANCE`. If Stage05 cannot obtain valid quality/E2E acceptance due the same scoped authority/environment blocker, record the affected item as `CHECK_RESULT: BLOCKED` but preserve the Stage04 current `IMPLEMENTATION_STATUS`, `CORE_ACCEPTANCE_STATUS`, and `REQUIRED_VERIFICATION_STATUS` exactly, in addition to retaining the immutable snapshot. Set Stage05 `INDEPENDENT_ACCEPTANCE_STATUS: BLOCKED` and `TASK_CLOSURE_STATUS: ACCEPTANCE_BLOCKED`; do not overwrite a Stage04 CORE value of `PASS`, `BLOCKED`, or `NOT_RUN` solely because Stage05 acceptance could not run. No implementation status is downgraded or blocked solely by these acceptance prerequisites; continue unrelated work. For each candidate profile, run N≥5 when practical; N=3 is the minimum when measured time/hardware cost is excessive, with that limitation recorded. Compare median, worst case, range and hard-fail count. Select by priority: (1) major fidelity hard fails, (2) causal correctness, (3) attribution correctness, (4) faithfulness, (5) traceability, (6) completeness, (7) usability. Keep diagnostic runs separate from the fresh blind cohort. Determine context from active loaded instance; retrieve relevant evidence before increasing context. Quality policy cannot branch by family. Never use temperature 0 as production default.

### W8 — Verification, E2E, acceptance

Run focused synthetic suite with live-boundary regressions and v4.7.4 set; full `uv run pytest tests/ -q`, `bash scripts/check_docs.sh`, `git diff --check`. First reproduce/reject the exact Stage05 C1 predicate inversion through the live gate, then run selected-claim E2E through source→structured extraction→ledger→section render→delivery. Helper-only A–I tests do not prove C1. Then fresh Gemma and Qwen E2E. Complete C14 repeated candidate-profile sampling before final profile selection; report sample counts and median/worst/range/hard-fail count. C9/C10/C14 are CORE acceptance inputs and required HARD_CLEAN verification items, but never per-record gates. For every missing evaluator/rubric/original unrounded baseline or unavailable model/hardware, record the affected item as `CHECK_RESULT: BLOCKED` with `AUTHORITY` or `ENVIRONMENT` scope respectively; preserve implementation/other CORE facts, and never substitute rounded baselines or self-waive. If Stage04 discovers such a blocker, set `CORE_ACCEPTANCE_STATUS: BLOCKED`; with other required evidence, `REQUIRED_VERIFICATION_STATUS: INCOMPLETE`; `INDEPENDENT_ACCEPTANCE_STATUS: PENDING`; `TASK_CLOSURE_STATUS: CORE_ACCEPTANCE_BLOCKED`. If these inputs are merely not yet run and no blocker is known, CORE acceptance is `NOT_RUN` and closure is `PENDING_CORE_ACCEPTANCE`. If Stage05 cannot obtain valid acceptance due the blocker, record any new item result as `CHECK_RESULT: BLOCKED` but preserve the Stage04 reported/current `IMPLEMENTATION_STATUS`, `CORE_ACCEPTANCE_STATUS`, and `REQUIRED_VERIFICATION_STATUS` exactly, as well as the immutable snapshot. Set Stage05 `INDEPENDENT_ACCEPTANCE_STATUS: BLOCKED` and `TASK_CLOSURE_STATUS: ACCEPTANCE_BLOCKED`; do not change a Stage04 CORE value of `PASS`, `BLOCKED`, or `NOT_RUN` solely because Stage05 could not conclude. The current closure follows the first applicable v4.2 routing rule; do not use `PENDING_REQUIRED_VERIFICATION` when a CORE acceptance blocker is already recorded in Stage04. Separately run blind 3+3 with frozen rubric and original unrounded Gemini baseline; diagnostic/profile-selection runs are excluded. Show per-output/per-dimension minimum, median, worst, range and hard-fail count. Held-out different-template/meeting evidence only if an approved privacy-safe source exists.

### W9 — Docs, audit, PR and delivery

Complete execution.md, architecture/operational docs and changelog if conventions require; privacy scan tracked diff; atomic commits; fetch/recheck before push; no force push; update existing Draft PR #19 with redacted evidence. Keep Draft if any required acceptance is pending/blocked/failing.

## VERIFICATION_AND_CLOSURE_MATRIX

Every item has independent goal criticality, evidence role and closure gate. No waiver is planned/allowed by this plan.

| CHECK_ID | GOAL_CRITICALITY | EVIDENCE_ROLE | CLOSURE_GATE | BASELINE_REQUIRED | FAILURE_CLASSIFICATION_RULE | WAIVER_ALLOWED | WAIVER_AUTHORITY | CHECK_RESULT | WAIVER_STATUS |
|---|---|---|---|---|---|---|---|---|---|
| C1 selected causal claim source→facts→render→delivery, including Stage05 inversion probe at live gate | CORE | OUTCOME | HARD_CLEAN | NO | Required relation checks compare source direction and rendered relation metadata; inversion/omission is CORE acceptance FAIL and requires repair/replan by workflow-routing v2 without retroactively erasing prior implementation evidence | NO | NONE | NOT_RUN | NOT_ALLOWED |
| C2 synthetic A–I plus extraction→schema→source alignment→template section render→firewall integration contracts | CORE | OUTCOME | HARD_CLEAN | NO | Changed contract failure or primitive/live mismatch is TASK_REGRESSION | NO | NONE | NOT_RUN | NOT_ALLOWED |
| C3 cloud semantics/golden regression and v4.7.4 invariants | CORE | MUST_NOT_BREAK | HARD_CLEAN | YES | Compare exact focused contract baseline before/after; changed behavior is TASK_REGRESSION; pre-existing failure requires exact signature evidence | NO | NONE | NOT_RUN | NOT_ALLOWED |
| C4 privacy/tracked-artifact audit | CORE | MUST_NOT_BREAK | HARD_CLEAN | NO | Any private transcript/prompt/raw output/name/path in tracked/GitHub content is must-not-break violation | NO | NONE | NOT_RUN | NOT_ALLOWED |
| C5 focused contract/integration checks | CORE | OUTCOME | HARD_CLEAN | NO | Changed-path failure is TASK_REGRESSION | NO | NONE | NOT_RUN | NOT_ALLOWED |
| C6 full `uv run pytest tests/ -q` | SUPPORTING | REPOSITORY_HEALTH | HARD_CLEAN | YES | Baseline failure remains debt; new/worsened relevant signature is TASK_REGRESSION | NO | NONE | NOT_RUN | NOT_ALLOWED |
| C7 `bash scripts/check_docs.sh` | SUPPORTING | REPOSITORY_HEALTH | HARD_CLEAN | YES | Same baseline-vs-new rule; must finish clean per explicit DoD | NO | NONE | NOT_RUN | NOT_ALLOWED |
| C8 `git diff --check` | SUPPORTING | REPOSITORY_HEALTH | HARD_CLEAN | NO | Current diff whitespace issue attributable to task | NO | NONE | NOT_RUN | NOT_ALLOWED |
| C9 Gemma/Qwen fresh E2E | CORE | OUTCOME | HARD_CLEAN | NO | CORE acceptance input and required verification item, not a per-record gate. Selected-claim failure or hidden fallback is FAIL; model/hardware unavailable after safe load/availability check is `CHECK_RESULT: BLOCKED` (`ENVIRONMENT`). Stage04 maps a known blocker to `CORE_ACCEPTANCE_STATUS: BLOCKED`, verification `INCOMPLETE` when other required evidence exists (otherwise phase `BLOCKED` only if no valid conclusion), independent acceptance `PENDING`, closure `CORE_ACCEPTANCE_BLOCKED`. At Stage05, record any new item-level blocker without changing Stage04 implementation/core/verification values; set independent acceptance `BLOCKED`, preserve the immutable snapshot, closure `ACCEPTANCE_BLOCKED` | NO | NONE | NOT_RUN | NOT_ALLOWED |
| C10 blind 3+3 frozen rubric + zero major hard-fails | CORE | OUTCOME | HARD_CLEAN | YES | CORE acceptance input and required verification item, not a per-record gate. Per-model every output/dimension ≥ frozen Gemini median×0.80 and zero major failures; missing evaluator/rubric/original unrounded baseline is `CHECK_RESULT: BLOCKED` (`AUTHORITY`) with `QUALITY_ACCEPTANCE_BLOCKED_BY_MISSING_FROZEN_EVALUATOR`, never a guessed PASS/FAIL or waiver. Stage04 maps a known blocker to core acceptance `BLOCKED`, verification `INCOMPLETE` when other required evidence exists (otherwise phase `BLOCKED` only if no valid conclusion), independent acceptance `PENDING`, closure `CORE_ACCEPTANCE_BLOCKED`. At Stage05, record any new item-level blocker without changing Stage04 implementation/core/verification values; set independent acceptance `BLOCKED`, preserve the immutable snapshot, closure `ACCEPTANCE_BLOCKED` | NO | NONE | NOT_RUN | NOT_ALLOWED |
| C11 performance/runtime metrics | SUPPORTING | DIAGNOSTIC | NON_GATING | NO | Record overhead and explain material increase; cannot veto absent correctness risk | NO | NONE | NOT_RUN | NOT_ALLOWED |
| C12 held-out different meeting/template | SUPPORTING | DIAGNOSTIC | NON_GATING | NO | Run only if privacy-safe source exists; absence is disclosed and non-gating | NO | NONE | NOT_RUN | NOT_ALLOWED |
| C13 execution record, docs and PR #19 update | CORE | MUST_NOT_BREAK | HARD_CLEAN | NO | Missing durable redacted artifacts or wrong PR update leaves closure incomplete | NO | NONE | NOT_RUN | NOT_ALLOWED |
| C14 repeated candidate-profile sampling and selection | CORE | OUTCOME | HARD_CLEAN | YES | CORE acceptance input and required verification item, not a per-record gate. Live runtime exposes/validates candidate settings; per candidate N≥5 preferred/N=3 minimum with limitation; compare median/worst/range/hard-fail count and select by W7 priorities. Missing evaluator/rubric/original unrounded baseline is `CHECK_RESULT: BLOCKED` (`AUTHORITY`) with `QUALITY_ACCEPTANCE_BLOCKED_BY_MISSING_FROZEN_EVALUATOR`; unavailable model/hardware is `CHECK_RESULT: BLOCKED` (`ENVIRONMENT`). Stage04 maps a known blocker to core acceptance `BLOCKED`, verification `INCOMPLETE` when other required evidence exists (otherwise phase `BLOCKED` only if no valid conclusion), independent acceptance `PENDING`, closure `CORE_ACCEPTANCE_BLOCKED`. At Stage05, record any new item-level blocker without changing Stage04 implementation/core/verification values; set independent acceptance `BLOCKED`, preserve the immutable snapshot, closure `ACCEPTANCE_BLOCKED` | NO | NONE | NOT_RUN | NOT_ALLOWED |

### C9/C10/C14 STATUS AGGREGATION — CANONICAL

These three system-level outcome checks contribute to both `CORE_ACCEPTANCE_STATUS` and the required-verification matrix; their CORE classification is not a per-record/section veto. Apply v4.2 precedence without conflating the status subjects:

| Situation | PRIMARY_OUTCOME_STATUS | IMPLEMENTATION_STATUS | CORE_ACCEPTANCE_STATUS | REQUIRED_VERIFICATION_STATUS | INDEPENDENT_ACCEPTANCE_STATUS | TASK_CLOSURE_STATUS |
|---|---|---|---|---|---|---|
| Stage04 implementation complete; C9/C10/C14 not run yet; no known blocker | UNKNOWN | COMPLETE | NOT_RUN | INCOMPLETE when other required evidence exists; otherwise NOT_RUN | PENDING | PENDING_CORE_ACCEPTANCE |
| Stage04 implementation complete; any C9/C10/C14 blocked by AUTHORITY/ENVIRONMENT; other required checks have valid evidence | UNKNOWN | COMPLETE | BLOCKED | INCOMPLETE | PENDING | CORE_ACCEPTANCE_BLOCKED |
| Stage04 implementation complete; blocked C9/C10/C14 and the required-verification phase as a whole cannot obtain any valid conclusion | UNKNOWN | COMPLETE | BLOCKED | BLOCKED | PENDING | CORE_ACCEPTANCE_BLOCKED |
| Stage05 cannot obtain valid C9/C10/C14 acceptance because scoped blocker persists | preserve Stage04 value unless new valid outcome evidence changes it | preserve Stage04 value | preserve Stage04 value exactly, including `NOT_RUN`, `BLOCKED`, or `PASS` | preserve Stage04 value exactly | BLOCKED | ACCEPTANCE_BLOCKED |

If Stage04 product implementation itself is still in progress, obey the earlier v4.2 Stage04 precedence for implementation state/closure; do not label implementation blocked merely because an acceptance dependency is unavailable. A completed C9/C10/C14 item may be `PASS` or `FAIL` only on valid evidence. Missing inputs stay `CHECK_RESULT: BLOCKED`, with blocker scope `AUTHORITY` or `ENVIRONMENT`, and cannot be self-waived. At Stage05, §7.8 preservation applies to the current aggregate status fields as well as the immutable snapshot: a new item-level blocker does not rewrite an existing Stage04 `CORE_ACCEPTANCE_STATUS` of `PASS`, `BLOCKED`, or `NOT_RUN`; Stage05 sets its own `INDEPENDENT_ACCEPTANCE_STATUS: BLOCKED` and `TASK_CLOSURE_STATUS: ACCEPTANCE_BLOCKED` while preserving Stage04 implementation/core/required-verification values. The table does not replace each item's result or the immutable Stage04 snapshot required by Stage05.

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

1. Stage05 attempt 01 conclusively found the current V2 firewall accepts a causal predicate inversion; do not treat the implementation candidate as accepted. Re-run the exact failing probe after any repair.
2. LM Studio native JSON schema support may vary; strict JSON + validation is the prescribed compatibility path, not a blocker.
3. Existing fidelity validators may produce false positives for Chinese source tags, names, dates and number formatting; use synthetic boundary cases and keep uncertainty scoped.
4. Exact frozen rubric, evaluator protocol, and unrounded Gemini baselines have not yet been located from current task evidence; do not use rounded displayed medians for final decision.
5. A full multi-template renderer risks compatibility drift; Stage05 found current generic sections are hardcoded and no per-section model rendering occurs. Map current production template contracts and preserve deterministic assembly/output checks.
6. The read-only mechanism audit found no live V2 coverage/entity/source-tag/term/cross-section checks in this candidate; prove call-site wiring for each required mechanism.

## BLOCKING_AND_NON_BLOCKING_UNKNOWNS

- Blocking to quality acceptance only: missing frozen evaluator/rubric or original unrounded baseline sets the affected C10/C14 `CHECK_RESULT: BLOCKED`, class `AUTHORITY`, exact label `QUALITY_ACCEPTANCE_BLOCKED_BY_MISSING_FROZEN_EVALUATOR`, and no waiver. This does not block implementation, regression, or available local E2E. Since C10/C14 are CORE acceptance inputs and required verification, Stage04 routes to `CORE_ACCEPTANCE_STATUS: BLOCKED`, verification `INCOMPLETE` when other valid evidence exists, independent acceptance `PENDING`, closure `CORE_ACCEPTANCE_BLOCKED`; Stage05 inability to conclude also sets independent acceptance `BLOCKED` and closure `ACCEPTANCE_BLOCKED`, preserving the Stage04 snapshot.
- Environment-scoped acceptance blockers: requested model/hardware unavailable sets the affected C9/C14 `CHECK_RESULT: BLOCKED`, class `ENVIRONMENT`. Complete all unrelated work and preserve prior implementation/CORE evidence. The same CORE/verification/independent-acceptance routing applies; never convert the model blocker to `IMPLEMENTATION_STATUS: BLOCKED`.
- Non-blocking: native structured-output support absent; use strict JSON validation. Optional glossary/registry item absent; degrade locally. Held-out data absent; state limitation.

## DEFINITION_OF_DONE

Architecture implementation is complete only when: fact ledger with provenance replaces Markdown as V2's core contract; live extraction requests and validates causal/conditional/negation/numeric/date/attribution fields; deterministic consolidation and conflicts work; template-derived section-by-section LLM render/assembly is live; firewall compares every required claim to raw evidence and rejects the Stage05 inverted-predicate probe at the live gate; coverage/entity/number/date/attribution/source-tag/cross-section/template-term mechanisms are actually wired; raw/corrected source roles are explicit; targeted patch is guarded and rollback demonstrated; Qwen/Gemma profile wiring and repeated selection are live and separate from model-independent quality rules; diagnostics are expanded; V1 rollback remains available; cloud/v4.7.4/privacy invariants hold. Profile controls/sampling are closure and scoped acceptance requirements, not gates on unrelated valid records.

Task closure additionally requires: selected causal claim correct end-to-end; focused and full tests/docs pass; fresh Gemma and Qwen E2E pass; fresh blind 3+3 meets every per-output/per-dimension 80% gate against original unrounded baseline with zero adjudicated major fidelity hard fails; privacy audit passes; execution.md complete; Draft PR #19 updated. If the frozen evaluator/baseline cannot be found, report the exact scoped blocker and keep task closure pending while preserving completed implementation evidence.

Profile-selection acceptance additionally requires repeated candidate-profile runs at the counts and statistics in W7/C14; these required CORE-acceptance runs never veto an unrelated record and never count as blind 3+3 samples. The canonical six-field status aggregation is in `C9/C10/C14 STATUS AGGREGATION`; it is not an implementation or record-level veto and cannot be self-waived.

## HANDOFF_HINTS

- Revision 1's first-divergence result and attempts are evidence; do not repeat the failed “put more transcript in final prompt” hypothesis.
- Revision 4 selected-claim and firewall requirement remains, but Stage05 attempt 01 proves the first implementation was defective. Re-run its exact causal-predicate inversion probe before and after the live-gate repair.
- C3 baseline is the pre-mutation focused cloud contract test command and redacted artifact specified in W0; if shared behavior is touched, add and hash a synthetic byte-level golden for the touched boundary. Baseline unavailability is reported as scoped `BLOCKED`/verification `INCOMPLETE`, never as unchanged-by-assumption.
- Do not implement until this revision's independent review gate is `PLAN_APPROVED`, then regenerate Handoff and use a fresh Stage 04 context.
- The review must specifically challenge veto scope, schema-failure behavior, test gate baselines, template coverage complexity, and whether experiment mechanisms are selected rather than copied.
- Execution/reporting uses orthogonal status fields from workflow-routing v2. `DONE` is only overall closure; see `C9/C10/C14 STATUS AGGREGATION` for all six fields when acceptance prerequisites are missing. Preserve implementation and independently proven CORE facts; never rewrite the Stage04 snapshot.
