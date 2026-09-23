# P4 比較總表（baseline_table.md）

- 作者：證據彙整員（**唯讀**；本檔為本次唯一新增檔案）。日期：2026-09-23（Asia/Taipei）。
- 用途：供後續 27B（`qwen3.8-27b-splash`）E2E 落地後對照，並提供非技術讀者的白話結論。
- 讀表規則：**每個數字都附「來源檔＋欄位路徑或行號」**；查無證據一律寫「無資料」；`[進行中]`＝E2 尚未寫完（不等待）。
- 共同素材：全部場次同一支音檔 `/Users/hsiaojohnny/Downloads/0903-科務會議.m4a`（`source_audio_sha256 = 982151f4…012828`，來源：各 `attempt-*/sha256_manifest.json:.source_audio_sha256`）；模板皆 `section_meeting`（C5 同）。
- 量尺（ruler）代號：
  - `tag_traceability-1.1.0`＝出處標註可查核性（主指標 `on_start_tag_ratio`＝時間戳恰為逐字稿真實段落起點）。
  - `tag_traceability`（無版本欄）＝舊儀器 v1.0 語意（其同名欄位實為「段落起點＋發言者一致」的嚴格版；v1.1 下應讀 `exact_tag_ratio`；來源：`attempt-B1-moe-fix/run_notes.md` errata 節）。
  - `coverage-1.0.0`＝事實涵蓋率（字面 probe；清單 67 條＝core 28＋supporting 39）；`checklist_sha256` 全場現值 `cf012d1f6983…`（前 8 碼 `cf012d1f`；來源：`quality/fact_checklist.json` 實測 sha、及 C5/D1/D2/E1 `coverage.json:.checklist_sha256`）。
- 逐字稿版本（影響「同一把尺的可比性」）：A1／B2＝`bd6b52d7`、B1＝`667365a4`、C1／D1／D2／C5＝`199d37b5`、E1＝`cc5b1d54`（來源：各場 `sha256_manifest.json:.transcript_sha256`；A1/B2/B1/C1 四檔 sha 已另外以 `shasum -a 256` 對 runtime 實體檔案複核一致）。

---

## 表一：各場次基本盤

| attempt | 日期時間（起→訖，+08:00） | 模型（LM Studio key） | 引擎 provider | 處理模式 | 模板 | `metric_version` | checklist sha256 前 8 碼 | 同一把尺？是否可比 | 來源 |
|---|---|---|---|---|---|---|---|---|---|
| A1（`attempt-A1-27b`） | 09-22 20:39:32 → 20:54:42 | `qwen3.8-27b-splash` | lmstudio（本機） | local | section_meeting | tag：原檔 v1.0 語意（無版本欄）；v1.1 離線重測另存 | 無（該場未套用清單；清單 09-23 00:29 才落地） | 標註面**可比**（須用 v1.1 重測值）；涵蓋率**無量測** | `attempt-A1-27b/attempt.json:.started_at/.finished_at/.model/.processing_mode/.meeting_template`；`data/cache/e2e/p2-27b-01/backend.log:48`（使用 LM Studio 本地模式） |
| B1（`attempt-B1-moe-fix`） | 09-22 21:07:41 → 21:15:13 | `qwen3.6-35b-a3b-splash` | lmstudio（本機） | local | section_meeting | tag：原檔 v1.0 語意；v1.1 離線重測另存；coverage 為**事後離線量測** | `cf012d1f`（離線量測使用） | 標註**可比**（v1.1 重測後）；coverage 非當場 runner 量測，引用須加註 | `attempt-B1-moe-fix/attempt.json:.started_at/.finished_at/.model`；`data/cache/e2e/p2-moe-fix-01/backend.log:49` |
| B2（`attempt-B2-27b-fix`） | 09-22 21:18:21 → 21:46:51 | `qwen3.8-27b-splash` | lmstudio（本機） | local | section_meeting | tag：`tag_traceability-1.1.0`（原生）；coverage 為事後離線量測 | `cf012d1f`（離線量測使用） | **可比**；惟 `record_quality.json` 曾於當晚被就地覆寫（v1.0→v1.1，見 §可信度） | `attempt-B2-27b-fix/attempt.json:.timing_breakdown.instrument_metric_version/.coverage`；`attempt-B2-27b-fix/run_notes.md`（首節） |
| C1（`attempt-C1-gemma31b-fix`） | 09-22 23:15:52 → 23:43:41 | `gemma-4-31b-it-mlx` | lmstudio（本機） | local | section_meeting | tag：`tag_traceability-1.1.0`（原生）；coverage 為事後離線量測 | `cf012d1f`（離線量測使用） | **可比**（標註 v1.1；coverage 離線） | `attempt-C1-gemma31b-fix/attempt.json:.started_at/.finished_at/.model_key` |
| C5（`attempt-C5-cloud-baseline`） | 09-23 03:25:30 起（任務完成 03:34:26；共 536.4 s） | 生成：`gemini-3.5-flash-lite`（雲端）＋語意校正：`gemma-4-31b-it-mlx`（LM Studio） | gemini（生成）＋lmstudio（校正） | **cloud** | section_meeting | tag：`tag_traceability-1.1.0`；coverage：`coverage-1.0.0`（產物事後由既有儀器量測） | `cf012d1f` | 清單／量尺同尺；但生成引擎不同＋**runner 未收尾**（無 verdict）→ 任何引用須加註 | `attempt-C5-cloud-baseline/run_notes.md`（第 1–9 點）；`attempt-C5-cloud-baseline/coverage.json:.metric_version/.checklist_sha256` |
| D1（`attempt-D1-gemma31b-p3`） | 09-23 01:35:25 → 01:55:53 | `gemma-4-31b-it-mlx` | lmstudio（本機） | local | section_meeting | tag：`tag_traceability-1.1.0`；coverage：`coverage-1.0.0` | `cf012d1f` | **可比**（同尺同模型） | `attempt-D1-gemma31b-p3/attempt.json:.started_at/.model_key/.coverage` |
| D2（`attempt-D2-gemma31b-head`） | 09-23 03:38:10 → 03:59:01 | `gemma-4-31b-it-mlx` | lmstudio（本機） | local | section_meeting | tag：`tag_traceability-1.1.0`；coverage：`coverage-1.0.0` | `cf012d1f` | **可比**（與 D1 同尺） | `attempt-D2-gemma31b-head/run_summary.json:.started_at/.finished_at`；`coverage.json:.metric_version` |
| E1（`attempt-E1-gemma31b-p4`） | 09-23 05:00:45 → 05:38:44 | `gemma-4-31b-it-mlx` | lmstudio（本機） | local | section_meeting | tag：`tag_traceability-1.1.0`；coverage：`coverage-1.0.0` | `cf012d1f` | **可比**，但逐字稿 sha 與 D1／D2 不同（`cc5b1d54` vs `199d37b5`；4 行語意校正差異）→ 跨場比較須加註 | `attempt-E1-gemma31b-p4/run_summary.json:.started_at/.finished_at`；`attempt-E1-gemma31b-p4/run_notes.md` §一／§五 |
| E2（`attempt-E2-gemma31b-p4a-fix`） | 09-23 09:21 起 **[進行中]** | `gemma-4-31b-it-mlx`（health `selected_model`） | lmstudio（`provider_info.effective_local_llm_provider`） | 無資料（尚未寫 `run_summary`／`task_final`） | 無資料 | 無資料 | 無資料 | **[進行中] 不得引用** | `attempt-E2-gemma31b-p4a-fix/health_snapshot.json:.raw_response.device_info.llm.selected_model`（captured_at 09:21:57，task_id `7bf495fe` 於 `upload_response.json`） |

附註（表一）：
- runner verdict：A1／B1／B2／C1／D1／D2／E1＝`PASS`（`attempt-*/run_summary.json:.verdict`，E1 為 `run_summary.json`）；E1 另有 **1 項品質觀測未過**：`quality_on_start_tag_ratio_ok=false`（0.9310 < 0.95；observe 模式、不列 verdict；來源：`attempt-E1-gemma31b-p4/run_notes.md` §二）。C5 無 verdict（runner 03:25:46 被外部終止；來源：`attempt-C5-cloud-baseline/run_notes.md` 開頭）。
- C5 的「雲端生效」證據：backend log 03:33:47–03:34:26 出現 4 次 `_gemini_chat_once`（`gemini-3.5-flash-lite`）、03:34:13 有「Gemini 摘要品質補強（第 1 輪）」；全場無 `_summarize_with_local_pipeline` 最終生成（來源：`attempt-C5-cloud-baseline/run_notes.md`；`data/cache/e2e/p3-cloud-baseline-05/backend.log:103`）。

---

## 表二：耗時

單位＝秒。「模型生成時間」＝摘要 pipeline 內部計時（不含 ASR／diarization／語意校正）。

| attempt | runner 牆鐘 `duration_seconds` | 任務端到端 | 補強輪數 | 固定成本（ASR＋diarization＋語意校正） | 模型生成時間 |
|---|---|---|---|---|---|
| A1 | **910** | **901.3** | **0** | ≈**284**（15.83＋150.4＋≈118）[本表推算] | **615.1** |
| B1 | **452** | **442.3** | **2**（未收斂） | ≈**208**（16.78＋157.0＋≈34）[本表推算] | **233.3** |
| B2 | **1710** | **1703.0** | **2**（未收斂） | ≈**297**（16.7＋153.7＋≈127） | **1404.7** |
| C1 | **1670** | **1659.6** | **1**（收斂） | **529.1**（15.8＋153.3＋360） | **1129.3** |
| C5 | 無資料（無 `run_summary.json`） | **536.4** | **1**（Gemini，收斂） | ≈**488**（15.622＋152.3＋320.4） | **47.1**（Gemini 3 次） |
| D1 | **1227.2** | **1218.6** | **0** | **478.8**（15.595＋151.7＋311.5） | **738.8** |
| D2 | **1251.13** | **1241.7** | **0** | **485.8**（15.485＋152.0＋318.3） | **755.0** |
| E1 | **2278.77** | **2270.8** | **2**（未收斂） | **526.4**（15.801＋152.0＋358.6） | **1743.6** |
| E2 | 無資料 [進行中] | 無資料 [進行中] | 無資料 [進行中] | 無資料 [進行中] | 無資料 [進行中] |

逐格來源：
- A1：runner＝`attempt-A1-27b/attempt.json:.duration_seconds`；任務＝`data/cache/e2e/p2-27b-01/backend.log:277`（「耗時: 901.3秒」；`task_final.json.created_at→completed_at` 亦＝901.3）；輪數＝同 log 無「品質補強（第 N 輪）」命中、`:255` `logical_generations=2`；ASR 15.83＝log:43 `elapsed_seconds`、diarization 150.4＝log:44、校正 ≈118＝log:48（20:42:25）→log:120（20:44:23）時間戳相減 [本表推算]；生成 615.1＝log:255 `pipeline metrics duration_seconds.total`（extraction 305.4＋final_and_refine 309.7）。
- B1：runner＝`attempt-B1-moe-fix/attempt.json:.duration_seconds`（452）；任務 442.3＝`data/cache/e2e/p2-moe-fix-01/backend.log:197`（attempt.json `.task_duration_seconds=442` 同源）；輪數＝log:138（第 1 輪）、log:158（第 2 輪）；log:175 有「仍有待補強問題」＝未收斂；ASR 16.78＝log:43、diarization 157.0＝log:45、校正 ≈34＝log:49（21:10:41）→log:104（21:11:15）[本表推算]；生成 233.3＝log:176 `pipeline metrics duration_seconds.total`。
- B2：runner／任務＝`attempt-B2-27b-fix/attempt.json:.duration_seconds`＝1710、`.task_duration_seconds`＝1703；任務亦見 `data/cache/e2e/p2-27b-fix-01/backend.log:449`（1703.0 秒）；輪數＝同 log「品質補強」2 命中＋log:449 前之警告（來源：`attempt-B2-27b-fix/run_notes.md` §一）；固定成本＝`attempt.json:.timing_breakdown_errata_20260922.corrected_breakdown_seconds`（16.7／153.7／約 127）[標籤更正如該欄]；生成 1404.7＝同欄 `pipeline_total`＋`data/cache/e2e/p2-27b-fix-01/backend.log:427`。
- C1：runner／任務＝`attempt-C1-gemma31b-fix/attempt.json:.duration_seconds`（1670）、`.task_duration_seconds`（1660）與 `data/cache/e2e/p2-gemma31b-fix-01/backend.log:438`（1659.6）；輪數＝`attempt.json:.refinement.rounds_executed=1`＋log:325（第 1 輪）；固定成本＝`attempt.json:.timing_breakdown`（15.8／153.3／360）；生成 1129.3＝同欄 `pipeline_total_seconds`。
- C5：runner＝無資料（`attempt-C5-cloud-baseline/` 無 `run_summary.json`）；任務 536.4＝`data/cache/e2e/p3-cloud-baseline-05/backend.log:128`（亦見 `e2e/timing-forensics-01/report.md` §2 附列）；輪數＝`backend.log:103`「Gemini 摘要品質補強（第 1 輪）」；固定成本＝`timing-forensics-01/report.md` §2（ASR 15.622／diarization 152.3／校正 320.4，證據行 C5L:34/35/38→87）；生成 47.1＝同報告 §2（C5L:90/91/95）。
- D1：runner／任務＝`attempt-D1-gemma31b-p3/attempt.json:.timing_breakdown.runner_total_seconds`＝1227.2、`.task_total_seconds`＝1218.6（log:344 同值）；輪數＝`attempt.json:.refinement.rounds_executed=0`；固定成本同理（15.595／151.7／311）；生成 738.8＝`.pipeline_total_seconds`。
- D2：runner＝`attempt-D2-gemma31b-head/run_summary.json`（started_at→finished_at＝1251.129303；亦見同場 `run_notes.md` §0）；任務＝同場 `run_notes.md` §一（1241.68）＋`data/cache/e2e/p3-gemma31b-d2/backend.log:349`（1241.7）；輪數＝同場 log 0 命中＋`run_notes.md` §三（`logical_generations=2`）；固定成本＝`run_notes.md` §三（15.485／152.0／318.3）；生成 755.0＝同節 metrics。
- E1：runner／任務＝`attempt-E1-gemma31b-p4/run_summary.json`（2278.766 由起訖相減；亦見 `run_notes.md` §一）＋`data/cache/e2e/p4-gemma31b-e1/backend.log:592`（2270.8）；輪數＝`run_notes.md` §三＋`backend.log` 2 命中；固定成本＝`run_notes.md` §三（15.801／152.0／358.6）；生成 1743.6＝同節（`logical_generations=4`）。

手動測試場（無 runner；來源＝`data/logs/structured_2026-09-22.jsonl`）：

| 任務 ID | 任務自報耗時 | 模型／模式 | 備註（來源） |
|---|---|---|---|
| `836fcae7` | **303.9 s** | `qwen3.6-35b-a3b-splash`／本地 (LM Studio) | 逐字稿快取命中（免 ASR/diarization）；`.docx` 於 md 後 +124.3 s 產出（18:01:44）。來源：`structured_2026-09-22.jsonl:1050`（耗時行）、`:1046`（模式/模板 section_meeting）、`:1051`（docx）；模型與 +124.3 s 見 `timing-forensics-01/report.md` §2／§8。 |
| `b20c90a7` | **1029.9 s** | `qwen3.8-27b-splash`／本地 (LM Studio) | 模板 section_meeting（`:954`）；逐字稿快取命中（報告 §2 附列）。來源：`structured_2026-09-22.jsonl:958`；報告 §2。 |
| `3ae2d9ec` | **1422.8 s** | 本地 (LM Studio) | **模板 general**（`:84`）→ 與其餘場次不同模板，**不可同尺**。來源：`structured_2026-09-22.jsonl:87`、`:84`。 |

`data/logs/structured_2026-09-23.jsonl`：0 筆任務耗時（僅 logger 初始化行）→ 09-23 無手動場紀錄。

---

## 表三：品質

### 三-A 涵蓋率（`coverage-1.0.0`）

| attempt | `coverage_all` | `coverage_core` | `coverage_supporting` | `missing_core_ids` 數量 | `decision` 命中 | `number` 命中 | `date` 命中 | 量測性質／來源 |
|---|---|---|---|---|---|---|---|---|
| A1 | 無資料 | 無資料 | 無資料 | 無資料 | 無資料 | 無資料 | 無資料 | 無 coverage 量測（執行時清單尚未落地） |
| B1 | **0.6269**（42/67） | **0.8214**（23/28） | **0.4872**（19/39） | **5**（F021,F025,F061,F065,F066） | 7/9＝0.7778 | 2/4＝0.5 | 2/4＝0.5 | **事後離線量測**：`quality/coverage/coverage_qwen35b-moe.md`（「總覽」／「分類涵蓋率」／「漏寫事實（core；5 條）」） |
| B2 | **0.8209**（55/67） | **0.8929**（25/28） | **0.7692**（30/39） | **3**（F021,F025,F055） | 9/9＝1.0 | 2/4＝0.5 | 3/4＝0.75 | **事後離線量測**：`quality/coverage/coverage_qwen27b.md`（同上節位） |
| C1 | **0.5672**（38/67） | **0.75**（21/28） | **0.4359**（17/39） | **7**（F001,F022,F025,F044,F054,F056,F066） | 7/9＝0.7778 | 2/4＝0.5 | 2/4＝0.5 | **事後離線量測**：`quality/coverage/coverage_gemma31b.md` |
| C5 | **0.8060**（54/67） | **0.8929**（25/28） | **0.7436**（29/39） | **3**（F025,F056,F066） | 9/9＝1.0 | 2/4＝0.5 | 4/4＝1.0 | `attempt-C5-cloud-baseline/coverage.json:.coverage_all/.coverage_core/.coverage_supporting/.missing_core_ids/.by_category` |
| D1 | **0.5075**（34/67） | **0.6786**（19/28） | **0.3846**（15/39） | **9**（F001,F019,F021,F025,F044,F060,F061,F065,F066） | 6/9＝0.6667 | 1/4＝0.25 | 1/4＝0.25 | `attempt-D1-gemma31b-p3/attempt.json:.coverage.*`＋`quality/coverage/coverage_gemma31b_d1.json:.by_category`（同值） |
| D2 | **0.5075**（34/67） | **0.6786**（19/28） | **0.3846**（15/39） | **9**（F025,F044,F048,F054,F056,F060,F061,F065,F066） | 7/9＝0.7778 | 1/4＝0.25 | 2/4＝0.5 | `attempt-D2-gemma31b-head/coverage.json:.coverage_all/.coverage_core/.coverage_supporting/.missing_core_ids/.by_category` |
| E1 | **0.6119**（41/67） | **0.8214**（23/28） | **0.4615**（18/39） | **5**（F019,F044,F054,F056,F066） | 9/9＝1.0 | 3/4＝0.75 | 3/4＝0.75 | `attempt-E1-gemma31b-p4/coverage.json:.coverage_all/.coverage_core/.coverage_supporting/.missing_core_ids/.by_category` |
| E2 | 無資料 [進行中] | 無資料 | 無資料 | 無資料 | 無資料 | 無資料 | 無資料 | 無 `coverage.json` |

逐字稿觀察值（永不作為閘門；同一組 probes 對逐字稿）：B1/B2 離線報告＝`coverage_all 0.9701`、`coverage_core 0.9643`；C1 離線報告＝0.9851／1.0；C5/D1/D2/E1 `coverage.json:.transcript.coverage_all/.coverage_core`＝0.9851／1.0（僅缺 supporting F058）。差異來源＝逐字稿版本不同（見表一附註）。

### 三-B `record_quality.json` 關鍵指標

主指標 `on_start` 以 **v1.1 語意**為準；A1／B1 原檔為 v1.0，採離線重測值並標註。

| attempt | `char_count` | `body_source_tag_count` | `table_source_tag_count` | `on_start_tag_ratio` | `distinct_tag_time_ratio` | `zero_time_tag_count` | 來源 |
|---|---|---|---|---|---|---|---|
| A1 | **4338** | **61** | **0** | **0.9508**（58/61；v1.1 重測） | **0.4754**（29 種；v1.1 重測） | 7（0.1148） | 原值：`attempt-A1-27b/record_quality.json:.char_count/.body_source_tag_count`（v1.0 欄位）；v1.1：`attempt-B2-27b-fix/instrument_recheck_20260922.json:.records.A1.tag_traceability` |
| B1 | **2124** | **14** | **0** | **1.0**（14/14；v1.1 重測亦 1.0） | **0.7857**（11 種；v1.1 重測） | 3（0.2143） | 原值：`attempt-B1-moe-fix/record_quality.json:.char_count/.body_source_tag_count`；v1.1：`instrument_recheck_20260922.json:.records.B1.tag_traceability` |
| B2 | **4062** | **52** | **0** | **1.0**（52/52） | **0.2885**（15 種） | 7（0.1346） | `attempt-B2-27b-fix/record_quality.json:.char_count/.body_source_tag_count/.tag_traceability.*`（v1.1 原生；`0.0192` 為 `exact_tag_ratio` 觀察值） |
| C1 | **1927** | **20** | **0** | **1.0**（20/20） | **0.55**（11 種） | 3（0.15） | `attempt-C1-gemma31b-fix/record_quality.json:.tag_traceability.*` |
| C5 | **2593** | **28** | **0** | **1.0**（28/28；**但 28 筆全為 00:00:00**，排除後＝分母 0、`on_start_tag_ratio_excluding_zero=null`） | **0.0357**（1 種） | 28（1.0） | `attempt-C5-cloud-baseline/record_quality.json:.tag_traceability.*` |
| D1 | **1955** | **24** | **0** | **0.9583**（23/24；排除零＝18/19＝0.9474） | **0.6667**（16 種） | 5（0.2083） | `attempt-D1-gemma31b-p3/record_quality.json:.tag_traceability.*` |
| D2 | **1951** | **23** | **0** | **1.0**（23/23；排除零＝16/16） | **0.5217**（12 種） | 7（0.3043） | `attempt-D2-gemma31b-head/record_quality.json:.tag_traceability.*` |
| E1 | **2552** | **29** | **0** | **0.9310**（27/29；排除零＝21/23＝0.9130） | **0.6552**（19 種） | 6（0.2069） | `attempt-E1-gemma31b-p4/record_quality.json:.metrics.*`（＝`run_summary.json:.quality.metrics` 同值） |
| E2 | 無資料 [進行中] | 無資料 | 無資料 | 無資料 | 無資料 | 無資料 | 無 `record_quality.json` |

補充（同表來源）：
- `unsupported_entities`（觀察值、永不閘門）：A1 `["徵收股","煙酒文宣股","稽查股"]`；B1 `["徵收股","煙酒稽徵股","稽徵股"]`；B2 `["徵收股","煙酒文神股","稽查股"]`；C1 `["徵收股","稽查股"]`；C5 `[]`；D2 含 `"一股、二股"`；D1／E1 見各自 `record_quality.json`。（欄位：各場 `.unsupported_entities`／`.metrics.unsupported_entities`）
- E1 runner 品質量測另記 1 項未過：`quality_on_start_tag_ratio_ok=false`（0.9310 < 0.95；observe 模式不列 verdict）＝`attempt-E1-gemma31b-p4/record_quality.json:.checks/.check_failures`。
- 修復前 MoE 對照（非本表 attempt 清單，供理解修復效果）：P1 修復前 `on_start 0.3704`（10/27）→ B1 修復後 1.0（來源：`instrument_recheck_20260922.json:.records.P1.tag_traceability.on_start_tag_ratio`）。

---

## 表四：白話摘要（非技術讀者）

1. **「慢」幾乎不是電腦不夠力，而是模型選擇與補強輪數。** 同一台 M4 Pro、同一支 45 分鐘音檔：MoE 35B 手動場（逐字稿快取）303.9 秒；Gemma 31B 一場約 20 分鐘，P4 的 E1 因多跑 2 輪補強變 38 分鐘（多出的 1,028 秒裡約 988 秒＝2 次額外生成；來源：`timing-forensics-01/report.md` §4／§6）。**注意**：手動場免 ASR/diarization 且模型不同，不能直接與 e2e 場當同尺相比，只能當「同機上限」參考。
2. **標註品質（時間戳能不能對回逐字稿）修好了。** 修復前 MoE 只有 0.37；修復後 qwen 27B＝1.0、MoE＝1.0、Gemma＝0.93–1.0（三-A／三-B 表）。但**雲端 Gemini 那場（C5）的 1.0 是虛胖**：28 筆標註全部是 `00:00:00`（辨別力 0.036），看起來達標、其實沒有指向力。
3. **寫進紀錄的「事實量」差很多，但目前只有 4 場是同一把尺且當場量的（C5/D1/D2/E1）**：Gemini 雲端 0.806、Gemma E1 0.612、Gemma D1/D2 0.508（core 0.68）。另外 3 場（B1/B2/C1）是**事後離線補量**：27B（B2）0.821、MoE（B1）0.627、Gemma（C1）0.567——同模型差 6–7 個百分點屬單次抽樣變異，不得當「模型高下」定論（來源：表三註記＋`attempt-D1-gemma31b-p3/attempt.json:.coverage.note`）。
4. **27B 在「有事實清單可量」的場次表現最好**（B2：coverage 0.821、core 0.893、決議 9/9），但它的紀錄字元數最多（4,062）也最囉唆（同一時間戳重複張貼，辨別力 0.288 最低）；Gemma 相反：字數最少（1,927–1,955）、內容偏精簡（C1／D1 涵蓋率最低）。
5. **補強輪數決定成本也反映收斂品質**：27B（B2）與 Gemma E1 都跑 2 輪且**沒收斂**（補完仍有問題）；MoE B1 2 輪未收斂、Gemma C1 1 輪收斂、Gemma D1/D2 0 輪。E1 的 2 輪已定位為對帳器假陽性（引用標頭污染等，已修補），修補後以 E2 重測（來源：`attempt-E1-gemma31b-p4/run_notes.md` §六／§八）。
6. **可對外引用的一句話**：以「單次抽樣」為前提，地端最好的一場是 27B（B2）與 MoE（B1）在各自尺上的結果；但**地端 vs 雲端目前唯一同尺對照（C5 vs D1/D2）顯示：雲端生成快（47 秒），全場仍慢（536 秒）因為本地校正佔 320 秒**；且 C5 runner 未收尾、無驗收 verdict。

---

## §可信度與缺口

### ① 單次抽樣（不可歸因、不得外推）
- 全場次皆**單次生成**（溫度 0.6／0.7 或 0.7）：A1/B1/B2/C1/D1/D2/E1/C5 的 notes 均標「單次抽樣」（來源：各場 `attempt.json`／`coverage.json` notes；如 `attempt-D1…/attempt.json:.coverage.note`）。
- 已觀測到的抽樣變異實例：D1 vs D2（同模型同尺）coverage 完全相同但 miss 集合不同（3 筆互換）；D1 vs C1（同模型）coverage core 差 7.1 個百分點（來源：`attempt-D1…/attempt.json:.coverage.note`、`attempt-D2…/run_notes.md` §五）；E1 vs D1/D2 的逐字稿 sha 不同（`cc5b1d54` vs `199d37b5`，4 行語意校正差異；來源：`attempt-E1…/run_notes.md` §五）。
- B1 的 `body_source_tag_count=14 < 17` 退化防線屬 run-to-run 變異，未被任何閘門判定為退化（來源：`attempt-B1-moe-fix/attempt.json:.core1.notes`）。

### ② 檔案有缺／收尾異常的 attempt
- **E2 `[進行中]`**：只有 `health_snapshot.json`／`model_snapshot.json`／`provider_info.json`／`upload_response.json`；缺 `run_summary.json`、`task_final.json`、`record_quality.json`、`coverage.json`、`run_notes.md`、`sha256_manifest.json`。本表不等待、不臆測。
- **C5**：**runner 未收尾**（03:25:46 被外部終止）→ 無 `run_summary.json`／`attempt.json`／`task_final.json`／runner verdict／runner 下載的 DOCX；DOCX 為事後以同一轉換器補產生、未經 runner 結構 checks（來源：`attempt-C5-cloud-baseline/run_notes.md` 開頭與「誠實邊界」）。
- **D2、E1 無 `attempt.json`**：`timing_breakdown` 缺；時序以 `run_notes.md`＋runtime log 重建（來源：`timing-forensics-01/report.md` §9-5；本表已逐格改引 log）。D2、E1 亦**無 `verify_independent.md`**（D1／B2／C1 有）。
- **A1**：無 `run_notes.md`、無 `timing_breakdown`、無 `coverage`；執行 agent 因平台 429 中止未回報（來源：`attempt-A1-27b/attempt.json:.notes`）。
- **紀錄完整性風險（B2）**：`record_quality.json` 於 21:48–21:50 被**就地覆寫**（v1.0→v1.1 同檔名），獨立驗收列為證據完整性風險；後續應 append-only＋版本欄（來源：`attempt-B2-27b-fix/attempt.json:.instrument_metric_version`；`attempt-B2-27b-fix/verify_independent.md` §4.3 相關敘述）。
- **來源互相衝突（已並列）**：B2 的 `attempt.json:.timing_breakdown.transcript_semantic_correction_detail` 寫「採納 27 處替換」，但**同場 backend log 寫 20 處**（`data/cache/e2e/p2-27b-fix-01/backend.log:123`；A1 同為 20 處：`p2-27b-01/backend.log:120`）；Gemma 系（C1/D1/D2/E1/C5）log 為 27 處。兩來源並列、不採信其一。
- **B2 的獨立驗收判定**：`FAIL（字面閘門 1/4 未達）/ PLANNER_REPLAN_REQUIRED`（`exact_tag_ratio=0.0192` 對 rev2 字面門檻 0.8）；使用者目標與 runner 16 checks 為 PASS（來源：`attempt-B2-27b-fix/verify_independent.md` §0）。
- **A1／B1 原始 `record_quality.json` 屬 v1.0 儀器語意**（無 `metric_version`／`zero_time`／`distinct` 欄）；v1.1 值只存在於離線重測檔 `attempt-B2-27b-fix/instrument_recheck_20260922.json`（未重生成紀錄）——引用 A1/B1 的 `on_start` 時必須註明是離線重測。

### ③ `[UNVERIFIED]`（無實機證據）
- **Windows 11 ＋ Ollama 實機**：全 repo 無實機 E2E 證據；P4 波跨 OS 稽核結論：產品執行路徑「預期可運作（信心中）」、P4 品質驗證工具「不修則不可運作（信心高，`tzdata` BLOCKER）」、品質對等「未成立為已證事實（信心低）」（來源：`e2e/crossos-p4-audit-01/report.md` §4）。
- Windows/Ollama 取樣參數（0.8/20/1.08）之輸出品質無 A/B 數據；Windows 逐字稿格式是否同為 `[start-end] 發言者：` 未驗；`host.docker.internal` 可解析性未驗；BOM／CRLF 影響範圍未驗（來源：同報告 §5 `[UNVERIFIED]` 清單 1–7）。
- 手動場 `.docx` 的 +124.3 s 觸發機制（下載觸發 vs 排程延遲）[UNVERIFIED]；gemma 冷啟動時間無樣本；執行當下 swap／熱節流無取樣（來源：`timing-forensics-01/report.md` §9-1/2/4/7）。
- D2、E1 的 `attempt.json` 缺＝其 `timing_breakdown` 屬「以 log 重建」而非產物自證（同報告 §9-5）。
- E1 校正比 D1 慢 46.9 s 的原因未知（同報告 §9-6）。

### 使用建議（給 27B 落地後的對照者）
- 新 27B E2E 落地後，請確認：同音檔 sha `982151f4…`、模板 `section_meeting`、`coverage-1.0.0`＋`tag_traceability-1.1.0`、checklist sha `cf012d1f…`，並以**同一張表二／表三欄位**填值＋附來源；與 B2（27B 現行最佳）對照時，務必標註「B2 為 v1.1 覆寫事件場＋單次抽樣」，且 B2 的 coverage 屬事後離線量測、新場若是 runner 當場量測，量測性質不同須加註。

