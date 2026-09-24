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
- [VERIFIED] Redacted manifests contain stage identifiers, hashes/counts, safe model/config scalars, branch labels, and categorical claim outcomes; no source or generated text is written into tracked evidence.
- [VERIFIED] The diagnostic test suite checks stage ordering, privacy, disabled behavior, and safe metadata.

## WAVE-04 — Frozen first-divergence evidence

Selected claim: `internal_audit_prep_attribution_0656` (attribution; source anchor `00:06:56`, speaker index 3). Exact expected relation and raw claim specification remain local-only.

- [VERIFIED] Frozen run: `03129fa7709a42f285c38f6b82fe5a0d`.
- [VERIFIED] Code revision: `722797b6fa42c8cca73838b1bd9e50fbdb12161f`; model/provider: Qwen 3.8 27B / LM Studio; loaded context: 32,000; template: `section_meeting`.
- [VERIFIED] The same redacted manifest records transcript SHA-256 `b7b9e5e05be5a560101312d9fb954d2e6aa10044febb8d3fca5a79f3931d9db0`, code revision, claim id, model/provider, context, template, and elapsed time.
- [VERIFIED] Temperatures remained extraction 0.1, final 0.2, refinement 0.15; requested output cap 3,072; thinking disabled; no semantic or network retries. No prompt/context/temperature/refinement changes were made before this evidence.
- [VERIFIED] Run completed successfully in 524,836 ms with 22 stage events, four extraction chunks, one merge round, zero refinement rounds, and `summary_failed=false`.

### Redacted claim stage table

| Stage | Claim status | Evidence summary |
|---|---|---|
| Source | CORRECT | Source relation is tied to the selected timestamp and speaker index. |
| `extraction.chunk.1.raw` | DISTORTED | The relation is assigned to the chair role and shifted to a different timestamp. |
| `extraction.chunk.1.cleaned` | DISTORTED | Byte-preserving cleanup did not repair the relation. |
| Other extraction chunks | NOT_APPLICABLE | The selected relation is in chunk 1. |
| `consolidation.output` | DISTORTED | The shifted attribution remains. |
| `final.input` (`notes_only`) | DISTORTED | Downstream local generation receives only the already-distorted notes. |
| `final.raw` | MISSING | The topic remains, but the selected attribution relation is omitted. |
| `final.cleaned` / `final.finalized` | MISSING | No deterministic transform restores the relation. |
| `selection.final` | MISSING | Final delivered candidate lacks the attribution. |

- **First divergence:** `extraction.chunk.1.raw`.
- **Final delivery status:** `MISSING`.
- [VERIFIED] Machine-readable categorical stage evidence with corresponding event input/output hashes is in [`evidence/first-divergence.json`](evidence/first-divergence.json); it references the local redacted manifest by SHA-256 and contains no raw text. Stage categories are human-adjudicated; hashes identify the exact frozen event payloads without disclosing them.
- **Historical reproduction:** the same source-verifiable attribution failure is reproduced in this controlled run; this does not establish that every historical cohort error has the same cause.
- **Rejected alternatives for this claim:** cleanup is not first (raw is already distorted); consolidation is later; final generation loses the attribution but its input already has a distortion; no refinement occurred. No evidence implicates output truncation, reasoning, retries, or model/context changes in this run.

## WAVE-05 — Evidence-driven repair (Branch A)

- [DECIDED] Use the plan's Branch A source-recovery option: make source evidence available to local final/refinement generation under the selected instance's effective context budget.
- [VERIFIED] The pre-repair fail-first regression captured the mechanism: final generation received notes only, so a source-verifiable correction could not be recovered from source.
- [IMPLEMENTED] A budget-aware resolver prefers the full transcript if it safely fits, otherwise selects complete timestamp/lexical-overlap source chunks, and otherwise reports an explicit notes-only fallback. It never silently truncates evidence. The local cloud path is unchanged.
- [VERIFIED] Temperature, context limit, extraction prompt, refinement count, and validation/gating semantics were not tuned by this repair.
- [PENDING] The mocked test proves the source branch is supplied; only fresh E2E can establish semantic recovery by the actual model.

## WAVE-06 — Targeted and repository regression

- [VERIFIED] Focused diagnostic tests: 7 passed after the change.
- [VERIFIED] Full suite after the current repair: 812 passed, 2 skipped.
- [VERIFIED] `git diff --check` passed.
- [PENDING] Run full required regressions again after any final code adjustment and record docs check result.

## WAVE-07–08 — Fresh E2E and blind cohort

- [PENDING] Fresh post-repair E2E for Gemma 4 31B and Qwen 3.8 27B.
- [PENDING] Fresh blind cohort: three outputs per model, scored against the recovered frozen unrounded Gemini baseline and rubric. Diagnostic runs are excluded from cohort samples.
- [VERIFIED] Historical Issue #18 already contains an earlier three-model comparison (Gemini 3, Gemma 3, Qwen 3; three outputs/model), with recorded local-model failures. That historical comparison is not the required post-repair fresh cohort and is not counted toward this acceptance gate.

## WAVE-09 — Closure

- [PENDING] Independent acceptance artifact, final privacy audit, architecture/docs updates if required, atomic commits/push, and PR #19 description update.
- No quality-gate pass is claimed until the fresh blind cohort satisfies every per-output/per-dimension threshold and has no adjudicated major fidelity hard fail.
