# 獨立驗收稽核（Stage 05 語意）— attempt-E1-gemma31b-p4

- 受測模型：`gemma-4-31B-it-MLX-4bit`（LM Studio instance `gemma-4-31b-it-mlx`，`context_length=71936`、`parallel=4`、`unique_loaded_llm_count=1`；`model_snapshot(.end).json`）
- 受測 build revision：`da37407462c997ebfd1f4b87c6a90f190fd2fe99`（`run_summary.expected_build_revision == actual_build_revision`）
- 稽核時 repo HEAD：`0d34fa1ca2d2537866b0e8b46ce310979ea1160f`（`git rev-parse HEAD`）
- 稽核時間：2026-09-23 10:10–10:25（Asia/Taipei）
- 執行窗：2026-09-23T05:00:45.897627+08:00 → 05:38:44.663878+08:00
- 角色邊界：本檔由 Stage 05 獨立驗收員新增（append-only）；產品程式碼／`plan.md`／`handoff.md`／既有證據檔**均未修改**，未執行 `git add`／`commit`。

## 一、稽核方法

實際執行（全部唯讀；`DATA_DIR=/tmp/probe_scratch`）：

1. `uv run --frozen python scripts/e2e/measure_coverage.py --record data/cache/e2e/p4-gemma31b-e1/backend_data/outputs/0903-科務會議_67fe4b0d.md --checklist …/quality/fact_checklist.json --label E1-verify-independent --transcript …_逐字稿.txt --json-out /tmp/verify_E1_coverage.json`
2. `uv run --frozen python scripts/e2e/measure_record_quality.py --record <同上> --transcript <同上> --template section_meeting --out /tmp/verify_E1_record_quality.json`
3. `shasum -a 256`：MD／DOCX／逐字稿／來源音檔／runtime 根副本／uploads 副本，逐項對 `sha256_manifest.json` 與 `run_summary.json`。
4. 由 `data/cache/e2e/p4-gemma31b-e1/backend_data/logs/app_2026-09-23.log` 逐行重建耗時分解，與 `pipeline metrics`、`task_final.json`、backend「耗時:」行交叉驗證。
5. **自建離線重播**（現行 HEAD、0 模型成本）：直接呼叫 `backend.services.summarization.SummarizationService._validate_record_source_coverage`（`LOCAL_LLM_RECORD_COVERAGE_CATEGORIES="number,date"`、`notes=""`），對 E1／E2／D1／D2／B2／C1 六份紀錄重跑數字／日期對帳。
6. 逐條 grep 最終紀錄原文（600／800／17／13600／15%／10 月 14 日／10 月底／週一）＋ `zipfile` 檢查 DOCX 結構。
7. 選跑相關測試：`pytest tests/test_t20260923_p4a_record_coverage.py tests/test_t20260923_p4a_false_positive_fix.py tests/test_t20260922_2037_p4b_fidelity_tripwires.py tests/test_t20260923_p4b_fidelity_wiring.py tests/test_owned_e2e_acceptance.py tests/test_record_quality_metrics.py tests/test_t20260922_2037_p3_parity.py -q` → **134 passed（1.35 s）**；全套未重跑（如實登錄）。

讀過的檔：`plan.md` §9（含 §9.3／§9.4／§9.6／§9.9／§9.11）、`handoff.md` §7／§8、`execution.md` §3／§8／§10、本場 `run_summary.json`／`task_final.json`／`coverage.json`／`record_quality.json`／`sha256_manifest.json`／`model_snapshot(.end).json`／`provider_info.json`／`coverage_observation.json`、本場 `run_notes.md`（**僅交叉比對，不採信其結論**）、D1 `attempt.json`（baseline 出處）。

## 二、重跑量尺 vs 證據檔

### 2.1 檔頭（`shasum -a 256`）

| 欄位 | 證據檔值 | 我的重跑值 | 一致？ |
|---|---|---|---|
| 來源音檔 `source_audio_sha256` | `982151f4…012828` | Downloads 原檔＝`982151f4…012828`（45,107,503 B） | ✅ |
| `stored_upload_sha256`（uploads/9660230a776b.m4a） | `982151f4…012828` | `982151f4…012828` | ✅ |
| MD（outputs `…_67fe4b0d.md`） | `c76dcba0…236b0`（=`run_summary.quality.record_markdown.sha256`=`coverage.json.record_sha256`） | `c76dcba0…236b0` | ✅ |
| DOCX（outputs／runtime 根 `meeting_record.docx`） | `28da0b3c…cee9b`（`sha256_manifest`） | 兩份皆 `28da0b3c…cee9b` | ✅ |
| 逐字稿（outputs／runtime 根 `transcript.txt`） | `cc5b1d54…f342c`（`sha256_manifest`） | 兩份皆 `cc5b1d54…f342c` | ✅ |
| DOCX 結構 | `formal_docx_valid=true` | `zipfile.testzip()` 無壞檔；`word/document.xml` 含 `600`／`800`／`13600` | ✅ |

### 2.2 coverage（`coverage-1.0.0`；checklist `cf012d1f6983f67ecb47cc7a6486e48c110a6b2782ad94cccf0332a4ec6ec001`）

逐欄比對（`/tmp/verify_E1_coverage.json` vs `coverage.json`）：**全部扁平欄位 0 差異**（僅 `label`／`record_path` 因重跑參數不同）。關鍵值：

| 欄位 | 證據檔值 | 重跑值 | 一致？ |
|---|---|---|---|
| `coverage_all`／`coverage_core`／`coverage_supporting` | 0.6119／0.8214／0.4615 | 同 | ✅ |
| `covered_total`／`covered_core`（41/67、23/28） | 41／23 | 同 | ✅ |
| `missing_core_ids` | F019、F044、F054、F056、F066 | 同 | ✅ |
| `by_category` number／date／decision／topic | 3/4、3/4、9/9、10/25 | 同 | ✅ |
| `record_char_count` | 2552 | 同 | ✅ |
| transcript 觀察列（66/67、core 28/28） | 0.9851／1.0 | 同 | ✅ |

### 2.3 record_quality（runner 投影 vs 腳本原始輸出）

兩者 schema 不同（`record_quality.json` 是 runner 投影；`--out` 是腳本原始輸出），逐鍵對映後**可比欄位全部相同**：`char_count=2552`、`body_source_tag_count=29`、`table=0`、`instruction_item_count=10`、`tagged_item_ratio=1.0`、`cross_section_duplicate_pairs=0`、`known_term_fix_hits(right)=1`、`tag_traceability`（29 tags／traceable 1.0／on_start 0.9310／excluding_zero 0.9130／distinct 19／0.6552）全鍵相同。`unsupported_entities_count=4`：重跑 raw 清單＝`["一股、二股","徵收股","煙酒文申股","稽查股"]`（4 筆），且 `sha256(json.dumps(list, ensure_ascii=False))` ＝ 證據檔 `unsupported_entities_sha256`（`ddedd816…91de`）→ **hash 可重現**。

獨立發現（原報告未見）：`run_summary.json`／`record_quality.json` 的 runner 投影**沒有 `fidelity` 區塊**（`rg fidelity scripts/e2e/run_owned_e2e.py`＝0 命中；腳本自 `da37407` 起就有此輸出）→ P4-B 絆索的觀測值**不進 stored 證據**，只能靠 log 或重跑腳本取得（見 §四-5）。

### 2.4 耗時分解（重建自 `app_2026-09-23.log`，交叉驗證）

| 階段 | 起訖（log 時戳） | 秒數 |
|---|---|---|
| ASR（Apple，子程序） | 05:00:51.270 → 05:01:07.644 | 16.4（音檔 2695.1 s） |
| diarization | ~05:01:07.7 → 05:03:39.670 | **152.0**（log 自報；682 段／8 位發言者） |
| 語意校正（LLM） | 05:03:39.8 → 05:09:38.427 | ~358.7 |
| 萃取筆記（extraction） | 05:09:38.436 → 05:15:50.619 | **372.2**（`pipeline metrics` 一致） |
| 首版紀錄生成 | 05:15:50.62 → 05:22:31.170 | ~400.6 |
| 補強第 1 輪 | 05:22:31.32 → 05:30:35.315 | ~484.0 |
| 補強第 2 輪 | 05:30:35.32 → 05:38:41.851 | ~486.5 |
| 收尾（驗證／log／DOCX／下載） | 05:38:41.9 → 05:38:44.664 | ~2.8 |

- `pipeline metrics`：`extraction=372.2`、`final_and_refine=1371.4`（＝400.6＋484.0＋486.5，吻合）、`total=1743.6`、`logical_generations=4`、`merge_rounds=0`。
- **補強輪數＝2**（log 出現「本地摘要品質補強（第 1 輪）」05:22:31、「（第 2 輪）」05:30:35）。
- `run_summary` 執行窗＝2278.766 s；`task_final`＝2270.759 s；backend log「任務 67fe4b0d 處理完成，耗時: 2270.8秒」→ 三者互相吻合（差距＝runner 起停／下載收尾）。
- 未解釋殘差 ≈5.6 s（階段間隙）；如實登錄，不美化。

## 三、plan §9 逐條判定

| 條件 | 判定 | 證據 |
|---|---|---|
| §9.3 量尺釘版（`coverage-1.0.0`＋`cf012d1f…`） | ✅ 已達成 | `coverage.json.checklist_sha256`＝釘版值；重跑同值 |
| §9.3 F1② 逐筆命中：`600／800／17／13,600` 0/4→4/4 | ✅ 已達成 | 紀錄原文：`600 元`、`800 元`、`共 17 個人`、`13600 元`（grep 皆 ≥1）；`coverage.json` F024/F025 `covered=true` |
| §9.3 F1② 日期類逐筆命中 | ✅ 已達成 | `10 月 14 日排程`、`提及 10 月底（年份待確認）`、`下週一` 皆在紀錄；F015/F021/F061 `covered=true` |
| §9.3 離線判缺表（5 數字＋1–2 日期、零誤判） | ✅ 已達成（我於現行 HEAD 離線重播驗證 4 份 baseline 全缺、E1 紀錄 0 誤判） | 我的重播：D1 缺 15/600/800/17/13600＋週一/10月底；D2 缺 6 數字＋10月底；B2、C1 各缺 5 數字＋10月底；**E1 紀錄缺 0／0**（與 `execution.md` §3 一致） |
| §9.3 議題／決議對帳實際召回 | ❌ 未達成（本場） | `cov_expected_topic=0`（log:1595「議題期望集合為空」WARNING）→ topic 類別整場 no-op；`cov_missing_decision=10`（11 項中 10 項判缺；人工 grep 至少 7 項其實已在紀錄、3 項為空殼條目） |
| §9.3 F1② 聚合觀察目標 `all ≥0.65`／`core ≥0.80` | ❌ `all` 未達（0.6119）；✅ `core` 達（0.8214） | `coverage.json`；單場不足以宣稱支持（見下） |
| §9.3 F1② 樣本數（≥2 次取中位數始可宣稱支持） | ❌ 未達（單場） | 本檔僅稽核單場；即使與 E2 併為 n=2，中位數仍 0.6119 < 0.65（E1／E2 同值） |
| §9.3 F1④ 隔離場（`LOCAL_FIDELITY_TRIPWIRES=false`） | ❌ 未達成 | 輪 1／輪 2 問題清單含 `fidelity_checks.py:461`（專名依據）、`:637`（來源標註歸屬）、`:829`（金額／數量）訊息；`grep -i fidelity` backend log 無開關字樣；`run_notes.md` §八-5 亦自承未開 → **P4-A＋P4-B 共同歸因** |
| §9.3 閘門不破（required 15 項／`--template`；`checks` 另含 1 非 required） | ✅ 已達成 | `run_summary.checks` 16 鍵全 `true`、`failure_reasons=[]`、`verdict=PASS`（與 C2 口徑一致） |
| §9.3 新增 ≥15 項單元測試 | ✅ 已達成 | `tests/test_t20260923_p4a_record_coverage.py` 23 項＋`…_false_positive_fix.py` 7 項；相關 7 檔 134 passed |
| §9.4 輪數 `>1＝未達` | ❌ 未達成 | **2 輪**（log 第 1／2 輪；`logical_generations=4`） |
| §9.4 wall 退步 `>+25%＝未達` | ❌ 未達成 | 2278.766 s vs D1 1227.2 s（`attempt-D1/attempt.json`）＝**+85.7%** |
| §9.4 雲端輸出 byte 不變（I-2） | `[UNVERIFIED]`（本場未跑雲端；observe 預設未動雲端路徑） | 僅單元測試層證據，非本場 E2E |
| §9.4 地端捏造 ≤1／不得報 registry 官名 | ⚠️ 部分達成 | 重跑 `fidelity`：`number_fabricated=0`、`entity_flags=1`（`煙酒文申股`，kind=`variant`）、`attribution_flags=1`（tag_owner，`（發言者2，00:11:13）`）；最終紀錄仍寫入該變體名稱 |
| §9.6 三模式語意（observe＝品質不影響 verdict） | ✅ 已達成（live 實證） | `quality.checks.quality_on_start_tag_ratio_ok=false`（0.9310<0.95）仍在 `check_failures`，但 `verdict=PASS` → observe 不改 verdict |
| §9.6 既有門檻不退步（traceable/body/table/excluding_zero） | ✅ 已達成 | traceable 1.0、body 29、table 0、excluding_zero 0.9130 |
| §9.6 既有門檻 `on_start≥0.95` | ❌ 未達（observe 模式不影響 verdict） | 0.9310；2 個 off-start 時戳 `00:04:35`／`00:42:15` 在逐字稿 grep＝0（模型自帶幻覺時戳，非 P4 造成；`required` 升級前必須處理） |
| §9.6 標註辨別力（B2 0.288→≥0.5；D1 ≥0.667 不退步） | ⚠️ 未達（同模型觀察） | 本場 `distinct_tag_time_ratio=0.6552`（19/29）**低於 D1 的 0.6667**（D1 `record_quality.json`）；單場、非同 build，僅登記為風險 |
| §9.6 runner 三模式 `off／required` | `[UNVERIFIED]`（本場只跑 observe） | 由單元測試覆蓋（`test_owned_e2e_acceptance.py` 等） |
| §9.3 F1③ 未達處理（如實記錄＋根因） | ✅ 已達成 | `run_notes.md` §八、commit `0054db4` 訊息均如實登錄未達項 |
| §9.11 如實邊界（單次抽樣、不得宣稱追上雲端） | ✅ 遵從 | 本場單次抽樣（temp 0.6/0.7）；無「追上雲端」宣稱 |

## 四、未達成與風險

1. **`[VERIFIED]` §9.4 輪數／牆鐘雙未達**：2 輪、+85.7%。成本拆解：多出的 ≈1028 s 幾乎全為 2 次額外 LLM 生成（≈971 s）；ASR＋diarization＋校正固定成本僅 ≈527 s。**plan 自身兩準則互相衝突**（同時要求「預期 1 輪」與「wall 退步 ≤+25%」，但本模型單輪生成 ≈485 s ＝ D1 牆鐘 +39.5%）→ 需 planner 決策（不得由驗收方放寬）。
2. **`[VERIFIED]` F1④ 未隔離**：本場 tripwires 為預設 `True`（`backend/core/config.py:304`），違反 §9.3 F1④ 的歸因隔離設計 → 數字／日期召回不得獨歸 P4-A。
3. **`[VERIFIED]` 決議類別假陽性＋不收斂**：最終 `cov_missing_decision=10`；其中 3 項為空殼條目（`[00:20:15]/[00:24:30]/[00:32:15] …裁示：`），其餘多項 grep 證明已在紀錄（如「嚴禁將科內公共訊息或照片轉傳至外部群組」出現 2 次）。第 2 輪問題集合與第 1 輪幾乎相同（11→10），顯示補強迴圈被假陽性驅動。此為 `0054db4`／`f374c27` 的後續修補對象。
4. **`[VERIFIED]` topic 類別本場 no-op**：`cov_expected_topic=0` 且 log WARNING 明確（`summarization.py:1595`）→ 67 條清單最大缺口類別（topic 25 條）本場完全未獲補強機會。
5. **`[VERIFIED]（獨立發現）` P4-B 觀測值不進 stored 證據**：runner 投影缺 `fidelity` 區塊（`rg fidelity scripts/e2e/run_owned_e2e.py`＝0）；`run_summary.json`／`record_quality.json` 因此無法自證 P4-B 絆索的 observe 數據（需 log 或重跑腳本）。
6. **`[VERIFIED]` `on_start_tag_ratio 0.9310`**：off-start 時戳 `00:04:35`／`00:42:15` 在逐字稿 0 命中（我 grep）；屬未來 `required` 升級阻礙。
7. **`[VERIFIED]` 輸入非 byte 相同**：本場逐字稿 `cc5b1d54…` 與 E2／D1／D2 的 `199d37b5…` 不同（`diff` 僅 2 行差異：`人事事報告`vs`人事室報告`；`審員圓`vs`瀋圓圓`）→ 跨場比較有小幅輸入差異，非完全同源。
8. **`[INFERRED]` 證據完整性小缺口**：本場無 `attempt.json`（D1 有），執行命令需由 `run_summary` 欄位重建；`sha256_manifest` 未收錄 MD hash（改由 `run_summary.quality.record_markdown.sha256` 錨定）。
9. **`[VERIFIED]（gate 語意澄清）`** 乾淨工作樹 preflight 於 attempt 目錄**空目錄**時執行（runner 先 `mkdir` 再檢查；空目錄對 git 不可見）→ 本場通過不衝突；gate 只能攔「閘門當下已存在的變更」。

## 五、驗收判決

**E1：`ACCEPTED_WITH_GAPS`**

理由：runner 閘門 16/16 PASS、主要歸因（數字／日期逐筆命中）與 `coverage_core ≥0.80` 達成、量尺與 hash 全部可重現；但 **§9.4 輪數／牆鐘雙未達**、F1④ 未隔離、`coverage_all 0.6119 < 0.65`、topic 類別 no-op、決議類別假陽性導致不收斂——全部如實列出，不得美化。

翻轉條件（如實聲明）：若 plan 擁有者將 §9.4 的「輪數 >1 或 wall >+25%＝未達」視為硬性驗收門檻，則本場應判 `REJECTED`／`PLANNER_REPLAN`。本稽核不代 planner 放寬門檻，也不代其宣告整體任務失敗。
