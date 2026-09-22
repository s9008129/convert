# attempt-C3-cloud-baseline（雲端基線；**中途中止，無判決**）

> 本目錄是**不完整**的 attempt 證據：runner 在任務仍於「語意校正」階段時被中止，
> 因此**沒有** `task_final.json`／`run_summary.json`／下載產物／verdict。
> 依 append-only 規則保留原始證據，並在此補上如實說明（不覆寫任何既有檔案）。

- 目的：取得「同一支音檔、同一模板（`section_meeting`）」的**雲端（Gemini）基線**，
  以便與地端 B2／B1／C1／D1 四場在同一把尺（`fact_checklist.json` 67 條）下對照。
- 音檔：`/Users/hsiaojohnny/Downloads/0903-科務會議.m4a`（sha256 `982151f4…012828`，與其他場次同一支）。
- 中止時刻：2026-09-23 03:23:12（backend 收到 shutdown；任務 fd37771f 未完成）。
- 中止時的**已觀測事實**（`runtime_dir`＝`data/cache/e2e/p3-cloud-baseline-03/backend.log`）：
  - ASR：`backend=apple`、音檔 2695.1s、耗時 15.747s、`segment_count=1340`。
  - diarization：682 段／8 位發言者／耗時 152.0s；發言者標註 183 段、threshold=0.6。
  - 語意校正：12 次本地生成呼叫（`temperature=0.3`，03:17:38→03:23:09）＝331s，
    即中止時**語意校正剛好結束**，尚未進入摘要階段。
- 重要澄清（避免誤判根因）：本場 log 出現的「使用 LM Studio 本地模式」是**語意校正層**的正常行為
  ——`backend/services/task_processor.py` 的語意校正在 local／cloud 兩種模式**都走本地 LLM**。
  因此「log 出現 LM Studio」**不能**證明上傳的 `processing_mode` 是 local。
  是否真的走雲端，必須以摘要階段是否出現 `_summarize_with_gemini` 證據（或 `task_final.processing_mode`）判定。
- 後續：已另開 `attempt-C4-cloud-baseline`（乾淨 HEAD 上重跑，讓 gate 的 clean-worktree 條件成立）作為正式雲端基線。
