# 獨立計畫審查 — T20260922-2037-02-local-model-quality-parity（Stage 02，attempt-01）

- 受審對象：`plan.md`（PLAN_REVISION 3，審查快照 sha256 `bf6158d05c8026affce509f8a0cf6cda108c32b9f62f43be29257f61ac64fd5d`，2026-09-22 22:0x 讀取）
- 審查者：獨立 Stage 02（read-only；未修改產品程式碼、`plan.md` 或既有證據檔；只建立本檔）
- 審查輸入：
  - `plan.md`（rev3）、`e2e/attempt-B2-27b-fix/`（`verify_independent.md`、`run_notes.md`、`attempt.json`、`record_quality.json`、`run_summary.json`）
  - `e2e/attempt-B1-moe-fix/attempt.json`、`e2e/attempt-A1-27b/{attempt.json, record_quality.json}`
  - `backend/core/text_postprocess.py`、`backend/services/summarization.py`、`scripts/e2e/measure_record_quality.py`、`scripts/e2e/run_owned_e2e.py`、`tests/test_t20260922_record_quality.py`
  - 研究文件 §10.3／§10.7（工作樹未提交 diff）、`git` HEAD `3fec08f` 與工作樹差異、`/tmp/b2-verify/repo-HEAD2`（釘住版原始碼）
- 獨立重算環境：`DATA_DIR=/tmp/rev-data .venv/bin/python`；釘住版重跑＝`git archive 3fec08f` 匯出樹（`/tmp/b2-verify/repo-HEAD2`）＋同一批 B2 產物

---

## 0. Goal Baseline 重建（權威來源：使用者需求＋獨立驗收報告）

1. 主目標：Mac ＋ LM Studio 以 `section_meeting` 產出的地端會議紀錄，品質「接近雲端 Gemini」；且品質機制**與模型無關**（日後 Win11＋RTX 4090＋Ollama＋Gemma 一體適用）。
2. 本波（P2）被縮限的 CORE＝「可查核性」：
   - CORE-1：正文出處標註的時間戳必須落在逐字稿的真實段落上，且（設計上）優先落在該標註指名發言者的段落內。
   - CORE-2：修復位於 LM Studio／Ollama 共用的確定性層，不得依賴模型名／家族／引擎特有參數。
3. 獨立驗收（attempt-B2-27b-fix）的事實：機械面無缺陷；判 FAIL 的唯一原因是 rev2 的字面閘門 `exact_tag_ratio ≥ 0.8` 在本場（51/52 筆標註用角色名「科長」）不可達 → 交付 `PLANNER_REPLAN`，建議更正閘門文字並把 `exact` 降為觀察值。
4. rev3 的任務：把量尺更正落地成可驗收的閘門契約，且不得把真閘門放寬、不得讓驗收變成事後湊分。

---

## 1. 獨立驗證方法（我實際做了什麼，不引用未重現的數字）

1. **重算三份紀錄的指標**（B2 `p2-27b-fix-01`、A1 `p2-27b-01`、P1 `p1-fixed-01` 的 `record.md`＋逐字稿）：
   - 以工作樹儀器 `measure_tag_traceability` 重算 → 與 `record_quality.json`／`instrument_recheck_20260922.json` 逐欄一致。
   - 以**釘住版 3fec08f 儀器**重跑 B2 → 共用欄位（on_start 1.0、exact 0.0192、traceable 1.0、total 52）一致；釘住版**無** `zero_time_*`／`distinct_*`／`excluding_zero` 欄位（該三組欄位是工作樹未提交新增）。
2. **離線重跑吸附**：對 A1 與 P1 的原始紀錄套用現行 `snap_source_tags_to_transcript`＋量測（重現研究文件所謂「吸附後」數字的唯一合理方法）。
3. **程式碼查核**：吸附／量測實作、`_finalize_record_text(mode="local")` 呼叫序、`_summarize_with_local_pipeline` 引擎分派、提示詞標註規則、`run_owned_e2e.py` 的 17 項 required checks 與 `metrics_valid` 語意、模型名／家族分支全域 grep。
4. **測試**：`pytest tests/test_t20260922_record_quality.py -q` → 22 passed（含本波 4 條新契約測試）。
5. **工作樹 vs HEAD**：`git status`／`git diff HEAD`（`text_postprocess.py`＋`measure_record_quality.py`＋測試＋研究文件均有未提交變更；`e2e/attempt-B2-27b-fix/` 為未追蹤）。

---

## 2. 逐條核實 rev3 的關鍵主張

### 2.1 `on_start_tag_ratio` 是否真的 speaker-agnostic — **真 [VERIFIED]**
`measure_tag_traceability` 的 `on_start` 只比較 `seg[0] == seconds`（任一真實段落起點），完全不看標籤；`snap` 規則 3 亦不改標籤。我對 A1（58/61→吸附後 61/61）、P1（10/27）、B2（52/52）重算全數吻合。

### 2.2 `exact_tag_ratio` 是否「結構上不可能」在角色名標註下通過 — **在本場為真，但 rev3 的理由應更精確 [VERIFIED＋表述要求]**
- 定義上 `exact` 需要「標籤字串等於該段發言者」＋「恰為該段起點」；B2 的 52 筆有 51 筆標籤是「科長」→ 上限 1/52，實測 0.0192。**在本場（角色名詞彙）確實不可通過。**
- 但要注意反例：**同一顆 27B 的 A1 場（修復前）61 筆標籤全是 `發言者N`**，`exact` 46/61；以現行吸附離線重跑 A1 → `exact` 58/61（0.951）。所以正確的論證不是「數學上不可能」，而是：**標籤詞彙是提示詞明文允許、且逐場變動的（`CLOUD_SPEAKER_TRACEABILITY_RULE`：「若該處能由內容確定身分（如科長…），則寫成（科長，00:12:04）」），確定性層無法控制也無法驗證 → 以它作模型無關閘門會產生 system-wide 不穩定。** rev3 §1 的「實測本場…結構上不可能通過」在句內範圍成立，但應引用 A1 反例把論證升級為「詞彙不可控」，否則讀者會誤以為只要模型乖乖寫 `發言者N` 這指標就永遠不可達。

### 2.3 新指標定義 vs 實作（分母） — **一致 [VERIFIED]，但有邊界缺口**
- `on_start_tag_ratio_excluding_zero`：實作＝`on_start_nonzero / (total - zero_time)`（分母＝非 `00:00:00` 標註數），docstring／量測腳本註記／研究文件三處一致；我對 B2 重算 45/45＝1.000、A1 51/54＝0.944、P1 0/27＝0.370，全部吻合。計畫 §4-3 的定義文字與實作一致。
- **邊界缺口**：全數標註皆 `00:00:00` 時 `ex0` 回 `None`（除以 0），計畫未定義驗收如何處理 `None`；且 `zero_time_tag_ratio`、`distinct_tag_time_ratio` 只列觀察值 → 一個「≥17 筆全是 `00:00:00`」的退化紀錄可讓 `on_start＝1.0`、`ex0＝None` 而不觸發任何閘門。P1-16 已把辨別力列為新缺口，但閘門層沒有下限。

### 2.4 CORE-2 模型無關性（程式碼分支反證搜尋） — **真 [VERIFIED]（實機 Ollama 仍 [UNVERIFIED]）**
- `snap_source_tags_to_transcript` 只依賴「逐字稿段落時間表」＋`template.speaker_traceability`；呼叫點唯一（`_finalize_record_text` 的 local 分支）；`_summarize_with_local_pipeline` 以 `_generate_with_local_engine` 分派 `ollama`／`lmstudio`，後處理同一條。
- 全域 grep `qwen|gemma|splash|a3b|27b|35b|llama|mistral`：後端僅出現在既有 provider/config（如 `OLLAMA_MODEL` 預設 `gemma4:31b`）與選模流程，**本波修復路徑（吸附／收尾／量測）無任何模型名或家族分支**。CORE-2 的結構性主張成立；實機 Ollama／Gemma 驗證仍為 BEST_EFFORT（計畫已如實標註）。

### 2.5 rev3 與實作／證據的一致性 — **計畫本文數字正確；研究文件（W6 交付物）離線數字錯誤 [見 F3]**
- 我重算確認：§1 基線「MoE 10/27（37.0%）、exact 4/27＝14.8%；27B 58/61（95.1%）、exact 46/61」正確；§6.1 表 A1（0.951／0.944／61／21／4,338）、B2（1.000／1.000／52／25／4,062）全部正確（含 `ex0` 分母語意）。
- 但研究文件 §10.3 的「**離線驗證**」表（未提交版）有不可重現數字：
  - P1 吸附後寫 `on_start 27/27（100%）`、`exact 0/27`；**現行含 `TAG_SNAP_MAX_SHIFT_SECONDS=120` 的程式實測為 20/27（74.1%）、19/27**（7 筆 kept_far）。
  - A1 吸附後寫 `exact 1/61（角色名標籤）`；**實測 58/61（A1 標籤 61/61 全是 `發言者N`，不是角色名）**，且與同列「吸附前 exact 46/61（label 相符）」自相矛盾——吸附不改標籤，46 筆不可能變 1 筆。
  - 研判：該表把「第一版（未加 120 s 上限）的舊離線結果」與「B1／B2 實際場次的 exact 分子」混用，並在標題宣稱「第三輪以新儀器重測」，但吸附後欄位並未以 shipped 程式重測。

### 2.6 E2E 證據是否足以支撐閘門 — **部分 [見 F2]**
- B2 於 clean HEAD `3fec08f` 執行、runner 16/16 PASS（`run_summary.json` 可查）；獨立驗收以釘住版重跑量測，共用欄位與執行時檔案逐欄一致 [VERIFIED]。
- 但 `run_owned_e2e.py` 的 `metrics_valid` 只驗 backend log 的 pipeline metrics，**不驗** `on_start/traceable/body/table` 等品質閘門；品質閘門是驗收者另行以 `measure_record_quality.py` 判讀。計畫 §4 把 runner PASS 與品質門檻分列，這個理解正確，沒有「runner PASS＝品質達標」的誤導。
- 真正缺口在 **F2**：rev3 的輔助閘門 `ex0 ≥ 0.9` 所依賴的欄位在釘住版 `3fec08f` 不存在（我以釘住版儀器確認）；B2 的 `ex0＝1.000` 只出現在工作樹儀器產物與被就地覆寫的 `record_quality.json`（`record_quality.json` mtime 21:47→21:50:52；獨立驗收 §4.3 已記錄 v1.0＝0.865→v1.1＝1.000 的同名換定義）。

---

## 3. 上而下審查（目標對齊、閘門比例、是否放水）

### 3.1 目標對齊
- rev3 把 CORE 縮限在「可查核性」並明列 SUPPORTING／BEST_EFFORT／排除項，與使用者需求 1–4 的分階段處理一致；吸附是確定性層、模型無關，符合需求 4。**目標對齊佳。**
- 本波不覆蓋「接近雲端」的覆蓋率／忠實度（計畫已排除 P1-4、觀察 unsupported_entities）——這是明示的範圍縮限，不是隱藏缺口（獨立驗收 §8 也照列）。維持為全案殘餘風險即可。

### 3.2 閘門比例原則：這是不是「放寬標準讓驗收過關」？——**方向合理，不是放水；但 rev3 的契約文字與證據治理未完成（F1–F4）**
我的判斷與依據：
1. **被降級的 `exact` 是一個無效量尺**：它要求發言者標籤字串等於逐字稿的 `發言者N`，但提示詞**明文允許**「（科長，00:12:04）」；且同一模型 A1／B2 兩場就換了詞彙。閘門若保留，等於對 prompt-compliant、模型自由的輸出抽獎 → 這正是獨立驗收所稱「量尺缺陷而非產品缺陷」。
2. **降級不等於刪除**：`exact`、`tags_inside_same_speaker_segment`、`zero_time_*`、`distinct_*` 全部保留為觀察值，並新增 `ex0` 反膨脹指標；沒有「因為會 FAIL 就把監控拿掉」。
3. **留下的閘門仍直接測量使用者結果**：時間戳存在於真實段落（traceable ≥0.95）、落於段落起點（on_start ≥0.95）、排除會議起點後的實質命中（ex0 ≥0.9）、標註數下限（≥17）、表格髒標註歸零。B2 全部大幅達標（1.0／1.0／1.0／52／0），不是踩線過關。
4. **但「指名發言者」是 CORE-1 的原始要求之一**：rev3 只把它降為觀察值，卻沒有在 CORE-1 定義句裡同步「本波不保證、非閘門」的語意（§1 仍寫「且優先落在該標註指名發言者的段落內」），§5 更寫出與實作相反的 `[VERIFIED]` 宣稱（見 F1）。這是**契約漂移**：rev2 就是死於「條文 vs 閘門不一致」，rev3 不該在同一個地方留第二顆地雷。
5. 若團隊認為歸屬必須被保證，替代方案（比照獨立驗收 §9.1 的兩個方向）：
   - **方案 A（本波最小、建議）**：CORE-1 改寫成「閘門＝時間戳真實且落於段落起點（speaker-agnostic）；發言者歸屬為非閘門觀察值（本波不保證）」，把「優先落在指名發言者段落內」移入「已知殘餘風險／後續項」，並在 §5 如實寫「規則 3 跨發言者吸附：只改時間、不改歸屬；B2 實測 39–44/45 為跨發言者，其中抽樣 2/8 落在 <5 s 碎片」。
   - **方案 B（若要真的閘門化歸屬，屬設計變更）**：先強化規則 3（跨發言者吸附優先退回「最近的同發言者實質段落」，排除 <5 s 碎片），再新增**speaker-agnostic** 的品質代理閘門，例如「跨發言者吸附占比 ≤ X」與「標註落點為 <5 s／極短內容段落之占比 ≤ Y」——這兩個量不需要知道標籤詞彙，且能抓到獨立驗收 §5 的「薄弱引註」。
   - **方案 C（不建議單獨使用）**：只保留觀察值、不寫任何殘餘風險說明——等於默認歸屬無人負責，與使用者「可查核」的期待不符。
6. 因此我的結論是：**更正量尺的「方向」本身合理，不構成放水**；但 rev3 尚未把「換尺」的語意、證據出處與研究文件數字治理完成，這些必須以修訂收斂（F1–F4），否則下一輪驗收仍可能出現同類 false FAIL／false PASS。

### 3.3 設計經濟性
- 修復落在單一確定性函式＋單一插入點，fail-soft、只依賴逐字稿段落格式；沒有新增服務、狀態或跨層耦合。**設計經濟性佳。**
- `TAG_SNAP_MAX_SHIFT_SECONDS=120` 的「長段落保留原時間戳」是合理取捨；但要注意這使「吸附後保證段首」不成立（P1 離線重跑 7/27 kept_far），閘門以比例 0.95 表述即可，勿在文件宣稱「必達 100%」的普遍保證。

---

## 4. 下而上審查（實作／證據／遺漏）

### 4.1 revision 是否真的反映實作與證據
- 計畫本文（§1、§4、§6.1）→ 與實作及我重算的證據一致 [VERIFIED]，除兩處文字缺陷：§5 首條 `[VERIFIED]` 宣稱（F1）、研究文件離線表（F3）。
- 量尺敘述：`ex0` 分母在計畫、docstring、腳本註記、研究文件四處一致 [VERIFIED]。

### 4.2 未記錄的量尺變更
- `ex0` 是**驗收期間才誕生**的指標，且有 v1.0→v1.1 兩版分母；B2 的同名指標在同一天出現 0.865 與 1.000（前者是 v1.0＝分母總數）。計畫 §6.2-3 已誠實記錄事件，但（a）未把「v1.1 定義」釘進 §4-3 的閘門文字（只寫了分母，未寫版本），（b）把 `metric_version` 欄位延到「後續波」，而本波閘門正好依賴這個換過定義的指標，（c）B2 的 `record_quality.json` 已被就地覆寫（舊版未保留）。（b）（c）是證據治理缺口，非數值造假——我已獨立重現 v1.1 的 45/45。

### 4.3 E2E 證據 vs 閘門
- 支撐 `on_start／traceable／body／table`：足夠（clean HEAD、runner PASS、釘住版量測重跑一致、我另行重算一致）。
- 支撐 `ex0 ≥ 0.9`：**目前只有工作樹儀器（未提交）＋被覆寫的輸出**；釘住版無法產生該欄位。最終驗收前必須把儀器提交並在該 revision 上重新推導一次（純量測重跑，成本近零）。

### 4.4 遺漏的風險（計畫未列或列錯的）
1. `ex0＝None`（全零標註）與零時間戳洗版的驗收語意未定義（F4）。
2. 歸屬正確性沒有閘門、也沒有在 CORE-1 條文裡除役（F1）；獨立驗收 §7.3／§8.1 的跨發言者／碎片引註事實未回寫計畫風險節。
3. B1（MoE 修復後、前次 commit 證據）`body_source_tag_count=14 < 17`，B1 檔內以 run 變異備註；§4-3 仍把 `body ≥ 17` 列為通用閘門而未註明適用範圍（F5）。
4. 吸附統計 log 不含 `kept_far`（僅 snapped/changed/untraceable 部分欄位），長段落案例的可觀測性略缺（低）。

---

## 5. 發現清單（含嚴重度）

| # | 發現 | 嚴重度 | 證據 |
|---|---|---|---|
| F1 | **CORE-1 契約漂移**：CORE-1 定義句仍要求「優先落在指名發言者的段落內」，但閘門清單已無任何歸屬量尺；§5 首條 `[VERIFIED]` 宣稱「吸附改寫目標仍為同一發言者的同一段落」，與實作規則 3（跨發言者吸附）及 B2 實測（39–44/45 跨發言者、抽樣 2/8 落在 3 s 碎片）矛盾。這正是 rev2 false FAIL 的同型地雷。 | 高 | `plan.md` §1/§5；`text_postprocess.py` 規則 3；`run_notes.md` 吸附日誌；`verify_independent.md` §5/§7.3 |
| F2 | **新閘門指標無釘住版出處**：`on_start_tag_ratio_excluding_zero` 於驗收期間才引入並改定義（v1.0 0.865→v1.1 1.000），釘住版 `3fec08f` 儀器無此欄位；B2 閘門值僅存在於未提交工作樹與被就地覆寫的 `record_quality.json`；計畫把 `metric_version` 延到後續波。 | 中高 | 我的釘住版重跑（無該欄位）；`instrument_recheck_20260922.json`；`verify_independent.md` §4.3；`plan.md` §6.2-3 |
| F3 | **研究文件（W6 交付物）離線吸附後數字不可重現**：P1 寫 `27/27`、`0/27`；現行 shipped 程式實測 `20/27`、`19/27`。A1 寫 `1/61（角色名標籤）`；實測 `58/61`（A1 標籤全為 `發言者N`），且與同列吸附前 `46/61` 自相矛盾。 | 中 | 我的離線重跑（stats: P1 snapped 20/kept_far 7；A1 snapped 54/kept_far 7）；研究文件 §10.3 未提交 diff |
| F4 | **閘門健壯性缺口**：`ex0` 全零標註時為 `None`，驗收未定義；零時間戳洗版（≥17 筆全 `00:00:00`）可讓 `on_start＝1.0`、`ex0＝None`；`distinct_tag_time_ratio`、`zero_time_tag_ratio` 僅觀察值；`kept_far` 使「吸附後保證段首」不成立（P1 離線 7/27），文件表述需一致。 | 中低 | 實作＋測試；我的重跑 |
| F5 | **`body ≥ 17` 閘門的適用範圍未註明**：B1（MoE 修復後）`body=14`，以 run 變異備註；本輪驗收主體是 27B（B2=52）。若不註明，下一輪 MoE 驗收會撞上同一 false FAIL 型問題。 | 低 | `attempt-B1-moe-fix/attempt.json`；`plan.md` §4-3 |

已驗證為真的摘要：on_start speaker-agnostic [真]；ex0 分母語意與實作一致且我獨立重現 [真]；計畫 §1/§6.1 數字 [真]；CORE-2 無模型名分支 [真]；雲端不變性由測試釘住（22 passed）[真]；B2 E2E runner 證據 [真]。產品碼本身在本次審查未發現缺陷。

---

## 6. 建議修訂（bounded，供 Planner；不需重做產品設計）

1. **F1（必做，文字）**：CORE-1 改為兩層——閘門＝「時間戳真實＋落於段落起點＋ex0」；歸屬＝「本波**不驗證**、非閘門」的明示觀察值，並把獨立驗收 §7.3 的跨發言者／碎片事實寫進 §5 風險（取代現行錯誤的 `[VERIFIED]` 句）。若要保留「優先落在指名發言者」為 CORE，需先採用方案 B 的可閘門代理（跨發言者吸附占比、碎片落點占比）。
2. **F2（必做，流程＋文字）**：本波即提交儀器 v4.9.0；在 §4-3 釘住 `ex0` 的定義與版本字串（v1.1＝分母非零標註數），並把「於最終 HEAD 以儀器重跑 B2 產物重新推導閘門值（含 0.865 的 v1.0 觀察值保留）」列入驗收步驟；`metric_version` 欄位建議本波加（小改動），或至少保證驗收證據檔內註記版本。B2 證據目錄後續禁止就地覆寫（append-only）。
3. **F3（必做，文件）**：研究文件 §10.3 的「吸附後」欄位以 shipped 程式重測（或明確標為 pre-120 s-cap 舊值並附註不可重現原因）；A1/P1 的 exact 值以實測更正並移除「角色名標籤」的錯誤歸因。
4. **F4（建議，文字）**：§4-3 補「`ex0 is None` ⇒ 閘門 FAIL」語意；並在後續波為 `zero_time_tag_ratio`／`distinct_tag_time_ratio` 訂下限。
5. **F5（建議，文字）**：§4-3 註明 `body ≥ 17` 的適用範圍（本輪 27B；MoE 依 §9.11 以觀察值處理），或補上 MoE 的等效防線定義。

---

## 7. 閘門結論

**PLAN_REVISION_REQUIRED**

- 依據：rev3 的**量尺更正方向正確**（`exact` 是受提示詞允許、逐場變動的標籤詞彙影響的無效閘門，降級並補上 `ex0` 是修尺不是放水），但修訂本身留下三類需收斂的問題：CORE-1 契約與 §5 `[VERIFIED]` 宣稱仍與實作／證據矛盾（F1，高）；新閘門指標 `ex0` 在釘住版不存在、定義於驗收期間變更、輸出被就地覆寫，且版本欄位被延後（F2，中高）；研究文件（W6 交付物）離線數字不可重現（F3，中）。修訂完成後（F1 文字除役或方案 B 代理閘門、F2 提交＋釘住版本＋最終 HEAD 重推、F3 更正數字），本計畫即可進入下一輪審查。
- 本結論不阻斷產品碼：B2 產物、吸附行為、CORE-2 結構、測試與 runner 證據本次審查皆 [VERIFIED]。
