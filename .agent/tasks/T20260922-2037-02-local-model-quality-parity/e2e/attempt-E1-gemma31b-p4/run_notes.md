# attempt-E1-gemma31b-p4 執行紀錄（`gemma-4-31B-it-MLX-4bit` @ HEAD `da37407`，真實音檔 E2E）

> 本檔由 **E1 證據打包員**撰寫（繁體中文）。文內數字一律由打包者以 `git rev-parse HEAD`、
> `shasum -a 256`、**重跑量尺**、直接讀取 runtime log 逐項查核。寫入範圍僅本目錄。
> 本場是 **P4 波（§9.3／§9.4／§9.6）落地後的第一次真實音檔 E2E**，也是**未達項的來源**（§九）。

## 0. 打包者自核結果

| 查核項 | 方法 | 結果 |
|---|---|---|
| HEAD | `git rev-parse HEAD` | `da37407462c997ebfd1f4b87c6a90f190fd2fe99`（＝P4 波實作 commit） |
| 來源音檔 | `shasum -a 256` Downloads 原檔 | `982151f4…012828`（45,107,503 bytes）＝`source_audio_sha256`＝`stored_upload_sha256` |
| 逐字稿 | `shasum -a 256`（outputs 與 runtime 根） | 兩份皆 `cc5b1d54…f342c`；**與 D1／D2 的 `199d37b5…` 不同**（見 §五註） |
| DOCX | `shasum -a 256`（outputs 與 runtime 根） | 兩份皆 `28da0b3c…cee9b`＝`meeting_record_docx_sha256` |
| 紀錄 md | `shasum -a 256` | `c76dcba0…236b0`；＝`record_quality.record_markdown.sha256` |
| 量尺重跑 | §七兩條指令（`DATA_DIR=/tmp/probe_scratch`） | `coverage.json` 與 `record_quality.json` 與 runner 產出**逐欄相同** |
| runner 閘門 | 讀 `run_summary.json` | 16/16 checks 全 `true`、`failure_reasons=[]`、`verdict=PASS` |
| 離線重播 | §六（P4-A 對帳，0 模型成本） | 重現 in-run 症狀（`expected_topic=0`、11/11 決議判缺）→ 修補後 3 項 |

## 一、受測設定

| 項目 | 值 | 來源 |
|---|---|---|
| 模型 | `gemma-4-31B-it-MLX-4bit`；LM Studio key `gemma-4-31b-it-mlx`（publisher `lmstudio-community`、arch `gemma4`、`mlx`、4bit、31B、18,444,440,967 bytes） | `model_snapshot(.end).json` |
| 已載入 LLM | `unique_loaded_llm_count=1`；instance `gemma-4-31b-it-mlx`、`context_length=71936`、`parallel=4`（與 D1／D2 同設定） | `model_snapshot.json` |
| 處理模式 | `processing_mode=local`／provider `lmstudio`（`effective_local_llm_provider`） | `task_final.json`＋`run_summary.engine` |
| 模板 | `section_meeting` | `task_final.template_id` |
| task_id | `67fe4b0d` | `task_final.json` |
| 執行窗 | 2026-09-23T05:00:45.897627+08:00 → 05:38:44.663878+08:00；**牆鐘 2278.766 s（37:58.77）** | 我以 datetime 相減 |
| 任務端到端 | 05:00:51.250653 → 05:38:42.009725；**2270.759 s**；backend log「耗時: 2270.8秒」 | `task_final.json`＋log |
| 觀測模式 | runner `--quality-mode observe`；產品 `LOCAL_LLM_RECORD_COVERAGE_MODE=enforce`（預設） | 啟動命令＋`backend.log` 的 `cov_*` 欄位有值 |

## 二、閘門結果

- `verdict=PASS`、`failure_reasons=[]`；16/16 checks 全 `true`（含 `formal_docx_valid`、`metrics_valid`、`child_terminated`）。
- 任務終態 `status=completed`、`progress=100.0`、`summary_failed=false`、`error_message=null`。
- **品質觀測（不列 verdict）**：`quality.checks`＝`quality_table_tag_count_zero=true`／`quality_body_tag_count_ok=true`／
  `quality_traceable_tag_ratio_ok=true`／**`quality_on_start_tag_ratio_ok=false`**／`quality_on_start_excluding_zero_ok=true`。
  逐字稿來源標註起點命中率 `0.9310 < 0.95`；依 plan §9.9「P4-D `required` 升級決策本波不做」，
  `observe` 模式下不影響 verdict，但這是**未來升級 `required` 前必須先處理的事實**（見 §九-3）。

## 三、耗時分解（證據：`data/cache/e2e/p4-gemma31b-e1/backend_data/logs/app_2026-09-23.log`）

| 階段 | 秒數 | 關鍵數字 |
|---|---|---|
| ASR（apple，fail-closed） | **15.801** | `audio_duration_seconds=2695.061`、`RTF=0.0059`、`segment_count=1340`、`dropped=0` |
| diarization | **152.0** | 682 段、8 位發言者、`RTF 0.056`；標註後 183 段發言 |
| 語意校正（LLM） | **≈358.6** | 05:03:39.795 → 05:09:38.427；45 段中 8 段有修正、1 段放棄、採納 27 處替換 |
| 本機 LLM pipeline | **1743.6** | `chunk_count=1`、**`logical_generations=4`**、`extraction=372.2`、`final_and_refine=1371.4`、`merge_rounds=0` |
| 補強輪數 | **2 輪** | 05:22:31（第 1 輪）、05:30:35（第 2 輪）；每輪生成 ≈485 s |
| 其餘（DOCX／後處理／收尾） | ≈8.8 | 2278.77 − (15.8+152.0+358.6+1743.6) |

**固定成本**（ASR＋diarization＋語意校正）＝**526.4 s（8.8 分）**；**模型生成**＝4 次呼叫 ×≈436 s ＝1743.6 s。

## 四、量測結果

### coverage（`coverage.json`；`coverage-1.0.0`；checklist `cf012d1f…`）

- `coverage_all=0.6119`（41/67）、`coverage_core=0.8214`（23/28）、`coverage_supporting=0.4615`（18/39）。
- `missing_core_ids=[F019, F044, F054, F056, F066]`（5 筆；D1／D2 為 9 筆）。
- `by_category`：decision **9/9=1.0**、name 3/3=1.0、action_item 6/9=0.6667、number **3/4=0.75**、
  constraint 7/13=0.5385、topic 10/25=0.4、date **3/4=0.75**。
- `record_char_count=2552`（D2 1951）、`record_normalized_char_count=1794`。
- 逐字稿觀察值：`coverage_all=0.9851`（66/67）、`coverage_core=1.0`（28/28）、僅缺 supporting `F058`。
- **P4-A 主歸因閘門逐筆核對（plan §9.3）**：`F024`（600 元）**False→True**、
  `F025`（800 元／17 人／13600 元）**False→True**、`F015`（10/14）**False→True**、
  `F021`（下週一內稽）**False→True**、`F061`（10月底搬進）**False→True**、
  `F010`（15%）True→True（不退步）。`F014`（100 多戶）仍 False（D1 亦 False；量尺 probe 假陰性，屬 P4-G 範圍）。

### record_quality（`record_quality.json`；`tag_traceability-1.1.0`）

- `body_source_tag_count=29`（D2 23）、`table_source_tag_count=0`、`tagged_item_ratio=1.0`、
  `cross_section_duplicate_pairs=0`、`instruction_item_count=10`。
- `tags_total=29`、`tags_inside_any_segment=29`、`traceable_tag_ratio=1.0`、`tags_exact_segment_start=2`、
  `exact_tag_ratio=0.0690`、`tags_on_real_segment_start=27`、`on_start_tag_ratio=0.9310`、
  `excluding_zero=21/23=0.9130`、`zero_time_tag_count=6`、
  **`distinct_tag_time_count=19`、`distinct_tag_time_ratio=0.6552`（D2 0.5217 → P4-D 去重複化生效）**。
- 逐字稿來源標註未命中的 2 筆＝`（科長，00:04:35）`、`（科長，00:42:15）`——**這兩個時間點不存在於逐字稿任何段首**
  （打包者以 `grep` 對逐字稿全文核對，0 命中）＝模型自帶時間戳幻覺，非 P4 造成（D1 亦有 1 筆、D2 恰為 0）。

## 五、與 D1／D2 同尺對照

| 指標 | D1（P3 後） | D2（HEAD `f001e93`） | **E1（P4，本場）** |
|---|---|---|---|
| `coverage_all` | 0.5075 | 0.5075 | **0.6119** |
| `coverage_core` | 0.6786 | 0.6786 | **0.8214** |
| `coverage_supporting` | 0.3846 | 0.3846 | 0.4615 |
| `missing_core_ids` | 9 筆 | 9 筆 | **5 筆** |
| `record_char_count` | 1955 | 1951 | **2552** |
| `body_source_tag_count` | 24 | 23 | **29** |
| `on_start_tag_ratio` | 0.9583 | 1.0 | 0.9310 |
| `distinct_tag_time_ratio` | 0.6667 | 0.5217 | 0.6552 |
| 補強輪數 | 0 | 0 | **2** |
| 牆鐘（秒） | 1227.2 | 1251.13 | **2278.77** |

**逐字稿註（歸因邊界）**：E1 的逐字稿 sha `cc5b1d54…` 與 D1／D2 的 `199d37b5…` 不同——差異僅 4 行、
集中在語意校正階段（LLM 溫度非 0）的字詞替換（例：`人事室`→`人事事`、`瀋圓圓`→`審員圓`），
ASR 段數與音檔完全相同（1340 段、2695.061 s）。因此 P4-A 的召回改善**不能完全排除**這 4 行差異的影響，
但兩者皆與 checklist 的 `F024／F025／F015／F021／F061` probes 無關（打包者以 probe token 對該 4 行核對）。

## 六、離線重播：P4-A 對帳的**假陽性根因**（本場最重要發現，0 模型成本）

E1 in-run log 顯示 `cov_missing_decision=11`（11 項決議全部判缺），但人工核對 E1 紀錄正文，
**11 項中有 7 項其實已經寫進紀錄**（例：「確認發放日期為 10/14，針對瑞理地區之發放人數約 100 多戶」
已在紀錄三（一）；「嚴禁將科內公共訊息或照片轉傳至外部群組（含親友）」已在二（七））。
另 3 項條目剝除引用標頭後是**空殼**（`[00:20:15] 發言者 1（主席）裁示：`，決議內容寫在下一層條列）。

**重播方法**（`[INFERRED]` 等價，非 byte 級重現）：以同一支萃取提示詞＋同一支模型＋同一份 E1 逐字稿
重新生成一份筆記（`temp=0.6`、`num_predict=3072`、2,519 字；真實 in-run `merged_notes` 未落盤），
再把該筆記與 **E1 最終紀錄**餵進 `_validate_record_source_coverage`：

| 觀測 | 修補前 | 修補後 |
|---|---|---|
| `expected_topic` / `missing_topic` | **0 / 0**（類別恆為 no-op） | **10 / 3** |
| `expected_decision` / `missing_decision` | **11 / 11** | **8 / 3** |
| `expected_number` / `missing_number` | 9 / 0 | 9 / 0 |
| `expected_date` / `missing_date` | 4 / 0 | 4 / 0 |
| `issues_added` | 1 | 2 |

重播**精確重現** in-run 症狀（`cov_expected_topic=0`、決議 11/11 判缺），故根因判定為：

1. **引用標頭污染比對**：真實筆記的決議條目寫成 `[00:08:15] 發言者 1（主席）裁示：<正文>`；
   引用標頭不是事實本身，卻在滑窗 LCS 裡佔掉一半長度 → 已涵蓋的條目被判遺漏。
2. **議題形式未被支援**：真實筆記把議題寫成**整行粗體標題**（`- **組織規程與編制變動（11月1日生效）**`），
   而非提示詞範例的 `- **議題**：X` → 議題期望集合恆為 0（67 條清單裡最大的缺口類別 topic 因此從未被補強）。
3. **空殼條目**：`…裁示：` 後面沒有正文者無法被滿足，只會讓補強永遠不收斂。

**修補**（commit 見 git log；只改 P4-A 的筆記解析，不動任何門檻／雲端路徑／`off` 行為）：
`_strip_notes_item_quote_prefix`（剝引用標頭）＋空殼丟棄＋`include_bold_titles`（議題粗體標題）。
落地後同組輸入 `cov_missing_decision` 11→3、`cov_expected_topic` 0→10；新增 T-20／T-21／T-22 三個回歸測試。

## 七、可重現指令（打包者實際執行；`DATA_DIR=/tmp/probe_scratch`）

```
cd /Users/hsiaojohnny/dev/convert
R="data/cache/e2e/p4-gemma31b-e1/backend_data/outputs/0903-科務會議_67fe4b0d.md"
T="data/cache/e2e/p4-gemma31b-e1/backend_data/outputs/0903-科務會議_67fe4b0d_逐字稿.txt"

uv run --frozen python scripts/e2e/measure_record_quality.py --record "$R" --transcript "$T" \
  --template section_meeting --out .agent/.../attempt-E1-gemma31b-p4/record_quality.json

uv run --frozen python scripts/e2e/measure_coverage.py --record "$R" \
  --checklist .agent/tasks/T20260922-2037-02-local-model-quality-parity/quality/fact_checklist.json \
  --label E1-gemma31b-p4 --transcript "$T" \
  --json-out .agent/.../attempt-E1-gemma31b-p4/coverage.json
```

## 八、如實邊界與**未達項**（不得超譯）

1. **未達（P4-B 驗收，plan §9.4 F2）**：本場**補強 2 輪**（>1 輪）且**牆鐘 2278.77 s vs D1 1227.2 s ＝ +85.7%**（>+25%）
   → 依 plan §9.4 的「輪數 >1 或 wall 退步 >25%＝未達」，**本場的輪數／牆鐘準則未達**。
   成本拆解：多出的 ≈1028 s 幾乎全部＝**2 次額外 LLM 生成**（≈988 s），非 ASR／非硬體。
   **根因已定位並修補（§六）**，修補後以 E2 場重測；但須誠實指出：**plan 自身的兩個準則互相衝突**——
   它同時「預期 1 輪」與「wall 退步 ≤+25%」，而本模型單輪生成成本 ≈485 s ＝ D1 牆鐘的 +39.5%，
   即使收斂到 1 輪仍會超過 +25%。此為 **planner 決策**（不得由實作者自行放寬門檻）。
2. **聚合觀察目標未達**：`coverage_all 0.6119 < 0.65`；`coverage_core 0.8214 ≥ 0.80` 已達。
   兩者皆為「觀察值、須 ≥2 次取中位數才可宣稱支持」（plan §9.3 F1②）→ 單場不得定論。
3. **`on_start_tag_ratio 0.9310 < 0.95`**：`observe` 模式下不影響 verdict；來源為模型自帶的 2 個不存在時間戳，
   非 P4 造成。`required` 升級前必須先處理（plan §9.9 已把升級決策排除在本波外）。
4. **單次抽樣**：temperature 0.7，跨 run 差異存在（D1 vs C1 曾差 6.0–7.1 pp）→ 跨模型比較需 ≥2 次中位數。
5. **未做的隔離場**：plan §9.3 F1④ 要求「P4-A 驗收場以 `LOCAL_FIDELITY_TRIPWIRES=false` 量測」以隔離
   P4-B 的召回貢獻；**本場未開該開關**（tripwires 為預設 True）→ 本場召回功勞**不得獨歸 P4-A**，
   須標示為 **P4-A＋P4-B 共同歸因**。隔離場待 E2／E3 或後續 attempt 補。
6. **本模型僅一場**：Gemma 31B 的 E1 為單場；plan §9.4 另要求 27B 一場（`Qwen3.8-27B-Splash`）。
