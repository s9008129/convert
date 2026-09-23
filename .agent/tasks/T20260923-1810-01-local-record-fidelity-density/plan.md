# P7-B 優化規劃：地端會議紀錄品質對齊雲端（模型無關）— rev2

- `TASK_ID`: T20260923-1810-01-local-record-fidelity-density
- `PLAN_REVISION`: 3
- `TASK_CLASS`: STANDARD（有語意變更，`REVIEW_REQUIRED: YES`）
- `REVIEW_REQUIRED`: YES
- `INDEPENDENT_ACCEPTANCE_REQUIRED`: YES
- `E2E_REQUIRED`: YES
- 分支：`fix/qwen-local-quality-parity`（rev1 `0254c7a` → rev2 依 attempt-01 審查修正
  → rev3 依 run-02 成本實測修正 CORE-1 設計，見 §0 最後兩列）
- 素材（固定）：`/Users/hsiaojohnny/Downloads/0903-科務會議.m4a`（sha256 `982151f4…2828`）、
  模板 `section_meeting`、`--quality-mode observe`
- 禁測：`qwen3.6-35b-a3b-splash`（僅可引用歷史數字）

## 0. rev1 → rev2 變更摘要（來源：`review/attempt-01/review.md`，gate `PLAN_REVISION_REQUIRED`）

| 審查項 | rev1 | rev2 修正 |
|---|---|---|
| I1 階段歸因未證實 | 以「萃取稀釋」為 CORE-1 前提，但筆記未落檔、無法區分階段 | ①新增**萃取筆記落檔**（零呼叫、additive）讓歸因可證；②CORE-1 **改為決定性結構補救，不再依賴偵測門檻**；③視窗由 25% 改為 **50%**（證據定界，見 §3） |
| I1 偵測門檻不可校準 | 以「尾段顯著詞命中率」當觸發條件 | **本輪實測否證**該訊號（`evidence/region-coverage-calibration/run-01.json`：四份紀錄全 0.00，無法區分 gemma 漏尾段與 qwen 有寫）→ **不做偵測**，改為「長逐字稿一律補一次尾段萃取」 |
| I2 更便宜的槓桿未列 | 無 | 明列**預註冊備援**：把尾段期望集合併入既有逐條對帳（零新機制）；並登錄 refine 輪上限 2 的殘留與 +17% 成本 |
| I3 去重對 section_meeting 結構性無效 | CORE-2.3「去重擴作用域」 | **撤銷**（`dedupe_cross_section_items` 需「決議＋主席裁示事項」標題且 `template.id != general` 直接回傳）→ 改為 CORE-2b：**提示詞反重複**＋**新觀測儀器**；確定性改寫**明確延後** |
| I4 指標與儀器不符 | 「78→≤45」用 ad-hoc grep | 每個目標釘死「定義＋儀器＋命令」（§5 量測表） |
| I5 三件事綁一起 | CORE-2 單一槓桿 | 拆為 2a（三條各自開關）／2b，各自可關可回退 |
| I6 單場門檻違反統計紀律 | 以單場 `coverage_core` 為成功定義 | **主驗收改結構式**（7 條尾段事實逐條＋原文片段）；`coverage_*` 降觀察值；加反 gaming 禁令與 Stage 05 抽查 |
| I7 跨模型／跨 OS 可觀測性 | 未處理 | skip-reason 觀測、engine 參數化測試、`.env.example` 文件化、Stage 05 顯式斷言 |
| I8 SUPPORTING 細節 | SUPPORTING-2 標為「確定性」 | 正式標為**語意變更**、自帶開關、**本波預設關閉**；SUPPORTING-1 作用域釘死；A 類佔位符明確 defer |

### 0b. rev2 → rev3（本節新增的實測推翻 rev2 的 CORE-1b 設計）

rev2 派出審查（attempt-02）後，同日完成兩個成本實測
（`evidence/tail-extraction-probe/README.md` 附錄 A2–A4）：

| 方案 | 萃取呼叫 | 實測／推估 | 相對現況 |
|---|---|---|---|
| 現況（E7C 實測） | 1 次（整份 11,711 est tokens） | **340.6 s** | — |
| rev2 的 CORE-1b（整份 ＋ 尾半段） | 2 次 | 340.6 ＋ **150.5** ＝ **491 s** | **+44%**（撞 §7 停損） |
| **rev3 的 CORE-1b（結構性分塊，每塊 ~6,000 tokens ⇒ 2 塊）** | 2 次（各約半份） | 150.5 × 2 ≈ **301 s** | **−12%**（推估） |

且 run-01／run-02 顯示**單一視窗的尾段萃取是機率性的**（兩次各 6/7，命中集合不同：
run-01 命中 F066 但缺 F044，run-02 命中 F044 但缺 F066）⇒
「在大呼叫之上再加一次尾段呼叫」既貴又不保證；**改為「取代」：讓每個區段都有自己的萃取呼叫**。
此即 v4.8.0 之前由 `LOCAL_LLM_CHUNK_INPUT_TOKENS_CEILING` 提供的結構保證（R1 的原始機制）。

## 1. Goal Contract（白話）

**主目標**：讓「地端模型」（LM Studio 或 Ollama，任意開源模型）產出的會議紀錄品質，
與雲端 Gemini 的落差縮小到使用者可接受的程度——具體是消掉兩個已量測到的最大落差：
① gemma 4 31B **漏掉整段會議後段的事實**；② qwen 3.8 27B **把紀錄拆成一堆破碎短句、重複寫同一件事**。

**不是目標**：不追求「地端＝雲端」；不改既有閘門門檻；不改 `off` 模式語意；不改雲端提示詞；
不做模型名分支；不引入新依賴；不改 `task_processor.py:259/262`。
**「可接受」的本波操作定義**：兩個已量測落差的代理指標＋結構式尾段檢查達標（§5），
**不宣稱全面品質對齊**。

**主要風險**：改流程 → 執行時間變長（使用者已抱怨 35 分鐘）。
因此本波**不得新增無條件的大量呼叫**；CORE-1b 採「**取代**單次大呼叫」的結構性分塊
（推估 −12%，見 §0b／§3），其成本仍必須以 E2E 實測登錄（§5 耗時列）。

## 2. 根因（皆有證據；全部模型無關）

| # | 根因 | 證據 | 歸因 |
|---|---|---|---|
| R1 | **長逐字稿的萃取只跑一次呼叫**（`chunk_count=1`）→ 尾段被稀釋 | `data/cache/e2e/p7a-gemma31b-e7c/backend.log`：`needs_chunking=False`、`chunk_count=1`、筆記 **1,669 tokens**（qwen 同素材 **3,967**）；gemma E6／E7C 缺同一組尾段事實（F044/F054/F055/F056/F060/F065/F066，時間戳 00:25:23–00:44:15） | 流程（v4.8.0 分塊上限改依 context 推導後，大 context 模型失去「每塊都有專屬呼叫」的結構保證） |
| R1b | **萃取筆記未落檔** → 階段歸因不可證 | 全 repo 無筆記落檔路徑（`rg write_text` 於 `summarization.py` 無命中的筆記輸出）；審查 I1 | 觀測缺口（本波補，additive） |
| R1c | 尾段缺漏**穿過整個流程**：兩條救援路徑都斷 | ①生成訊息以筆記為「涵蓋度檢查表」；②逐條對帳的議題／決議期望集合**取自已落檔的萃取筆記**（`summarization.py:1988-2002`）⇒ 筆記沒有尾段，兩者都不會要求 | 流程（設計缺口，非模型） |
| R2 | **生成階段逐條化過度＋一事多寫** | qwen E6b 交付 `.md`：全文 `N.` 條目 **78**、4,853 字、19% 無主詞指令句、7 對近似重複（3 對 r=1.0）；雲端 28 條／2,593 字；「盡量拆細」在 `summarization.py:291`（萃取）與 `:2484`（生成）兩處，未限定於待辦表格 | 提示詞（拆細規則外溢）＋補強輪整份重生成只增不併 |
| R3 | **佔位符落點錯** | E7C 交付 `.md:3` 相鄰重複「（待確認）（待確認）」×1、彙整表「辦理情形」`（待確認）：`×11 列；E6b 相鄰重複 ×2；雲端 0 | 模型填法＋缺確定性正規化（現行 `normalize_unfilled_placeholders` 只修骨架型佔位符行） |
| R4 | **出處時間碼 off-by-one**（地端 3 條／qwen 3 條）／雲端 100% `00:00:00` | Lorentz 抽樣；E7C `record_quality.tag_traceability`：`exact_tag_ratio 0.038`、`zero_time_tag_count 6` | 流程（讓模型憑記憶寫秒數） |

## 3. CORE-1：尾段覆蓋（決定性、非偵測式）

**設計原則（依審查 I1 ＋ run-02 成本實測）**：不做需要門檻校準的偵測器；且
**不「加」呼叫，而是「取代」呼叫**——把長逐字稿的一次大萃取，換成每個區段都有自己的呼叫
（結構性分塊），可關、可回退、成本可量測。

- **CORE-1a｜萃取筆記落檔（零呼叫、additive、預設關）**
  `LOCAL_LLM_DUMP_EXTRACTION_NOTES`（bool，預設 `False`）：開啟時把每份萃取筆記與零損串接後的
  合併筆記寫入 `<DATA_DIR>/debug/<task>/notes-*.md`。**不改任何產品輸出**；E2E 開啟，
  讓「尾段缺漏是萃取漏還是生成漏」以後可證、可重播（審查 I1 要求）。

- **CORE-1b｜結構性分塊萃取（取代單次大呼叫；不新增呼叫「次數」以外的成本）**
  新設定 `LOCAL_LLM_EXTRACTION_CHUNK_CEILING_TOKENS`（int，預設 `6000`；**0＝停用＝回本波前**）：
  實際分塊上限＝`min(既有 context 推導值, 本上限)`。既有 `LOCAL_LLM_CHUNK_INPUT_TOKENS_CEILING`
  的語意與預設**不動**（不改既有開關語意）。
  - **為何是「取代」而不是「新增」**：實測（§0b）整份 1 次＝340.6 s、尾半段 1 次＝150.5 s
    ⇒ 在大呼叫之上再加一次＝**+44%**（撞 §7 停損）；改成兩塊 ≈ 301 s（**−12% 推估**）。
    且 run-01／run-02 各只命中 6/7 且集合不同 ⇒ 加一次也不保證命中。
  - **它修的是 R1 的原始機制**：v4.8.0 把分塊上限改為依 context 推導後，大 context 模型
    （LM Studio 71,936 tokens）失去「每塊都有專屬呼叫」的結構保證；本上限把它找回來，
    **不需要偵測器、不需要模型名分支**，且每塊輸入變小（稀釋效應下降）。
  - **為何不是偵測式**：本輪以既有交付紀錄實測「罕見字窗」訊號 → 四份全 0.00
    （`evidence/region-coverage-calibration/run-01.json`）＝**否證**。
  - **契約**：觀測字串釘死 `結構性分塊萃取：上限 … tokens（來源 …）、實際分塊上限 …`；
    既有 `chunk_count=` 已在 pipeline metrics，維持不變。
  - **關閉＝byte 級回本波前**（`LOCAL_LLM_EXTRACTION_CHUNK_CEILING_TOKENS=0` 且 CORE-1a 不開）。

- **CORE-1c｜預註冊備援（依 E2E 結果二選一；兩者成本皆已實測或已界定）**
  - 備援①（分塊後尾段仍漏）：尾段專屬補萃取（視窗 0.5）——**實測 +150.5 s**（run-02），
    設定 `LOCAL_LLM_TAIL_EXTRACTION`（預設 False；只有 E2E 證實必要時才改預設）。
  - 備援②（筆記已有尾段、紀錄仍未寫入）：把尾段期望集合併入既有逐條對帳類別
    （零新機制、零新呼叫類型）。已知殘留：`LOCAL_LLM_MAX_REFINEMENT_ROUNDS` 預設 2
    （`config.py:280`）在 E7C 把核心未涵蓋停在 2 項；放行第 3 輪 ≈ +17% 單場時間，需顯式決策。

## 4. CORE-2：生成紀律與重複（拆成可各自回退的三＋一項）

### CORE-2a｜提示詞紀律（零呼叫；三條各自開關，預設 True）
只作用於**地端路徑**（`mode="local"`），雲端輸出 byte 級不變：
1. `LOCAL_LLM_ONEPERITEM_RULE`：正文**一案一條**——同一段發言、同一件工作不得拆成多條；
   「拆細」明文**只適用於待辦事項表格**（同時修 `summarization.py:291` 與 `:2484` 兩處措辭，
   並覆蓋**補強輪** builder `_build_record_refinement_message`，避免補強把紀律重置）。
2. `LOCAL_LLM_SPEAKER_DISCIPLINE_RULE`：正文主詞不得為「（待確認）」；講者不明時改寫為
   逐字稿可證的稱謂或整句改寫；推測語（可能是／應該是／建議）與 ASR 亂碼不得寫成事實。
3. `LOCAL_LLM_ANTI_DUPLICATE_RULE`：同一件事不得跨節重複（CORE-2b 的提示詞側）。

### CORE-2b｜重複：提示詞＋新觀測儀器（確定性改寫**延後**）
- 撤銷 rev1 的「`dedupe_cross_section_items` 作用域擴充」：該函式需要「決議」＋「主席裁示事項」
  標題且 `template.id != "general"` 直接回傳（`text_postprocess.py:680-712`）⇒ 對 `section_meeting`
  **結構性 no-op**；`measure_record_quality.cross_section_duplicate_pairs` 又共用同一函式 ⇒ 恆 0。
- 本波改為：①提示詞反重複（CORE-2a.3，零呼叫）；②在 `scripts/e2e/measure_record_quality.py`
  新增**模板無關**的觀測欄位（全文近似重複對數，≥0.80；`observation_only`，不參與 verdict）。
- **明確延後**：確定性近似去重的「改寫」動作（風險：誤刪事實、且無 no-regression 保護）。
  若延後則自 §5 成功門檻移除「3→0」，只留觀察值。

## 5. 量測表（每個目標釘死定義＋儀器＋命令；依審查 I4／I6）

| 目標 | 定義 | 儀器／命令 |
|---|---|---|
| 尾段 7 條事實 | 逐條判定（命中需附紀錄原文片段；未命中附原因） | 人工＋`rg` 於交付 `.md`；事實清單＝`quality/fact_checklist.json` F044/F054/F055/F056/F060/F065/F066 |
| `coverage_*` | 既有定義（67 條／core 28） | `scripts/e2e/measure_coverage.py`（**降為觀察值**） |
| 全文條目數 | 交付 `.md` 全文 leaf item（`^\d+\.`）數 | `rg -c '^\s*\d+\.'`；另存 `record_quality.json` 既有 `instruction_item_count` 作對照（定義不同，不得混用） |
| 平均條目字數 | 全文 leaf item 平均字元 | 同一支 ad-hoc 量測（腳本化後登錄） |
| 近似重複對 | 全文 ≥0.80 相似對數（新儀器） | `measure_record_quality.py`（本波新增 observation-only 欄位） |
| 相鄰「（待確認）」 | 相鄰重複計數 | `rg -o '（待確認）\s*（待確認）'` 計數 |
| 耗時 | `duration_seconds`（extraction／final_and_refine／total）× 牆鐘 | `backend.log`＋runner `run_notes.md` |
| DOCX | 交付檔存在且可開 | `ls *.docx`、`unzip -t` |

**E2E 場次**：gemma 4 31B 1 場（必）、qwen 3.8 27B 1 場（必，驗不回退）；資源允許再各 +1 場取中位數。
**主要驗收（結構式，不依單場覆蓋率）**：gemma 的 7 條尾段事實**命中 ≥6**且 **F044 命中**；
qwen `coverage_core` 不回退（≥27/28）且全文條目數與平均字數朝目標移動。
**反 gaming 禁令**：不得把 checklist／探針關鍵詞寫進任何提示詞；Stage 05 抽驗 2–3 條新命中事實的原文對照。

## 6. SUPPORTING／BEST_EFFORT

- **SUPPORTING-1｜佔位符正規化（確定性；開關 `LOCAL_LLM_PLACEHOLDER_NORMALIZE_EXT`，預設 True）**
  作用域**釘死**：①紀錄開頭欄位與標題行內的相鄰重複「（待確認）」收斂為一個（半形一併視為同一符號）；
  ②**僅**「決議事項辦理情形彙整表」第 2 欄儲存格的樣式（`（（待確認））`→`（待確認）`、半形冒號→全形）。
  不動其他表格、不動正文、不新增事實；雲端 byte 級不變（附測試）。
  量測：相鄰重複數（E6b 2／E7C 1 → 0）。
- **SUPPORTING-1b｜A 類佔位符（可填未填 6 處，5 處在「全體同仁」列）**：**明確 defer**。
  理由：確定性 fallback 會產生「未經逐字稿證實的內容」，違反本專案不捏造原則；本波只登錄為已知缺口。
- **SUPPORTING-2｜出處吸附加相似度（語意變更；開關 `LOCAL_LLM_TAG_SNAP_SIMILARITY`，本波預設 False）**
  正式標為**語意變更**（會改變標註落點）；本波只做離線量測，不改交付行為。
- **BEST_EFFORT｜雲端出處時間碼**：不做（需動雲端生成訊息；使用者未要求）。

## 7. 停損與回退

- 單場總時若比 P7-A 同模型場（gemma 1,570 s／qwen 1,023 s）**增加 ≥15%** 且 §5 主驗收未達
  ⇒ 停用 CORE-1b（`LOCAL_LLM_EXTRACTION_CHUNK_CEILING_TOKENS=0`）並改走 CORE-1c 備援。
  註：CORE-1b 的成本預期為 **−12%（推估，未實測）**；若 E2E 實測為增加，仍以 15% 為界。
- 每一槓桿可獨立關閉（1a／1b／2a.1／2a.2／2a.3／SUPPORTING-1／SUPPORTING-2）；
  全關＝byte 級回本波前。
- 任何語意變更若在 E2E 造成回退，走 Planner 重規劃，不由執行者就地改語意。

## 8. 跨模型／跨 OS（審查 I7）

- 全部槓桿位於 `_summarize_with_local_pipeline`（引擎分派點之後）⇒ LM Studio／Ollama 同碼路徑；
  **不得**出現 `platform.system`／`sys.platform`／`os.name`／`darwin`／`win32` 或模型名判斷（測試強制）。
- 新增：①所有新舊守衛的**跳過路徑記 `skipped_reason`**（observation-only，解「靜默停用」）；
  ②`engine="ollama"` 參數化單元測試（同一條程式碼路徑）；③`.env.example`＋CHANGELOG／手冊登錄新開關。
- Windows／Ollama **實機**仍 `[UNVERIFIED]`：Stage 05 對「守衛是否被評估／為何被跳過」做**顯式斷言**，
  讓未來 4090 實機可直接複驗。

## 9. 驗證計畫（Stage 04 → Stage 05）

1. 單元測試：CORE-1a（落檔／關閉＝無檔）、CORE-1b（觸發條件、關閉＝byte 級、尾段切片正確、
   零損併入）、CORE-2a（三開關各自生效、雲端不變、補強 builder 覆蓋）、SUPPORTING-1（作用域＋雲端不變）、
   engine 參數化、skip-reason 觀測。
2. 離線重播：以既有 artifact 驗證「關閉＝本波前」與「開啟＝預期差異」。
3. E2E（§5）：gemma 1 場＋qwen 1 場（同素材／同模板／`--quality-mode observe`）。
4. Stage 05 獨立複驗：結構式 7 條逐條證據＋DOCX 存在＋耗時對帳＋抽驗 2–3 條原文對照。
