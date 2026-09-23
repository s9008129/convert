# Stage 02 獨立計畫審查 — attempt-02（受審 PLAN_REVISION 3，sha256 已覆核）

- 受審對象：`.agent/tasks/T20260923-1810-01-local-record-fidelity-density/plan.md`（181 行，`PLAN_REVISION: 3`）
- sha256 覆核：審查者獨立計算＝`9d8e3e27cb3a9332d5131b5dbac2f89dbde3b9a567e6a59f933c9a0c4372d809`。
  第一次指定值 `12356cde…` 與實測當時內容不符（審查者實測即為 `9d8e…`）；使用者隨即勘誤為 `9d8e…`，
  複核**一致** ⇒ 以 `9d8…` 為受審快照，未觸發雜湊不符的 `PLAN_BLOCKED` 條件。`[VERIFIED]`
- 角色宣告：fresh context、**唯讀**。未修改 `plan.md`、未改任何產品程式、未 commit、未跑測試、未呼叫任何模型。
  本 attempt 目錄僅新增本檔。審查期間觀察到工作樹已有**未 commit** 的 CORE-1a／1b 實作與新測試檔
  （`backend/core/config.py`、`backend/services/summarization.py`、`tests/test_t20260923_p7b_tail_coverage.py`）——
  僅**讀取**用以複核計畫主張（不視為任何驗收、不影響下述 gate）。

主要複核來源（全部實查，不引用二手結論）：

| 類別 | 來源 |
|---|---|
| 成本實測 | `data/cache/e2e/p7a-gemma31b-e7c/backend.log`（pipeline metrics）、`evidence/tail-extraction-probe/{run-01,run-02-tailhalf}/result.json`、`evidence/tail-extraction-probe/README.md` 附錄 A2–A4 |
| 程式碼 | `backend/services/summarization.py`（`:262-300`、`:339`、`:565-570`、`:596-620`、`:856-996`、`:1984-2004`、`:2449-2520`、`:2556-2577`、`:2817-2857`）、`backend/core/config.py:220-232`、`:653-666`、`backend/core/text_postprocess.py:680+`、`scripts/e2e/measure_record_quality.py`、`.env.example` |
| 交付與歷史 | `p7a-gemma31b-e7c/**`、`p6a-qwen27b-e6b/**`、另 3 場 gemma 的 `quality/coverage.json`、`progress-report.md` |
| 決定性離線複算 | 以 `uv run --frozen` 呼叫**產品自身** `SummarizationService._split_transcript_into_chunks`（純字串函式、0 次模型呼叫）重播分塊；另以產品估 token 函式複算切片（全部唯讀、無網路） |

---

## 1. Goal Baseline（先自權威來源重建；rev3 受同一組判準檢驗）

使用者要的是：地端模型（LM Studio 現況；日後 Ollama／Windows）紀錄品質與雲端落差縮小，
且機制**模型無關**、跨 OS、**不得再顯著拉長執行時間**（已抱怨 35 分鐘）；禁測 splash。
前波紀律仍有效：不改既有閘門門檻、不改 `off`、不改雲端提示詞、不改 `task_processor.py:259/262`；
單次抽樣不可歸因（≥2 次中位數或明確降級為觀察值）；不得宣稱地端已達雲端。

**由 Baseline 導出的 CORE 判準**：C1（CORE）槓桿打中已量測的兩大落差且可證偽；
C2（CORE）機制模型無關＋跨 OS 可稽核；C3（CORE）驗收在單場變異下站得住；
C4（界線）不得動既有門檻語意、`off`、雲端提示詞，且**時間成本必須被量測與登錄**。

---

## 2. I1–I8 關閉複核（不採信 rev3 §0 自述，逐項自行實查）

| 項 | 判定 | 本次實查證據 |
|---|---|---|
| I1 階段歸因／門檻校準 | **CLOSED（殘留已登錄）** | run-01（尾 25%）與 run-02（尾 50%，`00:22:28` 起）各 6/7 且命中集合不同（run-01 缺 F044〔不在切片〕有 F066；run-02 有 F044、缺 F066）⇒「萃取稀釋、小呼叫可救回」有實測；偵測器**整組撤除**（primary 設計無門檻、無視窗）；CORE-1a 筆記落檔（實作已存在、預設關）讓未來可在產品內歸因。殘留：單一視窗為機率性（文件已明說）、`notes→最終紀錄` 仍待 E2E（§5） |
| I2 更便宜槓桿 | **CLOSED** | CORE-1c 預註冊兩備援（尾段補萃取 +150.5 s 實測；尾段期望集合併入既有逐條對帳＝零新機制），並登錄 refine 輪上限 2 的殘留與 +17% 成本 |
| I3 去重結構性無效 | **CLOSED** | 本輪複核 `dedupe_cross_section_items`（`text_postprocess.py:680+`）確需「決議」＋「主席裁示事項」標題且 general-only；量尺 `cross_section_duplicate_pairs` 共用同一函式（`measure_record_quality.py:30/80/193`）⇒ 對 `section_meeting` 恆 0；rev3 已撤銷並改提示詞＋新觀測欄位、「3→0」自成功門檻移除 |
| I4 指標 vs 儀器 | **CLOSED（殘留＝I13）** | `measure_record_quality.py` 已新增 `full_document_item_count／avg_item_chars／near_duplicate_items`（observation-only、與 `instruction_item_count` 明文分離）⇒ §5 量測表每個目標都有定義＋儀器＋命令 |
| I5 三件事綁一起 | **CLOSED** | §4 拆 2a（三條各自開關）／2b；補強 builder `_build_record_refinement_message`（`:2500`）已列覆蓋 |
| I6 單場門檻／anti-gaming | **CLOSED（殘留＝I13）** | 主驗收改結構式（§5:139），`coverage_*` 降觀察值，反 gaming 禁令＋Stage 05 抽查；歷史包絡見 Q4 |
| I7 跨模型／OS 可觀測性 | **CLOSED（交付尚待實作）** | §8 三件套（skip-reason／engine 參數化／`.env.example`）＋Stage 05 顯式斷言；`.env.example` 現況 10 條 `LOCAL_LLM_*`、尚無新鈕——依計畫屬待辦 |
| I8 SUPPORTING 細節 | **CLOSED** | SUPPORTING-2 正式標語意變更＋預設關；SUPPORTING-1 作用域釘死；A 類佔位符明確 defer |

---

## 3. Top-down 審查

- **Goal alignment**：rev3 把 CORE-1b 由「加一次呼叫」改「**取代**單次大呼叫」，直接回應使用者時間主訴；
  仍鎖定兩個已量測落差、不做模型名分支、不動雲端（除下述 I10 的文字風險），未把主訴縮成好過的版本。
- **必要性**：CORE-1b 的必要性比 rev2 **更強**（probe 證明小呼叫可把尾段事實寫進筆記；成本實測排除 rev2 設計）；
  CORE-1a 是可歸因性（驗收與未來模型複驗的前提），非裝飾。
- **關鍵路徑**：probe（已完成）→ 結構性分塊 → E2E 結構式主驗收 → 備援二選一；次序正確。
- **gate／veto 比例**：新鈕預設開（行為變更）但可 `0` 回退、有停損；殘餘＝I9（停損時鐘與合取語意）。
- **失敗隔離**：逐槓桿可關、全關＝byte 級；備援成本已量測或已界定；語意回退走 Planner——良好。
- **設計經濟**：重用既有 splitter／零損串接／模板機制，新增僅一旋鈕＋一觀測鈕；代價是兩個近乎同義旋鈕（見 Q3 註記）。

## 4. Bottom-up 審查（逐條根因複核）

| 根因 | 複核結果 | 本次實查證據 |
|---|---|---|
| R1 萃取只跑一次 → 尾段稀釋 | 機制與量測**成立**；rev3 的修法在程式層可行 | E7C `chunk_count=1`、筆記 1,669 tokens、`extraction 340.6 s`；實測 splitter 在 ceiling 6,000 下＝**2 塊 [5,960, 5,918]**，chunk2 涵蓋 `00:22:09→00:44:54`（含 F044、F054–F066） |
| R1b 筆記未落檔 | 已補；CORE-1a 實作存在（`summarization.py:2817`、開關 `config.py:663`） | 落檔路徑實作為 `<DATA_DIR>/debug/extraction-notes/`（與計畫 §3 文字 `<DATA_DIR>/debug/<task>/notes-*.md` 不一致——非阻斷註記） |
| R1c 兩條救援路徑斷 | 與前審一致（期望集合來自 notes）`[VERIFIED（attempt-01 實查；本輪 spot-check :1984-2004）]` | 備援② 正是打這個缺口 |
| R2 逐條化／一事多寫 | 成立 | qwen E6b 全文 `N.` ＝**78**（我以 §5 命令複算）；「拆細」兩處措辭 `:291`／`:2484` 仍在（未改） |
| R3 佔位符落點 | 成立 | E7C `:3` 相鄰「（待確認）（待確認）」×1、表格「（待確認）：」×**11**；E6b 相鄰×**2**（皆與 §6 一致） |
| R4 時間碼 off-by-one | 成立（沿用前審抽樣） | 本波不做（BEST_EFFORT） |

---

## 5. 必答問題逐題

### Q1 CORE-1b「取代而非新增」的設計判斷與 `2 塊 ≈ 301 s` 推估

1. **數字來源複核（我自行核對）**：
   - `340.6 s`＝E7C `backend.log` pipeline metrics 的 `duration_seconds.extraction`（同場 `total 1,570.2`）`[VERIFIED]`。
   - `150.5 s`＝`run-02-tailhalf/result.json` 的 `elapsed_seconds`（usage prompt 6,152／completion 1,138）`[VERIFIED]`；
     run-01 未記錄秒數（README 附錄亦寫「未量」）——一致。
2. **「2 塊」是否真的成立（不只採信計畫文字）**：以產品 splitter 離線重播固定素材
   （est 總量 11,711）：ceiling 6,000 ⇒ **2 塊 [est 5,960／5,918]**；chunk2 起 `[00:22:09]`、迄 `[00:44:46-00:44:54]`，
   7,197 字，**F044／F054／F066 全在 chunk2** `[VERIFIED]`。
   chunk2 與 run-02 切片（7,064 字、產品估 5,827 tok）幾近同構 ⇒ 以 150.5 s 作「每塊 ≈150 s」代理**合理** `[INFERRED]`。
3. **推估是否可疑**：`2×150.5≈301 s` 的方向有兩層支持（兩個半份呼叫 < 一次整份呼叫；run-02 即半份量級實測），
   但我複核出三個**未計入項**：①每呼叫固定開銷重複（run-02 usage 6,152 vs 產品估 5,827 ⇒ 約 +325 tok/呼叫）；
   ②兩塊筆記的 completion 總量大概率 > 單次 1,669 tokens（run-02 單塊 1,138）⇒ decode 略增；
   ③overlap 使總輸入 +167 est（+1.4%，可忽略）。LM Studio 一次性 prefill 成本無法離線證實 `[UNKNOWN]`，
   但每呼叫 prompt 開銷與 decode 增量是保守方向。**務實區間：萃取階段 ≈ −12%～+5%（gemma）；且這是萃取階段，
   對總時僅 ≈ −2.5%（40 s／1,570 s）**。**qwen 的單次萃取只 166.8 s（E6b），半份呼叫未實測 ⇒ 方向未知** `[UNKNOWN]`。
4. **敏感性（我實測）**：ceiling 5,500／5,860 ⇒ **3 塊**（5500: [5459, 5379, 1397]）；6,000 ⇒ 2 塊；6,500／7,000 ⇒ 2 塊
   ⇒「每塊 ~6,000 ⇒ 2 塊」對**預設值 6,000** 才成立，屬刀鋒邊界。
5. **判定**：設計判斷**站得住**（rev2 的 +44% 是實測；rev3 是唯一同時「不增呼叫類型、不需偵測器、成本有量測代理」的路）。
   更穩健做法（建議，非 gate）：把「此素材＝2 塊、大小 5,960／5,918、chunk2 起 `00:22:09`」寫成**預註冊可證偽預測**
   （E2E 開場先核對），並把`−12%`表述為**推估值域**而非單點；成本以 `duration_seconds.extraction` 前後差對帳（§5 已列）。

### Q2 rev3 是否真的解掉 I1？CORE-1a＋CORE-1b 組合是否足夠？

- **階段歸因**：run-01／run-02 兩次實測＋（本次新增的）CORE-1a 產品內落檔，把「萃取漏 vs 生成漏」從不可證變成
  「當下可歸因、日後可重播」`[VERIFIED（probe）／INFERRED（產品內運作）]`；而且 rev3 的 primary 設計**不再依賴**歸因結論
  ——即使殘餘是生成階段，備援②已預註冊。I1 的原始兩個坑（假設未證、門檻不可校準）都已被移除或繞開 `[VERIFIED]`。
- **足夠性**：對「尾段事實進**筆記**」足夠（probe 為證）；對「尾段事實進**最終紀錄**」仍未證——這正是 §5 主驗收
  與備援②要處理的。組合（1a 觀測＋1b 結構分塊）**足夠作為本波的階段一**；不宣稱保證（run-02 自身仍缺 F066，
  計畫已以 ≥6/7 容錯與備援登錄）。

### Q3 新舊兩旋鈕並存是否互相覆蓋或令使用者困惑？

- **語意**：舊鈕 `LOCAL_LLM_CHUNK_INPUT_TOKENS_CEILING`（`config.py:220-232`；0＝依 context 推導＝不由本鈕給上限）；
  新鈕 `LOCAL_LLM_EXTRACTION_CHUNK_CEILING_TOKENS`（`:653-666`；0＝停用＝不由本鈕給上限）。兩者「0」**效果一致**、字面不同。
- **組合**：未 commit 實作採**依序 min**（`summarization.py:596-620`：先舊鈕、後新鈕且僅在夾緊時記 log）
  ⇒ 有效上限＝`min(context 推導, 舊(>0), 新(>0))`，**舊鈕語意未被覆寫** `[VERIFIED（實作）]`。
  但計畫 §3:84 的公式只寫 `min(既有 context 推導值, 本上限)`，**漏提舊鈕** ⇒ 文字與實作不一致（非阻斷，建議照實補齊）。
- **困惑點**：①名稱高度相似；②既有配置（舊鈕=0）的**實際行為**會因新鈕預設 6,000 改變——這是本波目的且可 0 回退，
  但 `.env.example` 應並列兩鈕並註明「有效值＝三者取 min、各自 0 的意義」；③有效值 log 只在「夾緊」時輸出（未夾緊時無聲，
  惟此時行為與本波前相同，可接受）。判定：**無互相覆蓋**；需一句明文＋文件（建議同批修）。

### Q4 §5 結構式驗收在單場變異 ±14–18pp 下是否可證偽？gaming 空間？

- **可證偽性（我以 5 場 gemma 實查重建歷史包絡）**：7 條尾段事實的單場命中數＝**3, 3, 1, 1, 0**
  （E1／E2／E5b／E6／E7C）；其中 F044 **0/5**、F066 **0/5**。要求「≥6/7 且 F044 命中」遠在雜訊包絡之外 `[VERIFIED]`；
  且 run-02（≈未來 chunk2 的輸入量級）實測恰為 6/7 且 F044 命中 ⇒ 門檻與「可達到性」前例對齊（餘 1 條容錯吸收 F066 型抖動）`[INFERRED]`。
  單場仍是上限（計畫保留「資源允許 +1 場」）；`coverage_*` 已降觀察值，不再用 ±pp 當判準——此設計正確。
- **gaming 空間**：分塊走**未修改**的產品提示詞；反 gaming 禁令＋「命中需附原文片段」＋Stage 05 抽查。
  殘餘風險＝判定者把**關鍵詞出現**當語意命中（checklist probes 是字面詞對）⇒ Stage 05 必須以 checklist
  `statement` 逐條做**語意**核對（不能只 grep probes）。此為 Stage 05 執行要求，不需改計畫。

### Q5 §7 停損與「取代」敘述是否自洽？時間成本漏算？

- 「唯一新增呼叫」字樣已確實移除（我 grep 無殘留）`[VERIFIED]`；§0b／§1／§3／§4 一致改口「取代」；
  未 commit 實作亦確為取代（同一路徑夾 chunk budget）`[VERIFIED]`。
- **不自洽（gate 項，見 I9）**：§7:158 的 baselines **混用時鐘**——gemma `1,570 s`＝`duration_seconds.total`（管線），
  qwen `1,023 s`＝**牆鐘**（`progress-report.md:35`；同場管線總時為 **769.6 s**）。且「P7-A 同模型場」對 qwen 不成立
  （P7-A 只跑 gemma；qwen 對照場是 P6-A E6b）。
- **另三個需如實登錄的點**：①`−12%` 僅萃取階段、gemma 專屬；對總時 −2.5%，在單場雜訊內不可辨識；
  ②停損是「時間 AND 品質」合取 ⇒ 純時間回退（如 qwen 萃取變慢但品質達標）不觸發任何槓桿決策——與使用者時間主訴不完全對齊；
  ③備援①啟用時 +150.5 s 對總時比例：gemma ≈ +9.6%（管線）、qwen ≈ +19.6%（管線）⇒ 若啟用須 Planner 顯式時間決策。
- **漏算的細項**：每呼叫固定開銷重複、兩塊筆記 decode 總量略增（皆已見 Q1，小）。判定：除 I9 外自洽。

### Q6 §8 是否足以讓未來 Windows＋Ollama 實機直接複驗？

- 機制層：分塊邏輯為純字串、位於引擎分派點之後；既有測試禁止 `platform.system`／`sys.platform` 等出現 `[VERIFIED（code）]`；
  新鈕與 CORE-1a 亦無引擎分支（實作複核）⇒ 模型／OS 無關性在**程式層**成立。
- §8 三件套＋Stage 05 斷言是**足夠的複驗前提**，但成立條件是：①兩支新鈕確實寫入 `.env.example`（尚未）並註明與舊鈕的 min 關係；
  ②skip-reason 覆蓋「所有新舊守衛」（計畫文字；實作待驗）；③Stage 05 對「守衛是否被評估／為何被跳過」做顯式斷言（計畫已載）。
  engine 參數化測試對分塊的價值主要是 plumbing（chunk 邏輯與引擎無關），可接受。
- 實機仍 `[UNVERIFIED]`（計畫如實登錄）⇒ 判定：**足夠**，無需新增 gate 條件。

---

## 6. 問題清單（I 編號續 attempt-01；僅列 gate 會用到的）

### I9（**阻斷**，§7 停損語意）baseline 時鐘混用＋對照場標示錯誤
- **問題**：`gemma 1,570 s`（管線 `duration_seconds.total`）與 `qwen 1,023 s`（牆鐘）不是同一把尺；
  qwen 的管線總時實為 769.6 s、gemma 的牆鐘實為 2,126 s。未來停損判定會系統性偏移。
- **為什麼是問題**：停損是 rollback 觸發器（gate/veto 語意）；混鐘會讓「+15%」在不同模型上等於不同嚴格度，
  且與 §5「`duration_seconds`×牆鐘並存」的量測表互相打架。
- **建議（最小）**：釘死單一時鐘並重列（例：牆鐘 gemma 2,126 s／qwen 1,023.2 s；管線 gemma 1,570.2 s／qwen 769.6 s）；
  標題改「P6-A E6b（qwen 對照場）」；備援①啟用時的總時影響如實登錄，超過 15% 需 Planner 決策。
- **影響**：§7；C3／C4 的時間紀律。

### I10（**阻斷**，CORE-2a 凍結介面）`:291` 措辭修改會連帶改動**雲端**萃取提示詞
- **問題**：`:291` 位於共用常數 `LOCAL_EXTRACTION_PROMPT`（`:262-298`），而
  `CLOUD_EXTRACTION_PROMPT = LOCAL_EXTRACTION_PROMPT + …`（`:300`，class body 串接）⇒ 照計畫文字「修 `:291` 措辭」
  將**byte 級改變雲端萃取提示詞**，違反 §1「不改雲端提示詞」與 §4「雲端輸出 byte 級不變」。
  （`:2484` 之 builder 為雲端共用 `:2449`／wrapper `:2556-2577`，需以 `mode=="local"` 閘門——既有模式見 `:2431-2447`。）
- **為什麼是問題**：雲端提示詞是本波的凍結介面（前波 handoff 明文）；實作者照文字做會踩線，或被迫自行發明機制。
- **建議（最小）**：明文指定機制——新紀律以**地端專屬常數**追加於 `_local_extraction_prompt()`（`:565-567`），
  共用常數保持 byte 不變；`:2484` 以 `mode=="local"` 條件追加（比照 `_local_tag_placement_rule`）；
  新增「雲端提示詞 byte 不變」單元測試。
- **影響**：§4／§9.1；C4；雲端回歸風險。

### I13（**重大**，驗收可證偽性）qwen 主驗收「朝目標移動」無可判定目標
- **問題**：§5:140 以「全文條目數與平均字數**朝目標移動**」為主驗收一部分，但未定義「目標」的數值或方向門檻
  ⇒ 不可證偽、與 I6 的關閉條件（每個驗收有定義＋儀器＋命令）不符（儀器已有、目標沒有）。
- **為什麼是問題**：Stage 05 對 qwen 只能各說各話；且此條與 gemma 的結構式門檻並列為主驗收，模糊會污染 verdict。
- **建議（最小）**：給數值方向（例：全文 leaf item 中位數 < 78 且平均條目字元 ≥ 基線；或明確降級為 observation-only）。
- **影響**：§5；Stage 05 判定。

### 非阻斷註記（建議同批修，非獨立 gate 條件）
- §9.1:176 「CORE-1b（…**尾段切片正確**、零損併入）」為 rev2 殘留字樣，應改為分塊契約
  （2 塊預期＋min 組合＋舊鈕語意不變＋關閉＝byte 級）。工作樹實測 6 個契約測試已存在於
  `tests/test_t20260923_p7b_tail_coverage.py`。
- 檔名標題仍寫「— rev2」（`:1`），與 `PLAN_REVISION: 3` 不一致。
- CORE-1a 落檔路徑計畫文字（`<DATA_DIR>/debug/<task>/notes-*.md`）與實作（`<DATA_DIR>/debug/extraction-notes/notes-*.md`）不一致，擇一對齊。
- §5 「全文條目數」定義 `^\d+\.` 與命令 `rg -c '^\s*\d+\.'` 字面略異（不影響判定）。
- 新 config 描述「只在『大 context 導致整份逐字稿只跑一次呼叫』時才生效」不精確：只要 context 推導值 >6,000 即生效
  （例：16K context 下的 8K 逐字稿會由 1 塊變 2 塊）。

---

## 7. 重送審最低要求（只列會改變 gate 的最小必要修正）

1. **I9**：§7 停損統一時鐘、重列 gemma／qwen baselines（並更正「P7-A 同模型場」為 P6-A E6b），
   備援①的時間影響如實登錄。
2. **I10**：CORE-2a 明文指定「雲端 byte 不變」的實作機制（`:291` 不得就地改共用常數；`:2484` 以 `mode=="local"` 閘門）＋雲端提示詞 byte 測試。
3. **I13**：qwen 主驗收給可證偽目標，或明確降 observation-only。

（非阻斷註記可一併修，但不構成獨立 gate 條件。）

---

## Gate

`GATE: PLAN_REVISION_REQUIRED`
