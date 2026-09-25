# Qwen Runtime and Source-Free Native-Schema Probe

- Checked at: 2026-09-25 07:29–07:30 CST (+0800).
- Initial LM Studio inventory showed the target Qwen 3.8 27B downloaded but `not-loaded`; Gemma was also `not-loaded`. No source-bearing call was made at that point.
- With the parent Stage05 coordinator's explicit Qwen-only load authorization, loaded only the approved Qwen target via `POST /api/v1/models/load`, omitting custom context/profile settings. LM Studio returned status `loaded`, instance/model identifier `qwen3.8-27b-splash`, load time 37.115 s, default load context 8192.
- Fresh inventory after load: Qwen state `loaded`; `loaded_context_length=8192`; advertised `max_context_length=262144`; capability metadata `tool_use`. Gemma remained `not-loaded`; it was not loaded/unloaded.
- Production service selection resolved provider `lmstudio`, model `qwen3.8-27b-splash`, loaded instance `qwen3.8-27b-splash`.
- Called the production `_probe_native_schema_capability` path with its fixed synthetic `{ "claims": [] }` payload. Result: `SUPPORTED`, no error class/status. This was a source-free capability probe, not C1/C9 meeting acceptance.
- No meeting source, selected-target data, custom candidate profile, or model-output payload was recorded. No model/profile settings other than loading the approved Qwen target were changed.
