# P7 落差分析：地端 (LM Studio) vs 雲端 (Gemini) — 0903 科務會議／模板 `section_meeting`

- 版本：**v0.2**（2026-09-23）。唯讀研究；僅寫入 /tmp，未修改 repo、未執行 git 操作。
- 證據標籤：`[VERIFIED]`＝可用檔案行號查核；`[INFERRED]`＝由已驗證事實推導；`[UNVERIFIED]`／`[HYPOTHESIS]`。
- 主要來源：`data/cache/e2e/p3-cloud-baseline-05/`（雲端 C5）、`data/cache/e2e/p6a-qwen27b-e6b/`、`data/cache/e2e/p6a-gemma31b-e6/`、`.agent/tasks/T20260922-2037-02-local-model-quality-parity/e2e/attempt-*`、`doc/操作手冊/地端模型品質優化與驗證手冊_v4.10.md`、`doc/規格與設計/地端會議紀錄品質對齊雲端-研究與優化規劃.md`。

---

## 0. 摘要（三個最重要的結論）

1. **「事實涵蓋率」上，地端 qwen27B 已經超過雲端；gemma31B 才是明顯落後者。**
   `coverage_all`：qwen **0.8657** ＞ 雲端 **0.8060** ＞ gemma **0.6269**；
   `coverage_core`：qwen **0.9643** ＞ 雲端 **0.8929** ＞ gemma **0.7500**。`[VERIFIED]`（§1.2）
2. **使用者感受到的「差很多」主要不在事實，而在四個可量測的表面維度**：逐條化密度（qwen 78 條 vs 雲端 28 條）、
   `（待確認）` 殘留（qwen 20／gemma 26 vs 雲端 12）、字面亂碼（§2-R5）、以及**補強輪把已補到的事實寫回去**（§2-R1）。
3. **使用者「gemma 比 qwen 準」的直覺，在手冊 §6.5 的量尺下是「字面乾淨」而非「內容完整」**：
   gemma 每千字亂碼 0.42（比雲端 0.77 還低），但 core 覆蓋只有 0.75。兩者不是同一件事。`[VERIFIED]`

---

## 1. 落差量化

### 1.1 樣本與可比性（先把「同素材」講清楚）

| 場次 | 引擎／模型 | 產物 |
|---|---|---|
| 雲端 C5 | Gemini `gemini-3.5-flash-lite` | `data/cache/e2e/p3-cloud-baseline-05/backend_data/outputs/0903-科務會議_ce67d0dc.md`（2,593 字元）`[VERIFIED]` |
| 雲端 attempt-01 | 同上 | `.../p3-cloud-baseline-01/.../0903-科務會議_be23db52.md`＝**生成失敗 fallback**（檔頭「會議紀錄生成失敗」，log 00:22:04 `503 UNAVAILABLE`）`[VERIFIED]` |
| 雲端 attempt-03 | 同上 | `outputs/` **空**（無產物）`[VERIFIED]` |
| 地端 qwen27B | `qwen3.8-27b-splash` | `data/cache/e2e/p6a-qwen27b-e6b/backend_data/outputs/0903-科務會議_c605df1a.md`（4,853 字元）`[VERIFIED]` |
| 地端 gemma31B | `gemma-4-31b-it-mlx` | `data/cache/e2e/p6a-gemma31b-e6/backend_data/outputs/0903-科務會議_f9fee652.md`（2,184 字元）`[VERIFIED]` |

**可比性警告（重要）**：三場共享同一支音檔與同一份 ASR 快取（sha256 `982151f4…012828`，見 C5 `run_notes.md`），
但**語意校正後的逐字稿三場互不相同**（md5：雲端 `07ba4e3f…`、qwen `3aab0f4b…`、gemma `244f680e…`）；
以雲端 vs qwen 為例，194 行逐字稿中 **60 行不同**，差異集中在近音字修正
（雲端保留「編織錶／護數／一見／外麵」，qwen 已修成「編制表／戶數／一件／外面」）。`[VERIFIED]`
成因：`run_notes.md` 明載**雲端模式的語意校正層仍走本地 LLM**（`backend/services/task_processor.py:259-272`），
所以「雲端 vs 地端」的差異**只隔在最終摘要層**，但逐字稿本身帶有校正層的抽樣變異。→ 任何逐項比較都要扣掉這個雜訊。

### 1.2 同一把尺（`coverage-1.0.0`，67 條事實／core 28）

| 指標 | 雲端 C5 | qwen27B-e6b | gemma31B-e6 |
|---|---|---|---|
| `coverage_all` | 0.8060 | **0.8657** | 0.6269 |
| `coverage_core` | 0.8929 | **0.9643** | 0.7500 |
| `missing_core` | F025, F056, F066（3） | F055（1） | F001, F044, F054, F056, F060, F065, F066（7） |
| `unsupported_entities_count` | 0 | 0 | 0 |

`[VERIFIED]`：`attempt-C5-cloud-baseline/coverage.json`、`attempt-P6A-qwen27b-e6b/coverage_observation.json`、`attempt-P6A-gemma31b-e6/coverage_observation.json`

### 1.3 版型與密度（本輪新增量測；對 .md 全文計算）

| 指標 | 雲端 C5 | qwen27B-e6b | gemma31B-e6 |
|---|---|---|---|
| 總字元／中文字 | 2,593／1,782 | 4,853／2,821 | 2,184／1,324 |
| 行數 | 59 | 139 | 65 |
| 章節（一、二、三） | **只有一、二** | 一、二、三 | 一、二、三 |
| 編號條目數 | 28 | **78** | 23 |
| 彙整表資料列 | 6 | **13** | 9 |
| `（待確認）` 次數 | 12 | 20 | **26** |
| 出處標註數 | 28 | 78 | 23 |
| `00:00:00` 標註 | **28（全部）** | 9 | 4 |
| distinct 時間戳／比值 | 1／**0.036** | 49／0.628 | 17／**0.739** |
| `tagged_item_ratio` | 1.0 | 1.0 | 1.0 |
| `cross_section_duplicate_pairs` | 0 | 0 | 0 |

`[VERIFIED]`：`grep`／Python 對三檔重算；標註欄位並以 `measure_record_quality.py` 輸出核對
（`attempt-*/record_quality.json` → `metrics.tag_traceability`）。

**判讀**：
- 雲端**沒有**「三、歷次會議列管案件討論或臨時動議」，但它把討論塞進「二、（二）」等子節；地端兩場都有第三節。→ 章節完整度不是地端的落後項。
- 地端落後項是**逐條化過度**（qwen 78 條、平均 62 字元/條）與**`（待確認）` 內容級殘留**：
  - qwen 內文出現「指示**（待確認）**去確認『現金』發放的程序」（`0903-科務會議_c605df1a.md:105`）→ 主詞在萃取階段就已遺失。`[VERIFIED]`
  - gemma 表格列出現「（（待確認））」與「發言者3」欄位（後者由補強守衛要求修正，log 15:28:26）。`[VERIFIED]`
- 地端**勝過雲端**的是標註辨別力（0.628／0.739 vs 0.036）。

### 1.4 數字／金額／日期落地（逐字稿原文 vs 三份產物）

| 事實（逐字稿皆有） | 雲端 C5 | qwen27B-e6b | gemma31B-e6 |
|---|---|---|---|
| `600`（去年文康禮券） | **缺** | 有 | **缺**（log 15:42:20「數字遺漏 1 項：600」） |
| `800`／`13,600`（17 人 ×800） | **缺**（`800`、`13,600` 皆 0 次） | 有 | 有 |
| 40%／25%／15%（委任比） | 有 | 有 | 有 |
| `100多`（瑞里戶數） | 有 | 有 | 有 |
| `10月14` | 有 | 有 | 有（寫成 10/14） |
| `11月1`（生效日） | 有 | 有 | 有（寫成 11/1） |

`[VERIFIED]`：`grep -o` 對三檔＋gemma `backend.log` 覆蓋率比對行。→ 這維度**雲端最差**（缺 3 個金額，含 core F025）。

### 1.5 概數化／抽象化

三份產物都**沒有**「若干／相關經費／概略」等抽象化用詞（`grep` 0 次）。`[VERIFIED]`
→ 「把 600 元寫成『若干經費』」的擔憂在本樣本**不成立**；實際缺陷是**漏寫**與**待確認化**（1.3／1.4）。

### 1.6 語氣／可讀性（質性）

- 雲端：條目接近「一句一事＋完整從句」，欄位留白乾淨（`地點：`、`主持人：`）。
- qwen：資訊量最大，但把一件事拆成多條（例：「確認各單位皆報3人」自成一條），且一、（一）與二、（一）內容近重複。`[INFERRED]`
- gemma：最接近雲端密度，但**第三節整節只有「（待確認）」**（`0903-科務會議_f9fee652.md:62-64`）→ 看起來整齊、實際漏一整個章節。`[VERIFIED]`

---

## 2. 根因排序（依「可操作性 × 對落差的貢獻」）

### R1｜補強輪「整份重生成」造成事實回退（最高可操作）`[VERIFIED]`
- gemma 同一場三次對帳（`data/cache/e2e/p6a-gemma31b-e6/backend.log`）：
  | 時點 | 當下紀錄 | 數字未涵蓋 | 決議未涵蓋 |
  |---|---|---|---|
  | 15:28（首輪生成後） | content 2,014 字元 | `15`／`600`／`100`（3） | 2 項 |
  | 15:35（第 1 輪補強後） | content 2,231 字元 | **0 項** | 2 項（**換項**） |
  | 15:42（第 2 輪補強後） | content 2,181 字元 | `600`（**1**） | 0 項 |
  → 第 1 輪把 600 補回來，第 2 輪**又把它寫掉**；總共花 `final_and_refine=1,206.4s`（`extraction` 僅 328.8s）。`[VERIFIED]`
- 同構證據（qwen，同一 log 結構）：首輪生成 4,713 字元 →（補強 1 輪）4,842 字元；`final_and_refine=602.7s`。`[VERIFIED]`
- 手冊 §8-18 已獨立登錄同一現象並定調：「殘餘遺漏的成因不是輪數不夠，是**每輪重生成整份、沒有『已達標不得回退』保護**」。
- 預估改善：把 gemma `cov_missing_number` 1→0、refine 輪數與 `final_and_refine` 秒數下降；**不保證覆蓋率上升**（`[HYPOTHESIS]`：覆蓋率 +0～3pp，時間 −20%～35%）。

### R2｜萃取筆記階段的資訊量差異（gemma 的致命點）`[VERIFIED 部分]`
- gemma `萃取筆記零損串接：1 份、**1,563 tokens**`（15:22:14）；qwen `1 份、**3,967 tokens**`（14:52:30）。
  → 同一支音檔、同一模板，gemma 的筆記只有 qwen 的 **39%**；後續生成再怎麼寫也救不回沒進筆記的立場／理由／數據。`[VERIFIED]`
- 研究文件 §12.2 的歸因表亦記載「討論型 supporting（限制／理由／建議／他方回應）大面積遺漏（B1 −20、C1 −22、D1 −24）」。`[VERIFIED]`
- 對照：gemma 最終紀錄第三節整節空白，qwen 第三節有 5 條（含發言者2／3 的立場與 800×17=13,600）。`[VERIFIED]`
- 預估改善：`coverage_supporting` 為主戰場（gemma `coverage_all` 0.6269 → `[HYPOTHESIS]` +5～10pp，未驗證）。

### R3｜逐條化密度與 `（待確認）` 內容級殘留（可讀性主因，最貼近使用者抱怨）`[VERIFIED 量測]`
- 條目數 78（qwen）／23（gemma）／28（雲端）；`（待確認）` 20／26／12。
- qwen 內文把主詞寫成「（待確認）」兩次（`0903-科務會議_c605df1a.md:105,106`）→ 讀起來像「沒寫完」。`[VERIFIED]`
- 預估改善：屬文體層；`[HYPOTHESIS]` 可讓「人工可讀性」明顯改善，**量尺（coverage）不會動**——需要新儀器才驗得動（見 §4）。

### R4｜語意校正層抽樣變異（方法論風險，非模型能力）`[VERIFIED]`
- 三場逐字稿 md5 不同、60/194 行有差異；同一管線、同一模型在兩場的 `coverage_all` 可差 16.4pp
  （qwen 0.6866 vs 0.8507，手冊 §6.5／§8-16）。`[VERIFIED]`
- 意義：**單場「雲端 vs 地端」差距可能是抽樣雜訊**；任何 P7 優化宣稱至少要 2 場同 build。

### R5｜字面亂碼與專名失真（使用者說「gemma 比較準」的來源）`[VERIFIED 引用]`
- 手冊 §6.5：紀錄亂碼 qwen 5／11 處、gemma 1 處、雲端 2 處；每千字 1.60／2.03、**0.42**、0.77。
- 手冊 §8-10：`西龍股`、`煙酒文神股`、`工廠科` 等**無可信正解者刻意不登錄**（需人工確認）。
- 地端已有「確定性誤辨層」（`data/glossary/確定性誤辨校正.txt`），模型無關、跨 OS；擴表是低風險高報酬。

### R6｜context 預算／整併（`LOCAL_LLM_MERGE_NOT_CONVERGED`）— 本輪**未觸發**，降級為殘餘風險
- p6a 兩場 `chunk_count=1, merge_rounds=0`（gemma log 15:42:20、qwen log 15:02:33）＋零損串接
  （gemma 上限 62,794 tokens／視窗 71,936；qwen 上限 118,858／視窗 128,000）。`[VERIFIED]`
- 舊現場（`data/logs/app_2026-09-22.log` 14:12:47，1,754 tokens > 目標 900 → 整份 veto）已由 v4.8.0 的「零損串接＋目標下限化」涵蓋。`[VERIFIED]`（研究文件 §2.3）

### R7｜取樣參數與輸出上限 — 目前已對齊，非主因
- 現值：`temperature=0.7`（生成／補強）、`max_tokens=8192`、`context_budget=71,936`（gemma）／128,000（qwen）；
  萃取階段 `max_tokens=3072`（僅萃取小塊）。`[VERIFIED]`（兩場 backend.log）
- 組態旋鈕俱在：`backend/core/config.py:198-355`（`LOCAL_LLM_*`：`RESERVED_OUTPUT_TOKENS`、`OUTPUT_TOKENS_CEILING`、
  `MAX_REFINEMENT_ROUNDS`、`SAMPLING_TOP_P/TOP_K`、五個階段 temperature、`DISABLE_THINKING` 等）。`[VERIFIED]`

### 提示詞差異（使用者關心的「地端 vs 雲端提示詞」）`[VERIFIED]`
- **系統提示詞是共用的**：`template.resolve_system_prompt()` 一條路（`backend/services/summarization.py:519`），
  local／cloud 只差在**呼叫端**（`:527` 走 `_summarize_with_gemini`、`:529` 走 `_summarize_with_local_pipeline`）。
- 最終生成與補強訊息自 v4.8.0 起**共用同一 builder**（`_build_record_generation_message` `:2439`、
  `_build_record_refinement_message` `:2490`），差別只有地端多一列來源標註位置導引
  （`LOCAL_SOURCE_TAG_PLACEMENT_RULE` `:146`，雲端回空字串，見 `_local_tag_placement_rule` `:2429`）。
- 真正的分歧只有**萃取階段**：`LOCAL_EXTRACTION_PROMPT`（`:262`）＝基底；`CLOUD_EXTRACTION_PROMPT`（`:300`）＝基底＋雲端專屬增補。
  → P7 若要在不碰雲端提示詞的前提下補地端，**只能動 `LOCAL_EXTRACTION_PROMPT` 與其下游規則**，且需維持模型無關。`[VERIFIED]`

---

## 3. P7 優化候選（排序；前三名可在一輪內完成並驗收）

> 共同紅線：不得改門檻、不得改 `off` 模式語意、不得改雲端提示詞；機制需模型無關、macOS＋Windows 可用。

| 排序 | 做法 | 為什麼有效（證據） | 成本／風險 | 怎麼驗（哪個 metrics 會動） | 回退 |
|---|---|---|---|---|---|
| **1** | **補強輪加「不得回退」守衛**：重生成前記錄「已達標事實集合（數字／決議／日期）」，補強後若集合縮小則保留舊版本中已達標的段落（或改局部修補） | gemma 600 元「補回→又掉」（§2-R1 表）；qwen 同樣是整份重生成（4,713→4,842） | 中（改 `_summarize_with_local_pipeline` 補強收斂邏輯；屬語意變更 → 需 Plan/Review）；不改任何門檻 | gemma `cov_missing_number` 1→0、`logical_generations` 4→≤3、`final_and_refine` 1,206s→↓；`record_quality.metrics.char_count` 不得下降 >10% | 保留現行整份重生成路徑（旗標關閉即回舊行為） |
| **2** | **地端萃取提示詞補「討論型事實必收」清單**（限制／理由／建議／他方回應／金額用途），並要求每則附發言者與時間 | gemma 筆記僅 1,563 tokens（qwen 3,967）；研究文件 §12.2（B1 −20／C1 −22／D1 −24） | 低（改 `LOCAL_EXTRACTION_PROMPT:262` 一段文字＋模板增補；不動雲端） | `coverage_all`／`coverage_core`（runner `coverage_observation.json`）、`missing_core_ids`；筆記 token 數 | 提示詞常數可回復；不進任何閘門 |
| **3** | **逐條化與 `（待確認）` 收斂**：內容級 `（待確認）` 只允許出現在無可查依據欄位；同一子題不得拆成多條（給密度指引而非硬限） | qwen 78 條／20 待確認、gemma 26 待確認、雲端 12；qwen:105 主詞變「（待確認）」 | 低（提示詞層＋後處理檢查；**不得**變成回退保護的替代） | 條目數、`（待確認）` 計數（建議納入既有 `record_quality` 觀測欄位）、人工抽讀 | 純提示詞，可回復 |
| 4 | 擴充 `data/glossary/確定性誤辨校正.txt`（需人工確認正解的字：`西龍股`→徵收股等） | 手冊 §8-10／§6.5 亂碼統計（qwen 5／11 處 vs gemma 1） | 低（資料檔、跨 OS、模型無關）；風險＝寫錯正解 | 「紀錄亂碼／千字」指標（既有量測腳本） | 刪行即回復 |
| 5 | 逐字稿語意校正層：同 build 至少 2 場、固定校正輸入（或記錄 seed／溫度）以降低比較雜訊 | 三場逐字稿 md5 不同、60/194 行差異；qwen 兩場 coverage 差 16.4pp | 低（流程／記錄層） | 跨場 `coverage_all` 變異度、`known_term_fix_hits` | 純流程 |
| 6 | 為「文體／可讀性」補一個**觀測用**（非閘門）儀器：條目數、待確認數、密度、段落長度分佈 | 現行量尺看不到使用者真正在意的維度（研究文件 §12.1 結論 3） | 中；不可變成 verdict | 新增 observation 欄位；與人工評分對照 | 觀測層可移除 |
| 7 | 雲端自身缺陷（P4-F）：雲端模式 28 個標註全 `00:00:00` | C5 `zero_time_tag_count=28`、`distinct_tag_time_ratio=0.036` | — | 雲端場 `tag_traceability` | 與本輪地端優化無關，但**不可拿雲端當標註標竿** |

---

## 4. 風險與不可行項

1. **不可改雲端提示詞／不可改門檻／不可改 `off` 語意**（本輪硬約束）。任何「把覆蓋率門檻調鬆換好看」都會破壞 P4-A 對帳契約。
2. **不可換模型收場**：gemma 在手冊量尺下是最弱的一顆（core 0.75）；而 qwen 已 ≥ 雲端。換模型是產品決策，且非模型無關。
3. **不可宣稱已達雲端水準**：qwen 這一場雖然 `coverage_core` 0.9643 > 雲端 0.8929，但雲端場只有 **1 份可比產物**
   （C2/C3 兩場失敗），且 qwen 自己在兩場間差 16.4pp。**單場 ≠ 結論**（手冊 §8-8／§8-16）。
4. **雲端基線本身的效力邊界**：C5 的 runner 未完成收尾（無 verdict／無 stored-bytes SHA／DOCX 為事後補產生）→
   只能當「真實雲端產物＋儀器量測」，不得當一次通過的 E2E 驗收（C5 `run_notes.md` 誠實邊界 1）。
5. **不能宣稱「同素材」**：三場逐字稿不同（§1.1）；跨場比較必須標註此雜訊。`[VERIFIED]`
6. **R1 的修法是語意變更**：改補強收斂語意 → 需走 Plan→Review→Handoff→實作，不可當「bounded fix」。
7. **Windows＋Ollama 實機未驗** `[UNVERIFIED]`（手冊 §8-7／§8-15）：任何跨 OS 效果宣稱需 4090 實機 A/B。
8. **字表治理沒有 ground truth 就不能登錄**（手冊 §8-10）：寧可留錯字，也不要把不確定寫成規則。
9. **gemma 的第三節空白**屬模型行為（整節只寫「（待確認）」），**不是**管線缺陷 → 只能靠 R2（筆記補強）間接改善。`[INFERRED]`

---

## 5. 尚未完成／待補（v0.2 已可交付，但以下未驗）

1. `record_quality.json` 的 `known_term_fix_hits` 逐場差異（本輪只抽查雲端 C5）。`[UNVERIFIED]`
2. 19 型亂碼清單的逐場重算（手冊 §6.5 表格 vs 本次只做抽樣 grep，未重跑腳本）。`[UNVERIFIED]`
3. gemma／qwen 首輪生成與補強後版本的**全文 diff**（目前只有 `content_chars` 序列與未涵蓋集合；
   初稿本體未落檔 → 無法逐句證明「掉了什麼」）。`[UNVERIFIED]`
4. 萃取筆記本體（notes）未落檔，只有 token 數；R2 的「漏了哪些 supporting」尚無逐條證據。`[UNVERIFIED]`
5. `LOCAL_LLM_EXTRACTION_TEMPERATURE` 等實際生效值（log 只印生成／補強階段的 temperature=0.7）。`[UNVERIFIED]`
6. P7-1／P7-3 的量化預估幅度（目前為 `[HYPOTHESIS]`，需 2 場同 build A/B 才能定案）。
