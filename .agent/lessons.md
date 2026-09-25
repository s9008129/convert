# Project Lessons

## Local meeting-record model quality tests on macOS

- On the Mac test machine, model-quality validation for Qwen 3.8 27B and Gemma 4 31B must use the models loaded in LM Studio. Do not route these tests through Ollama.
- Treat LM Studio's OpenAI-compatible `/v1/chat/completions` API and native `/api/v1/chat` API as different capabilities. Per-request `context_length` is supported by the native endpoint; do not assume the OpenAI-compatible endpoint accepts it. Verify the effective context in the live response/configuration rather than trusting a requested value.
- Large local models may exceed available memory when loaded together. Run one large model at a time: finish its active request, unload it, verify it is unloaded, then load or test the next model. Do not unload/reload during generation, and stop on a resource warning instead of retrying blindly.
- A larger context window permits longer transcripts but does not itself guarantee better meeting-record quality; it can increase latency and memory use. To measure context effects, hold the source, prompt, and generation controls constant, compare contexts on the same transcript, and record input/output tokens, elapsed time, acceptance/errors, and grounded fact coverage.
- Synthetic inputs are useful for integration/context diagnostics only. They do not replace validation on a real audio-derived meeting transcript. Keep audio, transcript, prompts, and generated minutes local and out of reports; persist only necessary redacted metrics.
- Before treating a real-audio run as designated-source acceptance, verify its file/run/transcript identity and source mapping. If that link is unknown, label the run as a separate diagnostic; do not count it as C1/C9 acceptance or as a Gemini quality-comparison sample.
- The core quality target is local Qwen/Gemma meeting-record quality within about 10% of Gemini 3.5 Flash Lite. Freeze and state the exact scoring/rubric calculation before formal comparison. A smoke check or context experiment is not a quality-threshold pass.
- Diagnose API errors from sanitized status/code/message before attributing failure to a model or context limit. Use only parameters supported by the selected model; for example, omit `reasoning` when LM Studio reports that a model does not expose reasoning configuration.
