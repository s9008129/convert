# Stage 02 獨立計畫審查 — attempt-03（受審 PLAN_REVISION 4）

## 0. 受審快照、覆核與角色宣告

- 受審對象：`.agent/tasks/T20260923-1810-01-local-record-fidelity-density/plan.md`（221 行、`PLAN_REVISION: 4`、檔頭 rev4）
- **實測 sha256**：`shasum -a 256` 於審查開始與 19:12 各量一次，皆為
  `dc11dd1167418ab9fbad8325b723566cd9e3df4d2db1cf8e1c3272c2994e08fc`，與指定預期值**一致**
  ⇒ 以本快照為受審對象（審查期間 plan.md 未被改寫；mtime 19:03:58）。`[VERIFIED]`
- 角色宣告：fresh context、**唯讀**。未修改 `plan.md`、任何產品程式碼、任何既有 `review/**`；未 commit；
  未執行模型呼叫／E2E／pytest 全 suite；未呼叫外部服務。本 attempt 目錄僅新增 `review.md` 與 `evidence.md`。
- 允許的複算工具（皆有使用）：`uv run --frozen` 呼叫**產品自身純字串函式**（0 模型呼叫）、
  既有離線儀器 `scripts/e2e/measure_record_quality.py`、`rg`／`python3` 字面統計。
- 審查期間工作樹有**未 commit** 實作，且**仍在變動**（19:05–19:14：`.env.example`、
  `backend/core/config.py`、`backend/services/summarization.py`（sha `461e78db…` → `480f04b0…`）、
  `backend/core/text_postprocess.py`、數個測試檔）。這些僅用於**複核計畫主張的機制可行性**，
  **不作為任何驗收證據**；程式碼行號引用一律以 commit `HEAD` 為基準，工作樹讀取處另註明讀取時 sha。
- 既有 `review/attempt-01`、`review/attempt-02` 僅用於 I 編號延續與題目理解，**未引用其結論當證據**；
  本檔所有數字皆自行實查（出處＝檔案＋行號或指令）。
- 詳細原始輸出（重播、byte 比對、儀器、日誌擷取）見同目錄 `evidence.md`。

---

## 1. Goal Baseline（先自權威來源重建；不採信 plan 自述）

使用者要的是：**地端模型（LM Studio 現況；日後 Ollama／Windows）的會議紀錄品質與雲端 Gemini 落差縮小**，
機制必須**模型無關、跨 OS**，且**不得顯著拉長執行時間**（使用者抱怨過 35 分鐘）；禁測
`qwen3.6-35b-a3b-splash`。前波紀律仍有效：不改既有閘門門檻、不改 `off` 語意、不改雲端提示詞、
不改 `task_processor.py:259/262`；單次抽樣不可單獨歸因；不得宣稱地端已達雲端。

由此導出的本輪審查判準（沿用本專案 harness 語意，並以 rev4 內容檢驗）：

- **C1（CORE）**：槓桿打中**已量測**的兩個最大落差（gemma 尾段缺漏、qwen 破碎／重複），且驗收可證偽。
- **C2（CORE）**：機制模型無關、跨 OS 可稽核，無平台／模型名分支。
- **C3（CORE）**：驗收在單場抽樣變異下站得住（結構式判定，不依單場覆蓋率）。
- **C4（界線）**：不得動既有門檻語意、`off`、雲端提示詞；**時間成本必須被量測與登錄**、成本失控要有出口。

---

## 2. 三項阻斷逐項獨立複核（本輪重點）

### 2.1 I9（§7 停損時鐘）— 判定 **CLOSED**

四個對照數字逐一實查，全部與 rev4 §0c／§7 的引用一致：

| 數字 | 實查出處（本人複核） | 值 |
|---|---|---|
| gemma 牆鐘 | `.agent/tasks/T20260923-1700-03-local-refine-no-regress/e2e/attempt-P7A-gemma31b-e7c/README.md:42`（runner 全程 wall `16:42:14 → 17:17:39`） | **2,125.5 s** ✓ |
| gemma pipeline `total` | `data/cache/e2e/p7a-gemma31b-e7c/backend.log:527`（`duration_seconds={'extraction': 340.6, 'merge': 0.0, 'final_and_refine': 1229.6, 'total': 1570.2}`；同場 `chunk_count=1`） | **1,570.2 s** ✓ |
| qwen 牆鐘 | `.agent/tasks/T20260922-2037-02-local-model-quality-parity/e2e/attempt-P6A-qwen27b-e6b/README.md:18`（`14:45:32 → 15:02:35＝1,023.2 s` runner wall；task 1,015.4 s） | **1,023.2 s** ✓ |
| qwen pipeline `total` | `data/cache/e2e/p6a-qwen27b-e6b/backend.log:287`（`total: 769.6`、`extraction: 166.8`） | **769.6 s** ✓ |

- §7:193-195 已**釘死牆鐘為唯一停損時鐘**、更正對照場標示為 P7-A E7C（gemma）／P6-A E6b（qwen）、
  明寫 pipeline `duration_seconds.total`「**僅作交叉核對**，不與牆鐘混算」⇒ 舊混鐘問題已消除。`[VERIFIED]`
- **算式複核**（`python3 -c`，見 evidence.md）：`150.5/1023.2=14.709%` ⇒ **+14.7%** ✓；
  `150.5/2125.5=7.081%` ⇒ **+7.1%** ✓；另複核 §0b／§3 一併引用的
  `340.6+150.5=491.1`（+44.2%）、`301/340.6=−11.6%≈−12%`、`(301−340.6)/1570.2=−2.52%≈−2.5%`，皆自洽。`[VERIFIED]`
- 附帶發現（**非阻斷**，見 I15）：§0b:38／§3:102 仍寫「+44%**（撞 §7 停損）**」——+44% 是**萃取階段**比例；
  換算 §7 新釘死的牆鐘只有 +7.1%（gemma）／+14.7%（qwen），**並未達 15%**。敘事句與新 §7 不一致，但**不影響任何操作規則**。
- 判定：**CLOSED**（阻斷解除）。

### 2.2 I10（雲端提示詞凍結）— 判定 **CLOSED**

逐點實查（①／②／③ 為使用者指定問題）：

1. **`:300` 是否真的串接共用常數**：`git show HEAD:backend/services/summarization.py` 顯示
   `LOCAL_EXTRACTION_PROMPT` 定義於 `:262-298`（`:291` 即「待辦清單要盡量拆細」行），
   `:300`＝`CLOUD_EXTRACTION_PROMPT = LOCAL_EXTRACTION_PROMPT + """…`（就地改字即 byte 級改動雲端）；
   工作樹（sha `480f04b0`）同構（`:289`／`:327`）。`[VERIFIED]`
2. **三支 mount 是否真的存在、可承載 local-only 追加**：
   - `_local_extraction_prompt()`（HEAD `:562-565`；工作樹 `:589-596`）＝地端萃取掛載點；
   - `_build_record_generation_message`（HEAD `:2449`；工作樹 `:2539`）與
     `_build_record_refinement_message`（HEAD `:2500`；工作樹 `:2591`）皆**已具 `mode` 參數**，
     既有 `_local_tag_placement_rule(mode, …)`（HEAD `:2439-2447`；工作樹 `:2508-2517`）就是
     「mode 非 local 回空字串」的既有模式（比照對象正確）；
   - 雲端 wrapper `_build_cloud_summary_message`／`_build_cloud_refinement_message`（工作樹 `:2648／:2657`）
     **不傳 mode** ⇒ 走預設 `"cloud"`；地端 `_resolve_final_generation_message`／
     `_resolve_final_refinement_message`（工作樹 `:2955／:2979`）傳 `mode="local"`。`[VERIFIED]`
   - **機制實證**（工作樹 sha `461e78db` 與 `480f04b0` 各跑一次，純函式、0 呼叫）：三開關 on/off 下
     `cloud_extraction`（sha12 `437f3c9c44df`）、`cloud_gen`（`1fc472614ae2`）、`cloud_refine`（`f5f0a8926c40`）
     **byte 完全相同**；`local_extraction／local_gen／local_refine` 隨開關改變；且**全關時
     `local_gen==cloud_gen`、`local_refine==cloud_refine`** ⇒「地端全關＝byte 級回本波前」可達成。`[VERIFIED（工作樹實作，僅機制可行性）]`
3. **是否還有其他地端紀律會誤改雲端路徑的位置**：逐一盤點——
   - refine 輪：地端補強走同一 mode-gated `_build_record_refinement_message`（工作樹 `:2979` 附近），
     雲端走 `_build_cloud_refinement_message`（工作樹 `:4823` 呼叫端）⇒ 無洩漏；
   - 逐條對帳（「議題／決議／數字／日期」期望集合）：是**確定性**的字串抽取（HEAD `:1988-2002` 等），
     產出「問題清單」後再餵入 refine builder，**本身沒有提示詞常數**⇒ 無需另設閘門、也不會誤改雲端；
   - legacy `_build_refinement_message`（工作樹 `:2636`）與雲端 wrapper 一樣走 default `"cloud"`；
   - `_build_notes_merge_message`／`_build_chunk_extraction_message` 未含新紀律；雲端萃取走
     `_cloud_extraction_prompt`（工作樹 `:605`）不含地端紀律。`[VERIFIED]`
- 附帶觀察（**非阻斷**，供 Stage 04，見 I18）：本地 context 規劃的 `refinement_overhead` 估算
  （`_resolve_merge_targets`，工作樹 `:783-790`）以**預設 mode** 呼叫 `_build_refinement_message`，
  未計入地端紀律區塊 ⇒ 估算略保守不足（大 context 無虞、小 context 有 fail-loud 保護）。
- 判定：**CLOSED**（阻斷解除）。

### 2.3 I13（qwen 驗收可證偽）— 判定 **CLOSED**

1. **基線 78／42.5 的獨立複算**：對 qwen E6b 交付
   `data/cache/e2e/p6a-qwen27b-e6b/backend_data/outputs/0903-科務會議_c605df1a.md` 跑
   `scripts/e2e/measure_record_quality.py`（命令見 evidence.md）⇒ `char_count 4,853`、
   `full_document_item_count 78`、`full_document_avg_item_chars 42.5`、`near_duplicate_items.count 3`
   （`exact_count 2`）；`rg -c '^\s*\d+\.'` 亦 **78**（與儀器同值）；`python3` 自算 78 條／平均 42.46
   （儀器四捨五入 42.5）。另複跑雲端 C5 紀錄（`data/cache/e2e/p3-cloud-baseline-05/…_ce67d0dc.md`）
   ⇒ **28 條／65.1 字**，與 §5「朝雲端密度（28／65.1）移動」一致。`[VERIFIED]`
   - 出處鏈完整：`evidence/quality-instrument-p7b/README.md:44`（基線表）、
     `scripts/e2e/measure_record_quality.py`（欄位實作）、`tests/test_record_quality_metrics.py:50-52`
     （schema 釘死）與 `:229-237`（`notes` 明訂新欄位「永不作為閘門」、與 `instruction_item_count` 不得混用）。
2. **門檻算術**：78→62 ＝ **−20.5%**（≥20% ✓）；42.5→48 ＝ **+12.9%**（≥12% ✓）⇒ 數值方向與百分比一致。`[VERIFIED]`
3. **可證偽性與 gaming**：儀器為確定性字面統計（difflib／regex，無 LLM）；目標與基線皆為已釘死的數值；
   §5:171 的 gemma 阻斷條款（7 條命中 ≥6 且 F044 命中）與 §5:172 的 qwen `coverage_core` 阻斷條款
   （≥27/28）都和 **§5:172-175 的密度目標（明標「可證偽、非阻斷」）清楚分離**；
   「未達⇒如實登錄為未達、列下一波決策輸入、不阻斷本波收尾」語意明確，Stage 05 可依同一儀器照判。
   gaming 面：密度目標本身非阻斷；退化風險（靠刪內容拉高平均字元）由阻斷的 `coverage_core` 與既有
   補強不回退守衛約束，另有 §5:176 反 gaming 禁令＋Stage 05 抽查。`[VERIFIED]`
- 判定：**CLOSED**（阻斷解除）。

---

## 3. rev4 新增內容複核（相對 rev3；含使用者指定的自洽性檢查）

### 3.1 §3 CORE-1b 預註冊預測：以產品 splitter 離線重播（0 呼叫）

以**產品自身** `SummarizationService._split_transcript_into_chunks`（純字串函式；`git diff` 顯示本波未
commit 變更未觸及該函式，HEAD 與工作樹同內容）重播固定素材
`data/cache/e2e/p7a-gemma31b-e7c/transcript.txt`（工作樹 sha `461e78db` 時執行，19:11）：

| 觀測 | rev4 §3:113-115 預註冊 | 我的實測 | 判定 |
|---|---|---|---|
| 全文 est tokens | 11,711 | **11,711** | 一致 |
| ceiling 6,000 塊數 | 恰 2 塊 | **2 塊** | 一致 |
| 各塊大小 | 5,960／5,918 | **5,960／5,918** | 一致 |
| chunk 2 起點 | `[00:22:09]` | `[00:22:09-00:22:30]` | 一致 |
| chunk 2 涵蓋事實 | F044／F054／F066 | 尾段 7 條時間戳**全部落在 chunk 2**（F044 `[00:25:23`、F054 `[00:32:33`、F066 `[00:43:03`，其餘 F055/F056/F060/F065 亦在；時間戳出處＝`.agent/tasks/T20260922-2037-02-local-model-quality-parity/quality/fact_checklist.json` 各 fact 的 `evidence`） | 一致 |
| 刀鋒邊界 | 5,500／5,860 ⇒ 3 塊 | **5,860 ⇒ 3 塊**（5,801／5,541／682）；**5,500 ⇒ 3 塊**（5,459／5,379／1,397） | 一致 |

- 前提成立性：E7C `backend.log:177` 顯示 `context_window=71936`、`estimated_tokens=11711`、
  `chunk_budget=65999`、`needs_chunking=False` ⇒ 新鈕 6,000 在此情境必然夾住（`min`）並真的分塊。`[VERIFIED]`
- 「本上限是刀鋒邊界 ⇒ 實測以 `chunk_count=` 為準並如實登錄」的但書正確、必要（6,000 與 chunk1 5,960
  只差 40 tokens，估算法與實際切法可能有小差；見 evidence.md 中工作樹實作附帶揭露的 `estimated_chunk_count`
  與實際塊數差異）。

### 3.2 §0c／§1／§4／§7／§9 自洽性與殘留舊字樣

- **§0c 表格**：三列（I9／I10／I13）修正敘述與我的實查一致；非阻斷註記 ①標題（`:1` 已改 rev4）、
  ②CORE-1a 落檔路徑（`:54-55` 已對齊工作樹實作 `<DATA_DIR>/debug/extraction-notes/notes-*.md`，
  實作見工作樹 `summarization.py:2889` 附近 `_dump_extraction_notes`）、④生效條件（`:111-112`）已落實；
  ③§9 契約文字已由「尾段切片」改為「分塊契約」（`:216-217`；全檔已無 rev2 殘留字樣，該詞僅出現在 §0c 修正說明）；
  ⑤值域與預測已新增，但 §3:102 仍保留「≈301 s（−12% 推估）」句——與 §0c⑤「改列值域」**不完全一致**
  （見 I17，非阻斷）。`[VERIFIED]`
- **§1:73** 值域「−12%～+5%」與 §3:116-118（萃取階段值域、qwen 方向 `[UNKNOWN]`、一律以 E2E 實測登錄）、
  §7:198 註記一致；**§4:138-146** 機制已由 2.2 的 byte 實證確認為可實作；**§7:193-200** 新停損時鐘與算式正確；
  **§9:216-217** 分塊契約文字（6000⇒2 塊、`min()` 舊鈕語意不變、0＝停用、關閉＝byte 級）與 §3 一致
  （唯 §3:60 公式仍簡寫為 `min(既有 context 推導值, 本上限)`、未列舊鈕夾取——舊鈕=0 時等價，
  屬文字精確度，見 I17）。`[VERIFIED]`

### 3.3 §5 量測表（定義＋儀器＋命令）與 §8 三件套

- §5 八列中 **7 列**具「定義＋儀器＋命令」；**第 4 列「平均條目字數」**儀器欄仍是
  「同一支 ad-hoc 量測（腳本化後登錄）」，未指向已存在、可重現、且產出基線 42.5 的儀器欄位
  `full_document_avg_item_chars`（見 I16，非阻斷）。第 1 列清單路徑 `quality/fact_checklist.json`
  未寫全（實際在 `.agent/tasks/T20260922-2037-02-local-model-quality-parity/quality/fact_checklist.json`）、
  第 3 列定義 `^\d+\.` 與命令 `^\s*\d+\.` 字面略異（我複算兩者對 E6b 同為 78，暫無判定風險）——同上併入 I16。
- §8 三件套**仍完整**：skip-reason 觀測（`:209`）、engine 參數化單元測試（`:210`）、
  `.env.example`＋CHANGELOG／手冊登錄（`:210`），加上 Windows／Ollama `[UNVERIFIED]` 的顯式斷言（`:211`）。
  實作側（供參，不當驗收）：工作樹已有 `skipped_reason=ceiling_disabled／context_budget_below_ceiling`
  日誌（`summarization.py` 工作樹 `:645` 附近）、新測試檔 `tests/test_t20260923_p7b_generation_discipline.py`
  含 `engine` 參數化與「不得平台／模型分支」測試、`.env.example` 工作樹已列新開關（HEAD 尚無，屬未 commit 進度）。`[VERIFIED]`

---

## 4. Top-down 審查

- **目標對齊**：CORE-1b 以「**取代**單次大呼叫」讓每個區段各有呼叫，直接打 R1 的結構缺口、也直接回應
  使用者時間主訴（不加無條件呼叫）；CORE-2a 打 R2（逐條化外溢）；皆模型無關。無「把主訴縮成好過的版本」跡象。
- **必要性**：CORE-1a 是可歸因性（萃取漏 vs 生成漏）的前提，零呼叫 additive；CORE-1b 是結構性修復；
  CORE-2b 只做提示詞＋觀測、確定性去重明確延後——必要性與設計經濟成立（重用既有 splitter／零損串接／
  mode-gated builder 模式；新增僅 2 鈕＋3 紀律開關＋1 觀測鈕＋1 觀測欄位）。
- **關鍵路徑**：probe（已做）→ 結構性分塊（已預註冊可證偽預測）→ E2E 結構式主驗收 → 備援二選一；次序正確。
- **gate／veto 比例**：阻斷集中在「gemma 結構式 ≥6/7＋F044」與「qwen `coverage_core` 不回退」；
  密度目標與近似重複皆降觀察值；停損與回退為可獨立關閉的槓桿——比例合理。**殘留（非阻斷）**：
  §7 停損為「時間 AND 品質」合取（純時間增幅 ≥15% 但驗收達標 ⇒ 無任何決策出口；見 I14）。
- **失敗隔離**：逐槓桿可關、全關＝byte 級；成本失控有停損＋備援組合 ≥15% 回 Planner 的明文；
  語意回退走 Planner 重規劃——良好。
- **未見新增阻斷級問題**：本輪新發現的 I14–I18 全屬非阻斷（文件一致性／實作提醒），
  不改變任何 gate／驗收語意。

---

## 5. Bottom-up 審查（R1／R1b／R1c／R2／R3／R4 逐條複核）

| 根因 | 複核結果 | 本次實查證據（本人） |
|---|---|---|
| R1 長逐字稿萃取只跑一次 → 尾段稀釋 | **成立** | E7C `backend.log:177`（`context 71936／est 11711／chunk_budget 65999／needs_chunking=False`）、`:527`（`chunk_count=1`）、`:249`（筆記 **1,669** tokens）；qwen 同素材 `p6a…/backend.log:155`（筆記 **3,967** tokens）、`:287`（`chunk_count=1`）；機制起點＝v4.8.0 改 context 推導（工作樹 `summarization.py:629-634` 註解；舊鈕 `config.py:220` 語意未動，`git diff` 僅新增） |
| R1b 萃取筆記未落檔 | **已補（可歸因）** | 工作樹 `_dump_extraction_notes`（`:2889` 起）寫入 `<DATA_DIR>/debug/extraction-notes/notes-*.md`、預設關（`config.py:664`）；與計畫 §3:54-55 一致 |
| R1c 尾段缺漏穿過兩條救援路徑 | **成立** | HEAD `:1988-2002`：議題／決議期望集合由**萃取筆記**抽取（`_extract_notes_topic_items／_extract_notes_decision_items`）⇒ 筆記沒有尾段，生成檢查表與逐條對帳都不會要求（備援②打的正是此缺口） |
| R2 逐條化過度＋一事多寫 | **成立** | 儀器複算 E6b：78 條／4,853 字；`research/format-density-comparison.md:37`（動詞開頭 19%＝15/78）、`:46`／`:94-100`（7 對近似重複、3 對 r=1.0）；「拆細」兩處＝HEAD `:291`（萃取）與 `:2484`（生成 builder 內） |
| R3 佔位符落點 | **成立** | `rg` 於交付檔：E7C `.md:3` 相鄰「（待確認）（待確認）」×**1**、`（待確認）：`×**11**；E6b 相鄰×**2**（全與 §6:184 一致） |
| R4 出處時間碼 off-by-one | **成立（本波不做，BEST_EFFORT）** | E7C `quality/record_quality.json`：`exact_tag_ratio 0.03846…`、`zero_time_tag_count 6`（計畫寫 0.038／6 ✓） |

落地可行性：三個 mount 點與 mode 閘門已實查（2.2）；分塊預測已離線重播（3.1）；
未 commit 測試檔（`tests/test_t20260923_p7b_tail_coverage.py`、`tests/test_t20260923_p7b_generation_discipline.py`）
已見對應契約測試（分塊夾取／0＝停用／落檔開關／雲端 byte 不變／三開關獨立／engine 參數化／無平台分支）
——屬實作進度、非驗收證據，但證明計畫要求可落地。`[VERIFIED]`

---

## 6. 問題清單（編號續 attempt-02；本次全部為**非阻斷**）

### I14（非阻斷；§7 合取語意殘留）
- **問題**：§7:196-197 停損是「牆鐘增加 ≥15%**且** §5 主驗收未達」的合取 ⇒ 純時間回退（驗收達標）沒有任何決策出口；
  與使用者「不得顯著拉長執行時間」主訴不完全對齊（attempt-02 已點到，rev4 未變更）。
- **最小修正**：加一句「牆鐘增幅 ≥15%（無論驗收結果）⇒ 回 Planner 決策；驗收未達時執行者可逕行停用」，
  或明文登錄為「已知接受的權衡」。不影響 gate。

### I15（非阻斷；§0b/§3「+44%（撞 §7 停損）」與新 §7 不一致）
- **問題**：§0b:38／§3:102 的 +44% 是**萃取階段**比例；換算 §7 釘死的牆鐘僅 +7.1%／+14.7%，**未達 15% 門檻**，
  「撞 §7 停損」的字面結論不成立（rev2 設計被放棄的真正理由是「+150 s 且不保證命中」，§7:199 已如實登錄）。
- **最小修正**：該兩處改寫為「萃取階段 +44%（換算牆鐘 +7.1%／+14.7%，已逼近 15% 門檻）」或引 §7 數值。不影響 gate。

### I16（非阻斷；§5 量測表細節）
- **問題**：①第 4 列「平均條目字數」儀器欄仍為「同一支 ad-hoc 量測（腳本化後登錄）」，未釘死到
  既有 `measure_record_quality.py` 的 `full_document_avg_item_chars`（基線 42.5 即出自該欄位）；
  ②第 1 列事實清單路徑 `quality/fact_checklist.json` 未寫全；③第 3 列定義與命令字面略異（E6b 複算同值，暫無風險）。
- **最小修正**：把第 4 列儀器改成 `scripts/e2e/measure_record_quality.py` 欄位名＋命令示例；
  清單路徑寫全 `.agent/tasks/T20260922-2037-02-local-model-quality-parity/quality/fact_checklist.json`。不影響 gate。

### I17（非阻斷；文件細節）
- **問題**：①§0c:58 稱「『2 塊 ≈ 301 s』改列值域」，但 §3:102 仍保留「≈301 s（−12% 推估）」句（與 §3:116-118 值域並存，
  實害低）；②§4:143 的 `:2484` 行號實為**生成** builder 內的「拆成多列」句（HEAD），補強 builder 定義在 HEAD `:2500`——
  符號名已明列、實作不受影響；③§3:60 公式未列舊鈕夾取（舊鈕=0 時等價）。
- **最小修正**：行文對齊（301 s 句加「值域見下」或改寫；行號改「HEAD 基準、實作時以符號名為準」；公式補三項 min）。不影響 gate。

### I18（非阻斷；Stage 04 實作提醒）
- **問題**：本地 context 規劃的補強輪開銷估算（`_resolve_merge_targets`，工作樹 `:783-790`）以預設 `mode="cloud"`
  呼叫 `_build_refinement_message`，未計入地端紀律區塊（及既有 W2 標註導引）⇒ 對地端補強 prompt 的預算略低估；
  大 context（E2E 71,936）無虞，小 context 邊界有 fail-loud 保護。
- **最小修正**：Stage 04 將該估算改傳 `mode="local"`（或明文接受此低估並記錄）。不影響 gate。

---

## 7. 重送審最低要求

**無。** 三項阻斷（I9／I10／I13）經獨立實查皆已實質關閉；I14–I18 均為非阻斷的文件一致性／實作提醒，
不改變任何 gate、驗收或停損語意。建議 Stage 04 一併處理 I16／I18（成本 1 行內），I14／I15／I17 可於同批順修。

---

GATE: PLAN_APPROVED
