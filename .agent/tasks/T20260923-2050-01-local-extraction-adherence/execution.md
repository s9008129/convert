# Stage 04 Execution Record — Preflight Only

## Identity

- TASK_ID: `T20260923-2050-01-local-extraction-adherence`
- PLAN_REVISION: `4`
- PLAN_SHA256: `355e0bf8fffc79fb4e8d4f973b48da2b594666bbff1a2e99db86c5425a12f920`
- HANDOFF: `.agent/tasks/T20260923-2050-01-local-extraction-adherence/handoff.md`
- HANDOFF_SHA256: `e9f12999fa519b991a54064f7e885f3d062ef1cbadbc502404384ffff26a996b`
- REVIEW: `.agent/tasks/T20260923-2050-01-local-extraction-adherence/review/attempt-04/review.md`
- REVIEWED_PLAN_REVISION: `4`
- REVIEWED_PLAN_SHA256: `355e0bf8fffc79fb4e8d4f973b48da2b594666bbff1a2e99db86c5425a12f920`
- PREFLIGHT_TIME: `2026-09-23 Asia/Taipei`

## Freshness and repository state

- `[VERIFIED]` Handoff status is `READY_FOR_IMPLEMENTATION`.
- `[VERIFIED]` Handoff revision/hash match `plan.md` and review attempt 04.
- `[VERIFIED]` `shasum -a 256 plan.md` and the attempt-04 plan snapshot both return `355e0bf8fffc79fb4e8d4f973b48da2b594666bbff1a2e99db86c5425a12f920`.
- `[VERIFIED]` Branch: `fix/qwen-local-quality-parity`.
- `[VERIFIED]` HEAD: `ab2528b718e8c91557fd72db174b0f9bb78d3a68`.
- `[OBSERVED]` `git status --porcelain=v1` returns exactly:

  ```text
  ?? .agent/tasks/T20260923-2050-01-local-extraction-adherence/
  ```

- Product implementation has not started. No product/test files were modified by this Stage 04 run.

## Decisive preflight finding

- `[VERIFIED]` `scripts/e2e/run_owned_e2e.py:408-418` obtains `git status --porcelain`.
- `[VERIFIED]` `scripts/e2e/run_owned_e2e.py:421-428` splits nonblank lines and returns `clean: len(entries) == 0`.
- `[VERIFIED]` `scripts/e2e/run_owned_e2e.py:1888-1895` invokes that helper for the non-smoke E2E preflight and fails closed when `clean` is false, before backend startup.
- `[VERIFIED]` Plan §8 step 4 (`plan.md:253`) requires implementation and focused tests to be committed **only as product code + tests** before E2E, because the runner is fail-closed on a dirty worktree.
- `[VERIFIED]` Handoff `IMPLEMENTATION_WAVES` (`handoff.md:87-90`) carries the same commit-before-E2E prerequisite.
- `[CONFIRMED]` The task artifact directory remains an untracked porcelain entry. A product-code+tests-only commit cannot make this worktree clean under the current runner predicate. Therefore the approved E2E path is impossible in the current worktree unless Stage 01 makes an explicit contract decision.

## Verification matrix snapshot

All checks remain unrun; no waiver is allowed or requested.

| CHECK_ID | CHECK_RESULT | WAIVER_STATUS | Evidence / scope |
|---|---|---|---|
| CORE-A, CORE-B, CORE-C, CORE-D, CORE-E, CORE-F | `NOT_RUN` | `NOT_ALLOWED` | No E2E/model/backend work permitted in preflight. |
| ANTI-GAMING, LOCAL-CONTRACTS, BYTE-ROLLBACK, PLATFORM-INDEPENDENCE | `NOT_RUN` | `NOT_ALLOWED` | No product/test mutation or focused checks run. |
| FULL-SUITE | `NOT_RUN` | `NOT_ALLOWED` | Required baseline was not started after the preflight stop. |
| STAGE05-INDEPENDENT | `NOT_RUN` | `NOT_ALLOWED` | Stage 05 not started. |
| STATUS-CONTRACT-FIXTURES | `NOT_RUN` | `NOT_ALLOWED` | No fixture execution in this preflight. |

## Orthogonal status

```text
PRIMARY_OUTCOME_STATUS: UNKNOWN
IMPLEMENTATION_STATUS: ESCALATED
CORE_ACCEPTANCE_STATUS: NOT_RUN
REQUIRED_VERIFICATION_STATUS: NOT_RUN
INDEPENDENT_ACCEPTANCE_STATUS: PENDING
TASK_CLOSURE_STATUS: REPLAN_REQUIRED
```

`IMPLEMENTATION_STATUS: ESCALATED` is the Stage 04 §7.7 route for an invalidated load-bearing plan premise; product implementation itself is **not started**, and this is **not** `IMPLEMENTATION_BLOCKED`. CORE acceptance is **not run**.

## Next action and residual risk

- `NEXT_ACTION`: Stage 01 escalation-replan must decide how task artifacts and the runner's whole-worktree porcelain-clean gate coexist before any product/test edits, baseline, backend, model, commit, or E2E work.
- Residual risk: until that decision is persisted, any purported E2E attempt will fail the runner's clean-worktree gate before backend startup, and changing the runner, ignore rules, or task-artifact location would bypass or alter the approved contract.

## Stage 04 rev6 — startup and authoritative pre-mutation baseline

- TASK_ID: `T20260923-2050-01-local-extraction-adherence`
- PLAN_REVISION: `6`
- PLAN_SHA256: `79a92f9ec0e71a031a04656adcb7a5f081ad99574fab4d1fb11334a97d883f72`
- HANDOFF: `.agent/tasks/T20260923-2050-01-local-extraction-adherence/handoff.md`
- HANDOFF_SHA256: `8e116b37d23824fd43e6c01b8224230f2e4e94915ce19b512282b221878726e2`
- REVIEW: `review/attempt-06/review_report.md`; approved plan SHA matches rev6.
- Branch/HEAD at startup: `fix/qwen-local-quality-parity` / `ab2528b718e8c91557fd72db174b0f9bb78d3a68`.
- `[VERIFIED]` Handoff status is `READY_FOR_IMPLEMENTATION`; plan, handoff, and approved review hashes match.
- `[VERIFIED]` Startup porcelain was only `?? .agent/tasks/T20260923-2050-01-local-extraction-adherence/`; no product/test edits existed.
- `[VERIFIED]` `/tmp/test_scratch` was inspected and preserved; it was not used or modified.
- `[VERIFIED]` Authoritative pre-mutation baseline: `DATA_DIR=/tmp/p7c-baseline-Z64k1x uv run --frozen pytest tests/ -q`.
- `[VERIFIED]` Baseline exit code `0`; output `1129 passed, 2 skipped in 10.46s`.
- `[VERIFIED]` Baseline ran before product/test edits; no LM Studio/model inference or E2E has run.

### Current orthogonal status at baseline boundary

```text
PRIMARY_OUTCOME_STATUS: UNKNOWN
IMPLEMENTATION_STATUS: IN_PROGRESS
CORE_ACCEPTANCE_STATUS: NOT_RUN
REQUIRED_VERIFICATION_STATUS: INCOMPLETE
INDEPENDENT_ACCEPTANCE_STATUS: PENDING
TASK_CLOSURE_STATUS: IN_PROGRESS
```

### FULL-SUITE post-change baseline delta

- `CHECK_ID: FULL-SUITE`; `GOAL_CRITICALITY: SUPPORTING`; `EVIDENCE_ROLE: REPOSITORY_HEALTH`; `CLOSURE_GATE: BASELINE_DELTA`; `BASELINE_REQUIRED: YES`; `WAIVER_ALLOWED: NO`; `WAIVER_AUTHORITY: NONE`; `WAIVER_STATUS: NOT_ALLOWED`.
- `[OBSERVED]` Exact command: `DATA_DIR=/tmp/p7c-post-full-jaa6Rx uv run --frozen pytest tests/ -q`; exit code `0`; summary `1153 passed, 2 skipped in 10.64s`.
- `[VERIFIED]` Compared with the valid pre-mutation command at pinned HEAD (`1129 passed, 2 skipped in 10.46s`), the post-change suite has no failures and the same two skips; pass count increased by 24. No new/worsened failure signature observed.
- `CHECK_RESULT: PASS` for the approved BASELINE_DELTA criterion (this is not a claim that the full suite has zero skips). No E2E/provider/model call occurred.
- Next: finish the approved static platform-independence and status-contract fixture checks, then update status/evidence before the product+tests-only commit gate.

### Verification matrix snapshot at baseline boundary

All checks retain `WAIVER_STATUS: NOT_ALLOWED`, `WAIVER_ALLOWED: NO`, and `WAIVER_AUTHORITY: NONE`.

| CHECK_ID | CHECK_RESULT | Evidence / scope |
|---|---|---|
| FULL-SUITE | PASS | Authoritative pre-mutation baseline above; post-change BASELINE_DELTA remains required. |
| CORE-A, CORE-B, CORE-C, CORE-D, CORE-E, CORE-F | NOT_RUN | E2E not started. |
| ANTI-GAMING, LOCAL-CONTRACTS, BYTE-ROLLBACK, PLATFORM-INDEPENDENCE | NOT_RUN | CORE implementation/focused validation not started. |
| STATUS-CONTRACT-FIXTURES | NOT_RUN | Stage 04 fixture evidence not yet recorded. |
| E2E-COMMIT-PROVENANCE, STAGE05-INDEPENDENT | NOT_RUN | E2E/Stage 05 not started. |

Next action: execute the approved CORE-3 deterministic zero-model-call implementation and focused contracts; preserve the prior rev4 escalation as historical evidence.

## Rev6 wave result — CORE-3 deterministic proper-noun normalization

- Wave: CORE-3; zero-model-call implementation and focused contracts.
- Product/test files changed: backend/core/text_postprocess.py, backend/services/summarization.py, backend/core/config.py, .env.example, and new tests/test_t20260923_p7c_proper_noun_normalize.py.
- [VERIFIED] New control defaults to False, runs only in the local finalize path, and the cloud path does not call it.
- [VERIFIED] Replacement candidates are transcript literals with same suffix/length, existing near-homophone validation, unique-candidate requirement, registry priority, and source-tag protection.
- [VERIFIED] Focused command: uv run --frozen pytest tests/test_t20260923_p7c_proper_noun_normalize.py -q; exit 0; 5 passed in 0.41s.
- [VERIFIED] Adjacent command: uv run --frozen pytest tests/test_t20260922_record_quality.py tests/test_platform_provider_routing.py tests/test_record_term_fixes.py -q; exit 0; 48 passed in 0.43s.
- [VERIFIED] git diff --check passed.
- [VERIFIED] No LM Studio/model inference or E2E has run.

### Wave matrix update

| CHECK_ID | CHECK_RESULT | Evidence / scope |
|---|---|---|
| LOCAL-CONTRACTS | NOT_RUN | CORE-3 slice passed focused contracts; full matrix remains pending CORE-2/CORE-1 contracts and E2E. |
| PLATFORM-INDEPENDENCE | PASS | Adjacent platform/provider tests passed; implementation adds no model/platform branch. |
| BYTE-ROLLBACK | NOT_RUN | Full all-controls-off comparison remains pending after all waves. |
| FULL-SUITE | PASS | Authoritative pre-mutation baseline; post-change full suite still required. |
| CORE-A, CORE-B, CORE-C, CORE-D, CORE-E, CORE-F, ANTI-GAMING | NOT_RUN | E2E not started. |

Current status remains:

PRIMARY_OUTCOME_STATUS: UNKNOWN
IMPLEMENTATION_STATUS: IN_PROGRESS
CORE_ACCEPTANCE_STATUS: NOT_RUN
REQUIRED_VERIFICATION_STATUS: INCOMPLETE
INDEPENDENT_ACCEPTANCE_STATUS: PENDING
TASK_CLOSURE_STATUS: IN_PROGRESS

Next action: implement CORE-2 local-only adherence/refinement controls and focused zero-model-call contracts.

## CORE-3 conformance correction

- [VERIFIED] Review identified two direct plan gaps: arbitrary transcript homophones were accepted when no registry candidate existed, and stable skip reasons were not emitted.
- [VERIFIED] Correction restricts replacement to registry candidates only; registry candidates take priority, multiple registry matches report registry_conflict, multiple non-registry homophones report multiple_candidates, and no homophone reports no_candidate.
- [VERIFIED] Focused command: uv run --frozen pytest tests/test_t20260923_p7c_proper_noun_normalize.py -q; exit 0; 7 passed in 0.41s.
- [VERIFIED] No model inference or E2E has run.

Current status remains:

PRIMARY_OUTCOME_STATUS: UNKNOWN
IMPLEMENTATION_STATUS: IN_PROGRESS
CORE_ACCEPTANCE_STATUS: NOT_RUN
REQUIRED_VERIFICATION_STATUS: INCOMPLETE
INDEPENDENT_ACCEPTANCE_STATUS: PENDING
TASK_CLOSURE_STATUS: IN_PROGRESS

Next action: implement CORE-2 C2a/C2b/C2c local-only adherence/refinement controls and zero-model-call contracts.

## Rev6 semantic escalation snapshot

- [VERIFIED] Stage 04 stopped before further CORE-2 tests, E2E, commit, or model inference because the approved all-new-controls-off byte rollback contract has no C2a/C2c control while current C2 WIP changes local coverage/prompt behavior.
- Escalation artifact: .agent/tasks/T20260923-2050-01-local-extraction-adherence/escalation.md, Stage 04 rev6 section.
- Current working changes are preserved; no reset, deletion, or overwrite was performed.

### Current six orthogonal statuses

PRIMARY_OUTCOME_STATUS: UNKNOWN
IMPLEMENTATION_STATUS: ESCALATED
CORE_ACCEPTANCE_STATUS: NOT_RUN
REQUIRED_VERIFICATION_STATUS: INCOMPLETE
INDEPENDENT_ACCEPTANCE_STATUS: PENDING
TASK_CLOSURE_STATUS: REPLAN_REQUIRED

### Named blocker

BLOCKERS:
  - id: BLK-REV6-C2-ALLOFF-ROLLBACK
    scope: IMPLEMENTATION
    subject: CORE-2 C2a/C2c all-new-controls-off rollback semantics
    result: BLOCKED
    class: PLAN_PREMISE_INVALID
    task_regression_evidence: UNKNOWN
    evidence: escalation.md Stage 04 rev6 section; Plan §6; backend/core/config.py coverage defaults; backend/services/summarization.py local refinement block
    next_action: Stage 01 revise and persist explicit C2a/C2c off/default semantics, then obtain required review and handoff
    owner: Stage 01 Planner
    waiver_allowed: NO

### Verification matrix at escalation boundary

All checks retain WAIVER_STATUS NOT_ALLOWED, WAIVER_ALLOWED NO, and WAIVER_AUTHORITY NONE.

| CHECK_ID | CHECK_RESULT | Evidence / scope |
|---|---|---|
| FULL-SUITE | PASS | Authoritative pre-mutation baseline only; post-change BASELINE_DELTA remains outstanding. |
| CORE-A, CORE-B, CORE-C, CORE-D, CORE-E, CORE-F | NOT_RUN | No E2E/model inference. |
| LOCAL-CONTRACTS | BLOCKED | C2 rollback contract cannot be concluded under current approved Plan; named blocker above. |
| BYTE-ROLLBACK | BLOCKED | All-off state is not decision-valid until C2a/C2c semantics are revised and reviewed. |
| PLATFORM-INDEPENDENCE | PASS | CORE-3 adjacent platform/provider validation passed; no model/platform branch added. |
| ANTI-GAMING, STATUS-CONTRACT-FIXTURES, E2E-COMMIT-PROVENANCE, STAGE05-INDEPENDENT | NOT_RUN | Not started. |

Next action: Stage 01 escalation-replan; stop this Stage 04 session.

## Stage 04 rev8 — resumed startup and baseline revalidation

- TASK_ID: `T20260923-2050-01-local-extraction-adherence`
- PLAN_REVISION: `8`
- PLAN_SHA256: `8783d47192cb87886003561ca57f39064c133c69bbb620a4cf138f972d87b26c`
- HANDOFF: `.agent/tasks/T20260923-2050-01-local-extraction-adherence/handoff.md`
- HANDOFF_SHA256: `01d24704b59451967ad7eeed1b3d4274fed07e78f0b6e7773c7a63ce05b21de7`
- REVIEW: `.agent/tasks/T20260923-2050-01-local-extraction-adherence/review/attempt-08/review_report.md`; `FINAL_STATUS: PLAN_APPROVED`, reviewed revision/hash match rev8.
- Resumed startup: `2026-09-23 Asia/Taipei`; branch `fix/qwen-local-quality-parity`; HEAD `ab2528b718e8c91557fd72db174b0f9bb78d3a68`.
- `[VERIFIED]` Recomputed Plan, handoff, and attempt-08 report hashes; exact Plan and handoff bindings remain current. Handoff status is `READY_FOR_IMPLEMENTATION`.
- `[VERIFIED]` The recorded pre-mutation baseline remains valid: at exact HEAD `ab2528b718e8c91557fd72db174b0f9bb78d3a68`, before product/test mutations, `DATA_DIR=/tmp/p7c-baseline-Z64k1x uv run --frozen pytest tests/ -q`, exit 0, `1129 passed, 2 skipped in 10.46s`. Reuse this baseline; no new full-suite baseline was started.
- `[VERIFIED]` Main worktree retains the approved task's product/test WIP (`.env.example`, `backend/core/config.py`, `backend/core/text_postprocess.py`, `backend/services/summarization.py`, and untracked P7-C tests/fixture) plus task artifacts. No reset, stash, cleanup, or unrelated-worktree operation was performed.
- `[VERIFIED]` The task-created detached baseline worktree is `/private/tmp/p7c-byte-baseline-root-ONmyDD/worktree`, HEAD exactly `ab2528b718e8c91557fd72db174b0f9bb78d3a68`; its only untracked file is the copied `tests/test_t20260923_p7c_byte_rollback.py`. Its `.venv` exists (reported approximately 734 MB); no related uv/pytest process was active at resume. Preserve this worktree and environment; do not touch `/private/tmp/baseline_hl`.
- `[VERIFIED]` No Stage 04 rev8 record had previously been appended. This entry is the startup/baseline record required before further product/test mutation.
- `[OBSERVED]` At the original Stage 04 startup, `tests/test_t20260923_p4a_record_coverage.py` was dirty with a small expected-metrics edit adding zero-valued `cov_expected_fact`/`cov_missing_fact` fields. During rev8 implementation that assertion was removed from the legacy all-off golden expectation to preserve the approved P7-B byte contract. Equivalent enabled-only fact metrics coverage has not yet been confirmed at this resume point; next action is to preserve the intent in the dedicated P7-C flag tests and verify it, without restoring the incompatible all-off metric bytes.
- `[VERIFIED]` Before the pause, focused tests `uv run --frozen pytest tests/test_t20260923_p7c_proper_noun_normalize.py tests/test_t20260923_p4a_record_coverage.py -q` passed (`48 passed`); `git diff --check` passed. These do not yet establish complete rev8 contracts or BYTE-ROLLBACK.
- `[VERIFIED]` No LM Studio inference or E2E has run. The first baseline rollback harness attempt in the pinned worktree completed environment setup but was interrupted before a capture result was observed; no fixture was produced there and no cleanup was performed.

### Resumed Stage 04 status at startup boundary

```text
PRIMARY_OUTCOME_STATUS: UNKNOWN
IMPLEMENTATION_STATUS: IN_PROGRESS
CORE_ACCEPTANCE_STATUS: NOT_RUN
REQUIRED_VERIFICATION_STATUS: INCOMPLETE
INDEPENDENT_ACCEPTANCE_STATUS: PENDING
TASK_CLOSURE_STATUS: IN_PROGRESS
```

Next action: complete the dedicated C2a/C2c toggle and synthetic legacy-issue/fact assertions (including exact metrics and actual pipeline-return bytes), then capture the pinned-base hash fixture and compare it against current source using the same zero-provider-call harness. Stage 05 remains unstarted.

### Focused rev8 rerun — before authenticated baseline capture

- `[VERIFIED]` Command: `DATA_DIR=/tmp/p7c-focused-rerun-lQoqYb uv run --frozen pytest tests/test_t20260923_p7c_byte_rollback.py tests/test_t20260923_p7c_local_controls.py tests/test_t20260923_p7c_proper_noun_normalize.py tests/test_t20260923_p4a_record_coverage.py -q`.
- `[OBSERVED]` Exit code `1`; summary `58 passed, 1 failed in 0.53s`. The sole failure was `test_byte_rollback_fixture_or_capture` at its all-off `baseline == expected["fields"]` comparison. The focused C2a/C2c toggle, C1c/C2b local-controls, P7-C proper-noun, and existing P4-A coverage tests passed in this run.
- `[VERIFIED]` The compared fixture at `tests/fixtures/p7c_byte_rollback_ab2528b.json` had SHA-256 `7e8aeb4e234df8efd632b05ae0eb48f05036ad7ff9360e1d8b47e54efff48380`. Its fields were from the earlier capture command executed with the main repository as CWD (rather than the detached pinned worktree): it lacks the now-required extraction prompt and actual-return hashes, contains the empty-issue hash and legacy `provider_calls` field, and is therefore not valid pinned-base evidence. It was not used to classify a product regression and will only be superseded after authentic capture from the pinned worktree.
- `BYTE-ROLLBACK`: `BLOCKED` pending valid pinned-base capture and comparison; waiver remains `NOT_ALLOWED` / `WAIVER_ALLOWED=NO` / `WAIVER_AUTHORITY=NONE`.
- `[VERIFIED]` No real local/cloud provider calls, model inference, or E2E occurred in the focused run.
- Next action: verify Python imports resolve inside `/private/tmp/p7c-byte-baseline-root-ONmyDD/worktree`, copy the current hash-only harness there, capture fixture bytes from HEAD `ab2528b718e8c91557fd72db174b0f9bb78d3a68` using a fresh task-specific `DATA_DIR`, verify only the intended untracked harness/fixture were produced and the fixture contains hashes only, then install those hashes at the planned main-tree fixture path and rerun the exact focused suite.

### Authenticated pinned-base BYTE-ROLLBACK capture

- `[VERIFIED]` Capture worktree: `/private/tmp/p7c-byte-baseline-root-ONmyDD/worktree`; `pwd` returned that exact path; `git rev-parse HEAD` returned `ab2528b718e8c91557fd72db174b0f9bb78d3a68`.
- `[VERIFIED]` Baseline import check: `uv run --frozen python -c 'import backend; print(backend.__file__)'` returned `/private/tmp/p7c-byte-baseline-root-ONmyDD/worktree/backend/__init__.py`.
- `[VERIFIED]` The copied rollback harness SHA-256 matched the current main-tree harness at capture: `4fd86e327bfafd3ef1aec11d6ecd3e83d8e605ecd942338456bc296161eb5623`.
- `[VERIFIED]` Exact capture command: `DATA_DIR=/tmp/p7c-byte-baseline-2shQRN P7C_BYTE_ROLLBACK_CAPTURE_BASELINE=1 uv run --frozen pytest tests/test_t20260923_p7c_byte_rollback.py -q`.
- `[OBSERVED]` Capture exit code `0`; output `2 passed, 2 skipped in 0.37s`. The skips are the current-only C2a/C2c toggle assertions because the pinned P7-B baseline has no such switches.
- `[VERIFIED]` Baseline hash fixture: `/private/tmp/p7c-byte-baseline-root-ONmyDD/worktree/tests/fixtures/p7c_byte_rollback_ab2528b.json`; SHA-256 `117914c3a7503e941ce6c977fe4430418916bf6fc9dc744ac1296a256b7c529d`. Its JSON contains the pinned commit, synthetic fixture ID, frozen all-off settings, SHA-256 fields, and provider/mock call counts only; `real_provider_calls=0`, `mocked_generation_boundary_calls=3`.
- `[VERIFIED]` The baseline checkout remained at the pinned HEAD with tracked tree unchanged. Its only untracked files were the intended copied `tests/test_t20260923_p7c_byte_rollback.py` and generated `tests/fixtures/p7c_byte_rollback_ab2528b.json`; runtime/log data used the fresh external `DATA_DIR` above. No provider, network, model inference, or E2E call occurred.
- The main-tree fixture observed before transfer had SHA-256 `7e8aeb4e234df8efd632b05ae0eb48f05036ad7ff9360e1d8b47e54efff48380`; as recorded above, that task-created file came from the earlier wrong-CWD capture and is not treated as baseline evidence. It is now eligible to be replaced by the authenticated fixture with SHA-256 `117914c3a7503e941ce6c977fe4430418916bf6fc9dc744ac1296a256b7c529d`.
- `BYTE-ROLLBACK` remains `NOT_RUN` for the current-source comparison pending transfer and focused verification; no waiver is allowed.

### Authenticated current-source comparison — refinement prompt byte mismatch

- `[OBSERVED]` After installing the authenticated pinned-base hash-only fixture (SHA-256 `117914c3a7503e941ce6c977fe4430418916bf6fc9dc744ac1296a256b7c529d`), ran: `DATA_DIR=/tmp/p7c-focused-current-9S99Fa uv run --frozen pytest tests/test_t20260923_p7c_byte_rollback.py tests/test_t20260923_p7c_local_controls.py tests/test_t20260923_p7c_proper_noun_normalize.py tests/test_t20260923_p4a_record_coverage.py -q`.
- `[OBSERVED]` Exit code `1`; summary `58 passed, 1 failed in 0.56s`. The sole failure was the all-off field-hash comparison in `test_byte_rollback_fixture_or_capture`; all focused toggle, local-control, proper-noun, and P4-A coverage contracts passed. The harness asserted zero mocked real-provider calls; no model/E2E ran.
- `[OBSERVED]` Exactly two of 16 expected fields differed: `local_refinement_user` actual `fb4f537675b1db127b73112a17ebd5633d3dd3c6ad2e83185695bbb117ba0005` vs baseline `558727cb286ce462554b458c132fcdf3d71abbdbee54f31678452a45006bca65`; `cloud_refinement_user` actual `92983749fba7989547cd080cf96561ca525c0c78e3401b22391296827974a109` vs baseline `f718f39593836c78cba46a59b80bb970b6e5f174eea4ae69500c58d89cce41f7`. The other 14 hashes matched.
- `[CONFIRMED]` The shared refinement template interpolated an empty `local_adherence_block` on its own line while C2c was off, adding a newline to both local and cloud refinement user messages. The approved minimal fix is to concatenate `issue_lines` and `local_adherence_block` in one interpolation, preserving the existing blank line before `目前版本` and the enabled block text.
- No source fix had been applied when this failure evidence was appended. Next: make only that formatting fix, then rerun the focused suite with a new task-specific `DATA_DIR`; BYTE-ROLLBACK remains pending until that run passes.

### Current-source BYTE-ROLLBACK and focused contracts after formatting fix

- `[VERIFIED]` Applied the approved one-line prompt interpolation change: `{issue_lines}{local_adherence_block}` now shares one line in the template, while the two-newline separator before `目前版本` remains unchanged. With C2c off this reproduces the pinned-base layout; with C2c on the block still renders.
- `[OBSERVED]` Exact command: `DATA_DIR=/tmp/p7c-focused-fixed-KBXYnJ uv run --frozen pytest tests/test_t20260923_p7c_byte_rollback.py tests/test_t20260923_p7c_local_controls.py tests/test_t20260923_p7c_proper_noun_normalize.py tests/test_t20260923_p4a_record_coverage.py -q`.
- `[OBSERVED]` Exit code `0`; summary `59 passed in 0.53s`. This includes exact all-off comparison against the authenticated pinned fixture, C2a/C2c toggles, cloud byte invariance under local flags, local-controls, proper-noun normalization, and P4-A coverage. The rollback harness observed `real_provider_calls=0`; no model/E2E ran.
- `[VERIFIED]` Fixture remained hash-only and unchanged at SHA-256 `117914c3a7503e941ce6c977fe4430418916bf6fc9dc744ac1296a256b7c529d`.
- `BYTE-ROLLBACK`: `PASS` for the focused synthetic baseline contract. Continue remaining approved deterministic verification before any LM Studio E2E.

### Stage 04 safe checkpoint — before post-change full-suite delta

- Timestamp: `2026-09-24 Asia/Taipei`.
- `[VERIFIED]` Last completed check: authenticated BYTE-ROLLBACK plus focused local contracts, exit `0`, `59 passed in 0.53s`; evidence and exact command are recorded above. No LM Studio, provider, model, or E2E run has started.
- `[VERIFIED]` No pytest process or task test command is active. Process inspection listed only PID `66666` running `uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`; it was left untouched.
- `[VERIFIED]` Fresh post-change suite DATA_DIR created: `/tmp/p7c-post-full-jaa6Rx`. Full suite has not started.
- Next approved check: `DATA_DIR=/tmp/p7c-post-full-jaa6Rx uv run --frozen pytest tests/ -q`; compare its observed failure signatures with the recorded pre-mutation baseline before classifying FULL-SUITE `BASELINE_DELTA`.
- Stop point: after that command exits, preserve its exact output and classify the delta; do not commit or begin any E2E until the remaining deterministic audits and implementation/status evidence are complete.

```text
PRIMARY_OUTCOME_STATUS: UNKNOWN
IMPLEMENTATION_STATUS: IN_PROGRESS
CORE_ACCEPTANCE_STATUS: NOT_RUN
REQUIRED_VERIFICATION_STATUS: INCOMPLETE
INDEPENDENT_ACCEPTANCE_STATUS: PENDING
TASK_CLOSURE_STATUS: IN_PROGRESS
```

## Stage 04 rev8 append-only correction — full-suite evidence placement

- `[VERIFIED]` The FULL-SUITE post-change evidence block above was accidentally inserted inside the historical rev6 section rather than appended after the current rev8 record. The earlier block is preserved unchanged as historical evidence; this end-of-record addendum establishes the correct chronology and current applicability.
- `PLAN_REVISION: 8`; current approved handoff/review hashes are recorded in the rev8 startup entry.
- `CHECK_ID: FULL-SUITE`; `GOAL_CRITICALITY: SUPPORTING`; `EVIDENCE_ROLE: REPOSITORY_HEALTH`; `CLOSURE_GATE: BASELINE_DELTA`; `BASELINE_REQUIRED: YES`; `FAILURE_CLASSIFICATION_RULE: no new or worsened failure signatures versus the complete pre-mutation baseline`; `WAIVER_ALLOWED: NO`; `WAIVER_AUTHORITY: NONE`; `WAIVER_STATUS: NOT_ALLOWED`.
- `[OBSERVED]` Exact command `DATA_DIR=/tmp/p7c-post-full-jaa6Rx uv run --frozen pytest tests/ -q` exited `0`: `1153 passed, 2 skipped in 10.64s`. The valid pre-mutation baseline at pinned HEAD exited `0`: `1129 passed, 2 skipped in 10.46s`; same two skips and no new/worsened failure signature.
- `CHECK_RESULT: PASS` for the approved BASELINE_DELTA criterion; disclose the two skips (not a zero-skip suite). This supporting repository-health result is not CORE model/E2E evidence. No provider, model, or E2E call occurred.
- No test was rerun for this evidence-placement correction. Next: complete PLATFORM-INDEPENDENCE and STATUS-CONTRACT-FIXTURES, then finish Stage 04 gates before product+tests-only commit and E2E.

## Stage 04 rev8 — deterministic audit results

### PLATFORM-INDEPENDENCE

- `CHECK_ID: PLATFORM-INDEPENDENCE`; `GOAL_CRITICALITY: CORE`; `EVIDENCE_ROLE: MUST_NOT_BREAK`; `CLOSURE_GATE: HARD_CLEAN`; `BASELINE_REQUIRED: NO`; failure rule: any platform or model-name branch in new logic is `TASK_REGRESSION`; `WAIVER_ALLOWED: NO`; `WAIVER_AUTHORITY: NONE`; `WAIVER_STATUS: NOT_ALLOWED`.
- `[OBSERVED]` Command: `DATA_DIR=/tmp/p7c-platform-20260924 uv run --frozen pytest tests/test_t20260923_p7b_generation_discipline.py::test_no_platform_or_model_branching_in_new_code -q`; exit `0`, `1 passed in 0.33s`.
- `[VERIFIED]` The static function audit covers the existing local prompt helpers plus newly added `SummarizationService._extract_notes_fact_items` and `normalize_local_proper_nouns`. A separate added-line scan of the product diff found no prohibited OS/platform or model-family tokens.
- `[UNVERIFIED]` Windows and Ollama physical execution was not performed; this static result does not claim cross-OS/device execution.
- `CHECK_RESULT: PASS` for the approved static/platform-independent-code criterion only.

### Final FULL-SUITE baseline delta

- `CHECK_ID: FULL-SUITE`; `GOAL_CRITICALITY: SUPPORTING`; `EVIDENCE_ROLE: REPOSITORY_HEALTH`; `CLOSURE_GATE: BASELINE_DELTA`; `BASELINE_REQUIRED: YES`; failure rule: no new/worsened signatures versus the complete pre-mutation baseline; `WAIVER_ALLOWED: NO`; `WAIVER_AUTHORITY: NONE`; `WAIVER_STATUS: NOT_ALLOWED`.
- `[OBSERVED]` After adding the required static audit targets, command `DATA_DIR=/tmp/p7c-post-final-20260924 uv run --frozen pytest tests/ -q` exited `0`: `1153 passed, 2 skipped in 10.60s`.
- `[VERIFIED]` Compared with the valid pre-mutation baseline (`1129 passed, 2 skipped in 10.46s`), there are still exactly two skips and no failing/new/worsened failure signature. The count of passed tests is 24 higher.
- `CHECK_RESULT: PASS` for `BASELINE_DELTA`; two skips remain disclosed, so this is not described as a zero-skip run.

### BYTE-ROLLBACK evidence artifact

- `CHECK_ID: BYTE-ROLLBACK`; `GOAL_CRITICALITY: CORE`; `EVIDENCE_ROLE: MUST_NOT_BREAK`; `CLOSURE_GATE: HARD_CLEAN`; `BASELINE_REQUIRED: YES`; failure rule: any byte hash mismatch is `TASK_REGRESSION`; `WAIVER_ALLOWED: NO`; `WAIVER_AUTHORITY: NONE`; `WAIVER_STATUS: NOT_ALLOWED`.
- `[VERIFIED]` Hash-only per-field expected/actual comparisons are recorded in `verification/byte-rollback.json` (SHA-256 `7a23553eb798094b5324a2a614cc3516242429001ad9eb4ded9fecab867752ab`). The authenticated baseline fixture remains SHA-256 `117914c3a7503e941ce6c977fe4430418916bf6fc9dc744ac1296a256b7c529d`.
- `[VERIFIED]` The comparison test asserts exact all-off field equality; the focused contract run was `59 passed`, and the final full-suite run including the byte harness passed. It observed `mocked_generation_boundary_calls=3` and `real_provider_calls=0`; no raw prompt, transcript, or record content is stored in the hash evidence.
- `CHECK_RESULT: PASS`.

### STATUS-CONTRACT-FIXTURES

- `CHECK_ID: STATUS-CONTRACT-FIXTURES`; `GOAL_CRITICALITY: SUPPORTING`; `EVIDENCE_ROLE: MUST_NOT_BREAK`; `CLOSURE_GATE: HARD_CLEAN`; `BASELINE_REQUIRED: NO`; failure rule: any route mismatch, contradiction accepted, or original result rewritten is `TASK_REGRESSION`; `WAIVER_ALLOWED: NO`; `WAIVER_AUTHORITY: NONE`; `WAIVER_STATUS: NOT_ALLOWED`.
- `[OBSERVED]` Deterministic inventory uniqueness assertion over Plan §8.2: `awk -F'`' '/^\\| `SCF-/ {id=$2; count++; if (seen[id]++) duplicate=1} END {if (count != 27 || duplicate) {printf "FAIL: fixtures=%d duplicate=%d\\n", count, duplicate; exit 1} printf "PASS: %d unique fixture IDs\\n", count}' .agent/tasks/T20260923-2050-01-local-extraction-adherence/plan.md`; result: `PASS: 27 unique fixture IDs`.
- `[VERIFIED]` Recomputed each listed expected route against the canonical `workflow-routing.md` §7.7–§7.10 rules. The table records each Plan inventory ID exactly once, keeps the synthetic authorized-waiver case separate from P7-C's non-waivable gates, and does not turn conditional/incomplete inputs into `DONE`.

| FIXTURE_ID | 固定輸入 → 預期路由 | 實際重算路由 | FIXTURE_RESULT | 依據 |
|---|---|---|---|---|
| `SCF-01-CANONICAL-INCIDENT` | implementation `COMPLETE`、CORE `PASS`、required verification `INCOMPLETE` → 保留 implementation/CORE，closure `PENDING_REQUIRED_VERIFICATION` | 相同 | `PASS` | §7.7 #9 |
| `SCF-02-IMPLEMENTATION-BLOCKED` | 實作未完成且不能在核准契約內安全續行 → implementation `BLOCKED`、closure `IMPLEMENTATION_BLOCKED`，blocker 必須具名 | 相同 | `PASS` | §7.2、§7.6、§7.7 #2 |
| `SCF-03-CORE-FAIL` | implementation 原 `COMPLETE`、CORE 有效 `FAIL` → implementation `IN_PROGRESS`、closure `FIX_REQUIRED`；CORE 直接否證主要結果時 primary=`NOT_ACHIEVED` | 相同 | `PASS` | §7.7 #4 |
| `SCF-04-CORE-BLOCKED` | implementation `COMPLETE`、必要 CORE 證據受具名 blocker 阻斷 → implementation 保持 `COMPLETE`、closure `CORE_ACCEPTANCE_BLOCKED` | 相同 | `PASS` | §7.7 #5 |
| `SCF-05-CORE-NOT-RUN` | implementation `COMPLETE`、必要 CORE 未跑 → CORE `NOT_RUN`、closure `PENDING_CORE_ACCEPTANCE` | 相同 | `PASS` | §7.7 #6 |
| `SCF-06-CORE-NOT-REQUIRED` | 子例 a：Plan 未提供 rationale → `ESCALATED`／`REPLAN_REQUIRED`；子例 b：有明確 rationale → `CORE=NOT_REQUIRED` 合法、繼續按其餘 closure 條件判定，不等同 `NOT_RUN` | 相同；子例 b 不從本 fixture 未提供的其他狀態臆造終態 | `PASS` | §7.1、§7.7 #7 |
| `SCF-07-PLAN-PREMISE-INVALID` | 新證據推翻核准的 load-bearing 前提 → implementation `ESCALATED`、closure `REPLAN_REQUIRED` | 相同 | `PASS` | §7.7 #1 |
| `SCF-08-BASELINE-UNAVAILABLE` | CORE `PASS`、所需 mutation 前全庫基線缺失／不可比 → 該 check `BLOCKED`、aggregate verification `INCOMPLETE`、closure `PENDING_REQUIRED_VERIFICATION`；保留 implementation/CORE | 相同；不猜測、不自我 waiver | `PASS` | §7.4、§7.7 #9 |
| `SCF-09-BASELINE-DELTA` | 僅有相同既有 failure、無新增／惡化 → 明列 `PRE_EXISTING_FAILURE`，BASELINE_DELTA check 可 `PASS`，仍披露既有失敗 | 相同；不稱整庫全綠 | `PASS` | §7.4 |
| `SCF-10-HARD-CLEAN-DEBT` | HARD_CLEAN check 有非本波既有 red → check 不得標 `PASS`，verification `INCOMPLETE`、closure `PENDING_REQUIRED_VERIFICATION`；保留 implementation/CORE | 相同 | `PASS` | §7.4、§7.7 #9 |
| `SCF-11-FORMAL-WAIVER` | 僅合成授權案例 → 唯一原 check `FAIL` 保留；有效 owner waiver 可 `APPROVED`，aggregate 僅在其他未過項均合規時為 `WAIVED`，再走獨立驗收 | 相同；不改寫原 `CHECK_RESULT`，不授權本任務豁免 | `PASS` | §7.5 |
| `SCF-12-UNAUTHORIZED-WAIVER` | P7-C `WAIVER_ALLOWED=NO`、代理自行批准 → `WAIVER_STATUS=NOT_ALLOWED`，保留原 check result，依原結果決定 closure | 相同 | `PASS` | §7.5、§7.7 |
| `SCF-13-INDEPENDENT-PENDING` | implementation、CORE、verification 均已閉合，Stage 05 尚未跑 → independent `PENDING`、closure `READY_FOR_INDEPENDENT_ACCEPTANCE`，非 DONE | 相同 | `PASS` | §7.7 #11 |
| `SCF-14-INDEPENDENT-ENV-BLOCK` | Stage 05 因具名環境／工具／輸入 blocker 無效 → independent `BLOCKED`、closure `ACCEPTANCE_BLOCKED`，保留 Stage 04 三欄快照及 SHA | 相同 | `PASS` | §7.8 #3 |
| `SCF-15-INDEPENDENT-PRODUCT-DEFECT` | Stage 05 證明核准契約內機械缺陷 → independent `FAIL`、implementation `IN_PROGRESS`、closure `FIX_REQUIRED`，不回寫 Stage 04 快照 | 相同 | `PASS` | §7.8 #2 |
| `SCF-16-CONTRADICTIONS` | `BLOCKED+D​ONE`、`COMPLETE+IMPLEMENTATION_BLOCKED`、`CORE=NOT_REQUIRED` 無 rationale → 三者皆拒絕非法終態；第三者 replan | 三組均未接受為合法終態 | `PASS` | §7.1、§7.7 #7、§7.10 |
| `SCF-17-LEGACY-WITH-EVIDENCE` | 舊 `IMPLEMENTATION_BLOCKED` 但證據證明實作/CORE 已完成、僅 verification blocker → implementation `COMPLETE`、closure `PENDING_REQUIRED_VERIFICATION`，標 `EVIDENCE_BACKED` 並留舊值 | 相同 | `PASS` | §7.12 |
| `SCF-18-LEGACY-WITHOUT-EVIDENCE` | 舊單一狀態無法證明 blocker scope → 保留原值、標未知／需補證，不可宣稱 DONE | 相同 | `PASS` | §7.12 |
| `SCF-19-DONE-PASS` | primary `ACHIEVED`、implementation `COMPLETE`、CORE/verification/independent 均滿足、無 hard blocker、diff/artifact freshness 有效 → closure `DONE` | 相同 | `PASS` | §7.10 |
| `SCF-DONE-01-PRIMARY` | primary `NOT_ACHIEVED` 或 `UNKNOWN` → 不得 `DONE` | 保留 outcome；不允許 DONE | `PASS` | §7.10 #1 |
| `SCF-DONE-02-IMPLEMENTATION` | implementation 非 `COMPLETE` → 不得 `DONE`；按 `IN_PROGRESS`、`BLOCKED`、`ESCALATED` 分別續行、`IMPLEMENTATION_BLOCKED`、`REPLAN_REQUIRED` | 相同 | `PASS` | §7.2、§7.7 #2–3 |
| `SCF-DONE-03-CORE` | CORE `FAIL/BLOCKED/NOT_RUN` 或無 rationale 的 `NOT_REQUIRED` → 分別 `FIX_REQUIRED/CORE_ACCEPTANCE_BLOCKED/PENDING_CORE_ACCEPTANCE/REPLAN_REQUIRED`，不得 DONE | 相同 | `PASS` | §7.7 #4–7 |
| `SCF-DONE-04-VERIFICATION` | required verification 未閉合且無有效 waiver → regression `FAIL` 走 `FIX_REQUIRED`；其他 unresolved/`NOT_RUN` 走 `INCOMPLETE`／`PENDING_REQUIRED_VERIFICATION`；不得 DONE | 相同 | `PASS` | §7.5、§7.7 #8–10、§7.9 |
| `SCF-DONE-05-INDEPENDENT` | 必要 independent 非 `PASS` → pending=`READY_FOR_INDEPENDENT_ACCEPTANCE`；defect=`FIX_REQUIRED`／`REPLAN_REQUIRED`；環境 blocker=`ACCEPTANCE_BLOCKED`；不得 DONE | 相同 | `PASS` | §7.8 |
| `SCF-DONE-06-BLOCKER` | 存在未解 hard blocker → 不得 DONE；保留 blocker scope、evidence、next action | 相同 | `PASS` | §7.6、§7.10 #6 |
| `SCF-DONE-07-DIFF` | final diff 超出核准範圍或丟失無關 user work → 不得 DONE；修正 scope 並保留無關工作 | 相同 | `PASS` | §7.10 #7 |
| `SCF-DONE-08-FRESHNESS` | 必要 artifact 缺失／rev/hash stale／Stage 05 未保存快照 → 不得 DONE；指出並補齊 freshness evidence | 相同 | `PASS` | §7.10 #8 |

- `CHECK_RESULT: PASS`。以上是依核准規則逐列確定性重算，不是產品功能測試；Stage 05 仍須 fresh-context 獨立重算。`SCF-11` 為合成一般語意，不變更本任務所有 check 不可 waiver 的決定。

### Stage 04 狀態快照與目前驗證矩陣

```text
PRIMARY_OUTCOME_STATUS: UNKNOWN
IMPLEMENTATION_STATUS: COMPLETE
CORE_ACCEPTANCE_STATUS: NOT_RUN
REQUIRED_VERIFICATION_STATUS: INCOMPLETE
INDEPENDENT_ACCEPTANCE_STATUS: PENDING
TASK_CLOSURE_STATUS: PENDING_CORE_ACCEPTANCE
```

| CHECK_ID | GOAL_CRITICALITY | EVIDENCE_ROLE | CLOSURE_GATE | BASELINE_REQUIRED | WAIVER_ALLOWED / AUTHORITY / STATUS | CHECK_RESULT | 範圍／證據 |
|---|---|---|---|---|---|---|---|
| LOCAL-CONTRACTS | CORE | MUST_NOT_BREAK | HARD_CLEAN | NO | NO / NONE / NOT_ALLOWED | PASS | focused 59 項；C1c/C2a/C2b/C2c、local/cloud isolation、post-process 等契約 |
| BYTE-ROLLBACK | CORE | MUST_NOT_BREAK | HARD_CLEAN | YES | NO / NONE / NOT_ALLOWED | PASS | authenticated pinned-base hash-only evidence，零真實 provider calls |
| PLATFORM-INDEPENDENCE | CORE | MUST_NOT_BREAK | HARD_CLEAN | NO | NO / NONE / NOT_ALLOWED | PASS | static function/test audit；Windows/Ollama 實機仍 `[UNVERIFIED]` |
| FULL-SUITE | SUPPORTING | REPOSITORY_HEALTH | BASELINE_DELTA | YES | NO / NONE / NOT_ALLOWED | PASS | pre-mutation 1129/2 skip；final 1153/2 skip，無新／惡化 failure |
| STATUS-CONTRACT-FIXTURES | SUPPORTING | MUST_NOT_BREAK | HARD_CLEAN | NO | NO / NONE / NOT_ALLOWED | PASS | 27 IDs unique；§7.7–§7.10 逐列重算 |
| CORE-A, CORE-B, CORE-C, CORE-D, CORE-E, CORE-F | CORE | OUTCOME | HARD_CLEAN | per Plan | NO / NONE / NOT_ALLOWED | NOT_RUN | 尚無四場有效 LM Studio E2E；模型品質、成本與 DOCX 尚未驗收 |
| ANTI-GAMING | CORE | OUTCOME | HARD_CLEAN | NO | NO / NONE / NOT_ALLOWED | NOT_RUN | 留待四場 E2E 檢查 checklist 洩漏與事實來源 |
| E2E-COMMIT-PROVENANCE | SUPPORTING | MUST_NOT_BREAK | HARD_CLEAN | NO | NO / NONE / NOT_ALLOWED | NOT_RUN | 尚未建立產品測試 commit 的乾淨 detached worktree/run artifacts |
| STAGE05-INDEPENDENT | CORE | OUTCOME | HARD_CLEAN | NO | NO / NONE / NOT_ALLOWED | NOT_RUN | fresh Stage 05 尚未開始 |

- `[VERIFIED]` 在 `implementation=COMPLETE` 且必要 CORE 尚未執行的目前邊界，依 §7.7 #6 closure 為 `PENDING_CORE_ACCEPTANCE`；`REQUIRED_VERIFICATION_STATUS` 保持 `INCOMPLETE`，未以 supporting 證據取代 CORE 結果。
- `[VERIFIED]` 此階段尚未呼叫 LM Studio／Ollama／雲端 provider，沒有模型推論或 E2E；四場計數仍為 `0/4`。

### Append-only transcription errata for the status-fixture inventory

- The uniqueness-command transcription above and the invisible separator in the displayed `SCF-16` token are formatting errors in this newly appended record, not changes to Plan IDs or status semantics. For clarity, `SCF-16`'s first contradiction is exactly `IMPLEMENTATION=BLOCKED + TASK_CLOSURE_STATUS=DONE`.
- `[OBSERVED]` The reproducible uniqueness assertion was rerun with an explicit filter for inventory rows (excluding the Plan's separate MAJOR-02 prose reference to `SCF-03`). Exact command:

  ```sh
  awk 'substr($0, 1, 2) == "| " && substr($0, 3, 1) == sprintf("%c", 96) && match($0, /SCF-[A-Z0-9-]+/) {id=substr($0, RSTART, RLENGTH); count++; if (seen[id]++) duplicate=1} END {if (count != 27 || duplicate) exit 1; print "PASS: " count " unique fixture IDs"}' .agent/tasks/T20260923-2050-01-local-extraction-adherence/plan.md
  ```

- Result: `PASS: 27 unique fixture IDs`. Use this corrected, table-scoped assertion as the authoritative uniqueness evidence; all 27 Plan §8.2 inventory IDs occur exactly once.

## Stage 04 rev8 — final pre-commit verification checkpoint

- `[OBSERVED]` Added task-processor regression test: `DATA_DIR=/tmp/p7c-taskprocessor-budget-20260924 uv run --frozen pytest tests/test_task_processor.py::test_extraction_call_budget_failure_returns_transcript_only -q`; exit `0`, `1 passed in 0.34s`. It verifies the approved C1c overflow exception reaches the existing failure-isolation path: `summary_failed=true`, the document is explicitly transcript-only, and no partial meeting record is presented.
- `[OBSERVED]` Final post-change full-suite command: `DATA_DIR=/tmp/p7c-post-final2-20260924 uv run --frozen pytest tests/ -q`; exit `0`, `1154 passed, 2 skipped in 10.54s`.
- `[VERIFIED]` The final suite includes the current product and test diff. Against the valid pre-mutation baseline (`1129 passed, 2 skipped`), it shows 25 additional passes, the same two skips, and no failing/new/worsened signature. `FULL-SUITE` remains `PASS` under `BASELINE_DELTA`; not zero-skip.
- `[VERIFIED]` Focused all-off byte rollback remains backed by `verification/byte-rollback.json`; the just-completed full suite reran that comparison and all zero-provider contracts successfully. The task-processor fallback test adds proof at the consumer boundary; no product behavior was changed in this last test-only wave.

### Current Stage 04 status and next approved action

```text
PRIMARY_OUTCOME_STATUS: UNKNOWN
IMPLEMENTATION_STATUS: COMPLETE
CORE_ACCEPTANCE_STATUS: NOT_RUN
REQUIRED_VERIFICATION_STATUS: INCOMPLETE
INDEPENDENT_ACCEPTANCE_STATUS: PENDING
TASK_CLOSURE_STATUS: PENDING_CORE_ACCEPTANCE
```

- `[VERIFIED]` Product implementation and deterministic contract tests are complete at this checkpoint. Core outcome is still unknown because none of the four required LM Studio model E2Es has run. Per workflow-routing §7.7 #6, closure remains `PENDING_CORE_ACCEPTANCE`; no E2E/model PASS is claimed.
- Next: review and stage only the approved product-code/test paths, commit those files without `.agent/tasks/` evidence, then use a clean detached worktree at that commit for the four required LM Studio runs. Keep raw runner/runtime content only in ignored cache and append only the Plan §8 allowlisted derivatives to task evidence. Push remains withheld until fresh Stage 05 acceptance and all required closure gates are satisfied.

## Stage 04 rev8 — first LM Studio E2E attempt and escalation

- `[OBSERVED]` GEMMA-E1 was invoked from the planned detached worktree at product/test commit `a576b06fc93c4a9d057ae59cdb54f07426ce343d`. Runner expected and actual build revisions match; the input SHA matches the preregistered input; the loaded-model snapshot contains exactly one Gemma 4 31B instance; both raw output directories are ignored; detached `HEAD` remained the planned commit and porcelain remained empty.
- `[CONFIRMED]` The application task failed in the Apple ASR helper-resolution stage before transcript creation. The same helper exists in the main working tree but is absent from the detached checkout's ignored `apple_speech_cli/.build/release/` output; `apple-speech-cli` is not on `PATH`. `backend/services/task_processor.py` awaits `transcribe_isolated_detailed` before it can call `summarization_service.summarize`, so provider inference, extraction, chunks, and refinement were all `0`. The Gemma instance was loaded/probed but did not receive an inference request.
- `[OBSERVED]` Runner exit code was `1`, with a secondary failure-handler `NameError`: `scripts/e2e/run_owned_e2e.py` calls `_write_transcript_and_docx` for a non-completed task, but no such definition exists. This runner defect did not cause the ASR failure; raw task error details remain only in ignored cache and were not copied here.
- `[VERIFIED]` The E2E invocation lasted `20.723` seconds. Its redacted derivative and runner-file SHA-256 values are appended in `e2e/attempt-01/result.md`; no model-quality metrics or fact IDs are available. This invocation is a failed attempt, not one of the four valid model samples.
- `[VERIFIED]` Existing product/test commit, Plan revision 8, approved Review, and Handoff are unchanged and hash-consistent. The detached worktree is clean. No product code, runner, ignore rule, or plan was modified; no retry, additional model inference, push, or Stage 05 acceptance was started.

### New evidence invalidating the approved E2E execution premise

Plan §8.5 requires the unchanged runner to launch from a clean detached worktree but does not establish/build the ignored Apple ASR helper required by the application in that worktree. The main checkout's prebuilt helper is not inherited. The fixed E1 cache key is now occupied by preserved raw failure evidence, so retrying at the same path would overwrite evidence and violate the unique-cache rule. The approved four-run schedule cannot be completed as written without a planned, unique replacement attempt and an explicit detached-worktree helper preflight/build decision. The runner's failure-handler defect is also newly observed; do not patch it or alter the runner contract in Stage 04.

```text
PRIMARY_OUTCOME_STATUS: UNKNOWN
IMPLEMENTATION_STATUS: ESCALATED
CORE_ACCEPTANCE_STATUS: BLOCKED
REQUIRED_VERIFICATION_STATUS: INCOMPLETE
INDEPENDENT_ACCEPTANCE_STATUS: PENDING
TASK_CLOSURE_STATUS: REPLAN_REQUIRED
NEXT_ACTION: Stage 01 ESCALATION_REPLAN; obtain approval of the revised E2E preflight/retry policy, then fresh Review/Handoff/Stage 04 as required.
```

```yaml
BLOCKERS:
  - id: E2E-ASR-HELPER
    scope: CORE_ACCEPTANCE
    subject: LM Studio model E2E samples
    result: BLOCKED
    class: ENVIRONMENT_FAILURE
    task_regression_evidence: NONE
    evidence: GEMMA-E1 task failed before ASR completion; detached checkout lacked the repo-built helper; provider inference count 0
    next_action: Stage 01 must decide a reproducible helper-build preflight and a new unique cache key for the failed E1 replacement
    owner: Planner / user approval
    waiver_allowed: NO
```

- `[VERIFIED]` Prior deterministic implementation tests and full-suite evidence remain valid and unchanged (`1154 passed, 2 skipped`). They do not substitute for CORE model acceptance. `IMPLEMENTATION_STATUS: ESCALATED` and `TASK_CLOSURE_STATUS: REPLAN_REQUIRED` follow workflow-routing §7.7 rule 1 because new evidence invalidates the approved E2E execution premise.

### Latest check-result snapshot (supersedes the pre-E1 matrix above)

| CHECK_ID | GOAL_CRITICALITY | EVIDENCE_ROLE | CLOSURE_GATE | BASELINE_REQUIRED | WAIVER_ALLOWED / AUTHORITY / STATUS | CHECK_RESULT | 範圍／證據 |
|---|---|---|---|---|---|---|---|
| LOCAL-CONTRACTS | CORE | MUST_NOT_BREAK | HARD_CLEAN | NO | NO / NONE / NOT_ALLOWED | PASS | 59 focused contracts plus task-processor budget fallback test |
| BYTE-ROLLBACK | CORE | MUST_NOT_BREAK | HARD_CLEAN | YES | NO / NONE / NOT_ALLOWED | PASS | pinned-baseline hash-only comparison; zero provider calls |
| PLATFORM-INDEPENDENCE | CORE | MUST_NOT_BREAK | HARD_CLEAN | NO | NO / NONE / NOT_ALLOWED | PASS | static audit; Windows/Ollama real-device path remains `[UNVERIFIED]` |
| FULL-SUITE | SUPPORTING | REPOSITORY_HEALTH | BASELINE_DELTA | YES | NO / NONE / NOT_ALLOWED | PASS | 1129 passed/2 skipped baseline vs 1154 passed/2 skipped final |
| STATUS-CONTRACT-FIXTURES | SUPPORTING | MUST_NOT_BREAK | HARD_CLEAN | NO | NO / NONE / NOT_ALLOWED | PASS | 27 unique fixture IDs, routes manually recomputed |
| CORE-A, CORE-B, CORE-C, CORE-D, CORE-E, CORE-F | CORE | OUTCOME | HARD_CLEAN | per Plan | NO / NONE / NOT_ALLOWED | BLOCKED | GEMMA-E1 stopped before ASR completion; no valid model inference, metrics, or DOCX; common detached-worktree helper prerequisite unresolved |
| ANTI-GAMING | CORE | OUTCOME | HARD_CLEAN | NO | NO / NONE / NOT_ALLOWED | BLOCKED | no model prompt/transcript was produced for inspection |
| E2E-COMMIT-PROVENANCE | SUPPORTING | MUST_NOT_BREAK | HARD_CLEAN | NO | NO / NONE / NOT_ALLOWED | PASS | GEMMA-E1 alone: expected commit/revision matched, detached porcelain empty, input hash matched, raw dirs ignored, derivative includes file hashes |
| STAGE05-INDEPENDENT | CORE | OUTCOME | HARD_CLEAN | NO | NO / NONE / NOT_ALLOWED | NOT_RUN | fresh independent acceptance has not started |

- `[VERIFIED]` This latest snapshot supersedes the earlier `NOT_RUN` values for E2E-dependent checks and the pre-E1 overall status. It does not promote the failed attempt into a valid model sample.
- Current orthogonal status remains: `PRIMARY_OUTCOME_STATUS: UNKNOWN`; `IMPLEMENTATION_STATUS: ESCALATED`; `CORE_ACCEPTANCE_STATUS: BLOCKED`; `REQUIRED_VERIFICATION_STATUS: INCOMPLETE`; `INDEPENDENT_ACCEPTANCE_STATUS: PENDING`; `TASK_CLOSURE_STATUS: REPLAN_REQUIRED`.

## Stage 04 rev10 — fresh LM Studio E2E attempt-02 helper preflight

- Timestamp: 2026-09-24 Asia/Taipei.
- TASK_ID: `T20260923-2050-01-local-extraction-adherence`
- PLAN_REVISION: `10`
- PLAN_SHA256: `0803089532765fd2f146bf89d6e3ce6854369e4ac69ebe0737c0b15b4ff0d06f`
- HANDOFF: `.agent/tasks/T20260923-2050-01-local-extraction-adherence/handoff.md`
- HANDOFF_SHA256: `e41f959946405759b5bec99e83d3aa353a5fae112504ca1c4eab8105bd4bf302`
- REVIEW: `attempt-10 PLAN_APPROVED`, matching Plan revision/hash.
- FIXED_PRODUCT_TEST_COMMIT: `a576b06fc93c4a9d057ae59cdb54f07426ce343d`
- MAIN_WORKTREE: branch/HEAD unchanged; only the pre-existing untracked task-artifact tree is present.
- DETACHED_WORKTREE: newly created unique worktree at fixed commit; old detached worktrees were not reused or cleaned.

### Commands and observed results

1. Freshness probes: Plan, snapshot, Review, and Handoff hashes matched the approved rev10 contract; snapshot bytes matched Plan bytes.
2. Detached clean-worktree creation: PASS; HEAD matched fixed commit; porcelain empty before build.
3. `swift build -c release --package-path apple_speech_cli`: PASS.
4. `.build/` ignore probe: PASS; build output ignored.
5. Release helper exists: PASS.
6. Release helper `--help`: nonzero exit, stable category `ASR_HELPER_SMOKE_RUNTIME_FAILURE`; therefore W0 preflight is BLOCKED.
7. No LM Studio model was loaded and no runner/provider inference was started. Provider inference calls: `0`.

### Stage 04 status snapshot

```text
PRIMARY_OUTCOME_STATUS: UNKNOWN
IMPLEMENTATION_STATUS: COMPLETE
CORE_ACCEPTANCE_STATUS: BLOCKED
REQUIRED_VERIFICATION_STATUS: INCOMPLETE
INDEPENDENT_ACCEPTANCE_STATUS: PENDING
TASK_CLOSURE_STATUS: CORE_ACCEPTANCE_BLOCKED
```

### Verification matrix for this attempt

| CHECK_ID | GOAL_CRITICALITY | EVIDENCE_ROLE | CLOSURE_GATE | WAIVER_ALLOWED | WAIVER_AUTHORITY | WAIVER_STATUS | CHECK_RESULT | Scoped evidence / next action |
|---|---|---|---|---|---|---|---|---|
| E2E-ASR-HELPER-PREFLIGHT | SUPPORTING | DIAGNOSTIC | HARD_CLEAN | NO | NONE | NOT_ALLOWED | BLOCKED | Build passed but helper smoke exited nonzero; replan helper prerequisite before model load. |
| CORE-A | CORE | OUTCOME | HARD_CLEAN | NO | NONE | NOT_ALLOWED | BLOCKED | No valid E2E samples; no model inference. |
| CORE-B | CORE | OUTCOME | HARD_CLEAN | NO | NONE | NOT_ALLOWED | BLOCKED | No valid Gemma records. |
| CORE-C | CORE | OUTCOME | HARD_CLEAN | NO | NONE | NOT_ALLOWED | NOT_RUN | Qwen runs stopped before start. |
| CORE-D | CORE | OUTCOME | HARD_CLEAN | NO | NONE | NOT_ALLOWED | NOT_RUN | Qwen runs stopped before start. |
| CORE-E | CORE | OUTCOME | HARD_CLEAN | NO | NONE | NOT_ALLOWED | BLOCKED | No valid run summaries or inference calls. |
| CORE-F | CORE | OUTCOME | HARD_CLEAN | NO | NONE | NOT_ALLOWED | NOT_RUN | No E2E output was created. |
| ANTI-GAMING | CORE | OUTCOME | HARD_CLEAN | NO | NONE | NOT_ALLOWED | NOT_RUN | No prompt/transcript was produced for this attempt. |
| LOCAL-CONTRACTS | CORE | MUST_NOT_BREAK | HARD_CLEAN | NO | NONE | NOT_ALLOWED | PASS | Fixed product/test commit; no product or runner changes. |
| BYTE-ROLLBACK | CORE | MUST_NOT_BREAK | HARD_CLEAN | NO | NONE | NOT_ALLOWED | PASS | Existing pinned hash-only evidence unchanged; no real provider calls. |
| PLATFORM-INDEPENDENCE | CORE | MUST_NOT_BREAK | HARD_CLEAN | NO | NONE | NOT_ALLOWED | PASS | No product changes in this attempt; Windows/Ollama remains unverified. |
| FULL-SUITE | SUPPORTING | REPOSITORY_HEALTH | BASELINE_DELTA | NO | NONE | NOT_ALLOWED | PASS | Existing baseline/final evidence unchanged; no product mutation. |
| STATUS-CONTRACT-FIXTURES | SUPPORTING | MUST_NOT_BREAK | HARD_CLEAN | NO | NONE | NOT_ALLOWED | PASS | Existing fixture evidence unchanged. |
| E2E-COMMIT-PROVENANCE | SUPPORTING | MUST_NOT_BREAK | HARD_CLEAN | NO | NONE | NOT_ALLOWED | PASS | New detached HEAD and porcelain gates passed; no runner launch. |
| STAGE05-INDEPENDENT | CORE | OUTCOME | HARD_CLEAN | NO | NONE | NOT_ALLOWED | NOT_RUN | Separate fresh Stage 05 remains pending valid E2E evidence. |

### Durable evidence and routing

- Redacted attempt evidence: `.agent/tasks/T20260923-2050-01-local-extraction-adherence/e2e/attempt-02/result.md`.
- Raw helper/build material remains outside task evidence; no E2E raw cache was created or exposed.
- The new detached worktree is preserved for diagnosis; no old detached worktree was reused or cleaned.
- No `escalation.md` was created: this is the approved scoped environment preflight blocker, with no product or semantic contract change.
- NEXT_ACTION: Stage 01/02/03 must replan and reapprove the helper smoke prerequisite before any model load or E2E retry; do not retry blindly.

## Stage 04 rev11 — attempt-03 W0 and CORE E2E start

- Timestamp: 2026-09-24 Asia/Taipei.
- TASK_ID: `T20260923-2050-01-local-extraction-adherence`
- PLAN_REVISION: `11`
- PLAN_SHA256: `1fedc179cb21b74618e342340781816e737eb36e020a34a699882a540e8f43f2`
- HANDOFF_SHA256: `aa114a9b769d91a80b4f90f9303f3874570656bdc3d1a3899428c5f04d9d2d2c`
- REVIEW: `attempt-11 PLAN_APPROVED`, matching Plan revision/hash.
- FIXED_PRODUCT_TEST_COMMIT: `a576b06fc93c4a9d057ae59cdb54f07426ce343d`
- MAIN_WORKTREE: pre-existing untracked task evidence only; preserved.
- NEW_DETACHED_WORKTREE: created for this attempt; detached/head/script-root/pre/post-build/pre-probe clean provenance booleans all true; absolute path intentionally omitted.

### W0 observed results

- Command class: `swift build -c release --package-path apple_speech_cli`; exit `0`.
- `apple-speech-cli` release helper present and executable; package `.build/` ignored.
- Fixed input SHA-256 matched Plan: `982151f4629ade0c38f164b57a2f105c1e305677e7e10e4dc0e252f1ac012828`.
- Fixed template/mode preconditions: `section_meeting` / `observe`.
- Cache key: `data/cache/e2e/p7c-asr-helper-probe-r11`; ignored: `true`.
- Supported read-only probe: `probe --locale zh-TW`; exit `0`.
- Allowlisted probe fields: `locale_supported=true`, `transcriber_is_available=true`, `locale_installed=true`, `asset_status=installed`.
- Raw probe hashes: stdout `e37e33c7691b80b6cfa65a0db516ef3a31cd7f2d2f63700833a7848b5f5a3be5`; stderr `08132a99a297f1df77f845b6834cbc6dffd6ad1a883f7abd1c6d3c8480ea692f`.
- W0 classification: `PASS`; no Apple system speech asset installation was requested or performed.

### Attempt-03 status snapshot at E2E start

```text
PRIMARY_OUTCOME_STATUS: UNKNOWN
IMPLEMENTATION_STATUS: COMPLETE
CORE_ACCEPTANCE_STATUS: NOT_RUN
REQUIRED_VERIFICATION_STATUS: INCOMPLETE
INDEPENDENT_ACCEPTANCE_STATUS: PENDING
TASK_CLOSURE_STATUS: PENDING_CORE_ACCEPTANCE
```

- Model precondition: existing LM Studio native inventory reported exactly one loaded approved model, `Gemma 4 31B` (`gemma-4-31b-it-mlx`); no Qwen 3.6 selected.
- No inference had started at the time of this snapshot; runner launch began only after the above preconditions and preregistration.
- Current action: `GEMMA-E1R` only, with all fixed Plan controls; raw runner/runtime remain in its unique ignored cache; stop on first failure per handoff.

## Stage 04 rev13 — fresh-session acknowledgement of historical attempt-03 terminal state

- Timestamp: 2026-09-24 Asia/Taipei.
- `[VERIFIED]` Current Plan revision 13 SHA-256 is `2b663c68a8f49d0cf769000db5d6d7629c54e589bff8e6c62a5168bc34fbe588`; the attempt-14 plan snapshot is byte-identical and its review reports `FINAL_STATUS: PLAN_APPROVED` for the same revision/SHA.
- `[VERIFIED]` Current handoff is `READY_FOR_IMPLEMENTATION`, revision 13, and links the same approved Plan SHA.
- `[ACKNOWLEDGED]` Historical attempt-03 terminal state is preserved as a blocked runner launch, not a quality result: runner exit `1`, `RUN_RESULT: BLOCKED`, `INFERENCE_REACHED: UNPROVEN`, zero runner/runtime artifacts, raw cache preserved, stop reason `runner_nonzero_or_exception`, and remaining runs `NOT_RUN`.
- `[VERIFIED]` Fresh-session branch/HEAD are `fix/qwen-local-quality-parity` / `a576b06fc93c4a9d057ae59cdb54f07426ce343d`; porcelain contains only the untracked task-artifact directory and no tracked product/test diff.
- `[DECIDED]` This acknowledgement does not reuse, score, overwrite, or reinterpret attempt-03 cache/evidence. The next action is the rev13 W0 freeze/provenance gate, with no candidate output generated or read before the task-scoped rubric is frozen and hashed.

## Stage 04 rev13 — W0 candidate precondition and C-R01 launch

- `[VERIFIED]` Frozen rubric artifact: `quality/rubric-v1.md`; canonical pre-self-field SHA-256 `c89621deb5a63ee6bafe5e5ff750d7565e8128ed3424e78d046fb403c022d27c`. Final artifact SHA-256 is recorded separately after this append-only record is closed.
- `[VERIFIED]` Canonical transcript SHA-256 `b7b9e5e05be5a560101312d9fb954d2e6aa10044febb8d3fca5a79f3931d9db0`; checklist SHA-256 `cf012d1f6983f67ecb47cc7a6486e48c110a6b2782ad94cccf0332a4ec6ec001`; template `section_meeting`; mode `cloud`; cloud model `gemini-3.5-flash-lite`; approved local model keys remain `gemma-4-31b-it-mlx` and `qwen3.8-27b-splash`.
- `[VERIFIED]` Candidate cache root `data/cache/e2e/p7c-candidate-v13/` and raw output subdirectory are gitignored and unique; no prior candidate path existed. Raw output, stdout/stderr, service logs, and runtime remain confined to that ignored cache.
- `[OBSERVED]` Run alias `C-R01` was launched with the fixed candidate profile and unique raw output path. At this record point the command is still running; provider-call/inference completion is not yet claimed. No raw output or log content was read or printed.
- `[OBSERVED]` `C-R01` completed with exit `0`; output SHA-256 `e1511ebcaaaced670b9ebe6c414d517bd530b637449ca47946de7c4d0262baca`; raw output size `6133` bytes. This is generation evidence only; no quality score or candidate gate is claimed.
- `[OBSERVED]` `C-R02` (Gemma local, model key `gemma-4-31b-it-mlx`) was launched with the fixed candidate profile and unique output path. It is currently running; no raw output/log content has been read or printed.
- `[OBSERVED]` `C-R02` completed with exit `0` after the LM Studio request returned; output SHA-256 `1b4d30946077b675f2f18198f033d88f1732ef8c90e386af3b9462790dfab1af`; raw output size `8326` bytes. This is generation evidence only; no quality score or candidate gate is claimed.
- `[VERIFIED]` Gemma was unloaded and Qwen `qwen3.8-27b-splash` loaded through the approved local model service; safe inventory showed exactly one loaded LLM, target Qwen present, Gemma absent, and only approved model families present.
- `[OBSERVED]` Run alias `C-R03` (Qwen local, model key `qwen3.8-27b-splash`) is the next and only active candidate request; no raw output/log content has been read or printed.
- `[OBSERVED]` `C-R03` terminated with nonzero exit `1`; no output file was produced. stdout/stderr remain raw in the unique ignored cache and were not read or printed. Provider inference completion and quality evidence are unproven; this run is not scored.
- `[DECIDED]` Per the approved stop condition, the incomplete candidate cohort is `CANDIDATE-PARITY: BLOCKED` and no further candidate alias, persistence, supporting E2E, or scoring wave is launched. Candidate outputs C-R01/C-R02 remain preserved as generation-only evidence and cannot substitute for the required 3x3.

### Rev13 candidate-wave terminal status

| CHECK_ID | GOAL_CRITICALITY | EVIDENCE_ROLE | CLOSURE_GATE | BASELINE_REQUIRED | FAILURE_CLASSIFICATION | WAIVER_ALLOWED | WAIVER_AUTHORITY | CHECK_RESULT | WAIVER_STATUS |
|---|---|---|---|---|---|---|---|---|---|
| RUBRIC-FREEZE | CORE | MUST_NOT_BREAK | HARD_CLEAN | NO | Missing/changed/unlinked freeze blocks conclusion | NO | NONE | PASS | NOT_ALLOWED |
| PARITY-PROVENANCE | CORE | MUST_NOT_BREAK | HARD_CLEAN | NO | Incomplete candidate identity/evidence blocks conclusion | NO | NONE | BLOCKED | NOT_ALLOWED |
| CANDIDATE-PARITY | CORE | OUTCOME | HARD_CLEAN | NO | Nonzero C-R03; incomplete 3x3, no valid candidate gate | NO | NONE | BLOCKED | NOT_ALLOWED |
| ANTI-GAMING | CORE | MUST_NOT_BREAK | HARD_CLEAN | NO | No complete anonymous scored cohort | NO | NONE | NOT_RUN | NOT_ALLOWED |
| PROFILE-PERSISTENCE | CORE | MUST_NOT_BREAK | HARD_CLEAN | NO | Conditional on candidate PASS; not entered | NO | NONE | NOT_RUN | NOT_ALLOWED |
| FINAL-PARITY | CORE | OUTCOME | HARD_CLEAN | NO | Conditional on persistence; not entered | NO | NONE | NOT_RUN | NOT_ALLOWED |
| LOCAL-CONTRACTS | SUPPORTING | MUST_NOT_BREAK | HARD_CLEAN | NO | No new persistence wave | NO | NONE | NOT_RUN | NOT_ALLOWED |
| FULL-SUITE | SUPPORTING | REPOSITORY_HEALTH | BASELINE_DELTA | YES | No post-mutation wave | YES | approved Plan authority only | NOT_RUN | NOT_REQUESTED |
| STAGE05-INDEPENDENT | CORE | OUTCOME | HARD_CLEAN | NO | Final cohort absent | NO | NONE | NOT_RUN | NOT_ALLOWED |

```text
PRIMARY_OUTCOME_STATUS: UNKNOWN
IMPLEMENTATION_STATUS: COMPLETE
CORE_ACCEPTANCE_STATUS: BLOCKED
REQUIRED_VERIFICATION_STATUS: INCOMPLETE
INDEPENDENT_ACCEPTANCE_STATUS: PENDING
TASK_CLOSURE_STATUS: CORE_ACCEPTANCE_BLOCKED
NEXT_ACTION: Stage 01/02/03 evidence-backed replan for the candidate C-R03 nonzero blocker; do not persist defaults or launch another candidate until a fresh approved contract exists.
```

- `[VERIFIED]` Frozen rubric final artifact SHA-256: `ecdf138bc3e957d0747ed3e95f87205be384c35959b716d1ea61cc3a419c64eb`; canonical pre-self-field hash remains `c89621deb5a63ee6bafe5e5ff750d7565e8128ed3424e78d046fb403c022d27c` as defined in the rubric metadata.

## Stage 04 rev14 — fresh continuation W0 and approved Qwen recovery launch

- `[VERIFIED]` Fresh handoff/plan/review freshness: Plan revision `14`, Plan SHA-256 `53ee307586a3569cc5e91eac9c48a973147058f02a105263de9791ae6efdae9f`, attempt-15 snapshot SHA-256 matches, review `FINAL_STATUS: PLAN_APPROVED`, handoff SHA-256 `c8426dd9f508270ea3eb0d9fd7659a2b0f6f5bdb99fc25a4237a592535bc9fc6` and `STATUS: READY_FOR_IMPLEMENTATION`.
- `[VERIFIED]` Branch/HEAD remain `fix/qwen-local-quality-parity` / `a576b06fc93c4a9d057ae59cdb54f07426ce343d`; tracked product/test tree remains clean and only the task artifact directory is untracked.
- `[VERIFIED]` Frozen canonical transcript/checklist identities remain SHA-256 `b7b9e5e05be5a560101312d9fb954d2e6aa10044febb8d3fca5a79f3931d9db0` / `cf012d1f6983f67ecb47cc7a6486e48c110a6b2782ad94cccf0332a4ec6ec001`; template `section_meeting`, mode `local`, approved model key `qwen3.8-27b-splash`, and frozen rubric final SHA-256 `ecdf138bc3e957d0747ed3e95f87205be384c35959b716d1ea61cc3a419c64eb`.
- `[VERIFIED]` LM Studio native API is reachable. Post-restart inventory initially had zero loaded LLMs; the exact approved Qwen `qwen3.8-27b-splash` was then loaded with 4-bit quantization and selected context length `65,536`. Current inventory has exactly one loaded LLM instance with that key/context; this is recorded as a precondition, not a quality result. No raw log or model output was read.
- `[VERIFIED]` Candidate profile was set only for this invocation: extraction ceiling `4500`, extraction call budget `4`, fact coverage/adherence enabled, local refinement rounds `3`, local refinement call budget `3`, proper-noun normalization disabled; request timeout remained `1800` seconds. No cloud/shared defaults were changed.
- `[OBSERVED]` New unique ignored recovery cache `data/cache/e2e/p7c-candidate-v14/` was created; old C-R01/C-R02/C-R03 caches remain untouched. The single permitted run `C-R03-recovery-01` is now launched; raw output/stdout/stderr remain confined to that cache and are not read or printed. Outer controller will wait for LM Studio response without an agent-side 30-minute cancellation.
- `[OBSERVED]` `C-R03-recovery-01` naturally returned exit `0` after approximately 23 minutes; output is non-empty, size `20,132` bytes, SHA-256 `ae710334095f7da4ed2c009d0d7ac884c2f394a7dd879f030398f6ca064e14e8`; exit marker is `0` and the cache is gitignored. This is the sole permitted recovery and is now eligible to map to anonymous candidate alias `C-R03` (Qwen run 1/3). Raw output and logs remain unread.
- `[VERIFIED]` Post-recovery inventory still has exactly one loaded LLM: `qwen3.8-27b-splash`, quantization `4` bits, context `65,536`; no model switch occurred during recovery.
- `[OBSERVED]` Per rev14, the next approved round-robin sample `C-R04` (Gemma local, same fixed transcript/template/profile) was launched in the same new cache. Its raw output/stdout/stderr remain confined to ignored storage and are not read or printed; the request is still active at this append.
- `[OBSERVED]` `C-R04` naturally returned exit `0`; output is non-empty, size `8,230` bytes, SHA-256 `b67c7b9df642757dab7753d609d2a10b59f8264006155eebb72e45a21786a005`; stderr size is `0` bytes and the output remains in ignored storage. This is generation evidence only; no scoring or raw-content read occurred.
- `[VERIFIED]` Post-run inventory showed exactly one loaded LLM, Gemma `gemma-4-31b-it-mlx`, 4-bit, context `71,936`; no provenance mismatch was observed for the approved Gemma candidate run. The next approved round-robin sample is Qwen `C-R05`.
- `[VERIFIED]` Before C-R05, Gemma was unloaded and inventory rechecked to exactly one loaded approved Qwen `qwen3.8-27b-splash`, 4-bit, context `65,536`; model-load response artifact was empty due the CLI request wrapper timing, but the read-only inventory is authoritative and matches the required precondition.
- `[OBSERVED]` `C-R05` (Qwen local) naturally returned exit `0`; output is non-empty, size `11,556` bytes, SHA-256 `cd3d29456275977282dca4ad85018bb42aa1bbd2d8d29648241cebb70010542e`; stderr size is `0` bytes and the output remains in ignored storage. This is generation evidence only; no scoring or raw-content read occurred.
- `[VERIFIED]` Post-run inventory remained exactly one loaded Qwen `qwen3.8-27b-splash`, 4-bit, context `65,536`. The next approved round-robin sample is cloud `C-R06`.
- `[OBSERVED]` `C-R06` (cloud Gemini 3.5 Flash-lite) naturally returned exit `0`; output is non-empty, size `6,293` bytes, SHA-256 `8a23d79913564152f0c0e2aba189ce0d224d48b4c27d9ab3be807ac2f9893c98`, and the output remains in ignored storage. This is generation evidence only; no scoring or raw-content read occurred.
- `[VERIFIED]` Cloud run did not alter local model inventory. The next approved round-robin sample is Gemma local `C-R07`.
- `[OBSERVED]` `C-R07` (Gemma local) naturally returned exit `0`; output is non-empty, size `8,289` bytes, SHA-256 `88f22d9ef084afd5fdeca7d6b65ab98e68e56097a1fd41023efa6df5a6ab868f`, and the output remains in ignored storage. This is generation evidence only; no scoring or raw-content read occurred.
- `[VERIFIED]` Post-run inventory remained exactly one loaded Gemma `gemma-4-31b-it-mlx`, 4-bit, context `71,936`. The next approved round-robin sample is Qwen local `C-R08`.
- `[OBSERVED]` `C-R08` (Qwen local) naturally returned exit `0`; output is non-empty, size `8,547` bytes, SHA-256 `fac12fb42ce55f63bef5bb322f977fdb52a06551bdd98edc51186e619aa43496`, and the output remains in ignored storage. This is generation evidence only; no scoring or raw-content read occurred.
- `[VERIFIED]` Post-run inventory remained exactly one loaded Qwen `qwen3.8-27b-splash`, 4-bit, context `65,536`. The next approved round-robin sample is cloud `C-R09`.
- `[OBSERVED]` `C-R09` (cloud Gemini 3.5 Flash-lite) naturally returned exit `0`; output is non-empty, size `6,865` bytes, SHA-256 `ffa23bbc87f4321cf6d1cd7f618a56ba16f3322de1e4993e71b1ecd3a9964afd`, and the output remains in ignored storage. This is generation evidence only; no scoring or raw-content read occurred.
- `[VERIFIED]` Candidate generation cohort is complete: recovery-mapped `C-R03`, plus valid `C-R04`–`C-R09`, with all nine generation exit markers `0`, output hashes/sizes recorded, fixed transcript/template/profile controls preserved, and no raw candidate content opened. Blind scoring and candidate gate have not run; no persistence or final cohort has started.

### Rev14 candidate-generation boundary status

```text
PRIMARY_OUTCOME_STATUS: UNKNOWN
IMPLEMENTATION_STATUS: COMPLETE
CORE_ACCEPTANCE_STATUS: NOT_RUN
REQUIRED_VERIFICATION_STATUS: INCOMPLETE
INDEPENDENT_ACCEPTANCE_STATUS: PENDING
TASK_CLOSURE_STATUS: PENDING_CORE_ACCEPTANCE
NEXT_ACTION: Fresh blind scoring of the complete anonymous candidate 3x3; continue to persistence only if the approved candidate gate passes.
```

## Stage 04 rev14 — candidate blind scoring terminal evidence

- `[VERIFIED]` Candidate scoring used the relative cache keys `p7c-candidate-v14/raw/blind-candidate-v1` and `p7c-candidate-v14/raw/candidate-parity-final`; no raw output, transcript, prompt, or private alias-to-source mapping was opened or copied into this artifact.
- `[VERIFIED]` Locked scorer artifacts (SHA-256): blind-A score sheet `4ea698ce0f6c427c1428319bf4ff9a75f328a9a06205aeced3ba2122b377051d`; blind-B score sheet `e3d4ab5ddc44b8266e6c4725aa3493ad2ac4d3f8b9fea0a4cbc87a4ee67f67e0`; blind-C score sheet `cfa0d17497dc28cbc7b70940320e7e47bf1f255d35baa22339ff776cf29496d3`; blind-A addendum `af16075c4b5f1e13e26247042467195de43633e26409cee4e3a71fbb1484395d`; blind-B addendum `36b369f29bd086e07c250fd5fbb662d05dd4d83db31430c81123c1bfcfdae231`.
- `[VERIFIED]` Audit artifacts: blind reconciliation SHA-256 `76963e2b7deb3ef4e8345c85d8942aeaa00d7078a2bd0fe56b688304e401593b`; candidate parity audit SHA-256 `5c6a727ddc8e115d126ac09127a855ea6051d3e198ad1cb07746b65392ed53ec`.
- `[PASS]` Input/rubric provenance: rubric `ecdf138bc3e957d0747ed3e95f87205be384c35959b716d1ea61cc3a419c64eb`, canonical transcript `b7b9e5e05be5a560101312d9fb954d2e6aa10044febb8d3fca5a79f3931d9db0`, and checklist `cf012d1f6983f67ecb47cc7a6486e48c110a6b2782ad94cccf0332a4ec6ec001` matched expected values across all locked sheets/addenda. All 9/9 anonymous aliases and all 28 core-fact IDs were covered by all three score sheets; addenda were structurally adequate.

### Alias-coded consensus medians and strict-gap observations

Scores are consensus medians in the frozen dimension order `completeness / faithfulness / traceability / usability`; gaps are `max(0, 1 - local/cloud-median)` and remain unrounded in the audit. No source identity mapping is included.

| Alias | Median scores | Gaps | Majority hard fail |
|---|---|---|---|
| C-R01 | 83.9286 / 88.8889 / 92.0635 / 90 | 0 / 1.0101% / 1.9324% / 0 | NO |
| C-R02 | 98.2143 / 84.1379 / 89.6552 / 60 | 0 / 6.3009% / 4.4978% / 29.4118% | YES |
| C-R03 | 94.6429 / 85.8824 / 89.3204 / 70 | 0 / 4.3583% / 4.8544% / 17.6471% | YES |
| C-R04 | 96.4286 / 86.5672 / 91.0448 / 90 | 0 / 3.5957% / 3.0175% / 0 | YES |
| C-R05 | 73.2143 / 91.6667 / 94.4444 / 85 | 12.7659% / 0 / 0 / 0 | NO |
| C-R06 | 83.9286 / 88.4615 / 96.1538 / 90 | ~0 / 1.4860% / 0 / 0 | NO |
| C-R07 | 89.2857 / 89.7959 / 93.8776 / 80 | 0 / 0 / 0 / 5.8824% | NO |
| C-R08 | 98.2143 / 84.7059 / 89.4118 / 85 | 0 / 5.6684% / 4.7570% / 0 | NO |
| C-R09 | 98.2143 / 91.5663 / 95.1807 / 90 | 0 / 0 / 0 / 0 | NO |

- `[FAIL]` Candidate check: model-level candidate gate `FAIL` for both approved local model groups. Decisive alias-coded evidence includes usability gaps at C-R02 (`29.4118%`) and C-R03 (`17.6471%`), each with majority hard fail `YES`; C-R04 also has majority hard fail `YES`. The candidate 3x3 is a profile go/no-go gate only and is not the final primary parity outcome.
- `[BLOCKED]` Reconciliation residuals are scoped separately from the adverse gate: claim-level crosswalk status remained `BLOCKED` for all 9 aliases because complete reliable three-way claim alignment was unavailable; unresolved core-fact ties remain only as IDs for C-R01 (`F048`, `F060`), C-R05 (`F025`, `F044`, `F045`, `F048`, `F060`), C-R06 (`F060`, `F061`, `F066`), and C-R07 (`F048`, `F066`). These unresolved details do not overturn the candidate `FAIL`.
- `[DECIDED]` Per the approved Plan, candidate failure prohibits profile persistence, final 3x3 generation, supporting audio-to-DOCX E2Es, and Stage 05 in this wave. A fresh Stage 01/02/03 replan is required; no product settings or tracked product files were changed.

### Rev14 candidate-scoring terminal status

```text
PRIMARY_OUTCOME_STATUS: UNKNOWN
IMPLEMENTATION_STATUS: ESCALATED
CORE_ACCEPTANCE_STATUS: NOT_RUN
REQUIRED_VERIFICATION_STATUS: INCOMPLETE
INDEPENDENT_ACCEPTANCE_STATUS: PENDING
TASK_CLOSURE_STATUS: REPLAN_REQUIRED
NEXT_ACTION: Fresh Stage 01/02/03 evidence-backed replan for the candidate parity FAIL; do not persist defaults or launch final/E2E waves.
```
