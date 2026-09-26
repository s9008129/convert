# Status Contract Fixtures — v4.2 / Contract v2

**TASK_ID:** `T20260924-1523-01-issue18-local-fidelity`
**Plan basis:** R11, C13 / Decision G
**Authority:** `workflow-routing.md`, §7 (Status Semantics Contract v2)
**Fixture nature:** synthetic, redacted status-semantic examples only; no production/user payloads.
**Append-only note:** initial fixture entry; retain this version and append a new dated section for future changes rather than rewriting prior evidence.
**Gate/waiver constraint:** every gate in this task remains `WAIVER_ALLOWED: NO`, `WAIVER_AUTHORITY: NONE`. The formal-waiver scenario below is isolated contract-semantic coverage under an explicitly hypothetical, separately authorized fixture gate; it grants or requests no waiver for this task.

## Field legend

Each case states the six independent terminal subjects:

```text
PRIMARY_OUTCOME_STATUS: ACHIEVED | NOT_ACHIEVED | UNKNOWN
IMPLEMENTATION_STATUS: NOT_STARTED | IN_PROGRESS | COMPLETE | BLOCKED | ESCALATED
CORE_ACCEPTANCE_STATUS: NOT_REQUIRED | NOT_RUN | PASS | FAIL | BLOCKED
REQUIRED_VERIFICATION_STATUS: NOT_REQUIRED | NOT_RUN | PASS | FAIL | BLOCKED | INCOMPLETE | WAIVED
INDEPENDENT_ACCEPTANCE_STATUS: NOT_REQUIRED | PENDING | PASS | FAIL | BLOCKED
TASK_CLOSURE_STATUS: IN_PROGRESS | PENDING_CORE_ACCEPTANCE | CORE_ACCEPTANCE_BLOCKED | READY_FOR_INDEPENDENT_ACCEPTANCE | PENDING_REQUIRED_VERIFICATION | FIX_REQUIRED | REPLAN_REQUIRED | IMPLEMENTATION_BLOCKED | ACCEPTANCE_BLOCKED | DONE
```

`BLOCKED` always identifies its subject and scope in `BLOCKERS`; `DONE` appears only as `TASK_CLOSURE_STATUS`. Each check example is synthetic and does not report an actual repository check or behavioral result.

## Matrix

### F01 — Canonical incident: outcome achieved, pre-existing hard-clean debt remains

**Synthetic condition:** the user-visible objective has valid direct evidence; implementation and CORE acceptance are independently established. A required hard-clean repository-health item reports a verified pre-existing failure. This debt blocks closure but does not retroactively invalidate the outcome, implementation, or CORE evidence.

```yaml
PRIMARY_OUTCOME_STATUS: ACHIEVED
IMPLEMENTATION_STATUS: COMPLETE
CORE_ACCEPTANCE_STATUS: PASS
REQUIRED_VERIFICATION_STATUS: INCOMPLETE
INDEPENDENT_ACCEPTANCE_STATUS: PENDING
TASK_CLOSURE_STATUS: PENDING_REQUIRED_VERIFICATION
CHECK:
  CHECK_ID: SYNTHETIC-HARD-CLEAN-01
  GOAL_CRITICALITY: SUPPORTING
  EVIDENCE_ROLE: REPOSITORY_HEALTH
  CLOSURE_GATE: HARD_CLEAN
  BASELINE_REQUIRED: NO
  CHECK_RESULT: FAIL
  FAILURE_CLASSIFICATION: PRE_EXISTING_REPOSITORY_FAILURE
  WAIVER_ALLOWED: NO
  WAIVER_AUTHORITY: NONE
  WAIVER_STATUS: NOT_ALLOWED
BLOCKERS:
  - scope: REQUIRED_VERIFICATION
    subject: SYNTHETIC-HARD-CLEAN-01
    result: FAIL
    class: PRE_EXISTING_REPOSITORY_FAILURE
    task_regression_evidence: NONE
    evidence: synthetic pre-existing failure signature
    next_action: resolve the hard-clean item or use only a Plan-authorized closure route
    owner: unknown
    waiver_allowed: NO
```

**Expected invariant:** no claim that the repository is clean; no downgrade of proven `ACHIEVED`, `COMPLETE`, or CORE `PASS`.

### F02 — True product implementation blocker

**Synthetic condition:** approved product implementation is unfinished and cannot safely continue because a required implementation input is unavailable. This is an implementation blocker, not an acceptance prerequisite blocker.

```yaml
PRIMARY_OUTCOME_STATUS: UNKNOWN
IMPLEMENTATION_STATUS: BLOCKED
CORE_ACCEPTANCE_STATUS: NOT_RUN
REQUIRED_VERIFICATION_STATUS: NOT_RUN
INDEPENDENT_ACCEPTANCE_STATUS: PENDING
TASK_CLOSURE_STATUS: IMPLEMENTATION_BLOCKED
BLOCKERS:
  - scope: IMPLEMENTATION
    subject: SYNTHETIC-UNFINISHED-COMPONENT
    result: BLOCKED
    class: AUTHORITY_REQUIRED
    task_regression_evidence: NONE
    evidence: synthetic missing implementation prerequisite
    next_action: obtain the named prerequisite, then resume approved implementation
    owner: project owner
    waiver_allowed: NO
```

**Expected invariant:** `IMPLEMENTATION_BLOCKED` is valid only because implementation itself is unfinished and unable to continue; it cannot coexist with `IMPLEMENTATION_STATUS: COMPLETE` or `TASK_CLOSURE_STATUS: DONE`.

### F03 — CORE acceptance outcome matrix

These are distinct Stage 04 terminal routes. `NOT_REQUIRED` is valid only in the explicitly Plan-rationalized row; it is not a substitute for `NOT_RUN`.

| Synthetic condition | PRIMARY_OUTCOME_STATUS | IMPLEMENTATION_STATUS | CORE_ACCEPTANCE_STATUS | REQUIRED_VERIFICATION_STATUS | INDEPENDENT_ACCEPTANCE_STATUS | TASK_CLOSURE_STATUS | Route / invariant |
|---|---|---|---|---|---|---|---|
| Valid CORE evidence conclusively violates its criterion | NOT_ACHIEVED | IN_PROGRESS | FAIL | INCOMPLETE | PENDING | FIX_REQUIRED | Fix the CORE failure; preserve unrelated valid evidence. |
| CORE evidence cannot yield a conclusion due to a scoped authority/environment blocker; another required item has valid evidence | UNKNOWN | COMPLETE | BLOCKED | INCOMPLETE | PENDING | CORE_ACCEPTANCE_BLOCKED | Preserve implementation; name blocker scope and subject. |
| CORE evidence cannot yield a conclusion and the whole required-verification phase has no valid conclusion | UNKNOWN | COMPLETE | BLOCKED | BLOCKED | PENDING | CORE_ACCEPTANCE_BLOCKED | Use verification `BLOCKED` only because the phase as a whole cannot reach a valid conclusion. |
| Implementation is complete and CORE acceptance has not run; no blocker is known | UNKNOWN | COMPLETE | NOT_RUN | INCOMPLETE | PENDING | PENDING_CORE_ACCEPTANCE | Do not infer `PASS`, `BLOCKED`, or `NOT_REQUIRED`. |
| An explicit Plan rationale declares CORE not required and all other closure conditions are satisfied | ACHIEVED | COMPLETE | NOT_REQUIRED | PASS | NOT_REQUIRED | DONE | Legal only with explicit Plan rationale and every other DONE prerequisite satisfied. |
| CORE is set `NOT_REQUIRED` without Plan rationale | UNKNOWN | ESCALATED | NOT_REQUIRED | NOT_RUN | PENDING | REPLAN_REQUIRED | Invalid contract state; replan rather than silently treating it as `NOT_RUN`. |

The `DONE` row is illustrative only and assumes every other §7.10 closure condition is satisfied. It does not alter this task’s CORE gates.

### F04 — Replan routing when approved premise is invalidated

**Synthetic condition:** new evidence invalidates an approved load-bearing semantic premise. This takes precedence over ordinary mechanical fix routing.

```yaml
PRIMARY_OUTCOME_STATUS: UNKNOWN
IMPLEMENTATION_STATUS: ESCALATED
CORE_ACCEPTANCE_STATUS: NOT_RUN
REQUIRED_VERIFICATION_STATUS: INCOMPLETE
INDEPENDENT_ACCEPTANCE_STATUS: PENDING
TASK_CLOSURE_STATUS: REPLAN_REQUIRED
BLOCKERS:
  - scope: IMPLEMENTATION
    subject: approved semantic premise
    result: BLOCKED
    class: PLAN_PREMISE_INVALIDATED
    task_regression_evidence: UNKNOWN
    evidence: synthetic contradictory premise evidence
    next_action: escalate and replan the affected contract decision
    owner: Planner
    waiver_allowed: NO
```

**Expected invariant:** do not continue by improvising a new contract, and do not report ordinary `FIX_REQUIRED` when the approved premise itself is invalidated.

### F05 — Required baseline unavailable

**Synthetic condition:** a planned `BASELINE_DELTA` item cannot establish a trustworthy pre-change baseline. No PASS/FAIL inference is allowed from an absent baseline.

```yaml
PRIMARY_OUTCOME_STATUS: UNKNOWN
IMPLEMENTATION_STATUS: COMPLETE
CORE_ACCEPTANCE_STATUS: PASS
REQUIRED_VERIFICATION_STATUS: INCOMPLETE
INDEPENDENT_ACCEPTANCE_STATUS: PENDING
TASK_CLOSURE_STATUS: PENDING_REQUIRED_VERIFICATION
CHECK:
  CHECK_ID: SYNTHETIC-DELTA-01
  GOAL_CRITICALITY: SUPPORTING
  EVIDENCE_ROLE: REPOSITORY_HEALTH
  CLOSURE_GATE: BASELINE_DELTA
  BASELINE_REQUIRED: YES
  CHECK_RESULT: BLOCKED
  FAILURE_CLASSIFICATION: BASELINE_UNAVAILABLE
  WAIVER_ALLOWED: NO
  WAIVER_AUTHORITY: NONE
  WAIVER_STATUS: NOT_ALLOWED
BLOCKERS:
  - scope: REQUIRED_VERIFICATION
    subject: SYNTHETIC-DELTA-01 baseline
    result: BLOCKED
    class: AUTHORITY_REQUIRED
    task_regression_evidence: UNKNOWN
    evidence: trustworthy pre-change signature comparison unavailable
    next_action: establish an approved equivalent baseline or report the item unresolved
    owner: verification owner
    waiver_allowed: NO
```

**Expected invariant:** no assumption of unchanged behavior; keep the original item `BLOCKED`; aggregate is `INCOMPLETE` when other required evidence is valid, or `BLOCKED` only if the entire phase cannot reach a valid conclusion.

### F06 — Baseline-delta check with unchanged pre-existing debt

**Synthetic condition:** a trustworthy same-command/environment baseline proves an existing signature predates mutation; the post-change run shows no new or worsened relevant signature. The delta criterion passes, while the existing debt remains disclosed and is not called clean.

```yaml
PRIMARY_OUTCOME_STATUS: UNKNOWN
IMPLEMENTATION_STATUS: COMPLETE
CORE_ACCEPTANCE_STATUS: PASS
REQUIRED_VERIFICATION_STATUS: PASS
INDEPENDENT_ACCEPTANCE_STATUS: PENDING
TASK_CLOSURE_STATUS: READY_FOR_INDEPENDENT_ACCEPTANCE
CHECK:
  CHECK_ID: SYNTHETIC-DELTA-02
  GOAL_CRITICALITY: SUPPORTING
  EVIDENCE_ROLE: REPOSITORY_HEALTH
  CLOSURE_GATE: BASELINE_DELTA
  BASELINE_REQUIRED: YES
  CHECK_RESULT: PASS
  FAILURE_CLASSIFICATION: NONE
  WAIVER_ALLOWED: NO
  WAIVER_AUTHORITY: NONE
  WAIVER_STATUS: NOT_REQUESTED
BASELINE_NOTE: Existing synthetic signature is disclosed as PRE_EXISTING_FAILURE; no new/worsened relevant signature was observed.
```

**Expected invariant:** `PASS` belongs only to the named delta check’s criterion. It does not relabel the known baseline failure as clean or as `PASS`.

### F07 — Hard-clean pre-existing debt

**Synthetic condition:** a `HARD_CLEAN` item is red because of a trustworthy pre-existing failure. Since the whole named gate must be clean, the item is `FAIL`; closure is pending, but implementation and CORE facts remain intact.

```yaml
PRIMARY_OUTCOME_STATUS: ACHIEVED
IMPLEMENTATION_STATUS: COMPLETE
CORE_ACCEPTANCE_STATUS: PASS
REQUIRED_VERIFICATION_STATUS: INCOMPLETE
INDEPENDENT_ACCEPTANCE_STATUS: PENDING
TASK_CLOSURE_STATUS: PENDING_REQUIRED_VERIFICATION
CHECK:
  CHECK_ID: SYNTHETIC-HARD-CLEAN-02
  GOAL_CRITICALITY: SUPPORTING
  EVIDENCE_ROLE: REPOSITORY_HEALTH
  CLOSURE_GATE: HARD_CLEAN
  BASELINE_REQUIRED: NO
  CHECK_RESULT: FAIL
  FAILURE_CLASSIFICATION: PRE_EXISTING_REPOSITORY_FAILURE
  WAIVER_ALLOWED: NO
  WAIVER_AUTHORITY: NONE
  WAIVER_STATUS: NOT_ALLOWED
```

**Expected invariant:** pre-existing hard-clean debt may block `DONE`, but is not by itself evidence of implementation failure or a task regression.

### F08 — Formal waiver preserves the original item result (semantics only)

**Synthetic condition:** a hypothetical, unrelated fixture Plan explicitly allows waiver of `SYNTHETIC-WAIVER-01` and names an authorized project owner. A formal waiver record is complete. This scenario tests the v2 rule that waiver changes aggregate closure treatment, never the check’s original result. It is not a waiver request or approval for any task gate here.

```yaml
PRIMARY_OUTCOME_STATUS: ACHIEVED
IMPLEMENTATION_STATUS: COMPLETE
CORE_ACCEPTANCE_STATUS: PASS
REQUIRED_VERIFICATION_STATUS: WAIVED
INDEPENDENT_ACCEPTANCE_STATUS: NOT_REQUIRED
TASK_CLOSURE_STATUS: DONE
CHECK:
  CHECK_ID: SYNTHETIC-WAIVER-01
  GOAL_CRITICALITY: SUPPORTING
  EVIDENCE_ROLE: REPOSITORY_HEALTH
  CLOSURE_GATE: HARD_CLEAN
  BASELINE_REQUIRED: NO
  CHECK_RESULT: FAIL
  WAIVER_ALLOWED: YES
  WAIVER_AUTHORITY: hypothetical project owner, explicitly named by that fixture Plan
  WAIVER_STATUS: APPROVED
WAIVER_RECORD:
  WAIVED_BY: hypothetical authorized project owner
  WAIVER_SCOPE: SYNTHETIC-WAIVER-01 only
  RATIONALE: hypothetical closure remains decision-valid under that fixture Plan
  EVIDENCE: hypothetical baseline/non-regression evidence
  RESIDUAL_RISK: hypothetical pre-existing debt remains
  APPROVED_AT: synthetic timestamp
  REVIEW_OR_EXPIRY_TRIGGER: hypothetical next release
TASK_GATE_POLICY: Every actual gate in this task remains WAIVER_ALLOWED=NO and WAIVER_AUTHORITY=NONE.
```

**Expected invariant:** item result stays `FAIL`, never becomes item-level `PASS`; aggregate `WAIVED` is legal only when every otherwise-unsatisfied required gate has an authorized valid waiver and no unwaived blocker/failure remains. The sample `DONE` is conditional on all §7.10 prerequisites in this unrelated hypothetical fixture.

### F09 — Stage 05 pending before independent acceptance runs

**Synthetic condition:** Stage 04 is closure-ready for an independent acceptance stage, which has not yet run. This is pending, not blocked or passed.

```yaml
PRIMARY_OUTCOME_STATUS: ACHIEVED
IMPLEMENTATION_STATUS: COMPLETE
CORE_ACCEPTANCE_STATUS: PASS
REQUIRED_VERIFICATION_STATUS: PASS
INDEPENDENT_ACCEPTANCE_STATUS: PENDING
TASK_CLOSURE_STATUS: READY_FOR_INDEPENDENT_ACCEPTANCE
STAGE_04_SNAPSHOT:
  STAGE_04_REPORTED_IMPLEMENTATION_STATUS: COMPLETE
  STAGE_04_REPORTED_CORE_ACCEPTANCE_STATUS: PASS
  STAGE_04_REPORTED_REQUIRED_VERIFICATION_STATUS: PASS
  STAGE_04_EXECUTION_ARTIFACT_SHA256: synthetic-stage04-artifact-sha256
```

**Expected invariant:** retain the immutable Stage 04 snapshot in the Stage 05 artifact before reporting Stage 05 current fields.

### F10 — Stage 05 environment blocker with immutable Stage 04 snapshot

**Synthetic condition:** Stage 05 cannot run one independent acceptance item because a required model/runtime environment is unavailable. Stage 04 had already reported implementation `COMPLETE`, CORE `PASS`, and verification `INCOMPLETE`; the new Stage 05 blocker must preserve all three exactly.

```yaml
PRIMARY_OUTCOME_STATUS: ACHIEVED
IMPLEMENTATION_STATUS: COMPLETE
CORE_ACCEPTANCE_STATUS: PASS
REQUIRED_VERIFICATION_STATUS: INCOMPLETE
INDEPENDENT_ACCEPTANCE_STATUS: BLOCKED
TASK_CLOSURE_STATUS: ACCEPTANCE_BLOCKED
STAGE_04_SNAPSHOT:
  STAGE_04_REPORTED_IMPLEMENTATION_STATUS: COMPLETE
  STAGE_04_REPORTED_CORE_ACCEPTANCE_STATUS: PASS
  STAGE_04_REPORTED_REQUIRED_VERIFICATION_STATUS: INCOMPLETE
  STAGE_04_EXECUTION_ARTIFACT_SHA256: synthetic-immutable-stage04-artifact-sha256
CHECK:
  CHECK_ID: SYNTHETIC-INDEPENDENT-ENV-01
  CHECK_RESULT: BLOCKED
  BLOCKER_SCOPE: ENVIRONMENT
  FAILURE_CLASSIFICATION: ENVIRONMENT_FAILURE
BLOCKERS:
  - scope: INDEPENDENT_ACCEPTANCE
    subject: SYNTHETIC-INDEPENDENT-ENV-01
    result: BLOCKED
    class: ENVIRONMENT_FAILURE
    task_regression_evidence: NONE
    evidence: synthetic runtime unavailable
    next_action: restore the environment and rerun the independent acceptance item
    owner: acceptance owner
    waiver_allowed: NO
```

**Expected invariant:** Stage 05’s item-level blocker does not rewrite Stage 04 aggregate facts or snapshot; current independent acceptance is `BLOCKED`; closure is `ACCEPTANCE_BLOCKED`.

### F11 — Contradictory-state rejection

**Synthetic condition:** candidate terminal state claims implementation `COMPLETE` while routing closure as `IMPLEMENTATION_BLOCKED`. This violates the legal-state invariant and is rejected rather than normalized by guessing.

```yaml
REJECTED_CANDIDATE:
  PRIMARY_OUTCOME_STATUS: UNKNOWN
  IMPLEMENTATION_STATUS: COMPLETE
  CORE_ACCEPTANCE_STATUS: NOT_RUN
  REQUIRED_VERIFICATION_STATUS: NOT_RUN
  INDEPENDENT_ACCEPTANCE_STATUS: PENDING
  TASK_CLOSURE_STATUS: IMPLEMENTATION_BLOCKED
REJECTION:
  code: CONTRADICTORY_IMPLEMENTATION_AND_CLOSURE_SUBJECTS
  reason: IMPLEMENTATION_BLOCKED requires IMPLEMENTATION_STATUS=BLOCKED for unfinished implementation unable to continue.
  action: reject terminal routing; correct from evidence and re-evaluate precedence.
```

**Expected invariant:** also reject any candidate with `IMPLEMENTATION_STATUS: BLOCKED` and `TASK_CLOSURE_STATUS: DONE`. Do not silently replace one subject with another.

### F12 — Evidence-backed legacy normalization

**Synthetic historical condition:** an old single-enum artifact says `IMPLEMENTATION_BLOCKED`, but its evidence proves implementation actions and CORE evidence were complete and the blocker was verification-only. Preserve the historical value and record an evidence-backed normalized interpretation; do not string-replace the source.

```yaml
HISTORICAL_VALUE:
  LEGACY_STATUS: IMPLEMENTATION_BLOCKED
NORMALIZED_INTERPRETATION:
  PRIMARY_OUTCOME_STATUS: UNKNOWN
  IMPLEMENTATION_STATUS: COMPLETE
  CORE_ACCEPTANCE_STATUS: PASS
  REQUIRED_VERIFICATION_STATUS: INCOMPLETE
  INDEPENDENT_ACCEPTANCE_STATUS: PENDING
  TASK_CLOSURE_STATUS: PENDING_REQUIRED_VERIFICATION
  NORMALIZATION_CONFIDENCE: EVIDENCE_BACKED
  EVIDENCE: synthetic historical artifact proves implementation/CORE completion and verification-only blocker
```

**Expected invariant:** if evidence instead shows implementation was genuinely unfinished and unable to continue, retain `IMPLEMENTATION_STATUS: BLOCKED` / `TASK_CLOSURE_STATUS: IMPLEMENTATION_BLOCKED`. All other legacy values require artifact-specific evidence; no blind string mapping.

### F13 — All prerequisites for `DONE`

**Synthetic positive condition:** all applicable closure requirements have valid evidence. `DONE` is solely the overall closure field; neither implementation completion nor a passing individual check is enough on its own.

```yaml
PRIMARY_OUTCOME_STATUS: ACHIEVED
IMPLEMENTATION_STATUS: COMPLETE
CORE_ACCEPTANCE_STATUS: PASS
REQUIRED_VERIFICATION_STATUS: PASS
INDEPENDENT_ACCEPTANCE_STATUS: PASS
TASK_CLOSURE_STATUS: DONE
DONE_PREREQUISITES:
  - primary outcome is ACHIEVED for the user-visible objective, or Plan defines an explicit equivalent closure condition
  - current approved implementation scope is COMPLETE
  - CORE acceptance is PASS, or NOT_REQUIRED with explicit Plan rationale
  - required verification is PASS, NOT_REQUIRED, or WAIVED under approved gate/waiver policy
  - independent acceptance is PASS or NOT_REQUIRED
  - no unresolved hard closure blocker remains
  - final diff/work is in scope and unrelated work is preserved
  - required durable artifacts and freshness links are valid
```

**Expected invariant:** if any listed prerequisite is absent, keep the accurate non-DONE closure state (`PENDING_CORE_ACCEPTANCE`, `CORE_ACCEPTANCE_BLOCKED`, `PENDING_REQUIRED_VERIFICATION`, `READY_FOR_INDEPENDENT_ACCEPTANCE`, `ACCEPTANCE_BLOCKED`, or another precedence-selected state). Never use `DONE` for implementation-only completion.

## Completeness index

| Plan R11 / Decision G required case | Fixture |
|---|---|
| Canonical incident | F01 |
| True implementation blocker | F02 |
| CORE FAIL / BLOCKED / NOT_RUN / explicit NOT_REQUIRED | F03 |
| Replan routing | F04 |
| Baseline unavailable and baseline-delta | F05, F06 |
| Hard-clean pre-existing debt | F01, F07 |
| Formal waiver preserving original item result | F08 |
| Stage 05 pending / environment blocker with immutable Stage 04 snapshot | F09, F10 |
| Contradictory-state rejection | F11 |
| Legacy normalization | F12 |
| All DONE prerequisites | F13 |
