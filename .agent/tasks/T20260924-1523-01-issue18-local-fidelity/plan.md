# Issue #18 地端會議紀錄 Fidelity Root-Cause + Repair Plan

## META

- TASK_ID: T20260924-1523-01-issue18-local-fidelity
- ISSUE: #18 [P7-C] 定位 Gemma 4 31B / Qwen 3.8 27B 會議紀錄品質失真根因
- STATUS: READY_FOR_IMPLEMENTATION
- PLAN_REVISION: 1
- TASK_CLASS: CRITICAL
- REVIEW_REQUIRED: YES
- INDEPENDENT_ACCEPTANCE_REQUIRED: YES
- E2E_REQUIRED: YES
- ACCEPTANCE_MODE: DIAGNOSTIC + E2E + BLIND_RUBRIC
- BASE_BRANCH: main
- ANCHOR_HEAD: b9cb3772edbd65c2663b267d18eb6e89432de720
- IMPLEMENTATION_BRANCH: issue-18-first-divergence-diagnostic
- Fresh implementer required: YES
- Target executor: GPT-6 on the owner's local repository
- This PR is intentionally plan-first. Do not merge before implementation, validation, and independent acceptance are complete.

## PRIMARY_OUTCOME

Find the first stage at which a source-verifiable claim diverges from the transcript in the local summarization pipeline, implement the smallest mechanism-level repair supported by that evidence, and validate that fresh Gemma 4 31B and Qwen 3.8 27B outputs meet the issue's 80% engineering target without a major fidelity hard fail.

The task is not complete when observability exists. The task is not complete when one diagnostic run looks better. The task is complete only when:
1. first divergence is evidenced rather than guessed;
2. the repair addresses that evidenced mechanism;
3. focused and full regression tests pass;
4. fresh E2E outputs are produced;
5. a fresh blind cohort is evaluated against the frozen rubric;
6. privacy constraints are respected;
7. no unsupported claim of success is made.

## FIRST-PRINCIPLES ROOT-CAUSE ANALYSIS

### What is already established

The historical failing cohort showed final-quality failures for both local models. The failure shapes include overlong or over-segmented records, repeated sections, unsupported details, and possible causal-direction or attribution mistakes. The cohort used three extraction chunks. For the cited failing batch, consolidation was a zero-loss concatenation and merge rounds were zero. Therefore an LLM merge-round truncation mechanism is not supported as the root cause for that batch.

The current local code path is structurally:

transcript
→ chunking
→ local extraction LLM per chunk
→ cleaned extraction notes
→ merge/consolidation
→ local final generation from merged notes
→ cleaned/finalized record
→ quality validator comparing record mainly to merged notes
→ zero or more full-record refinement rewrites from current record + merged notes
→ cleaned/finalized record
→ final result

The critical code boundary is backend/services/summarization.py, especially:
- _summarize_with_local_pipeline
- _build_chunk_extraction_message
- _merge_notes_until_fit
- _build_summary_from_notes_message
- _build_refinement_message
- _generate_with_local_engine
- _clean_ollama_output
- _finalize_record_text
- _validate_summary_quality

Deterministic post-processing also crosses backend/core/text_postprocess.py.

### RC-A: Observability gap is the root cause of the current diagnostic deadlock

Historical evaluation can tell us that the final answer is wrong, but the program does not retain enough per-stage evidence to tell us where the first divergence occurred. Without raw/clean/finalized checkpoints and branch metadata for the same claim, changing prompts, context size, refinement behavior, or model parameters is causal guesswork.

This is a root cause of our inability to diagnose the historical failures. It is not, by itself, proof of the product-quality mechanism that created the wrong sentence.

### RC-B: The local path contains a structural source-grounding cut after extraction

In the current local path, _build_summary_from_notes_message accepts extracted_notes but not transcript. _build_refinement_message accepts current_summary + extracted_notes + issues but not transcript. _validate_summary_quality accepts summary + extracted_notes and performs structural checks, minimum length, language/leakage checks, and action recall relative to the notes.

By contrast, the cloud path explicitly has _build_cloud_summary_message(extracted_notes, transcript, ...) and _build_cloud_refinement_message(..., transcript, ...), and also has transcript-grounded checks for selected risks.

First-principles consequence: once a claim is omitted or distorted in local extraction notes, downstream local final generation cannot recover the missing source fact because the source is no longer available to it. A later refinement cannot recover it either for the same reason.

This is an architectural source-grounding gap. It does not prove that every historical failure started in extraction, but it proves that extraction mistakes are irreversible under the current local architecture.

### RC-C: Local validation is self-referential for semantic truth

A validator cannot establish source fidelity if its reference is itself a lossy derived artifact that may already contain the same error.

Current _validate_summary_quality is useful for format, minimum content, leakage, simplified Chinese, and action recall. It is not a transcript-fidelity validator. If extraction invents a wrong attribution and final generation faithfully copies it, the validator can pass because the notes and final record agree with each other. If extraction omits a critical fact, the validator cannot know the fact existed in the transcript.

Therefore current local validation provides useful product hygiene but cannot serve as evidence that a claim is source-faithful.

### RC-D: Refinement is a full regenerative rewrite and therefore can regress fidelity

When issues are detected, the pipeline asks the model to rewrite the full record. That creates another stochastic transformation boundary. A refinement may fix formatting or completeness while changing a previously correct attribution, causal direction, number, or scope. The current local loop has no semantic regression guard against the source transcript and no explicit before/after fidelity comparison.

This does not prove refinement caused the historical defects. It proves refinement is an independent risk boundary that must be observed and tested.

### What remains UNKNOWN until the diagnostic run

Do not claim any of the following as confirmed before evidence:
- extraction is the first divergence;
- final generation is the first divergence;
- refinement is the first divergence;
- post-processing is the first divergence;
- context window size is the quality root cause;
- Gemma or Qwen model capability alone is the root cause;
- a prompt-only change will fix the issue;
- the old failed cohort can be exactly reconstructed without its missing stage snapshots.

## GOAL_CONTRACT

### CORE

- G1. Add opt-in local diagnostic tracing with stable stage identifiers and privacy-safe metadata.
- G2. Capture enough information to identify first divergence for at least one source-verifiable failed claim.
- G3. Run a controlled diagnostic with frozen transcript/template/model/context/generation settings/code revision.
- G4. Determine the first divergence and prove it with stage evidence.
- G5. Implement a minimal fix chosen from the evidence-driven decision tree below.
- G6. Add fail-first regression tests that reproduce the mechanism before the fix and pass after it.
- G7. Run fresh E2E for Gemma 4 31B and Qwen 3.8 27B.
- G8. Run a fresh 3-output cohort per local model and evaluate with the frozen four-dimensional rubric.
- G9. Each output and each dimension must meet the frozen Gemini median × 0.80 threshold, with zero adjudicated major fidelity hard fail, before declaring the 80% target achieved.
- G10. Preserve user privacy and keep transcript/prompt/raw model content out of GitHub, tracked files, PR comments, and ordinary logs.

### MUST NOT BREAK

- Existing merge convergence/fail-loud guarantees from v4.7.4.
- Existing LM Studio immutable loaded-instance selection within a task.
- Existing local/cloud separation unless a specific repair deliberately changes local source access.
- Existing cloud behavior unless a shared helper change requires a no-behavior-change refactor.
- Existing fallback semantics.
- Existing template-driven required-section behavior.
- Existing privacy rules around transcript and meeting content.
- Existing deterministic post-processing tests.
- No force push.

### NON-GOALS

- Do not redesign the entire summarization system.
- Do not add a second LLM judge as a production truth oracle.
- Do not change the frozen blind-rubric definition merely to make local models pass.
- Do not relax hard-fail criteria.
- Do not count the diagnostic run as an independent quality sample.
- Do not use one meeting to claim general cross-meeting quality.
- Do not commit transcript, prompts, raw local-model responses, private names, absolute local paths, or sensitive cache files.

## PRIVACY AND EVIDENCE CONTRACT

Tracked evidence may contain only:
- run id
- code revision
- model/provider identifier that is safe to disclose
- context window and generation parameter scalars
- stage id
- parent stage id
- input/output SHA-256
- estimated token/character counts
- finish reason / completion token counts when available
- branch choice such as notes_only or notes_plus_transcript
- validation issue counts
- selected claim id
- stage-level claim status as a categorical label
- accepted/discarded/rollback state
- elapsed time
- redacted verdicts

Raw material must remain local and gitignored, under a task-specific runtime directory such as:
data/cache/diagnostics/T20260924-1523-01-issue18-local-fidelity/<run-id>/

The executor must verify this path is ignored before writing sensitive content. If it is not ignored, fix the ignore rule first. Never print raw transcript or raw generated text to ordinary logs.

If a diagnostic needs raw stage snapshots, use an explicit opt-in flag. Raw snapshots are local-only. Default product behavior must not start storing them.

## DIAGNOSTIC STAGE CONTRACT

At minimum emit a stable event at these boundaries:

- pipeline.start
- extraction.chunk.N.input
- extraction.chunk.N.raw
- extraction.chunk.N.cleaned
- consolidation.input
- consolidation.output
- final.input
- final.raw
- final.cleaned
- final.finalized
- final.validation
- refinement.round.N.input
- refinement.round.N.raw
- refinement.round.N.cleaned
- refinement.round.N.finalized
- refinement.round.N.validation
- refinement.round.N.accepted_or_discarded
- selection.final
- pipeline.end

Each generation-stage event must record the actual source branch:
- notes_only
- notes_plus_transcript
- notes_plus_source_excerpt
- other explicitly named branch

Do not infer the branch after the fact.

For LM Studio, also record safe generation metadata already available or derivable at the provider boundary:
- selected loaded instance identity
- model key
- context length
- requested max tokens
- finish reason
- reasoning presence/count if exposed
- prompt/completion token counts if exposed
- semantic retry count
- network retry count

## SELECTED CLAIM CONTRACT

The first diagnostic claim must be:
- verifiable directly from the transcript;
- important enough to represent a fidelity failure;
- specific enough to label at every stage;
- free of ambiguous segmentation where possible;
- one of: attribution, causal direction, numeric fact, decision, explicit action, deadline, or another atomic factual relation.

Create a local-only claim specification with:
- claim_id
- claim_type
- source anchor or source hash
- expected relation
- unacceptable inversion/attribution variants
- normalized keywords used only as aids, not as the sole semantic judge

Tracked artifacts may record only claim_id and categorical stage status:
- CORRECT
- MISSING
- DISTORTED
- UNSUPPORTED_ADDITION
- AMBIGUOUS
- NOT_APPLICABLE

If a claim requires human semantic adjudication, record the category locally and commit only the redacted category/result.

## FIRST-DIVERGENCE RULE

The first divergence is the earliest stage where the selected claim changes from source-correct to MISSING, DISTORTED, or UNSUPPORTED_ADDITION and is not merely a representation change.

A later stage that fixes the claim does not erase the earlier first divergence. Record both:
- first_divergence_stage
- final_delivery_status

One run that does not reproduce the defect means only NOT_REPRODUCED_THIS_RUN. It does not falsify the historical hypothesis.

## EVIDENCE-DRIVEN REPAIR DECISION TREE

The executor must not choose a repair branch until the first divergence is evidenced.

### Branch A: First divergence occurs during extraction

Required reasoning:
- The local pipeline has already lost source truth before final generation.
- Prompt-only tweaks are allowed only if a fail-first test isolates a prompt instruction defect.
- Prefer mechanism-level grounding/provenance if the failure is omission, attribution, relation inversion, or unsupported compression.

Allowed minimal repairs, choose the smallest evidenced one:
1. strengthen extraction contract for the failing relation type and add provenance anchors;
2. preserve source references in extraction notes so later stages can recover/verify;
3. add a source-recovery path for claims missing from notes;
4. if context allows, provide transcript or bounded source excerpts to local final/refinement for grounded recovery.

Mandatory tests:
- source claim present in transcript but omitted/distorted in extraction before fix;
- corrected extraction after fix;
- no invention when the source claim is absent;
- chunk overlap does not duplicate or flip the claim.

### Branch B: Extraction is correct, first divergence occurs in final generation

Required reasoning:
- Notes already contain the correct claim, so extraction is not the mechanism.
- Fix final-generation grounding or validation, not extraction.

Allowed minimal repairs:
1. explicit relation-preservation rules for the demonstrated failure;
2. source-aware final input when budget permits;
3. provenance-preserving representation from notes into final generation;
4. a deterministic or evidence-backed guard that rejects a demonstrated unsupported transformation.

Mandatory tests:
- correct notes in, wrong final out on fail-first fixture;
- fixed final preserves relation;
- absence case remains absent;
- no context-budget regression.

### Branch C: Final is correct, first divergence occurs in refinement

Required reasoning:
- Full-record rewrite is introducing a regression.

Preferred repair order:
1. do not accept a refinement that regresses the selected fidelity invariant;
2. rollback to the prior candidate when the refinement is worse;
3. narrow refinement to the failed requirement if feasible;
4. only then adjust refinement prompt.

Mandatory tests:
- round N input correct;
- round N candidate regresses;
- guard rejects or rolls back;
- real needed refinements can still be accepted.

### Branch D: Raw model output is correct but cleaning/finalization causes divergence

Fix deterministic transformation only.

Mandatory tests:
- exact pre/post fixture proving the transformation;
- semantics-preserving cases;
- protected terms;
- no new structural regressions.

### Branch E: No selected claim reproduces after controlled runs

Do not invent a root cause. Expand the diagnostic claim set to the next source-verifiable hard-fail claim, still one claim at a time. After a bounded set of attempts, report non-reproduction and keep the issue root cause UNKNOWN.

## SOURCE-GROUNDING DESIGN RULES

If the evidenced repair requires giving transcript evidence back to local final/refinement, implement it as a budget-aware source resolver rather than blindly appending the entire transcript.

Required properties:
- compute fit against the same effective context used by the selected local instance;
- reserve output budget and refinement feedback budget;
- prefer full transcript only when it fits safely;
- otherwise use bounded source excerpts/provenance-linked chunks;
- never silently truncate source evidence;
- log only hashes/counts/branch labels, not content;
- keep current notes-only behavior as an explicit fallback only if source evidence cannot fit, and make that branch observable.

Do not copy cloud behavior mechanically. Local context limits are real.

## OBSERVABILITY IMPLEMENTATION GUIDANCE

Prefer a small diagnostic recorder abstraction rather than scattering ad-hoc file writes.

Suggested shape:
- immutable diagnostic config created at pipeline start;
- in-memory event collector;
- optional raw snapshot writer behind explicit opt-in;
- redacted manifest writer at pipeline end;
- no global mutable singleton;
- no production behavior change when diagnostics are disabled.

The recorder must be injectable/testable. Unit tests must be able to capture emitted events without filesystem dependence.

The recorder must fail soft:
- a failure to write diagnostic evidence must not corrupt the meeting record;
- emit a warning without raw content;
- do not change generation decisions merely because tracing is enabled.

## IMPLEMENTATION WAVES

### WAVE-00: Re-verify repository and protect owner work

Before editing:
- git fetch origin
- git status --short
- git rev-parse HEAD
- verify this branch contains the planning commit and is based on the intended main lineage
- if unrelated local changes exist, do not clean, reset, stash, or overwrite them automatically
- create a local safety branch named backup/issue-18-before-gpt6-<timestamp> from current HEAD
- no force push

Record fresh baseline:
- focused summarization tests
- full tests if practical
- docs checker
- exact model inventory and loaded context, without sensitive payload

### WAVE-01: Fail-first tests for diagnostic event coverage

Add tests that assert:
- required stage events are emitted in order;
- source branch labels are exact;
- raw/cleaned/finalized hashes differ only when content differs;
- diagnostics disabled means no raw files and no behavior change;
- diagnostic writer failure is fail-soft;
- no raw meeting content appears in the redacted manifest.

No product-quality fix in this wave.

### WAVE-02: Implement privacy-safe stage tracing

Implement the diagnostic recorder and wire every stage in DIAGNOSTIC STAGE CONTRACT.

Do not alter prompts, generation parameters, or validation semantics yet.

Run focused tests and a synthetic pipeline run.

### WAVE-03: Controlled first-divergence runner

Extend or add a task-specific local diagnostic harness, preferably building on scripts/e2e/rerun_local_summarize.py rather than duplicating unrelated ASR work.

Required CLI inputs:
- transcript path or task artifact path
- model/provider selection expectation
- template id
- diagnostic output root
- claim spec path
- optional fixed seed if provider supports it
- explicit raw-snapshot opt-in

The harness must:
- freeze and print safe configuration;
- verify model identity before and after run;
- refuse to mix model changes into the same run;
- produce redacted manifest + claim stage table;
- exit nonzero on invariant violation;
- never treat a pre-model ASR/helper failure as a quality sample.

### WAVE-04: Reproduce and identify first divergence

Run a diagnostic for one source-verifiable failure on Gemma 4 31B and/or Qwen 3.8 27B as applicable.

Freeze:
- transcript
- template
- model key
- loaded instance/context
- code revision
- generation settings
- local pipeline settings

Output:
- first_divergence_stage
- final_delivery_status
- stage status table
- evidence hashes
- whether the historical failure reproduced

Do not change production behavior until this evidence exists.

### WAVE-05: Implement minimal mechanism-level repair

Choose Branch A/B/C/D/E from the decision tree.

Before the fix, add a fail-first regression reproducing the mechanism using mocked model boundaries where possible. The test must fail for the right reason.

Implement the smallest repair that changes the evidenced mechanism.

Do not combine unrelated quality tuning.

### WAVE-06: Targeted contrast and regression

Required:
- fail-first test now passes;
- adjacent negative cases pass;
- existing summarization tests pass;
- v4.7.4 merge/context/reasoning regressions remain green;
- cloud path remains unchanged unless an explicit shared-helper no-op refactor was necessary;
- full tests pass or any pre-existing failure is separately evidenced.

### WAVE-07: Fresh E2E

Use the same fixed material for controlled comparison.

For each local model:
- produce at least one fresh E2E output after the fix;
- preserve diagnostic manifest;
- ensure summary_failed=false;
- run scripts/e2e/check_record_output.py if applicable;
- record call counts, refinement rounds, context branch, and safe timing metadata.

This run is for mechanism validation and product E2E. It is not automatically the blind-quality cohort.

### WAVE-08: Fresh blind quality cohort

Produce three fresh outputs for Gemma 4 31B and three fresh outputs for Qwen 3.8 27B using the frozen evaluation conditions.

Use the already-frozen rubric:
- Completeness
- Faithfulness
- Traceability
- Usability

Use the same blind-evaluation process described in Issue #18:
- two independent scorers;
- third adjudicator only when the frozen disagreement rule triggers;
- preserve anonymization;
- do not reuse the diagnostic run as an independent cohort sample.

The acceptance threshold must be computed from the original unrounded Gemini baseline data. Do not hardcode only the displayed rounded values. The displayed medians are a sanity check:
- Completeness about 83.9286
- Faithfulness about 89.7959
- Traceability about 93.8776
- Usability 85.0000

Displayed approximate 80% sanity checks:
- Completeness about 67.14
- Faithfulness about 71.84
- Traceability about 75.10
- Usability 68.00

Actual gate uses the underlying unrounded baseline.

Pass condition:
- every one of the three outputs for each local model;
- every rubric dimension;
- score >= corresponding Gemini median × 0.80;
- no adjudicated major fidelity hard fail.

If the frozen evaluator assets or unrounded baseline are unavailable locally, do not invent them. Mark QUALITY_ACCEPTANCE_BLOCKED_BY_MISSING_FROZEN_EVALUATOR and report exactly what is missing. Mechanism repair may still be completed, but the 80% goal must remain unclaimed.

### WAVE-09: Documentation, execution record, and PR closure

Add/update:
- task execution.md with redacted evidence;
- system architecture documentation if pipeline behavior changed;
- CHANGELOG/VERSION only if repository release policy requires it for the behavior change;
- tests list and diagnostic usage instructions.

Update PR body with:
- confirmed first divergence;
- confirmed mechanism;
- code changes;
- tests;
- E2E;
- blind cohort outcome;
- residual risks.

Only mark PR ready for review after all closure gates are satisfied or explicitly blocked by an external prerequisite.

## ACCEPTANCE CONTRACT

### CHECK-01 Diagnostic stage coverage
CORE. Unit test proves every required stage event and ordering.

### CHECK-02 Privacy
CORE. Redacted manifest contains no transcript/raw output/prompt/private names/absolute paths. Raw snapshots are opt-in and gitignored.

### CHECK-03 Behavior neutrality while tracing
CORE. With diagnostics disabled, outputs and call behavior are unchanged for deterministic mocked fixtures.

### CHECK-04 First divergence evidenced
CORE. A source-verifiable claim has a stage table and a clearly identified first divergence, or bounded non-reproduction is honestly reported.

### CHECK-05 Fail-first mechanism test
CORE. A regression test fails before the repair for the demonstrated mechanism and passes after.

### CHECK-06 Minimal repair
CORE. Diff is scoped to the mechanism. No unrelated prompt tuning or quality tweaks.

### CHECK-07 Refinement safety
CORE when Branch C or a shared refinement path is touched. Demonstrated fidelity regression cannot be silently accepted.

### CHECK-08 Post-processing safety
CORE when Branch D/shared post-processing is touched. Exact fixture proves no semantic deletion/inversion.

### CHECK-09 v4.7.4 invariants
CORE. Merge convergence, no hard truncation, loaded-instance context authority, and LM Studio thinking behavior remain protected.

### CHECK-10 Focused tests
CORE. Relevant summarization and new issue-18 tests green.

### CHECK-11 Full regression
REPO-HEALTH. Full tests green; pre-existing failures require explicit evidence and must not be hidden.

### CHECK-12 E2E
CORE. Fresh local E2E for both target model families when environment permits. Environment blocker is distinct from implementation failure.

### CHECK-13 Blind rubric
CORE QUALITY GATE. Fresh 3+3 cohort meets per-output/per-dimension 80% thresholds and no major fidelity hard fail.

### CHECK-14 Documentation/evidence hygiene
CORE. execution.md and tracked evidence are redacted; no sensitive artifacts tracked.

## TEST COMMANDS

Executor must adapt to the repo's current environment but should begin with:
- PYTHONPATH=. DATA_DIR=./data .venv/bin/python -m pytest tests/test_summarization_service.py -q
- PYTHONPATH=. DATA_DIR=./data .venv/bin/python -m pytest tests/test_t20260922_regression.py -q
- PYTHONPATH=. DATA_DIR=./data .venv/bin/python -m pytest tests/ -q
- bash scripts/check_docs.sh

Use uv equivalents if the local repo has migrated to uv and the commands above are stale. Record which command actually ran.

## COMMIT AND GIT DISCIPLINE

- Never force push.
- Preserve unrelated local work.
- Use atomic commits by wave or coherent mechanism.
- Before each push: git fetch origin and verify no unexpected remote branch movement.
- If remote moved, rebase/merge deliberately and rerun affected tests; do not overwrite.
- Do not commit raw diagnostic runtime data.
- Do not commit model binaries or private artifacts.
- Do not claim tests were run unless they actually ran.

Suggested commit progression:
1. test(issue18): add diagnostic trace fail-first coverage
2. feat(issue18): add privacy-safe local stage tracing
3. test(issue18): reproduce first-divergence mechanism
4. fix(issue18): repair confirmed fidelity divergence mechanism
5. docs(issue18): record diagnosis, acceptance, and residual risk

## DEFINITION OF DONE

All must be true:
- root cause statement distinguishes diagnostic root cause from product mechanism;
- first divergence is evidenced or explicitly not reproducible;
- a mechanism-level fix is implemented if divergence reproduced;
- new tests demonstrate the mechanism;
- full regression is green or pre-existing failures are transparently isolated;
- fresh E2E completed for target models when environment permits;
- fresh blind 3+3 cohort evaluated with frozen rubric;
- 80% target is claimed only if exact gate passes;
- no major fidelity hard fail;
- no sensitive content leaked to Git/GitHub;
- execution.md exists and is sufficient for a fresh reviewer;
- PR body is updated from plan-only to implementation evidence;
- independent reviewer can reproduce the decision from tracked redacted evidence and local instructions.

## STOP / ESCALATE CONDITIONS

Stop and report rather than guess if:
- the frozen evaluation rubric or unrounded Gemini baseline cannot be recovered;
- the fixed transcript/candidate material needed for the agreed cohort is unavailable;
- target model identity cannot be frozen;
- the selected local model changes during a diagnostic run;
- the fix would require weakening an existing fail-loud or privacy invariant;
- the only way to pass is to lower the rubric threshold;
- raw sensitive artifacts would need to be committed;
- unrelated local changes overlap the same code and cannot be safely reconciled.

Environment blockers do not equal implementation failures. Report them separately.

## EXECUTOR FINAL REPORT FORMAT

At completion, report:
- Anchor and final HEAD
- Confirmed first divergence
- Confirmed mechanism
- Chosen repair branch A/B/C/D/E
- Files changed
- Fail-first evidence
- Focused test result
- Full regression result
- E2E result per model
- Blind cohort table per model/output/dimension
- Hard-fail count
- 80% gate PASS/FAIL/BLOCKED
- Residual risks
- Sensitive-artifact audit
- PR readiness recommendation
