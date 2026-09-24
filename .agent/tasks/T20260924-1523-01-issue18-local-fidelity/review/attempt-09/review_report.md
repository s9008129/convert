# Plan Review Report

## REVIEW_METADATA
- TASK_ID: T20260924-1523-01-issue18-local-fidelity
- REVIEW_ATTEMPT: 09
- REVIEWED_PLAN_REVISION: 10
- REVIEWED_PLAN_SHA256: 816434537b7b16f38f4e218dd910bb17660a83861cf657a851917716daf95ed3
- PLAN_SNAPSHOT_PATH: `.agent/tasks/T20260924-1523-01-issue18-local-fidelity/review/attempt-09/plan_snapshot.md`
- Repository anchor observed: branch `issue-18-first-divergence-diagnostic`, HEAD `693f7ee`; working tree has the known Plan R10 edit, untracked Stage05 attempt-06 evidence, and this reviewer-owned attempt-09 directory.
- Reviewer runtime/model: Codex GPT-6 (informational only)

## OWNER_VERDICT
The goal remains a source-faithful local meeting-record architecture for Gemma/Qwen, with the selected causal claim preserved end-to-end and the frozen blind quality threshold met with zero major fidelity hard fails. Essential work is structured source evidence, deterministic consolidation, guarded section rendering/repair, and live acceptance. Optional held-out data, performance optimization, and glossary enrichment remain non-gating. R10 correctly prevents model-authored requiredness and coarse chunks from creating global vetoes, but the selected-target contract is not yet tied to a defined live invocation path and the template policy that makes unselected claims required is not operationally specified. Those gaps can leave the production path without a selected-core check and silently omit unclassified facts. Status-routing scenarios also need explicit fixtures before this revision is ready. Complexity is substantial but broadly justified by the observed fidelity defects; biggest remaining risk is completeness under the new default-optional rule.

## GOAL_BASELINE
- **PRIMARY_OUTCOME:** redesign local Gemma 4 31B/Qwen 3.8 27B meeting-record generation around immutable evidence, structured facts, deterministic validation, and controlled generation, approaching Gemini 3.5 Flash-lite quality while reducing major fidelity hard fails to zero.
- **SUCCESS_EVIDENCE:** selected causal claim remains correct from source through final delivery; architecture and regression evidence; fresh local E2E and blind 3+3 meeting every output/dimension threshold against the original unrounded Gemini baseline with zero adjudicated major hard fails.
- **MUST_NOT_BREAK:** cloud behavior, privacy, template/output compatibility, retry/runtime-selection safety, explicit V1 rollback, and raw-source provenance.
- **NON-GOALS:** prompt-only recovery, hard-coded issue facts, raw private content in tracked artifacts, wholesale experiment-branch merge, second-LLM truth oracle, lowered quality threshold, or unrelated ASR/UI work.
- **CRITICAL_PATH:** source occurrence evidence → typed extraction → deterministic ledger → source-alignment firewall → section rendering/assembly → guarded patch/rollback → selected-claim live E2E → model/quality acceptance.

## GOAL_ALIGNMENT
R10 preserves the approved primary outcome and acknowledges the new Stage05 evidence without treating it as a prompt-only problem. It appropriately keeps the quality evaluator blocker scoped to quality acceptance/task closure and does not claim architecture work must stop. However, the new default-optional behavior needs an explicit completeness contract: otherwise the plan can produce a parseable, source-grounded but materially incomplete record while all unmatched assertions are non-gating.

## NECESSITY_AND_TRACEABILITY
Typed source evidence, claim relations, overlap-aware conflict detection, section rendering, and guarded repair trace to fidelity and reliability. Candidate profile sampling and blind evaluation trace to the requested controlled quality outcome. Diagnostics, docs, privacy protection, and PR delivery have explicit operational/user-task rationale. The trusted per-template requiredness policy is necessary but its required slots/mapping rules are not specified sufficiently to show which high-value facts become required or how omissions are detected.

## GATE_AND_VETO_AUDIT
R10 improves proportionality: invalid optional evidence remains local; mapped required/selected failures do not abort unrelated sections; quality/runtime blockers affect acceptance and closure rather than implementation. C6–C8 are SUPPORTING but HARD_CLEAN; this is traceable to the user's explicit Definition of Done requiring full tests/docs, though the plan correctly says these are not product CORE failures absent regression evidence. The selected-target gate itself is proportionate only if the target is actually supplied on the live production path and the acceptance journey exercises that path.

## COUPLING_AND_FAILURE_CONTAINMENT
The scoped failure rules are generally sound. Invalid refs are excluded from conflict analysis and prompts; conflicts are scoped to dependent claims/sections; optional uncertainty is local. Current code still has a whole-ledger conflict failure path, so implementation must replace that behavior as planned. The selected-target API and policy mapping are cross-layer boundaries that require explicit end-to-end ownership to avoid a helper-only implementation.

## DESIGN_ECONOMY
Architecture complexity is justified by the user's system-level goal and the observed first-divergence and firewall defects. R10 avoids copying whole experiment branches and keeps uncertain enrichment optional. Exact-quote resolution is fail-safe, but whole-transcript uniqueness can produce unresolved claims for repeated phrases; prefer source-chunk-local validated offsets plus quote equality where available, with unresolved ambiguity retained when still indistinguishable.

## CRITICAL_PATH_AND_PRIORITY
W0–W6 prioritize the live fidelity architecture, then W7–W9 acceptance/delivery. This is appropriate. The explicit selected-target caller route and trusted required-slot policy must be settled before rendering/acceptance implementation; they are prerequisites, not follow-up polish. Missing evaluator/model blockers must not delay diagnostics, docs, or the redacted PR update (W6/W9 already require continuing available work).

## REQUIREMENT_FIDELITY
The plan preserves the user's quality threshold, source-of-truth model, selected causal target obligation, cloud invariance, privacy, and rollback. The source evidence occurrence rule is conservative and avoids inventing offsets. The remaining concern is whether the architecture can prove completeness when non-policy-mapped claims default optional; the plan does not define which template slots/claim classes are required or an observable rule for source-supported core facts that are omitted entirely.

## GROUNDING_AND_DRIFT
The current worktree/HEAD and dirty Plan/evidence state match the relevant task evidence. Stage05 attempt-06 safely reports 87 claims from four chunks, 33 with at least one unknown ref, and seven conflicts (five touching unknown refs); Stage04 follow-up says current section planning marks every asserted claim required and selects the first causal/conditional assertion positionally. R10 directly addresses these problems. Repository inspection confirms the live service signature at `backend/services/summarization.py:399` has no selected-target argument, and the production caller at `backend/services/task_processor.py:330` does not pass one. Current local V2 code still selects the first asserted causal/conditional claim (`backend/services/summarization.py:2431`) and current template planning puts asserted claims into `required_claim_ids` based on template-pattern routing (`backend/services/local_pipeline_v2.py:390-415`). Existing `MeetingTemplate` declares text/presence regex patterns and header/section skeletons, not typed claim-requiredness slots (`backend/core/templates.py:129-148`). These are verified plan-to-repository gaps, not reviewer preference.

## ARCHITECTURE_AND_CONTRACTS
Evidence occurrence overlap is a materially improved conflict contract, and the plan states no fuzzy match/no arbitrary first occurrence. The explicit caller target, however, is not defined as an input flowing through the production path. Without a typed API/source and propagation through the caller into V2, a test could exercise a helper with an injected target while ordinary local generation still lacks the selected-core identity. The template `ClaimRequirementPolicy` is a new semantic requiredness contract, but W4 only says to map existing template requirements; the existing patterns mainly describe output sections/labels and do not specify claim-level obligations. Define policy records/slots per active template, their trusted matching logic, and how omissions of required source-supported facts are observable. No implementation of those decisions is authorized until revised Plan approval and fresh Handoff.

## DATA_SECURITY_RELIABILITY
Privacy rules consistently keep raw quotes/prompts/model outputs local and require redacted tracked evidence. Exact quote/offset validation is safe if offsets are checked against the exact quoted substring and source hash; ambiguous occurrences should remain unresolved. A concrete contract should specify chunk-relative versus absolute offset and containment/validation, to prevent incorrect occurrence mapping. Rollback and explicit V1 selection remain adequate at plan level.

## IMPLEMENTATION_SEQUENCE
W0 baseline and worktree classification precede mutations; W1–W6 implement fidelity before profile and blind acceptance work. The sequence is sound once the two load-bearing inputs (caller target flow and template policy) are specified. Keep user-goal criticality separate from closure gating.

## TESTABILITY_AND_ACCEPTANCE
C1/C2 require live extraction-to-delivery evidence, which is necessary. Add an end-to-end fixture that enters through the real local caller and carries an explicit selected target, rather than only testing target resolution or a direct V2 helper. Add per-template policy fixtures proving required slots are assigned, optional/unclassified claims degrade locally, and omission of a mapped core fact fails its intended scope. The Stage05 inversion and unknown-ref/conflict cases are correctly called out. The frozen evaluator remains a valid scoped authority blocker; do not fabricate baseline/sample evidence.

## SCOPE_AND_COMPLEXITY
No broad unrelated scope was identified. New occurrence anchoring and policy machinery are substantial but directly address the observed failure classes; scope should not expand into exhaustive future-template enrichment. Status-semantic scenarios are a process/acceptance obligation and should reuse existing harness fixtures if available rather than add unrelated product code.

## FINDINGS

### RV10-001 — selected target has no defined live caller path
- **Severity:** MAJOR
- **Category:** SEMANTIC_CONTRACT
- **Affected plan:** `DECISION A`, `TARGET_CONTRACT`, W4, C1/C2.
- **Evidence:** Plan requires an explicit caller-supplied target, but current `SummarizationService.summarize` has no such input (`backend/services/summarization.py:399`) and `TaskProcessor` calls it without one (`backend/services/task_processor.py:330`). Current V2 instead chooses the first causal claim (`backend/services/summarization.py:2431`), the exact heuristic R10 intends to remove. C1 requires live source-to-delivery evidence.
- **Failure mechanism:** Implementer may add a target resolver/helper used only by synthetic tests, leaving production V2 with no selected target or falling back to positional inference. The historical selected-claim outcome would then remain unenforced in real use, despite C1 appearing covered.
- **Smallest required correction:** Define a typed target-spec source and its propagation from the actual local invocation into V2 (without hard-coding the historical claim); make C1 exercise that caller-to-delivery route. If targets are diagnostic-only rather than normal runtime inputs, explicitly separate that acceptance contract from production gating and prove the selected claim through the actual production path.

### RV10-002 — default-optional requiredness lacks a usable template policy and completeness contract
- **Severity:** MAJOR
- **Category:** SEMANTIC_CONTRACT
- **Affected plan:** `DECISION B`, R5/R6, `TARGET_CONTRACT` item 4, W4/W5, C1/C2.
- **Evidence:** R10 says unclassified claims are optional and non-gating, while W4 says to map current template requirements into trusted claim policies. Current `MeetingTemplate` exposes header/section pattern and skeleton metadata (`backend/core/templates.py:129-148`); those are output-presence/format patterns, not an existing typed claim-slot policy. Current planning maps every asserted claim to required by matching text/pattern or defaulting to the first body section (`backend/services/local_pipeline_v2.py:390-415`), so no current policy demonstrates which facts must remain required after this semantic change.
- **Failure mechanism:** If claims cannot be matched to specified trusted slots, they all default optional; whole source-supported decisions, actions, numbers, or meeting facts can be silently omitted without a section/record failure. That prevents demonstrating completeness and risks optimizing only the selected causal claim while the user's omissions problem remains.
- **Smallest required correction:** Specify the policy schema and the required slot/claim mapping for each active production template, distinguishing format-required headings from content-required facts. Define deterministic matching and an observable omission check for mapped core facts; test mapped omissions and unrelated optional degradation. Do not promote every extracted claim to required.

### RV10-003 — status-contract fixture coverage is not planned
- **Severity:** MAJOR
- **Category:** TEST
- **Affected plan:** `VERIFICATION_AND_CLOSURE_MATRIX`, C2/C5/C9/C10/C14, canonical status aggregation.
- **Evidence:** The independent review prompt requires explicit fixtures for the canonical incident, true implementation blocker, CORE fail/blocked/not-run/not-required, replan, baseline unavailable/delta, hard-clean debt, formal waiver preserving the original result, independent acceptance pending/environment block, contradictory-state rejection, legacy normalization, and every DONE prerequisite. R10 has selected C9/C10/C14 routing rows and a Stage04/Stage05 blocker table, but no fixture/test matrix or artifact reference proving the full set. The cited attempt-06 report demonstrates some real blocked/pending states, not the complete status contract.
- **Failure mechanism:** Stage04/05 can still emit contradictory or invalid terminal combinations, collapse verification and acceptance states, or close DONE without all prerequisites; the plan's long routing prose would not detect those errors.
- **Smallest required correction:** Add a compact status-contract fixture matrix to verification planning, reusing existing harness fixtures where present and otherwise requiring redacted Stage04/Stage05 artifact cases. Preserve original check results under formal waiver cases even though this task declares waivers unavailable for its own gates.

## REQUIRED_PLAN_CHANGES
1. Define and trace the selected target from the real caller into the live V2 path; make C1 exercise that route.
2. Specify trusted required-slot policy for active templates and completeness/omission behavior under default-optional claims; add focused fixtures.
3. Plan explicit status-contract fixtures covering the required v4.2 scenarios or cite exact existing reusable evidence/fixtures.

## RESIDUAL_MINOR_NOTES
- Exact-quote ambiguity is correctly treated as unresolved; specify offset coordinate system and source-chunk validation details when updating the evidence-reference contract. Prefer validated chunk-relative offsets with exact-substring equality where available rather than requiring a globally unique string when an exact source location is available.
- The missing evaluator is correctly an authority-scoped quality blocker, not an implementation stop. W6/W9 already require continuing diagnostics, docs, and redacted PR work; stating this directly in `BLOCKING_AND_NON_BLOCKING_UNKNOWNS` would improve clarity but is not independently gating.

FINAL_STATUS: PLAN_REVISION_REQUIRED
NEXT_ACTION: Stage 01 revision mode on the same TASK_ID; resolve RV10-001 through RV10-003, increment PLAN_REVISION, and keep prior evidence/history append-only.
