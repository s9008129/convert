# Exploratory Local Model Diagnostic — Attempt 16

> This is a redacted diagnostic record only. It is not a formal Stage 05 acceptance verdict, does not establish Issue #18 source identity, and does not measure the user's updated ~10% Gemini gap.

## RUN_METADATA

- TASK_ID: `T20260924-1523-01-issue18-local-fidelity`
- PLAN_REVISION: 17 (stale for updated quality goal; diagnostic evidence only)
- Attempt: 16, append-only.
- Date: 2026-09-25 UTC.
- Runtime: macOS local LM Studio native REST API `POST /api/v1/chat`; no Ollama or cloud service.
- Model: `qwen3.8-27b-splash` (Qwen 3.8 27B), sole loaded target model during generation.
- Input: local cached ASR transcript from a real audio file; transcript SHA-256 `809d6a0c635789bbe8da6052fd6ca73dbcfcee4adce3cbc6d21f7524f304f154`; 15,667 characters. This sample is not mapped to the designated Issue #18 run/input or the Gemini baseline.
- Request configuration: context `32,768`; `reasoning=off`; `max_output_tokens=4,096`; temperature `0.2`; `store=false`.
- Privacy: source transcript, prompt, and generated meeting notes were not written to tracked or temporary files and are not reproduced here. Only aggregate metadata and heuristic counts are retained.

## OBSERVED_RESULT

- API returned HTTP success; model instance `qwen3.8-27b-splash`.
- Input tokens: `11,782`.
- Output tokens: `1,982`; reasoning output tokens: `0`.
- Visible message: `2,837` characters (one message).
- Time to first token: `113.107s`; generation speed: `20.78 tokens/s`; total elapsed: `208.428s`.
- A lexical numeric-pattern diagnostic found 88 source patterns, 7 output patterns, and 5 output patterns not present as literal source substrings. These are candidates only: number formatting can differ, omissions are not measured, and no semantic adjudication was performed.

## INTERPRETATION_AND_LIMITS

- The prior Qwen real-audio call was unusably short because reasoning consumed nearly all of its output budget. This controlled rerun produced a substantially sized visible meeting-record response with reasoning tokens at zero; therefore the specific output-truncation issue is resolved for this request configuration.
- This run used a non-designated real-audio sample. It cannot satisfy C1/C9 or be compared against Gemini as a same-input baseline.
- The generated text was intentionally not retained, so no source-fact coverage, hallucination, action-item, relation, or overall quality score is claimed.
- No model-parity, 10% threshold, or task-closure claim is supported. Formal scoring remains subject to the updated-goal replan/review, denominator applicability adjudication, and designated-source/input mapping.
- LM Studio inventory before the Qwen generation confirmed Gemma absent and Qwen loaded at context `32,768`.

## SEQUENTIAL_GEMMA_PROBE

- After the Qwen request completed, Qwen was unloaded and inventory verified both target models absent before loading Gemma.
- Gemma load request asked for context `32,768`; LM Studio reported the applied instance config as context `71,936`, parallel `4`, with Qwen absent.
- A tiny synthetic meeting-summary request (request context `4,096`; no reasoning parameter) returned HTTP `400` in `0.029s`; no model output was generated. The response's specific error message was not captured, so do not classify this new failure as a confirmed resource error.
- No source-audio request was sent to Gemma. Gemma was unloaded afterward; final inventory verified both Qwen and Gemma absent.
- This probe did not establish Gemma quality or why its requests are rejected. Do not retry without a changed, verified configuration and diagnosis.

## CURRENT_STATUS

```text
DIAGNOSTIC_RUN: COMPLETED
QUALITY_ACCEPTANCE: NOT_EVALUATED
UPDATED_GOAL_ACCEPTANCE: NOT_ADJUDICATED
TASK_CLOSURE: NOT_DONE
```

See `evidence/verification_log.md` for the redacted action log.
