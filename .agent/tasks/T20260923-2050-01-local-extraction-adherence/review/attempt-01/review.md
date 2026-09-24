# Stage 02 獨立計畫審查 — P7-C（`T20260923-2050-01-local-extraction-adherence`）

## 0 受審快照與角色宣告

- 角色：**Stage 02 獨立計畫審查員（fresh context、唯讀）**。未修改 `plan.md`、產品碼、既有 `review/**`・`e2e/**`・`research/**`；未 commit。唯一寫入＝本目錄 `review.md` ＋ `evidence.md`。
- 受審對象：`.agent/tasks/T20260923-2050-01-local-extraction-adherence/plan.md`（`PLAN_REVISION: 1`）。
- **計畫指紋**：`sha256＝325e8487b4430b3fcf38f301513487314b0d730f7d6385b88eec191357d2cb0a`（`shasum -a 256` 實跑 **3 次**：開審前、審查中、寫入本檔前，三次同值；與委託方宣告一致）`[VERIFIED]`。
- Repo／分支：`/Users/hsiaojohnny/dev/convert`、`fix/qwen-local-quality-parity`、`HEAD＝ab2528b718e8c91557fd72db174b0f9bb78d3a68`（`git rev-parse HEAD`）。`git status --porcelain` 僅一項未追蹤＝本任務目錄（含 Planner 自己產的 `evidence/chunk-replay-p7c/`；`plan.md` 之外無產品碼變更）`[VERIFIED]`。
- 約束遵守：**全程零模型呼叫**（未 curl LM Studio、未啟動 backend）、未跑全 suite。唯一執行的程式＝**產品自身的純字串函式**（`_build_local_context_plan` ＋ `_split_transcript_into_chunks`，`DATA_DIR=/tmp/rev_scratch`），以及 `rg`／`shasum`／`python` 讀 JSON。
- 證據標籤：`[VERIFIED]`＝本人實跑或實查檔案行號；`[INFERRED]`＝由已驗證事實推得；`[UNKNOWN]`＝查不到。原始輸出見同目錄 `evidence.md`。

## 1 Goal Baseline（自權威來源重建）

**使用者要的（原話要旨）**：地端模型（LM Studio；日後 Office 的 Ollama＋Windows／RTX 4090）生出來的會議紀錄品質「**至少不要跟雲端 Gemini 差太多**」；機制必須**模型無關**；並明確要求 macOS／Windows 都要能用。

**前波（P7-B，`T20260923-1810-01-local-record-fidelity-density`）已證實的事實**（來源：`e2e/attempt-P7B-stage05/verification-report.md`、`escalation.md`）`[VERIFIED]`：

| 項目 | 實測 |
|---|---|
| gemma 4 31B | core 覆蓋 21/28 → **25/28**（+19.0%）；但 §5 主驗收**尾段 7 條結構命中 2/7、F044 未命中（FAIL）**；標註 `on_start` 0.9615→0.84（既有門檻回退） |
| qwen 3.8 27B | 密度 78→37 條、42.5→61.2 字（PASS）；但 `coverage_core` **27/28 → 25/28（FAIL）**；牆鐘 1,023.2→**1,814.9 s（+77.38%）** |
| 歸因 | gemma 的三條尾段缺失＝**萃取側**（筆記內就沒有）；qwen 的 F019／F056＝**生成側**（筆記內有，且第 2 輪補強清單已明文列出仍未寫入） |

**由 Baseline 推出的必要性質**（本審查即以此檢核 plan）：

1. 新門檻必須**可證偽**、且對**單場變異穩健**——專案自己的規則：同一 build／模型／素材的重跑擺動達 14–18 個百分點，**小於約 ±10pp 的差異不可宣稱是優化造成的**（`.agent/tasks/T20260923-1810-01-local-record-fidelity-density/progress-report.md:14-17`）`[VERIFIED]`。
2. **不得回吐已證成果**（密度、gemma core +19% 皆算成果）。
3. 成本不得失控（P7-B §7 的相對牆鐘條款已被 I14 證明不可用；escalation §3 D1／D2 要求改寫）。
4. 不得以模型名／平台名分支；全關須 byte 級回前波。

**plan 自述目標與 Baseline 的對齊**：§1 的 Goal Contract（含非目標、模型無關）與 Baseline **一致**，且 §6 明確**廢除**相對牆鐘條款（修掉 P7-B I14 缺口）、§5 新增**每模型 2 場**（部分修掉「單場不可判定」）——這三點是本 plan 的實質進步 `[VERIFIED]`。**但**門檻與成本之間出現自相矛盾（§4 I1）、門檻在 n=2 時語意不明（I2）、且 CORE-2 的機制與它自己引用的證據相反（I3）——見下。

## 2 Top-down 審查

### 2.1 目標對齊（正面）

- 兩個缺口（gemma 尾段萃取側、qwen 生成側）**各自對到一條 CORE**，與 §1 的 Baseline 表格一致，沒有把「密度」當成本波主戰場（正確：密度已由 P7-B 拿到）。
- §2 的 R1／R2／R3／R5 逐條標了證據出處，且 **R1／R2／R3／R5 我逐條實查為真**（見 §3.3）——根因主張不是敘事，是可回溯的檔案／log 行。

### 2.2 必要性與關鍵路徑

- CORE 四條與兩個缺口一一對應，沒有夾帶無關重構；SUPPORTING（S1 投影補洞、S2 標註只量測、S3 消融）確實都**非阻斷**，比例正確。
- **但關鍵路徑有一條「未綁定設定值」的斷點**：CORE-1（C1b 區塊細化）是 gemma 腿的**唯一**槓桿，而 plan 全文**沒有寫出 E2E 要用的 ceiling 值**（§3 C1b 只寫「由 6,000 下調」並列了 5,500／5,860 兩個離線數字）。我實查 Planner 自己的 `evidence/chunk-replay-p7c/README.md §3` 已把預測釘在 **ceiling 4,500**，但 `plan.md` 沒有引用該檔、也沒有綁定該值 ⇒ 執行者無法在「照計畫」與「照證據檔」之間取得唯一解。見 I4。
- 另一條：CORE-2 被宣稱要解決 R2（qwen 生成側），但 **R2 的證據顯示該項早已進入補強問題清單**（見 I3）⇒ 這條 CORE 目前沒有可支持的機制。

### 2.3 門檻／否決比例性與可證偽性

- **CORE-D（成本）自相矛盾且未推導**：qwen 實測牆鐘 **1,814.9 s**（Stage 05 §1.8）已高於 plan 的 ≤1,500 s；而 plan 自己的 C2b 要加第 3 輪補強，我從 qwen E8 `backend.log` 的時戳實測**每輪補強約 360 s**（20:26:56→20:32:56）⇒ 期望值約 2,175 s，**超標約 45%**。另外 1,500 這個數字與 qwen 的 **pipeline total 1,497.3 s** 幾乎相同（Stage 05 特別警告「牆鐘／pipeline 不可混算」）⇒ 高度疑似把 pipeline 值當牆鐘。見 I1。
- **「2 場中位數」在 n=2 時語意不明**：數學上兩個樣本的中位數＝兩者平均，於是 `{4/7, 7/7}` 的「中位數 5.5 ≥ 5」會**放行**一場只有 4/7 的結果；而 qwen `{25/28, 27/28}` 平均 26 也會**放行**一場 25/28（＝P7-B 的 FAIL 值）。同一份門檻在兩種讀法下結論相反 ⇒ 阻斷條文不可判定。見 I2。
- **門檻與變異量級不匹配**：專案自訂噪聲帶是 ±10pp，而 CORE-B 的容許落差只有 2/28＝**7.1pp**（＝落在噪聲帶內）⇒ 這條阻斷門檻**無法區分真回退與雜訊**；plan 自己引 R4（18pp 擺動）卻只給 ±1 條容差，內部不一致。見 I2。
- **CORE-C 把觀察值升級成否決、且門檻未推導**：P7-B 的 Gate 表明確把 qwen 密度列為**非阻斷**（`verification-report.md` §2），plan 未說明為何本波要升為阻斷；且 ≤45 條／≥55 字的目標比實測（37／61.2）**寬鬆**，寫成「維持 P7-B 成果」名實不符。見 I9。
- **F044 子句的可控性**：F044 在 gemma 歷史 6 場（E1／E2／E5b／E6／E7C／E8）**0 命中**（Stage 05 §4.1＋E8），而 plan 把「F044 至少命中 1 場」寫成阻斷子句卻**沒有綁定任何會改變 F044 處境的設定**。我實測：ceiling 6,000 時 F044 與其他 6 條同在 5,918 tokens 的塊；**5,500／5,860 時 F044 仍在 5,379／5,541 tokens 的大塊**；只有 ceiling ≤4,500（我實測 4,500／3,800／3,000）F044 才單獨落進 4,413／3,761／2,981 tokens 的塊。見 I4。

### 2.4 失敗圍堵

- §6 的「先關本輪新增槓桿、保留 P7-B 成果、登錄 escalation、不得就地改語意」與 §10 的未解疑點登錄，屬良好圍堵 `[VERIFIED]`。
- **缺口**：gemma 腿**沒有任何整體保真度地板**。CORE-A 只看尾段 7 條，於是「尾段過了、但 core 覆蓋從 25/28 掉回 21/28（含 P7-B 新回退的 F048 型）」可以**通過全部阻斷條文**。這與 §6「保留 P7-B 已知成果」的自我承諾衝突。見 I5。
- 另外：CORE-1 的效果**可能被 C1c 的預設值直接抵銷**（見 I4），那會讓整場 E2E 變成「無法歸因的空跑」——這是最大的預算風險（4 場 ≈ 2 小時 20 分，§9）。

### 2.5 設計經濟

- 選用的儀器（`measure_coverage.py`／`measure_record_quality.py`／runner）都是**既有**的，未另造尺；S1 只補投影不加門檻；S2 明示「只量測不改行為」——節制良好 `[VERIFIED]`。
- **但漏了一個已量測、成本更低的槓桿**：P7-B 的尾段萃取探針實測「尾半段單獨一次呼叫（150.5 s）可命中 6/7，**含 F044**」（`evidence/tail-extraction-probe/README.md` A2／A4），而 plan 只把 C1b（全域縮塊）列為 CORE-1，未把這條已量測的「尾段單次呼叫（方案 A）」列為候選或備援（§6 只說「全關回前波」）。見 I13。
- C1b 的候選值區間（4,000／3,000）依 Planner 自己的重播會產生 **151 tokens 碎片尾塊**（`evidence/chunk-replay-p7c/README.md` 註）⇒ 成本效益差，plan 未處理此邊界（I4）。

## 3 Bottom-up 審查

### 3.1 開關盤點（本波點名的每一個 `LOCAL_LLM_*`）

| plan 的敘述 | 實查結果（出處） | 判定 |
|---|---|---|
| `LOCAL_LLM_DUMP_EXTRACTION_NOTES`「已於 P7-B 存在（預設關）」（§3 C1a） | 存在，`backend/core/config.py:664`，`default=False` | `[VERIFIED]` 正確 |
| `LOCAL_LLM_EXTRACTION_CHUNK_CEILING_TOKENS`「由 6,000 下調」（§3 C1b） | 存在，`config.py:653`，`default=6000`；`summarization.py:636-661` 使用（`min(既有, 本上限)`） | `[VERIFIED]` 正確 |
| `LOCAL_LLM_MAX_REFINEMENT_ROUNDS`「2→3」（§3 C2b） | 存在，`config.py:280`，`default=2` | `[VERIFIED]` 正確 |
| `LOCAL_LLM_RECORD_COVERAGE_MODE`／`LOCAL_LLM_REFINEMENT_NO_REGRESSION` 語意不變式（§3 C2） | 存在，`config.py:287`／`config.py:636`（後者描述已載明 observe 的界線） | `[VERIFIED]` 正確 |
| `LOCAL_LLM_EXTRACTION_CALL_BUDGET`「新，預設 2；0＝不限制」（§3 C1c） | **不存在**（`rg` 全庫 0 命中）⇒ 確實是新旋鈕 | 標「新」正確，但**預設值語意未定義**（見 I4） |
| `LOCAL_LLM_REFINEMENT_CALL_BUDGET`（§3 C2b） | **不存在** ⇒ 新旋鈕 | 新增正確 |
| `LOCAL_LLM_PROPER_NOUN_NORMALIZE`「預設 False」（§3 C3b） | **不存在** ⇒ 新旋鈕 | 新增正確 |
| `LOCAL_LLM_TAG_SNAP_SIMILARITY`「僅能走 …（語意變更）」（§4 S2） | **不存在**（`config.py` 內與 `TAG_SNAP` 相關的只有模組常數 `TAG_SNAP_TOLERANCE_SECONDS`／`TAG_SNAP_MAX_SHIFT_SECONDS`，`backend/core/text_postprocess.py:781,785`；另有 `LOCAL_SOURCE_TAG_DIVERSIFY_ENABLED`）。此名稱在 P7-B `verification-report.md §5-F` 就已出現，屬**沿用未經驗證的既有敘述** | **誤把「不存在」當「既有」**（I6） |

### 3.2 行號／函式／儀器核對

- `_summarize_with_local_pipeline` 存在，且 `_validate_summary_quality`（`:1395`）／`_validate_record_source_coverage`（`:2018`）在地端管線內被呼叫（`:3334`／`:3341`）；`_finalize_record_text`（`:3681`，`@staticmethod`）在 `:3521`／`:3600` 被地端管線呼叫（`:3788` 為另一條路徑）⇒ plan §7「全部槓桿位於地端管線、且 C2a 走既有對帳迴圈」在**落地上成立**（但須留在 `mode=="local"` 分支內，因 `_validate_summary_quality` 也被雲端路徑用，`:4815`／`:4853`）`[VERIFIED]`。
- `SECTION_MEETING_RECORD_TERM_FIXES` 存在（`backend/core/prompt_templates/section_meeting.py:141`，經 `templates.py:474` 綁進模板）⇒ C3 的「既有不動、另立新階段」可行 `[VERIFIED]`。
- C3 的「近音唯一候選」有現成原語：`pyproject.toml:56` 已依賴 `pypinyin`，`backend/services/correction.py:80-110` 有同音／近音判定（`is_homophone_swap`）⇒ 不是新造重裝備 `[VERIFIED]`。
- 「5 項既有門檻不得放寬」為真：`scripts/e2e/run_owned_e2e.py:179-195` 恰 5 條 `QUALITY_TAG_THRESHOLDS` `[VERIFIED]`。
- S1 的投影缺口為真：`project_record_quality_metrics`（`scripts/e2e/run_owned_e2e.py:928-980`）**沒有** `full_document_item_count`／`full_document_avg_item_chars`／`near_duplicate_items` `[VERIFIED]`。
- 素材與量尺檔存在：`/Users/hsiaojohnny/Downloads/0903-科務會議.m4a` sha256 `982151f4629ade0c38f1…`；`quality/fact_checklist.json` sha256 `cf012d1f6983f67ecb47cc7a6486e48c110a6b2782ad94cccf0332a4ec6ec001`（plan §量尺只寫相對路徑 `quality/fact_checklist.json`，全庫僅一份，可用 sha 對上）`[VERIFIED]`。
- §8 的「不得平台／模型名分支，測試強制」有既有機制：`tests/test_t20260923_p7b_generation_discipline.py:183-193`（函式清單式檢查）⇒ 新函式必須加入該清單（Stage 04 待辦）`[VERIFIED]`。

### 3.3 §2 根因主張逐條核對

| plan 主張 | 我的實查 | 判定 |
|---|---|---|
| R1：gemma E8 萃取筆記「**無**政治／禮堂・走廊・三樓／新聞行銷處・局長室」，「選舉」僅出現在日期行 | `rg` 該筆記：`政治`0、`禮堂|走廊|三樓`0、`新聞行銷處|局長室`0；`選舉` 僅 L66／L178「日期：未提及（僅提到近期為年底選舉前）」 | `[VERIFIED]` 為真 |
| R1：`chunk_count=2` 已生效、`merged_tokens=2303` | gemma `backend.log`：`20:00:44` metrics `chunk_count=2`；`19:37:03`「萃取筆記零損串接…2 份、**2303** tokens」 | `[VERIFIED]`（log 未用 `merged_tokens=` 字面，數字為真） |
| R1：`finish_reason=stop`、`completion_tokens 235–331` ⇒ 排除 max_tokens 截斷 | `finish_reason=stop` 全為真；但 **235–331 是「逐字稿語意校正」階段**（`temperature=0.3`／`max_tokens=3072` 的 12 次呼叫，見 `19:24:49`–`19:30:16`）；**萃取階段**實為 `completion_tokens=1,356`（`19:34:00`）／`1,248`（`19:37:03`），`max_tokens=8192`。結論（非截斷）成立，**引註數字錯** | `[VERIFIED]` 數字，**引註錯**（I7） |
| R2：qwen 筆記 L47／L199 有 F019／F056，且 F056 敘述比 gemma 更精確 | L47「上次颱風平上班日，土地稅科倉庫嚴重漏水，影響土地卡」；L199「樓上施工（防水層重做）刨掉舊防水層，導致早期埋設的排水管外漏…」 | `[VERIFIED]` 為真 |
| R3：qwen 成本來自呼叫數（萃取 1→2、補強輪 1→2、logical 3→5） | Stage 05 §1.7 同值；我另實測 qwen E8 每輪補強約 **360 s**（`20:26:56`→`20:32:56`） | `[VERIFIED]` |
| R4：qwen「同模型同素材歷史擺動 0.7857 ↔ 0.9643」標 `[VERIFIED]` | 數字出處為 E5（`ce99502`）與 E5b（`run_summary.json: expected=actual=eaa4f45`）——**兩場 SHA 不同**，中間有 `58e65de`（`utf-8-sig` 詞表讀取）。我實查 `data/glossary/*.txt` **兩檔皆無 BOM** ⇒ 該 commit 對本場「byte 級等價」⇒ 擺動仍可視為抽樣變異。**但「同 build」字面不成立**，標 `[VERIFIED]` 過強 | `[SUPPORTED]`（I8） |
| R5：gemma 標註 `on_start` 0.9615→0.84、`excl0` 0.95→0.8095 | Stage 05 §1.2 同值 | `[VERIFIED]` |

**我自己補跑的零呼叫分塊重播**（`DATA_DIR=/tmp/rev_scratch`；輸入＝P7-B gemma E8 實際吃進去的逐字稿 `fd40a201…`，15,666 字；qwen E8 `b7b9e5e0…` 同長度）：

| ceiling | 塊數／est tokens | F044 落點 | 其餘 6 條落點 |
|---|---|---|---|
| 6,000（P7-B 現值） | 2 ／ 5,960＋5,918 | 第 2 塊（5,918） | **全部與 F044 同塊**（該塊含全部 7 條 probe） |
| 5,860 | 3 ／ 5,801＋5,541＋682 | 第 2 塊（5,541） | F054／F065／F066 在第 3 塊（682） |
| 5,500 | 3 ／ 5,459＋5,379＋1,397 | 第 2 塊（5,379） | 第 3 塊 3 條（F054／F065／F066；F060 跨重疊區） |
| 4,500 | 3 ／ 4,466＋4,413＋2,995 | 第 2 塊（4,413） | 第 3 塊 6 條（2,995） |
| 3,800 | 4 ／ 3,737＋3,761＋3,554＋1,397 | 第 2 塊（3,761） | 第 3／4 塊 |
| 3,000 | 5 ／ 2,986＋2,922＋2,981＋2,961＋151 | 第 3 塊（2,981） | 第 4 塊 6 條 |

**兩個關鍵事實**（都與 plan 的槓桿選擇直接相關）：

1. **ceiling 6,000 時，E8 的第 2 塊「已經含有全部 7 條尾段 probe 的字面」**，但模型在該塊的筆記只寫到 `[00:32:34]`（筆記第 2 段時戳範圍 00:22:44–00:32:34）——即**塊內覆蓋不足**，R1 的結論方向正確 `[VERIFIED]`。
2. **5,500／5,860 這兩個值幾乎沒有改變 F044 的處境**（仍是 5.4–5.5k tokens 的大塊）；能讓 F044 單獨落進 ≤4,500 塊的只有 ceiling ≤4,500。plan §3 C1b 卻把 5,500 列為第一個候選而不提 4,500（4,500 只存在於 Planner 自己的 evidence 檔）。

### 3.4 契約與語意不變式（可落地）

- §6「全關 ⇒ byte 級回 `ab2528b`」可驗：`git show --stat ab2528b` ＝**只新增 `.agent/.../escalation.md`**，產品樹即 P7-B `5cff85f` ⇒ 這個錨點定義清楚 `[VERIFIED]`。
- §3 C2 的兩條不變式（`RECORD_COVERAGE_MODE=off` 不得有新 log／metrics；`REFINEMENT_NO_REGRESSION=false` 不得有守衛 log）與 P7-A／P7-B 既有契約一致（`config.py:287,636`）`[VERIFIED]`。
- §3 C3a「只在逐字稿近音唯一候選時替換、無候選維持原文（不捏造）」是正確的安全方向，但**未納入研究 L1 明列的兩個護欄**：官方白名單 `data/entities/entity_registry.json` 優先（該檔存在，且 `backend/core/fidelity_checks.py:313` 已在讀），以及「替換一律寫進可稽核 log／計數」（`research/next-wave-gap-p7b.md:220-221`）。見 I10。

### 3.5 驗證可行性

- CORE-A／B／C 的儀器都在（`measure_coverage.py`、`measure_record_quality.py`），且 CORE-A 的「交付層 7 條」需要人工＋`rg`（plan 已寫）。**但 CORE-3 的評法（§3 C3b「E2E 兩場各開／關比對」）與 §5／§9 的 4 場預算不相容**：4 場已全數指派給 CORE-A／B／C 的量測；若閘門場同時開 C3，CORE-A／B 的歸因會混雜（P7-B 已有「多槓桿同時開啟 ⇒ 無法歸因」的前例）。見 I11。
- §8／§9 **未列「跑 E2E 前必須先 commit」**；runner 對 dirty worktree 是 fail-closed（P7-A 已因此白跑一場：`e2e/attempt-P7A-gemma31b-e7b`）。見 I12。

## 4 問題清單

### I1（**阻斷**）CORE-D 的成本門檻與本波自己的槓桿相反，且時鐘來源可疑
- **為什麼**：qwen 實測牆鐘 **1,814.9 s** 已 > plan 的 ≤1,500 s；C2b 要加第 3 輪補強（我實測每輪 ≈360 s）⇒ 期望 ≈2,175 s，**超標 ≈45%**。1,500 又與 qwen **pipeline total 1,497.3 s** 幾乎相同，而 Stage 05 §1.8 明文警告兩者不可混算（差額 317.6 s ＝ ASR／上傳／render 等）。gemma 側 ≤2,600 s 亦只比實測 2,378.5 s 高 9.3%，而 C1b 預測本身就要 +5–10% ⇒ 邊緣。
- **怎麼修**：①明示時鐘來源（牆鐘，`run_summary.started_at/finished_at`）；②由**實測成本模型**推導上限（每輪補強 ≈360 s、每次萃取 ≈150–200 s），或改寫成「≤ 同模型 P7-B 基線 +N s／+X%」並登錄基線值；③若保留 ≤1,500 s，就必須同時列出「買到 −315 s」的槓桿（目前沒有）。

### I2（**阻斷**）阻斷門檻「2 場中位數」語意不明，且容差落在專案自訂噪聲帶內
- **為什麼**：n=2 的中位數＝平均，於是 `{4/7,7/7}`（中位數 5.5）與 `{25/28,27/28}`（中位數 26）都會**放行一場未達標的結果**；改讀成「兩場都須達標」結論相反 ⇒ 阻斷條文不可判定。且專案自訂噪聲帶為 ±10pp（`progress-report.md:14-17`），CORE-B 的容差只有 7.1pp ⇒ 無法區分真回退與雜訊；plan 引 R4（18pp）卻只給 ±1 條，自相矛盾。CORE-A 的預測值（4,500 下 ≥5/7）本身就是門檻值 ⇒ 2 場取中位數約等於丟硬幣（I4 一併處理）。
- **怎麼修**：把 n=2 的條文寫成**集合語意**（例：「2 場皆 ≥X」或「2 場中 ≥1 場 ≥X 且另一場 ≥X−1」），或改為 3 場取中位數並先登錄基線；容差需與噪聲帶同量級，或改成**配對比較**（同模型同素材的前後場）。

### I3（**阻斷**）CORE-2a 的機制與它自己引用的證據相反
- **為什麼**：plan 說 C2a 要「讓 R2 型漏寫進入補強問題清單」，但 R2 的證據（Stage 05 §1.10）與 qwen `backend.log` 顯示：第 1 輪清單**已**含「議題遺漏 7 項：**土地稅科倉庫漏水與土地卡重印**、…政治敏感議題應對…」、第 2 輪仍含同一項，模型仍未寫入 ⇒ 瓶頸是**遵循度／輪數**，不是「沒進清單」。把同粒度、同型別的類別再加一類，**不會改變**這型失敗；而 Stage 05 真正支持「期望集合粒度不足」的是 **gemma 的 F048 型**（議題級 vs 事實級）。
- **怎麼修**：①把 C2a 的目標敘述改對準 gemma 型（事實級期望集合；並把 F048 這類 P7-B 新回退登錄為回歸探針）；②為 qwen 型補一個**零呼叫**的遵循度槓桿（例：把未落實項目在下一輪以獨立區塊重申並要求逐項處置／逐項確認），讓 CORE-B 不只靠「多一輪 360 s」；③若仍要靠 C2b，須與 I1 的成本決策一起處理。

### I4（**阻斷**）CORE-1（gemma 腿唯一槓桿）沒有釘死設定值，且預設值會把它抵銷
- **為什麼**：(a) plan 只說 ceiling「由 6,000 下調」，未寫 E2E 的值（Planner 自己的 evidence 檔寫 4,500，plan 未引用）；(b) 我實測 **5,500／5,860 幾乎不改變 F044 的處境**（F044 仍在 5.4–5.5k 大塊），只有 ≤4,500 才把 F044 隔進單獨小塊——若不釘死值，CORE-A 的 F044 子句近似不可控；(c) C1c 的新旋鈕 `LOCAL_LLM_EXTRACTION_CALL_BUDGET`「預設 2」語意未定義（是「總呼叫數」還是「額外呼叫數」？），若為總數，則 ceiling 4,500（3 塊）會被截回 2 塊＝**P7-B 現狀**，且違反 plan 自己的不變式「CALL_BUDGET 不設 ⇒ 行為與 C1b 設定一致」；(d) 4,000／3,000 依 Planner 自己的重播會產生 151 tokens 碎片尾塊（成本效益差）卻未處理。
- **怎麼修**：在 plan 內**寫死** E2E 的（ceiling, call_budget）配對與其預註冊預測（例：ceiling 4,500／budget 0 或 3），並把 `evidence/chunk-replay-p7c/README.md §3` 的 5 條預註冊（含 FALSIFIER）**引用進 plan**；定義 budget 語意並讓預設值不與 C1b 互斥；加註「不得落在碎片塊（151 tokens）區間」。

### I5（**阻斷**）gemma 腿缺「整體保真度不得退步」的地板
- **為什麼**：全部 gemma 阻斷條文只有尾段 7 條（CORE-A）。P7-B 的 gemma core 由 21/28 升到 25/28，且同期出現 **F048 新回退**（E7C covered → E8 missing）；本波若為救尾段而犧牲中段（例如縮塊造成其他區段被稀釋、或多一輪補強把已寫事實寫掉），仍然可以「通過驗收」。這與 §6 自述「保留 P7-B 已知成果」與使用者目標（整份品質）衝突。
- **怎麼修**：加一條**非/阻斷皆可但須存在**的地板：gemma `coverage_core`（2 場）不得低於 P7-B E8 的 25/28（或登錄成「±1 條」帶寬），並把 F048 等 P7-B 回退項列入「不得再回退」清單。

### I6（非阻斷）`LOCAL_LLM_TAG_SNAP_SIMILARITY` 不存在，S2 誤把它當既有
- **為什麼**：全庫無此旋鈕（`rg` 0 命中）；真正的既有槓桿是模組常數 `TAG_SNAP_TOLERANCE_SECONDS=180`／`TAG_SNAP_MAX_SHIFT_SECONDS=120`（`backend/core/text_postprocess.py:781,785`）與 `LOCAL_SOURCE_TAG_DIVERSIFY_ENABLED`。此錯誤是從 P7-B `verification-report.md §5-F` 沿用下來、未經複核。
- **怎麼修**：改成正確的既有槓桿名稱，或明示「本旋鈕尚不存在，需新增（屬語意變更）」。

### I7（非阻斷）R1 的 `completion_tokens 235–331` 屬校正階段，非萃取階段
- **為什麼**：見 §3.3；結論（非 max_tokens 截斷）成立，但引註會誤導 Stage 04 去調錯階段。**怎麼修**：引 `19:34:00`／`19:37:03` 的萃取 diagnostics（1,356／1,248 ≪ 8,192），或寫明階段。

### I8（非阻斷）R4 的「同 build」不成立，`[VERIFIED]` 過強
- **為什麼**：E5（`ce99502`）vs E5b（`eaa4f45`）SHA 不同，中間有 `58e65de`；我實查兩份詞表皆無 BOM ⇒ 對本場行為等同，擺動仍可視為抽樣變異 ⇒ 結論可用，但標籤應降為 `[SUPPORTED]`。**怎麼修**：補一句「兩場 SHA 不同、中間僅一筆對無 BOM 詞表 byte 等價的 commit」，或補真正同 SHA 的重跑證據。

### I9（非阻斷）CORE-C 把觀察值升級為阻斷，門檻未推導，且「維持成果」名實不符
- **為什麼**：P7-B Gate 表明載 qwen 密度②為非阻斷；本波升為阻斷未給理由。≤45 條／≥55 字比實測 37／61.2 寬鬆（允許退步），與「維持 P7-B 成果」不一致。§5「近似重複對」列為觀察值卻寫「不得回升至 ≥3」（規範語與觀察語混用）。
- **怎麼修**：明示推導與理由，或降回觀察值並登錄基線；若真要維持成果，用貼近實測的帶寬（例：≤40 條／≥58 字）並說明；把「不得回升」改成阻斷或改成純觀察。

### I10（非阻斷）C3 缺安全網與觀測（白名單、log／計數、候選定義）
- **為什麼**：研究 L1 明列「官方白名單優先」與「替換寫進可稽核 log」，plan 未納入；「專名候選」的判定規則（regex／類別）未釘死，Stage 04 只能自行發揮。
- **怎麼修**：加入 `data/entities/entity_registry.json` 優先與 `skipped_reason`／計數；定義候選（例：`…股／科／室／處` 等）與「唯一候選」判準（沿用 `is_homophone_swap` 精神），並在測試中斷言提示詞不含 checklist token（反 gaming）。

### I11（非阻斷）CORE-3 的評法與場次預算／歸因不相容
- **為什麼**：4 場已全數指派給 CORE-A／B／C；C3 的「各開／關比對」沒有預算，且若閘門場同時開 C3 會混雜歸因。**怎麼修**：明確指定閘門場的 C3 狀態（建議關，或另以配對場處理），把 C3 的開／關對照排進 +1 場或另開小波。

### I12（非阻斷）缺「E2E 前先 commit」的操作前置
- **為什麼**：runner 對 dirty worktree fail-closed；P7-A 已白跑一場（`e2e/attempt-P7A-gemma31b-e7b`）。**怎麼修**：§8 加一步「實作後先 commit（僅產品碼＋測試），再啟動 E2E」。

### I13（非阻斷）更便宜、且**已量測**的槓桿未被列入 CORE-1
- **為什麼**：尾段探針實測「尾半段單次呼叫（+150.5 s）」命中 6/7 **含 F044**（`evidence/tail-extraction-probe/README.md` A2／A4）；相對 C1b（+1 次呼叫且依 I4 可能被預算截回），此方案的成本已量測、對 F044 的有效性已有證據。plan 未把它列為候選或備援（§6 只提「全關回前波」）。
- **怎麼修**：至少在 plan 內並列比較 C1b 與「尾段單次呼叫（方案 A）」，並說明在 F044 子句下為何選 C1b（若選 C1b，需以 I4 的值釘死支撐）。

## 5 結論

- **Top-down**：目標對齊良好、槓桿與缺口一一對應、圍堵與回退敘述完整；但**四個阻斷門檻中有三個不滿足「可證偽且對變異穩健」**（I1 成本自相矛盾、I2 n=2 中位數語意不明且容差 < 噪聲帶、I4 主槓桿未釘死設定值），且 gemma 腿缺整體保真度地板（I5）。
- **Bottom-up**：行號／函式／儀器／5 項門檻／投影缺口／素材 sha 皆與 repo 現況相符（多數主張可驗）；但有一個**不存在的旋鈕被當成既有**（I6）、一處**引註階段錯誤**（I7）、一處**標籤過強**（I8），以及 C3 的安全網與評法缺口（I10／I11）。
- **最站不住腳的一點**：**CORE-D 與 CORE-1b／C2b 的成本方向互斥**——門檻值（qwen ≤1,500 s）低於現行實測牆鐘 1,814.9 s（且疑似誤用 pipeline total 1,497.3 s），而本波同時要加一次萃取呼叫與一輪補強（實測 ≈+360 s）⇒ 依計畫設定，這一波在跑完之前就已註定過不了自己的阻斷條文。
- **建議**：以 rev2 修正 I1–I5（必要）＋I6–I13（建議）後再送 Stage 02 複審；**受審快照指紋未變**（`325e8487…`，3 次實測同值），審查期間無並發寫入 `plan.md`。

GATE: PLAN_REVISION_REQUIRED
