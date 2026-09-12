# CHECK-07 Apple ASR E2E — verdict FAIL

- task: T20260912-2242-01-apple-speech-analyzer-asr（PLAN_REVISION 1）
- harness: /Users/hsiaojohnny/dev/convert/.agent/tasks/T20260912-2242-01-apple-speech-analyzer-asr/e2e/run_apple_asr_e2e.py
- core failed: ['helper_invocations_single_call', 'conversion_reason_fragile_native_container']

## CORE checks
- PASS — backend_started
- PASS — health_ok
- PASS — health_accelerator_apple_neural
- PASS — health_apple_helper_available
- PASS — upload_ok
- PASS — task_completed
- PASS — transcript_nonempty
- FAIL — helper_invocations_single_call
- FAIL — conversion_reason_fragile_native_container
- PASS — no_apple_fallback
- PASS — no_apple_temp_residue

## Observations
```json
{
  "health_backend": null,
  "health_accelerator": "apple-neural",
  "apple_helper": {
    "supported": true,
    "available": true,
    "path": "/Users/hsiaojohnny/dev/convert/apple_speech_cli/.build/release/apple-speech-cli",
    "reason": null
  },
  "task_status": "completed",
  "summary_failed": true,
  "task_duration_seconds": null,
  "transcript_chars": 6811,
  "transcript_head": "各位同仁早安，我們現在開始今天的例行會議會議記錄的部分，請各單位在三天內把修正意見回覆給幕僚單位與其。是同沒有意見資訊安全的部分我們已經完成全體同仁的資教育訓練接下來會進行社交工程演練請大家務必提高警覺目前係統的尖峰使用時段集中在上午 9點到 11點我們建議在這個區間加派人力避免民眾等候時間過長。根據統計上個月的案件處",
  "apple_transcribe_ok_count": 0,
  "apple_transcribe_ok": null,
  "apple_metadata_log_lines": [
    "{\"audio_duration_seconds\": 1658.958, \"conversion_reason\": \"fragile_native_container\", \"conversion_seconds\": 0.607, \"elapsed_seconds\": 9.744, \"engine_chain\": \"apple,mlx_whisper\", \"helper_invocations\": 1, \"locale\": \"zh-Hant-TW\", \"real_time_factor\": 0.0059, \"requested_engine\": \"auto\", \"resolved_engine\": \"apple\", \"segment_count\": 572, \"segments_dropped\": 0, \"segments_time_degraded\": 0}"
  ],
  "apple_fallback_log_lines": [],
  "backend_log_bytes": 48310,
  "apple_metadata": {
    "audio_duration_seconds": 1658.958,
    "conversion_reason": "fragile_native_container",
    "conversion_seconds": 0.607,
    "elapsed_seconds": 9.744,
    "engine_chain": "apple,mlx_whisper",
    "helper_invocations": 1,
    "locale": "zh-Hant-TW",
    "real_time_factor": 0.0059,
    "requested_engine": "auto",
    "resolved_engine": "apple",
    "segment_count": 572,
    "segments_dropped": 0,
    "segments_time_degraded": 0
  },
  "apple_temp_residues": []
}
```

## Failures
- apple transcribe 觀測行數=0（預期 1）；helper_invocations=[]
- conversion reason=[]，預期 fragile_native_container
