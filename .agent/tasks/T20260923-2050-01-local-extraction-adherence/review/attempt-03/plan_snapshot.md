# P7-C 優化規劃：地端萃取與生成遵循度（模型無關）— rev3

- `TASK_ID`: T20260923-2050-01-local-extraction-adherence
- `TASK_MODE`: REVIEW_REVISION
- `PLAN_STATUS`: READY_FOR_REVIEW
- `PLAN_REVISION`: 3
- `TASK_CLASS`: STANDARD（有語意變更 ⇒ `REVIEW_REQUIRED: YES`）
- `REVIEW_REQUIRED`: YES
- `INDEPENDENT_ACCEPTANCE_REQUIRED`: YES
- `E2E_REQUIRED`: YES
- `ACCEPTANCE_MODE`: E2E
- 前波：`T20260923-1810-01-local-record-fidelity-density`（P7-B，rev4）。前波**兩條阻斷條文皆未達**，
  已依 §7 提出 `escalation.md`（`ab2528b`），本波即為該升級要求的重規劃。
- 分支：`fix/qwen-local-quality-parity`（HEAD `ab2528b`）
- 素材（固定）：`/Users/hsiaojohnny/Downloads/0903-科務會議.m4a`（sha256 `982151f4…2828`）、
  模板 `section_meeting`、`--quality-mode observe`
- 禁測：`qwen3.6-35b-a3b-splash`
- 量尺（既有、不改定義）：`scripts/e2e/measure_coverage.py`（coverage-1.0.0）、
  `scripts/e2e/measure_record_quality.py`、`quality/fact_checklist.json`（sha256 `cf012d1f…`）

## 0. rev2 變更紀錄（回應 Stage 02 attempt-01 的 I1–I13）

審查 artifact：`review/attempt-01/review.md`（`GATE: PLAN_REVISION_REQUIRED`，受審快照 `325e8487…`）。

| 項 | 處置 | 位置 |
|---|---|---|
| **I1 成本自相矛盾** | 廢除 `≤1,500 s`／`≤2,600 s` 兩個無推導值，改為「**實測基線＋已量測增量**」推導的絕對上限，並明示時鐘來源＝`run_summary.json` 的 `started_at`→`finished_at`（牆鐘），不可用 pipeline total | §5 CORE-E、§6 |
| **I2 n=2 中位數語意不明／容差 < 噪聲帶** | 全部阻斷條文改為**集合語意**（「2 場皆 ≥地板」＋「至少 1 場 ≥目標」），容差以本專案自訂噪聲帶（±10pp；28 條制 ≈3 條）為下限，並登錄「<10pp 的差異 n=2 不可判定」 | §5 |
| **I3 CORE-2a 與自身證據相反** | C2a 目標改對準 **gemma F048 型**（事實級期望集合）；qwen 型（遵循度）改由**新增 C2c 零呼叫槓桿**承擔，C2b 不再當唯一手段 | §3 CORE-2 |
| **I4 主槓桿未釘死值／預設值互斥** | plan 內**寫死** E2E 配對 `ceiling=4500`、`CALL_BUDGET=4`；定義 `CALL_BUDGET` 語意＝**總萃取呼叫數上限**、**預設 0（不限制）**；引用重播證據的 5 條預註冊（含 FALSIFIER）；加註碎片塊護欄 | §3 CORE-1、§5、§11 |
| **I5 gemma 腿缺整體保真度地板** | 新增 **CORE-B**（gemma `coverage_core` 地板＋重現條款）與「不得再回退」觀察清單（F048 型） | §5 |
| **I6 `LOCAL_LLM_TAG_SNAP_SIMILARITY` 不存在** | S2 改用**正確的既有**槓桿名稱（模組常數 `TAG_SNAP_TOLERANCE_SECONDS`／`TAG_SNAP_MAX_SHIFT_SECONDS`、`LOCAL_SOURCE_TAG_DIVERSIFY_ENABLED`），並註明若需新旋鈕屬語意變更、本波不做 | §4 S2 |
| **I7 R1 引註階段錯誤** | 改引萃取階段 diagnostics（`19:34:00` completion 1,356／`19:37:03` 1,248、`max_tokens=8192`） | §2 R1 |
| **I8 R4 標籤過強** | R4 降為 `[SUPPORTED]`，補註 E5／E5b 的 SHA 差異與中間 commit 的 byte 等價性 | §2 R4 |
| **I9 CORE-C 升級未推導／名實不符** | 密度改為**阻斷地板＋重現條款**並寫明升級理由（本波兩條新槓桿有回吐密度風險）；近似重複對改為**純觀察值**（明文：不得單獨通過或否決） | §5 CORE-D |
| **I10 C3 缺安全網** | 加入 registry 白名單優先、候選定義、唯一性判準（沿用既有近音原語）、替換 log／計數與 `skipped_reason`、反 gaming 斷言 | §3 CORE-3 |
| **I11 C3 評法與場次預算不相容** | 閘門 4 場一律 **C3 關**；C3 開／關配對場降為 SUPPORTING（資源允許才跑） | §3 CORE-3、§9 |
| **I12 缺「E2E 前先 commit」** | §8 加入顯式前置步驟（runner 對 dirty worktree fail-closed） | §8 |
| **I13 已量測的便宜槓桿未列** | 新增 §11「方案 A（尾段補萃取）vs C1b（全域細塊）」比較與決策理由、備援啟用條件 | §11 |

**受審快照規則**：本 rev2 的指紋以 `shasum -a 256 plan.md` 於 attempt-02 開審時登錄；rev1 的審查
（`review/attempt-01/`）為 append-only 歷史，不覆寫。

## 0.1 rev3 變更紀錄（回應 Stage 02 attempt-02 的 RV-001–RV-004）

受審來源：`review/attempt-02/review.md`（rev2 SHA-256：`32e6ac0fe2473a951cc8d1e8217ffa1385722bdb5b59f302f726bf608390b1d2`）。

| 項 | rev3 處置 | 位置 |
|---|---|---|
| **RV-001 狀態／閉合語意不足** | 依 workflow-routing.md §7 增加逐項驗證矩陣、全庫測試基線政策、Stage 04 execution.md 與 Stage 05 不可變快照及 PASS／FAIL／BLOCKED／NOT_RUN／重規劃／閉合路由 | §8 |
| **RV-002 重播文件引用過寬** | C1b 僅引用重播 README 的塊數／事實落點及預測項 1–3、5；明示 §3 項 4 的 `CALL_BUDGET=2` 為舊預測、非本計畫依據；rev3 預設 `0`、E2E=`4` 為唯一有效值 | §3 CORE-1、§5 |
| **RV-003 Qwen 成本上限依據不等價** | 以 P7-B Qwen 同音檔／同地端路徑實測的完整萃取 427.6 s 作為保守新增萃取 allowance（不再借用 Gemma 的 150.5 s）；Qwen 上限修訂為 2,650 s，推導見 §5 | §5、§9、§11 |
| **RV-004 萃取呼叫逾限語意未定** | 改為 provider I/O 前全有或全無預檢；超限時只中止該次本地摘要、不丟塊、不消耗部分筆記、不產出可接受的部分紀錄；增加零呼叫邊界測試及 Stage 04/05 路由 | §3 CORE-1、§6、§8 |

僅更新本任務 canonical `plan.md`；不改 attempt-01／02、重播 evidence、prep 落點圖或產品碼。rev3 必須由全新 Stage 02 attempt-03 審查；舊核准／快照不可沿用。

## 1. Goal Contract（白話）

使用者要的是：**地端模型（LM Studio／日後 Ollama＋Windows）生出來的會議紀錄，跟雲端 Gemini 不要差太多。**
P7-B 已證實：**「密度／可讀性」可以靠機制大幅拉近**（qwen 條目 78→37、平均 42.5→61.2 字；
gemma 平均 49.7→60.7 字，字數 2,576 vs 雲端 2,593），但**「有沒有把會中講的事寫進去」仍是主要落差**：

| 模型 | P7-B 實測 | 未達條文 |
|---|---|---|
| gemma 4 31B | 核心覆蓋 21/28 → **25/28（+19.0%）** | §5 主驗收：尾段 7 條結構命中 **2/7**、**F044 未命中**（阻斷） |
| qwen 3.8 27B | 密度 78→37 條（−52.6%）、42.5→61.2 字（+44.0%） | `coverage_core` **27/28 → 25/28**（阻斷）；牆鐘 **+77.4%**（§7 觸發） |

本波（P7-C）要解決的就是這兩個缺口，且**不得**讓已拿到的密度與覆蓋成果退回去。
**非目標**：不追求「地端＝雲端」的全面等價；不宣稱已達雲端水準。
**模型無關**：不得出現模型名／平台名分支；所有槓桿關閉後須 byte 級回前波行為。

## 2. 根因（皆有 P7-B 實測證據）

- **R1｜萃取側區塊內漏寫（gemma）** `[VERIFIED]`
  gemma E8 的萃取筆記（`data/cache/e2e/p7b-gemma31b-e8/backend_data/debug/extraction-notes/notes-20260923-193703-2c452049.md`）
  經 `rg` 實查：**無**「政治」（F044 的實質內容）、**無**「禮堂／走廊／三樓」（F055）、
  **無**「新聞行銷處／局長室」（F066）；「選舉」只出現在「日期：未提及（僅提到近期為年底選舉前）」。
  ⇒ 這三條**不是生成階段掉的，是筆記根本沒抓到**。該場萃取階段 diagnostics 為
  `completion_tokens=1,356`（`19:34:00`）／`1,248`（`19:37:03`）、`max_tokens=8192`、
  `finish_reason=stop` ⇒ **排除 max_tokens 截斷**（註：`235–331` 是「逐字稿語意校正」階段的數字，
  非萃取階段——rev1 引註錯誤，已在 rev2 更正）。
  `chunk_count=2` 已生效 ⇒ 排除「沒有分塊」。離線重播另證實：**ceiling 6,000 時該塊（5,918 tokens）
  已含全部 7 條尾段 probe 的字面**，模型卻只寫到 `[00:32:34]` ⇒ 結論：**單次呼叫對 ~5,900 token 區塊的覆蓋不足**。
- **R2｜生成側遵循度（qwen）** `[VERIFIED]`
  qwen E8 漏掉的 F019／F056 **在它的萃取筆記裡本來就有**（Stage 05 指出 notes L47／L199，
  且 F056 的敘述比 gemma 的交付紀錄更精確）；補強第 2 輪的問題清單也明文寫了
  「議題遺漏：土地稅科倉庫漏水與土地卡重印」，模型仍未寫入 ⇒ **是「寫不出來」而非「沒聽到」**。
  **界線（rev2 修正）**：這代表瓶頸是**遵循度／收斂**，**不是**「清單裡沒有這一項」⇒
  只加一類同粒度期望（rev1 的 C2a）**不會**改變這型失敗（見 §3 CORE-2 的重指向）。
- **R3｜成本結構改變（qwen）** `[VERIFIED]`
  qwen 牆鐘由 E6b 1,023.2 s 升至 1,814.9 s（+77.38%）。機制是**呼叫數增加**
  （萃取 1→2、補強輪 1→2、logical_generations 3→5），不是單次變慢。
  另實測**每輪補強 ≈360 s**（`20:26:56`→`20:32:56`）、**單次尾段萃取 ≈150.5 s**、
  **整份萃取 ≈340.6 s**（`evidence/tail-extraction-probe/README.md` A4）⇒ 本波成本上限即以此推導。
- **R4｜門檻在實測變異內，單場不可判定** `[SUPPORTED]`
  qwen 歷史擺動 `0.7857 ↔ 0.9643`（18pp）。**標籤降級理由（rev2）**：兩場 SHA 不同
  （E5 `ce99502` vs E5b `eaa4f45`），中間有 `58e65de`；實查 `data/glossary/*.txt` **兩檔皆無 BOM**
  ⇒ 該 commit 對本場行為 byte 等價，擺動仍可視為抽樣變異 ⇒ 結論可用，但字面「同 build」不成立。
  **對本波的意義**：28 條制的 ±10pp ≈ ±3 條 ⇒ n=2 只能偵測 >10pp 的真回退（見 §5）。
- **R5｜既有標註門檻回退（gemma）** `[VERIFIED]`
  `on_start_tag_ratio` 0.9615（E7C）→ 0.84（E8）、`on_start_tag_ratio_excluding_zero` 0.95 → 0.8095；
  Stage 05 另發現 F054 的標註 `00:41:51` 與來源段 `[00:32:34-00:33:07]` 不符。

## 3. CORE（本波主路徑）

### CORE-1｜萃取側：把「區塊內覆蓋」變成可驗、可調（模型無關）

- **C1a 觀測先行**：`LOCAL_LLM_DUMP_EXTRACTION_NOTES`（P7-B 已存在，`config.py:664`，預設關）
  本波 E2E 固定開啟，並把**筆記層的尾段 7 條**列入 §5 量測（人工＋`rg`，附引文）。
- **C1b 區塊細化（值已釘死）**：E2E 使用 **`LOCAL_LLM_EXTRACTION_CHUNK_CEILING_TOKENS=4500`**。
  - 依據＝`evidence/chunk-replay-p7c/README.md`（零模型呼叫重播；重播值與產品實跑 log 對帳一致：
    依 context 推導上限 65,953、`estimated_transcript_tokens=11,711`）。
  - 該值在本場產生 3 塊（4,466／4,413／2,995），**F044 單獨落在 4,413 的塊**，其餘 6 條落在 2,995 的尾塊；
    6,000（P7-B 現值）則是 2 塊且**7 條全擠在同一塊 5,918 tokens**。審查另實測 5,500／5,860
    **不改變 F044 的處境** ⇒ 只有 ≤4,500 才能把 F044 隔進小塊。
  - 預註冊預測（含 FALSIFIER）引用 `evidence/chunk-replay-p7c/README.md` 的 §1–2 及 §3 項 1–3、5，並於每場開跑前登錄。
    該 README §3 項 4 是較早期預測，仍寫 `CALL_BUDGET` 預設 2，與本 rev3 契約衝突；不得引用或採用該項成本推論／預設值。
  - **碎片塊護欄（新）**：不得讓 E2E 落在會產生 <800 est tokens 尾塊的區間（4,000／3,000 會產生 151 tokens 碎片塊）。
    一般化的「極小尾塊併回前一塊（僅在併後仍 ≤ 預算時）」列為 **SUPPORTING S4**（非阻斷），
    因為它會改動分塊語意，需獨立測試。
- **C1c 呼叫數護欄（新旋鈕）**：`LOCAL_LLM_EXTRACTION_CALL_BUDGET`
  - **語意（明文定義，回應 I4c）**：**總萃取呼叫數上限（含所有 chunk）**；`0`＝不限制。
  - **預設值＝`0`**：使「全關 ⇒ byte 級回前波」成立（不與 C1b 互斥）。
  - E2E 顯式設 **4**（≥3 塊所需；仍有護欄作用且可被單元測試以 `2` 驗證逾限路徑）。
  - 逾限行為：在任何 provider/model 呼叫前，以完整 chunks 清單預檢；若 chunk 數大於非零 budget，**不得截斷、跳過尾塊或用部分筆記繼續生成**。中止該次本地摘要，沿用既有摘要失敗隔離流程：只回傳逐字稿並附明顯失敗警告（`summary=None`、`summary_failed=true`），不產生可被當成完整會議紀錄的部分摘要；不改 `task_processor.py:259/262`。記錄 `skipped_reason=extraction_call_budget_exceeded` 與要求／允許呼叫數。這是此單一會議的摘要降級結果，不是 observation-only skip；其他任務及全域服務不受影響。
  - 驗證：以 3 塊／budget 2 的確定性測試證明 provider 呼叫數為 0、沒有部分筆記／交付紀錄；budget 0 與 3 塊／budget 4 均照常完整處理。
- 語意不變式：`CEILING=6000`＋`CALL_BUDGET=0` ⇒ 回 P7-B 行為。

### CORE-2｜生成側：把「寫不出來」變成可觀測、可收斂（模型無關）

> rev2 重指向（回應 I3）：R2 的證據顯示 qwen 型漏寫**已進入清單仍未落實**，故本 CORE 拆成
> 「期望集合粒度」（C2a，對準 gemma F048 型）與「遵循度」（C2c，對準 qwen 型）兩條獨立機制。

- **C2a 事實級期望集合（對準 gemma F048 型）**：沿用既有逐條對帳迴圈（零新呼叫類型），
  把「**筆記已列、交付未寫**」以**事實級**粒度列出（現行期望多為議題級：議題寫了、該議題下的具體事實沒寫
  ⇒ 不會被列出）。P7-B 的 **F048 型**（E7C 有、E8 無）登錄為回歸探針。
- **C2c 逐項處置重申（新，零呼叫的遵循度槓桿）**：在既有補強輪的提示詞內（local-only 區塊），
  把上一輪未落實項目以**獨立區塊**重申，並要求模型**逐項顯式處置**（每項標明「已寫入」或
  「逐字稿無此資訊／不適用」）⇒ 讓「模型寫不出來」從靜默失敗變成可觀測輸出，且不新增任何呼叫。
  本項為 R2 型的**主要**手段。
- **C2b 補強輪上限（輔助，非唯一手段）**：`LOCAL_LLM_MAX_REFINEMENT_ROUNDS` 2→3，受
  `LOCAL_LLM_REFINEMENT_CALL_BUDGET`（新，同 C1c 語意：**總補強輪數上限**、`0`＝不限制、**預設 0**）約束；
  超出即停並記 `skipped_reason`。成本已由 CORE-E 上限涵蓋（+1 輪 ≈360 s）。
- 語意不變式：`LOCAL_LLM_RECORD_COVERAGE_MODE=off` ⇒ 完全不跑、無 log、無 metrics；
  `LOCAL_LLM_REFINEMENT_NO_REGRESSION=false` ⇒ 不得有任何守衛 log（P7-A 契約）。

### CORE-3｜確定性專名正規化（零模型呼叫；安全網齊備）

- **開關**：`LOCAL_LLM_PROPER_NOUN_NORMALIZE`（**新，預設 False**）。
- **判定鏈（全部確定性，rev2 補齊 I10）**：
  1. **registry 優先**：`data/entities/entity_registry.json`（既有檔；既有消費者 `backend/core/fidelity_checks.py:313`）
     命中的官方名稱優先於任何近音推斷；衝突時採 registry 值。
  2. **候選定義**：以單位名詞尾綴（`股／科／室／處`）與 registry 既有專名為候選集合；
     僅處理「**交付文字中的專名不在逐字稿、而逐字稿存在唯一近音候選**」的情形。
  3. **唯一性判準**：沿用既有近音原語 `backend/services/correction.py:80-110`（`is_homophone_swap`）
     ＋`pypinyin`（`pyproject.toml:56`）⇒ 不新造重裝備；**候選數 ≠ 1 或無候選 ⇒ 保持原文**（不捏造）。
  4. **可稽核**：每次替換寫 log（`original → replaced`）＋累計計數；
     `skipped_reason` 覆蓋 `no_candidate`／`multiple_candidates`／`registry_conflict`。
- **評法（回應 I11）**：閘門 4 場（gemma×2、qwen×2）一律 **C3 關**（避免與 CORE-A/B/D 混雜歸因）；
  C3 開／關配對場列 **SUPPORTING S5**（資源允許才跑，1 場 gemma ≈40 分）。
- **反 gaming**：測試須斷言 C3 **不讀** `quality/fact_checklist.json`、提示詞不含 checklist token（沿用 P7-B 禁令）。
- 既有 `SECTION_MEETING_RECORD_TERM_FIXES`（`backend/core/prompt_templates/section_meeting.py:141`）**不動**，僅新增獨立階段。

## 4. SUPPORTING／BEST_EFFORT（非阻斷）

- **S1｜E2E 投影補洞（零成本）**：把 `full_document_item_count`／`full_document_avg_item_chars`／
  `near_duplicate_items.count` 補進 `project_record_quality_metrics`（`scripts/e2e/run_owned_e2e.py:928-980`）
  **只補投影、不加門檻**（既有 5 條 `QUALITY_TAG_THRESHOLDS` 在 `:179-195`，不得新增／放寬）。
- **S2｜標註落點（R5）**：**只量測不改行為**。既有可動槓桿是模組常數
  `TAG_SNAP_TOLERANCE_SECONDS=180`／`TAG_SNAP_MAX_SHIFT_SECONDS=120`（`backend/core/text_postprocess.py:781,785`）
  與 `LOCAL_SOURCE_TAG_DIVERSIFY_ENABLED`；**`LOCAL_LLM_TAG_SNAP_SIMILARITY` 並不存在**
  （rev1 誤引，已更正）。新增該旋鈕屬語意變更 ⇒ 本波不做，只登錄「不得放寬既有 5 項門檻」。
- **S3｜生成紀律歸因消融**：P7-B 三開關開／關各 1 場 qwen，檢驗「密度改善是否以覆蓋為代價」。成本 ≈30 分 ⇒ 排在 CORE 之後。
- **S4｜極小尾塊併回（需獨立測試）**：當最後一塊 est tokens <800 且併回前一塊後仍 ≤ 預算時併回；
  否則保持原狀（不得違反 `_validate_chunk_postcondition`）。
- **S5｜C3 開／關配對場（1 場 gemma）**：見 CORE-3 評法。
- **BEST_EFFORT｜跨場逐字稿差異**：各場 ASR／校正不同 ⇒ 跨場比對僅作觀察值。

## 5. 量測表（門檻對變異穩健；集合語意；時鐘來源明示）

**通則（回應 I2）**：所有阻斷條文採「**2 場皆 ≥地板** ＋ **至少 1 場 ≥目標**」的集合語意
（n=2 的「中位數」＝平均，會放行一場不達標的結果 ⇒ 不使用）。
容差下限＝本專案自訂噪聲帶 ±10pp（28 條制 ≈3 條、7 條制 ≈0.7 條）。
**明文限制**：n=2 且容差 ≥ 噪聲帶時，**小於 10pp 的變化不可宣稱是優化或回退造成的**，
一律以觀察值登錄。

| 目標 | 定義 | 儀器／命令 | 門檻（阻斷） |
|---|---|---|---|
| **CORE-A** gemma 交付層尾段 7 條 | F044／F054／F055／F056／F060／F065／F066 是否出現在交付 `.md`（附引文） | 人工＋`rg`（+ C1a 筆記層為觀察值） | 2 場**皆 ≥4/7**（1 條＝14.3pp＞噪聲帶）且**至少 1 場 ≥5/7**（＝預註冊預測值）且 **F044 至少命中 1 場** |
| **CORE-B** gemma 整體保真度地板（新，I5） | `coverage_core`（28 條核心） | `measure_coverage.py` | 2 場**皆 ≥22/28**（＝P7-B 25 −3 條 ≈10.7pp）且**至少 1 場 ≥25/28**（重現 P7-B 水準） |
| **CORE-C** qwen 整體保真度 | 同上 | 同上 | 2 場**皆 ≥24/28**（＝歷史最佳 27 −3 ≈10.7pp）且**至少 1 場 ≥27/28**（重現歷史最佳） |
| **CORE-D** qwen 密度地板（升為阻斷，I9） | `full_document_item_count`／`full_document_avg_item_chars` | `measure_record_quality.py` | 2 場**皆 ≤45 條且 ≥52 字**；且**至少 1 場 ≤40 條且 ≥58 字**（重現 P7-B 37／61.2，留 ~10% 餘裕） |
| **CORE-E** 成本（取代相對門檻） | ①**呼叫數**（確定性）：萃取呼叫數／補強輪／logical_generations；②**牆鐘**（`run_summary.json` `started_at`→`finished_at`，**非** pipeline total） | `backend.log` metrics＋`run_summary.json` | ①萃取呼叫 ≤ 實際完整塊數且 ≤ `CALL_BUDGET`(=4)；補強輪 ≤3；②牆鐘 **gemma ≤2,750 s**（＝P7-B 2,378.5＋340.6 整份萃取）、**qwen ≤2,650 s**（＝1,814.9 基線＋381 補強輪 allowance＋427.6 同路徑完整萃取 allowance，再留 26.5 s） |
| **CORE-F** DOCX | 存在且可開 | `ls`＋`unzip -t` | 阻斷（沿用 runner） |
| 反 gaming | 抽驗 2–3 條新命中事實的原文對照 | Stage 05 人工 | 阻斷（沿用 P7-B 禁令：不得把 checklist 關鍵詞寫進提示詞） |

**觀察值（不得單獨通過或否決；修掉 rev1 的規範／觀察混用）**：近似重複對（≥0.80）、
筆記層尾段 7 條、標註落點（`on_start_tag_ratio` 等 5 項既有門檻仍由 runner 判定）、
「不得再回退」清單（gemma F048 型；單條無法在噪聲帶下否決，故只登錄）。

**密度升為阻斷的理由（I9）**：本波新增兩條會直接影響密度的槓桿（多塊萃取＝素材碎片化、
第 3 輪補強＝整份紀錄重生成），密度有實質回吐風險；且密度是使用者最直接可感的維度（P7-B 已量測 −52.6% 條目）。

**Qwen 成本上限推導（RV-003；開跑前固定，不得看結果後調門檻）**：P7-B Qwen E8 的 `run_summary.json`
（`e2e/attempt-P7B-qwen27b-e8/run_summary.json`）實測同音檔、同本地路徑牆鐘 1,814.937858 s；其 `backend.log`
記錄兩塊萃取合計 427.6 s，且兩輪補強各約 381 s、360 s。新分塊的單一額外 Qwen 呼叫尚無直接實測；因此不假稱 150.5 s Gemma 尾段探針可外推，而用 Qwen 已量到的**完整兩塊萃取總時間 427.6 s**作保守增量 allowance，並用 Qwen 實測補強輪較慢值 381 s：
`1,814.937858 + 427.6 + 381 = 2,623.537858 s`，上取整至預註冊硬上限 **2,650 s**（含 26.462142 s 餘裕）。這是成本預算而非新 chunk 精確耗時預測；Stage 05 必須報告每場實際牆鐘／呼叫數，不得事後改門檻。若基線、日誌或計時失效，CORE-E 記 `BLOCKED`，不可估算代替。

**E2E 場次**：gemma 2 場（必）、qwen 2 場（必）＝4 場；資源允許再跑 S3／S5。
**預註冊**：每場開跑前寫下「塊數／各塊 tokens／尾段 7 條落點／預期命中集合」，跑完對帳。

## 6. 停損與回退

- 停損以 **CORE-E（呼叫數＋由實測推導的絕對牆鐘上限）** 判定；**不再**用「相對對照場 +15%」（P7-B I14 教訓）。
- C1c 超限必須在任何萃取呼叫前拒絕該次本地摘要；禁止為滿足呼叫數上限而丟棄 transcript chunks。受影響任務沿用現有摘要失敗行為，只提供逐字稿與明顯警告，不得產出可驗收的部分會議紀錄；這是**單一會議摘要降級**，不得升級成全域服務 veto，亦不得改 `task_processor.py:259/262`。若固定 E2E 音檔實際需要超過預註冊 4 呼叫，該輸出不可計為會議紀錄或 E2E 品質 PASS；代表「3 塊預期」前提失效：Stage 04 停止後續 E2E、記 `PRIMARY_OUTCOME_STATUS: UNKNOWN`、`IMPLEMENTATION_STATUS: ESCALATED`、`CORE_ACCEPTANCE_STATUS: BLOCKED`、`TASK_CLOSURE_STATUS: REPLAN_REQUIRED`，不得暗中加大 budget。
- 任一槓桿可獨立關閉；全關（`CEILING=6000`、`CALL_BUDGET=0`、`REFINEMENT_CALL_BUDGET=0`、
  `MAX_REFINEMENT_ROUNDS=2`、`PROPER_NOUN_NORMALIZE=false`）⇒ **byte 級回 `ab2528b` 行為**
  （`git show --stat ab2528b` ＝只新增 `.agent/` 證據檔，產品樹即 P7-B `5cff85f`）。
- 觸發停損時：先關「本輪新增槓桿」，保留 P7-B 已知成果（分塊＋密度），並登錄 `escalation.md`；**不得**就地改語意。

## 7. 跨模型／跨 OS

- 全部槓桿位於 `_summarize_with_local_pipeline`（引擎分派點之後）⇒ LM Studio／Ollama 同碼路徑。
- 不得出現 `platform.system`／`sys.platform`／`os.name`／`darwin`／`win32` 或模型名判斷
  （測試強制；既有函式清單式檢查在 `tests/test_t20260923_p7b_generation_discipline.py:183-193`，新函式須加入）。
- 新開關全部登錄 `.env.example`；一般 guard skip 路徑記 `skipped_reason`（observation-only）；C1c 超限依 §3/§6 是阻斷該次摘要的明確降級，不能當 observation-only 繼續生成。
- Windows／Ollama 實機仍 `[UNVERIFIED]`，Stage 05 對「守衛是否被評估／為何被跳過」做顯式斷言。

## 8. 驗證計畫（Stage 04 → Stage 05）

1. Stage 01 rev3 → **Stage 02 獨立複審 attempt-03（fresh context，rev3 hash 專屬）**→ Stage 03 handoff → Stage 04 實作。
2. **產品碼變更前取得完整全庫基線**：`DATA_DIR=/tmp/test_scratch uv run --frozen pytest tests/ -q`；保存完整命令、結束碼、摘要及必要 log。曾被中斷的 pytest 不算基線。若不能取得有效基線，依 §8.1 的 `V-FULL-SUITE` 標記，不得假設為乾淨。
3. 每個 CORE 切片先做**零模型呼叫驗證**（離線重播／單元與契約測試），再做 E2E；每個新開關需單元測試、`.env.example` 文件化及全關 byte 級回退證明。
4. **E2E 前置（新，I12）**：實作完成且單元測試綠 ⇒ **先 commit（僅產品碼＋測試）** ⇒ 才啟動 E2E。理由：runner 對 dirty worktree **fail-closed**（P7-A 已因此白跑一場 `e2e/attempt-P7A-gemma31b-e7b`）。
5. Stage 05 獨立驗收：CORE-A／B／C／D／E／F 逐條、DOCX、反 gaming 抽驗、成本對帳、狀態路由與殘餘風險。
6. 產出 `result.md`；誠實登錄未達項，不得以觀察值替代阻斷條文或把 `BLOCKED`／`NOT_RUN` 改寫成 `PASS`。

### 8.1 狀態感知驗證、基線與閉合（workflow-routing.md §7）

每個下列檢查在計畫時的初始值均為 `CHECK_RESULT: NOT_RUN`、`WAIVER_STATUS: NOT_ALLOWED`；Stage 04/05 依實證更新，永不回寫成推測的 PASS。所有列均為 `WAIVER_ALLOWED: NO`、`WAIVER_AUTHORITY: NONE`；代理不得自行豁免。`GOAL_CRITICALITY` 是對主要結果的貢獻，不等於是否為閉合閘門。

| CHECK_ID | 服務目標 | GOAL_CRITICALITY | EVIDENCE_ROLE | CLOSURE_GATE | BASELINE_REQUIRED | FAILURE_CLASSIFICATION_RULE |
|---|---|---|---|---|---|---|
| `CORE-A` | REQ-品質：Gemma 尾段事實命中集合達 §5 門檻 | CORE | OUTCOME | HARD_CLEAN | NO | 有效兩場中未達任一集合門檻＝FAIL；必要場次因輸入／環境無法取得有效結論＝BLOCKED；未開跑＝NOT_RUN。 |
| `CORE-B` | REQ-品質／保留 P7-B：Gemma 整體 coverage_core | CORE | OUTCOME | HARD_CLEAN | NO | 依 §5 絕對集合門檻判定；無效／缺失量測不可補估。 |
| `CORE-C` | REQ-品質：Qwen 整體 coverage_core | CORE | OUTCOME | HARD_CLEAN | NO | 依 §5 絕對集合門檻判定；低於門檻＝FAIL，測量無效／缺場按 BLOCKED 或 NOT_RUN。 |
| `CORE-D` | REQ-品質／保留密度：Qwen 文件密度 | CORE | OUTCOME | HARD_CLEAN | NO | 依 §5 條目數與字數集合門檻；不可用平均值取代每場地板。 |
| `CORE-E` | REQ-品質成本取捨：呼叫數、補強輪及 E2E 牆鐘 | CORE | OUTCOME | HARD_CLEAN | YES | 有效同條件場次超過 §5 固定呼叫／牆鐘上限＝FAIL；缺 run_summary／有效基線或計時不等價＝BLOCKED，不得改用 pipeline total 或事後調門檻。 |
| `CORE-F` | REQ-交付：DOCX 可用 | CORE | OUTCOME | HARD_CLEAN | NO | DOCX 缺失或 `unzip -t` 失敗＝FAIL；檔案取得／驗證受環境阻斷＝BLOCKED。 |
| `ANTI-GAMING` | REQ-量測有效：2–3 項新命中事實與逐字稿原文相符，提示詞不含 checklist token | CORE | OUTCOME | HARD_CLEAN | NO | 抽驗發現無來源事實或 checklist 洩漏＝FAIL；原文／提示詞證據不完整＝BLOCKED。 |
| `LOCAL-CONTRACTS` | NFR-相容：新開關、C1c 超限原子失敗、off/no-log、補強輪及後處理順序不變式 | CORE | MUST_NOT_BREAK | HARD_CLEAN | NO | 新增或改動路徑違反任一已核准語意、超限仍有 provider 呼叫／部分會議摘要，或雲端路徑變動＝TASK_REGRESSION；預期的逐字稿-only＋明顯摘要失敗警告不算部分會議摘要。 |
| `BYTE-ROLLBACK` | NFR-回退：全部新旋鈕關閉時逐位元回到本波前產品行為 | CORE | MUST_NOT_BREAK | HARD_CLEAN | YES | 與固定 P7-B／ab2528b 基準不一致＝TASK_REGRESSION；基準檔或可比輸出缺失＝BLOCKED。 |
| `PLATFORM-INDEPENDENCE` | NFR-跨平台：新增邏輯同一路徑、無平台／模型名稱分支 | CORE | MUST_NOT_BREAK | HARD_CLEAN | NO | 靜態禁用清單／新函式測試發現平台或模型分支＝TASK_REGRESSION。Windows/Ollama 實機本波仍未執行，必須保留 `[UNVERIFIED]`，不得以靜態測試宣稱實機 PASS。 |
| `FULL-SUITE` | NFR-回歸：全庫測試 | SUPPORTING | REPOSITORY_HEALTH | BASELINE_DELTA | YES | 相同相關 failure signature 註記為 PRE_EXISTING_FAILURE；只有完整前置基線對照後無新增／惡化才可使 BASELINE_DELTA gate PASS，仍須揭露舊失敗且不得稱全庫全綠；新生／惡化且與改動相關＝TASK_REGRESSION；基線或同等環境不可得＝BLOCKED/INCOMPLETE。 |
| `STAGE05-INDEPENDENT` | REQ-獨立驗收：核對 CORE 證據、原始輸出及成本 | CORE | OUTCOME | HARD_CLEAN | NO | 獨立驗收依證據 PASS／FAIL；外部輸入／工具／環境造成無效結論＝scoped BLOCKED，不能抹除 Stage 04 已證狀態。 |

**狀態與路由**：Stage 04 的 `execution.md` 必須記錄六個正交欄位 `PRIMARY_OUTCOME_STATUS`、`IMPLEMENTATION_STATUS`、`CORE_ACCEPTANCE_STATUS`、`REQUIRED_VERIFICATION_STATUS`、`INDEPENDENT_ACCEPTANCE_STATUS`、`TASK_CLOSURE_STATUS`，以及每項檢查的上述完整欄位、阻斷範圍／證據／下一步、`PLAN_REVISION`、HANDOFF 身分／SHA-256、執行時間與可得的 artifact hash。核心門檻全數有效達成才可記 CORE `PASS`；有效違反門檻為 `FAIL`；環境／輸入不能形成有效結論為具名 scope 的 `BLOCKED`；尚未執行為 `NOT_RUN`。固定 E2E 若超過預註冊 4 chunks，依 §6 記錄摘要被安全降級為逐字稿-only，該場沒有有效紀錄交付，並走 escalation/replan，不得以不完整輸出計分。

Stage 04 路由遵循 workflow-routing.md §7.7：語意／計畫前提失效 ⇒ `IMPLEMENTATION_STATUS: ESCALATED`、`TASK_CLOSURE_STATUS: REPLAN_REQUIRED`；核心 FAIL ⇒ 按政策設 implementation `IN_PROGRESS`、closure `FIX_REQUIRED`；核心 BLOCKED／NOT_RUN 分別進 `CORE_ACCEPTANCE_BLOCKED`／`PENDING_CORE_ACCEPTANCE` 並保留已證 implementation 狀態；核心通過但全庫基線差異未能結論 ⇒ `REQUIRED_VERIFICATION_STATUS: INCOMPLETE`、`PENDING_REQUIRED_VERIFICATION`，不得降格為 implementation blocker。只有 V-FULL-SUITE 基線差異已得結論，且所有其他 required checks closure-satisfied，aggregate `REQUIRED_VERIFICATION_STATUS` 才可 PASS；未結論的非迴歸驗證只能是 INCOMPLETE/BLOCKED，不能自動 waivable。

Stage 05 必須先讀取並記錄 Stage 04 `execution.md` 的 SHA-256 與不可變快照欄位 `STAGE_04_REPORTED_IMPLEMENTATION_STATUS`、`STAGE_04_REPORTED_CORE_ACCEPTANCE_STATUS`、`STAGE_04_REPORTED_REQUIRED_VERIFICATION_STATUS`；環境阻斷時保留這些快照，路由至 `INDEPENDENT_ACCEPTANCE_STATUS: BLOCKED`、`TASK_CLOSURE_STATUS: ACCEPTANCE_BLOCKED`。若驗收推翻 load-bearing 計畫前提則改走 `REPLAN_REQUIRED`。只有主要結果已達、implementation complete、CORE 與 required verification 閉合、獨立驗收 PASS 且無未解硬閘門時，`TASK_CLOSURE_STATUS` 才可為 `DONE`（§7.10）。

## 9. 預算與切片

- 4 場 E2E 的**預算上限合計約 3 小時**（2×gemma 2,750 s＋2×qwen 2,650 s）；成本推導分別見 §5。Qwen 實測 allowance 高於 rev2，實際時間可能較低，但不得再以舊「qwen 約 30 分／場」作承諾。
  ＋離線驗證與實作＋S3／S5（資源允許）。
- 切片順序：**S1（零成本）→ CORE-3（零呼叫）→ CORE-2（生成側）→ CORE-1（萃取側）→ 4 場 E2E**。
  理由：先做零成本與零呼叫項，可在不確定萃取側前先確認生成側不是瓶頸。
- 實作 aid（非證據）：`prep/site-map-core12.md`（CORE-1／2＋S1 落點圖）、`prep/site-map-core3.md`（CORE-3 落點圖）。

## 10. 未解疑點（不得當成事實）

- 雲端紀錄標註 100% 落在 `00:00:00` 的機制未知 `[UNKNOWN]`。
- gemma 漏 F044／F055／F066 是「該區塊模型注意力不足」或「筆記格式誘導忽略」未分辨 `[INFERRED]`；
  §11 的 FALSIFIER 即為此設計。
- 各場逐字稿（ASR＋本地校正）不同 ⇒ 跨場「真漏寫」判定僅在場內成立 `[VERIFIED]`。
- qwen 的 `coverage_core` 在 n=2 下 <10pp 的變化不可判定（見 §5 通則）。

## 11. 方案 A（尾段補萃取）vs C1b（全域細塊）— 決策與備援（回應 I13）

| 面向 | 方案 A：尾段補萃取（rev1 前探針） | C1b：全域細塊（本波採用） |
|---|---|---|
| 證據 | 已量測：Gemma 尾半段單次呼叫 **6/7 命中（含 F044）**、**150.5 s** | 零呼叫重播（3 塊、F044 落 4,413 塊）＋P7-B 已證「分塊取代大呼叫」；Gemma／Qwen 成本分開估列 |
| 成本 | +1 次呼叫（+150.5 s，**僅 Gemma 探針實測**；不得外推 Qwen） | +1 次呼叫。Gemma 依其整份萃取實測增量；Qwen 依同路徑 E8 的 427.6 s 兩塊萃取總時間作保守 allowance（CORE-E 推導見 §5） |
| 覆蓋範圍 | **只有尾段**（中段漏寫無解） | **整份逐字稿**（每塊都有獨立呼叫） |
| 模型無關 | 是 | 是 |
| 風險 | 需決定「尾段」定義（時間／比例）＝新啟發式；單次視窗是**機率性**（兩次各 6/7 但命中集合不同） | 塊數隨逐字稿長度成長 ⇒ 成本需護欄（C1c） |
| 決策 | **備援**：若 C1b 之後尾段仍 <5/7（FALSIFIER 成立），依 Stage 01/02 重規劃；150.5 s 只可作 Gemma 探針依據，Qwen 須另有同路徑成本依據 | **主方案**（覆蓋範圍與模型無關性勝出） |

**成本證據邊界**：tail-half 的 150.5 s 僅為 Gemma 的單次探針時間，不用於 Qwen CORE-E 門檻。Qwen 的 2,650 s 是 P7-B Qwen E8 基線＋Qwen 自身實測補強 allowance＋完整兩塊萃取時間所推導的保守預算（§5）；額外 C1b chunk 的精確時間仍 `[UNVERIFIED]`，不得描述為已量測。
