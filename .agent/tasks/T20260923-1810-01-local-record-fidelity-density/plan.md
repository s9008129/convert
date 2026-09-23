# P7-B 優化規劃：地端會議紀錄品質對齊雲端（模型無關）

- `TASK_ID`: T20260923-1810-01-local-record-fidelity-density
- `PLAN_REVISION`: 1
- `TASK_CLASS`: STANDARD（有語意變更，`REVIEW_REQUIRED: YES`）
- `REVIEW_REQUIRED`: YES
- `INDEPENDENT_ACCEPTANCE_REQUIRED`: YES
- `E2E_REQUIRED`: YES
- 分支：`fix/qwen-local-quality-parity`（HEAD `c13fb41`）
- 素材（固定）：`/Users/hsiaojohnny/Downloads/0903-科務會議.m4a`、模板 `section_meeting`、`--quality-mode observe`
- 禁測：`qwen3.6-35b-a3b-splash`（僅可引用歷史數字）

---

## 1. Goal Contract（白話）

**主目標**：讓「地端模型」（LM Studio 或 Ollama，任意開源模型）產出的會議紀錄品質，
與雲端 Gemini 的落差縮小到使用者可接受的程度——具體是**先消掉兩個已量測到的最大落差**：
① 有些模型（如 Gemma 4 31B）**漏掉整段會議後段的事實**；② 有些模型（如 Qwen 3.8 27B）
**把紀錄拆成一堆破碎短句、還重複寫同一件事**。

**不是目標**：不追求「地端＝雲端」；不改任何既有閘門門檻；不改 `off` 模式語意；
不做模型名分支；不引入新依賴；不改雲端路徑的輸出行為。

**成功的樣子**（可量測，同一把尺：`fact_checklist.json` 67 條／core 28）：
- Gemma 4 31B：`coverage_core` 0.75（21/28）→ **≥0.86（24/28）**，且缺失不再集中在尾段。
- Qwen 3.8 27B：`coverage_core` 維持 ≥0.96（不得回退），正文條目數 78 → **≤45**、
  平均條目字數 42.5 → **≥50**、逐字重複對 3 → **0**。
- 交付 DOCX 正常產生、runner 16/16 checks PASS、無「會議紀錄生成失敗」。

**主要風險**：改流程 → 執行時間變長（使用者已抱怨 35 分鐘）。
因此所有新增的 LLM 呼叫都必須是**有條件的**（偵測到缺口才補），不得變成每場固定多跑。

## 2. 根因（皆有證據，全部模型無關）

| # | 根因 | 證據 | 歸因 |
|---|---|---|---|
| R1 | **長逐字稿的萃取只跑一次呼叫**（`chunk_count=1`），長會議尾段被模型自然稀釋 | `data/cache/e2e/p7a-gemma31b-e7c/backend.log` 的 `chunk_count=1`、萃取筆記 **1,669 tokens**（qwen 同素材 3,967）；gemma 兩場（E6／E7C）**缺同一組**尾段事實（F044/F054/F056/F060/F065/F066，逐字稿時間戳全落在 00:25–00:43） | 流程（v4.8.0 把分塊上限改為依 context 推導後，大 context 模型失去「每塊都有專屬呼叫」的結構保證；`LOCAL_EXTRACTION_PROMPT` 的「若**這一段**沒有明確交辦…」正是為分塊設計） |
| R2 | **生成階段逐條化過度＋一事多寫** | qwen `78 條`／平均 42.5 字／19% 無主詞指令句；7 對近似重複其中 3 對 r=1.0；雲端 28 條、gemma 23 條 | 提示詞（`LOCAL_EXTRACTION_PROMPT` 明文「待辦清單要盡量拆細」外溢到正文）＋補強輪整份重生成只增不併 |
| R3 | **佔位符落點錯**：gemma 把彙整表「辦理情形」欄 11/12 列填成「（待確認）：」，且開頭出現相鄰重複「（待確認）（待確認）」 | `data/cache/e2e/p7a-gemma31b-e7c/...md` L15–L25；E6b 亦有 2 處相鄰重複（雲端 0 處） | 模型填法＋缺確定性正規化 |
| R4 | **出處時間碼 off-by-one**（地端）／**雲端 100% `00:00:00`** | Lorentz 抽樣：gemma 3 條、qwen 3 條明顯錯位；雲端 29 個時間碼 distinct=1 | 流程（讓模型自己憑記憶寫秒數） |

## 3. 槓桿（依「價值 ÷ 風險」排序；每項標記是否語意變更）

### CORE-1｜尾段覆蓋守衛（R1）— **語意變更，需審查**
- 內容：地端萃取完成後，對「逐字稿時間軸最後 N%（預設 25%）」做**確定性命中檢查**——
  以該區間逐字稿段落的顯著詞（數字／專有名詞／罕見詞）字面比對萃取筆記；
  命中率低於門檻 ⇒ **只對該區間再跑一次萃取**並零損併入筆記（既有整併路徑）。
- 為何模型無關：判定是字面統計，不含模型名或模型特性假設。
- 為何低成本：多一次呼叫**只在偵測到缺口時**發生（qwen 這類模型不會多跑）。
- 契約：新增 `LOCAL_LLM_TAIL_COVERAGE_GUARD`（bool，預設 True）與門檻設定；
  關閉＝逐字等同本波前。觀測字串釘為契約（比照 P7-A）。
- 風險：門檻太鬆會誤觸發（多花時間）、太緊抓不到 gemma。以既有兩場 gemma 證據離線校準。

### CORE-2｜生成紀律（R2）— **語意變更，需審查**
- 內容（三件，皆在地端路徑）：
  1. 生成訊息補「**一案一條**：同一段發言、同一件工作不得拆成多條；正文以『一則發言一件事』為上限」；
     「拆細」明文限定在**待辦清單表格**，不得外溢到正文。
  2. 生成訊息補「正文主詞不得為『（待確認）』；講者不明時改寫為逐字稿可證的稱謂或整句改寫」、
     「推測語（可能是／應該是／建議）與 ASR 亂碼不得寫成事實」。
  3. 跨節近似去重（`dedupe_cross_section_items`）作用域由 `general` 擴到 `section_meeting`
     （≥0.80 同句只留一處）；先以**觀測**模式量測再決定是否常開。
- 為何模型無關：文字契約＋確定性去重，無模型名分支。
- 量測：`instruction_item_count`（78→）、條目平均字數、`cross_section_duplicate_pairs`。

### SUPPORTING-1｜佔位符正規化（R3）— **確定性後處理（低風險）**
- 內容：`normalize_unfilled_placeholders` 擴充——在**紀錄開頭欄位與標題行**內，
  把相鄰重複的「（待確認）」收斂為一個（半形 `(待確認)` 一併視為同一符號）；
  彙整表「辦理情形」欄的樣式正規化（`（（待確認））`→`（待確認）`、半形冒號→全形）。
- 不變式：只動紀錄開頭欄位／標題行與表格儲存格樣式，**不動正文內容**、不新增事實、
  不改變雲端輸出（雲端無此類樣式 ⇒ byte 級不變）。
- 量測：相鄰重複數（E6b 2／E7C 1 → 0）。

### SUPPORTING-2｜出處吸附（R4）— **確定性（既有機制的門檻校正）**
- 內容：`snap_source_tags_to_transcript` 只做「吸附到最近段落起點」；
  增加「**同句內容與候選段落相似度**」的確認，避免 off-by-one。
- 若離線證據不足則降級為 **BEST_EFFORT**，不阻擋 CORE。

### BEST_EFFORT｜雲端出處時間碼（R4 雲端側）
- 雲端路徑目前 100% `00:00:00`；修它需要動雲端生成訊息（使用者未要求、且屬雲端品質）。
- 本波**不做**，只在報告中列為下一步建議。

## 4. 關鍵路徑（先做會動到「主結果」的）

1. CORE-1（尾段覆蓋守衛）：離線校準門檻 → 實作 → 單元測試 → gemma 實機 E2E。
2. CORE-2（生成紀律＋去重）：實作 → 單元測試 → qwen 實機 E2E（不得回退）。
3. SUPPORTING-1（佔位符正規化）：實作 → 單元測試（含雲端 byte 不變）→ E2E 觀察值。
4. E2E 驗收：兩顆模型各一場（`section_meeting`／`observe`）＋ Stage 05 獨立複驗。
5. 跨 OS：Windows＋Ollama 由 `research/crossos-ollama-audit.md` 稽核；實機仍 `[UNVERIFIED]`。

## 5. 界線與停損

- 不改：`LOCAL_LLM_RECORD_COVERAGE_*` 既有門檻語意、`off` 模式、`task_processor.py:259/262`、雲端提示詞。
- 新增呼叫必須有條件；若某槓桿讓單場時間增加 >15%，必須回到本規劃重新決策。
- 任何槓桿若在離線校準中**無法重現**預期效果，降級為 BEST_EFFORT 並如實登錄，不得為了達標而調門檻。
- 若 E2E 顯示 core 覆蓋回退，先還原該槓桿（每個槓桿各自可關）。

## 6. 驗收（Stage 05，獨立執行）

- 指令（固定）：runner 以 `--audio …0903-科務會議.m4a --template section_meeting --quality-mode observe`。
- 必要證據：`run_summary.json`（verdict／16 checks）、`coverage_core`／`coverage_all`、
  `record_quality.json`、DOCX sha256／bytes、backend.log 的守衛字串、耗時（runner wall／task）。
- 對照：本規劃 §1 的成功門檻＋本波前後同模型同素材的單場差；
  並**必須**揭露單場變異（qwen 18pp／gemma 14pp 實測）。
