# Plan Review Report

## REVIEW_METADATA
- TASK_ID: `T20260923-2050-01-local-extraction-adherence`
- REVIEW_ATTEMPT: `05`
- REVIEWED_PLAN_REVISION: `5`
- REVIEWED_PLAN_SHA256: `940bc274ca61f77340b19fd256b62ad848affdb64dcbbf340d8eb786e2305e69`
- PLAN_SNAPSHOT_PATH: `.agent/tasks/T20260923-2050-01-local-extraction-adherence/review/attempt-05/plan_snapshot.md`
- Repository anchor observed: `/Users/hsiaojohnny/dev/convert`, branch `fix/qwen-local-quality-parity`, HEAD `ab2528b718e8c91557fd72db174b0f9bb78d3a68`; the task directory is the only observed untracked worktree path before this review artifact was created.
- Reviewer runtime/model: Codex fresh review context; no tests, baseline, backend, model inference, or E2E executed.
- Preflight: `review/attempt-05/` was absent before creation; canonical plan and snapshot both hashed to the exact SHA above before this report was written.

## OWNER_VERDICT
The plan still targets the right user outcome: improve local-model meeting-record quality toward cloud parity without claiming equivalence, preserve prior gains, remain model/platform independent, and report numeric results honestly. Rev5 correctly addresses the clean-worktree invalidation with a detached worktree and preserves the task evidence in place; it does not modify runner clean-gate semantics, hide/move/commit planning evidence, or alter the product contract. The required quality, rollback, status-history, and E2E provenance gates remain materially justified and optional S1–S5 work remains non-gating.

The plan is not ready for handoff because its new privacy/provenance claim is contradicted by the unchanged runner: the runner writes full `raw_response` objects into files under `--artifacts-dir`, while rev5 requires that directory to contain only redacted metadata/hashes and explicitly rejects raw payload there. This is a material security/evidence-contract gap, not a reviewer preference. The plan must be revised to resolve that contradiction before E2E can be decision-valid.

## GOAL_BASELINE
From the authoritative source `/Users/hsiaojohnny/.codex/attachments/bbb6190c-103e-4a0f-afca-3142aa462bb0/pasted-text-1.txt`:
- Primary outcome: make local-model meeting records not materially worse than the cloud Gemini records, while reporting the remaining gap and improvement percentages honestly.
- Must-not-break constraints: no model/platform-specific branches; one code path across macOS/LM Studio and Windows/Ollama; never test `qwen3.6-35b-a3b-splash`; do not claim cloud-level quality; preserve prior P7-B behavior when new controls are disabled; retain valid commit/push and independent-acceptance provenance.
- This wave must address extraction omissions and delivery/adherence omissions while protecting coverage, density, cost, valid DOCX output, privacy, and truthful closure routing.

## GOAL_ALIGNMENT
Rev5's primary outcome and critical path match the baseline. CORE-1 addresses extraction omissions; CORE-2 addresses facts present in notes but absent from delivery; CORE-B/C/D/E/F and anti-gaming protect observable quality and measurement validity. The plan keeps Windows/Ollama real-machine behavior `[UNVERIFIED]` and does not claim cloud equivalence.

## NECESSITY_AND_TRACEABILITY
The material product requirements remain traceable: C1b/C1c address the verified chunk-level failure; C2a/C2c address fact-level/adherence failures; CORE-B/C/D preserve prior quality; CORE-E controls cost; CORE-F and ANTI-GAMING protect deliverable and measurement validity; local-only settings protect the cloud contract. The detached worktree is necessary to satisfy the existing whole-worktree clean gate without mutating runner semantics or relocating task evidence. E2E-COMMIT-PROVENANCE is a SUPPORTING/MUST_NOT_BREAK gate with an explicit decision-validity and privacy rationale, not a product-quality veto.

## GATE_AND_VETO_AUDIT
The collection-style quality thresholds, fixed wall-clock source, pre-registered caps, no-waiver policy, and scoped C1c degradation are proportionate. The plan correctly routes provenance failure to affected E2E-dependent CORE checks being `BLOCKED` while preserving implementation status; it does not call this an implementation blocker. FULL-SUITE remains SUPPORTING/BASELINE_DELTA and does not veto the core meeting-record path merely because it is a closure gate. The status fixture inventory covers the required §7 cases, including history-preserving Stage 04 snapshots, blocked/not-run states, baseline debt, waiver preservation, legacy normalization, contradictions, and DONE prerequisites.

## COUPLING_AND_FAILURE_CONTAINMENT
The detached checkout confines the runner's clean-status predicate to the product/test commit while leaving the main task evidence untouched. Absolute paths are appropriate: the runner resolves an absolute `--artifacts-dir` directly, an absolute `--runtime-dir` directly, and derives its own `REPO_ROOT` from the detached script path. C1c, C2b, and provenance failure scopes remain local and explicit.

## DESIGN_ECONOMY
Rev5 is the smallest apparent change that addresses the observed dirty-worktree premise without changing product or runner semantics: a clean detached checkout, fixed expected revision, and separated evidence/runtime paths. No new model calls or unrelated architecture are introduced. The remaining defect is not excess complexity; it is that the runner's existing artifact writer does not satisfy the plan's stated redaction boundary.

## CRITICAL_PATH_AND_PRIORITY
The plan still runs baseline and deterministic contract checks before implementation, commits only product code/tests before E2E, runs the four required model trials only after the clean detached preflight, and performs independent acceptance afterward. Supporting S1/S3/S4/S5 work is explicitly subordinate. Rev5 also preserves the prior escalation and execution history rather than rewriting it.

## REQUIREMENT_FIDELITY
The fixed audio/template/mode, prohibited model, no-parity language, cross-platform requirement, prior-gain preservation, and later commit/push requirements are retained. Rev5 directly answers the prior Stage 04 escalation: it neither changes the runner clean gate nor manufactures a clean main worktree by ignoring, moving, deleting, or committing task evidence.

## GROUNDING_AND_DRIFT
The requested plan SHA is verified exactly. The prior Stage 04 `execution.md` and `escalation.md` document the rev4 invalidation and show that no product/test/runner work, baseline, backend, model, or E2E was run. Attempt-04 approved rev4 only; rev5 correctly requires a new review and does not inherit that approval.

Runner/source checks performed read-only:
- `REPO_ROOT = Path(__file__).resolve().parents[2]` (`scripts/e2e/run_owned_e2e.py:78`), so execution from a detached checkout uses that checkout as the repository root.
- `--expected-revision` is accepted and takes precedence over `git rev-parse HEAD` (`:209-218`, `:1764`); the health gate compares the actual build revision with that expected value (`:1948-1967`).
- Absolute `--artifacts-dir` and `--runtime-dir` are accepted without rebasing (`:1823-1832`, `:454-470`); `data/cache/*` is ignored (`.gitignore:55`).
- The clean gate remains unchanged and fails closed before backend startup (`:421-428`, `:1888-1895`).

## ARCHITECTURE_AND_CONTRACTS
### RV-001 through RV-006 / I1 through I5
The earlier material findings are resolved in rev5 insofar as still relevant: I1/I2/I4/I5 are addressed by fixed cost sources, set semantics/noise disclosure, pinned E2E values/defaults, and the gemma whole-record floor; I3 is addressed by separating fact-level expectations from adherence; RV-001 is addressed by the §8.1 matrix and §8.2 fixtures; RV-002 by excluding the stale replay prediction; RV-003 by same-path Qwen evidence and a fixed conservative cap; RV-004 by full-list preflight and transcript-only degradation; RV-005 by local-only refinement settings; RV-006 by the explicit fixture inventory. No prior approved finding was silently reopened.

### RV-007 — OPEN
- severity: `MAJOR`
- category: `SECURITY` / `SEMANTIC_CONTRACT`
- affected plan: rev5 change log §0.3; §8 step 5; §8.1 `E2E-COMMIT-PROVENANCE`; §8.1 privacy paragraph.
- evidence: rev5 says `--artifacts-dir` contains only redacted metadata/hash and that raw payload must not enter it (`plan.md:80-81,272-274,297,303`). The unchanged runner writes `health_snapshot.json` with `raw_response: health` (`scripts/e2e/run_owned_e2e.py:1949-1958`) and `model_snapshot.json`/`model_snapshot_end.json` with `raw_response: raw` (`:347-359`). Its CLI also describes `--artifacts-dir` as redacted-only (`:1747-1754`), so the implementation and stated contract disagree.
- failure/rework mechanism: a conforming detached-worktree E2E run will place full provider/backend response payloads in the main task evidence directory. Stage 05 then cannot truthfully mark `E2E-COMMIT-PROVENANCE` or the security/privacy boundary clean, and retaining/deleting those files after the fact would conflict with the plan's append-only evidence and no-hide/no-move rules. This can expose more external response data than the approved evidence contract permits and makes the E2E decision invalid even though HEAD/porcelain provenance is correct.
- smallest required correction: revise the plan before handoff to make the evidence boundary executable against the unchanged runner—explicitly identify and resolve the runner's raw-response fields with an authorized, evidence-preserving decision (or explicitly stop/replan the E2E path if the no-runner-semantics constraint forbids that resolution). The plan must not rely on an after-the-fact deletion, relocation, or unrecorded redaction, and Stage 05 must retain the original artifact/result classification if the boundary cannot be satisfied.

The detached worktree mechanics themselves are supported and do not constitute a finding: the runner's path resolution and CLI behavior match the rev5 invocation, and the status-history/provenance routing is internally consistent.

## DATA_SECURITY_RELIABILITY
The registry-first/unique-candidate-only C3 rules and raw-runtime separation are otherwise sound. The open RV-007 is the material privacy issue: `security-privacy.md` prohibits full request/response dumps and requires redaction, while the runner's artifact writer currently emits `raw_response` into the supposedly redacted location.

## IMPLEMENTATION_SEQUENCE
The sequence is otherwise executable: baseline, deterministic checks, implementation, product/test commit, detached clean preflight, four E2E runs, then Stage 05. However, the artifact-boundary decision must occur before implementation/E2E because it affects acceptance validity and cannot safely be delegated to Stage 04 improvisation.

## TESTABILITY_AND_ACCEPTANCE
The plan has strong status-aware acceptance coverage, including E2E-COMMIT-PROVENANCE failure routing, immutable Stage 04 snapshots, and preservation of historical `ESCALATED`/`REPLAN_REQUIRED` evidence. The unresolved raw-response mismatch means the provenance/privacy fixture is not currently executable as written; it needs a plan-level correction and an explicit evidence rule before Stage 04.

## SCOPE_AND_COMPLEXITY
The plan remains economical and goal-aligned overall. No additional untraceable scope was found. The open issue is a contract/grounding inconsistency in an existing runner, not a request to add a new product subsystem.

## FINDINGS
### RV-007
- severity: `MAJOR`
- category: `SECURITY` / `SEMANTIC_CONTRACT`
- status: unresolved
- exact hash under review: `940bc274ca61f77340b19fd256b62ad848affdb64dcbbf340d8eb786e2305e69`
- required action: resolve the runner artifact redaction contradiction before Stage 03/Handoff.

## REQUIRED_PLAN_CHANGES
1. Replan the rev5 E2E evidence boundary so the no-raw-payload requirement is actually satisfied by the unchanged runner contract, or explicitly route the E2E path to a new scoped replan if that cannot be satisfied without a permitted runner/evidence-contract change.
2. Preserve the current detached-worktree clean-gate solution, status-history rules, and E2E-COMMIT-PROVENANCE failure routing unless the corrected evidence decision directly changes them.

## RESIDUAL_MINOR_NOTES
- Windows/Ollama real-machine behavior remains correctly `[UNVERIFIED]` and must not be reported as acceptance.
- The runner source hash observed during review was `3a6557fcdda65b2ccb726416a3b79b094853caf09e4d0bf7ef9c8e72621d975b`; no source was changed.
- No tests, baseline, backend, model inference, or E2E were run, as required.

FINAL_STATUS: `PLAN_REVISION_REQUIRED`
NEXT_ACTION: Stage 01 revision mode on the same TASK_ID to resolve RV-007, then submit the resulting plan revision for a fresh Stage 02 review.
