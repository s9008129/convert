# 獨立計畫審查 — T20260922-2037-02-local-model-quality-parity（Stage 02，attempt-02）

- 受審對象：`.agent/tasks/T20260922-2037-02-local-model-quality-parity/plan.md`，自稱 `PLAN_REVISION 3`；
  本審查快照 sha256 `4cf6ac0a6bca1c2a0feeac15ace82565399f93e3a92b8500b6200cd8976b9767`（開審與收審前後各量一次，同值）。
- **修訂標籤衝突（本審查新發現 N1 的證據）**：`review/attempt-01/review.md` 受審的「rev 3」快照為
  `bf6158d05c8026affce509f8a0cf6cda108c32b9f62f43be29257f61ac64fd5d`——與本次不同檔。即「rev 3」
  在紀錄上同時指向兩份不同內容（attempt-01 判 `PLAN_REVISION_REQUIRED` 的版本＋已修正版本）。
- 審查者：獨立 Stage 02（fresh context；read-only）。未修改產品程式碼、`plan.md`、`review/attempt-01/`；
  本次僅新建 `review/attempt-02/review.md`（append-only，新目錄）。
- 環境：HEAD `3fec08f`（`fix/qwen-local-quality-parity`），工作樹含本波未提交變更（`git status` 已逐項核對）。
- 獨立驗證動作（全部實跑；不引用未重現的數字）：
  1. `DATA_DIR="$PWD/data" uv run --no-sync pytest tests/test_t20260922_record_quality.py -q -p no:randomly`
     → **`22 passed in 0.49s`**。
  2. 純函式離線重跑吸附＋量測（`snap_source_tags_to_transcript` → `measure_tag_traceability`，
     `get_template("section_meeting")`；**未呼叫任何模型**）：`data/cache/e2e/p1-fixed-01/backend_data/outputs/0903-科務會議_327a48e6.md`
     與 `data/cache/e2e/p2-27b-01/backend_data/outputs/0903-科務會議_f012e80c.md`（各自 transcript 已核同一 hash）。
  3. 釘住版查證：`git show 3fec08f:backend/core/text_postprocess.py`、`git log -S"on_start_tag_ratio"`。
  4. 執行日誌：`data/cache/e2e/p2-27b-fix-01/backend.log`（21:34:59／21:40:58／21:46:49 三筆吸附統計）。
  5. B2 產物 `record_quality.json`＋對 B2 正文標籤逐筆計數；`instrument_recheck_20260922.json`。
  6. 研究文件（工作樹未提交版本）§10.2–§10.7 全文核對。

## 0. Goal Baseline（權威來源：使用者需求＋獨立驗收報告）

1. 主目標：Mac＋LM Studio 以 `section_meeting` 產出的地端紀錄品質「接近雲端 Gemini」；機制必須**與模型無關**（需求 4）。
2. 本波（P2）CORE＝可查核性：CORE-1 出處標註（時間戳落在逐字稿真實段落／吸附後落段首）；CORE-2 修復位於確定性層、無模型名分支。
3. 獨立驗收 attempt-B2 的事實：機械面無缺陷；false FAIL 來自 rev2 的字面閘門 `exact_tag_ratio ≥ 0.8` 在「角色名標註」場結構性不可達 → 建議更正閘門量尺。
4. rev3 的任務：把量尺更正＋F1–F3 落地，且不得真放寬、不得讓驗收變成事後湊分。

## 1. F1 驗證（CORE-1 契約文字漂移）→ 已收斂 [VERIFIED]

1. **「指名發言者」除役明示**（plan.md:28–31）：「**已除役（rev 3，非閘門殘餘風險）**：『時間戳落在該標註
   指名發言者的段落內』不再作為本波閘門」，並列出理由、將 `tags_inside_same_speaker_segment` 列為觀察值、
   明示「**發言者歸屬正確性仍是已知殘餘風險**（P1-1）」。符合 attempt-01 §6-1 的要求（明示除役、非閘門、殘餘風險在案）。[VERIFIED 文字]
2. **§5 錯誤敘述已更正**（plan.md:87–90）：現為「**不保證同一發言者**（規則 3：跨發言者時只改時間、不改歸屬；
   B2 實測 45 筆吸附中 44 筆為跨發言者、最終輸出 40 筆中 39 筆為跨發言者）」，並註明「先前版本的 `[VERIFIED]`
   敘述『仍改到同一發言者同一段落』與實作不符，rev 3 一併更正」。
  我以執行日誌逐筆核對：`p2-27b-fix-01/backend.log` 21:34:59「吸附 45 處（段落內 1／最近段落 0／跨發言者 44）」
  與 21:40:58／21:46:49「吸附 40 處（…跨發言者 39）」（`backend.log:273／:350／:425`）——文字與實測一致。[VERIFIED 實測]
3. **plan 內「發言者」敘述全掃描**（6 組：:28–31／:35／:37／:65／:88–90／:91）：除 N2 的語氣殘留外，
   未發現新的同型契約漂移。R21（:65）「25/27（MoE）、61/61（27B）時間戳落在正確發言者段落內」經我離線重測
   ＝ `tags_inside_same_speaker_segment` 前值恰為 25/27、61/61，數字為真。[VERIFIED]
4. **殘留（N2，低／建議，不阻斷）**：①:27「吸附後必須落在真實段落起點」為絕對語氣，未帶 `TAG_SNAP_MAX_SHIFT_SECONDS=120`
   的 `kept_far` 例外（§6.3 與研究 §10.3 有說明，CORE 條文本身沒有）；②:65「不需重生成」為條件性成立
   （MoE 舊紀錄單靠吸附僅 20/27＝74.1%；達 1.000 的是重新生成後的 B1）；③§5「改寫目標是時間戳所在的
   真實段落起點」對規則 2（nearest）不精確（本波全部實測 `snapped_nearest=0`）。

## 2. F2 驗證（輔助閘門無釘住版出處／就地覆寫）→ 已收斂 [VERIFIED]

1. **`metric_version` 真的存在且有測試釘住**：`backend/core/text_postprocess.py:959` 回傳
   `"metric_version": "tag_traceability-1.1.0"`；`tests/test_t20260922_record_quality.py:726` 斷言該字串；
   實跑 `DATA_DIR="$PWD/data" uv run --no-sync pytest tests/test_t20260922_record_quality.py -q -p no:randomly`
   → **22 passed**（含 `test_measure_tag_traceability_zero_time_tags_are_isolated` 新契約）。[VERIFIED]
2. **「B2 閘門只依 `on_start_tag_ratio`，該指標在 `3fec08f` 即存在」已明示**（plan.md:116–117）。
   查證：`git log -S"on_start_tag_ratio"` 唯一命中 `3fec08f`；`git show 3fec08f:…text_postprocess.py`
   第 951 行即為 `"on_start_tag_ratio": (on_start / total)`；`metric_version` 在 `3fec08f` 不存在（本輪新增，合理）。
   現行 `on_start`／`exact` 計算式與 `3fec08f` 版逐字相同（工作樹 diff 僅新增欄位），故 B2 閘門值 52/52＝1.000
   可由釘住版重現（與 attempt-01 的釘住版重跑一致）。[VERIFIED]
3. **`record_quality.json` 就地覆寫風險已記錄**：plan §6.2-3（:114–118）記錄覆寫事實
   （`on_start_tag_ratio_excluding_zero` 分母 0.865 → 1.000）與處置；`verify_independent.md` §4.3（:104–108）
   保留完整紀錄（含 v1.0 觀測值 0.865、mtime 21:50:52）。B2 現行 `record_quality.json` 已帶
   `metric_version=tag_traceability-1.1.0`。[VERIFIED]
4. **殘留（N3，低／建議，不阻斷）**：①plan 未把「E2E 證據 append-only」明文寫成決策（harness §12 已規範，
   但 attempt-01 的建議未被收成 plan 條文）；②`instrument_recheck_20260922.json`（研究 §10.3 數字的重測來源）
   本身未帶 `metric_version` 欄；③W3 工作項未列 `metric_version` 為交付物（僅見於 §6.2-3）。

## 3. F3 驗證（研究文件「吸附後」數字）→ 已收斂 [VERIFIED，逐項獨立重現]

以 shipped 程式（純函式、無模型）離線重跑吸附＋量測，與研究 §10.3（:771–772）及 plan §6.3 完全一致：

| 紀錄 | `on_start`（我重跑） | `exact`（我重跑） | `inside_same` | 吸附統計（我重跑） |
|---|---|---|---|---|
| MoE 35B p1-fixed | 10/27（37.0%）→ **20/27（74.1%）** | 4/27（14.8%）→ 19/27（70.4%） | 25/27 → 25/27 | `snapped=20`（`changed=16`、`speaker_mismatch=1`）、`kept_far=7`、`untraceable=0` |
| dense 27B p2-A1 | 58/61（95.1%）→ **61/61（100%）** | 46/61（75.4%）→ 58/61（95.1%） | 61/61 → 61/61 | `snapped=54`（`changed=14`）、`kept_far=7`、`untraceable=0` |

- 舊「推論值」（27/27、0/27、1/61）已不存在於文件；§10.3 的更正註記（把 46/61、4/27 正名為 `exact_tag_ratio`）與實測相符。
- 重跑方式（可複製）：`DATA_DIR="$PWD/data" LOG_LEVEL=CRITICAL .venv/bin/python` →
  `snap=snap_source_tags_to_transcript(rec, tr, get_template("section_meeting"))` → `measure_tag_traceability(rec/…, tr)`（純函式、無模型）。
- 附帶核對：plan §6.1 表（A1 `0.951（58/61）`、`excl0 0.944（51/54）`）與 B2 `record_quality.json`
  （`1.000（52/52）`、`1.000（45/45）`、`tags_total=52`、`zero_time=7`、`distinct=15／0.288`）全數一致。
- 殘留（N4，低／建議，不阻斷）：①研究 §10.4（:797）「21 passed，含 4 條本波新契約」已過時——現行實測本檔 22 passed
  （＋回歸檔共 31 passed）；②研究 §10.5（:813）SOP 門檻 `on_start_tag_ratio ≥ 0.9` 與計畫 §4-3（:82）閘門 `≥ 0.95`
  不一致，同一指標兩個門檻、未說明關係。

## 4. 是否有「為了讓驗收通過而放寬標準」？——判定：非放水，屬量尺修正

- **被除役的是什麼**：rev2 閘門 `exact_tag_ratio ≥ 0.8` 要求「時間戳為段首**且**標籤字串等於該段逐字稿發言者名」。
  逐字稿只有 `發言者1..8`（實測 distinct=8），提示詞明文允許「能確定身分時寫角色名」；B2 場 52 筆標註中
  **51 筆是「科長」、僅 1 筆是「發言者3」**（我逐筆計數）→ 該指標上限 ≈1/52＝0.019，屬**結構性不可達**的
  false FAIL，與產品缺陷無關。此判斷正是獨立驗收（attempt-B2）自身給出的建議。
- **替代閘門不是臨時發明**：主指標 `on_start_tag_ratio` 在驗收所用釘住版 `3fec08f` 已存在（本審查查證），
  B2 的值（52/52）不需任何新欄位即可重現；新增的 `on_start_tag_ratio_excluding_zero ≥ 0.9` 是**更嚴**的輔助閘
  （排除必然命中的 `00:00:00`）。
- **真需求是明示降級、不是刪除**：發言者歸屬正確性（P1-1）與標註辨別力（P1-16）保留在文件與後續波清單；
  `exact`／`inside_same` 仍以觀察值列出。
- **同時揭露的界線（必須說清楚）**：新閘門驗證「時間戳真實＋落在真實段首（speaker-agnostic）＋非零時間戳段首命中率」，
  **不驗證**「時間戳屬於標註指名發言者」的語意；且對 27B 場，修復前 A1 的 0.951 本已接近 0.95——閘門不是
  「修復偵測器」，修復效果另由 W5 對照承擔（A1 0.951→B2 1.000；MoE 離線 0.370→0.741、重新生成 B1＝1.000）。
  以上皆為計畫明示的殘餘風險，非隱性放水。

## 5. 本次發現清單

| # | 發現 | 嚴重度 | 證據 | 要求 |
|---|---|---|---|---|
| N1 | **修訂身分不單調**：`plan.md` 自稱 `PLAN_REVISION 3`，但內容已非 attempt-01 受審快照（`bf6158d0…`→`4cf6ac0a…`）；§6.4（:130）稱三項發現「已在 rev 3 逐項處理」——對 attempt-01 審過的 rev 3 並非事實。同一修訂號承載矛盾結論（attempt-01：REVISION_REQUIRED），違反 harness §7／§12「審查驅動 replan 遞增 PLAN_REVISION」「修訂單調」；下游 Stage 03 的修訂/雜湊一致性檢查將無單一權威可驗。 | 中（流程／決定有效性） | attempt-01:3（受審 hash）；本檔開頭 hash；plan.md:4、:126–131 | **必做**（見 §6） |
| N2 | `kept_far` 例外未反映在 CORE-1／§2／§5 的絕對語氣（§1.4 三點） | 低 | plan.md:27、:65、:88；本審查重跑 | 建議 |
| N3 | E2E 證據 append-only 未明文化；recheck 檔無 `metric_version`；W3 未列 `metric_version` | 低 | plan §3、§6.2-3；`instrument_recheck_20260922.json` | 建議 |
| N4 | 研究 §10.4 測試數過時（21→22／31）；§10.5 門檻 0.9 與 §4-3 的 0.95 不一致 | 低 | 我的 pytest 實跑；研究 :797、:813 | 建議 |
| N5 | attempt-01 的 F4／F5 建議仍未處理（`ex0 is None` 的閘門語意；`body ≥ 17` 對 MoE（B1=14）的適用範圍） | 低 | attempt-01 §5/§6-4、§6-5；plan §1、§4-3 | 建議 |

## 6. 閘門結論

**PLAN_REVISION_REQUIRED**（bounded；僅 N1 為阻斷項）

- 必做（純文本、不動產品碼）：①`PLAN_REVISION` 遞增為 **rev 4**，修訂紀錄行如實記載「rev 3（hash `bf6158d0…`）
  經 attempt-01 判 `PLAN_REVISION_REQUIRED`；rev 4 依該審查與獨立驗收完成：CORE-1 除役文字／§5 更正／
  `metric_version` 落地／研究文件數字更正」；②改寫 §6.4，不再聲稱「審查過的 rev 3 已逐項處理」，並註明
  attempt-02 已獨立驗證 F1–F3 的實質修正。§1／§5／§6.2／§6.3 的實質內容已驗證，可原樣沿用。
- 建議（可一併納入 rev 4，非阻斷）：N2–N5。
- 狀態語意：F1／F2／F3 **實質已修正並經本審查獨立重現**；產品程式碼、吸附行為、B2 產物與測試證據
  本次審查**未發現缺陷**；本閘門不阻斷產品碼的持續工作，但 `plan.md` 在修訂身分修正前**不能**作為被核准的
  計畫修訂（approval 必須綁定唯一修訂；同一「rev 3」不得同時承載兩個結論）。
- 未重驗（不在本審查範圍）：全測 baseline 881 passed／2 skipped 未重跑；§6.2-1（710 s 補強浪費）沿用
  attempt-B2 獨立驗收之既有結論；B1（MoE）數字未重跑（本輪依使用者指示僅測 27B）。
