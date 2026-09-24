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

### Attempt 2: source-verifiable omission claim did not reproduce

- [VERIFIED] Claim `W04-OMISSION-ENV-01` was anchored to `00:33:57–00:35:21` and concerned a repeated concrete facilities issue, without relying on speaker-role mapping or private names.
- [VERIFIED] Frozen pre-repair baseline run: `5ddabe69fff64cdab0b9ce8a1240b487`, code revision `722797b6fa42c8cca73838b1bd9e50fbdb12161f`, same Qwen loaded instance/context/template/transcript hash. It completed in 685,497 ms with 34 events, four chunks, one merge round, two refinement rounds, and `summary_failed=false`.
- [VERIFIED] Human-adjudicated claim table with event hashes is in [`evidence/claim-attempt-2-no-divergence.json`](evidence/claim-attempt-2-no-divergence.json): the claim remained represented through extraction chunks 3–4, consolidation, final generation, both refinements, and `selection.final`. Chunks 1–2 are `NOT_APPLICABLE`.
- **First divergence:** none in this run. **Final delivery:** `CORRECT`.
- [CORRECTION] Although the user DOCX omitted this concrete issue, the current controlled Qwen pipeline output retained it. Thus this DOCX omission is not a valid first-divergence claim for the current pipeline and cannot support a repair branch. It may reflect different run/configuration or an output artifact not reproducible in this controlled path.

### Historical cohort score comparison (redacted aggregates)

- [VERIFIED] Historical adjudicated three-output medians, in rubric order Completeness / Faithfulness / Traceability / Usability: Gemini `83.9286 / 89.7959 / 93.8776 / 85.0000`; Gemma `98.2143 / 86.5672 / 91.0448 / 90.0000`; Qwen `94.6429 / 85.8824 / 89.6552 / 70.0000`.
- [VERIFIED] Relative to Gemini medians, Gemma's dimension deltas were `+17.02% / -3.60% / -3.02% / +5.88%`; Qwen's were `+12.77% / -4.36% / -4.50% / -17.65%`. Positive means the local score is higher; negative means lower.
- [VERIFIED] These are descriptive historical medians only, not fresh post-repair results. Historical majority hard-fails affected Gemma 1/3 outputs and Qwen 2/3 outputs; high medians do not clear the zero-hard-fail criterion.

### Attempt 3: select a source-verifiable historical hard-fail claim

- [VERIFIED] Selected historical Qwen hard-fail claim `C-R03-F056-CAUSAL-DIRECTION`, an anchored causal-direction claim that does not rely on speaker-role mapping. The historical blind cohort had majority adjudication as a major fidelity hard fail for this candidate.
- [VERIFIED] Frozen pre-repair baseline run `65f618d42a5d4b1180f8fe5609f7f9e5`, code revision `722797b6fa42c8cca73838b1bd9e50fbdb12161f`, same Qwen model/context/template/transcript hash. It completed in 564,460 ms with 22 events, four chunks, one merge round, zero refinements, and `summary_failed=false`.
- [VERIFIED] Two independent redacted audits agreed: source and `extraction.chunk.3.input` are correct; chunk 3 raw/cleaned output distorts the relation; subsequent chunk 4 is not the same anchored claim; consolidation output and all final-delivery stages are missing the claim. The first divergence is `extraction.chunk.3.raw`; final delivery is `MISSING`. Event-hash-linked categorical judgments are in [`evidence/claim-attempt-3-baseline.json`](evidence/claim-attempt-3-baseline.json).
- [CORRECTION] The valid claim was identified only after the source-grounding candidate had already been implemented based on the initially presumed attribution claim. That earlier claim was subsequently downgraded as ambiguous. Therefore the candidate is not treated as accepted merely because it exists; only the selected-claim post-repair E2E and the required blind cohort can validate it.

## WAVE-05 — Evidence-driven repair (Branch A candidate; acceptance pending post-repair evidence)

- [SUPPORTED] Attempt 3 established a valid first divergence during extraction and showed that final generation had no transcript source available to recover the distorted causal relation. The source-grounding change below gives local final/refinement a bounded, budget-checked source path. The valid selected-claim E2E has now shown that this candidate alone is insufficient: source was present in final input, but final delivery remained `MISSING`.
- [VERIFIED] The fail-first regression captures the downstream recovery mechanism: final generation received notes only, so a source-verifiable correction could not be recovered from source. The corrected causal-direction fixture **failed on the pre-repair `722797b` worktree** at `assert source in final_message`, then passed on the candidate implementation.
- [IMPLEMENTED] A budget-aware resolver prefers the full transcript if it safely fits, otherwise selects complete timestamp/lexical-overlap source chunks, and otherwise reports an explicit notes-only fallback. It never silently truncates evidence. The local cloud path is unchanged.
- [VERIFIED] The first source-grounding candidate did not change temperature, context, extraction prompt, refinement count, or validation/gating semantics. The new evidence-driven extraction-contract attempt changes only the local extraction prompt; cloud prompt, context, temperatures, refinement count, and validation/gating semantics remain unchanged.
- [FAILED] The first valid-claim post-repair Qwen E2E did not establish semantic recovery. Two independent reviewers found first divergence still at `extraction.chunk.3.raw`, with claim missing from final delivery despite source in `final.input`. Do not treat the source-grounding candidate alone as accepted.
- [VERIFIED] Added a fail-first test requiring local extraction to preserve causal/conditional/temporal/negation direction, retain source timestamps, avoid inference, and leave the cloud extraction prompt unchanged. It failed before the local-only contract change because the required relation-direction instruction was absent.
- [IMPLEMENTED] Added a local-only relation/provenance contract to extraction: preserve subject/object/direction and negation scope, carry explicit source timestamps, treat overlap as one fact, and leave unsupported or unclear relations unasserted. Cloud extraction prompt is unchanged.
- [VERIFIED] Focused checks for the new local extraction contract, source-grounding path, and overlap preservation: 3 passed. The overlap fixture carries a synthetic anchored relation unchanged across adjacent chunks.
- [PENDING] The extraction-contract edit has not yet been validated by the selected-claim Qwen E2E; it remains a candidate until that run is independently adjudicated.

## WAVE-06 — Targeted and repository regression

- [VERIFIED] Focused diagnostic suite after claim-table tooling and selected-claim correction: 8 passed; the evidence-driven local extraction-contract, source-grounding, and overlap checks add 3 passing focused cases.
- [VERIFIED] Full repository suite after the local-only extraction-contract change: 814 passed, 2 skipped in 10.12 s.
- [VERIFIED] `git diff --check` passed.
- [VERIFIED] Documentation checker exited 0 after the extraction-contract change; it repeated the two README version warnings (`README.md`, `doc/README.md` vs VERSION).
- [PENDING] Re-run required regressions after any further product-code adjustment.

## WAVE-07–08 — Fresh E2E and blind cohort

- [VERIFIED] Qwen post-repair pipeline run `16c2ffac86224d6dacb0aa8cef6ea088` completed with `summary_failed=false`, 22 events, 719,134 ms, and `final.input=notes_plus_transcript`; it used the invalidated attribution claim and is not counted as a quality sample.
- [VERIFIED] Valid-claim Qwen diagnostic `170d08f286b145f59798da29c7ded61b`, code revision `2e5c34fb06c67edfb9480458b83ee7ee9612a493`, completed at 32,000 context with four chunks, one merge round, zero refinements, 22 events, `summary_failed=false`, and 712,587 ms. It is not a cohort sample.
- [VERIFIED] Two independent redacted reviewers found `final.input=CORRECT` (source supplied), but `final.raw`, selection, and pipeline delivery remained `MISSING`; first divergence persisted at `extraction.chunk.3.raw`. Semantic recovery: **NO**.
- [VERIFIED] `check_record_output.py` rejected this Markdown artifact only on `formal_title`; fallback marker, required sections (6/6), decision/action sections, minimum length, placeholder, and CJK-ratio checks passed. No DOCX artifact was produced by this transcript-only diagnostic.
- [PENDING] Fresh post-repair E2E for Gemma 4 31B.
- [PENDING] Fresh blind cohort: three outputs per model, scored against the recovered frozen unrounded Gemini baseline and rubric. Diagnostic runs are excluded from cohort samples; defer cohort until a mechanism candidate passes selected-claim E2E.
- [VERIFIED] Historical Issue #18 already contains an earlier three-model comparison (Gemini 3, Gemma 3, Qwen 3; three outputs/model), with recorded local-model failures. That historical comparison is not the required post-repair fresh cohort and is not counted toward this acceptance gate.

## WAVE-09 — Closure

- [PENDING] Independent acceptance artifact, final privacy audit, architecture/docs updates if required, atomic commits/push, and PR #19 description update.
- No quality-gate pass is claimed until the fresh blind cohort satisfies every per-output/per-dimension threshold and has no adjudicated major fidelity hard fail.
