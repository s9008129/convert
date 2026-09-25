# Attempt 16 Verification Log (Redacted)

## Actions and results

| Action | Result |
|---|---|
| Read-only `GET http://127.0.0.1:1234/api/v1/models` before switching | Exactly one Gemma target instance loaded; no Qwen instance. Gemma config context `71,936`, parallel `4`. |
| `POST /api/v1/models/unload` for exact Gemma instance ID, followed by inventory verification | Gemma absent; Qwen absent. No generation was active during unload. |
| `POST /api/v1/models/load` with model `qwen3.8-27b-splash`, context `32,768`, `echo_load_config=true` | Load request took longer than the initial command wait; a subsequent read-only inventory confirmed Qwen loaded at context `32,768`, and Gemma absent. |
| Native `POST /api/v1/chat` with cached real-audio transcript; context `32,768`, reasoning off, 4,096 max output tokens, temperature 0.2, store false | HTTP success. 11,782 input tokens; 1,982 output tokens; 0 reasoning output tokens; 2,837 visible characters; TTFT 113.107s; 20.78 tokens/s; elapsed 208.428s. Response text was not retained. |
| `POST /api/v1/models/unload` for exact Qwen instance, then read-only inventory | Qwen absent; Gemma absent before load. |
| `POST /api/v1/models/load` for Gemma with requested context `32,768`, `echo_load_config=true` | Loaded in 13.175s, but applied config echoed context `71,936`, parallel `4`; Qwen absent. |
| Tiny synthetic Gemma meeting-summary request; context `4,096`, 256 max output tokens, no reasoning field, store false | HTTP `400` in `0.029s`; no model output. Specific error message was not captured. No source-audio retry was made. |
| `POST /api/v1/models/unload` for exact Gemma instance, then read-only inventory | Both target models absent; no active generation. |

## Evidence boundaries

- Local input cache file SHA-256: `809d6a0c635789bbe8da6052fd6ca73dbcfcee4adce3cbc6d21f7524f304f154`.
- Input file was identified from the local audio-hash-keyed ASR cache. The candidate has not been linked to the designated Issue #18 source/run; do not infer such a link.
- The numeric scan was a simple in-memory lexical diagnostic only. It is not a fact-level precision/recall test or rubric score.
- No raw audio, transcript, prompt, output, output hash, or cloud request is included or retained by this artifact. `store=false` was set on LM Studio's native chat request.
- The Gemma request used synthetic input only; its output was empty and its error detail was not retained.
- No software tests were run in this attempt. No product-code or prior-attempt files were modified.
