# Stage 02 Independent Plan Review — attempt-07

- `TASK_ID`: `T20260923-2050-01-local-extraction-adherence`
- `REVIEWED_PLAN_REVISION`: `7`
- `REVIEWED_PLAN_SHA256`: `a84b06b71a5d6d57b80bfbf1823a91cc5545eb45f5ace314fe46544636bb46e9`
- `PLAN_SNAPSHOT`: `review/attempt-07/plan_snapshot.md`
- `PLAN_SNAPSHOT_SHA256`: `a84b06b71a5d6d57b80bfbf1823a91cc5545eb45f5ace314fe46544636bb46e9`
- `SNAPSHOT_LINES`: `420`
- `REVIEW_MODE`: fresh Stage 02; read-only for canonical plan/product/test code
- `TESTS_RUN`: none; no backend, model inference, baseline, or E2E run

## GOAL_BASELINE

Source: `/Users/hsiaojohnny/.codex/attachments/bbb6190c-103e-4a0f-afca-3142aa462bb0/pasted-text-1.txt`.

- **PRIMARY_OUTCOME:** improve local-model meeting-record quality so it is not materially worse than the cloud result, with numeric improvement reporting and honest disclosure when targets are missed.
- **CORE:** address the two P7-B failures: extraction-side fact loss and generation-side adherence; preserve the achieved coverage/density quality; validate with the fixed audio/template/quality mode and required four local E2Es.
- **MUST_NOT_BREAK:** model/platform/OS agnosticism and one code path; no forbidden model/platform branches; cloud behavior unchanged; P7-B prompts/metrics/output bytes recoverable with new controls off; no unsafe/incomplete record accepted as a full record; evidence must remain privacy-safe and decision-valid.
- **SUPPORTING:** deterministic proper-noun normalization, status-contract fixtures, full-suite baseline delta, raw-cache provenance, detached clean-worktree execution, and operational reporting.
- **BEST_EFFORT / NON-GOAL:** no claim of reaching cloud parity; optional S3/S5 experiments and cross-run transcript comparison must not gate the core path.
- **CRITICAL_PATH:** reviewed plan → fresh handoff/Stage 04 → deterministic local-only contracts and exact rollback proof → focused verification and baseline delta → clean detached-worktree four-run E2E with redacted evidence → independent Stage 05 → only then commit/push closure.

## PREFLIGHT_AND_FRESHNESS

- `[VERIFIED]` Current plan declares `PLAN_REVISION: 7`, `PLAN_STATUS: READY_FOR_REVIEW`, `TASK_ID` matches.
- `[VERIFIED]` `review/attempt-07/` did not exist before this review.
- `[VERIFIED]` Exact snapshot was created before detailed plan judgment; plan and snapshot SHA-256 are identical.
- `[VERIFIED]` `review/attempt-06/review_report.md` and `handoff.md` are explicitly rev6 / SHA `79a92f...`; they are stale and were not used as approval or handoff for rev7.
- `[VERIFIED]` `execution.md` / `escalation.md` record the rev6 all-off C2 contradiction, preserve the partial WIP, and show the authoritative pre-mutation baseline at fixed HEAD `ab2528b` (`1129 passed, 2 skipped`). This evidence was used only as grounding; no new check was run and no WIP result was promoted to rev7 acceptance.

## TOP_DOWN_REVIEW

### Alignment and economy

`[VERIFIED]` The rev7 goal and critical path remain aligned with the authoritative request. The two new default-false controls are a minimal direct response to the rev6 contradiction: `LOCAL_LLM_RECORD_FACT_COVERAGE_ENABLED` gates C2a fact expectations/metrics, and `LOCAL_LLM_RECORD_ADHERENCE_ENABLED` gates C2c local refinement prompt text. Retaining the legacy coverage mode/categories instead of redefining `mode=off` is correct and preserves the prior contract.

`[VERIFIED]` CORE/SUPPORTING/BEST_EFFORT separation is generally proportional. CORE-A–F, local/cloud contracts, rollback, platform independence, and anti-gaming are tied to the user outcome or MUST_NOT_BREAK invariants. `FULL-SUITE` is SUPPORTING with BASELINE_DELTA, not a product-quality veto. E2E provenance is SUPPORTING but has an explicit decision-validity rationale because the runner fails closed on dirty worktrees. Commit/push is correctly deferred until Stage 05 and required checks close.

`[VERIFIED]` The plan preserves the local-only boundary in its stated design and repository grounding: current code uses local mode-specific builders and a separate cloud refinement loop; the plan requires the new flags to be ignored by cloud behavior and adds explicit cloud byte assertions. The existing runner boundary is also correctly treated as raw for the entire artifacts directory, with raw runtime/cache outside task evidence and a fixed allowlist derivative inside task evidence.

## BOTTOM_UP_FINDINGS

### MAJOR-01 — BYTE-ROLLBACK acceptance is not executable enough

- **Affected plan:** §6 lines 289–294; §8 step 3; `BYTE-ROLLBACK` matrix row §8.1.
- **Evidence:** The plan requires prompt/metrics/output bytes to match P7-B/`ab2528b`, but only states “unit tests” and a generic “fixed P7-B/ab2528b” comparison. It does not name the deterministic test harness, exact baseline source/artifact, comparison fields, or how output bytes are compared without model nondeterminism. The focused repository grounding already identifies that no golden directory exists and that a concrete `git show ab2528b`/fixture or equivalent stub comparison is needed (`prep/site-map-core12.md` §“byte 級回退證明怎麼寫”).
- **Failure mechanism:** Stage 04 could implement both flags with false defaults and pass local unit assertions while failing to prove that C2a issue/metrics bytes and C2c refinement prompt bytes are exactly unchanged relative to P7-B. Stage 05 would then have an acceptance gate whose baseline is not reproducible or decision-valid.
- **Smallest correction:** In the canonical plan, specify one deterministic zero-model-call rollback procedure and its immutable baseline: exact test file/fixture or `git show`-derived fixture, exact local-mode inputs, exact prompt/metrics/output byte fields, expected hashes/diff rule, and evidence artifact written by Stage 04. Keep the two flag proofs independent and include the legacy `mode=enforce` plus default categories state required by §6. The procedure must also explicitly assert cloud prompt/output bytes are unchanged.

### MAJOR-02 — Required status-fixture inventory has a duplicate identifier/row

- **Affected plan:** §8.2, around the `SCF-03-CORE-FAIL` entries.
- **Evidence:** `SCF-03-CORE-FAIL` appears twice with the same fixed input and expected result. `STATUS-CONTRACT-FIXTURES` is a required `HARD_CLEAN` check, and the plan requires each fixture to be recorded by `FIXTURE_ID`.
- **Failure mechanism:** Stage 04/05 evidence cannot unambiguously enumerate or reconcile the required fixture set; a result keyed by `FIXTURE_ID` can overwrite or silently collapse one row, undermining the status/closure proof and freshness audit.
- **Smallest correction:** Remove the duplicate row, or assign it a distinct ID with a materially distinct scenario and expected route. Preserve a unique-ID assertion in the fixture inventory/evidence procedure.

## REQUIRED CONTRACT CHECKS

- `[VERIFIED]` C2a/C2c all-off semantics are now explicit and distinct from legacy `LOCAL_LLM_RECORD_COVERAGE_MODE=off`; this directly addresses the rev6 escalation.
- `[VERIFIED]` C2b local max/budget defaults and cloud shared-loop preservation are explicitly planned and have repository call-site grounding.
- `[VERIFIED]` Baseline reuse is conditional on execution evidence being pre-mutation at fixed HEAD; fallback requires a new task-specific `mktemp -d` directory and forbids touching `/tmp/test_scratch` or old scratch.
- `[VERIFIED]` Detached worktree, `--expected-revision`, zero porcelain, raw-cache boundary, redacted derivative allowlist, and no raw payload in task evidence are explicitly preserved. No runner/ignore-rule bypass is proposed.
- `[VERIFIED]` Stage 05 is independent and read-only; commit/push is after Stage 05 plus closure, with no force-push and remote fast-forward checks.
- `[UNVERIFIED]` The new flags, their `.env.example` entries, implementation tests, and final cloud/local assertions do not yet exist in the current WIP; this is expected pre-implementation state, not evidence of approval.

## OWNER_VIEW

- **Essential:** make local records capture the missing facts and follow the existing issue list, while proving old behavior/cloud behavior remain unchanged when the new controls are off.
- **Optional/deferred:** C3 normalization experiments, S3/S5 ablations, and cross-run comparisons.
- **Whole-task blockers:** a failed CORE quality gate, invalid rollback proof, invalid raw/evidence boundary, or missing clean-commit provenance can invalidate the result; the plan gives a decision-validity rationale for each. Full-suite pre-existing debt should remain a closure-pending baseline issue, not a product veto.
- **Biggest remaining risk:** exact byte rollback and status-fixture evidence are still underspecified/ambiguous, so acceptance could be non-reproducible even if the implementation is mechanically correct.

## GATE

PLAN_REVISION_REQUIRED

The rev7 design resolves the specific rev6 C2 all-off contradiction and preserves the correct local/cloud, baseline, raw-cache, detached-worktree, status-routing, and post-Stage-05 push boundaries. It is not ready for Handoff because MAJOR-01 can invalidate the central rollback acceptance and MAJOR-02 makes a required closure fixture inventory ambiguous. Revise only those affected acceptance details, increment the plan revision, and obtain a fresh Stage 02 review; do not use attempt-06 approval or the rev6 handoff for the revised plan.
