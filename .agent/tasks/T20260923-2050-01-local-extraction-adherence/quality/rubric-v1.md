# P7-C Quality Rubric v1

RUBRIC_VERSION: 1.0.0
FROZEN_AT_UTC: 2026-09-24T01:31:05Z
STAGE04_OWNER: fresh-stage04-quality-execution
BLIND_SCORERS_CANDIDATE: stage04-blind-a, stage04-blind-b
BLIND_SCORERS_FINAL: stage04-blind, stage05-independent
PLAN_REVISION: 13
PLAN_SHA256: 2b663c68a8f49d0cf769000db5d6d7629c54e589bff8e6c62a5168bc34fbe588
TRANSCRIPT_PATH: data/cache/e2e/p7b-qwen27b-e8/transcript.txt
TRANSCRIPT_SHA256: b7b9e5e05be5a560101312d9fb954d2e6aa10044febb8d3fca5a79f3931d9db0
CHECKLIST_PATH: .agent/tasks/T20260922-2037-02-local-model-quality-parity/quality/fact_checklist.json
CHECKLIST_SHA256: cf012d1f6983f67ecb47cc7a6486e48c110a6b2782ad94cccf0332a4ec6ec001
RUBRIC_SHA256: c89621deb5a63ee6bafe5e5ff750d7565e8128ed3424e78d046fb403c022d27c
RUBRIC_SHA256_DEFINITION: SHA-256 of this frozen artifact with the RUBRIC_SHA256 value represented by the literal placeholder TO_BE_RECORDED_AFTER_FREEZE; final artifact hash is recorded separately in execution evidence.

## Common scale

All four dimensions are normalized to 0–100, higher is better. Every rationale carries only raw-cache fact/claim IDs and transcript anchors. Scorers see anonymous outputs and do not see model, provider, or run-order mapping.

## CORE dimensions

### COMPLETENESS

Evaluate the fixed 28 core facts one by one: HIT=1 when the main proposition and necessary subject/condition/direction are complete; PARTIAL=0.5 when the core proposition is identifiable but necessary non-direction-changing detail is missing; MISS=0 when absent or too vague; FABRICATED=0 when contrary to or unsupported by the transcript. Score = sum / 28 × 100. A major fabricated or contradicted claim about a core decision, person ownership, amount/number, date, or direction is a fidelity hard fail.

### FAITHFULNESS

Split the output into atomic factual claims (each independently verifiable/falsifiable; split when subject, action, result, condition, or value varies). A claim is grounded only with clear transcript support and no contradiction. Score = grounded atomic factual claims / all substantive atomic claims × 100. Major unsupported or contradicted claims about core decisions, person ownership, amounts/numbers, dates, or direction are hard fails. Pure formatting and stylistic headings are not claims.

### TRACEABILITY

For each atomic factual claim, determine whether the correct transcript passage/time anchor can be located. Score = claims with correct source anchors / all substantive factual claims, including ungrounded/fabricated claims, × 100. Missing, wrong, or false anchors do not count. A zero denominator is invalid/BLOCKED; do not award 100%.

### USABILITY

Score each subdimension 0/25/50/75/100 and average: U1-STRUCTURE (clear structure), U2-TOPIC-SEPARATION (topics not conflated), U3-ACTION-DECISION-OWNERSHIP (decisions/actions/owners/deadlines identifiable), U4-READABILITY, U5-CONCISION. Shared anchors: 0=missing/unusable; 25=severe defects requiring most content to be redone; 50=partly usable with multiple major edits; 75=mostly directly usable with minor local edits; 100=no substantive defect and directly usable. Do not add dimensions.

## Strict parity formula

For each dimension d, take the median of the three valid Gemini scores C_d. For every local output score L_d, compute gap=max(0, 1 - L_d/C_d), retaining unrounded values. Pass requires gap < 0.10; gap exactly 0.10 fails. C_d <= 0 or invalid baseline/model/config/rubric/score identity is scoped BLOCKED. Gemma and Qwen are evaluated separately; each requires all 3/3 outputs to pass all four dimensions. Do not use local medians to hide a single regression or average across dimensions.

## Blind assignment and disagreement

After all outputs in a cohort are generated and hashed, assign fresh random anonymous aliases C-R01–C-R09 or F-R01–F-R09. Mapping and permutation seed remain in ignored raw cache. Candidate scoring uses two independent blind contexts; final scoring uses Stage 04 blind context and fresh Stage 05 context. Score sheets are hash-locked before mapping disclosure. Any disagreement on a fact label, claim grounding/contradiction, anchor correctness, or hard-fail, or any dimension difference >5 points, triggers a third fresh blind scorer. Use majority for discrete decisions and median for numeric dimensions; unresolved disagreement is scoped BLOCKED.

## Privacy and evidence

Raw outputs, prompts, responses, mappings, score ledgers, transcripts, and free-text rationale remain in unique gitignored raw cache. Task evidence retains only allowlisted aliases, hashes, scorer IDs, dimension values, fact/claim IDs, and statuses. No raw payload, transcript, absolute path, input filename, or free-text prompt is copied into task evidence.
