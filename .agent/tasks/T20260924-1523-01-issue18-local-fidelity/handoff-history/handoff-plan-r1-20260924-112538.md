# GPT-6 Implementation Handoff — Issue #18

## TASK

- TASK_ID: T20260924-1523-01-issue18-local-fidelity
- STATUS: READY_FOR_IMPLEMENTATION
- PLAN_PATH: .agent/tasks/T20260924-1523-01-issue18-local-fidelity/plan.md
- PLAN_REVISION: 1
- ISSUE: #18
- BRANCH: issue-18-first-divergence-diagnostic
- BASE_ANCHOR: b9cb3772edbd65c2663b267d18eb6e89432de720
- Fresh implementer required: YES
- Target implementer: GPT-6 running locally in the owner's repo
- PR mode: DRAFT until implementation + acceptance are complete

## READ FIRST

Read the full plan.md before editing code. The key mistake to avoid is treating the current observability gap as if it were already proof that extraction, final generation, refinement, or the model itself is the product root cause.

The plan distinguishes:
1. diagnostic root cause: no stage-level evidence;
2. architectural risk: local final/refinement/validator lose access to transcript after extraction;
3. actual historical first divergence: still UNKNOWN until reproduced.

Do not collapse these into one claim.

## VERIFIED CODE FACTS AT PLANNING TIME

On main anchor b9cb3772:
- _summarize_with_local_pipeline extracts each chunk through _generate_with_local_engine and stores cleaned notes.
- local final generation calls _build_summary_from_notes_message(merged_notes, ...) and therefore uses notes, not transcript.
- local refinement calls _build_refinement_message(current_summary, merged_notes, issues, ...) and therefore uses current summary + notes, not transcript.
- local _validate_summary_quality(summary, merged_notes, ...) checks template sections, extra fields, forbidden patterns, minimum length, simplified Chinese, leakage, and action recall relative to notes; it is not a transcript-fidelity validator.
- cloud generation/refinement has explicit transcript-aware builders.
- failing cohort cited by Issue #18 had 3 extraction chunks, zero LLM merge rounds, and zero-loss consolidation; do not blame merge-round truncation without new evidence.
- current main is v4.7.4 lineage and contains merge/context/reasoning protections that must not regress.

## FIRST ACTIONS

1. git fetch origin
2. switch to issue-18-first-divergence-diagnostic
3. inspect git status; preserve unrelated owner work
4. create local backup/issue-18-before-gpt6-<timestamp> from current HEAD
5. read plan.md completely
6. run fresh focused baseline tests
7. inspect current code again for drift since b9cb3772
8. begin WAVE-01 only after confirming no conflicting changes

Do not force push. Do not clean/reset/stash unrelated owner changes automatically.

## IMPLEMENTATION ORDER

### 1. Instrument before tuning

Add fail-first unit coverage for the required diagnostic events, then implement the recorder. While doing this, do not modify prompts, context sizing, refinement policy, temperature, or quality thresholds.

### 2. Build controlled diagnostic runner

Prefer extending existing local re-summarization tooling. Freeze model identity, context, template, transcript, generation settings, and code revision. Record only safe metadata in tracked evidence.

### 3. Pick one atomic source-verifiable claim

Use an existing fidelity hard-fail claim if local evidence is available. The claim must be traceable through every stage.

### 4. Find first divergence

Trace extraction raw → extraction cleaned → consolidation → final input/raw/cleaned/finalized → each refinement round → final selection.

Record both:
- first divergence stage
- final delivery status

If not reproduced, do not pretend it was ruled out.

### 5. Only then implement repair

Choose exactly one evidence branch from plan.md:
- A extraction
- B final generation
- C refinement
- D post-processing
- E bounded non-reproduction

Add a fail-first mechanism test before changing behavior.

### 6. Validate mechanism and repo

Run focused tests, v4.7.4 regressions, full test suite, docs checker, and fresh E2E.

### 7. Run fresh blind 3+3 cohort

Three Gemma + three Qwen outputs, frozen rubric, two blind scorers + adjudicator rule, using the original unrounded Gemini baseline.

Do not count diagnostic outputs as blind-quality samples.

## HARD RED LINES

- Never write transcript/raw model output/raw prompts/private names into GitHub issue, PR body, tracked evidence, or ordinary logs.
- Never lower the 80% threshold to create a pass.
- Never remove the no-major-fidelity-hard-fail condition.
- Never infer success from structure-only check_record_output.py.
- Never claim source fidelity from notes-vs-summary agreement.
- Never blame model capability without isolating the pipeline stage.
- Never widen scope into unrelated ASR, diarization, UI, or cloud tuning.
- Never regress v4.7.4 merge fail-loud/no-truncation/context authority.
- Never force push.

## QUALITY TARGET

Use the frozen original unrounded Gemini medians as the source of truth.

Displayed issue medians are only sanity checks:
- Completeness 83.9286
- Faithfulness 89.7959
- Traceability 93.8776
- Usability 85.0000

Displayed approximate 80% thresholds:
- Completeness 67.14
- Faithfulness 71.84
- Traceability 75.10
- Usability 68.00

Pass only when every fresh output for both local models meets every dimension threshold and has no adjudicated major fidelity hard fail.

If the exact frozen baseline/evaluator is unavailable, mark final quality acceptance BLOCKED. Do not invent numbers.

## EXPECTED NEW/CHANGED ARTIFACTS

Exact file names may change if a simpler design is found, but the implementation should normally include:
- diagnostic recorder/helper near local summarization code
- issue-18 focused tests
- a controlled diagnostic runner or extension to existing rerun_local_summarize.py
- .agent/tasks/T20260924-1523-01-issue18-local-fidelity/execution.md
- redacted diagnostic evidence/manifest only
- architecture/changelog updates if behavior changes

Raw runtime artifacts belong under data/cache/diagnostics/... or another verified gitignored local path.

## ACCEPTANCE SUMMARY

Do not mark the PR ready until:
- stage tracing is covered and privacy-safe;
- first divergence is evidenced or honestly non-reproduced;
- mechanism repair has fail-first proof;
- focused + full tests pass;
- fresh E2E succeeds for target model environment;
- blind 3+3 quality gate is PASS, or missing external evaluator is explicitly BLOCKED;
- execution.md and PR description are updated with redacted evidence.

## FINAL PR UPDATE

Replace the plan-only PR narrative with:
- first divergence
- mechanism
- why alternative hypotheses were rejected
- exact minimal fix
- tests and fail-first evidence
- E2E details
- quality cohort table
- residual risks
- privacy audit
- final gate PASS/FAIL/BLOCKED
