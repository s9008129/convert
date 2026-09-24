# Stage 04 Execution — Issue #18 Local V2

TASK_ID: T20260924-1523-01-issue18-local-fidelity
PLAN_REVISION: 4
PLAN_SHA256: 72d23f2facf0a88b12ec2f18a6850db011a2ff0dd9e15cefa1037bc230220c89
HANDOFF: `.agent/tasks/T20260924-1523-01-issue18-local-fidelity/handoff.md` (READY_FOR_IMPLEMENTATION)

## Waves

- W0: complete. Branch/HEAD and safety backups verified. Native JSON-schema support and active model/evaluator inventory are unavailable in this environment; strict JSON + Pydantic is retained as the prescribed compatibility path.
- W1: complete. Added typed evidence/fact/ledger/conflict/section/snapshot/profile contracts and synthetic A–I tests.
- W2–W6: implemented as pure deterministic primitives plus an explicit opt-in live V2 extraction/render path. Exactly one schema-only repair is attempted; failure raises `LocalPipelineV2Error` and never falls through to V1. The source-grounded fidelity firewall is wired before assembly and guarded patch results roll back to accepted bytes.
- W7–W8: runtime-dependent local model/profile and frozen blind evaluator gates remain pending; no model or evaluator was available in this environment.
- W9: this redacted execution record is complete; PR update/push is owned by the parent delivery role.

## Orthogonal status

PRIMARY_OUTCOME_STATUS: UNKNOWN
IMPLEMENTATION_STATUS: COMPLETE
CORE_ACCEPTANCE_STATUS: BLOCKED
REQUIRED_VERIFICATION_STATUS: INCOMPLETE
INDEPENDENT_ACCEPTANCE_STATUS: PENDING
TASK_CLOSURE_STATUS: PENDING_REQUIRED_VERIFICATION

## Verification matrix

| Check | Result | Evidence |
|---|---|---|
| C1 selected causal source→facts→render→delivery | NOT_RUN | Requires live local model/selected fixture |
| C2 synthetic A–I and contract suite | PASS | `DATA_DIR=/tmp/meetingscribe-test uv run pytest -q tests/test_local_pipeline_v2.py`: 9 passed |
| C3 cloud focused contract | PASS under safe env; default env BLOCKED | Default collection fails at `/app/data/logs`; writable `DATA_DIR` gives 13 passed, 41 deselected; see `baseline/cloud-contract-focused.txt` |
| C4 privacy/tracked artifacts | PASS (redacted artifacts) | New diagnostics store hashes/counts only; raw text is runtime-only |
| C5 focused/full integration | PASS | `DATA_DIR=/tmp/meetingscribe-test uv run pytest tests/ -q`: 826 passed, 2 skipped |
| C6 full repository | PASS under safe env | Same full-suite command/result |
| C7 docs | PASS with 2 pre-existing version warnings | `bash scripts/check_docs.sh` |
| C8 diff check | PASS | `git diff --check` |
| C9 Gemma/Qwen E2E | BLOCKED environment | No active local model/backend available |
| C10 blind 3+3 | BLOCKED quality acceptance | Frozen evaluator/unrounded Gemini baseline unavailable |
| C11 runtime metrics | NOT_RUN | Runtime unavailable |
| C12 held-out | NOT_RUN | No privacy-safe held-out source supplied |
| C13 execution/docs | PASS for this artifact | This redacted record |
| C14 repeated profiles | BLOCKED environment | No active models |

Every matrix item remains `WAIVER_STATUS: NOT_ALLOWED`; no waiver was self-approved.

## Changes

- Added `backend/services/local_pipeline_v2.py` with immutable evidence, typed claims, deterministic consolidation/conflicts, section plan/render/assembly, quality snapshots, guarded rollback, model-independent policy/runtime profile, and strict JSON validation.
- Added `LOCAL_PIPELINE_VERSION` (`v1` default; explicit `v2` only) and live V2 dispatch in `SummarizationService`; V2 failures never silently fall back.
- Added privacy-safe synthetic A–I coverage in `tests/test_local_pipeline_v2.py`.
- Cloud path was not modified.

## Blockers and next action

- BLK-ENV-LOG: scope `REQUIRED_VERIFICATION`, default pytest collection; class `ENVIRONMENT_FAILURE`; evidence is the `/app/data/logs` read-only failure; next action is to run in a writable runtime or inject a writable `DATA_DIR` in the external runner.
- BLK-QUALITY-EVAL: scope `INDEPENDENT_ACCEPTANCE`, frozen blind quality gate; class `ENVIRONMENT_FAILURE`; evaluator and original unrounded baseline are absent; next action is to run the mandated evaluator/cohort externally.
- BLK-MODEL: scope `CORE_ACCEPTANCE`, fresh local E2E/profile gates; class `ENVIRONMENT_FAILURE`; no Gemma/Qwen loaded instance is available; next action is to run against the active LM Studio backend.

Current product implementation is complete within approved scope; closure remains pending required verification and independent acceptance.

---

## Stage 04 R9 Fresh Implementer Update (2026-09-24T12:57Z onward)

TASK_ID: T20260924-1523-01-issue18-local-fidelity
PLAN_REVISION: 9
PLAN_SHA256: `63b30bcae58abbba98e15a9d3b62ef23da391cbcbded19d6e22e494b29f1ba67`
HANDOFF: `.agent/tasks/T20260924-1523-01-issue18-local-fidelity/handoff.md` (`READY_FOR_IMPLEMENTATION`)
REVIEW: `review/attempt-08/review_report.md` (matching revision/hash)

### W0 recheck

- Branch `issue-18-first-divergence-diagnostic`; HEAD `eb3ca049cc72d21d2f4db974db5314b5f399d736` unchanged at start.
- All dirty paths matched the handoff-listed Stage 04 candidate or task evidence/artifact classes; no unclassified owner path was found. No reset, stash, clean, or overwrite was performed.
- New safety ref created: `backup/issue-18-stage04-20260924-1257` at the starting HEAD.
- Cloud focused baseline: default environment collection is blocked by read-only `/app/data/logs` (exit 2); writable process-scoped `DATA_DIR` baseline is 13 passed, 41 deselected (exit 0), recorded in `baseline/cloud-contract-focused.txt`.
- LM Studio probes to loopback `/v1/models` and `/api/v0/models` found no active endpoint. Gemma/Qwen loaded-instance evidence is therefore unavailable in this environment.
- The adjacent rubric/cache is not Issue18-linked and has no frozen evaluator executable or original unrounded Gemini baseline. C10/C14 retain the exact blocker `QUALITY_ACCEPTANCE_BLOCKED_BY_MISSING_FROZEN_EVALUATOR`; rounded/adjacent scores were not substituted.

### Core implementation wave

- Added the exact live Stage05 C1 inversion regression through `SummarizationService._summarize_with_local_pipeline_v2`. Before the repair it **failed as expected**: the inverted predicate was accepted because the firewall skipped relation checks when the opaque claim ID was absent from prose.
- Repaired the approved live-boundary contract: relation checks no longer depend on claim-ID prose membership; the selected asserted causal/conditional claim is wired from the live ledger into the firewall and must have its predicate supported by both raw evidence and rendered relation metadata.
- After repair, the same live inversion probe rejected with `LocalPipelineV2Error` as required.
- Focused V2/cloud selection: **24 passed, 40 deselected**.
- Full suite in writable process-scoped environment: **827 passed, 2 skipped**.
- `bash scripts/check_docs.sh`: exit 0 with the two pre-existing version warnings for README files.
- `git diff --check`: pass.
- Cloud behavior remains on the separate path; no cloud implementation edits were made in this wave.

### Current verification matrix

| Check | Result | Evidence |
|---|---|---|
| C1 live selected-claim inversion gate | PASS after fail-first | focused live regression in `tests/test_local_pipeline_v2.py` |
| C2 synthetic A–I/live contract | PASS | focused run; full suite includes 827 passed |
| C3 cloud focused contract | PASS in writable env; default collection BLOCKED | `baseline/cloud-contract-focused.txt` |
| C4 privacy/tracked artifacts | PASS for new redacted diagnostics | runtime raw text remains untracked/local; no raw payload added by this wave |
| C5 focused/full integration | PASS | focused and full suite results above |
| C6 full repository | PASS in writable env | 827 passed, 2 skipped |
| C7 docs | PASS with pre-existing warnings | `bash scripts/check_docs.sh` |
| C8 diff check | PASS | `git diff --check` |
| C9 Gemma/Qwen E2E | BLOCKED (ENVIRONMENT) | no active LM Studio endpoint/model |
| C10 blind 3+3 | BLOCKED (AUTHORITY) | `QUALITY_ACCEPTANCE_BLOCKED_BY_MISSING_FROZEN_EVALUATOR` |
| C11 runtime metrics | NOT_RUN | runtime unavailable |
| C12 held-out | NOT_RUN | no newly approved privacy-safe source |
| C13 execution/docs | PASS | this redacted update |
| C14 repeated profiles | BLOCKED (ENVIRONMENT/AUTHORITY) | model/evaluator prerequisites unavailable |

### Orthogonal status and routing

PRIMARY_OUTCOME_STATUS: UNKNOWN
IMPLEMENTATION_STATUS: COMPLETE
CORE_ACCEPTANCE_STATUS: BLOCKED
REQUIRED_VERIFICATION_STATUS: INCOMPLETE
INDEPENDENT_ACCEPTANCE_STATUS: PENDING
TASK_CLOSURE_STATUS: CORE_ACCEPTANCE_BLOCKED
NEXT_ACTION: Stage 05 runs independent C1/C9/C10/C14 acceptance when the active Gemma/Qwen runtime and frozen evaluator/unrounded baseline are supplied; preserve this Stage 04 snapshot if those scoped blockers persist.

No waiver was applied. C9/C10/C14 remain system-level acceptance/closure evidence and were not used as per-record or per-section vetoes. Parent delivery role owns the eventual atomic commit/push and Draft PR #19 update.

## Stage 04 R9 repair update — fresh implementation after Stage05 attempt03

TASK_ID: T20260924-1523-01-issue18-local-fidelity
PLAN_REVISION: 9
PLAN_SHA256: `63b30bcae58abbba98e15a9d3b62ef23da391cbcbded19d6e22e494b29f1ba67`
HANDOFF: `.agent/tasks/T20260924-1523-01-issue18-local-fidelity/handoff.md` (`READY_FOR_IMPLEMENTATION`)
STARTING_HEAD: `eb3ca049cc72d21d2f4db974db5314b5f399d736`
W0_EVIDENCE: `baseline/w0-stage04-repair-20260924T131402Z.txt`

### Repair scope completed

- W4/R5: template-derived section plans now assign claims/evidence in production order, and each planned section receives exactly one model render call with a strict JSON envelope carrying claim IDs and relation metadata outside prose.
- W5/R6: source-backed firewall now checks entity, numeric/unit, date, attribution, relation, and evidence source tags against ordered raw evidence; cross-section duplicate and template-term diagnostic helpers are available.
- W6/R7: each section candidate is compared against a source-backed deterministic baseline through guarded byte-preserving rollback; accepted/rolled-back patch events are recorded using safe metadata only.
- W7/R8: runtime profile candidates are explicit for Qwen/Gemma families, active capability validation reports unsupported controls, and profile sample summaries report count/median/worst/range/hard-fail count.
- R9/R10: section planning, render envelope, rollback, capability, and profile-summary tests added; diagnostics record section input/validation/patch status without raw payloads.

### Verification actually run

- `python3 -m py_compile backend/services/local_pipeline_v2.py backend/services/summarization.py`: PASS.
- `DATA_DIR=$(mktemp -d /tmp/meetingscribe-pytest-log.XXXXXX) uv run pytest -q tests/test_local_pipeline_v2.py`: PASS, 12 passed.
- `DATA_DIR=$(mktemp -d /tmp/meetingscribe-pytest-log.XXXXXX) uv run pytest -q tests/test_summarization_service.py -k "cloud_pipeline or cloud_generation or validate_cloud or cloud_finalize or gemini_chat"`: PASS, 13 passed, 41 deselected.
- `DATA_DIR=$(mktemp -d /tmp/meetingscribe-pytest-log.XXXXXX) uv run pytest tests/ -q`: PASS, 829 passed, 2 skipped.
- `bash scripts/check_docs.sh`: PASS (exit 0; two pre-existing README version warnings).
- `git diff --check`: pre-existing failure remains limited to trailing whitespace in the prior historical execution section; no product whitespace error observed.

### Current matrix and routing

| Check | Result | Evidence / scope |
|---|---|---|
| C1 live selected-claim inversion | PASS | Prior fail-first live gate remains; repaired section envelope and relation metadata are now live-wired |
| C2 A-I plus extraction→schema→alignment→section render→firewall | PASS | 12 focused tests and full suite |
| C3 cloud contract | PASS | 13 focused tests in writable process-scoped DATA_DIR |
| C4 privacy | PASS | W0 and diagnostics are redacted; no raw payload tracked |
| C5 focused integration | PASS | 12 V2 tests; full suite 829 passed |
| C6 full suite | PASS | 829 passed, 2 skipped |
| C7 docs | NOT_RUN | Run by parent acceptance/delivery role |
| C8 diff check | BLOCKED by historical artifact whitespace | Existing execution lines only; preserved as immutable history |
| C9 Gemma/Qwen fresh E2E | BLOCKED ENVIRONMENT | LM Studio lists models but loaded instances are empty; no load/cleanup attempted |
| C10 blind 3+3 | BLOCKED AUTHORITY | `QUALITY_ACCEPTANCE_BLOCKED_BY_MISSING_FROZEN_EVALUATOR`; no substitute used |
| C11 runtime metrics | NOT_RUN | No loaded model |
| C12 held-out | NOT_RUN | No approved privacy-safe source |
| C13 execution/docs | IN PROGRESS | This append is durable; docs/PR remain parent-owned |
| C14 repeated profiles | BLOCKED ENVIRONMENT/AUTHORITY | Same C9/C10 blockers; no fabricated samples |

PRIMARY_OUTCOME_STATUS: UNKNOWN
IMPLEMENTATION_STATUS: COMPLETE
CORE_ACCEPTANCE_STATUS: BLOCKED
REQUIRED_VERIFICATION_STATUS: INCOMPLETE
INDEPENDENT_ACCEPTANCE_STATUS: PENDING
TASK_CLOSURE_STATUS: CORE_ACCEPTANCE_BLOCKED
NEXT_ACTION: Stage05 attempt04 must independently rerun C1/C2 and acceptance checks; retain scoped C9/C10/C14 environment/authority blockers and run docs/privacy/PR delivery checks.

## Stage 04 R9 repair update — live-contract follow-up

This append preserves all earlier Stage04 and Stage05 status/history. No plan or handoff file was changed.

### Approved-scope repairs

- Extraction JSON now explicitly requests relation direction, polarity, condition/dependency, number/unit, date, attribution, uncertainty, status, and evidence references, with unsupported values represented as explicit null or unknown/ambiguous status.
- `validate_asserted_claims_against_source` rejects asserted high-risk values absent from the ordered immutable raw evidence before they become required section claims.
- `validate_relation_metadata` is a core firewall function. Every required causal/conditional claim must have external metadata keyed by the exact claim ID and containing the source-supported predicate; missing, unknown-ID, or wrong-predicate metadata is rejected.
- Every V2 generation call receives the validated runtime profile. LM Studio's current adapter only proves native temperature/max-token support; context/thinking/top-p/top-k are explicitly recorded unsupported and are not marked validated or transmitted as controls. The profile event records `validated` versus `unsupported_controls`.
- Template-derived per-section calls remain one-call-per-section, and each candidate is evaluated against the deterministic source-backed baseline with guarded rollback before final firewall acceptance.

### Follow-up verification actually run

- `python3 -m py_compile backend/services/local_pipeline_v2.py backend/services/summarization.py`: PASS.
- `DATA_DIR=$(mktemp -d /tmp/meetingscribe-pytest-log.XXXXXX) uv run pytest -q tests/test_local_pipeline_v2.py`: PASS, 14 passed.
- `DATA_DIR=$(mktemp -d /tmp/meetingscribe-pytest-log.XXXXXX) uv run pytest -q tests/test_summarization_service.py -k "cloud_pipeline or cloud_generation or validate_cloud or cloud_finalize or gemini_chat"`: PASS, 13 passed, 41 deselected.
- `DATA_DIR=$(mktemp -d /tmp/meetingscribe-pytest-log.XXXXXX) uv run pytest tests/ -q`: PASS, 831 passed, 2 skipped.
- C9/C10/C14 were not rerun or altered; no model loading/cleanup was attempted.

PRIMARY_OUTCOME_STATUS: UNKNOWN
IMPLEMENTATION_STATUS: COMPLETE
CORE_ACCEPTANCE_STATUS: BLOCKED
REQUIRED_VERIFICATION_STATUS: INCOMPLETE
INDEPENDENT_ACCEPTANCE_STATUS: PENDING
TASK_CLOSURE_STATUS: CORE_ACCEPTANCE_BLOCKED
NEXT_ACTION: Fresh Stage05 attempt04 should exercise the live extraction/source-grounding and relation-metadata rejection paths, then retain the existing scoped C9/C10/C14 blockers.

## Stage 04 R9 repair update — after Stage05 attempt04

Date: 2026-09-25. This append supersedes implementation/verification claims above only where explicitly restated; earlier attempt status remains historical. Plan/handoff stayed unchanged and still match Plan R9 SHA-256 `63b30bcae58abbba98e15a9d3b62ef23da391cbcbded19d6e22e494b29f1ba67` and handoff SHA-256 `78ffbdec979529e0e1648054cda32abe86cc94f596d1ecdd08a763d23d0beb71`.

### Approved-scope completion

- Preserved the original ASR transcript in `TaskProcessor` before semantic correction and passed it as an optional argument through `summarize` to V2 only. V1/cloud still consume the same corrected transcript as before. Because no verified corrected-to-raw aligner exists, V2 deliberately extracts raw-only and records that the corrected view was supplied but not mapped; evidence hashes and checks are raw-source based.
- Replaced required-pattern-derived section labels with a complete ordered mapping from `MeetingTemplate.record_header_fields` followed by `record_sections` and nested `subfields`. Header labels use explicit template-id slots; fallback derives labels from formatter-owned skeleton lines, never regex guesses. Claims route once using explicit header semantics and raw-evidence template section/subfield patterns; unmatched claims route to the first body section, not every section.
- Relation claims carry structured subject/predicate/object/type/direction/polarity/condition metadata outside prose. Extraction validates evidence-reference order and absolute source-span offsets; render and final-delivery firewalls compare complete relation metadata, source ordering, rendered clauses, and source tags. Unsafe section candidates are rolled back to the deterministic source-backed baseline; unplanned sections cannot repeat a claim.
- Wired final coverage, cross-section duplicate and template-term diagnostics after deterministic assembly/finalization. Duplicate and missing-term results are diagnostic-only and cannot veto unrelated valid sections. Runtime controls are capability-scoped to the selected adapter: LM Studio temperature/top_p/top_k are sent through Chat Completions, context comes from the loaded instance for planning only, and native thinking control remains explicitly unsupported. A 400 response removes only the rejected control, preserves other supported request values, and records the unsupported control. Profile sample/selection helpers consume only caller-provided evaluator observations; unsupported or unsampled profiles are ineligible, and no model/evaluator samples were fabricated.
- Updated the V2 architecture document. Trimmed only the pre-existing trailing spaces in historical `execution.md` status lines to satisfy the approved hard-clean diff gate; historical text and status values were not changed.

### Verification

- Fresh `DATA_DIR=/tmp/convert-r9.8Hz uv run pytest -q tests/test_local_pipeline_v2.py tests/test_task_processor.py tests/test_summarization_service.py`: PASS, 92 passed.
- Fresh `DATA_DIR=/tmp/convert-r9.8Hz uv run pytest tests/ -q`: PASS, 839 passed, 2 skipped.
- Cloud compatibility baseline command: PASS, 13 passed, 41 deselected.
- `bash scripts/check_docs.sh`: exit 0; two existing README version warnings remain.
- `git diff --check`: PASS, exit 0.
- LM Studio/model sampling was not invoked by Stage04. Parent reports Qwen 3.8 27B loaded; this implementer did not call it. No Gemma E2E or frozen evaluator/baseline was available for Stage04 acceptance.

### Status and scoped blockers

| Subject | Result | Scope |
|---|---|---|
| Primary outcome | UNKNOWN pending fresh model/quality acceptance | C9/C10/C14 |
| Implementation | COMPLETE | Approved Stage04 implementation is present |
| CORE acceptance | BLOCKED | Gemma availability/E2E and frozen evaluator/baseline; runtime profiles with unsupported controls cannot count as valid samples |
| Required verification | INCOMPLETE | Available code/contracts/full/docs checks pass; blocked acceptance items remain required |
| Independent acceptance | PENDING | Parent-owned fresh Stage05 attempt required |
| Task closure | CORE_ACCEPTANCE_BLOCKED | No waiver applied |

NEXT_ACTION: Parent runs the controlled Qwen E2E with the supplied privacy-safe selected-claim fixture, records a fresh Stage05 attempt against R9, and retains scoped Gemma/evaluator/profile-sampling blockers. Do not load/unload models or substitute/fabricate evaluator samples.

## Stage 04 R9 repair update — Stage05 attempt04 audit findings

Date: 2026-09-25. This append preserves the prior Stage04/Stage05 record. Plan and handoff remain unchanged at the approved R9 hashes recorded above.

### Repairs

- The live fidelity firewall now checks every required causal/conditional relation, not only the selected claim. The production render path requires the complete required-relation ID set in plan order (with no duplicate IDs) and exact structured relation metadata before accepting the candidate; raw evidence offsets/order and rendered clauses remain checked. Invalid candidate metadata rolls back to the source-backed baseline.
- After finalization, coverage and relation firewalls now run against each exact marker-delimited section slice. Marker integrity is fail-closed: every start/end marker must occur exactly once, each start must precede its own end, and section pairs must be ordered and non-overlapping. No section can borrow another section's coverage.
- The normal W7 production temperature is now explicit and uniform per run: Qwen 0.7, Gemma 1.0. Qwen 0.3/0.5/0.7 remain extraction-only C14 candidate settings and do not alter production absent valid sampling/selection. Diagnostics separate the profile baseline from the exact temperature sent on each V2 stage request, including a separate privacy-safe request event for schema-only extraction repair. The diagnostic runner explicitly sets/requires `LOCAL_PIPELINE_VERSION=v2` and reports stage-event temperatures rather than stale V1 values.
- Added live regressions for a non-selected required relation predicate change, complete relation ID/metadata handling, post-finalizer cross-section movement, deleted/duplicated/reordered/interleaved boundary markers, direct V2 invocation under V1, Qwen production temperature, and stage temperature diagnostics.

### Verification actually run

- `python3 -m py_compile backend/services/local_pipeline_v2.py backend/services/summarization.py tests/test_local_pipeline_v2.py scripts/e2e/diagnose_local_fidelity.py`: PASS.
- `DATA_DIR=$(mktemp -d /tmp/convert-stage04.XXXXXX) uv run pytest -q tests/test_local_pipeline_v2.py`: PASS, 34 passed.
- `DATA_DIR=$(mktemp -d /tmp/convert-stage04.XXXXXX) uv run pytest -q tests/test_local_pipeline_v2.py tests/test_task_processor.py tests/test_summarization_service.py`: PASS, 104 passed.
- Cloud compatibility selection: PASS, 13 passed, 41 deselected.
- `DATA_DIR=$(mktemp -d /tmp/convert-stage04.XXXXXX) uv run pytest tests/ -q`: PASS, 851 passed, 2 skipped.
- `bash scripts/check_docs.sh`: exit 0; two existing README version warnings remain.
- `git diff --check` and `git diff --cached --check`: PASS. Plan/handoff SHA-256 remain `63b30bcae58abbba98e15a9d3b62ef23da391cbcbded19d6e22e494b29f1ba67` and `78ffbdec979529e0e1648054cda32abe86cc94f596d1ecdd08a763d23d0beb71` respectively.
- No model/evaluator call, load/unload, or raw transcript access was performed in this repair.

### Status and routing

IMPLEMENTATION_STATUS: COMPLETE
CORE_ACCEPTANCE_STATUS: BLOCKED pending parent-controlled Qwen E2E and evaluator-backed profile/quality evidence
REQUIRED_VERIFICATION_STATUS: INCOMPLETE (available code/full/docs/diff checks pass; C9/C10/C14 remain externally scoped)
INDEPENDENT_ACCEPTANCE_STATUS: PENDING fresh Stage05 attempt
TASK_CLOSURE_STATUS: CORE_ACCEPTANCE_BLOCKED
NEXT_ACTION: Parent runs the controlled Qwen E2E and fresh Stage05 audit; do not fabricate C10/C14 samples or change the production baseline without approved evidence.
