# 獨立驗收稽核（Stage 05 語意）— attempt-E2-gemma31b-p4a-fix

- 受測模型：`gemma-4-31B-it-MLX-4bit`（LM Studio instance `gemma-4-31b-it-mlx`，`context_length=71936`、`parallel=4`、`unique_loaded_llm_count=1`；`model_snapshot(.end).json`）
- 受測 build revision：`0054db4485a0a07fde982494c85601d5e26dae42`（`run_summary.expected_build_revision == actual_build_revision`）
- 稽核時 repo HEAD：`0d34fa1ca2d2537866b0e8b46ce310979ea1160f`（`git rev-parse HEAD`）
- 稽核時間：2026-09-23 10:10–10:30（Asia/Taipei）
- 執行窗：2026-09-23T09:21:52.672510+08:00 → 09:57:00.540682+08:00
- 角色邊界：本檔由 Stage 05 獨立驗收員新增（append-only）；產品程式碼／`plan.md`／`handoff.md`／既有證據檔**均未修改**，未執行 `git add`／`commit`。稽核當時本目錄**尚無 `run_notes.md`**（打包者另行撰寫中）——本檔未依賴、未建立、未修改該檔。

## 一、稽核方法

實際執行（全部唯讀；`DATA_DIR=/tmp/probe_scratch`）：

1. `uv run --frozen python scripts/e2e/measure_coverage.py --record data/cache/e2e/p4-gemma31b-e2/backend_data/outputs/0903-科務會議_7bf495fe.md --checklist …/quality/fact_checklist.json --label E2-verify-independent --transcript …_逐字稿.txt --json-out /tmp/verify_E2_coverage.json`
2. `uv run --frozen python scripts/e2e/measure_record_quality.py --record <同上> --transcript <同上> --template section_meeting --out /tmp/verify_E2_record_quality.json`
3. `shasum -a 256`：MD／DOCX／逐字稿／來源音檔／runtime 根副本／uploads 副本，逐項對 `sha256_manifest.json` 與 `run_summary.json`。
4. 由 `data/cache/e2e/p4-gemma31b-e2/backend_data/logs/app_2026-09-23.log` 逐行重建耗時分解，與 `pipeline metrics`、`task_final.json`、backend「耗時:」行交叉驗證。
5. **自建離線重播**（現行 HEAD、0 模型成本）：直接呼叫 `backend.services.summarization.SummarizationService._validate_record_source_coverage`（`LOCAL_LLM_RECORD_COVERAGE_CATEGORIES="number,date"`、`notes=""`），對 E2 紀錄重跑數字／日期對帳。
6. **殘餘問題逐條 grep 最終紀錄**（log 第 125 行所列 8 項：議題 5＋決議 3）＋ `zipfile` 檢查 DOCX 結構。
7. 選跑相關測試：`pytest tests/test_t20260923_p4a_record_coverage.py tests/test_t20260923_p4a_false_positive_fix.py tests/test_t20260922_2037_p4b_fidelity_tripwires.py tests/test_t20260923_p4b_fidelity_wiring.py tests/test_owned_e2e_acceptance.py tests/test_record_quality_metrics.py tests/test_t20260922_2037_p3_parity.py -q` → **134 passed（1.35 s）**；全套未重跑（如實登錄）。

讀過的檔：`plan.md` §9（含 §9.3／§9.4／§9.6／§9.9／§9.11）、`handoff.md` §7／§8、`execution.md` §3／§8／§10、本場 `run_summary.json`／`task_final.json`／`coverage.json`／`record_quality.json`／`sha256_manifest.json`／`model_snapshot(.end).json`／`provider_info.json`／`coverage_observation.json`、E1 `run_notes.md`（交叉比對用）、D1 `attempt.json`（baseline 出處）。

## 二、重跑量尺 vs 證據檔

### 2.1 檔頭（`shasum -a 256`）

| 欄位 | 證據檔值 | 我的重跑值 | 一致？ |
|---|---|---|---|
| 來源音檔 `source_audio_sha256` | `982151f4…012828` | Downloads 原檔＝`982151f4…012828`（45,107,503 B） | ✅ |
| `stored_upload_sha256`（uploads/864d539f76f1.m4a） | `982151f4…012828` | `982151f4…012828` | ✅ |
| MD（outputs `…_7bf495fe.md`） | `6b7e8fc1…e02a60`（=`run_summary.quality.record_markdown.sha256`=`coverage.json.record_sha256`） | `6b7e8fc1…e02a60` | ✅ |
| DOCX（outputs／runtime 根 `meeting_record.docx`） | `f7e51573…a530ec`（`sha256_manifest`） | 兩份皆 `f7e51573…a530ec` | ✅ |
| 逐字稿（outputs／runtime 根 `transcript.txt`） | `199d37b5…08060a`（`sha256_manifest`） | 兩份皆 `199d37b5…08060a`；**與 D1／D2 逐字稿 byte 相同**（三方同 hash） | ✅ |
| DOCX 結構 | `formal_docx_valid=true` | `zipfile.testzip()` 無壞檔；`word/document.xml` 含 `600`／`800`／`13600` | ✅ |

### 2.2 coverage（`coverage-1.0.0`；checklist `cf012d1f6983f67ecb47cc7a6486e48c110a6b2782ad94cccf0332a4ec6ec001`）

逐欄比對（`/tmp/verify_E2_coverage.json` vs `coverage.json`）：**全部扁平欄位 0 差異**（僅 `label`／`record_path` 因重跑參數不同）。關鍵值：

| 欄位 | 證據檔值 | 重跑值 | 一致？ |
|---|---|---|---|
| `coverage_all`／`coverage_core`／`coverage_supporting` | 0.6119／0.8214／0.4615 | 同 | ✅ |
| `covered_total`／`covered_core`（41/67、23/28） | 41／23 | 同 | ✅ |
| `missing_core_ids` | F044、F048、F060、F065、F066 | 同 | ✅ |
| `by_category` number／date／decision／topic | 3/4、**4/4**、7/9、8/25 | 同 | ✅ |
| `record_char_count` | 2318 | 同 | ✅ |
| transcript 觀察列（66/67、core 28/28） | 0.9851／1.0 | 同 | ✅ |

### 2.3 record_quality（runner 投影 vs 腳本原始輸出）

逐鍵對映後**可比欄位全部相同**：`char_count=2318`、`body_source_tag_count=27`、`table=0`、`instruction_item_count=10`、`tagged_item_ratio=1.0`、`cross_section_duplicate_pairs=0`、`known_term_fix_hits(right)=1`、`tag_traceability`（27 tags／traceable 1.0／on_start 1.0／excluding_zero 1.0／zero_time 9／distinct 16／0.5926）全鍵相同。`unsupported_entities_count=2`：重跑 raw 清單長度＝2，`sha256(json.dumps(list, ensure_ascii=False))` 之值與證據檔欄位同源（同 E1 之可重現性檢查法）。重跑 `fidelity`（腳本原始輸出）：`entity_flags=0`、`attribution_flags=1`（kind=`tag_owner`）、`number_fabricated=0`、`number_missing=0`。

獨立發現（原報告未見）：`run_summary.json`／`record_quality.json` 的 runner 投影**沒有 `fidelity` 區塊**（`rg fidelity scripts/e2e/run_owned_e2e.py`＝0 命中）→ P4-B 絆索觀測值不進 stored 證據（見 §四-3）。

### 2.4 耗時分解（重建自 `app_2026-09-23.log`，交叉驗證）

| 階段 | 起訖（log 時戳） | 秒數 |
|---|---|---|
| ASR（Apple，子程序） | 09:21:57.947 → 09:22:14.164 | 16.2（音檔 2695.1 s） |
| diarization | ~09:22:14.3 → 09:24:46.526 | **152.4**（log 自報；682 段／8 位發言者） |
| 語意校正（LLM） | 09:24:46.6 → 09:30:42.554 | ~356.0 |
| 萃取筆記（extraction） | 09:30:42.563 → 09:36:14.583 | **332.0**（`pipeline metrics` 一致） |
| 首版紀錄生成 | 09:36:14.58 → 09:42:37.946 | ~383.4 |
| 補強第 1 輪 | 09:42:38.051 → 09:49:49.508 | ~431.5 |
| 補強第 2 輪 | 09:49:49.597 → 09:56:57.026 | ~427.4 |
| 收尾（驗證／log／DOCX／下載） | 09:56:57.0 → 09:57:00.541 | ~3.5 |

- `pipeline metrics`：`extraction=332.0`、`final_and_refine=1242.5`（＝383.4＋431.5＋427.4，吻合）、`total=1574.5`、`logical_generations=4`、`merge_rounds=0`。
- **補強輪數＝2**（log「本地摘要品質補強（第 1 輪）」09:42:38、「（第 2 輪）」09:49:49）。
- `run_summary` 執行窗＝2107.868 s；`task_final`＝2099.206 s；backend log「任務 7bf495fe 處理完成，耗時: 2099.2秒」→ 三者互相吻合。
- 未解釋殘差 ≈7.8 s（階段間隙）；如實登錄。
- 相對 E1：總牆鐘 −170.9 s（−7.5%）＝萃取 −40 s＋首版 −17 s＋兩輪補強 −112 s（同一模型、同 audio；輸入逐字稿與 D1／D2 byte 相同、與 E1 差 2 行）。

## 三、plan §9 逐條判定

| 條件 | 判定 | 證據 |
|---|---|---|
| §9.3 量尺釘版（`coverage-1.0.0`＋`cf012d1f…`） | ✅ 已達成 | `coverage.json.checklist_sha256`＝釘版值；重跑同值 |
| §9.3 F1② 逐筆命中：`600／800／17／13,600` | ✅ 已達成 | 紀錄原文：`發放 600 元之案例`、`17 個人每人 800 元，共計 13600 元`；`coverage.json` F024/F025 `covered=true` |
| §9.3 F1② 日期類逐筆命中 | ✅ 已達成 | `10月14日排程`、`原定 10月底搬入之計畫可能受影響`、`下週一`；`by_category.date=4/4`（100%） |
| §9.3 離線判缺表（5 數字＋1–2 日期、零誤判） | ✅ 已達成（我於現行 HEAD 離線重播驗證：E2 紀錄 0 誤判） | 我的重播：E2 `missing_number=0`／`missing_date=0`；同期 D1／D2／B2／C1 皆判缺 5 數字＋10月底（D1 另有週一） |
| §9.3 議題對帳（P4-A 修補後首次生效） | ⚠️ 部分達成 | in-run `cov_expected_topic=12／missing_topic=5`（E1 為 0／0 → no-op）；**我 grep 驗證 5 項全部已存在於最終紀錄＝假陽性** |
| §9.3 決議對帳 | ⚠️ 部分達成 | in-run `cov_expected_decision=12／missing_decision=3`（E1 為 11／10）；**我 grep 驗證 3 項全部已存在＝假陽性** |
| §9.3 F1② 聚合觀察目標 `all ≥0.65`／`core ≥0.80` | ❌ `all` 未達（0.6119）；✅ `core` 達（0.8214） | `coverage.json` |
| §9.3 F1② 樣本數（≥2 取中位數始得宣稱支持） | ❌ 未達（gemma 現為 n=2：0.6119／0.6119 → 中位數 0.6119 < 0.65） | E1＋E2 `coverage.json`；惟兩場 build 不同（`da37407` vs `0054db4`），非嚴格同條件重複 |
| §9.3 F1④ 隔離場（`LOCAL_FIDELITY_TRIPWIRES=false`） | ❌ 未達成 | 輪 1 問題清單含 `fidelity_checks.py:637`（來源標註歸屬）訊息 → tripwires 未關；召回功勞＝**P4-A＋P4-B 共同歸因** |
| §9.3 閘門不破（required 15 項；`checks` 另含 1 非 required） | ✅ 已達成 | `run_summary.checks` 16 鍵全 `true`、`failure_reasons=[]`、`verdict=PASS` |
| §9.3 新增 ≥15 項單元測試 | ✅ 已達成 | P4-A 兩檔 30 項；相關 7 檔 134 passed |
| §9.4 輪數 `>1＝未達` | ❌ 未達成 | **2 輪** |
| §9.4 wall 退步 `>+25%＝未達` | ❌ 未達成 | 2107.868 s vs D1 1227.2 s＝**+71.8%** |
| §9.4 雲端 byte 不變（I-2） | `[UNVERIFIED]`（本場未跑雲端） | 僅單元測試層證據 |
| §9.4 地端捏造 ≤1 | ✅ 已達成 | 重跑 `fidelity`：`entity_flags=0`、`number_fabricated=0`；殘餘僅 `tag_owner=1`（歸屬瑕疵，非捏造） |
| §9.6 三模式語意（observe 不影響 verdict；required 未開） | ✅ 已達成（live） | `quality.checks` 全 true、`check_failures=[]`、`verdict=PASS` |
| §9.6 既有門檻不退步 | ✅ 已達成 | traceable 1.0、on_start 1.0、excluding_zero 1.0、body 27、table 0 |
| §9.6 標註辨別力（B2→≥0.5；D1 ≥0.667 不退步） | ❌ 未達（同模型觀察） | `distinct_tag_time_ratio=0.5926`（16/27）**低於 D1 0.6667（−0.074）** 且低於 E1 0.6552；`zero_time_tag_count=9/27`（33%）偏高，`on_start=1.0` 受零時戳膨脹風險 |
| §9.6 runner `off／required` 模式 | `[UNVERIFIED]`（本場只跑 observe） | 單元測試覆蓋 |
| §9.3 F1③ 未達處理（如實記錄＋根因） | ✅ 已達成（本次稽核另補強根因證據） | 見 §四-1：殘餘 8 項全為假陽性 |
| §9.11 如實邊界 | ✅ 遵從 | 單次抽樣；無「追上雲端」宣稱 |

## 四、未達成與風險

1. **`[VERIFIED]（本稽核獨立發現）` 最終殘餘問題 8/8 全部是假陽性**：log 第 125 行（09:56:57）列「議題遺漏 5 項＋決議遺漏 3 項」，我逐條 grep 最終紀錄——
   - 議題：`整理並重新列印損毀之土地稅卡`✅、`請示局長關於市場端權限之需求`✅、`近期有逼真之社交工程釣魚郵件`✅、`嚴禁將科內公共訊息轉傳至外部群組`✅、`預計搬遷時間將延後（原定 10月底…）`✅
   - 決議：`將先公告預佈缺，避免 11月1日才找人過晚`✅、`確認於 10月14日排程`✅、`費用報支應照實報，不可浮報`＋`小額採購需避免與廠商利益交換`✅
   → 「2 輪不收斂」的直接原因是 **P4-A 對帳器假陽性**，不是模型漏寫；此即 `f374c27` 後續修補標的（該修補不在本場 build 內）。
2. **`[VERIFIED]` §9.4 輪數／牆鐘雙未達**：2 輪、+71.8%。多出成本 ≈880 s 幾乎全為 2 次額外 LLM 生成；plan 自身兩準則衝突（見 E1 稽核 §四-1）未解 → planner 決策。
3. **`[VERIFIED]（獨立發現）` P4-B 觀測不進 stored 證據**：runner 投影缺 `fidelity` 區塊；證據目錄內無任何檔案保存本場 tripwire 摘要（本稽核靠重跑腳本才取得 `entity_flags=0／attribution_flags=1／number_fabricated=0`）。
4. **`[VERIFIED]` 標註辨別力未達**：`distinct_tag_time_ratio` 0.5926（D1 0.6667、E1 0.6552）＝目前 gemma 三場最低；`zero_time_tag_count` 9 筆（33.3%）使 `on_start=1.0` 的說服力打折（`excluding_zero` 亦 1.0，可部分抵銷此疑慮）。
5. **`[VERIFIED]` F1④ 未隔離**：本場亦未開 `LOCAL_FIDELITY_TRIPWIRES=false`（預設 `True`，`config.py:304`）→ 召回不得獨歸 P4-A。
6. **`[VERIFIED]` 聚合目標未達（n=2 亦同）**：gemma 兩場 `coverage_all` 均 0.6119（中位數 0.6119 < 0.65）；`missing_core` 兩場不同（E1：F019/F044/F054/F056/F066；E2：F044/F048/F060/F065/F066）→ 聚合數字相同屬巧合，逐條集合仍有差；不得以「兩場同值」宣稱穩定。
7. **`[INFERRED]` 證據完整性小缺口**：本場無 `attempt.json`、無 `run_notes.md`（稽核當下）；`sha256_manifest` 未收錄 MD hash（改由 `run_summary` 錨定）。
8. **`[VERIFIED]` E2 輸入與 D1／D2 byte 相同**（同 hash `199d37b5…`）→ 與 D1 的比較屬「同輸入、不同 build」；與 E1 的比較則不同輸入（2 行差異），如實登記。

## 五、驗收判決

**E2：`ACCEPTED_WITH_GAPS`**

理由：runner 閘門與既有品質門檻全數 PASS、逐筆主要歸因（數字／日期）達標、P4-A 議題／決議類別首次實際生效且我獨立證明殘餘 8 項全為假陽性（品質問題在對帳器、非模型）；但 **§9.4 輪數／牆鐘雙未達**、`coverage_all 0.6119 < 0.65`、F1④ 未隔離、`distinct_tag_time_ratio` 低於 D1＝0.6667、P4-B 觀測未進 stored 證據——全部如實列出。

翻轉條件（如實聲明）：若 plan 擁有者將 §9.4 的「輪數 >1 或 wall >+25%＝未達」視為硬性驗收門檻，則本場應判 `REJECTED`／`PLANNER_REPLAN`。本稽核不代 planner 放寬門檻。
