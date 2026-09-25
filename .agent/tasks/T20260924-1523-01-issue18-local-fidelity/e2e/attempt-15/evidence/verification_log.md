# Stage 05 Attempt 15 Verification Log (Redacted)

## Freshness and inherited authority evidence

- Plan R17 SHA-256: `835a2888be6b593a35dc1d59ff53b714b11371d8bd37b8cd5b373aa8d14896a5`.
- Handoff R17 SHA-256: `f436f7adde390c717caa6a161d9e8f420bff08a6f90516307d86a1c99946b995`; it binds the same Plan hash.
- Review attempt-17 report SHA-256: `91ef4f91b56505466e2786884c2e2c276818d2dadfa1935e6985021725cdfe2f`; it approves the same Plan hash.
- Current Stage04 `execution.md` SHA-256: `7e63f928185426d73cd7321eaa7240533fb5f590ad1f7f54af57a5a26196f9e5`.
- Immutable Stage04 snapshot carried forward: implementation `COMPLETE`; core acceptance `BLOCKED`; required verification `INCOMPLETE`.
- Attempt-12 designated-source C1 preflight remains the latest source-authority evidence: source identity and unique occurrence passed, but the raw-derived relation adjudication was inconclusive. No designated-source/model call was made in this attempt.

## Actions and outcomes

| Timestamp (UTC) | Command/action | Result |
|---|---|---|
| 2026-09-25 03:12 UTC | `curl --max-time 5 -sS http://127.0.0.1:1234/api/v0/models` (read-only inventory) | HTTP 200. `qwen3.8-27b-splash` and `gemma-4-31b-it-mlx` were already `loaded`; no load/unload action. |
| 2026-09-25 03:13:33.611602–03:14:28.329124 UTC | Production `SummarizationService.summarize` via Local V2 with local LM Studio, `LMSTUDIO_MODEL=qwen3.8-27b-splash`, and the same synthetic selected-target harness used by attempt 13 (`DATA_DIR=/tmp/issue18-attempt15-qwen`) | PASS; selected-target final guard accepted; target preserved; output length 328 characters. |
| 2026-09-25 03:14:43.239834–03:17:59.084954 UTC | Same production V2 synthetic selected-target harness, sequentially with `LMSTUDIO_MODEL=gemma-4-31b-it-mlx` (`DATA_DIR=/tmp/issue18-attempt15-gemma`) | PASS; selected-target final guard accepted; target preserved; output length 331 characters. |

The smoke harness used only synthetic input and an in-memory selected target, through the production local V2 call path. No generated text, source-bearing input, raw prompt/output, output hash, or evaluator score was written to tracked evidence. Runtime logs stayed in the task-specific `/tmp` directories. The commands did not load/unload models and no other backend runtime was called.

No product code, tests, Plan, Handoff, Review, Stage04 execution record, or prior E2E attempt was modified by this verifier.

## Superseding exploratory local diagnostics (2026-09-25; no acceptance verdict)

The user’s current target (approximately ≤10% quality gap to Gemini 3.5 Flash Lite) conflicts with approved R17’s ≥80% criterion and requires a Plan replan. Accordingly all work below is exploratory only. No Stage05 acceptance/closure verdict or C1/C9/C10/C14 acceptance is issued. The R17 freshness hashes and immutable Stage04 snapshot are rechecked and unchanged: Plan `835a2888be6b593a35dc1d59ff53b714b11371d8bd37b8cd5b373aa8d14896a5`; Handoff `f436f7adde390c717caa6a161d9e8f420bff08a6f90516307d86a1c99946b995`; Review attempt-17 `91ef4f91b56505466e2786884c2e2c276818d2dadfa1935e6985021725cdfe2f`; Stage04 execution `7e63f928185426d73cd7321eaa7240533fb5f590ad1f7f54af57a5a26196f9e5`. Stage04 snapshot: implementation `COMPLETE`, CORE acceptance `BLOCKED`, required verification `INCOMPLETE`.

| Timestamp UTC | Action | Safe result |
|---|---|---|
| 2026-09-25 03:30:52.365836–03:31:02.836594 | Synthetic long-input Qwen native `/api/v1/chat`, `context_length=32000` | HTTP 200; input 25,414 tokens; output 82 tokens / 143 chars; beginning/middle/end fact booleans all true; 10.469s. |
| 2026-09-25 03:31:41.219849–03:36:32.143075 | Same synthetic Qwen request, `context_length=128000` | HTTP 200; input 25,414; output 82 tokens / 143 chars; same three fact booleans true; 290.922s (~27.8× slower). No response text retained; no exact/normalized similarity calculated. |
| 2026-09-25 03:36–03:39 UTC | Synthetic Gemma 32K/128K requests with reasoning setting, then one request without it | Reasoning setting rejected as unsupported. Retry without that field returned API insufficient-system-resources/model-load warning; no generated output and no further retry. |
| 2026-09-25 03:41:51.196852–03:45:50.767766 | Real-audio-derived Qwen native chat, request context 32,000, `store=false`; local cache was keyed to SHA-256 `982151f4629ade0c38f164b57a2f105c1e305677e7e10e4dc0e252f1ac012828` | HTTP 200; 11,779 input tokens; 2,048 total output tokens, 1,961 reasoning and 87 visible-message tokens; 23.009 tokens/s; TTFT 114.700s; elapsed 239.57s. Excluded from quality evaluation due only 87 visible tokens. No transcript/output text persisted. This upload is not mapped to designated C1/C9. |
| 2026-09-25 03:46:52–03:47:14 | Unloaded Qwen instances by exact IDs, then verified native inventory | Both Qwen instances absent. |
| 2026-09-25 03:48:34–03:48:40 | Unloaded old Gemma; verified inventory | Both target models absent before subsequent configuration attempt. |
| 2026-09-25 03:49 UTC | Loaded Gemma requesting 128,000 with `echo_load_config=true`; read-only model list | API said loaded in 14.3s but echoed/applied context was 71,936. Advertised model max was 262,144. |
| 2026-09-25 03:50 UTC | Official LM Studio load docs checked | Docs state load-time `context_length` only affects llama.cpp-based engines; inventory identifies Gemma format as MLX. Thus echoed 71,936 is the applied load config, not evidence of 128K load. |
| 2026-09-25 03:51 UTC | Unloaded Gemma and verified both target models absent, then reloaded one Gemma instance without a context override | Gemma load echoed 71,936; Qwen remained absent. |
| 2026-09-25 03:52:29.508600 | One real-audio-derived Gemma native chat request with per-request `context_length=32000`, `store=false`, no reasoning field | HTTP 400 in 0.028s; sanitized API error reported insufficient system resources and warned that continuing could overload/freeze the system. No model output was generated. Stopped; no 128K attempt. |
| 2026-09-25 03:52 UTC | Read-only inventory after failure | One Gemma instance remains at load context 71,936; Qwen instances absent. No further model calls. |

The same Traditional-Chinese summarization instruction was used for real-audio Qwen and the attempted Gemma call: organize by topic; preserve confirmed decisions, actions, owners, deadlines, amounts/quantities, and causal relations; mark uncertainty; do not add unsupported facts; output meeting notes only. Request body/prompt and source text are not retained here.

Qwen's in-memory-only heuristic tallies for the first real-audio call: source/output numeric mention counts 79/10, retained-vs-source numeric overlap 9, unsupported numeric count 1; date mentions 0/0; causal-marker counts 111/1. These are lexical diagnostics, not a semantic quality score. Gemma generated no output, so no checklist was possible. No generated text, transcript, output hash, or private ignored source/output was written to artifacts. No Ollama/cloud call, product-code/test edit, or test-suite run occurred.

Final scope status: `CURRENT_STAGE05_ACCEPTANCE_STATUS=NOT_ADJUDICATED_UNDER_UPDATED_GOAL`; `TASK_CLOSURE_STATUS=NOT_ADJUDICATED`; no current parity-threshold conclusion.

### Append-only correction — context-setting interpretation (2026-09-25)

Withdraw the earlier unsupported statement that load-time `context_length` applies only to llama.cpp engines. Observed facts: Gemma load request `context_length=128000` echoed `load_config.context_length=71936`; the native chat request with per-request `context_length=32000` returned HTTP 400 with an insufficient-system-resources warning. Cause of the echoed value and cause of the resource warning are unresolved. No retry or 128K chat was run. Final inventory: one Gemma instance at 71,936, Qwen absent. No acceptance claim.
