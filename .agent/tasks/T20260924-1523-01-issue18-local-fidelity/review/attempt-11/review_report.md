# Plan Review Report

## REVIEW_METADATA
- TASK_ID: T20260924-1523-01-issue18-local-fidelity
- REVIEW_ATTEMPT: 11
- REVIEWED_PLAN_REVISION: 12
- REVIEWED_PLAN_SHA256: `40973ac5abd00aac1c8e84613d248f741a2333166a5e0aeea4ff8dcc565c3247`
- PLAN_SNAPSHOT_PATH: `.agent/tasks/T20260924-1523-01-issue18-local-fidelity/review/attempt-11/plan_snapshot.md`
- Repository anchor observed: branch `issue-18-first-divergence-diagnostic`, HEAD `35e98a29f63c155e25454b494c5d21436529aa28`; working tree had the uncommitted R12 plan and this reviewer-owned attempt only. Product code was not modified.
- Reviewer runtime/model: Codex GPT-6 (informational only)

## OWNER_VERDICT
R12 still aims at the owner's real goal: make local Gemma/Qwen meeting records preserve source facts, eliminate major fidelity hard failures, and meet the frozen Gemini quality bar without changing cloud behavior or exposing private transcripts. Its final-byte check, conservative novelty detection, retry classification, profile eligibility, and experiment-mechanism porting are well connected to the newly audited defects and mostly keep optional failures local. Missing Gemma/evaluator inputs are correctly scoped to their acceptance checks, not unrelated records or implementation progress.

One load-bearing acceptance premise needs correction before handoff: R12 calls the ignored target specification owner-backed/human-authored, but the private provenance audit found no author or creation record. The user's attachment does identify this claim and asserts its raw source is correct; a private source adjudication has independently matched the input hash, derived a unique exact source occurrence, and read the expected positive subject-to-object causal relation from that raw source. That is sufficient to ground a controlled C1 acceptance target **if the raw source—not the unauthenticated ignored file—is stated as authority and independently rechecked by Stage05**. R12 currently instead requires a “human-authored normalization” and presents the local spec as owner-backed. Correct this provenance contract and preserve `BLOCKED/AUTHORITY` if raw-source adjudication cannot be repeated. Also remove one stale HEAD assertion. Until the R12 plan is corrected and reviewed, do not compile its Handoff.

## GOAL_BASELINE
- **PRIMARY_OUTCOME:** redesign the actual local Gemma 4 31B/Qwen 3.8 27B pipeline around immutable raw source, structured facts, deterministic validation, and controlled generation, approaching Gemini 3.5 Flash-lite quality with zero major fidelity hard failures.
- **SUCCESS_EVIDENCE:** selected causal target is correct source→extraction→ledger→render→delivery; required regressions pass; fresh local E2E and blind 3+3 meet every output/dimension threshold against the original unrounded Gemini median; privacy and delivery obligations hold.
- **MUST_NOT_BREAK:** cloud semantics; privacy/provenance; template/output compatibility; v4.7.4 reliability; source immutability; explicit V1 rollback/no hidden fallback.
- **NON_GOALS:** prompt-only recovery; hard-coded Issue #18 answers; wholesale experiment-branch merge; fabricated/rounded baseline; private raw payload in tracked artifacts; unrelated ASR/UI work.
- **CRITICAL_PATH:** source-backed structured claims and exact occurrence provenance → deterministic conflict handling → trusted requiredness and section rendering → live final-byte firewall and guarded patching → selected-target and model E2E → authoritative blind cohort.

## GOAL_ALIGNMENT
R12 remains aimed at architecture-level fidelity, not prompt tuning or a single demo. The finalizer postcondition and novelty detection address the actual user-visible output boundary; retry typing addresses the observed conflation of runtime and schema errors; complete profile eligibility addresses misleading N=1/incomplete comparisons; selective deterministic mechanisms trace to mechanisms explicitly named by the user. The plan keeps the frozen quality target intact and does not reinterpret an unavailable evaluator as a pass.

## NECESSITY_AND_TRACEABILITY
Structured evidence, occurrence resolution, typed causal/conditional/polarity data, deterministic consolidation, per-template trusted policy, section rendering, final output checks, targeted rollback, and runtime profile testing each map to a user-requested failure class or must-not-break invariant. R12's experimental branch work is explicitly mechanism-by-mechanism rather than a broad merge. Verified glossary corrections remain scoped/supporting; absent mappings do not block. The additional R13–R15 requirements are direct responses to code-level gaps, not speculative scope.

## GATE_AND_VETO_AUDIT
R12 largely distinguishes candidate/section failure from task/record/acceptance closure. Requiredness comes from trusted template policy or explicit selected target; optional/ambiguous evidence remains local. C9/C10/C14 are system acceptance inputs, not per-record vetoes; Gemma availability and missing evaluator/baseline are scoped environment/authority blockers. C15 confines veto to decisive mapped-required loss/provenance break or confirmed unsupported high-risk content/duplicate, while uncertain normalization and weak text similarity remain diagnostic. A rejected final candidate is not allowed to masquerade as successful delivery.

**Target authority:** the raw input copies were privately verified to match the historical pipeline input hash; the normalized exact locator was found uniquely in both copies, and its typed relation was independently adjudicated from that raw source. The user's attachment authoritatively names the claim and states that its source is correct. However, the ignored `claim.json`/target artifact's authorship and creation provenance are not established. It must be treated only as an untrusted locator, not as owner authority. C1 may be run as a controlled diagnostic; it can count as acceptance only if Stage05 independently validates the unique source mapping and expected typed relation against the same user-designated raw source. Otherwise preserve `C1: BLOCKED (AUTHORITY)` and do not infer a pass/fail from model output.

## COUPLING_AND_FAILURE_CONTAINMENT
The acceptance-only target stays in memory and out of prompts/persisted task data; invalid evidence cannot become conflict/render provenance; section errors and optional unknowns remain scoped; V1 rollback is explicit. R12 does not let Qwen success erase Gemma's environment blocker or let Stage05 rewrite Stage04 status. These are proportionate boundaries. The target spec itself remains an untrusted input whose only authority is verified source mapping.

## DESIGN_ECONOMY
The new finalizer, high-risk inventory, retry classification, and profile eligibility checks pay rent against observed failure modes and the user's enumerated acceptance criteria. Four-template policy scope follows the live registry and excludes speculative future adapters. The remaining implementation is substantial, but the plan avoids broad similarity vetoes, unverifiable correction, extra judge models, persistent raw content, and whole-branch merges. The recorded summary must not become a transcript-reproduction requirement: candidate inventory is acceptable only insofar as the trusted template policy identifies a source-present material obligation; incidental facts remain optional.

## CRITICAL_PATH_AND_PRIORITY
The plan fixes the release-boundary defects before acceptance, then runs available Qwen C1 and other independent checks while preserving scoped blockers for Gemma and the missing frozen evaluator. Profile sampling and the blind cohort are distinct. It does not stop unrelated architecture work for missing authority/evaluator/model inputs. Stage04 must first revalidate status and establish the cloud baseline.

## REQUIREMENT_FIDELITY
The plan retains the source goal's fresh Gemma/Qwen runs, fresh blind 3+3, per-dimension 0.80 threshold, zero-major-hard-fail gate, cloud/privacy/reliability constraints, diagnostics, docs, and Draft PR delivery. A Qwen C1 acceptance run is only valid against the actual user-designated source and source-adjudicated target relation; authorship of a private cache file is not itself an acceptance criterion or authority.

## GROUNDING_AND_DRIFT
R12's code audit is grounded. At current HEAD, `summarization.py` recomputes final per-section snapshots after finalization but records aggregate coverage as `diagnostic_only` and returns the assembled result; it does not convert a non-accepted final snapshot into a final firewall issue. The extraction `try` covers both model generation and `parse_fact_payload`, then sends either exception through the schema repair. `local_pipeline_v2.py` accepts positive repeats below three, and profile selection does not enforce complete dimensions (missing dimensions are defaulted to zero). These findings support R12's decisions H–K.

One contradictory repository anchor remains: Plan META and the R11 audit record `35e98a2`, which matches live HEAD, but `SOURCE_OF_TRUTH_AND_BASELINE` line 92 states current HEAD `eb3ca049...`. W0's mandatory live re-inventory contains the operational risk, but the plan should not preserve two incompatible “current HEAD” claims.

## ARCHITECTURE_AND_CONTRACTS
Final validation is planned on post-finalizer bytes and before success/delivery; its veto is limited to mapped required facts and decisive confirmed high-risk additions. Schema-only repair is one-time and separated from operational runtime/generation failure. Profile selection requires at least three distinct observed, complete, finite, authority-backed samples with supported controls and does not gate individual records. Experiment mechanisms are selected and tested on the live final path rather than counted by helper presence. No unresolved design defect was found in these R12 additions.

The target authority wording is the exception: the Plan's assertion that a local target is “owner-backed”/“human-authored” is contradicted by the provenance audit. The underlying source-derived target is usable only under the corrected authority rule above; do not rely on the local file's authorship.

## DATA_SECURITY_RELIABILITY
Raw transcripts/prompts/model outputs remain ignored/local; the target remains out of prompts and task persistence; tracked evidence is redacted. The plan also requires exact source/hash occurrence validation and no fuzzy/arbitrary alignment. The private target artifact must not be promoted to trusted data solely because it is present; treat it as untrusted and independently bind it to the user-designated source. The explicit V1 rollback and no hidden fallback are appropriate.

## IMPLEMENTATION_SEQUENCE
W0 protects the dirty-state baseline and cloud behavior before mutation; W1 fail-first tests precede the coherent mechanism waves; W2–W6 establish the live structured path and post-finalizer gate; W7 profile control follows; W8 performs exact inversion and selected-target verification; W9 closes evidence/delivery. The target preflight is correctly before a model call that could count as C1 acceptance. Reword its authority source so an unauthenticated file is not prerequisite authority.

## TESTABILITY_AND_ACCEPTANCE
C1 requires the real caller→service→V2→finalizer→delivery path, not helper-only evidence. C2 contains the listed malformed-ref, overlap, scoped degradation, finalizer, novelty, schema-retry, and incomplete-profile cases. C15–C17 map the new current-HEAD gaps to executable contracts. Fresh Qwen can produce valid acceptance only after the source mapping/relation checks; Stage05 must independently recheck those checks. The frozen rubric/original unrounded baseline remains a valid scoped C10/C14 blocker; Gemma remains an environment-scoped portion of C9/C14. The aggregate status subjects and immutable Stage04/05 evidence rules are coherent.

## SCOPE_AND_COMPLEXITY
The added work is broad but required by the user's architecture and quality goal plus independently observed live defects. Four active templates, conservative high-risk detection, selective experiment ports, and scoped blockers contain complexity. No unnecessary new dependency, persistence, or branch merge is introduced. Missing candidate metrics/evaluator may block profile selection but cannot gate unrelated records.

## FINDINGS

### RV11-001
- Severity: **MAJOR**
- Category: `GROUNDING`
- Affected plan: `R11 → R12 decisions`, `RISKS_AND_UNKNOWNS` item 4, `BLOCKING_AND_NON_BLOCKING_UNKNOWNS` C1 bullet, W4/W8, C1, and Definition of Done.
- Evidence: The private provenance audit reports the ignored local target/claim artifact predates the diagnostic and matches claim ID, historical anchor digest, run ID, and input hash, but no author/creation-command record exists. The user's attachment establishes the target claim identity and says its raw source is correct. A separate private raw-source adjudication verified the matching source files, unique exact occurrence, and positive subject→object causal relation. Thus source truth supports the target; the private spec's claimed “owner-backed”/“human-authored” provenance does not.
- Failure/rework mechanism: C1 readiness is currently justified by a provenance assertion that is not established. If a later verifier trusts the target file's authored relation instead of checking it against raw source, a stale or fabricated locator/relation could be mistaken for canonical acceptance; if it enforces the plan's “human-authored normalization” literally, it may block the independently source-validated target for an irrelevant file-authority condition. Either outcome makes C1 acceptance authority inconsistent.
- Smallest required correction: Revise R12 to state that the user attachment's selected claim identity/source-correct assertion plus exact raw-source evidence is authoritative; treat the ignored file as an untrusted locator only. Specify that Stage02/Stage05 independently bind the locator to the input hash, unique exact occurrence, and relation read from raw source, without trusting file authorship. Keep C1 blocked as `AUTHORITY` if any source mapping or typed-relation check is unresolved; a diagnostic Qwen call may not count as acceptance. Remove/qualify “owner-backed” and “human-authored normalization” wording.

### RV11-002
- Severity: **MINOR**
- Category: `GROUNDING`
- Affected plan: `SOURCE_OF_TRUTH_AND_BASELINE` current HEAD statement (line 92).
- Evidence: `git rev-parse HEAD` is `35e98a29f63c155e25454b494c5d21436529aa28`, agreeing with META and the R12 code-audit record; line 92 calls `eb3ca049...` the current branch head.
- Failure/rework mechanism: The plan carries inconsistent source-code anchors, making it unclear which worktree state the escalation evidence describes. W0 revalidation mitigates this operationally, but the durable premise is stale.
- Smallest correction: Replace the stale assertion with the observed `35e98a2` HEAD and clarify that Stage04 must still re-inventory it immediately before mutation.

## REQUIRED_PLAN_CHANGES
1. Correct RV11-001's target-authority/provenance contract across every occurrence: use the user-designated raw source and independent source adjudication as authority; keep the private file as a locator only; retain a fail-closed C1 authority blocker if any source validation is inconclusive. Distinguish diagnostic model calls from acceptance evidence.
2. Correct the stale current-HEAD statement (RV11-002) in the same R12 revision.

## RESIDUAL_MINOR_NOTES
- R12's high-risk inventory must stay scoped to source-present material template obligations; detected incidental numbers/dates or weak name/similarity matches must remain optional/local unless trusted policy maps them as required. The current policy and veto clauses mostly establish this boundary.
- Stage04 execution, live mechanism wiring, C13 fixtures, Qwen/Gemma behavior, and quality acceptance remain future evidence, not proven by this plan review.

FINAL_STATUS: PLAN_REVISION_REQUIRED
NEXT_ACTION: Stage 01 revise this same TASK_ID to correct the target-authority and current-HEAD claims, then request a fresh Stage 02 attempt.
