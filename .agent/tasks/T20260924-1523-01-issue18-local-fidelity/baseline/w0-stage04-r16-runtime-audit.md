# Stage04 R16 runtime audit (redacted)

- Reported at: 2026-09-24 21:49:50 UTC (read-only live audit)
- `/api/v0/models`: HTTP 200; one Qwen 3.8 27B model entry loaded; Gemma not loaded.
- Active Qwen context reported as 32,000 tokens; advertised model maximum is 262,144. The active value is 32,000 and must not be replaced with the advertised maximum.
- Endpoint reports no instance identifier/count and exposes only `tool_use` capability metadata; no JSON-schema capability metadata.
- Handoff contains an earlier successful source-free Qwen schema probe, scoped only to its tested Qwen/runtime instance. Do not assume it proves the current instance without matching identity; native structured-output capability remains unverified for a fresh instance until a source-free probe completes normally with schema-valid output.
- Gemma is not loaded. Do not load it over Qwen before the approved Qwen acceptance run.
- No transcript, prompt, model output, local path, or exact model key is included. This audit made no inference, load, or unload request.
