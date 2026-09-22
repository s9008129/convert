# attempt-D2-gemma31b-head 執行紀錄（`gemma-4-31B-it-MLX-4bit` @ HEAD `f001e93`，真實音檔 E2E）

> 本檔由 **D2 E2E 證據打包員**撰寫（繁體中文）。文內數字一律由打包者以 `git rev-parse HEAD`、`shasum -a 256`、**重跑兩支量尺指令**、直接讀取 runtime log 與既有證據檔逐項查核；**未發現與既有證據檔不符之處**。
> 寫入範圍僅本目錄：本檔新增、`sha256_manifest.json` 補一個 key（§八）；未觸碰 `plan.md`／`review/**`／產品程式碼／受測 runtime。

## 0. 打包者自核結果（非照抄）

| 查核項 | 方法（我實際執行） | 結果 |
|---|---|---|
| HEAD | `git rev-parse HEAD` | `f001e930d6d953af0bcb5d31e41332cd4c7d3a98`；＝`run_summary.expected_build_revision`＝`actual_build_revision`＝`health_snapshot.build_revision` |
| 「含 P3 修復」 | `git merge-base --is-ancestor <c> HEAD` | `f0ff0e7`（規則 0 全域段首保護）、`9c0d912`（規則 4 精度保護）、`f0cd5d4`（回歸測試）皆為 HEAD 祖先＝YES |
| 來源音檔 | `shasum -a 256 "/Users/hsiaojohnny/Downloads/0903-科務會議.m4a"` | `982151f4…012828`（45,107,503 bytes；＝`source_audio_sha256`＝`stored_upload_sha256`） |
| 逐字稿 | `shasum -a 256`（`outputs/…_逐字稿.txt`＋runtime 根 `transcript.txt`） | 兩份皆 `199d37b5…`（＝`transcript_sha256`） |
| DOCX | `shasum -a 256`（`outputs/…52cf64f1.docx`＋runtime 根 `meeting_record.docx`） | 兩份皆 `b9257bb9…`（＝`meeting_record_docx_sha256`） |
| 紀錄 md | `shasum -a 256`（`outputs/…52cf64f1.md`） | `734e66e1…`；＝`coverage.json.record_sha256`；原 manifest 未涵蓋，已補登（§八） |
| checklist | `shasum -a 256` | `cf012d1f…`；＝`coverage.json.checklist_sha256` |
| 量尺重跑 | §七兩條指令（`DATA_DIR=/tmp/probe_scratch`） | 輸出與 `coverage.json`／`record_quality.json` **逐欄 diff 為空（完全相同）** |
| runner 閘門 | 讀 `run_summary.json` | 16/16 checks 全 `true`、`failure_reasons=[]`、`verdict=PASS` |
| D1 對照來源 | 讀 attempt-D1 目錄兩檔 | `record_quality.json`（char 1955／body tags 24）＋`quality/coverage/coverage_gemma31b_d1.json`（record sha `010a5224…`，已用 `shasum` 對 D1 md 驗證一致） |

## 一、受測設定

| 項目 | 值 | 來源 |
|---|---|---|
| 模型（指定） | `gemma-4-31B-it-MLX-4bit`；LM Studio key `gemma-4-31b-it-mlx`（publisher `lmstudio-community`、arch `gemma4`、format `mlx`、4bit、31B、18,444,440,967 bytes） | `model_snapshot(.end).json` |
| 已載入 LLM | `unique_loaded_llm_count=1`（僅 gemma；instance `gemma-4-31b-it-mlx`、context 71936） | `model_snapshot.json`＋`model_snapshot_end.json` 一致 |
| 處理模式／上傳 | `processing_mode=local`／`upload_mode=api`／runner `mode=full` | `task_final.json`＋`run_summary.json` |
| 模板 | `section_meeting` | `task_final.template_id`；log「使用會議模板生成會議記錄: section_meeting」 |
| 音檔 | `0903-科務會議.m4a`（存檔名 `6f89beef2ada.m4a`、45,107,503 bytes、sha256 `982151f4…012828`；來源＝Downloads 原檔，hash 相符） | `upload_response.json`＋我的 shasum |
| build_revision | `f001e93…`（expected＝actual＝health 三方一致） | `run_summary.json`／`health_snapshot.json` |
| task_id | `52cf64f1` | `task_final.json` |
| 執行窗 | `started_at` 2026-09-23T03:38:10.696960+08:00 → `finished_at` 2026-09-23T03:59:01.826263+08:00；**牆鐘 1251.129303 s ≈ 1251.13 s（20:51.13）** | 我以 datetime 相減 |
| 任務端到端 | `created_at` 03:38:15.964215 → `completed_at` 03:58:57.647739；**1241.683524 s ≈ 1241.68 s（20:41.68）**；backend log「耗時: 1241.7秒」 | 我以 datetime 相減＋log |

## 二、閘門結果（runner verdict）

- `verdict=PASS`、`failure_reasons=[]`；16/16 required checks 全 `true`：
  `backend_started`、`health_ok`、`build_revision_match`、`model_snapshot_captured`、`model_inventory_unique`、`upload_ok`、`stored_upload_sha_match`、`template_applied`、`task_completed`、`task_summary_failed_false`、`transcript_downloaded`、`docx_downloaded`、`formal_docx_valid`、`metrics_valid`、`model_snapshot_consistent`、`child_terminated`。
- 任務終態：`status=completed`、`progress=100.0`、`summary_failed=false`、`error_message=null`。
- health（快照時）：`version=4.9.0`、`gpu_available=true`、`lmstudio_available=true`、`asr_backend=apple`、`current_device=apple-neural`、`loaded_llm_count=1`、`selected_model=gemma-4-31b-it-mlx`。

## 三、耗時分解（取證：`data/cache/e2e/p3-gemma31b-d2/backend_data/logs/app_2026-09-23.log`）

| 階段 | 秒數 | 關鍵數字（log 原文摘要） |
|---|---|---|
| ASR（apple，fail-closed 無 fallback） | **15.485 s**（03:38:15.985→03:38:32.004） | `audio_duration_seconds=2695.061`、`real_time_factor=0.0057`、`segment_count=1340`、`segments_dropped=0`、`segments_time_degraded=0`、`locale=zh-Hant-TW`、`helper_invocations=1` |
| diarization | **152.0 s**（03:38:32.004→03:41:04.020；RTF **0.056**） | `682 段、8 位發言者、音檔 2695s` |
| 發言者標註 | ≈0.1 s（03:41:04.148） | `8 位發言者、183 段發言（diarization 682 段、threshold=0.6）` |
| 逐字稿語意校正 | **≈318.3 s**（第一支校正呼叫 03:41:04.377 → 完成 03:46:22.639＝**318.262 s**；自「標註完成」起算 318.491 s） | `45 段中 8 段有修正、1 段放棄、採納 27 處替換`；期間 **12 次** temp=0.3 小呼叫、間隔 21.0–32.5 s；對照表 17 列僅記於 log |
| 抽取（單次大呼叫） | metrics **extraction=358.1**（03:46:22.649→03:52:20.706＝358.06 s） | temp=0.6、prompt_tokens=12583、completion_tokens=1792 |
| 最終生成 | metrics **final_and_refine=396.9**（03:52:20.709→03:58:57.631＝396.93 s；本場無補強輪） | temp=0.7、prompt_tokens=16332、completion_tokens=1543 |
| LLM pipeline 小計 | metrics **total=755.0**（＝358.1＋396.9＋merge 0.0） | `chunk_count=1, logical_generations=2, semantic_attempts=0, network_retries=0, merge_rounds=0, merge_groups_last_round=0, duration_seconds={'extraction': 358.1, 'merge': 0.0, 'final_and_refine': 396.9, 'total': 755.0}` |
| 後處理吸附 | 03:58:57.634（一行內含） | 「術語修正 0 處、**出處標註吸附 1 處**（段落內 0／最近段落 0／跨發言者 1；**全域段首保護 22 筆不動**；**精度保護 0 筆不動**；往前收 1 筆／最大 109 s；不可回溯保留 0）、表格出處標註移除 0 處、跨節重複移除 0 條」；另「修復範本骨架佔位符 3 行（日期欄位改回『（待確認）』）」 |
| 收尾 | 03:59:01.321 DOCX 轉換完成；03:59:01.539 服務關閉 | `_process_task`「任務 52cf64f1 處理完成，耗時: 1241.7秒」 |

- 分解占比（以任務端到端 1241.68 s 為分母；各段取 log 值）：ASR＋diarization＋標註 ≈167.6 s（≈13.5%）；語意校正 ≈318.5 s（≈25.7%）；LLM pipeline 755.0 s（≈60.8%）；餘 ≈0.6 s 為階段間 overhead。全場 LLM 生成呼叫共 14 次（12×temp 0.3＋1×0.6＋1×0.7），模型名全為 `gemma-4-31b-it-mlx`。

## 四、量測結果（我重跑量尺，與既有檔完全相同）

### coverage（`coverage.json`；metric_version `coverage-1.0.0`）

- `coverage_all=0.5075`（34/67）、`coverage_core=0.6786`（19/28）、`coverage_supporting=0.3846`（15/39）；`covered_total=34`、`covered_core=19`、`covered_supporting=15`。
- `missing_core_ids=[F025, F044, F048, F054, F056, F060, F061, F065, F066]`（9 筆）。
- `record_char_count=1951`、`record_normalized_char_count=1367`。
- `by_category`：decision 7/9=0.7778；name 3/3=1.0；action_item 6/9=0.6667；number 1/4=0.25；constraint 6/13=0.4615；topic 9/25=0.36；date 2/4=0.5。
- transcript 觀察值（永不作為閘門）：`coverage_all=0.9851`（66/67）、`coverage_core=1.0`（28/28）、僅缺 supporting `F058`；逐字稿 15,667 字、sha256 `199d37b5…`。

### record_quality（`record_quality.json`）

- `char_count=1951`、`body_source_tag_count=23`、`table_source_tag_count=0`、`non_prefixed_tableish_source_tag_count=0`、`instruction_item_count=13`、`tagged_item_ratio=1.0`、`cross_section_duplicate_pairs=0`。
- `tag_traceability` 全欄位（metric_version `tag_traceability-1.1.0`）：
  `segments=183`、`tags_total=23`、`tags_inside_any_segment=23`、`traceable_tag_ratio=1.0`、
  `tags_exact_segment_start=1`、`exact_tag_ratio=0.043478260869565216`、
  `tags_on_real_segment_start=23`、`on_start_tag_ratio=1.0`、
  `tags_on_real_segment_start_excluding_zero=16`、`on_start_tag_ratio_excluding_zero=1.0`、
  `tags_inside_same_speaker_segment=1`、`zero_time_tag_count=7`、`zero_time_tag_ratio=0.30434782608695654`、
  `distinct_tag_time_count=12`、`distinct_tag_time_ratio=0.5217391304347826`。
- `unsupported_entities` 全文：`["一股、二股", "徵收股", "煙酒文申股", "稽查股"]`（觀察值、永不作為閘門）。

## 五、與 D1（同模型、前一次執行）同尺對照

D1 數字來源（我直接讀取，非轉述）：`e2e/attempt-D1-gemma31b-p3/record_quality.json` 與 `quality/coverage/coverage_gemma31b_d1.json`（其 label 為 `D1-gemma31b（P3 修復後新 run）`，record sha `010a5224…` 已用 shasum 對 D1 md 驗證）。

| 指標 | D1 | D2 |
|---|---|---|
| `coverage_all` | 0.5075（34/67） | 0.5075（34/67） |
| `coverage_core` | 0.6786（19/28） | 0.6786（19/28） |
| `coverage_supporting` | 0.3846（15/39） | 0.3846（15/39） |
| `missing_core_ids` | F001,F019,F021,F025,F044,F060,F061,F065,F066 | F025,F044,F048,F054,F056,F060,F061,F065,F066 |
| `record_char_count` | 1955 | 1951 |
| `record_normalized_char_count` | 1388 | 1367 |
| `body_source_tag_count` | 24 | 23 |
| `tags_total` | 24 | 23 |
| `zero_time_tag_count` | 5（0.2083） | 7（0.3043） |
| `distinct_tag_time_count` | 16（0.6667） | 12（0.5217） |
| `on_start_tag_ratio` | 0.9583（23/24） | 1.0（23/23） |
| `on_start_tag_ratio_excluding_zero` | 0.9474（18/19） | 1.0（16/16） |
| `exact_tag_ratio` | 0.0417（1/24） | 0.0435（1/23） |
| `traceable_tag_ratio`／`segments` | 1.0／183 | 1.0／183 |
| `tagged_item_ratio`／`cross_section_duplicate_pairs` | 1.0／0 | 1.0／0 |
| `instruction_item_count` | 19 | 13 |
| `table_source_tag_count` | 0 | 0 |
| `unsupported_entities` | 徵收股、煙酒分管股、稽查股 | 一股、二股、徵收股、煙酒文申股、稽查股 |
| record sha256 | `010a5224…` | `734e66e1…` |
| 逐字稿 sha256 | `199d37b5…` | `199d37b5…`（兩場相同） |

**如實觀察（僅描述證據、不超譯）**：同一 checklist、同一逐字稿、同一量尺版本下，D1／D2 的 `coverage_all`／`coverage_core`／`coverage_supporting` 與三層 covered 計數**完全相同**，但（a）紀錄字元數 1955→1951、正規化字元 1388→1367；（b）正文標註 24→23（`tags_total` 同幅）；（c）`missing_core_ids` 集合不同——D1 缺的 F001／F019／F021 在 D2 已被涵蓋，D2 缺的 F048／F054／F056 在 D1 曾被涵蓋，共同缺 6 筆（F025／F044／F060／F061／F065／F066）；（d）`tag_traceability` 部分欄位不同（`zero_time` 5→7、`distinct_tag_time` 16→12、`on_start_tag_ratio` 0.9583→1.0）。兩場逐字稿 sha256 相同（ASR＋語意校正路徑 byte 相同），差異僅在 LLM 生成端與後處理。單次抽樣（final temp 0.7），以上不作跨 run 穩定性結論。

## 六、可重現指令（我實際執行；`DATA_DIR=/tmp/probe_scratch`）

```
cd /Users/hsiaojohnny/dev/convert
R="data/cache/e2e/p3-gemma31b-d2/backend_data/outputs/0903-科務會議_52cf64f1.md"
T="data/cache/e2e/p3-gemma31b-d2/backend_data/outputs/0903-科務會議_52cf64f1_逐字稿.txt"

DATA_DIR=/tmp/probe_scratch uv run --frozen python scripts/e2e/measure_coverage.py \
  --record "$R" \
  --checklist .agent/tasks/T20260922-2037-02-local-model-quality-parity/quality/fact_checklist.json \
  --label D2-gemma31b-head --transcript "$T"

DATA_DIR=/tmp/probe_scratch uv run --frozen python scripts/e2e/measure_record_quality.py \
  --record "$R" --transcript "$T" --template section_meeting
```

- 兩支量尺預設 `--no-timestamp`＝確定性輸出；我的 stdout 重跑與 `coverage.json`／`record_quality.json` 逐欄 diff 為空。
- runner 指令（依 `run_summary.json` 逐值重建；port 52849／`child_pid=38232`／`upload_mode=api` 由 runner 自動或預設）：

```
uv run python scripts/e2e/run_owned_e2e.py \
  --audio "/Users/hsiaojohnny/Downloads/0903-科務會議.m4a" \
  --template section_meeting --processing-mode local --upload-mode api \
  --artifacts-dir .agent/tasks/T20260922-2037-02-local-model-quality-parity/e2e/attempt-D2-gemma31b-head \
  --runtime-dir data/cache/e2e/p3-gemma31b-d2
```

## 七、如實邊界

- **單次抽樣**：最終生成 temp=0.7、每設定一次；覆蓋率／標註差異（§五）不得外推為跨 run 穩定性或模型能力結論。
- **平台範圍**：本場只驗 **macOS／Apple Silicon（apple-neural）／LM Studio**（`lmstudio_available=true`；`ollama_available=false`）；**Windows 未驗**（本場與 Windows 部署路徑無關）。
- **runner 完整收尾（與 C5 不同）**：本場有 `run_summary.json`（`finished_at` 已寫、`child_terminated=true`、port/pid 記錄）；對照 C5 目錄無 `run_summary.json`，其 `run_notes.md` 自述 runner 被外部終止、無 verdict／required checks。
- 量尺限制（沿用量尺文件）：字面比對，改寫／同義可能計為漏寫；`unsupported_entities`、`known_term_fix_hits` 等皆為觀察值、永不作為閘門。
- 本場「吸附 1 處、段首保護 22 筆、精度保護 0 筆」（§三）為後處理行為的 log 觀測，與儀器 `tag_traceability` 的 23/23 段落起點分屬不同量尺，勿互推因果。

## 八、`sha256_manifest.json` schema 與補登說明

- Schema（沿用原檔）：僅以「角色名＋`_sha256`」鍵存 hash，**不存路徑**；`note` 說明 raw payload 在 gitignored runtime dir；`generated_at` 為該 run 產物生成時刻。角色對映（皆已 shasum 覆核）：
  - `source_audio_sha256`＝Downloads 來源音檔＝`stored_upload_sha256`（runtime `backend_data/uploads/6f89beef2ada.m4a`）。
  - `transcript_sha256`＝`outputs/…_逐字稿.txt`（＝runtime 根 `transcript.txt`，同 bytes）。
  - `meeting_record_docx_sha256`＝`outputs/…52cf64f1.docx`（＝runtime 根 `meeting_record.docx`，同 bytes）。
  - `meeting_record_md_sha256`＝**本次打包補登**（原 run 未含 md；值＝`outputs/…52cf64f1.md` 實測 hash，亦＝`coverage.json.record_sha256`）。
- 未補登檔案（維持原 schema 邊界）：量尺輸出 JSON／log／snapshot 等 redacted 證據為「證據本身」，非受測產物；其 hash 可由重跑量尺（§六）與本檔 §0 交叉查核。
