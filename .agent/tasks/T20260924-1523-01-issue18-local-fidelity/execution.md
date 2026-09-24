# Execution Record — Issue #18 Local Fidelity

- TASK_ID: T20260924-1523-01-issue18-local-fidelity
- PLAN_REVISION: 1
- IMPLEMENTATION_BRANCH: issue-18-first-divergence-diagnostic
- PLAN_ANCHOR: b9cb3772edbd65c2663b267d18eb6e89432de720
- Current implementation before evidence-driven repair: 722797b6fa42c8cca73838b1bd9e50fbdb12161f
- Privacy: source transcript, prompts, generated text, private names, and absolute source paths are excluded from this tracked record.

## WAVE-00 — Repository and baseline

- [VERIFIED] Work is on the planned implementation branch; unrelated untracked owner work was preserved.
- [VERIFIED] Local safety branch was created before implementation.
- [VERIFIED] Baseline and intermediate regression runs are recorded in the implementation session; full test suite before the quality repair was green.
- [VERIFIED] Frozen local model inventory identified Qwen 3.8 27B and Gemma 4 31B. The Qwen run below used a fixed 32,000-token loaded instance.

## WAVE-01–03 — Trace, runner, and privacy

- [VERIFIED] Added opt-in stage diagnostics and a controlled local runner. Tracing disabled preserves ordinary pipeline behavior; raw snapshots require explicit opt-in and stay in the ignored task cache.
- [VERIFIED] Redacted manifests contain stage identifiers, hashes/counts, safe model/config scalars, and branch labels; a separate validator links human-adjudicated categorical claim statuses to event hashes. No source or generated text is written into tracked evidence.
- [VERIFIED] The diagnostic test suite checks stage ordering, privacy, disabled behavior, and safe metadata.

## WAVE-04 — Frozen first-divergence evidence

### Attempt 1: attribution claim rejected as ambiguous

- [VERIFIED] Frozen Qwen baseline run: `03129fa7709a42f285c38f6b82fe5a0d`, code revision `722797b6fa42c8cca73838b1bd9e50fbdb12161f`, LM Studio loaded instance `qwen3.8-27b-splash`, context 32,000, template `section_meeting`, transcript SHA-256 `b7b9e5e05be5a560101312d9fb954d2e6aa10044febb8d3fca5a79f3931d9db0`. It completed in 524,836 ms with four chunks, one merge round, zero refinements, and `summary_failed=false`.
- [VERIFIED] A second fresh run after the candidate repair, `16c2ffac86224d6dacb0aa8cef6ea088`, completed in 719,134 ms with `final.input=notes_plus_transcript`, 22 events, and `summary_failed=false`. It is not counted as a quality sample.
- [CORRECTION] The original claim attempted to infer that source speaker index 3 was not the DOCX role “科長”. Independent source audit found no verified speaker-index-to-role mapping. Therefore the claim is **AMBIGUOUS**, and neither run establishes first divergence for that claim. The earlier categorical stage table was too strong and has been superseded.
- [VERIFIED] [`evidence/first-divergence.json`](evidence/first-divergence.json) now records this adjudication as `AMBIGUOUS`, includes no first-divergence stage, and links only safe event hashes to the two local redacted manifests. It contains no raw text.

### Attempt 2: source-verifiable omission claim

- [DECIDED] Use `W04-OMISSION-ENV-01`, an omission claim anchored to `00:33:57–00:35:21`, concerning a concrete facilities/pipe issue that appears repeatedly in the source but is absent from the supplied DOCX. This does not rely on speaker-role mapping or private names.
- [PENDING] Run a controlled pre-repair Qwen diagnostic at the frozen baseline revision, then adjudicate the claim across all stages before accepting any repair branch.

## WAVE-05 — Evidence-driven repair (Branch A candidate; acceptance pending valid claim evidence)

- [UNVERIFIED] The source-grounding change below is a candidate Branch A mechanism, not an accepted root-cause repair until Attempt 2 establishes a valid first divergence and fresh E2E validates the selected claim.
- [VERIFIED] The pre-repair fail-first regression captured the mechanism: final generation received notes only, so a source-verifiable correction could not be recovered from source.
- [IMPLEMENTED] A budget-aware resolver prefers the full transcript if it safely fits, otherwise selects complete timestamp/lexical-overlap source chunks, and otherwise reports an explicit notes-only fallback. It never silently truncates evidence. The local cloud path is unchanged.
- [VERIFIED] Temperature, context limit, extraction prompt, refinement count, and validation/gating semantics were not tuned by this repair.
- [PENDING] The mocked test proves the source branch is supplied; only fresh E2E can establish semantic recovery by the actual model.

## WAVE-06 — Targeted and repository regression

- [VERIFIED] Focused diagnostic tests before claim-table tooling: 7 passed.
- [VERIFIED] Full suite before claim-table tooling: 812 passed, 2 skipped.
- [PENDING] Re-run focused/full tests after claim-table tooling and the selected-claim correction.
- [VERIFIED] `git diff --check` passed.
- [PENDING] Run full required regressions again after any final code adjustment and record docs check result.

## WAVE-07–08 — Fresh E2E and blind cohort

- [PENDING] Fresh post-repair E2E for Gemma 4 31B and Qwen 3.8 27B.
- [PENDING] Fresh blind cohort: three outputs per model, scored against the recovered frozen unrounded Gemini baseline and rubric. Diagnostic runs are excluded from cohort samples.
- [VERIFIED] Historical Issue #18 already contains an earlier three-model comparison (Gemini 3, Gemma 3, Qwen 3; three outputs/model), with recorded local-model failures. That historical comparison is not the required post-repair fresh cohort and is not counted toward this acceptance gate.

## WAVE-09 — Closure

- [PENDING] Independent acceptance artifact, final privacy audit, architecture/docs updates if required, atomic commits/push, and PR #19 description update.
- No quality-gate pass is claimed until the fresh blind cohort satisfies every per-output/per-dimension threshold and has no adjudicated major fidelity hard fail.
