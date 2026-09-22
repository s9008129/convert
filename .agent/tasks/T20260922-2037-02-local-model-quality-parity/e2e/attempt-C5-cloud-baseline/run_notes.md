# attempt-C5-cloud-baseline（雲端 Gemini 基線；**產物完成、runner 未完成收尾**）

> 如實聲明：本場**任務本身走完全程並產出紀錄**，但 **runner 程序在 03:25:46（ASR 完成後）被外部終止**
> （以背景啟動的 runner 隨終止的 shell session 一起結束），因此**沒有** `run_summary.json`／runner verdict／
> 下載階段的 DOCX。紀錄與逐字稿仍由 backend 完整產出，本目錄量測證據由我事後以既有儀器補齊。

- 目的：取得與地端 B2／B1／C1／D1 **同一支音檔、同一模板（`section_meeting`）** 的雲端（Gemini）基線，
  讓「地端 vs 雲端」終於可以用**同一把尺**（`quality/fact_checklist.json`，67 條／core 28）對照。
- 音檔：`/Users/hsiaojohnny/Downloads/0903-科務會議.m4a`（sha256 `982151f4…012828`；與其他場次同一支）。
- 模式：`--processing-mode cloud`（runner 上傳表單 `processing_mode=cloud`；API `POST /api/upload`）。
- **雲端確實生效的證據**（`runtime_dir=backend.log`）：03:33:47–03:34:26 出現 `_gemini_chat_once`
  「Gemini 摘要生成成功，模型: gemini-3.5-flash-lite」共 4 次，且 03:34:13 有
  「Gemini 摘要品質補強（第 1 輪）」；全場**沒有**任何 `_summarize_with_local_pipeline` 的最終生成。
- 時序（backend log）：03:25:30 開始處理 → ASR 15.6 s（03:25:46）→ diarization 152 s（03:28:1x）→
  語意校正 12 次本地呼叫（03:28:18–03:33:33）→ Gemini 抽取/整併/補強/最終（03:33:47–03:34:26）→
  **任務完成，耗時 536.4 秒**（8 分 56 秒）。`[VERIFIED]`
- 產物：`data/cache/e2e/p3-cloud-baseline-05/backend_data/outputs/0903-科務會議_ce67d0dc.{md,docx}`、
  `..._ce67d0dc_逐字稿.txt`（DOCX 由既有 `backend/services/docx_converter.py` 以 `section_meeting` 模板補產生，
  命令見下）。

## 量測（同一把尺；由我在 03:35–03:37 補跑）

| 指標 | 值 | 命令 |
| --- | --- | --- |
| `coverage_core` | **0.8929**（25/28） | `scripts/e2e/measure_coverage.py --record … --checklist quality/fact_checklist.json --transcript …` |
| `coverage_all` | **0.8060**（54/67） | 同上（`coverage.json`） |
| missing core | `F019, F021, F044` | 同上 |
| `char_count` | 2,593 | `scripts/e2e/measure_record_quality.py --record … --transcript … --template section_meeting` |
| `body_source_tag_count`／`table_source_tag_count` | 28／0 | 同上 |
| `tagged_item_ratio` | 1.0 | 同上 |
| `unsupported_entities` | `[]` | 同上 |
| 出處標註**是否可用** | **28 筆全為 `00:00:00`**（`zero_time_tag_count=28`、`distinct_tag_time_count=1`、`distinct_tag_time_ratio=0.0357`） | 同上（`record_quality.json`） |

## 誠實邊界

1. **runner 未完成收尾** → 本場**不得**當作一次通過的 E2E 驗收（沒有 required checks／verdict／stored-bytes SHA）。
   它是一份**真實雲端產物**＋以既有確定性儀器量出的品質證據。
2. 雲端模式的**語意校正層仍走本地 LLM**（`backend/services/task_processor.py:259-272` 無條件注入）——
   這代表「雲端基線」也含地端校正層，兩者的差異**只隔在最終摘要層**；此為產品現行設計（P1-9 已登錄為候選）。
3. 單次抽樣（temperature 0.7）；比較僅限「同一音檔、同一模板、同一清單」的一次性對照。
4. DOCX 為事後補產生（非 runner 下載路徑），已用同一模板 id，但**未經 runner 的大小/結構 checks**。
