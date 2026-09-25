# Stage 05 Attempt 13 Verification Log (Redacted)

## Freshness and inherited authority evidence

- Plan R17 SHA-256: `835a2888be6b593a35dc1d59ff53b714b11371d8bd37b8cd5b373aa8d14896a5`.
- Handoff R17 SHA-256: `f436f7adde390c717caa6a161d9e8f420bff08a6f90516307d86a1c99946b995`; it binds the same Plan hash.
- Review attempt-17 report SHA-256: `91ef4f91b56505466e2786884c2e2c276818d2dadfa1935e6985021725cdfe2f`; approved the same Plan hash.
- Current Stage04 `execution.md` SHA-256: `7e63f928185426d73cd7321eaa7240533fb5f590ad1f7f54af57a5a26196f9e5`.
- Attempt-12 C1 evidence is carried forward: run/input identity and unique exact occurrence passed, but the in-memory raw-derived relation check was `INCONCLUSIVE/AUTHORITY`. No new decisive raw-authoritative verdict was obtained, so no designated-source/model call was made in this attempt.

## Actions and outcomes

| Timestamp (Asia/Taipei) | Command/action | Result |
|---|---|---|
| 2026-09-25 10:40:51 +0800 | `curl --max-time 5 -sS http://127.0.0.1:1234/api/v0/models` (read-only LM Studio inventory) | HTTP 200. `qwen3.8-27b-splash` and `gemma-4-31b-it-mlx` both reported `loaded`; no model was loaded or unloaded. |
| 2026-09-25, before 10:40:51 +0800 | `DATA_DIR=/tmp/issue18-focused uv run pytest -q tests/test_local_pipeline_v2.py -k 'ollama_v2_uses_effective_model_family'` | PASS — 2 passed, 100 deselected. This is the exact Stage04 repair selector. |
| 2026-09-25 10:41:49.093894–10:42:56.739790 UTC (10:41:49–10:42:56 +0800) | `DATA_DIR=/tmp/issue18-qwen-smoke LOCAL_PIPELINE_VERSION=v2 LOCAL_LLM_PROVIDER=lmstudio LMSTUDIO_MODEL=qwen3.8-27b-splash uv run python - <<'PY' … summarize(synthetic_source, mode=LOCAL, raw_source_transcript=synthetic_source, selected_claim_target=target) … PY` | PASS — selected-target final-delivery guard accepted; target relation preserved; output length 332. Synthetic source/quote: `預算導致延後。`; target: subject `預算`, predicate `導致`, object `延後`, relation `causal`. No generated text was recorded. |
| 2026-09-25 10:43:07.925556–10:45:38.684387 UTC (10:43:07–10:45:38 +0800) | Same production V2 synthetic selected-target command, sequentially, with `DATA_DIR=/tmp/issue18-gemma-smoke` and `LMSTUDIO_MODEL=gemma-4-31b-it-mlx` | PASS — selected-target final-delivery guard accepted; target relation preserved; output length 291. Same synthetic-only source/target. No generated text was recorded. |

The smoke commands used the live LM Studio OpenAI-compatible API at `http://127.0.0.1:1234/v1` through production `SummarizationService.summarize` and the Local V2 implementation. Neither run is designated-source acceptance or quality scoring. Output hashes were not retained; only status, relation-preservation result, length, and timestamps are recorded. The service emitted runtime logs to task-local `/tmp` data directories; no raw/model output was copied into tracked evidence.

No product code, Plan, Handoff, Review, Stage04 execution record, or prior E2E attempt was modified by this verifier.
