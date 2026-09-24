# Stage 02 Independent Plan Review Report

## REVIEW_METADATA

- TASK_ID: `T20260923-2050-01-local-extraction-adherence`
- REVIEW_ATTEMPT: `attempt-11`
- REVIEWED_PLAN_REVISION: `11`
- REVIEWED_PLAN_SHA256: `1fedc179cb21b74618e342340781816e737eb36e020a34a699882a540e8f43f2`
- PLAN_SNAPSHOT_PATH: `.agent/tasks/T20260923-2050-01-local-extraction-adherence/review/attempt-11/plan_snapshot.md`
- SNAPSHOT_STATUS: exact byte-for-byte copy made before judgment
- REVIEW_SCOPE: read-only product/plan review; no probe, build, model load, E2E, Stage 05, commit, or push

## GOAL_BASELINE

- **PRIMARY_OUTCOME:** obtain four valid real local-model E2E meeting-record samples—Gemma 4 31B ×2 and Qwen 3.8 27B ×2—using the fixed audio fixture, `section_meeting`, and observe mode; compare local quality relative to Gemini without claiming parity.
- **SUCCESS_EVIDENCE:** each of the four samples reaches the real ASR → local generation → LM Studio inference → DOCX path, is valid under the existing quality measures, and is independently accepted by fresh Stage 05 evidence. Qwen 3.6 must never be tested.
- **MUST_NOT_BREAK:** fixed fixture/model scope and provenance, existing measurement definitions, prior quality gains, local/cloud isolation, privacy redaction, truthful PASS/FAIL/BLOCKED/NOT_RUN routing, and no push before the user’s stated post-Stage-05 condition is satisfied.
- **NON_GOALS:** parity claims, runner/product redesign outside the approved plan, new model downloads, Qwen 3.6, and immediate commit/push.
- **CRITICAL_PATH:** approved product/test revision → new detached clean worktree with in-context provenance → helper build and supported ASR preflight → four valid E2E samples → allowlisted evidence → independent Stage 05 acceptance.

## PREFLIGHT

- `[VERIFIED]` Plan status is `READY_FOR_REVIEW`; revision is 11; SHA matches the user-supplied expected SHA.
- `[VERIFIED]` No project-local `AGENTS.md` applies.
- `[VERIFIED]` Attempt-11 was the next unused review directory; the exact plan snapshot exists and matches the canonical plan SHA.
- `[VERIFIED]` Raw cache was not inspected.
- `[VERIFIED]` The latest redacted E2E result records zero provider/model inference for attempt-02; the latest escalation and execution history preserve that attempt as historical `BLOCKED` evidence.

## PASS A — TOP-DOWN GOAL ALIGNMENT AND DESIGN ECONOMY

### Intent and necessity

`[VERIFIED]` Plan §1 and the rev11 Owner/Debug Contract match the Goal Baseline. The four required samples, fixed input/template/mode, prohibited model, existing metrics, and non-parity comparison are still the primary outcome.

`[VERIFIED]` CORE-A–F and ANTI-GAMING directly establish valid quality/record evidence. Local contracts, byte rollback, provenance, and helper preflight protect decision validity or must-not-break invariants. S1–S5 and cross-run observations remain supporting/best-effort and are not substituted for the four core samples.

`[VERIFIED]` The plan’s sequence puts deterministic/offline checks and preflight before expensive E2E, while keeping the four Gemma/Qwen runs mandatory and supplemental S3/S5 resource-dependent.

### Gates, authority, and failure containment

`[VERIFIED]` `E2E-ASR-HELPER-PREFLIGHT` is supporting/diagnostic but its gate is proportionate: without a working helper and an installed usable locale, the application cannot reach ASR or local inference, so a model-quality result would be decision-invalid. Failure blocks only E2E/core acceptance and preserves implementation status.

`[VERIFIED]` The new locale-asset authority stop is not an unjustified global veto. The user authorized loading local models, while the transcribe path may install Apple system speech assets; the plan does not infer authorization for that separate host mutation. It records `AUTHORITY_REQUIRED`/scoped `BLOCKED`, does not load models, and does not call that condition a product-quality FAIL.

`[VERIFIED]` C1c/C2b budget failures are local to the affected summary; they do not become a global service veto. The plan explicitly preserves transcript-only degradation and rejects partial meeting records for acceptance.

`[VERIFIED]` The plan separates goal criticality from closure gating, records waiver fields, disallows self-waiver, preserves original check results, and defines the six orthogonal status fields and contradiction routes. No missing status, waiver, degradation, or decision-validity contract was found that would invalidate readiness.

### Rev10 finding RV-001

`[VERIFIED]` RV-001 is resolved. Rev11 §8.8 retains commit/push only as conditional post-Stage-05 scope: Stage 05 must pass, all required checks must be closure-satisfied, and no unresolved blocker may remain. It expressly withholds push before that point and disallows force-push/rebase/history rewrite. This matches the authoritative user brief and does not authorize a push now.

## PASS B — BOTTOM-UP ENGINEERING CONTRACT REVIEW

### CLI and ASR grounding

`[VERIFIED]` `apple_speech_cli/Sources/AppleSpeechKit/CLIArgumentParser.swift` accepts only `probe` and `transcribe`; unsupported `--help` is an input error. `Errors.swift` maps `APPLE_INPUT_ERROR` to exit 5. This confirms the rev10 classification correction and removes the invalid `--help` runtime-success premise.

`[VERIFIED]` `Runner.runProbe` calls `SpeechRuntime.localeReport`; the probe path does not call `AssetInstallFlow`. `SpeechRuntime` reports supported/installed locale and asset status, while `TranscriptionService` is the path that invokes asset readiness. The plan’s proposed probe is therefore a no-inference, no-installation diagnostic candidate, not a substitute for E2E.

`[VERIFIED]` Probe raw output is restricted to ignored cache, with task evidence limited to fixed booleans/enums/cache identity/hash. This is consistent with the source payload containing host metadata and locale lists and with the security/privacy requirement not to expose raw host data.

### Worktree and runner provenance

`[VERIFIED]` The runner’s clean gate counts every nonblank porcelain entry and executes before backend startup; `REPO_ROOT` is derived from the running script path. Rev11 therefore requires the same execution context to prove detached state, fixed HEAD, script-root match, and pre/post empty porcelain, rather than treating the parent repository’s worktree inventory as conclusive.

`[VERIFIED]` This is proportionate and grounded in the latest escalation: the parent inventory did not show the claimed newly created worktree, but the exact agent context is unobservable. Rev11 neither accepts the parent absence as proof of failure nor accepts the claim without in-context evidence. Missing proof blocks only affected E2E evidence.

### Verification and status routing

`[VERIFIED]` CORE-A–F, ANTI-GAMING, local contracts, byte rollback, platform independence, baseline-delta full suite, provenance, helper preflight, and Stage 05 each have explicit evidence roles, closure gates, baseline requirements, failure classifications, and no-waiver status. The plan preserves `BLOCKED`/`NOT_RUN` rather than converting preflight failure into model-quality failure or PASS.

`[VERIFIED]` Attempt-02 remains historical `BLOCKED`; the plan does not relabel it or count it as a Gemma sample. The four required valid samples remain `0/4` until actual E2E execution.

`[MINOR]` The plan calls the retained probe stdout/stderr material “raw JSON”; source shows stdout is the JSON payload while stderr is diagnostic text. The surrounding cache/evidence handling treats both as raw and allowlists only derivatives, so this wording does not change the gate or privacy behavior.

## FINDINGS

No unresolved `BLOCKER` or `MAJOR` findings.

## REQUIRED_PLAN_CHANGES

None.

## RESIDUAL_RISK

`[UNVERIFIED]` The probe has not been run, locale installation state is unknown, the helper has not been exercised with the supported diagnostic in this review, no model has been loaded, the four E2Es have not run, and Stage 05 has not accepted the result. These are later-stage evidence obligations, not claims of current success.

FINAL_STATUS: PLAN_APPROVED
NEXT_ACTION: Stage 03 handoff for Plan revision 11 and this exact SHA; do not probe, build, load models, run E2E, or push during review.
