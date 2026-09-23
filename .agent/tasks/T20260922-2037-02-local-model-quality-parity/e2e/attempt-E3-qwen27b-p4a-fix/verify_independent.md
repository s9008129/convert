# attempt-E3-qwen27b-p4a-fix 獨立驗收稽核（Stage 05）

- 稽核者角色：Stage 05 獨立驗收員（唯讀產品碼／`plan.md`／`handoff.md`／既有 evidence；唯一寫入＝本檔）。
- 受測場次：`Qwen3.8-27B-Splash`（LM Studio，`processing_mode=local`、模板 `section_meeting`、真實音檔 `0903-科務會議.m4a` 2695.1 s）。
- 受測 build：`run_summary.expected/actual_build_revision = 0d34fa1ca2d2537866b0e8b46ce310979ea1160f`（相等；`[VERIFIED]`）。
- 稽核時間：2026-09-23（台北）。稽核期間 `git status --porcelain` 為空（未動任何既有檔）。

## 一、稽核方法

### 1.1 讀取（唯讀）

| 類別 | 檔案 |
|---|---|
| 規劃／交接 | `plan.md` §9.2／§9.3／§9.4／§9.6／§9.10／§9.11；`handoff.md` §7／§8／§9／§10／§11 |
| 受測場證據 | 同目錄 `run_summary.json`、`task_final.json`、`coverage.json`、`coverage_observation.json`、`record_quality.json`、`sha256_manifest.json`、`model_snapshot.json`、`model_snapshot_end.json`、`provider_info.json`、`upload_response.json`、`health_snapshot.json`、`run_notes.md`（引用但不採信） |
| runtime（gitignored） | `data/cache/e2e/p4-qwen27b-e3/backend_data/logs/app_2026-09-23.log`（151 行）、`outputs/0903-科務會議_d48ce298.{md,docx}`、`outputs/0903-科務會議_d48ce298_逐字稿.txt`、`uploads/92431496b03e.m4a` |
| 釘版量尺素材 | `quality/fact_checklist.json`（sha256 `cf012d1f…ec001`）、`backend/services/summarization.py`、`backend/core/fidelity_checks.py`、`backend/core/text_postprocess.py`、`backend/core/config.py`、`scripts/e2e/run_owned_e2e.py` |

### 1.2 實際執行（全部在本機實跑，非引用他人報告）

1. 重跑量尺（`DATA_DIR=/tmp/probe_scratch uv run --frozen python …`，輸出 `/tmp/e3_verify_coverage.json`、`/tmp/e3_verify_rq.json`）：
   - `scripts/e2e/measure_coverage.py --record <md> --checklist quality/fact_checklist.json --label E3-qwen27b-p4a-fix --transcript <逐字稿> --json-out /tmp/e3_verify_coverage.json`
   - `scripts/e2e/measure_record_quality.py --record <md> --transcript <逐字稿> --template section_meeting --out /tmp/e3_verify_rq.json`
2. 逐欄比對：對 `coverage.json` 做全檔 leaf-key 比對（688 鍵）＋ byte 比對（`cmp`／`shasum -a 256`）；對 `record_quality.json`／`run_summary.quality.metrics` 做重疊鍵比對。
3. `shasum -a 256`：來源音檔、stored upload、md、docx、逐字稿 ↔ `sha256_manifest.json` ↔ `run_summary.quality.record_markdown.sha256`。
4. DOCX 結構：`unzip -l` ＋ 解析 `word/document.xml` 文字（獨立於 runner 的 `formal_docx_valid`）。
5. 耗時重建：以 log 逐階段時間戳重算；與 `run_summary`（runner 窗）、`task_final.json`（started/completed）、log「耗時」三方交叉。
6. 對帳器離線重播（0 模型成本，現行 HEAD；已驗證相關函式與受測 build `0d34fa1` **byte 相同**）：`SummarizationService._scan_transcript_number_items`／`_date_canonical_is_covered`／`_fold_record_for_number_matching`；`fidelity_checks.analyze_fidelity`（P4-B）。
7. 測試（獨立實跑）：聚焦 `pytest tests/test_t20260923_p4a_record_coverage.py tests/test_t20260922_2037_p4b_fidelity_tripwires.py tests/test_owned_e2e_acceptance.py tests/test_record_quality_metrics.py -q` → **97 passed**；全套 `pytest tests/ -q --ignore=tests/test_end_to_end.py` → **1047 passed, 2 skipped**。
8. `grep`／`awk` 逐詞核對最終紀錄（md 與 docx 雙軌）15 筆未涵蓋事實。

## 二、重跑量尺 vs 證據檔

| 欄位／群組 | 證據檔值 | 我的重跑值 | 一致？ |
|---|---|---|---|
| `coverage.json` 全檔（688 個 leaf 欄位） | sha256 `83b0adae33782f2f…` | sha256 `83b0adae33782f2f…`（`cmp` BYTE-IDENTICAL） | **是** `[VERIFIED]` |
| `metric_version`／`checklist_sha256` | `coverage-1.0.0`／`cf012d1f…ec001` | 同 | 是 |
| `coverage_all`／`coverage_core`／`coverage_supporting` | 0.7761（52/67）／0.8571（24/28）／0.7179（28/39） | 同 | 是 |
| `missing_core_ids` | `[F021,F054,F055,F056]` | 同 | 是 |
| `by_category` | decision 9/9、name 3/3、number 4/4（1.0）、constraint 12/13、action_item 6/9、topic 16/25（0.64）、date 2/4（0.5） | 同 | 是 |
| `record_char_count` | 3396 | 同 | 是 |
| runner `coverage_observation.json`（投影） | `all 0.7761`／`core 0.8571`／`covered_core 24`／`missing_core [F021,F054,F055,F056]`／`checklist_sha256 cf012d1f…` | 與 `coverage.json` 全等 | 是（`by_category`／`covered_total`／`char_count` 未投影＝缺鍵，非差異） |
| `record_quality.json.metrics` ↔ `run_summary.quality.metrics` | — | Python 深度相等（含 `checks`） | 是 |
| `record_quality` 重跑 vs 落檔 | 重疊 9 鍵 | 8 鍵相等；`known_term_fix_hits` 落檔為投影 `{left_hits:0,right_hits:4}`，重跑另有 `by_form`／`transcript` 子物件 | 是（差異僅投影裁切） |
| `known_term_fix_hits` 內容 | `right_hits=4` | `right_by_form{徵收股:1, 瑞里:3}`＝4；`transcript.left_hits=3`（增收股1／征收股1／瑞裏1） | 是（與 `run_notes` §四一致） |
| `tag_traceability` | `traceable 1.0`／`on_start 1.0`／`excluding_zero 1.0`／`exact 0.7333`／`zero_time 8`／`distinct 0.6667 (30/45)`／`body tags 45`／`table tags 0`／`cross_dup 0`／`instructions 24` | 同 | 是 |
| `unsupported_entities_count`（觀察） | 4 | 4（`徵收股、煙酒文神股、煙酒管理股、稽查股`；registry-aware 版＝`[]`） | 是 |

### 2.1 SHA 核對（`shasum -a 256` 實跑）

| 對象 | 實測值 | 對照來源 | 一致 |
|---|---|---|---|
| `Downloads/0903-科務會議.m4a` | `982151f4…012828` | `manifest.source_audio_sha256` | 是 |
| `uploads/92431496b03e.m4a`（stored） | `982151f4…012828` | `manifest.stored_upload_sha256` | 是 |
| `0903-科務會議_d48ce298.md` | `740b0429…d1b520` | `run_summary.quality.record_markdown.sha256` | 是 |
| `0903-科務會議_d48ce298.docx` | `ad396dd9…f7a3dfd` | `manifest.meeting_record_docx_sha256` | 是 |
| `0903-科務會議_d48ce298_逐字稿.txt` | `b3cb89a6…7e9b90e7` | `manifest.transcript_sha256` | 是 |
| 跨場逐字稿（輔助） | E3 `b3cb89a6…`；E2／D1／D2 `199d37b5…`；E1 `cc5b1d54…` | `run_notes` §九-6 之「跨場非同輸入」 | 是（主張成立） |

DOCX 獨立結構檢查 `[VERIFIED]`：zip 內 17 檔、`word/document.xml` 可取文字 3141 字；含「科務會議紀錄」×2、「廉政宣導」×1、「13,600」×1、「搬遷時間可能延遲」×1；**「600塊」×0**。

### 2.2 閘門與耗時（log 逐階段重算）

| 階段 | 起→訖（log） | 秒 | 對照 |
|---|---|---|---|
| ASR（apple，fail-closed） | 10:14:05.180→10:14:21.424 | 16.24（引擎自報 `elapsed_seconds=15.62`） | log:36 |
| diarization | →10:16:56.551 | 155.13（自報 155.1） | log:37 |
| 發言者標註 | →10:16:56.681 | 0.13 | log:38 |
| 語意校正（12 次 LM Studio 呼叫） | →10:18:56.802 | 120.12 | log:43–90 |
| 萃取生成 | 10:18:56.812→10:23:10.218 | 253.41 | log:95–97（metrics `extraction 253.4`） |
| 首版最終生成 | 10:23:10.227→10:27:36.915 | 266.69 | log:99–101 |
| 補強第 1 輪 | 10:27:37.028→10:32:31.937 | 294.91 | log:107–110 |
| 補強第 2 輪 | 10:32:32.036→10:37:09.908 | 277.87 | log:113–116 |
| 收尾＋DOCX | →10:37:15.089 | 5.18（任務完成後 5.06 s） | log:142–143 |

- `[VERIFIED]` 三方一致：runner 窗 `10:13:59.923→10:37:16.040 = 1396.117 s`；任務窗 `10:14:05.159→10:37:10.027 = 1384.868 s`；log「耗時: 1384.9秒」（log:142）。
- `[VERIFIED]` 固定成本（ASR＋diar＋校正）＝290.9 s；模型生成＝253.41＋266.69＋294.91＋277.87＝1092.9 s ≈ metrics `total 1093.2`（`final_and_refine 839.8` vs 我算 839.5，差 0.3 s 屬量測邊界）；補強 572.8 s＝牆鐘 41.0%。
- `[VERIFIED]` `pipeline_metrics`：`logical_generations=4`、`semantic_attempts=0`、`network_retries=0`、`merge_rounds=0`（log:120）。
- `[VERIFIED]` 時間面：1396.117／1227.2（D1 baseline `attempt.json`）＝**+13.77% ≤ +25% → 達標**（若用任務端到端：1384.868／1218.6＝+13.64%，同結論）。
- `[VERIFIED]` 閘門：`verdict=PASS`、16 鍵 checks 全 true（＝15 required＋非 required 的 `model_snapshot_captured`）、`failure_reasons=[]`；`quality.checks` 5/5 true；`--quality-mode observe` 下品質值未改變 verdict（`gate_effect=none`）。

### 2.3 in-run 對帳（log `cov_*`）與 run_notes 對照

| 指標 | log（log:120） | run_notes §四 | 一致 |
|---|---|---|---|
| `cov_expected_topic` / `cov_missing_topic` | 13 / 1 | 13 / 1 | 是 |
| `cov_expected_decision` / `cov_missing_decision` | 0 / 0（3 次 WARNING「決議期望集合為空」log:106/112/118） | 0 / 0（§九-4） | 是 |
| `cov_expected_number` / `cov_missing_number` | 9 / 0 | 9 / 0 | 是（但見 §五-2：此 0 不成立） |
| `cov_expected_date` / `cov_missing_date` | 4 / 0 | 4 / 0 | 是 |
| `cov_issues_added` | 1 | 1 | 是 |

## 三、§五 逐筆性質判定對照（15 筆未涵蓋事實）

判定準則：內容確實不在最終紀錄＝**真缺**；內容在但關鍵詞被改寫／漏一字＝**部分命中**；內容完整而 probes 用字未列＝**量尺字面假陰性**。證據皆為我自行 `grep` 最終 md（並以 docx 複核）。

| fact | run_notes 判定 | 我的判定 | 一致？ | 依據（行號／命中） |
|---|---|---|---|---|
| F008 先開預估缺、最近公告 | 真缺（`預估缺` 0） | **量尺字面假陰性**（內容已寫、用字變體） | ✗ | md:52「先開**預備缺**公告，避免11月1日生效時來不及找人」；md:14 同；probes 只列 `預估缺`／`預佈缺`，未列 `預備缺` |
| F016 瑞里較遠、早點出發、開車小心 | 疑似假陰性 | **部分命中**（「早點出發」有；「開車小心」走樣） | ~ | md:54「需早點出發，**注意開路**」；逐字稿 L22「小心開到三路…早點上去」→ 語意有、措辭走樣 |
| F017 公文會辦、各村里名單 | 真缺 | 真缺 | ✓ | `會辦`／`名單`／`村里` 全 0 命中（md＋docx） |
| F021 下週一內稽、下午受檢 | 真缺（`內稽` 0） | **部分命中**（內容在、術語走樣 `內稽→內機`） | ✗ | md:38「下週一（日期未明）下午進行**內機**檢查」、md:17/57 同 |
| F030 文康活動上班時間／中午／請假 | 真缺 | 真缺 | ✓ | `上班時間`／`請假`／`中午` 全 0 |
| F032 慶生聚會形式 | 真缺 | 真缺 | ✓ | `慶生` 0 |
| F047 五個測試題目（AI 生成） | 真缺 | 真缺 | ✓ | `測試`／`題目` 0 |
| F051 Kiosk／城鄉差異／跨縣市 | 真缺 | 真缺 | ✓ | `Kiosk`／`縣市`／`城鄉` 0 |
| F054 搬遷時程可能拖很久 | 疑似假陰性 | **量尺字面假陰性**（內容完整） | ✓ | md:48「搬遷時間可能**延遲**」；docx 同樣命中；probes 只列 `拖延／延後／拖很久` |
| F055 三樓淹水溢流到禮堂、走廊 | 真缺 | 真缺 | ✓ | `禮堂`／`走廊`／`三樓` 0（md:48 僅「排水管倒灌、破損」） |
| F056 防水工程刨除舊防水層 | 真缺 | 真缺 | ✓ | `防水`／`刨除` 0 |
| F057 外牆挖四個孔、封管線 | 真缺 | 真缺 | ✓ | `挖`／`孔` 0 |
| F058 國稅局天花板／高架地板 | 真缺 | 真缺 | ✓ | `國稅局`／`高架` 0 |
| F059 整棟大樓霉味、三樓最明顯 | 部分命中 | 部分命中 | ✓ | `黴味`×2（md:48）、`三樓` 0 |
| F062 找出發霉處、約廠商來看 | 部分命中 | **真缺**（關鍵詞偶然命中、語境不同） | ✗ | `廠商`×2 皆在採購／廉政語境（md:40、md:65）；`發霉`／`鋁箔` 0（主題「黴味」另於 md:77「除黴」帶到） |

- 彙總：我＝真缺 10（F017、F030、F032、F047、F051、F055、F056、F057、F058、F062）／部分命中 3（F016、F021、F059）／量尺字面假陰性 2（F008、F054）。
- `[VERIFIED]` run_notes §五三分類的**數量**（10／3／2）相同，但**組成不同**：F008 與 F021 被列為真缺（實為用字變體／術語走樣），F062 被列為部分命中（實為關鍵詞跨語境偶然命中）。結論方向「本場漏寫以真缺為主」仍成立。
- 與 Gemma E2 場相反之陳述 `[VERIFIED]`：E2 的殘餘問題經稽核全為假陽性；本場殘餘同時含**真缺**（見 §五-2）。

## 四、plan §9 逐條判定

### 4.1 P4-A（§9.3；CORE）

| 準則 | 判定 | 證據 |
|---|---|---|
| 釘版量尺（`coverage-1.0.0`＋`cf012d1f…`） | **已達成** | `coverage.json.checklist_sha256=cf012d1f…`、`metric_version=coverage-1.0.0`；P4-G 未回溯套用 |
| 逐條事實閘門（`600／800／17／13,600` 逐筆命中；以 `facts[].covered` 判讀） | **未達成（部分）** | `800`（md:39）、`17`（md:39）、`13600`（md:39）真命中；**`600` 僅由「13,600」子字串造成 `F024 covered=true`**，獨立 grep 紀錄＋docx 為 0 命中（§五-2／§五-3） |
| 日期類逐筆命中 | **未達成（2/4）** | covered：F015（10/14）、F061（10月底）；未 covered：F021、F054（兩者內容其實都在，見 §三） |
| 聚合門檻 `all ≥0.65`、`core ≥0.80`（觀察值，須 ≥2 次取中位數才可宣稱） | **觀察值達標，不得宣稱** | 0.7761／0.8571；本場 n=1（`run_notes` §九-5 已如實登錄） |
| 未達不得放寬量尺／擴類／改 denominator | **已達成** | runner 門檻未動（`ge 17`／`ge 0.95`／`ge 0.9`／`eq 0`，`run_owned_e2e.py:181-188`）；`da37407` 僅接線，`a412884` 僅 tz |
| 共同歸因隔離 F1④（`LOCAL_FIDELITY_TRIPWIRES=false`） | **未達成** | 本場三開關全預設開（`config.py:288/304/309`：`enforce`／`True`／`True`）；`run_notes` §九-3 已如實登錄共同歸因 |
| 閘門不破（required 14／`--template` 15） | **已達成** | `run_owned_e2e.py:2062-2080`（4＋10＋1＝15）；本場 16 鍵全 true |
| 新增 ≥15 項單元測試 | **已達成** | `tests/test_t20260923_p4a_record_coverage.py` 23 個 test 函式；聚焦 97 passed／全套 1047 passed, 2 skipped |
| 副作用 +350–400 s／輪（預估） | **資訊性**：實測 294.9／277.9 s／輪 | 低於預估 |

### 4.2 P4-B（§9.4；CORE）

| 準則 | 判定 | 證據 |
|---|---|---|
| 捏造 ≤1（校準實績 0） | **已達成** | 我重跑 `analyze_fidelity`：`fabricated_entities=[]`、`fabricated_entity_kinds=[]`、`failed_checks=[]`、`attribution_kinds=['tag_owner']` |
| 數字漏寫命中（**F024／F025 由 missing→covered**） | **僅形式達成（F025 真、F024 假）** | F025 真（800/17/13,600 在 md:39）；F024 由 probes `["600","便當"]` 在 `13,600` 內命中 → 內容實缺 |
| registry-aware：不得報出官方名 | **已達成** | `registry_aware_unsupported_entities=[]`（raw 4 → 0） |
| 關閉開關＝byte 不變 | **已達成（測試層）** | P4-B 測試 27 項含開關 golden，全數通過（`[VERIFIED]` 實跑） |
| 雲端 `observe` 預設、`enforce` 不得開 | **本場未涉**（地端場） | `[UNVERIFIED]`（未於本場驗證雲端路徑） |
| **輪數 >1（需第 2 輪）＝未達** | **未達成** | 2 輪（log:107／113），且第 2 輪後仍有殘餘（log:119） |
| wall 退步 >25%＝未達 | **已達成** | +13.77%（§2.2） |
| E2E `required` 閘門全通過、不退步 | **已達成** | verdict PASS、15 required 全 true |

### 4.3 P4-D（§9.6；CORE，本場為 observe 用）

| 準則 | 判定 | 證據 |
|---|---|---|
| `observe`＝quality 有值、verdict 不因品質值改變 | **已達成** | `quality.gate_effect=none`；`quality.checks` 5/5 |
| B2 `distinct_tag_time_ratio` ≥0.5、D1 ≥0.667 不退步 | **已達成（本場資訊）** | 本場 30/45＝0.6667＝D1 水準、遠高於 B2 0.288 |
| 「3 場 observe 穩定後才談升級」＋比值 max−min ≤0.02 | **未達成** | E1 0.6552／E2 0.5926／E3 0.6667 → 極差 **0.0741 > 0.02**；不得升級 |
| 防 false PASS（required 不含品質儀器時仍可辨識） | **已達成** | 15 required 全 true 且 `failure_reasons=[]`；品質值僅觀察 |

### 4.4 SUPPORTING／不在本場範圍

- P4-C（§9.5 取樣同源 A/B）、P4-E（§9.7 詞彙表）／P4-G（§9.8 量尺修訂）：本場未設驗收點 → **不判定**。
- §9.11 如實邊界：單次抽樣（本場 n=1）、C5 無 verdict、Windows／Ollama `[UNVERIFIED]`、67 條清單為相對工具 → 本場全部維持，未見超譯。

## 五、未達成與風險（含本次獨立發現）

1. **〔新〕P4-B B1 歸屬絆索 14/14 全為邊界假陽性** `[VERIFIED]`：我重跑 `analyze_fidelity` 得 14 筆 `tag_owner` 違規，**逐筆**比對逐字稿段落後發現，每一筆的標註時間戳都同時是「前一位發言者段落結尾」與「標註所指發言者段落起點」（例：00:06:14＝`(357,374,發言者3)` 尾＋`(374,408,發言者1)` 頭；00:07:08；00:07:11…共 14/14）。`_tag_owner_issues` 以 `start <= t <= end` 由檔序取首命中（`fidelity_checks.py:502-533`），因此永遠判給前一段＝**誤報**。本場 3 筆（`ATTRIBUTION_MAX=3`）被送入第 1／2 輪補強提示詞（log:107／113）且**不可被模型修正**，是「跑滿第 2 輪、最終仍待補強」的直接共因之一。HEAD `d00d778` 尚未修此缺陷（`[VERIFIED]` 現行碼仍為首命中即 break）。
2. **〔新〕P4-A 數字對帳器「子字串假命中」掩蓋 2 個真缺口** `[VERIFIED]`：離線重播（與受測 build `0d34fa1` 相關函式 byte 相同）顯示期望 9 個數字中，**`600` 命中來源是紀錄「13,600」**、**`15` 命中來源是紀錄自身的清單編號「15.」**（`summarization.py` 數字覆蓋＝`folded_literal in folded_record`）。故 `cov_missing_number=0`（log:120）**不成立**：逐字稿真有「發 600塊」（逐字稿 L25）與「少了 15%」（逐字稿 L12），最終 md／docx 皆 0 命中。這也解釋了為何 P4-B 絆索同時報 `number_missing_tokens=['600塊','15%']`（同輪問題字串，log:107／113）。期望集合另含日期片段 `11`（來自 40%／25% 同句外溢），顯示錨定精確度不足。
3. **〔新〕釘版清單量尺有同一 artifact → `number 4/4` 被高估** `[VERIFIED]`：`F024` 的 `matched_group_index=0`＝`["600","便當"]`，`matched_positions=[1047,1022]`；我把正規化後紀錄定位到索引 1047 得「…總計13600元發言者100…」＝**`600` 落在 `13,600` 內**。因此：`coverage_all 0.7761` 與 `number 1.0` 屬上界；校正後 `all＝51/67≈0.7612`（`[INFERRED]` 算術外推），仍 ≥0.65，但 §9.4 CORE「F024 由 missing→covered」**僅形式達成**；`run_notes` §六「number 4/4 優於雲端」不應採信（真實 3/4）。
4. `[VERIFIED]` **`run_notes` 低估殘餘問題**：log:119 第 2 輪後「本地摘要仍有待補強問題」共 **5 筆**（議題 1＋歸屬 3＋金額／數量 1）；`run_notes` §五頭行寫「in-run 唯一殘留問題＝假陽性」、§九-1 寫「仍有 1 筆未解」。方向（假陽性為主因）可接受，但**數量與組成**與 log 不符，且遺漏「真缺的 600塊／15% 未被修復」這一事實。
5. `[VERIFIED]` **P4-B 觀測值未進 stored evidence**：`rg -c fidelity scripts/e2e/run_owned_e2e.py`＝0；`run_summary.quality`／`record_quality.json` 無 `fidelity` 區塊（原始儀器輸出有）。→ 「F024 真缺」這件事在 tracked 證據裡**無痕**，只能靠 gitignored log＋本次重跑；跨機（Windows）對帳會失去這條線。
6. `[VERIFIED]` **P4-D 升級門檻未滿足**：三場 observe 比值 0.6552／0.5926／0.6667，極差 0.0741 > 0.02 → 不得升級 `required`（與 §9.6 一致）。
7. `[VERIFIED]`（正面）**決議類 no-op 已如實登錄**：`cov_expected_decision=0`＋3 次 WARNING（log:106/112/118），`run_notes` §九-4 寫明「決議類補強保障在本場等於沒作用」，未美化為 P4-A 的功勞。
8. `[VERIFIED]`（正面）**可重現性與證據鏈**：`coverage.json` 與我重跑 byte 相同；`record_quality` 重跑除投影裁切外全等；5 支 hash 全對；DOCX 結構完好；`formal_docx_valid=true` 由我獨立複核。
9. **單場 n=1 與跨場非同輸入** `[VERIFIED]`：本場逐字稿 `b3cb89a6…` 與 E1／E2／D1／D2 皆不同 → 跨場只能「同尺」不能「同輸入」；`run_notes` §九-5／§九-6 已正確登錄，**未宣稱聚合支持**（符合 F1②）。
10. **風險（需 planner 決策，稽核員無權放寬）**：①`600` 若依 §9.3 F1② 字面解讀即為 CORE 未達 → 是否可接受、或以修正後的量尺語意重新界定，須 planner 決策；②輪數上限（>1＝未達）在本場未達，且其共因是**絆索假陽性**（非模型品質）→ 修 B1 邊界誤報後是否重跑，須 planner 決策；③F1④ 未隔離（P4-A／P4-B 共同歸因）本場仍未補。

## 六、驗收判決

**判決：`ACCEPTED_WITH_GAPS`** — `[VERIFIED]` 閘門 16/16 全綠、量尺可重現（byte 相同）、時間面達標（+13.77% ≤ +25%）、聚合觀察值達標（all 0.7761 ≥0.65、core 0.8571 ≥0.80），但 **2 項 CORE 未達成且不得美化**：①§9.3 逐條事實閘門的 `600` 未真命中（量尺子字串假陽性所致，`F024` 實缺）；②§9.4 輪數 >1（2 輪未收斂，共因含 P4-B B1 的 14/14 邊界假陽性）。另 §9.3 F1④ 隔離場未開、§9.4 `F024 missing→covered` 僅形式達成、P4-D 三場穩定準則未達；聚合門檻為 **n=1 觀察值**，依 F1②不得宣稱支持。以上 CORE 短差屬門檻語意範疇，依 handoff §8 應交 planner 決策，稽核員不放寬、不代為重跑。
