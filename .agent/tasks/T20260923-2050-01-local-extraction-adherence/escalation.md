# Stage 04 Escalation — Clean-worktree Premise Invalidated

- TASK_ID: `T20260923-2050-01-local-extraction-adherence`
- CURRENT_PLAN_REVISION: `4`
- ROUTE: `Stage 01 ESCALATION_REPLAN`; if the revised contract changes runner/requiredness/closure semantics, require fresh Stage 02 review and Stage 03 handoff before a new Stage 04.

## Affected approved anchors

- `GOAL_ANCHOR.PRIMARY_OUTCOME` / independent E2E acceptance path.
- Plan §8 step 4 (`plan.md:253`): commit only product code + tests before E2E.
- Plan `FULL-SUITE`/E2E sequencing and Handoff `IMPLEMENTATION_WAVES` (`handoff.md:87-90`).
- Runner clean-worktree decision-validity gate (`scripts/e2e/run_owned_e2e.py:408-428,1888-1895`).
- No literal `REQ-*`, `DEC-*`, `WAVE-*`, or `H-*` identifiers are present in the approved plan/handoff; the cited section/anchor names are the affected identifiers.

## New fact and decisive evidence

- `[OBSERVED]` Command: `git status --porcelain=v1`
- `[OBSERVED]` Result: `?? .agent/tasks/T20260923-2050-01-local-extraction-adherence/`
- `[VERIFIED]` `check_clean_worktree` at `scripts/e2e/run_owned_e2e.py:421-428` filters nonblank porcelain lines and returns clean only when the count is zero.
- `[VERIFIED]` The non-smoke E2E path at `scripts/e2e/run_owned_e2e.py:1888-1895` fails closed on that result before backend startup.
- `[VERIFIED]` The plan requires a product-code+tests-only commit before E2E at `plan.md:253`; the task artifact directory is not product code or tests and remains untracked.

## Why the current Plan is invalid

The approved plan assumes that the E2E prerequisite can produce a zero-entry `git status --porcelain` while committing only product code and tests. In this worktree, the required Stage 04/plan artifacts themselves produce a non-empty porcelain entry. Therefore the prescribed commit cannot satisfy the runner's necessary clean-worktree predicate. This is a load-bearing sequencing/acceptance premise, not a mechanical product defect.

## Safe current repository state

- Branch remains `fix/qwen-local-quality-parity` at `ab2528b718e8c91557fd72db174b0f9bb78d3a68`.
- No product, test, runner, ignore/exclude, plan, handoff, or review files were changed.
- Only the Stage 04-owned `execution.md` and `escalation.md` artifacts were added.
- No full-suite baseline, backend run, model inference, or E2E was run.

## Exact missing decision for Stage 01

Persist one explicit, evidence-preserving policy for the pre-E2E clean-worktree boundary:

> **Must the pre-E2E clean HEAD include the current task's `.agent/tasks/<TASK_ID>/` artifacts (and, if so, which artifacts and at what append-only timing), or must the runner's clean-worktree contract be revised to permit task-artifact-only porcelain entries?**

The current plan chooses neither. Stage 04 must not choose between these alternatives, modify the runner, add ignore/exclude rules, or hide/move/delete task artifacts. After the decision, revise/review/regenerate the affected plan and handoff as required, then start a fresh Stage 04 preflight.

## Verification already run

- Handoff `READY_FOR_IMPLEMENTATION`, plan revision 4, plan SHA, and review attempt-04 SHA were checked.
- Branch, HEAD, and porcelain status were checked.
- Runner helper and fail-closed call site were inspected.
- No tests or product/runtime checks were run by instruction and because the load-bearing premise failed pre-mutation.

## Stage 04 rev6 escalation — CORE-2 all-controls-off rollback contradiction

- TASK_ID: T20260923-2050-01-local-extraction-adherence
- CURRENT_PLAN_REVISION: 6
- AFFECTED_GOAL_REQ_DEC_WAVE_IDS:
  - GOAL_ANCHOR.PRIMARY_OUTCOME and MUST_NOT_BREAK byte-level rollback
  - Plan §3 CORE-2 C2a/C2b/C2c
  - Plan §6 all-new-controls-off rollback
  - Plan §8.1 BYTE-ROLLBACK and LOCAL-CONTRACTS
  - Handoff CORE-2 wave and SEMANTIC_INVARIANTS

### New fact

The approved all-new-controls-off rollback list has no control for C2a fact-level coverage or C2c local adherence prompt behavior. The partial CORE-2 implementation allows fact coverage and adds a local per-item disposition block whenever local issues exist. With documented off/0 values, LOCAL_LLM_RECORD_COVERAGE_MODE remains enforce and the refinement prompt still changes, so the documented all-off state cannot be byte-identical to ab2528b/P7-B.

### Decisive evidence path/command/result

- [VERIFIED] Plan §6 requires every new control off/0 to return byte-level to ab2528b, but names no C2a/C2c control.
- [VERIFIED] backend/core/config.py:297-306 retains LOCAL_LLM_RECORD_COVERAGE_MODE default enforce and the existing categories default topic,decision,number,date; current C2 code allows fact as an additional category.
- [VERIFIED] backend/services/summarization.py:2638-2650 adds a local refinement disposition block whenever issues exist; no approved C2c off control exists.
- [VERIFIED] Command: git status --short --branch && git diff --stat. Result: partial product/test changes are present; no model/E2E process was started.
- [VERIFIED] Command: uv run --frozen pytest tests/test_t20260923_p7c_proper_noun_normalize.py -q. Result: 8 passed in 0.41s after CORE-3 registry/skip-log corrections.
- [VERIFIED] Command: uv run --frozen pytest tests/test_t20260923_p4a_record_coverage.py -q. Result: 35 passed in 0.43s; this does not validate the newly added C2 tests.

### Why current Plan/Goal/Semantic Contract is invalid

This is a load-bearing semantic contradiction between the approved rollback invariant and the C2 behavior. Existing mode=off is not the P7-B default and cannot substitute for a missing C2a/C2c off state. Choosing a new flag, changing defaults, or redefining mode=off would change prompt/output bytes, fallback semantics, or rollback authority and exceeds Stage 04 authority.

### Safe current repository/data state

- All current product/test working changes remain intact and uncommitted; no reset, deletion, or overwrite was performed.
- CORE-3 implementation and focused tests are present and tested.
- CORE-2 is partial WIP; newly added C2-specific tests were not run after the contradiction was identified.
- Authoritative baseline: DATA_DIR=/tmp/p7c-baseline-Z64k1x uv run --frozen pytest tests/ -q; exit 0; 1129 passed, 2 skipped in 10.46s. /tmp/test_scratch was not touched.
- No LM Studio/model inference, E2E, detached worktree, commit, or Stage 05 run occurred.

### Decision required

Stage 01 must revise and persist explicit C2a/C2c all-off/default semantics and prove every documented all-new-controls-off state restores P7-B/ab2528b prompt/output bytes. If the semantic rollback contract changes, obtain fresh Stage 02 review and Stage 03 handoff. Stage 04 must not invent a flag, repurpose mode=off, or continue CORE-2/E2E.

### Verification already run

- Rev6 startup plan/handoff/review hash and dirty-state preflight: verified.
- Authoritative safe pre-mutation FULL-SUITE baseline: pass as recorded above.
- CORE-3 focused/adjacent tests: pass; latest CORE-3 focused result 8 passed in 0.41s.
- Existing P4-A coverage contracts: 35 passed in 0.43s.
- New CORE-2 focused tests: not run.
- Model inference, E2E, commit, and Stage 05: not run.

ROUTE: Stage 01 ESCALATION_REPLAN; preserve current working changes and prior rev4 escalation.

## Stage 04 rev8 escalation — detached E2E missing the Apple ASR helper

- TASK_ID: `T20260923-2050-01-local-extraction-adherence`
- CURRENT_PLAN_REVISION: `8`
- AFFECTED_GOAL_REQ_DEC_WAVE_IDS:
  - `GOAL_ANCHOR.PRIMARY_OUTCOME` and `CRITICAL_PATH`
  - Plan §8.5 detached clean-worktree E2E procedure and fixed `GEMMA-E1` cache key
  - `CORE-A` through `CORE-F`, `E2E-COMMIT-PROVENANCE`, `STAGE05-INDEPENDENT`
  - Handoff `CRITICAL_PATH`, `SEMANTIC_INVARIANTS`, and E2E stop conditions

### New fact

The first planned Gemma E2E started the correct committed backend and observed the expected build revision, but the application task failed during Apple ASR helper resolution, before transcript creation and before the summarization/provider call. The detached checkout did not contain the ignored `apple_speech_cli/.build/release/apple-speech-cli` build artifact, and `apple-speech-cli` was not on `PATH`; the main checkout's ignored build artifact is not inherited by a detached worktree. `backend/services/task_processor.py` calls `transcribe_isolated_detailed` before `summarization_service.summarize`, confirming no LM Studio inference was reached. The loaded Gemma snapshot only proves availability, not a model test.

The runner also emitted a secondary failure-handler `NameError`: its non-completed-task branch calls `_write_transcript_and_docx`, which is not defined in `scripts/e2e/run_owned_e2e.py`. This did not cause the ASR failure, but the current Plan requires the runner to remain unchanged, so Stage 04 must not repair it without a revised Plan.

### Decisive evidence path/command/result

- `data/cache/e2e/p7c-gemma-e1/runner-output-raw/run_summary.json` (raw; ignored): `verdict=FAIL`; expected and actual revision equal the approved commit; elapsed `20.723` seconds; effective provider `lmstudio`; no successful task/inference metrics.
- `data/cache/e2e/p7c-gemma-e1/runner-output-raw/task_final.json` (raw; ignored): terminal status `failed` at the Apple ASR helper-check stage. Raw `error_message`, task payload, and any identifying fields were not copied into task evidence.
- `data/cache/e2e/p7c-gemma-e1/runner-output-raw/model_snapshot.json` (raw; ignored): exactly one loaded Gemma 4 31B instance; availability only.
- The registered derivative and hashes are in `e2e/attempt-01/result.md`; no transcript, DOCX, prompt, response, or raw error text is recorded there.
- Read-only prerequisite checks: the detached checkout's helper executable was absent; the main checkout's corresponding ignored build output was present; `command -v apple-speech-cli` returned no executable; Swift is available. Both run-specific raw directories are Git-ignored.
- Code-order evidence: `backend/services/task_processor.py` awaits `transcribe_isolated_detailed` before the later `summarization_service.summarize` call. Runner evidence: `scripts/e2e/run_owned_e2e.py:1582` invokes `_write_transcript_and_docx` on a failed task; `rg '^def _write_transcript_and_docx'` finds no definition.
- Provenance: detached `HEAD` equals `a576b06fc93c4a9d057ae59cdb54f07426ce343d`, porcelain is empty, registered input SHA matches, runner build revision matches. No product or runner files changed.

### Why current Plan / acceptance procedure is invalid

Plan §8.5 preserves a clean detached worktree and requires the original runner, but omits a required ignored runtime build artifact used by the app's ASR critical path. Consequently, a formally clean checkout cannot reach the LM Studio path as currently provisioned. The unique E1 cache path now contains preserved raw evidence and cannot be reused; the four valid model-quality samples therefore cannot be obtained under the current fixed paths without a revised retry/cache-key policy. The observed runner exception branch is a separate acceptance-harness defect whose repair/defer decision must also be explicit because Plan §8.5 requires the runner to remain unchanged.

### Safe current repository/data state

- Product/test commit remains `a576b06fc93c4a9d057ae59cdb54f07426ce343d`; main branch is one commit ahead of origin. No push occurred.
- Product implementation, tests, Plan revision 8, Review attempt-08, and Handoff are unchanged and hash-consistent. The main worktree's only porcelain entry is this task-artifact directory; the detached worktree is clean at the committed SHA.
- First E2E raw inputs/outputs remain in their verified ignored cache locations for any later read-only acceptance. No cleanup, overwrite, or migration occurred.
- No LM Studio inference occurred; no valid CORE model sample or quality metric exists. No further E2E was started.

### Decision required

Stage 01 must prepare a candidate revision and ask the user to approve a reproducible E2E recovery policy before any further model run:

1. Whether each detached worktree may build the repository-documented Apple helper (`swift build -c release --package-path apple_speech_cli`) as an ignored local preflight artifact, and what to do if build/package resolution is unavailable.
2. Which new unique cache key/alias replaces the failed `GEMMA-E1`, preserving its raw evidence and still obtaining two valid Gemma samples plus two valid Qwen 3.8 samples.
3. Whether the minimal runner failed-task error-path defect is fixed under a revised runner/test commit, or explicitly deferred while retaining raw task status as the source of failure detail. Stage 04 must not edit the runner before this decision.

The Qwen 3.6 variants remain excluded. No model inference, runner patch, helper build, cache cleanup, threshold change, push, or other E2E may occur before the revised Plan is accepted, reviewed, and handed off.

### Verification already run

- Current Plan SHA `8783d47192cb87886003561ca57f39064c133c69bbb620a4cf138f972d87b26c`, Review attempt-08 SHA `12e29036b0269d894be2bbbbd65d0aced722543e75f20349b8d0f6960c22cad4`, and Handoff SHA `01d24704b59451967ad7eeed1b3d4274fed07e78f0b6e7773c7a63ce05b21de7` were rechecked.
- `git status`/HEAD checks: committed detached SHA correct, detached porcelain empty; E1 output/runtime directories ignored.
- Input SHA comparison: matched preregistration. Loaded-model inventory: one Gemma 4 31B instance.
- Task-processor order and runner undefined failure-path call were inspected; no raw error payload was opened or copied.
- The approved full suite remains `1154 passed, 2 skipped`; no new tests were run because this escalation concerns the unplanned detached E2E prerequisite and retry procedure.

ROUTE: Stage 01 ESCALATION_REPLAN; preserve E1 raw cache and all prior planning/review/execution evidence.

## Stage 04 rev10 follow-up escalation — helper smoke-check premise is invalid

- TASK_ID: `T20260923-2050-01-local-extraction-adherence`
- CURRENT_PLAN_REVISION: `10`
- PLAN_SHA256: `0803089532765fd2f146bf89d6e3ce6854369e4ac69ebe0737c0b15b4ff0d06f`
- HANDOFF_SHA256: `e41f959946405759b5bec99e83d3aa353a5fae112504ca1c4eab8105bd4bf302`
- ROUTE: `Stage 01 ESCALATION_REPLAN`; if the revised helper preflight changes an acceptance gate, error interpretation, or evidence/privacy contract, require fresh Stage 02 review and Stage 03 handoff before a new Stage 04.

### Affected approved anchors

- `GOAL_ANCHOR.PRIMARY_OUTCOME` and the E2E critical path.
- `E2E-ASR-HELPER-PREFLIGHT` in the Plan acceptance contract.
- Plan §§0.7, 8, and 8.1, including the recovery/publish authority, detached E2E procedure, raw/derivative privacy boundary, and preflight stop rule.
- Handoff `CRITICAL_PATH`, `SEMANTIC_INVARIANTS`, `REVERIFY_ON_START`, `IMPLEMENTATION_WAVES.W0`, `ACCEPTANCE_CONTRACT`, and `STOP_AND_ESCALATE_IF`.
- Attempt-02’s `e2e/attempt-02/result.md` and the appended Stage04 rev10 record in `execution.md` remain historical evidence; their `BLOCKED` result is not retroactively relabeled.
- No literal `REQ-*`, `DEC-*`, `WAVE-*`, or `H-*` identifiers are present in the approved Plan/handoff; the named section/check/anchor identifiers above are the affected anchors.

### New fact

- `[CONFIRMED]` The release helper was built and present, but `apple-speech-cli --help` is not a supported command in the current committed CLI contract. `CLIArgumentParser.swift` accepts only the `probe` and `transcribe` subcommands; unknown subcommands/flags throw `AppleSpeechError(.inputError)`.
- `[VERIFIED]` `Errors.swift` maps `.inputError` to exit code `5`, and `Runner.run` catches parser errors and returns that code. Therefore the observed `--help` exit `5` is the expected unsupported-command response after the executable starts, not evidence of helper runtime failure.
- `[VERIFIED]` `apple-speech-cli probe --locale zh-TW` is the appropriate non-inference diagnostic candidate: `Runner.runProbe` calls `SpeechRuntime.localeReport`, which reads platform/locale/asset-inventory state and does not invoke `AssetInstallFlow`. `AssetInstallTests.swift::testProbePathPerformsNoAssetInstallation` asserts that probe does not access installation APIs.
- `[DECIDED FOR THIS STAGE04 STOP]` The probe was not run. Its JSON includes host metadata; if Stage01 approves it later, raw output must remain in a unique ignored cache and task evidence may contain only the approved allowlist derivative.

### Decisive evidence paths / commands / results

- Source paths: `apple_speech_cli/Sources/AppleSpeechKit/CLIArgumentParser.swift`, `apple_speech_cli/Sources/AppleSpeechKit/Errors.swift`, and the runner implementation containing `Runner.run`; static source inspection confirmed the parser, error mapping, and catch/return behavior described above.
- Attempt-02 evidence: `.agent/tasks/T20260923-2050-01-local-extraction-adherence/e2e/attempt-02/result.md`; recorded `swift build -c release --package-path apple_speech_cli` as `PASS`, helper presence as `YES`, ignored build output as `YES`, and helper `--help` as nonzero. No raw stdout/stderr is copied here.
- Stage04 execution evidence: `.agent/tasks/T20260923-2050-01-local-extraction-adherence/execution.md`, appended `Stage 04 rev10` record; it records zero provider calls, no model load, no E2E launch, and the historical preflight `BLOCKED` classification.
- Test/source evidence path: `apple_speech_cli/Tests/AppleSpeechKitTests/AssetInstallTests.swift`, test `testProbePathPerformsNoAssetInstallation`; this supports the candidate diagnostic’s non-installation property and is not a request to run it now.

### Why the current Plan / Goal / Semantic Contract is invalid

The approved `E2E-ASR-HELPER-PREFLIGHT` premise requires a successful helper `--help` smoke result and routes any nonzero result as an ASR runtime/preflight failure. The executable’s verified public CLI contract does not support `--help`; exit `5` is the stable input-error response for that unsupported command. Thus the smoke-check command cannot distinguish “helper starts and rejects an unsupported command” from the runtime failure class the gate intends to detect. Treating this result as helper runtime failure would incorrectly block the E2E path; treating it as success without a Plan decision would silently change a HARD_CLEAN gate and its failure semantics. This is a load-bearing acceptance/error-semantics issue, not a mechanical helper failure.

### Safe current repository / data state

- Product code, tests, Plan, handoff, review, and runner were not changed by this follow-up. The only intended write in this turn is this append-only escalation section.
- Attempt-02 remains historically recorded as `BLOCKED` under Plan revision 10; no retroactive relabeling is made.
- No LM Studio model was loaded, no provider inference occurred, no E2E was launched, and no new E2E raw cache was created or inspected.
- The parent repository’s worktree inventory did not show a newly registered worktree after the attempt. Worktree identity/provenance is therefore unresolved from this context; no new worktree identity is asserted and no worktree cleanup is performed.
- The fixed product/test commit, existing ignored artifacts, and all prior task evidence remain preserved. No raw output is exposed here.

### Exact decision required from Stage 01

Persist an explicit rev11 policy for `E2E-ASR-HELPER-PREFLIGHT` that:

1. replaces or supplements the unsupported `--help` smoke command with a supported, deterministic diagnostic such as `apple-speech-cli probe --locale zh-TW`, and defines the exact accepted exit/status semantics;
2. preserves the diagnostic’s non-inference and no-asset-installation properties, including whether host/locale/asset-inventory JSON is written to a unique ignored cache and exactly which redacted derivative may enter task evidence;
3. states whether the unsupported `--help` exit-5 observation is retained as diagnostic evidence only or remains part of any gate, without misclassifying it as helper runtime failure; and
4. states the provenance requirement for the detached worktree and how the preflight result is tied to the fixed product/test revision, without relying on an unverified worktree identity.

Stage04 must not run the probe, invent an exit-code waiver, modify the CLI/runner, alter the helper gate, inspect raw caches, or retry model E2E before the revised Plan is accepted. If this decision changes requiredness, gating, stable error semantics, privacy handling, or failure propagation, obtain fresh Stage02 review and Stage03 handoff before Stage04 resumes.

### Verification already run

- Rev10 Plan, review, snapshot, and Handoff hashes were checked against the supplied current identities.
- Swift release build: `PASS`.
- Release helper presence and ignored `.build/` output: `PASS`.
- Helper `--help`: exit `5`; source contract confirms this is the expected unsupported-command/input-error response.
- Parent branch/HEAD/porcelain inventory was checked; the task-artifact directory remains the observed untracked entry, with detached-worktree provenance unresolved as stated above.
- No model load, provider inference, E2E, probe, raw-cache inspection, or additional helper/runtime command was run in this follow-up.

ROUTE: `Stage 01 ESCALATION_REPLAN` → revise Plan rev11; if the revision changes the acceptance/error/privacy contract, `Stage 02 INDEPENDENT PLAN REVIEW` → `Stage 03 HANDOFF` → fresh `Stage 04`. Preserve attempt-02’s historical `BLOCKED` result and all prior escalation/execution evidence.
