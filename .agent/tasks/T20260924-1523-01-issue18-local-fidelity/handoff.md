# Next-Conversation Handoff — Issue #18 Local Meeting-Record Quality

> **Purpose:** resume this task in a fresh conversation. This is a session-continuity handoff, **not** a valid Stage-03 implementation handoff for R17: the user changed the mandatory quality criterion after R17 approval. Re-plan and obtain the required review before formal acceptance or further semantic/product changes.

## Goal contract — current user instruction is authoritative

- **CORE outcome:** improve local meeting-record generation quality for **Qwen 3.8 27B** and **Gemma 4 31B** running in **LM Studio on the Mac test machine**, with quality difference from **Gemini 3.5 Flash Lite** kept to approximately **10% or less**.
- **CORE evidence:** validate using a real audio-derived meeting transcript, in addition to synthetic diagnostics. Compare like-for-like inputs and freeze the rubric and exact 10% calculation before formal scoring. A synthetic smoke or a context-size experiment is not a quality-threshold pass.
- **Runtime constraint:** LM Studio only for these Mac model-quality tests; do not use Ollama. Keep source audio, transcript, prompts, and generated minutes local and out of tracked reports/PR text.
- **Memory constraint:** do not have Qwen and Gemma loaded together. Finish any generation, unload every instance of that model, verify it is absent, and only then load/use the other model. Never unload/reload during generation. Stop on an LM Studio resource warning; do not blindly retry.
- **Best-effort diagnostics:** context-size comparisons (8K/32K/128K where actually supported) help measure fit, latency, and grounding but do not independently establish Gemini parity.

## Current status at handoff

```text
IMPLEMENTATION_STATUS: COMPLETE (per immutable Stage04 R17 snapshot)
STAGE04_CORE_ACCEPTANCE_STATUS: BLOCKED
STAGE04_REQUIRED_VERIFICATION_STATUS: INCOMPLETE
CURRENT_UPDATED_GOAL_ACCEPTANCE: NOT_ADJUDICATED
TASK_CLOSURE: NOT_DONE
```

Do not rewrite the immutable Stage04 snapshot to make these diagnostics look like acceptance. Stage05 attempt-15 is explicitly exploratory only; it issues no current acceptance/closure verdict.

## Plan/review freshness and required replan

- Task: `T20260924-1523-01-issue18-local-fidelity`.
- Branch: `issue-18-first-divergence-diagnostic`.
- Last known HEAD before this handoff/closure commit: `430950148cf02ece5845cc807665e0e4f35ea7e1` (`fix(local): harden final record fidelity validation`).
- R17 Plan SHA-256: `835a2888be6b593a35dc1d59ff53b714b11371d8bd37b8cd5b373aa8d14896a5`.
- R17 Review attempt-17 approved that exact plan. R17's quality check is **≥80% of Gemini medians**, not the user's newly stated approximately **≤10% gap**. The new user criterion supersedes R17 and is a semantic planning change; do not score or close under stale R17. Create a monotonic Plan revision, state the 10% formula and goal contract, obtain mandatory independent review, then compile a fresh implementation handoff before formal acceptance work.
- A clarification question is pending on how the 10% gap should be computed: each dimension's relative gap, average relative gap, or absolute score-point gap. Use the user's answer if it arrives; otherwise ask once at the start of the next conversation and do not silently choose for formal scoring.
- Existing R17 handoff was archived byte-for-byte at `handoff-history/handoff-plan-r17-20260925-before-user-goal-override.md` (SHA-256 `f436f7adde390c717caa6a161d9e8f420bff08a6f90516307d86a1c99946b995`). This current file deliberately replaces it as a next-session note and is not the approved Stage-03 artifact.

## What is implemented and verified (carry forward; do not repeat blindly)

- Local V2 implementation and scoped docs/tests are in the current tree. The last full suite result was **923 passed, 2 skipped**. `bash scripts/check_docs.sh` passed with two existing README version warnings; `git diff --check` passed. These were run before the latest diagnostic/handoff edits; no product code changed during the model diagnostics.
- See `execution.md` for immutable Stage04 status and `e2e/attempt-15/e2e_report.md` plus `e2e/attempt-15/evidence/verification_log.md` for redacted local diagnostic evidence. Latest hashes after the documentation correction: report `8856baa1733fd44962af5a539daeaf94032b9c2a2d2d97dbde027cd438ee751c`; log `894765af36cfb2f356710a9db3aa1c55e342ada012720f980e39efabbaef2ffb`.
- `evaluator_rescore_identity_correction_r17.md` corrects the O1/O2/O3 source-output hash mapping but does not complete semantic re-adjudication or make the old Gemini medians a valid denominator. `evaluator_authority_r17.md` explains the outstanding rubric/baseline applicability issue. No blind score or 10% result exists.
- Product implementation/tests/docs are already staged in Git at the time of this note; task evidence and `.agent/lessons.md` have additional unstaged paths. Inspect every status/diff before staging/committing. Do not use `git add -A`.

## LM Studio diagnostic evidence from this session (not quality acceptance)

- LM Studio is at `http://127.0.0.1:1234`. Native `POST /api/v1/chat` supports per-request `context_length`; OpenAI-compatible `/v1/chat/completions` does not. See official docs: [native chat](https://lmstudio.ai/docs/developer/rest/chat), [model load](https://lmstudio.ai/docs/developer/rest/load).
- Model inventory advertised `max_context_length=262144` for both target models. Qwen loaded default context was 8,192; Gemma MLX load config reported 71,936. The documented load API accepts `context_length`, but a request to load Gemma with 128,000 echoed 71,936 instead; the reason is unresolved. Distinguish requested context, echoed load config, and per-request context. The native chat API documents per-request `context_length`; Gemma's per-request 32K call nevertheless returned an insufficient-resources warning.
- Synthetic long input, Qwen: native API at requested 32K and 128K both passed HTTP 200; actual input 25,414 tokens, output 82 tokens / 143 chars, three predeclared beginning/middle/end facts all present. Durations 10.469s vs 290.922s (~27.8× slower at 128K). No text was retained; equal lengths/fact flags are not semantic similarity or general-quality scores.
- Synthetic long input, Gemma: requests with `reasoning=off` were rejected because Gemma does not expose that setting. After omitting it, LM Studio returned an insufficient-system-resources warning. No synthetic Gemma result was generated.
- Real-audio-derived Qwen diagnostic used a local cache keyed by the audio file hash; the candidate file could not be mapped to the Issue #18 designated run/input. It is a separate diagnostic only, not C1/C9 and not matched to the Gemini baseline. At request context 32K, Qwen returned 11,779 input tokens and 2,048 output tokens, of which 1,961 were reasoning and only 87 visible-message tokens; elapsed 239.57s. A lexical in-memory check flagged one unsupported-number candidate. This response is **excluded** as a valid quality result; re-run with supported `reasoning=off` and sufficient visible output budget if the sample remains useful.
- User instructed one model at a time. All Qwen instances were unloaded and verified absent. Gemma was then the sole loaded model. Its real-audio native request at per-request context 32K returned HTTP 400 with an insufficient-system-resources warning; stopped without a 128K retry. Final observed inventory: one Gemma instance at load context 71,936; Qwen absent. No generated Gemma text exists.
- No model text, transcript, or source audio was written into tracked evidence. No Ollama or cloud call occurred during these diagnostics.

## Source identity and privacy boundary

- One local real audio candidate exists in ignored upload data and has a matching local ASR cache key. A read-only identity check did **not** find a link from its file hash to the designated Issue #18 run ID/input digest. Therefore it may be used, under the user's explicit request, as a local real-audio diagnostic sample only; it cannot satisfy designated-source C1/C9 or be assumed to match the historical Gemini baseline.
- Do not copy the audio, transcript, prompt, generated minutes, or private locator/quote into this repository, task artifacts, commit messages, or PR. Retain only redacted model IDs, status, token/time counts, and justified scores.
- Do not send this real transcript to Gemini or any cloud service unless the user explicitly authorizes that specific data transfer. Prefer identifying/validating an existing same-source Gemini baseline first.

## Exact next actions for the next agent

1. Read this handoff, `.agent/lessons.md`, the current `plan.md`, `execution.md`, and attempt-15 report/log. Recheck Git status/HEAD/PR and LM Studio inventory; preserve existing dirty/staged work.
2. Resolve the user's 10% formula and write a candidate Plan revision that makes the new goal/acceptance criteria explicit. Preserve the four existing dimensions only if independently valid; do not import the old ≥80% rule as a substitute. Obtain the required independent Plan review and compile a fresh Stage-03 handoff.
3. Establish a privacy-safe designated real audio/transcript/run mapping. If mapping remains unknown, keep the real-audio sample diagnostic-only and C1/C9 blocked; do not infer source identity from cache/hash alone.
4. Re-run Qwen alone with `reasoning=off`, an adequate visible output budget, and verified 32K context. Record only redacted stats/checklist; unload all Qwen instances and verify absent before Gemma.
5. Resolve Gemma's LM Studio resource/context behavior before any retry. At the last check, even a sole Gemma instance's 32K per-request attempt returned an overload/freeze warning; do not repeat without a changed, evidence-based configuration. Confirm actual effective/request context rather than assuming 128K was applied.
6. Re-establish an authorized, hash-linked Gemini 3.5 Flash Lite baseline on the exact same input and a frozen blind scoring protocol. The current R17 O1–O3 mapping was corrected, but semantic re-adjudication remains unresolved. Only then run the fresh required local cohorts and calculate the user's chosen 10% criterion; no smoke/context run counts as a blind sample.
7. Preserve status orthogonality and current Stage04 snapshot. Update the Draft PR only with redacted, accurate evidence; keep it Draft until all required acceptance gates pass. Do not merge or deploy.

## Communication / stop rules

- Explain progress in plain language: what is genuinely verified, what remains blocked, and why.
- Use LM Studio on the Mac only for model-quality validation; never pivot to Ollama for this test machine.
- At most one 27B/31B model is loaded at any time. Stop on explicit LM Studio resource warnings; do not issue duplicate generations.
- No formal quality pass, Gemini-parity claim, designated-source acceptance, or task closure is currently supported by evidence.
