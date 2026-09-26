# Plan Review Report

## REVIEW_METADATA

- TASK_ID: `T20260923-2050-01-local-extraction-adherence`
- REVIEW_ATTEMPT: `attempt-14`
- REVIEWED_PLAN_REVISION: `13`
- REVIEWED_PLAN_SHA256: `2b663c68a8f49d0cf769000db5d6d7629c54e589bff8e6c62a5168bc34fbe588`
- PLAN_SNAPSHOT_PATH: `.agent/tasks/T20260923-2050-01-local-extraction-adherence/review/attempt-14/plan_snapshot.md`
- SNAPSHOT_STATUS: `[VERIFIED]` byte-identical copy; before/after/snapshot SHA-256 values match and `cmp` exited 0
- Repository anchor observed: `[VERIFIED]` `/Users/hsiaojohnny/dev/convert`, branch `fix/qwen-local-quality-parity`; task artifacts are untracked and were not altered
- Reviewer runtime/model: Codex review runtime (informational)
- REVIEW_SCOPE: read-only plan review; no product edits, plan edits, tests, model inference, probes, builds, E2E, commit, or push

## OWNER_VERDICT

The plan targets the stated product outcome: formal local Gemma 4 31B and Qwen 3.8 27B paths must each remain strictly under a 10% gap from Gemini 3.5 Flash-lite on every frozen core quality dimension. Essential work is the frozen same-transcript comparison, candidate gate, persistence of the accepted local-only profile without changing cloud or explicit user overrides, a fresh post-persistence final cohort, and independent Stage 05 acceptance. Audio-to-DOCX remains supporting integration evidence and is explicitly scoped so an ASR/helper blocker does not erase valid parity evidence. No unresolved BLOCKER or MAJOR was found. The largest residual risk is limited generalization from one fixed meeting and human scoring; the plan correctly keeps that outside the core claim.

## GOAL_BASELINE

- **PRIMARY_OUTCOME:** Formal product local paths for Gemma 4 31B and Qwen 3.8 27B each produce meeting records whose gap from the project Gemini 3.5 Flash-lite result is strictly `<10%` on every core quality dimension. `[VERIFIED]` in the current plan's rev13 Owner/Goal Contract; the original user brief is not separately present in this reviewer context.
- **SUCCESS_EVIDENCE:** Freeze and hash the rubric before any output is generated/read; run candidate cloud/Gemma/Qwen 3x3 on one canonical transcript; persist only an accepted local-only profile; run a new final 3x3 with effective settings; independently rescore final outputs and verify scoped E2E/provenance. `[VERIFIED]` §§0.12–0.13, 5, 8, 8.1.
- **MUST_NOT_BREAK:** cloud/local isolation, explicit `.env`/process precedence, model/input/config provenance, no partial complete record, raw/derivative privacy separation, rollback, and orthogonal truthful status routing. `[VERIFIED]` §§0.12–0.13, 6, 8.1.
- **NON_GOALS:** Qwen 3.6, lowered threshold or favorable sample selection, post-freeze rubric changes, cross-meeting generalization, and Windows/Ollama real-device claims. `[VERIFIED]` §§0.12, 9–10.
- **CRITICAL_PATH:** rubric freeze/hash → candidate 3x3 and blind scoring → conditional persistence and precedence/isolation checks → fresh final 3x3 and independent scoring → supporting E2E → Stage 05 closure. `[VERIFIED]` §1 and §8.

## GOAL_ALIGNMENT

`[VERIFIED]` The primary outcome is parity of the formal persisted local product paths, not historical coverage/density or a temporary shell experiment. Candidate scores are explicitly non-final, and only the post-persistence final cohort can establish the outcome. The four core dimensions are non-compensating and the strict `<10%` rule is per output/per dimension.

## NECESSITY_AND_TRACEABILITY

`[VERIFIED]` Canonical transcript/checklist/model/config hashes, rubric freeze, blind aliases, profile persistence, fresh final cohort, and independent scoring each serve either parity decision validity or a stated must-not-break invariant. Candidate 3x3 is a conditional supporting decision gate; final parity and profile persistence are core. Historical P7-C controls are explicitly not themselves parity evidence.

## GATE_AND_VETO_AUDIT

`[VERIFIED]` Missing provenance, invalid rubric, invalid model/input identity, or hard factual error appropriately prevents a valid parity conclusion. Explicit environment overrides block only the profile-persistence claim and are not overwritten. ASR/helper/DOCX gates are supporting integration gates and do not veto valid same-transcript parity. `FULL-SUITE` is a SUPPORTING `BASELINE_DELTA` repository-health closure gate, not a product-quality veto. All material checks specify `WAIVER_ALLOWED`/authority and preserve original check results.

## COUPLING_AND_FAILURE_CONTAINMENT

`[VERIFIED]` Candidate failure stops persistence and later supporting E2E; final failure routes to evidence-backed replan. Extraction/refinement budgets fail the affected local summary atomically rather than discarding chunks or globally stopping the service. E2E/helper and cache/provenance failures remain scoped to integration evidence. Explicit user overrides are not silently changed.

## DESIGN_ECONOMY

`[VERIFIED]` The rev13 additions are bounded to the missing persistence/revalidation and reproducible scoring path, reusing existing config, summary entry points, transcript/checklist, cache, and status machinery. No new dependency or generic benchmark framework is introduced. Blind scoring/adjudication is proportionate to the subjective quality dimensions and strict threshold.

## CRITICAL_PATH_AND_PRIORITY

`[VERIFIED]` The plan proves candidate quality before changing defaults, then proves the actual persisted path before supporting E2E and closure. It does not spend E2E resources before candidate/final core evidence. Supporting observability remains non-vetoing unless it is an explicit decision-validity or safety prerequisite.

## REQUIREMENT_FIDELITY

`[VERIFIED]` Model keys are exact (`gemma-4-31b-it-mlx`, `qwen3.8-27b-splash`, `gemini-3.5-flash-lite`); the gap is relative to the cloud score, strictly `<10%`, equality at 10% fails, and no cross-dimension averaging or favorable sample selection is allowed. Candidate outputs cannot substitute for final outputs.

## GROUNDING_AND_DRIFT

`[VERIFIED]` Current repository anchors match the persistence boundary: `backend/core/config.py` contains the local controls/defaults and `.env.example` documents them; the plan preserves the known runner path-collision evidence and requires new runner-owned paths. The canonical transcript/checklist paths and hashes are explicit. `[UNVERIFIED]` No model inference, probe, build, or E2E was run in this review.

## ARCHITECTURE_AND_CONTRACTS

`[VERIFIED]` The plan identifies the six local-only profile values, config precedence, forbidden shared/cloud settings, local-only flags, atomic budget failure behavior, byte rollback, and cloud isolation. The load-bearing changes are correctly kept in Stage 01/02 planning rather than delegated to a bounded executor fix.

## DATA_SECURITY_RELIABILITY

`[VERIFIED]` Raw runner/runtime data stays in ignored cache; task evidence is restricted to aliases, hashes, IDs, booleans, approved non-sensitive settings, and stable classifications. The plan forbids raw responses, prompts, transcript/DOCX content, filenames, absolute paths, and identity mappings in task artifacts. Stop, rollback, and status-preservation rules are explicit.

## IMPLEMENTATION_SEQUENCE

`[VERIFIED]` Stage 04 first records the prior attempt-03 terminal state, freezes the rubric, performs candidate 3x3, obtains a pre-change baseline before conditional persistence, runs focused/rollback/full-suite delta checks, commits the product/test change, runs a new final 3x3, then runs supporting E2E and Stage 05. Old attempt evidence is append-only and not reused as current results.

## TESTABILITY_AND_ACCEPTANCE

`[VERIFIED]` The plan defines a frozen rubric, anonymous cohort aliases, independent scorer contexts, disagreement adjudication, hash linkage, per-output/per-dimension scoring, and explicit blocked/failed invalid-evidence behavior. The status-contract fixture inventory covers canonical incident, implementation blocker, CORE fail/blocked/not-run/not-required, baseline unavailable/delta, hard-clean debt, formal/unauthorized waiver, independent pending/environment/product outcomes, contradictions, legacy normalization, and every DONE prerequisite. Stage 05 must preserve Stage 04 immutable status snapshots.

## SCOPE_AND_COMPLEXITY

`[VERIFIED]` Scope is one fixed meeting, two requested local models, the existing product path, conditional candidate/final cohorts, and two supporting audio-to-DOCX runs. Cross-meeting, Windows/Ollama, extra ablations, and generic benchmark infrastructure are deferred/non-goal.

## FINDINGS

### RV-014-01 — rubric artifact path should be made fully task-scoped

- Severity: `MINOR`
- Category: `HANDOFF`
- Affected plan/sections: §0.13, §5, §8 steps 3/5/8/10
- Evidence: The plan repeatedly names the frozen artifact as `quality/rubric-v1.md`, while the plan also calls it a task-scoped hash artifact and the current task has no `quality/` directory. The referenced checklist lives under a different historical task artifact. No single exact owner path for the new rubric is stated.
- Failure/rework mechanism: A fresh Stage 04/Handoff could place the rubric in different locations, weakening artifact ownership/freshness linkage or leaving an unintended repository-root untracked file. This is a path/ownership ambiguity, not a defect in the scoring contract.
- Smallest correction: Stage 03 handoff should resolve one exact task-scoped path (recommended `.agent/tasks/<TASK_ID>/quality/rubric-v1.md` or an explicitly designated ignored cache path), and require that path plus hash in `execution.md` and Stage 05 evidence. This is handoff-level clarification only if Stage 03 is authorized to resolve non-semantic path details; otherwise revise the Plan.

## REQUIRED_PLAN_CHANGES

None required for approval. The handoff must carry the exact rubric path/hash linkage noted in RV-014-01; it must not alter scoring semantics, gate scope, privacy rules, or status routing.

## RESIDUAL_MINOR_NOTES

- `[UNVERIFIED]` This review did not run tests, model inference, probes, builds, E2E, or Stage 05 acceptance.
- `[UNVERIFIED]` One fixed transcript and human scoring cannot establish cross-meeting generalization; the Plan correctly labels that out of scope.
- `[VERIFIED]` Existing `.env.example` already documents the relevant local controls; implementation must preserve precedence and comments while changing only approved defaults if persistence is reached.
- `[VERIFIED]` Snapshot SHA is the binding review identity; any later canonical plan edit requires a new review attempt.

FINAL_STATUS: PLAN_APPROVED
NEXT_ACTION: Stage 03 Handoff for PLAN_REVISION 13 at SHA-256 `2b663c68a8f49d0cf769000db5d6d7629c54e589bff8e6c62a5168bc34fbe588`; resolve RV-014-01 as a handoff-level path clarification if permitted.
