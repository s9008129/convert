# attempt-E4-qwen27b-p4-final 獨立驗收稽核（Stage 05）

- 稽核者角色：Stage 05 獨立驗收員（唯讀產品碼／`plan.md`／`handoff.md`／既有 evidence；**唯一寫入＝本檔**）。
- 受測場次：`Qwen3.8-27B-Splash`（LM Studio，`processing_mode=local`、模板 `section_meeting`、真實音檔 `0903-科務會議.m4a` 2695.1 s；task_id `a5abfc7c`）。
- 受測 build：`818b71e6cc96934e922361d54b362b76ce1e0a2e`（`run_summary.expected==actual`；backend log「Build revision」同值；`[VERIFIED]`）。
- 稽核時間：2026-09-23（台北）。**未修改任何既有檔、未 `git add`／`commit`、未呼叫任何模型（0 模型成本）**；暫存一律 `/tmp`。
- 判決：**`ACCEPTED_WITH_GAPS`**（§八）。CORE-1／CORE-3 完全達成；CORE-2 (a)(c)(d) 達成、(b) 字面達成但**證據力受限**（見 §四-2）；另有 2 項 `run_notes.md` 內部錯誤與 3 項殘餘風險必須點名。

## 一、稽核方法

### 1.1 讀取（唯讀）

| 類別 | 檔案 |
|---|---|
| 受測場證據 | 同目錄 `run_summary.json`、`task_final.json`、`coverage.json`、`coverage_observation.json`、`record_quality.json`、`sha256_manifest.json`、`model_snapshot(.end).json`、`provider_info.json`、`upload_response.json`、`health_snapshot.json`、`run_notes.md`（引用但逐項稽核） |
| runner 交棒日誌 | `/tmp/e4_runner.log`（561 B，5 行） |
| runtime（gitignored，只讀） | `data/cache/e2e/p4-qwen27b-e4/backend_data/logs/app_2026-09-23.log`（146 行）、`outputs/0903-科務會議_a5abfc7c.{md,docx}`、`outputs/0903-科務會議_a5abfc7c_逐字稿.txt` |
| 對照場 | `e2e/attempt-E3-qwen27b-p4a-fix/{coverage.json,record_quality.json,verify_independent.md}`、`e2e/attempt-E2-gemma31b-p4a-fix/coverage.json`、`e2e/attempt-E1-gemma31b-p4/coverage.json`、`e2e/attempt-C5-cloud-baseline/coverage.json`、`e2e/timing-forensics-02/report.md`、`e2e/quality-parity-01/report.md`、`e2e/pre-push-review-01/report.md` |
| 釘版量尺素材 | `quality/fact_checklist.json`（sha256 `cf012d1f…ec001`）、`scripts/e2e/measure_coverage.py`、`scripts/e2e/measure_record_quality.py`、`scripts/e2e/run_owned_e2e.py`（門檻常數區）、`backend/services/summarization.py`、`backend/core/fidelity_checks.py` |

### 1.2 實際執行（全部我在本機實跑）

1. **重跑量尺**（`DATA_DIR=/tmp/probe_scratch uv run --frozen python …`）：
   - `measure_coverage.py --record <md> --checklist quality/fact_checklist.json --label runner-coverage-a5abfc7c --transcript <逐字稿> --json-out /tmp/verify_cov_byte.json`
   - `measure_record_quality.py --record <md> --transcript <逐字稿> --template section_meeting --out /tmp/verify_rq.json`
   - 另對 E2／E3 素材各重跑一次 `measure_record_quality.py`（對照 `number_missing` 宣稱）。
2. **逐欄比對**：`coverage.json` 全檔（除 `label`）→ `cmp` byte 相同；`record_quality.json` 的 `metrics` 與我重跑的 raw 輸出 11 個鍵全等。
3. `shasum -a 256`：來源音檔、md、docx、逐字稿 ↔ `sha256_manifest.json` ↔ `run_summary.quality.record_markdown.sha256`。
4. **DOCX 獨立結構檢查**：`unzip -t`（零錯誤）＋ `file`（Microsoft OOXML）＋ 解析 `word/document.xml` 取文字 2,455 字。
5. **時間重建**：以 log 逐階段時間戳重算，與 `run_summary`／`task_final.json`／log「耗時: 985.2秒」三方交叉。
6. **B1 歸屬絆索新舊碼離線重播**（0 模型成本）：`git show eb9dfeb^:backend/core/fidelity_checks.py > /tmp/old_fidelity_checks.py`，對 E3／E4 兩份素材分別以舊碼與 HEAD 碼執行 `analyze_fidelity`。
7. **數字對帳器與議題比對離線重播**（HEAD 碼，E3 素材）：`_validate_record_source_coverage`（`/tmp/e3_replay.py`，實跑非引用）。
8. **標籤命名空間盤點**：紀錄標註標籤分布（正則）＋ `fidelity_checks._tag_owner_issues` 的可檢命名空間（`發言者\d+`）比對；抽 5 個時間戳用 `iter_transcript_segments` 取含該時間戳的段落所有人。
9. **外部統計腳本重跑**（唯讀 repo、輸出 `/tmp`）：`/tmp/qp01/garble7.py`（ASR 亂碼殘留）、`/tmp/qp01/probe7b.py`（46 項細節探針）、結構統計（條目數／均字／最長／`（待確認）`）。

## 二、重跑量尺 vs 證據檔（CORE 3）

| 欄位／群組 | 證據檔值 | 我的重跑值 | 一致？ |
|---|---|---|---|
| `coverage.json`（全檔；`label` 除外） | sha256 `063b55e1…542fbe` | sha256 `8dc59c12…7f6ebe`（`label` 對齊後 `cmp` **BYTE-IDENTICAL**，diff 0 行） | **是** `[VERIFIED]` |
| `metric_version`／`checklist_sha256` | `coverage-1.0.0`／`cf012d1f…ec001` | 同 | 是 |
| `coverage_all`／`coverage_core`／`coverage_supporting` | 0.7015（47/67）／0.8214（23/28）／0.6154（24/39） | 同（逐欄） | 是 |
| `missing_core_ids`／`missing_core_statements` | `[F021,F045,F054,F065,F066]` | 同 | 是 |
| `by_category` | decision 8/9、name 3/3、number 4/4、constraint 11/13、action_item 6/9、topic 13/25、date 2/4 | 同 | 是 |
| transcript 觀察值（同 probes 對逐字稿） | all 0.9701／core 0.9643；漏 F021、F058 | 同 | 是 |
| `record_char_count`／正規化字元數 | 2717／1899 | 同 | 是 |
| `record_quality.json.metrics`（11 鍵） | char 2717、body tag 29、table 0、non-prefixed 0、items 7、tagged ratio 1.0、dup 0、term-fix 左 0／右 5、tag_traceability 全欄、`unsupported_entities_count=3` | 11/11 全等（`tag_traceability` 逐欄，含 `segments 183`） | 是 `[VERIFIED]` |
| `unsupported_entities_sha256` | `8e2e4effcc4d4c42…` | `sha256(json.dumps(['徵收股','煙酒文宣股','稽查股'], ensure_ascii=False))`＝`8e2e4effcc4d4c42…` | **是**（清單非聚合造假） |
| 5 支 sha256 | `sha256_manifest.json` | 音檔 `982151f4…`、md `45a942c3…`、docx `89d88e40…`、逐字稿 `c4136d39…` 全等 | 是 |
| DOCX | `formal_docx_valid=true` | `unzip -t` 無錯誤、OOXML、`word/document.xml` 取文字 2,455 字（含「科務會議紀錄」×2、「（待確認）」×29、「13,600」×1、「煙酒文宣股」×1） | 是 |

- 唯一非 byte 相同處＝`label`：證據檔 `coverage.json` 的 `label` 是 `E4-qwen27b-p4-final`、其 `coverage_observation.json`（runner 投影）是 `runner-coverage-a5abfc7c`，而該檔 mtime（11:25）晚於 runner 收尾（11:21）→ 該檔在 runner 交棒後被以同一支量尺**重寫過一次（僅改 `label`）**。內容經我 byte 級複核不變，**不影響任何量測值**，但屬 provenance 註記（見 §六-2(e)）。

## 三、CORE 1：能正常生成會議紀錄檔案（閘門與產物）

| 準則 | 判定 | 證據 |
|---|---|---|
| `.md`＋`.docx` 存在 | **達成** | `backend_data/outputs/0903-科務會議_a5abfc7c.md`（6,745 B）、`.docx`（40,535 B）；outputs 目錄 `.md` 恰一份（`outputs glob 唯一命中`） |
| DOCX 結構有效 | **達成** | 見 §二末列（獨立於 runner 的 `formal_docx_valid`） |
| 任務終態 | **達成** | `task_final.json`：`status=completed`、`progress=100`、`summary_failed=false`、`error_message=null` |
| runner 閘門 | **達成** | `verdict=PASS`、`failure_reasons=[]`、16/16 checks 全 `true`（含 `build_revision_match`、`task_summary_failed_false`、`formal_docx_valid`、`model_snapshot_consistent`） |
| runner 交棒 | **達成** | `/tmp/e4_runner.log`：`expected==actual 818b71e…`、`/api/health 200`、`backend child 已終止（exit=0）`、`[OK] verdict=PASS` |
| 品質閘門（5 項） | **達成** | `record_quality.checks` 5/5 true、`check_failures=[]`；`--quality-mode observe` 下 `gate_effect=none`（未影響 verdict） |
| 引擎與模型 | **達成** | `run_summary.engine`：`mode_used=local`、`effective_local_llm_provider=lmstudio`；`model_snapshot`：`unique_loaded_llm_count=1`、instance `qwen3.8-27b-splash`、`context_length=128000` |

## 四、CORE 2：三項修補 in-run 生效＋獨立重播

### 4.1 議題類假陽性（`849e934`）— **達成**

- in-run：`cov_expected_topic=9 cov_missing_topic=0`（log:114）；E3 對照為 `13／1`（E3 log:120）。E3 的「廉政宣導」假陽性在 E4 不再出現 `[VERIFIED]`。
- 獨立重播（HEAD 碼、E3 素材、`/tmp/e3_replay.py` 實跑）：`missing_topic=0`（E3 `1→0`），同時 `missing_number=2`——修補在**前一場失敗素材**上同樣成立 `[VERIFIED]`。
- 註：詞級覆蓋是**已知放寬**（`pre-push-review-01` 已列 false-accept 風險：碎片詞命中無關專名仍可接受）；本場未觀察到誤接受（本場期望集合 9 項全部真有對應內容）。

### 4.2 歸屬絆索（`eb9dfeb`）— **in-run 字面達成，但 E4 的證據力受限（重點）**

- in-run：`來源標註歸屬待確認` 在 E4 log **0 筆**（`grep -c`＝0）、`fidelity.attribution_flags=0` `[VERIFIED]`。
- **獨立重播（新舊碼對照、0 模型成本）**：E3 素材舊碼 `14` 筆 `tag_owner` 違規 → HEAD 碼 `0` 筆 `[VERIFIED]`（我自跑，非引用他人）；E4 素材舊碼 `0` → HEAD 碼 `0`。
- **命名空間限制（必須揭露）**：`_tag_owner_issues`（`fidelity_checks.py:529`）只檢查標籤為 `發言者\d+` 者。實測 E3 紀錄 45 個標註**全部**是 `發言者1`（故舊碼可報 14 筆）；E4 紀錄 29 個標註**全部**是 `科長`（角色名）→ **E4 的 0 筆有一部分是「不在可檢命名空間內」而非「已驗證正確」**。
- 補強證據（時間戳本身有效）：E4 `on_start_tag_ratio=1.0`（29/29 落在真實段首）、`attribution_overlap_median=0.2667`；我抽驗 5 個時間戳（00:06:14／00:19:49／00:22:09／00:13:37／00:31:34），每個都同時落在 `發言者1` 段與另一位發言者段的**共用邊界**上（例：00:06:14 ∈ `(357,374,發言者3)` 且 `(374,408,發言者1)`）→ 角色名歸屬「與至少一個含該時間戳的段落一致」，但**無法用現行儀器完整驗證**（無「科長↔發言者N」對照可查）。發言者1 佔 2254/2636 s（85.5%），與「科長」角色一致 `[INFERRED]`。

### 4.3 數字對帳器（`818b71e`）— **達成**

- in-run：`cov_expected_number=9 cov_missing_number=2`（log:114）＋ log:103「紀錄覆蓋率比對（數字）：未涵蓋 2 項：15、600」`[VERIFIED]`。
- 獨立重播（HEAD 碼、E3 素材）：`missing_number=2`（`15`、`600`，E3 場 in-run 為 0＝當時的子字串假命中）`[VERIFIED]`。
- 形式命中已消失：E4 md 的 `600` 只出現在 `13,600`（md:50）、`100` 只出現在「人數約 100 多」（md:38）→ 皆非真命中，對帳器正確判缺。

### 4.4 輪數與停損（`_summarize_with_local_pipeline:3136-3160`）— **達成**

- in-run：`logical_generations=3`、補強只跑 **1 輪**（log:105「本地摘要品質補強（第 1 輪）」）、第 2 輪在生成前被停損攔下：log:112「本地摘要補強未收斂（問題集合與上一輪相同，共 4 項）→ 停止再補強」`[VERIFIED]`。
- 對照：E3 跑了 **2 輪**（E3 log:107 第 1 輪、E3 log:113 第 2 輪，`logical_generations=4`）＝上限即停；E4＝1 輪＝停損即停 → **輪數 2→1 由設計保護達成**。
- `[INFERRED]` E4 的第 1 輪補強輸出與首版同尺寸（`content_chars=2706`、`completion_tokens=2051`，log:100 vs log:107）→ 該輪實質無改寫（問題集合因此相同）。

## 五、殘餘 4 項逐條定性（真缺 vs 假陽性）

判定準則：內容確不在最終紀錄＝**真缺**；內容在但改寫／漏字＝**部分命中**；內容完整僅 probes 用字未列＝**量尺假陰性**；檢查器對「逐字稿未出現的字面」告警且該字面確為重建／推測＝**合法告警（真待確認）**。證據皆為我自行 `grep` md／docx／逐字稿。

| # | 項目（in-run 問題字串） | 我的定性 | 逐字稿引文（行號） | 紀錄現況（行號） |
|---|---|---|---|---|
| 1 | 數字遺漏 `15` | **真缺（字面）／語意部分涵蓋** | L12「所以就原則上委任的部分就會少了 15%當然有 15%的人會升稅務員」 | md:34「委任比例從 40% 降至 25%，部分人員將透過甄選升為稅務員（非原地升遷）」→ 40→25 隱含 15 個百分點、「部分人員」取代「15% 的人」，**`15%` 字面 0 次** |
| 2 | 數字遺漏 `600` | **真缺** | L25「有一次是吃便當，然後發禮券啊 600什麼時候有啦…你就發 600塊，然後那個便當還加上飲料」 | 紀錄全篇無 600 元案例（md:50 僅 `13,600 元`＝17 人×800 元，屬另一事實；`600` 為 `13,600` 子字串，已正確不算命中） |
| 3 | 日期遺漏 `週一` | **真缺（整條事實被略去）** | L23「然後下個禮拜一我們要做內機哦嘿…就下禮拜一我們是下午會來看他們這邊是整天都內機」 | md「內稽／內機／週一／禮拜一」皆 0 次（`grep` 四詞全 0）；docx 亦 0；量尺 core `F021` 同步未涵蓋 |
| 4 | 專名依據待確認 `煙酒文宣股` | **合法告警（真待確認；非捏造、非假陽性）** | L12 逐字稿為 ASR 亂碼「煙酒為神穀」「煙酒文神穀股掌」（`煙酒文宣股` 字面 0 次） | md:31「下設『煙酒文宣股』與『欠稅管理股』」→ 模型把亂碼**正常化重建**成合理機構名；registry-aware 檢查仍列為未支持（`entity_registry` 無此名）→ 檢查器行為正確 |
| 5 | 金額／數量依據待確認 `600塊`／`100塊`／`15%` | **真缺（3 個字面皆缺）** | `600塊`：L25（如上）；`100塊`：L96「禮券會多 100塊嗎」、L97「送 100塊哪有」；`15%`：L12 | md：`600塊` 0、`100塊` 0、`15%` 0（`100` 唯一出現處是「人數約 100 多」，語境不同） |

- 彙總：4 條問題中 **3 條為真缺**（`15`／`600`／`週一`；其中 `15` 語意部分涵蓋）、`100塊` 亦為真缺（瑣碎問答細節）、`煙酒文宣股` 為**合法待確認告警**。**無一條是檢查器假陽性**——與 E3 場相反（E3 殘餘以假陽性為主）。`[VERIFIED]`
- `[VERIFIED]` `number_fabricated=0`、`entity_flags=1`（僅 `煙酒文宣股`、kind=`variant`）、人工抽查未發現捏造。

## 六、宣稱核對與 `run_notes.md` 稽核

### 6.1 任務書列出的宣稱（逐項）

| 宣稱 | 實測 | 判定 |
|---|---|---|
| 牆鐘 ~992 s | runner `11:05:23.833→11:21:56.075`＝**992.243 s**；任務窗 985.157 s（log「耗時: 985.2秒」） | **相符** |
| 補強 1 輪 | log 只有第 1 輪 + 停損（log:105／112） | **相符** |
| `logical_generations=3` | log:114 | **相符** |
| coverage all 0.7015／core 0.8214 | 我重跑 byte 相同 | **相符** |
| chars 2717 | md `len`＝2717、`record_char_count`＝2717 | **相符** |
| `unsupported_entities_count=3` | 清單 `['徵收股','煙酒文宣股','稽查股']`、sha 對得上 | **相符** |

**無誇大**；未發現與 raw evidence 不符的數字。

### 6.2 `run_notes.md` 稽核（逐項；2 項必須更正）

**（a）必須更正①：§二 兩列階段標籤對調。** log 的兩支大生成本來是「先萃取、後首版」：
- 第 1 支（11:09:27.109→11:13:46.059，258.950 s，`prompt_tokens=12474`／`completion_tokens=3482`／`content_chars=4776`）＝**萃取筆記**（其後立刻出現「萃取筆記零損串接…1 份、3220 tokens」log:98；且 pipeline metrics 的 `extraction=259.0` 對上它）。
- 第 2 支（11:13:46.064→11:17:37.771，231.707 s，`prompt_tokens=17983`）＝**首版紀錄**（prompt 含筆記；`content_chars=2706`≒最終 md 2717）。
- `run_notes.md` 卻把 258.9 s 標成「摘要 round 0（紀錄生成）」、231.7 s 標成「摘要（萃取筆記）…產出 3220 tokens 筆記」→ **兩列描述對調**（數字本身正確，總和 985.2 s 不變）。此錯誤會誤導後續判讀「哪一步是瓶頸」。

**（b）必須更正②：§四「補強輪數 E3＝1（收斂後停）」錯誤。** E3 log 有「第 1 輪」（E3 log:107）與「第 2 輪」（E3 log:113）、`logical_generations=4` → **E3 是 2 輪（上限即停）**，且 E3 verify_independent 已寫「2 輪未收斂」。故該列「E3 1／E4 1／相同」→ 應為「E3 2（上限即停）／E4 1（停損即停）」。

**（c）應補登錄：`決議期望集合為空` WARNING ×2。** log:102／109（`_validate_record_source_coverage:1868`）：萃取筆記「議題與決議」區塊的**決議**抽取為 0 項 → 決議類覆蓋檢查在本場是 no-op（E3 亦有 3 次同警告）。`run_notes.md` 全篇未提，屬登錄缺口（不影響 verdict，但影響「決議保障有生效」的宣稱）。

**（d）數字全數對得上（我逐項重跑）**：階段秒數（ASR 15.9／diar 153.0／校正 68.4／萃取 258.9／首版 231.7／補強 256.3／LLM 合計 815.3＝82.8%）；`ASR segment_count=1340、dropped 0、RTF 0.0059`；`diarization 682 段、8 位發言者、183 段發言`；`校正 45 段中 8 段修正、採納 22 處`；`（待確認）17→29`（我算 E4＝29、E3＝17）；`條目 45／37.2／98 vs 29／43.2／69`（我以同一腳本重跑完全一致）；`亂碼 9 次／6 型`（重跑 `/tmp/qp01/garble7.py`：E4 6 型 9 次、E3 18、B2 18、C5 1）；`46 探針 31/46=0.674`（重跑 `/tmp/qp01/probe7b.py`：E4 0.674、E3 0.761、B2 0.848、C5 0.652）；`number_missing E2=0／E3=2`（我各重跑一次量尺，E2 0 項、E3 `['600塊','15%']`）；`內機 ×2、紀錄整條略去`；`猜情×1 抄進紀錄`。

**（e）provenance 註記**：`coverage.json` 於 runner 交棒後被重寫（僅 `label` 由 `runner-coverage-a5abfc7c` 改為 `E4-qwen27b-p4-final`；mtime 11:25 vs 其他檔 11:21）。內容經 byte 級複核不變。另 `quality-parity-01/report.md` 的「993 秒」為 992.243 s 的向上取整（±0.8 s，非錯誤）。

## 七、未達項、額外觀測與殘餘風險

1. **E4 歸屬證據力受限（最重要）**：E4 的 29 個標註全為角色名「科長」，落在 `fidelity_checks._tag_owner_issues` 的**可檢命名空間之外**（`:529` 只收 `發言者\d+`）→「0 筆歸屬問題」不可解讀為「29 筆歸屬已驗證正確」。修補本身已被 E3 材料重播證明（14→0），但要在角色名紀錄上恢復可檢性，需另行設計（超出本場驗收範圍，不得由稽核員放寬）。
2. **決議類覆蓋 no-op**：萃取筆記決議 0 項（log:102／109）→ 決議保障在本場等於沒作用；紀錄的 13 列決議表「辦理情形」全為「（待確認）」（quality-parity-01 §二：`待確認 12、空白 26`），可讀性明顯不足。
3. **品質較 E3 回退（n=1，不可比大小）**：`all` 0.7761→0.7015（−7.5pt）、`core` 0.8571→0.8214（−3.6pt）、細節探針 0.761→0.674；換到的好處是亂碼 18→9、`（待確認）` 17→29 的避險策略。與雲端 C5（0.8060／0.8929）仍差 10.5pt／7.2pt `[VERIFIED]`（單場觀察值）。
4. **`內稽／下週一` 校正缺口第 3 次重現**（B2／E3／E4）：交付逐字稿仍 `內機`×2、紀錄整條略去（core F021 未涵蓋）→ 27B 校正層穩定缺陷。
5. **已知量尺盲區**（沿用 `pre-push-review-01`）：議題詞級覆蓋可被碎片命中接受；數字殘留 `１５．`／`• 15.` 形式；B1 中段重疊不再回報。本場未觀察到被觸發，但風險仍在。
6. **Windows 11＋Ollama 實機仍 `[UNVERIFIED]`**：靜態／payload 級相容已驗（`portability-audit-02`），本場未觸及。
7. **`run_notes.md` 需附更正**（§六-2 (a)(b) 兩處；建議以 append-only addendum 方式補記，比照 E3 的 `run_notes_addendum.md`）。

## 八、判決

**`ACCEPTED_WITH_GAPS`**

- `[VERIFIED]` CORE-1 完全達成：`verdict=PASS`、16/16 checks、`summary_failed=false`、md＋docx 存在且 DOCX 結構有效（我獨立複核）。
- `[VERIFIED]` CORE-3 完全達成：`coverage.json` 除 `label` 外 **byte 相同**；`record_quality` 11 鍵全等；5 支 sha256 全對。
- `[VERIFIED]` CORE-2：(a) 議題、(c) 數字、(d) 1 輪＋停損 皆達成；**(b) 歸屬 0 筆字面達成，但 E4 的證據力受限**（命名空間），修補以 E3 素材重播（舊 14→新 0）完成獨立驗證。
- `[VERIFIED]` CORE-4：殘餘 4 條全數逐條定性完成（3 真缺＋1 合法待確認；`100塊` 亦真缺），無檢查器假陽性。
- `[VERIFIED]` CORE-5：任務書 6 項宣稱全部與 raw evidence 相符、無誇大；`run_notes.md` 有 **2 處必須更正的內部錯誤**（階段標籤對調、E3 輪數誤值）與 1 處登錄缺口（決議 no-op 警告），建議更正後再引用。
- 依 `handoff §8`：以上 gap 均不屬「需改語意／門檻才過關」→ **不判 `PLANNER_REPLAN`**；稽核員未放寬任何門檻。
