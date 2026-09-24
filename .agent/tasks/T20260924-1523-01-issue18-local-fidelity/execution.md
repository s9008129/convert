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

## Stage 04 R9 diagnostics repair — after controlled Qwen attempt

Date: 2026-09-25. This append preserves all prior status and does not alter the approved plan or handoff.

### Parent-reported attempt and diagnostic repair

- Parent reports the controlled Qwen R9 run failed after approximately 291 seconds with `LocalPipelineV2Error`. The redacted manifest showed extraction chunks 1 and 2 and a chunk-2 schema-repair input before the pipeline failure. The run had raw-snapshot opt-in enabled for inputs, but generated outputs were not captured, so the failing output could not be located. This implementer did not read raw transcript/model payloads and did not call a model.
- Added opt-in diagnostic output snapshots for extraction responses, schema-repair responses, section-render candidates, guarded patch outputs, and final selection. With snapshots disabled these outputs are retained only as allow-listed hash/count events; no raw output files are created. The final-selection recorder uses the same explicit opt-in mechanism.
- Added safe outcome events for extraction parse, schema repair, and section envelope handling. Failure status contains only the exception class (for example `failed:ValueError`); exception messages and payload text are never copied into manifest metadata.
- Added synthetic snapshot-off/on tests verifying private sentinels are absent from redacted manifests, generated output files exist only with explicit raw-snapshot opt-in, relevant stage outputs are captured, and exception messages are not recorded.

### Verification actually run

- `python3 -m py_compile backend/services/summarization.py tests/test_local_pipeline_v2.py`: PASS.
- `DATA_DIR=$(mktemp -d /tmp/convert-stage04.XXXXXX) uv run pytest -q tests/test_local_pipeline_v2.py`: PASS, 37 passed.
- `git diff --check` and `git diff --cached --check`: PASS.

IMPLEMENTATION_STATUS: COMPLETE
CORE_ACCEPTANCE_STATUS: BLOCKED pending parent-controlled rerun and evaluator-backed quality/profile evidence
REQUIRED_VERIFICATION_STATUS: INCOMPLETE
INDEPENDENT_ACCEPTANCE_STATUS: PENDING fresh Stage05 review of the new controlled attempt
TASK_CLOSURE_STATUS: CORE_ACCEPTANCE_BLOCKED
NEXT_ACTION: Parent reruns controlled Qwen with raw snapshots explicitly enabled and inspects private outputs outside the tracked task artifacts; record only a redacted finding in the next Stage05 attempt. No model was invoked by this implementer.

### Final diagnostics-wave verification rerun (2026-09-25)

- `DATA_DIR=$(mktemp -d /tmp/convert-stage04-final.XXXXXX) uv run pytest tests/ -q`: PASS, 854 passed, 2 skipped (9.60s).
- `bash scripts/check_docs.sh`: exit 0; the same two README version warnings remain.
- `git diff --check` and `git diff --cached --check`: PASS.

These results supersede the earlier full-suite/docs/diff results for the diagnostics repair wave; no product semantics or plan/handoff files changed.

## Stage 04 R9 repair update — Stage05 attempt05 findings

Date: 2026-09-25. Plan/handoff remain unchanged. Repairs implement the existing R2/R4/R6 ledger and rendered-relation contracts.

### Approved-scope repairs

- `FactClaim.fingerprint` now includes direction, status, and uncertainty in addition to the prior normalized semantic fields, so reverse-direction and AMBIGUOUS variants cannot be silently consolidated into the first claim.
- Deterministic same-evidence conflict detection now preserves incompatible directed relation, predicate/type, polarity, condition, status, uncertainty, number/unit/date, and attribution variants as explicit `ClaimConflict` records; it does not choose a winner. The established different-object conflict remains explicit.
- The live fidelity firewall now checks every endpoint-bearing rendered clause against section-planned relation claims whose metadata exactly matches their claim and whose ordered raw evidence supports the subject/predicate/object. A correct expected phrase no longer blesses an added competing predicate. Contrastive continuations that omit a repeated subject but repeat a relation endpoint (e.g. `...但避免延後`) are rejected as unsupported residue without a lexical model or parser recovery.
- Added ledger tests for direction, status, uncertainty, polarity, condition, and reversed endpoints; added helper and live summarize rollback tests for comma-separated and no-comma competing predicates.

### Verification actually run

- `python3 -m py_compile backend/services/local_pipeline_v2.py backend/services/summarization.py tests/test_local_pipeline_v2.py`: PASS.
- `DATA_DIR=$(mktemp -d /tmp/convert-stage04-audit.XXXXXX) uv run pytest -q tests/test_local_pipeline_v2.py`: PASS, 47 passed.
- `DATA_DIR=$(mktemp -d /tmp/convert-stage04-audit.XXXXXX) uv run pytest -q tests/test_summarization_service.py -k 'cloud_pipeline or cloud_generation or validate_cloud or cloud_finalize or gemini_chat'`: PASS, 13 passed, 41 deselected.
- `DATA_DIR=$(mktemp -d /tmp/convert-stage04-audit.XXXXXX) uv run pytest tests/ -q`: PASS, 864 passed, 2 skipped (8.76s).
- `bash scripts/check_docs.sh`: exit 0; the same two README-version warnings remain.
- `git diff --check` and `git diff --cached --check`: PASS.
- No model call was made. Parent-reported C9 output-shape observations were not used to alter temperatures, JSON parsing, or failure semantics.

IMPLEMENTATION_STATUS: COMPLETE
CORE_ACCEPTANCE_STATUS: BLOCKED pending parent-controlled C9 rerun and evaluator-backed quality/profile evidence
REQUIRED_VERIFICATION_STATUS: INCOMPLETE
INDEPENDENT_ACCEPTANCE_STATUS: PENDING fresh Stage05 review
TASK_CLOSURE_STATUS: CORE_ACCEPTANCE_BLOCKED
NEXT_ACTION: Parent reruns the affected live R9 checks and records a new Stage05 attempt; keep C10/C14 evidence absent/blocked until the frozen evaluator is available.

## Stage 04 follow-up — attempt06 invalid-reference/conflict diagnosis

Date: 2026-09-25. Stage05 attempt06 report was recorded and preserved. Plan/handoff identity still matches approved R9; no product-code changes were made in this follow-up.

### W0 and safe evidence

- Branch/HEAD at inspection: `issue-18-first-divergence-diagnostic` / `f15117351e45b230180850b625edba91eee75e5b`. Before this artifact update the worktree only contained the untracked immutable `e2e/attempt-06/` artifact. No reset, stash, cleanup, or model call occurred.
- Parent-provided safe aggregate: 4 extraction chunks parsed, 87 claims, 7 `same_evidence_value` conflicts, valid refs `span-1..span-4`, 54 claims with valid refs, 33 claims with unknown refs (17 unique); 5/7 conflicts include unknown refs. Failure occurred before `v2.ledger` diagnostics. No raw transcript or model output was read.
- Plan SHA-256 remains `63b30bcae58abbba98e15a9d3b62ef23da391cbcbded19d6e22e494b29f1ba67`; handoff SHA-256 remains `78ffbdec979529e0e1648054cda32abe86cc94f596d1ecdd08a763d23d0beb71`.

### Escalation and work disposition

- Appended a new attempt06-scoped Stage04 escalation; historical escalation text and all attempt06 evidence remain intact.
- The current section planner puts every `ASSERTED` claim into `required_claim_ids`; it has no optional/core input mapping and leaves optional IDs empty. The live core selection is inferred as the first causal/conditional assertion, not bound to the diagnostic target claim ID. Downgrading all non-first claims with invalid refs would invent optionality; failing all unknown refs would create a forbidden global veto; using invalid refs as conflict/prompt evidence would violate R1.
- W3 requires normalized claim/evidence identity and overlap, and the approved guidance says coarse chunk-level `span_id` alone does not prove same evidence. A statement-level anchor/overlap threshold that drives conflict gating is not specified. Stop before changing claim status, requiredness, conflict eligibility, or run gating; Stage01 must resolve selected/core identity, optional-vs-required mapping, and the deterministic source-occurrence conflict rule.
- The parent-reported response-shape diagnostics remain consistent with possible truncation, but `finish_reason` is unknown. No parser recovery, output-budget increase, prompt semantic change, or temperature change was made.

### Verification and status

- No product code changed, so no tests were run for this stopped repair. `git diff --check` and `git diff --cached --check`: PASS after the task-artifact update.
- `IMPLEMENTATION_STATUS: BLOCKED` — unfinished R1/R4 behavior cannot safely continue without the planner decisions above.
- `CORE_ACCEPTANCE_STATUS: BLOCKED`; `REQUIRED_VERIFICATION_STATUS: INCOMPLETE`; `INDEPENDENT_ACCEPTANCE_STATUS: PENDING planner-directed repair and fresh Stage05`; `TASK_CLOSURE_STATUS: CORE_ACCEPTANCE_BLOCKED`.
- NEXT_ACTION: Stage01 resolves the three semantic mappings, then Stage04 resumes on a fresh approved revision/handoff. Do not inspect or copy raw output into tracked artifacts.

## Stage 04 authoritative status correction — attempt06 plan-premise invalidation

This append-only correction supersedes the `IMPLEMENTATION_STATUS: BLOCKED` and
`TASK_CLOSURE_STATUS: CORE_ACCEPTANCE_BLOCKED` values in the immediately
preceding attempt06 follow-up's terminal status block. Those values remain
preserved above as the original report; they are not the current routing result.

The attempt06 evidence invalidates load-bearing approved R9 premises about
selected/core identity, required-vs-optional claim mapping, and R4
same-evidence/conflict identity. Per `workflow-routing.md` §7.7 precedence row
1, this is a Stage01 replan condition, rather than only an inability to continue
within an otherwise valid approved contract. This Stage04 record is grounded in
Plan R9 SHA-256
`63b30bcae58abbba98e15a9d3b62ef23da391cbcbded19d6e22e494b29f1ba67` and its
matching R9 handoff SHA-256
`78ffbdec979529e0e1648054cda32abe86cc94f596d1ecdd08a763d23d0beb71`.

Freshness note: a later Plan R11 draft is now present with SHA-256
`1ef80c7807d7078981051f740346668a827b20266a39b1f1ebdad081ee3975a2`, marked
`READY_FOR_REVIEW`; it has not been used as authority for this historical R9
Stage04 run. This correction does not claim R11 approval or authorize product
implementation against R11. Stage01 review and, if approved, a fresh matching
handoff remain prerequisites for resumed implementation.

### Current authoritative Stage 04 status for the attempt06 finding

PRIMARY_OUTCOME_STATUS: UNKNOWN
IMPLEMENTATION_STATUS: ESCALATED
CORE_ACCEPTANCE_STATUS: BLOCKED
REQUIRED_VERIFICATION_STATUS: INCOMPLETE
INDEPENDENT_ACCEPTANCE_STATUS: PENDING
TASK_CLOSURE_STATUS: REPLAN_REQUIRED

NEXT_ACTION: Stage01 resolves/reviews the replan; Stage04 resumes only after an
approved current Plan and matching handoff. No product files were edited for
this status correction.

## Stage 04 implementation — approved Plan R11

Date: 2026-09-25. Startup freshness verified before product edits:

- `TASK_ID: T20260924-1523-01-issue18-local-fidelity`
- Plan R11 SHA-256: `1ef80c7807d7078981051f740346668a827b20266a39b1f1ebdad081ee3975a`
- Review attempt10: `PLAN_APPROVED` for that exact plan SHA.
- Handoff R11 SHA-256: `bc29f344f7066f8e44b6b1dcebedc1da6b140b2c80851c515848a4b707b21fc0`
- The pre-existing dirty task artifacts were preserved. Stage04 owned only code,
  tests, the V2 design note, and append-only updates to this execution record.
  The delegated C13 fixture artifact remains parent-owned and was not edited.

### Implemented approved waves

- Added ephemeral selected-target routing from the actual `TaskProcessor` local
  call through `SummarizationService` to V2. Target data stays in memory for
  deterministic binding/final-delivery checks; it is not added to prompts or
  persisted `TaskInfo`.
- Added exact raw chunk-origin offsets and unique source-quote occurrence
  resolution. Missing, invalid, repeated, or mismatched occurrences remain
  ambiguous; conflicts require validated absolute-interval overlap and typed
  incompatibility, with no automatic winner.
- Added trusted source-present requiredness policies and bounded lexical
  candidate coverage for the four active templates. Unresolved optional claims
  remain local; unresolved required/selected claims retain their mapped gate.
- Completed section-by-section allow-listed rendering, deterministic template
  order assembly, final marker/source checks, and guarded byte-for-byte section
  rollback. V1 remains the explicit default and V2 has no hidden V1 fallback.
- Wired occurrence-level entity, relation, polarity, condition, number, date,
  attribution, source-tag, cross-section duplicate, and template-term checks.
  Unsupported claims become ambiguous rather than globally vetoing unrelated
  sections. A bounded numeric equivalence accepts one Chinese digit plus its
  exact explicit unit only; mismatched values/units remain unresolved.
- Kept Qwen candidate extraction temperature separate from rendering: Qwen
  section/render temperature stays at the approved 0.7 baseline. Candidate
  extraction temperatures are diagnostic-only; they cannot change production
  settings or be selected without evaluator-backed samples.
- Updated the local V2 design note with the raw-source, target-routing,
  requiredness, numeric-equivalence, and profile boundaries.

### Verification and runtime evidence

- `DATA_DIR=/tmp/issue18-stage04-data uv run pytest -q tests/test_local_pipeline_v2.py tests/test_task_processor.py`:
  PASS, 72 tests.
- `DATA_DIR=/tmp/issue18-final-cloud uv run pytest -q tests/test_summarization_service.py -k 'cloud_pipeline or cloud_generation or validate_cloud or cloud_finalize or gemini_chat'`:
  PASS, 13 passed, 41 deselected; same count as the pre-change baseline.
- `DATA_DIR=/tmp/issue18-final-full uv run pytest tests/ -q`:
  PASS, 873 passed, 2 skipped (pre-change baseline: 864 passed, 2 skipped).
- `python3 -m py_compile` on changed backend modules and tests: PASS.
- `bash scripts/check_docs.sh`: exit 0; the same two pre-existing README
  version warnings remain. `git diff --check`: PASS.
- LM Studio runtime inventory: Qwen `qwen3.8-27b-splash` loaded; Gemma
  `gemma-4-31b-it-mlx` installed but not loaded. No model load/unload was
  attempted. Live Qwen requests used the loaded instance and the production
  0.7 profile.
- Multiple controlled synthetic Qwen selected-target probes and repeats failed
  closed when the extraction claim was ambiguous or its quote did not resolve
  to the exact selected occurrence. TaskProcessor reported summary failure and
  used its existing transcript-only degradation; relation text seen in that
  fallback is not counted as a selected-target pass. A first pre-normalization
  probe exposed an unsupported structured number representation; the bounded
  same-unit Chinese digit rule was then added and covered synthetically.
- Diagnostic-only candidate runs used the same synthetic source/target at
  extraction temperatures 0.3, 0.5, and 0.7 (N=3 each), with render fixed at
  0.7. All 9 selected-target gates failed closed. No raw response, quote,
  prompt, or output was retained or recorded in this artifact. No profile score
  or candidate selection was fabricated.
- Canonical target resolution was not possible: both allowed ignored transcript
  copies match the original full input digest `b7b9e5e0...1d9db0`, but exhaustive
  exact substring SHA checks through 512 characters found no match for the
  authoritative anchor digest `5eb677f3...30010f`. Filename-only inspection
  under the current task and those two local cache directories found no
  separate target-spec file. No source contents were printed or copied. Thus
  synthetic model probes remain diagnostic only; canonical `C1`/`C9` is
  `BLOCKED`/not run on the authoritative selected target.
- Parent's scoped evaluator audit remains controlling: no authoritative frozen
  rubric/protocol or original unrounded Gemini baseline/sample set is
  available. `C10` and quality-based `C14` selection remain
  `BLOCKED/AUTHORITY` with exact label
  `QUALITY_ACCEPTANCE_BLOCKED_BY_MISSING_FROZEN_EVALUATOR`.
- Privacy review found no raw transcript, prompt, model response, private name,
  or absolute local path added to tracked implementation/evidence. PR #19 was
  not mutated; it remains Draft per the existing delivery plan.

### Stage 04 status snapshot for independent acceptance

PRIMARY_OUTCOME_STATUS: UNKNOWN
IMPLEMENTATION_STATUS: COMPLETE
CORE_ACCEPTANCE_STATUS: BLOCKED
REQUIRED_VERIFICATION_STATUS: INCOMPLETE
INDEPENDENT_ACCEPTANCE_STATUS: PENDING
TASK_CLOSURE_STATUS: CORE_ACCEPTANCE_BLOCKED

BLOCKERS:
- `C1/C9` canonical selected-target E2E: `BLOCKED/AUTHORITY` because the
  supplied anchor digest did not resolve to an exact source substring and no
  typed target spec was present in the authorized current-task/data filenames.
- `C9-Gemma`: `BLOCKED/ENVIRONMENT`; runtime lists Gemma as not loaded. No load
  was attempted.
- `C10/C14`: `BLOCKED/AUTHORITY` by
  `QUALITY_ACCEPTANCE_BLOCKED_BY_MISSING_FROZEN_EVALUATOR`.

NEXT_ACTION: Supply/resolve the authoritative selected-target anchor/spec,
perform canonical Qwen and Gemma E2E without exposing raw source/output, and
obtain the frozen evaluator before any C10/C14 scoring or profile selection.
Stage05 may now preserve and independently audit this snapshot; keep Draft PR
#19 unpublished and unmerged.

### Anchor-search extension

After the initial status snapshot, the source-anchor check was extended to
41,616 sentence/paragraph-boundary spans up to 4,096 characters and 248,052
exact, trimmed, whitespace-normalized, and Unicode-normalized candidate forms.
Zero candidates matched the authoritative anchor SHA-256. No source text was
printed. This confirms the canonical selected target still cannot be resolved
from the authorized local source/anchor pair; the `C1/C9` blocker and all status
fields above remain unchanged.

### W9 closeout — docs, privacy, and status routing

- Documentation: the V2 design note records the approved selected-target
  boundary, exact source-occurrence grounding, template requiredness, bounded
  numeric equivalence, and extraction/render profile separation. The delegated
  `evidence/status-contract-fixtures.md` is present and remains parent-owned.
- Privacy: the tracked-diff audit found zero added absolute user paths,
  API-key-like strings, transcript-cache paths, or raw prompt/model-output dump
  markers. Raw source and live model payloads remain unretained. The expanded
  anchor-resolution check recorded counts only (zero matching candidates), not
  source text or offsets for non-matches.
- Verification evidence remains as recorded above: focused/full/cloud test
  suites, Python compilation, docs check, and whitespace check passed; docs
  check emitted only the same two baseline README-version warnings.
- `C1`: `CHECK_RESULT: BLOCKED` (`AUTHORITY` / unresolved selected-target
  specification). The authoritative anchor digest did not match any examined
  exact or normalized source span, so no typed expected relation can safely be
  derived. Canonical selected-target C1 was not run. No expected target was
  inferred from synthetic probes.
- `C9`: canonical fresh E2E is `CHECK_RESULT: BLOCKED` (`AUTHORITY`) pending
  the same authoritative selected-target specification. The Gemma-specific C9
  run is separately `CHECK_RESULT: BLOCKED` (`ENVIRONMENT`) because Gemma was
  not loaded. Synthetic Qwen nine-run candidate sampling remains diagnostic
  only and is not a C9 acceptance result. No model loading was attempted.
- `C10` and `C14`: each `CHECK_RESULT: BLOCKED` (`AUTHORITY`) with exact label
  `QUALITY_ACCEPTANCE_BLOCKED_BY_MISSING_FROZEN_EVALUATOR`; no scoring or
  candidate selection was performed.
- The Stage04 aggregate follows the Plan R11 row for completed implementation
  with acceptance blocked and other required evidence available. Its six
  orthogonal fields are:

  ```text
  PRIMARY_OUTCOME_STATUS: UNKNOWN
  IMPLEMENTATION_STATUS: COMPLETE
  CORE_ACCEPTANCE_STATUS: BLOCKED
  REQUIRED_VERIFICATION_STATUS: INCOMPLETE
  INDEPENDENT_ACCEPTANCE_STATUS: PENDING
  TASK_CLOSURE_STATUS: CORE_ACCEPTANCE_BLOCKED
  ```

  These fields do not convert diagnostic synthetic Qwen observations into a
  canonical PASS/FAIL. Implementation and completed verification evidence
remain intact; C1/C9 target authority, Gemma environment, and C10/C14
evaluator authority remain separate scoped blockers. Stage05 must preserve
this Stage04 snapshot and report any acceptance-phase blocker in its own
fields. PR #19 remains Draft, unpublished and unmerged.

### Evidence-preservation correction

The pre-existing `baseline/cloud-contract-focused.txt` evidence is preserved
byte-for-byte as the file prefix (verified against `HEAD`). The R11
pre-mutation 13-pass run is retained after it as a separate labeled section;
the detailed W0 record remains in `baseline/w0-stage04-r11-20260924T182410Z.txt`.
No product code or test files changed for this correction. The status snapshot
above is unchanged.

### Stage04 bounded repair after independent review attempt07

Stage05 attempt07 reported two mechanical defects within the approved R11
contract. Attempt07 and the original Stage04 snapshot above are preserved
unchanged; this section records the repair and current post-repair state.

- Numeric source grounding now checks the entire Arabic numeric token and its
  exact supplied unit, or the already-approved bounded Chinese single digit
  plus exact unit. It rejects substring matches, decimal/longer values,
  different units, mixed Chinese numerals, and explicit quantity modifiers.
- Occurrence resolution now marks a matching quote in an offsetless evidence
  span `AMBIGUOUS` immediately because it cannot establish an absolute unique
  source interval; the scan no longer repeats without advancing.
- Fail-first numeric boundary test before the product fix: 4 expected-negative
  cases failed (2 vs 12, 1 vs 10, 1 vs 1.5, and 1 week vs one-and-a-half weeks);
  the four exact/positive or already-rejected mixed/different-unit cases passed.
  The offsetless-span regression case was added. A pre-fix runtime timeout probe
  could not be executed because this shell lacks the `timeout` utility, so no
  hang is claimed as experimentally observed; the no-advance loop was directly
  identified in code review. Post-fix test confirms prompt `AMBIGUOUS` result.
- Post-fix focused verification:
  `DATA_DIR=/tmp/issue18-p1p2-focused uv run pytest -q tests/test_local_pipeline_v2.py tests/test_task_processor.py` — 81 passed.
- Post-fix full verification:
  `DATA_DIR=/tmp/issue18-p1p2-full uv run pytest tests/ -q` — 882 passed, 2 skipped.
- Cloud focused verification:
  `DATA_DIR=/tmp/issue18-p1p2-cloud uv run pytest -q tests/test_summarization_service.py -k 'cloud_pipeline or cloud_generation or validate_cloud or cloud_finalize or gemini_chat'` — 13 passed, 41 deselected.
- `python3 -m py_compile backend/services/local_pipeline_v2.py tests/test_local_pipeline_v2.py` and `git diff --check` passed. `bash scripts/check_docs.sh` exited 0 with the same two README version warnings recorded in the original Stage04 run.
- This review repair introduces no semantic-contract or schema change. During repair the current implementation state was `IN_PROGRESS`; after the bounded fixes and verification it is `COMPLETE`, awaiting fresh independent attempt08. The prior immutable Stage04 snapshot remains unchanged. Current scoped status remains:

  ```text
  PRIMARY_OUTCOME_STATUS: UNKNOWN
  IMPLEMENTATION_STATUS: COMPLETE
  CORE_ACCEPTANCE_STATUS: BLOCKED
  REQUIRED_VERIFICATION_STATUS: INCOMPLETE
  INDEPENDENT_ACCEPTANCE_STATUS: PENDING
  TASK_CLOSURE_STATUS: CORE_ACCEPTANCE_BLOCKED
  ```

  Existing C1/C9 target-spec, Gemma environment, and C10/C14 evaluator blockers
  remain exactly as previously scoped. Stage05 should run fresh attempt08 on
the repaired code without editing attempt07.

### Stage04 freshness follow-up — location-neutral Handoff

- Verified Plan R11 remains SHA-256
  `1ef80c7807d7078981051f740346668a827b20266a39b1f1ebdad081ee3975a`; Review
  attempt10 remains `PLAN_APPROVED` for that exact revision/hash. The regenerated
  current Handoff is SHA-256
  `09b322244a338f800cc427c939c41143fe1226c27863602277d2a74f1a5731bc` and its
  `PLAN_SHA256` and `REVIEWED_PLAN_SHA256` both match R11 and attempt10.
- Stage03 regenerated the same R11 Handoff solely to redact an absolute local
  project-root path to `.`. This is a location/privacy correction only: no
  plan, product, or semantic contract changed; no product code or tests changed
  in this follow-up.
- The status-contract fixture now cites `workflow-routing.md`, §7 (Status
  Semantics Contract v2) without an absolute home-directory path; its synthetic
  cases and status meanings are unchanged.
- Stage05 attempt08 remains immutable and bound to the prior Handoff SHA-256
  `bc29f344f7066f8e44b6b1dcebedc1da6b140b2c80851c515848a4b707b21fc0` and the
  prior Stage04 execution SHA-256
  `875cebda1a106eab1391d4eabe9cef8c6fb02c4283ac0cfb9ca2189b77e54143`. Do not
  edit or reuse attempt08 as acceptance for the regenerated Handoff/current
  execution artifact; a fresh Stage05 attempt09 is required.
- Current six-field Stage04 status remains exactly:

  ```text
  PRIMARY_OUTCOME_STATUS: UNKNOWN
  IMPLEMENTATION_STATUS: COMPLETE
  CORE_ACCEPTANCE_STATUS: BLOCKED
  REQUIRED_VERIFICATION_STATUS: INCOMPLETE
  INDEPENDENT_ACCEPTANCE_STATUS: PENDING
  TASK_CLOSURE_STATUS: CORE_ACCEPTANCE_BLOCKED
  ```

  Existing scoped C1/C9 target-spec, Gemma environment, and C10/C14 evaluator
  blockers remain unchanged.

## Stage 04 implementation — approved Plan R13

### Identity and pre-mutation state

- TASK_ID: `T20260924-1523-01-issue18-local-fidelity`
- PLAN_REVISION: 13; PLAN SHA-256: `ea0334db6c32294f26fdcf7b22db52c376b9cc03e98dd3214cb011f6ac56f900`
- Review: attempt 12 returned `PLAN_APPROVED` for the same plan SHA.
- Handoff SHA-256: `b2df3b9fbb296d35e0277d3663f895d01c264e954633a0b5f8d3546e8b2dadba`
- Branch/HEAD: `issue-18-first-divergence-diagnostic` / `35e98a29f63c155e25454b494c5d21436529aa28` (no commit created in this Stage04 run).
- The timestamped, path-classified W0 snapshot is `evidence/stage04-w0-20260924T203258Z.md`, SHA-256 `866a2bd45d8c9a41d09400e4fbfc235e55486341e2f2b48350509502757c3404`. All pre-existing dirty paths were approved task plan/handoff/review/archive evidence; product code was clean before this implementation. Safety branches were verified as ancestors of HEAD, and the pre-R12 safety branch equals HEAD.
- PR #19 was rechecked OPEN/Draft, base `main`, correct head. It remains Draft; no push or PR edit was made before Stage05.
- Runtime recheck at W0: Qwen 3.8 27B was loaded; Gemma remained not-loaded. No model call was made in this Stage04 run.

### Implemented CORE repairs

- Final post-finalizer assembled bytes now reject decisive mapped-required coverage/relation/source-tag failures, selected-target delivery failure, source-inventory candidate omissions, unresolvable citation IDs, confirmed unsupported exact high-risk additions, and required claims duplicated across sections. Optional/ambiguous signals remain non-gating. Novelty checks are intentionally exact and conservative; equivalent date/number formatting and same-stem legal-suffix aliases are not vetoed.
- Required source tags must appear on the claim-bearing clause and refer to validated evidence spans. Independent claim occurrences can use distinct validated span references; no tag is synthesized.
- Extraction generation/runtime failures are classified separately and fail without schema repair. Only strict JSON/schema validation failure receives one schema-only repair; repair generation/schema failure terminates without another attempt.
- Runtime profile sampling/selection rejects repeats below 3, repeated run IDs, missing IDs/dimensions, non-finite/out-of-range scores, and malformed error counts. It no longer imputes missing dimensions as zero. This is profile/acceptance eligibility only, not a per-record gate.
- Exact template-owned glossary mappings are applied deterministically and idempotently after the existing finalizer, before final-byte validation. No broad/global term substitution was introduced.
- Tests use synthetic content; no raw meeting source, prompts, or model output were added to tracked files.

### Verification evidence

| Check | Result | Evidence / notes |
|---|---|---|
| C1 selected-target source→delivery E2E | `BLOCKED` / `AUTHORITY_REQUIRED` | Stage05 must freshly verify designated source identity/hash, unique occurrence, and raw-derived relation before any acceptance call. No Qwen call was made. |
| C2 synthetic A–I and live V2 regressions | `PASS` | `DATA_DIR=/tmp/issue18-stage04-data uv run pytest -q tests/test_local_pipeline_v2.py` — 74 passed. Includes fail-first/post-fix finalizer, novelty, citation, schema retry, and profile-eligibility contracts. |
| C3 cloud non-regression | `PASS` | Pre and post: `DATA_DIR=/tmp/issue18-stage04-cloud-final uv run pytest -q tests/test_summarization_service.py -k "cloud_pipeline or cloud_generation or validate_cloud or cloud_finalize or gemini_chat"` — 13 passed, 41 deselected. The initial no-override collection failed because logger default `/app/data/logs` was read-only; using task-local `/tmp` DATA_DIR resolved the environment-only issue. |
| C4 privacy | `PASS` | Reviewed changed paths and executed a suppressed sensitive-pattern scan over product/test diff; no matches. New tests are synthetic; no Qwen/Gemma outputs or source payloads exist in the diff. |
| C5 local V2/task-processor focused integration | `PASS` | `DATA_DIR=/tmp/issue18-stage04-c5 uv run pytest -q tests/test_local_pipeline_v2.py tests/test_task_processor.py` — 92 passed. |
| C6 repository suite | `PASS` | `DATA_DIR=/tmp/issue18-stage04-final uv run pytest tests/ -q` — 893 passed, 2 skipped. |
| C7 docs | `PASS` | `bash scripts/check_docs.sh` exited 0; it emitted the same 2 README version warnings noted by prior task evidence. No documentation content was changed in this Stage04 wave. |
| C8 diff hygiene | `PASS` | `git diff --check` and `python3 -m py_compile backend/services/local_pipeline_v2.py backend/services/summarization.py tests/test_local_pipeline_v2.py` exited 0. |
| C9 fresh Qwen and Gemma E2E | `BLOCKED` / scoped acceptance | Qwen was loaded but its C1 acceptance call is gated on Stage05 preflight. Gemma was not loaded; do not alter runtime until the Qwen path is complete. |
| C10 blind Gemma 3 + Qwen 3 vs original unrounded Gemini median | `BLOCKED` / `AUTHORITY_REQUIRED` | Frozen evaluator/rubric and original unrounded baseline remain unavailable. No scores were invented, rounded, or substituted. |
| C11 cost/context diagnostics | `NOT_RUN` / supporting | Non-gating. |
| C12 held-out meeting | `NOT_RUN` / best-effort | No approved additional source was supplied. |
| C13 execution/docs/status fixtures/PR | `INCOMPLETE` | This execution record and W0 evidence are durable; status fixture remains existing task evidence. PR #19 remains Draft and awaits the appropriate post-Stage05 redacted update. |
| C14 profile selection/repeated evaluator runs | `BLOCKED` / `AUTHORITY_REQUIRED` | Eligibility contracts pass; actual samples require the missing frozen evaluator and complete authoritative dimensions. |
| C15 final-byte coverage/fidelity/tag/duplicate checks | `PASS` | C2 regressions directly exercise required post-finalizer removal, ungrounded numeric/entity/attribution additions, source-inventory omission, unanchored tags, and final cross-section duplication. |
| C16 schema/runtime retry classification | `PASS` | Runtime exception has no repair request; malformed JSON has exactly one schema repair (2 generation calls total). |
| C17 profile evidence eligibility | `PASS` | Repeats<3, replayed run IDs, missing dimensions/run IDs, and out-of-range scores are rejected; missing metrics are not defaulted. |

All waivers: `NOT_ALLOWED` (Plan authority is `NONE`). C9/C10/C14 acceptance blockers do not downgrade the implementation or focused test facts above.

### Current orthogonal status and scoped blockers

```text
PRIMARY_OUTCOME_STATUS: UNKNOWN
IMPLEMENTATION_STATUS: COMPLETE
CORE_ACCEPTANCE_STATUS: BLOCKED
REQUIRED_VERIFICATION_STATUS: INCOMPLETE
INDEPENDENT_ACCEPTANCE_STATUS: PENDING
TASK_CLOSURE_STATUS: CORE_ACCEPTANCE_BLOCKED
NEXT_ACTION: Fresh Stage05 attempt repeats the private source identity/hash, unique-occurrence, and raw-derived relation preflight. If it passes, run Qwen C1 and record its actual result; if inconclusive, keep C1 BLOCKED/AUTHORITY and make no model call. Then address Gemma runtime and frozen evaluator/baseline only within their scoped acceptance items.
```

C1 is blocked at the Stage05 authority boundary pending that independent preflight; Qwen's loaded state does not prove source mapping. C9 remains unaccepted until the Qwen journey and the separately scoped Gemma run are evidenced. C10/C14 remain blocked only by missing evaluator authority. Implementation is not blocked. No commit, push, Draft PR edit, waiver, or Stage05 acceptance claim is included in this Stage04 snapshot.
