# Plan Review Report

## REVIEW_METADATA
- TASK_ID: T20260924-1523-01-issue18-local-fidelity
- REVIEW_ATTEMPT: 10
- REVIEWED_PLAN_REVISION: 11
- REVIEWED_PLAN_SHA256: 1ef80c7807d7078981051f740346668a827b20266a39b1f1ebdad081ee3975a2
- PLAN_SNAPSHOT_PATH: `.agent/tasks/T20260924-1523-01-issue18-local-fidelity/review/attempt-10/plan_snapshot.md`
- Repository anchor observed: branch `issue-18-first-divergence-diagnostic`, HEAD `693f7ee`; existing known uncommitted Plan/evidence state is preserved; attempt10 is reviewer-owned.
- Reviewer runtime/model: Codex GPT-6 (informational only)

## OWNER_VERDICT
The goal remains to make the actual local Gemma/Qwen meeting-record path preserve source facts, approach the frozen Gemini quality bar, and eliminate major fidelity hard fails. R11 resolves the three attempt09 gaps: the selected target is an in-memory acceptance input carried along the real caller path and excluded from prompts/persistence; all four active templates have structural and source-present content obligations with explicit absence handling and a stated limit on deterministic semantic completeness; and C13 plans the canonical status-contract fixture matrix. Requiredness and evidence failures remain scoped, while the frozen evaluator blocker is limited to quality acceptance and closure. The added policy/scanner/rendering work is substantial but traces to the observed fidelity failures and is ordered on the critical path. Biggest remaining risk is implementation fidelity: the caller route, template mappings, raw-source coverage scanners, and status fixtures are commitments, not yet implemented evidence.

## GOAL_BASELINE
- **PRIMARY_OUTCOME:** redesign the local meeting-record pipeline around immutable source evidence, structured facts, deterministic validation, and controlled rendering so Gemma 4 31B and Qwen 3.8 27B can approach Gemini 3.5 Flash-lite quality while reducing major fidelity hard fails to zero.
- **SUCCESS_EVIDENCE:** selected causal claim is correct source-to-delivery; architecture and focused/full regression evidence; fresh local E2E and blind 3+3 results meet every per-output/per-dimension threshold against the original unrounded Gemini baseline with zero adjudicated major hard fails.
- **MUST_NOT_BREAK:** cloud semantics, privacy, template/output compatibility, v4.7.4 reliability invariants, immutable raw-source provenance, and explicit V1 rollback.
- **NON_GOALS:** prompt-only recovery, hard-coded Issue #18 answers, wholesale experiment-branch merges, private raw payloads in tracked artifacts, fabricated quality baselines, and unrelated ASR/UI changes.
- **CRITICAL_PATH:** validated raw evidence occurrence → structured claim extraction → deterministic ledger/conflict handling → trusted template/selected-target policy → section rendering and firewall → guarded patch/rollback → live selected-claim E2E → local model and blind quality acceptance.

## GOAL_ALIGNMENT
R11 retains the source-fidelity and local-quality objective without reducing it to prompt work or a single selected-claim demo. The acceptance-only target strengthens diagnosis/acceptance without changing normal task data or persisting meeting-specific target information. The four-template contract and C10 blind evaluation preserve both deterministic high-risk coverage and the user's broader completeness outcome. The plan explicitly states that general semantic omissions not deterministically enumerable remain subject to blind evaluation/target fixtures rather than claiming that schema validity proves completeness.

## NECESSITY_AND_TRACEABILITY
The selected-target route serves the historically failing causal claim; trusted required slots protect known format/content obligations without trusting model labels; occurrence anchors prevent coarse chunks or fabricated references from manufacturing same-evidence conflicts; raw-source candidate coverage and per-section rendering trace to completeness/fidelity and failure containment. Status fixtures trace to correct implementation/acceptance/closure reporting under the global v4.2 contract. Runtime profile comparisons, diagnostics, privacy audit, documentation, and the existing Draft PR update retain explicit task/DoD justification. No new material source or dependency is untraceable.

## GATE_AND_VETO_AUDIT
The plan distinguishes record/section validity from acceptance and task closure. Schema-invalid V2 data fails explicitly after one schema-only repair; this is justified because unvalidated core facts cannot safely feed rendering, with explicit V1 operator rollback rather than hidden fallback. A failed selected target affects only its acceptance; required content gaps are section-scoped; optional/unresolved candidates degrade locally; status/evaluator/runtime blockers do not veto unrelated records or implementation. C9/C10/C14 are explicitly system-level acceptance/verification inputs, never per-record gates. Missing evaluator/baseline is an AUTHORITY-scoped C10/C14 blocker, not an implementation stop or permission to guess.

## COUPLING_AND_FAILURE_CONTAINMENT
The acceptance-only `SelectedClaimTarget` is in-memory from TaskProcessor through SummarizationService/V2 to the final validator, and is withheld from prompts and persisted task schema. Its failure cannot abort unrelated sections. Claim conflicts require overlapping validated absolute raw-source intervals and typed incompatibility; invalid or unresolved references cannot become conflict evidence or renderable provenance. Template requiredness is assigned by trusted policy, with unknown candidates optional and failure localized to the affected section. V2 failure does not silently route to V1. These boundaries contain the supporting/evaluator and per-claim failure modes at the narrowest described safe scope.

## DESIGN_ECONOMY
Structured evidence, occurrence resolution, trusted policy, raw-source scanners, section rendering, and guarded patching add coordination, but each addresses a confirmed failure mechanism or explicit quality/privacy obligation. The plan limits policy to the four active templates and keeps glossary enrichment/unknown entity mapping and held-out examples best-effort. It does not add another LLM judge, wholesale branch ports, persistent transcript state, or a generalized future-template framework. Section-scoped candidate coverage and honest blind-rubric boundaries are more proportionate than either requiring every extracted claim or treating every unclassified claim as a global veto.

## CRITICAL_PATH_AND_PRIORITY
W0 safety/baseline precedes mutation; W1–W6 build and exercise the fidelity path; W7 profile control follows architecture; W8 proves the live causal gate and then runs E2E/acceptance; W9 closes docs/privacy/PR delivery. This prioritizes the reproduced inversion and live path over optional held-out data/performance/glossary expansion. The evaluator blocker is explicitly contained while unrelated architecture, diagnostics, available E2E, documentation, and privacy work continue.

## REQUIREMENT_FIDELITY
R11 retains the original quality threshold, 3+3 blind cohort, zero-major-hard-fail requirement, E2E, repository/docs checks, privacy, rollback, cloud invariance, diagnostics, performance measurements, and PR delivery obligations through the retained R9 decisions and current DoD. It preserves source truth as raw transcript and treats corrected text as advisory. Missing frozen evaluator/rubric/unrounded baseline remains an explicit blocker, not a guessed value. The selected-target scope is evaluator-only and does not hard-code the historical claim into product behavior.

## GROUNDING_AND_DRIFT
Current `git rev-parse --short HEAD` is `693f7ee`, matching the plan and attempt09 anchor. Repository inspection confirms `TaskProcessor` currently calls `SummarizationService.summarize` with transcript/mode/template/raw transcript but no evaluator target; `summarize` has no target parameter and V2 is selected inside the local pipeline. The existing diagnostic E2E runner directly calls `SummarizationService.summarize` and bypasses TaskProcessor. R11 explicitly requires C1 to enter through the real TaskProcessor local invocation and prove caller→service→V2→final delivery, so the runner/harness must be changed (or an equivalent end-to-end TaskProcessor journey added) rather than merely testing a service/helper parameter; this is a planned code change, not an unacknowledged existing capability. Repository template registry contains exactly `general`, `procurement_evaluation`, `section_meeting`, and `isms_monthly`; their definitions/prompts contain structural label/skeleton and missing-value rules matching the plan's source authorities. The planned `evidence/status-contract-fixtures.md` is not present yet; C13 explicitly treats it as a required future artifact, not existing proof. Attempt09 report hash matches its stated SHA-256; R11 cites its reviewed R10 hash accurately.

## ARCHITECTURE_AND_CONTRACTS
**RV10-001 resolved.** `DECISION D`, TARGET_CONTRACT §4, W4, and C1 define the target as acceptance-only evaluator context; it is loaded by the ignored E2E harness, passed through the real local TaskProcessor → SummarizationService → V2 route to final deterministic validation, never placed in model prompts/task persistence, and C1 must exercise that complete route. Current code lacks the new argument, as expected before implementation; the route is explicit and there is no fallback to positional selection.

**RV10-002 resolved.** `DECISION E`, TARGET_CONTRACT §4, W4, and completeness rules distinguish format structure from source-present content across all four registered templates. The plan enumerates content obligations per template, requires template-order labels/sections and canonical placeholders/absence semantics, and keeps only source-present obligations required. The high-risk raw-source candidate inventory is reconciled with extraction/ledger/render coverage. It explicitly limits deterministic completeness claims and assigns otherwise non-enumerable semantic omissions to C10 blind evaluation and evaluator-target fixtures. Current template definitions/prompts are suitable source authorities for the policy.

**RV10-003 resolved.** `DECISION G` and C13 name a redacted, append-only fixture matrix and enumerate canonical incident, true implementation blocker, CORE status variants including explicit NOT_REQUIRED, replan, unavailable/delta baseline, hard-clean debt, waiver preserving original result, Stage05 snapshot/pending/environment-blocker behavior, contradictory state rejection, legacy normalization, and every DONE prerequisite. C9/C10/C14 routing preserves the independent status subjects and Stage05's Stage04 snapshot.

Evidence occurrence resolution has a clear coordinate contract: chunk-relative character offsets are accepted only where `raw_chunk[start:end] == evidence_quote` and source hash/chunk origin match; valid offsets translate to absolute transcript character intervals. Without offsets, exact matching must be unique within the chunk; ambiguity stays unresolved. Overlapping chunks therefore unify without treating a chunk ID as an occurrence. The source-present-only rules/placeholders and section-scoped failure semantics constrain template over-gating; semantic omission limits are honestly stated. No unresolved load-bearing contract or compatibility issue was found.

## DATA_SECURITY_RELIABILITY
Raw/corrected evidence payloads and the evaluator target remain local/in-memory or ignored; tracked diagnostics are limited to IDs/hashes/counts/status. Target is excluded from prompts and task persistence. Raw chunk quote validation, source hash, and chunk origin protect evidence identity; no fuzzy match or arbitrary first occurrence is accepted. Invalid refs cannot affect conflicts, prompts, or rendered trace. Explicit V1 selection is the rollback mechanism; hidden success fallback is prohibited. Cloud/shared-contract regression is required where shared code is touched.

## IMPLEMENTATION_SEQUENCE
The plan sequences baseline/worktree protection first, then fail-first schemas, extraction/provenance, deterministic consolidation, template policy/rendering, firewall, guarded repair, runtime profiles, acceptance, and docs/PR closure. The caller-to-target contract and per-template mappings are specified before W4/W8 implementation. Missing evaluator/model evidence is correctly scoped and does not stop unrelated work. Full details for C13 fixture generation are scheduled as a C13 closure deliverable.

## TESTABILITY_AND_ACCEPTANCE
C1 is stronger than a helper test: it requires the real caller-to-delivery journey and the known inversion probe through the live final gate. C2 covers unknown/malformed references, offset validation, repeated ambiguity, overlap/non-overlap conflicts, local optional degradation, required/selected scope, and render/firewall integration. The policy requires source-present mapped omissions to be observable and uses blind acceptance for semantic omissions outside deterministic inventory. C13 fixture cases cover the §7 status scenarios and DONE prerequisites; Stage05 preserves the Stage04 snapshot. The missing evaluator is represented as a named authority blocker. These are observable and proportionate acceptance criteria.

## SCOPE_AND_COMPLEXITY
Four-template scope is grounded in the current registry and canonical prompts rather than hypothetical future templates. Template content obligations are broad but source-present-only; absence placeholders are explicit; the policy's candidate inventory is section-scoped and unknown semantic completeness is not falsely claimed. R11 preserves the original task's requested deliverables and defers optional held-out sources, performance optimization, and uncertain glossary/entity enrichment. No material scope growth or priority inversion remains.

## FINDINGS
No unresolved BLOCKER or MAJOR finding.

## REQUIRED_PLAN_CHANGES
None.

## RESIDUAL_MINOR_NOTES
- `evidence/status-contract-fixtures.md` is not yet present; C13 explicitly requires creating it during execution. Implementation must retain the listed case matrix, original item result under simulated waiver, and immutable Stage04 snapshot in the fixture evidence.
- The real TaskProcessor/SummarizationService target argument and all per-template policy/scanner contracts are planned changes, not current behavior. The existing diagnostic runner bypasses TaskProcessor; C1 must change its entry path or add an equivalent caller-to-delivery journey, and C1/C2 plus per-template fixtures must prove these contracts are wired and source-present-only before acceptance.

FINAL_STATUS: PLAN_APPROVED
NEXT_ACTION: Stage 03 Handoff for this exact revision.
