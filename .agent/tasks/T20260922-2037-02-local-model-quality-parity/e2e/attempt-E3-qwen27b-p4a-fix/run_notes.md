# attempt-E3-qwen27b-p4a-fix 執行紀錄（`Qwen3.8-27B-Splash` @ HEAD `0d34fa1`，真實音檔 E2E）

> 本檔由主執行 agent 撰寫（繁體中文）。數字一律由撰寫者以 `git rev-parse HEAD`、`shasum -a 256`、
> 重跑量尺、直接讀 runtime log 逐項查核；寫入範圍僅本目錄（append-only）。
> 本場是 **P4-A 假陽性修補（`f374c27`）落地後，27B 的第一次真實音檔 E2E**，也是使用者要求「不要測 35B-A3B、
> 專注 27B」的直接對應場次。

## 0. 自核結果

| 查核項 | 方法 | 結果 |
|---|---|---|
| HEAD／build revision | `run_summary.expected/actual_build_revision` | `0d34fa1ca2d2537866b0e8b46ce310979ea1160f`（相等） |
| 來源音檔 | `sha256`（Downloads 原檔＝stored upload） | `982151f4…012828`（45,107,503 bytes） |
| 逐字稿 | `sha256` | `b3cb89a6…7e9b90e7`（**與 E2／D1／D2 的 `199d37b5…` 不同**，見 §九-6） |
| DOCX | `sha256` | `ad396dd9…f7a3dfd`＝`sha256_manifest.meeting_record_docx_sha256` |
| 紀錄 md | `sha256` | `740b0429…d1b520`＝`run_summary.quality.record_markdown.sha256` |
| 量尺重跑 | `measure_coverage.py`（同一釘版清單） | `coverage_all 0.7761`／`core 0.8571` 與 runner `coverage_observation.json` **完全一致** |
| 閘門 | `run_summary.json` | `verdict=PASS`、16/16 checks 全 `true`、`failure_reasons=[]` |
| record_quality 重跑 | `measure_record_quality.py` | 除 `known_term_fix_hits` 之外全欄相同（該欄取決於逐字稿；重跑值＝`right_hits 4`） |

## 一、受測設定

| 項目 | 值 | 來源 |
|---|---|---|
| 模型 | `Qwen3.8-27B-Splash`（LM Studio key `qwen3.8-27b-splash`） | `model_snapshot(.end).json` |
| 已載入實例 | `unique_loaded_llm_count=1`；instance `qwen3.8-27b-splash`、**`context_length=128000`**、`parallel=4` | `model_snapshot.json` |
| 處理模式 | `processing_mode=local`；`effective_local_llm_provider=lmstudio` | `task_final.json`＋`run_summary.engine` |
| 模板 | `section_meeting` | `task_final.template_id` |
| task_id | `d48ce298` | `task_final.json` |
| 執行窗 | 2026-09-23T10:13:59.923 → 10:37:16.040；**牆鐘 1396.117 s（23:16.12）** | `run_summary` 加減 |
| 任務端到端 | 10:14:05.159 → 10:37:10.027；**1384.868 s**；log「耗時: 1384.9秒」 | `task_final.json`＋log |
| 觀測模式 | runner `--quality-mode observe`；產品端 `LOCAL_LLM_RECORD_COVERAGE_MODE` 預設（enforce） | 啟動命令＋log `cov_*` 有值 |
| 執行前置 | 乾淨工作樹 preflight 通過（HEAD `0d34fa1`） | runner stdout |

啟動命令：

```
uv run python scripts/e2e/run_owned_e2e.py \
  --audio "/Users/hsiaojohnny/Downloads/0903-科務會議.m4a" --template section_meeting \
  --processing-mode local \
  --artifacts-dir .agent/tasks/T20260922-2037-02-local-model-quality-parity/e2e/attempt-E3-qwen27b-p4a-fix \
  --runtime-dir data/cache/e2e/p4-qwen27b-e3 \
  --quality-mode observe \
  --coverage-checklist .agent/tasks/T20260922-2037-02-local-model-quality-parity/quality/fact_checklist.json
```

## 二、閘門結果

- `verdict=PASS`、`failure_reasons=[]`、`checks` 16/16 全 `true`（含 `formal_docx_valid`、`metrics_valid`、`child_terminated`）。
- `quality.checks` 5/5 全 `true`：`table_tag_count_zero`、`body_tag_count_ok`、`traceable_tag_ratio_ok`、
  **`on_start_tag_ratio_ok=true`（1.0）**、`on_start_excluding_zero_ok=true`（1.0）。
- 任務終態：`status=completed`、`progress=100.0`、`summary_failed=false`、`error_message=null`。

## 三、耗時分解（證據：`data/cache/e2e/p4-qwen27b-e3/backend_data/logs/app_2026-09-23.log`）

| 階段 | 秒數 | 關鍵數字 |
|---|---|---|
| ASR（apple，fail-closed） | **15.62** | `audio_duration_seconds=2695.061`、RTF 0.0058、`segment_count=1340`、dropped 0、locale `zh-Hant-TW` |
| diarization | **155.1** | 682 段、8 位發言者、RTF 0.058；標註後 183 段發言 |
| 語意校正（LLM） | **120.1** | 10:16:56.681→10:18:56.802；45 段中 8 段有修正、1 段放棄、採納 21 處替換（12 次 LM Studio 呼叫） |
| 萃取（extraction） | **253.4** | 10:18:56.80→10:23:10.218；零損串接（3265 tokens ≤ 118858） |
| 首版最終生成 | **266.7** | 10:23:10.227→10:27:36.915（temperature 0.7） |
| 補強第 1 輪 | **294.9** | 10:27:37.028→10:32:31.937 |
| 補強第 2 輪 | **277.9** | 10:32:32.036→10:37:09.908 |
| 後處理＋DOCX | ≈5.1 | 術語修正 1 處、標註吸附 2 處；10:37:15.089 DOCX 完成 |

- pipeline metrics：`chunk_count=1`、**`logical_generations=4`**、`semantic_attempts=0`、`network_retries=0`、
  `merge_rounds=0`；`duration_seconds={'extraction': 253.4, 'merge': 0.0, 'final_and_refine': 839.8, 'total': 1093.2}`。
- **固定成本**（ASR＋diarization＋校正）＝**290.8 s**；**模型生成**＝1093.2 s（其中補強 572.8 s＝牆鐘 41.0%）。
- 對照：D1 1218.6–1227.2 s → 本場 **+13.8%**（**≤ +25%，時間面達標**；E1 +85.7%、E2 +71.8% 皆未達）。

## 四、量測結果

### coverage（`coverage.json`，label `E3-qwen27b-p4a-fix`；`coverage-1.0.0`；清單 sha `cf012d1f…`）

- `coverage_all=0.7761`（52/67）、`coverage_core=0.8571`（24/28）、`coverage_supporting=0.7179`（28/39）。
- `missing_core_ids=[F021, F054, F055, F056]`。
- `record_char_count=3396`（E2 2318、C5 2593、B2 4062）。
- by_category：**decision 9/9＝1.0**、name 3/3＝1.0、**number 4/4＝1.0**、constraint 12/13＝0.9231、
  action_item 6/9＝0.6667、topic 16/25＝0.64、**date 2/4＝0.5**。

### record_quality（`record_quality.json`；`tag_traceability-1.1.0`）

- `char_count=3396`、`body_source_tag_count=45`、`table_source_tag_count=0`、`tagged_item_ratio=1.0`、
  `cross_section_duplicate_pairs=0`、`instruction_item_count=24`。
- `traceable_tag_ratio=1.0`、`on_start_tag_ratio=1.0`、`excluding_zero=1.0`、`exact_tag_ratio=0.7333`、
  `zero_time_tag_count=8`（0.1778）、**`distinct_tag_time_ratio=0.6667`**（E2 0.5926、D1 0.6667、B2 0.288）。
- `known_term_fix_hits`：`right_hits=4`（`徵收股` 1、`瑞里` 3；逐字稿側 `left_hits=3`）。
- `unsupported_entities_count=4`（P4-B tripwire 之量尺投影；E2 為 2）。

### in-run 對帳（log `cov_*`；產品側真實觸發值）

| 指標 | 值 |
|---|---|
| `cov_expected_topic` / `cov_missing_topic` | **13 / 1**（E2 為 12 / 5） |
| `cov_expected_decision` / `cov_missing_decision` | **0 / 0**（見 §九-4） |
| `cov_expected_number` / `cov_missing_number` | **9 / 0** |
| `cov_expected_date` / `cov_missing_date` | **4 / 0** |
| `cov_issues_added` | 1 |

## 五、殘餘問題逐條判定（真缺 vs 假陽性）

**in-run 唯一殘留問題＝假陽性（已離線重播證實）**

- 第 2 輪問題字串：「議題遺漏 1 項：廉政宣導（拆勤、採購、公務車使用）」。
- 紀錄第 40 行同時含「廉政宣導」「拆勤」「採購」「公務車」；失敗點是括號內詞組 `公務車使用` 未連續出現。
- 離線重播（`/tmp/e3_replay.py`，0 模型成本、現行 HEAD）：`missing_topic=1`，
  診斷 `{'廉政宣導': True, '拆勤': True, '採購': True, '公務車使用': False}` → **確認為假陽性**。
- 影響：這一筆假陽性使本場跑滿第 2 輪（收斂保護未觸發），也是 §九-1 未達的直接原因。

**清單（pinned checklist）15 筆未涵蓋的性質判定**（以 `grep` 對紀錄逐詞核對）

- **真缺（紀錄確實沒有該內容）**：`F021`（內稽＝0 命中）、`F008`（預估缺＝0）、`F017`（會辦／名單＝0）、
  `F032`（慶生＝0）、`F047`（測試＝0）、`F051`（Kiosk／縣市＝0）、`F055`（禮堂／走廊＝0）、`F056`（防水／刨除＝0）、
  `F057`（挖＝0）、`F058`（國稅局／高架＝0）。
- **部分命中（紀錄以不同措辭寫到）**：`F030`（文康 3 命中、`請假` 0）、`F059`（`黴味` 1 命中、`三樓` 0）、
  `F062`（廠商 2 命中、`發霉` 0）。
- **疑似量尺字面假陰性（需 P4-G 範圍處理）**：`F016`（出發／小心各 2 命中）、`F054`（紀錄第 48 行「搬遷時間可能延遲」）。
- 結論：**本場漏寫以真缺為主（約 10/15），不是對帳器誤判**——與 Gemma E2 場「in-run 全是假陽性」恰相反。

## 六、跨場同尺比較（同一支音檔、同模板、同釘版清單）

| 場次 | 模型（引擎） | 補強輪數 | 牆鐘 s | all | core | topic | number | date | action | decision | 字元數 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| C5 | `gemini-3.5-flash-lite`（雲端） | 1 | 無資料 | **0.8060** | **0.8929** | 0.72 | 0.50 | 1.00 | 0.6667 | 1.00 | 2593 |
| **E3（本場）** | **Qwen3.8-27B-Splash（地端）** | **2** | **1396.1** | **0.7761** | **0.8571** | 0.64 | **1.00** | 0.50 | 0.6667 | 1.00 | 3396 |
| B2（較早） | Qwen3.8-27B（地端，p2-27b-fix-01） | 2 | 1710 | 0.8209 | 0.8929 | 0.76 | 0.50 | 0.75 | 0.7778 | 1.00 | 4062 |
| E2 | `gemma-4-31B-it-MLX-4bit`（地端） | 2 | 2107.9 | 0.6119 | 0.8214 | 0.32 | 0.75 | 1.00 | 0.7778 | 0.7778 | 2318 |
| E1 | `gemma-4-31B-it-MLX-4bit`（地端） | 2 | 2278.8 | 0.6119 | 0.8214 | 0.40 | 0.75 | 0.75 | 0.6667 | 1.00 | 2552 |

- **本場把地端與雲端的事實留存差縮到 3.0 pp（all）／3.6 pp（core）**（單場、非同輸入，見 §九-6）。
- 分類上：**number 4/4 反而優於雲端（2/4）**；弱點在 **date 2/4（雲端 4/4）** 與 topic（0.64 vs 0.72）。
- 同一台 M4 上，Qwen3.8-27B 比 gemma-4-31B **快 34%（1396 vs 2108 s）且事實留存高 16.4 pp（all）**。

## 七、可重現指令

```
DATA_DIR=/tmp/probe_scratch uv run --frozen python scripts/e2e/measure_coverage.py \
  --record data/cache/e2e/p4-qwen27b-e3/backend_data/outputs/0903-科務會議_d48ce298.md \
  --checklist .agent/tasks/T20260922-2037-02-local-model-quality-parity/quality/fact_checklist.json \
  --label E3-qwen27b-p4a-fix \
  --transcript data/cache/e2e/p4-qwen27b-e3/backend_data/outputs/0903-科務會議_d48ce298_逐字稿.txt \
  --json-out .agent/tasks/T20260922-2037-02-local-model-quality-parity/e2e/attempt-E3-qwen27b-p4a-fix/coverage.json

DATA_DIR=/tmp/probe_scratch uv run --frozen python scripts/e2e/measure_record_quality.py \
  --record data/cache/e2e/p4-qwen27b-e3/backend_data/outputs/0903-科務會議_d48ce298.md \
  --transcript data/cache/e2e/p4-qwen27b-e3/backend_data/outputs/0903-科務會議_d48ce298_逐字稿.txt \
  --template section_meeting --out /tmp/e3_rq_recheck.json
```

## 八、產物路徑（raw payload 於 gitignored runtime dir）

- 會議紀錄 DOCX：`data/cache/e2e/p4-qwen27b-e3/backend_data/outputs/0903-科務會議_d48ce298.docx`
- 會議紀錄 md：`.../0903-科務會議_d48ce298.md`（3396 字元、83 行、8 個章節）
- 逐字稿：`.../0903-科務會議_d48ce298_逐字稿.txt`

## 九、未達項與風險（如實登錄）

1. **補強輪數 2 > 1（§9.4 未達）**：跑滿 `MAX_REFINEMENT_ROUNDS=2`，且第 2 輪結束仍有 1 筆未解
   （log `本地摘要仍有待補強問題`）。根因＝§五的**假陽性**（1 筆），非模型漏寫。
2. **時間面達標但代價可觀**：牆鐘 +13.8% vs D1（≤+25% 達標），但補強占牆鐘 41.0%（572.8 s）。
3. **共同歸因未隔離（§9.3 F1④）**：本場未以 `LOCAL_FIDELITY_TRIPWIRES=false` 隔離 → 數字／日期類的
   召回功勞**不得獨歸 P4-A**。
4. **決議類 in-run 為 no-op**：`cov_expected_decision=0`，3 次 WARNING 明示「決議期望集合為空」。
   警告有 fire（符合 §9.3 設計），但**決議類的補強保障在本場等於沒作用**；最終 decision 9/9 是模型本身寫到，
   不是補強救回。根因疑為 Qwen 的萃取筆記「議題與決議」區塊格式與抽取器期望不符（`[UNVERIFIED]`，未保存中間筆記可證）。
5. **聚合門檻為單場觀察值**：`all 0.7761 ≥0.65`、`core 0.8571 ≥0.80` **皆達標**，但依 §9.3 F1② 需
   **≥2 次取中位數**才可宣稱支持；本場 n=1。
6. **跨場非同輸入**：本場逐字稿 `b3cb89a6…` 與 E1／E2／D1／D2 不同（ASR 抽樣差異），與 C5／B2 亦不同 →
   表列為「同尺」而非「同輸入」。
7. **Windows／Ollama 未實機**：`[UNVERIFIED]`（見 `e2e/portability-audit-02/report.md`；靜態稽核 PASS）。
8. **本場後續修補未回溯**：§五的假陽性已交後續修補處理（不改變本場已凍結之數字）。
