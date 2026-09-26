# Stage05 Verification Log (Redacted)

All checks used synthetic fixtures or the fixed source-free capability probe. `DATA_DIR` pointed to `/tmp/issue18-stage05-r17` to avoid the known read-only `/app/data/logs` default. No product files were edited.

| Time (CST, +0800) | Command/action | Result |
|---|---|---|
| 2026-09-25 07:30:03 | `DATA_DIR=/tmp/issue18-stage05-r17 uv run python` calling production local-engine selection and `_probe_native_schema_capability` | Qwen selected as LM Studio active instance; source-free native schema `SUPPORTED`. |
| 2026-09-25 07:31:32 | Synthetic direct dispatch check: set pipeline to V2, stub V2 to raise a synthetic error, legacy selector to count invocations, call `_summarize_with_local_pipeline` | V2 error propagated; V2 calls=1, legacy/V1 calls=0. |
| 2026-09-25 07:36:29 | `DATA_DIR=/tmp/issue18-stage05-r17 uv run python` invoked the actual V2 orchestrator with synthetic source/target, a stubbed `SUPPORTED` capability, and a stop-after-capture generation stub | One extraction call received `response_format.type=json_schema` / schema `v2_fact_payload`; synthetic selected target was absent from prompt/schema; no source-bearing provider call occurred. |
| 2026-09-25 07:32:05–07:32:06 | `DATA_DIR=/tmp/issue18-stage05-r17 uv run pytest -q tests/test_local_pipeline_v2.py -k 'native_schema_probe or ollama_native_schema or ollama_unknown_schema or ollama_explicit_unsupported or selected_target'` | 10 passed, 80 deselected. Covers exact/schema probe behavior, narrow unsupported/fallback, unknown pre-source stop and diagnostics, and selected-target contracts. |
| 2026-09-25 07:32:10–07:32:11 | `DATA_DIR=/tmp/issue18-stage05-r17 uv run pytest -q tests/test_local_pipeline_v2.py -k 'live_c1_inverted_predicate or live_c1_unsafe_render or v2_unknown_native_schema_capability'` | 6 passed, 84 deselected. Covers live V2 inversion/omission/unsafe-render rollback and UNKNOWN capability stop. |
| 2026-09-25 07:32:14–07:32:15 | `DATA_DIR=/tmp/issue18-stage05-r17 uv run pytest -q tests/test_task_processor.py -k 'selected_claim_target or selected_causal_inversion'` | 2 passed, 16 deselected. Covers ephemeral caller-to-local target flow and final-delivery inversion rejection. |
| 2026-09-25 07:32:19–07:32:20 | `DATA_DIR=/tmp/issue18-stage05-r17 uv run pytest -q tests/test_summarization_service.py -k 'ollama_generation_dispatch_forwards_json_schema_format or ollama_native_json_schema_is_sent_as_api_chat_format'` | 2 passed, 54 deselected. Covers local Ollama native-schema dispatch and `/api/chat` wire format. |
| 2026-09-25 07:31–07:34 | `git diff --check` and final path/status inspection | `git diff --check` exited 0. Existing uncommitted paths were preserved; only this attempt-11 evidence/report was added by Stage05. |

An earlier combined pytest command applied one global `-k` expression across both files and selected only the TaskProcessor inversion case (1 passed, 107 deselected); it was superseded by the correctly separated invocations above. No failing test signature was observed.

Stage04 R17 reports 911 passed, 2 skipped for the full repository suite; this is inherited, not rerun as part of this focused Stage05 acceptance.
