# P7-A 通用性／可移植性獨立審查報告（唯讀）

- 任務：`T20260923-1700-03-local-refine-no-regress`（P7-A 地端補強輪「不回退」守衛）
- repo：`/Users/hsiaojohnny/dev/convert`｜分支：`fix/qwen-local-quality-parity`｜受審實作 commit：`3e9311a`
- 審查者：獨立唯讀審查。本報告為**唯一**寫入產物；未改任何產品程式／測試／文件、未 commit、未 kill process、未跑模型推論、未碰 `data/cache/e2e/p7a-gemma31b-e7c/`。
- 方法：①靜態閱讀 `3e9311a` diff 與現行碼；②跑單檔測試；③以 `/tmp/p7a_probe/probe_q5.py` 直接呼叫產品純函式（無模型）。
- 本次跑過的驗證指令（可重現）：
  - `DATA_DIR=/tmp/probe_generality uv run --frozen python -m pytest tests/test_t20260923_p7a_refine_no_regression.py -q` ⇒ `12 passed in 0.49s`（[VERIFIED]）
  - `uv run --frozen python /tmp/p7a_probe/probe_q5.py` ⇒ 探針輸出見 Q5（[VERIFIED]）

---

## 0. 結論（一句話，直接回答）

**守衛不綁任何一支錄音檔：任何錄音檔只要走地端流程（LM Studio 或 Ollama）都會經過同一條守衛程式路徑；差別只在「逐條對帳是否抽得到非空的期望集合」——抽得到就生效（預設即生效），抽不到（非中文格式的筆記／逐字稿、類別設成空等）就靜默不作用。**

## 0.1 給非技術使用者的白話前言

1. 這波做的是「補強輪不回退」：補強每輪都是**整份紀錄重新生成**；若某一輪把先前已經寫進去的重要事實弄丟（或換掉），就丟棄那一輪的輸出，改交付本次執行中「核心事實寫得最全」的那一版。
2. 它**不是**針對某一支錄音的優化：程式裡沒有檔名、時長、語言、模板或模型名的判定分支；它是拿「這次執行中每一版紀錄」的對帳統計互相比較（核心四類：議題、決議、數字、日期）。
3. 它要能運作需要一個「標準答案清單」（期望集合）：議題／決議從**萃取筆記的「議題與決議」區塊**抽；數字／日期從**逐字稿的「[時間] 發言者：」段落列**抽。
4. 若清單全空（例如英文會議、筆記沒有那個區塊、逐字稿不是那個格式），守衛**不會報錯，但也不會保護**——這是目前最大的通用性限制（詳見第 3 節表）。
5. 預設是開啟的：使用者什麼都不設，`LOCAL_LLM_RECORD_COVERAGE_MODE=enforce`＋`LOCAL_LLM_REFINEMENT_NO_REGRESSION=True`。
6. 已知誤判風險：模型若把同一事實**換句話說**（例：把「600 元」寫成「六百元」），對帳器可能誤判成「掉了」而回退。已用產品實際函式重現（見 Q5），但回退的代價上限＝維持前一版，不會弄壞內容。

---

## Q1. 是否與音檔綁定？

**結論：不綁定。** 守衛程式沒有檔名／時長／錄音內容／模板／模型名分支；換不同主題、不同長度、不同語言混雜的會議，都走同一條守衛路徑。唯一的固定假設是「對帳類別詞彙固定四類」與「期望集合抽取器的中文格式前提」，兩者都不是單支錄音的形狀。

證據：
- 守衛主體只依賴 `settings` 開關與兩份快照，不含任何音檔／模板／模型變數：[VERIFIED] `backend/services/summarization.py:3404-3408`（初始化）、`3454-3499`（比較與交付決策）。
- 固定類別詞彙：`_core_coverage_snapshot` 以 `("topic", "decision", "number", "date")` 迭代（`backend/services/summarization.py:3223`）；類別有效值過濾（`backend/services/summarization.py:1937-1941`）。這是「類別清單」常數，不是某支錄音的假設。
- 「不同長度」只影響前面的切塊與整併（`backend/services/summarization.py:3291`、`3307-3309`）；守衛比較發生在最終生成／補強之後（`3368`、`3433`），與 chunk 數無關。
- 「語言／格式」前提來自既有 P4-A 抽取器（非本波新增、本波只加 `missing_items_*` 三個 additive 鍵）：
  - 議題／決議取「萃取筆記」的中文區塊標記（`_extract_notes_topic_items` `backend/services/summarization.py:1710-1722`；`_extract_notes_decision_items` `1724-1740`）。
  - 數字／日期只掃「`[start-end] 發言者：`」段落列（`_iter_transcript_segment_bodies` `1809-1822`；數字單位白名單「元|塊|萬元|個人|人|％|%|個|孔|樓」`200-203`；`_scan_transcript_number_items` `1840-1866`；`_scan_transcript_date_items` `1868-1901`）。
- commit 內文的「0903／gemma／section_meeting」字樣只出現在**註解**（`backend/core/config.py:629-634`、`backend/services/summarization.py:3397-3403`），不構成分支：[VERIFIED]（`git show 3e9311a` 對照）。
- 不同語言混雜：會走同一條路；但若筆記沒有中文「議題／決議」結構、逐字稿不是該段落格式，期望集合可能為 0 → 守衛不作用（見 Q3）。

信心：高（[VERIFIED]，靜態＋12 測試通過）。

## Q2. 是否與模型綁定？

**結論：不綁定。沒有模型名分支；LM Studio（Mac）與 Ollama（Windows/RTX 4090）共用同一條 `_summarize_with_local_pipeline()` 程式路徑，守衛對兩者一視同仁。**

實際呼叫路徑（由呼叫端追到引擎）：
1. `backend/services/task_processor.py:333`（任務 → `summarize()`）
2. `backend/services/summarization.py:490` `summarize()`；`526-529` 分派：`mode==CLOUD` 走雲端，否則（含 lmstudio／ollama）一律走 `_summarize_with_local_pipeline`（`533` 回傳）。
3. `backend/services/summarization.py:3257` `_summarize_with_local_pipeline()`；`3265` 呼叫 `_select_local_engine()`（定義 `3099-3134`）——引擎選擇只影響「用哪個 transport 生成」，不影響流程。
4. 每次生成經 `_generate_with_local_engine()`（定義 `3136`；dispatch `3155`（ollama）→ `_summarize_with_ollama`（定義 `3817`）；`3166`（lmstudio）→ `_summarize_with_lmstudio`（定義 `4016`））。
5. 守衛位於 pipeline 層：在 `_generate_with_local_engine` 回傳＋`_finalize_record_text` 之後（`3433-3451`），對兩種引擎完全相同（`3454-3499`）。
6. 平台差異只在 provider 解析（`backend/core/platform_config.py:23-29`、`46-55`：macOS arm64 `auto` → LM Studio；非 Mac 保留 Ollama 優先）。

信心：高（[VERIFIED]，靜態；模型實際行為差異不在本題範圍）。

## Q3. 預設是否開啟？判定鏈與所有「不作用」情境

**結論：預設開啟、預設生效（只要期望集合非空且至少跑了一輪補強）。**

判定鏈（由設定到生效）：
1. `LOCAL_LLM_RECORD_COVERAGE_MODE` 預設 `enforce`（`backend/core/config.py:287-292`；validator 亦預設 `enforce`，`backend/core/config.py:132-139`）。逐條對帳照算並產生補強問題（`backend/services/summarization.py:1959-1963`、`2131`）。
2. `LOCAL_LLM_REFINEMENT_NO_REGRESSION` 預設 `True`（`backend/core/config.py:636-644`；讀取 `backend/services/summarization.py:3404`）。
3. 期望集合來源：
   - 議題／決議 ← 萃取筆記「議題與決議」區塊（`backend/services/summarization.py:1710-1740`）；
   - 數字／日期 ← 逐字稿「[start-end] 發言者：」段落列（`1809-1822`、`1840-1901`）。
4. 快照 `(未涵蓋數, 期望數, 未涵蓋身分集合)`：期望數總和 ≤0 或逐條對帳未執行 ⇒ `None`（`backend/services/summarization.py:3219-3232`）。
5. `None` ⇒ `guard_comparable=False`（`backend/services/summarization.py:3406-3407`）⇒ 守衛區塊整段不進入（`3454`）⇒ 交付最後一版。
6. `observe` 模式統計照算、只是問題不併入補強清單（`2131`），守衛仍可運作（`3214-3217`；測試 `tests/test_t20260923_p7a_refine_no_regression.py:381-394`）。
7. 實測佐證（本次重跑）：`12 passed in 0.49s`，含 off 不作用（`tests/test_t20260923_p7a_refine_no_regression.py:396-406`）、關閉開關等同本波前（`340-365`）、observe 可供快照（`381-394`）。

信心：高（[VERIFIED]）。

## Q4. `off` 模式是否真的 byte 級回本波前？

**結論：是（就「交付版本／守衛 log／額外 `_validate_*` 呼叫」三件事）。**

- `off` ⇒ `_validate_record_source_coverage()` 立即 return、`_record_coverage_stats={}`（`backend/services/summarization.py:1959-1963`；此 early-return 於本波前即存在，本波 diff 未動它）⇒ 快照 `None`（`3219-3232`）⇒ `guard_comparable=False`（`3406-3407`）⇒ 守衛區塊（`3454-3499`）不進入：**無任何守衛 log、無回退、交付＝最後一版**。
- 「無額外 `_validate_*` 呼叫」：本波對既有檢查的唯一結構改動是把初稿後／每輪後的同一組 5 個檢查抽成 `_validate_local_record()`（`backend/services/summarization.py:3181-3207`），順序與項目與本波前 inline 版本一致（`git show 3e9311a` 的 diff 可逐行對照）；守衛啟用時才在**回退分支**多一次重算（`3486-3488`），off 模式不可能走到。
- 註：off 模式下 `_core_coverage_snapshot()` 會被呼叫一次（`3406`，純 dict 讀取、無 log、無副作用），不影響 byte 級輸出。
- 「`missing_items_*` 不入 metrics」：`cov_*` 欄位只讀 legacy 鍵（`backend/services/summarization.py:2133-2154`；注入點 `3519`）。
- 測試佐證：T05（off：交付最後一版＋無守衛 log＋metrics 空字串，`tests/test_t20260923_p7a_refine_no_regression.py:236-250`）、T10（`396-406`）、T12（關閉開關與「無守衛 stub」產物與 log 逐字相同、僅遮罩 wall-clock，`340-365`）。

信心：[VERIFIED]（off 路徑靜態＋T05/T10/T12）。未直接做「真機 backend.log 逐字 diff」，但 off 路徑在本波沒有任何新增寫點（見 Q5 附註與未驗證項）。

## Q5. 等量互換判定是否會誤判？

**結論：會——但機制不是「項目身分字串中途改變」，而是「同一事實換寫法 → 判定器翻面 → 身分集合換項」。確實可能造成「明明變好卻被回退」。**

機制說明：
- 身分字串取自**期望側**（`類別:項目字串`）：議題／決議項目來自 `merged_notes`（`backend/services/summarization.py:2046`），數字來自 `transcript` literal＋snippet（`2074-2077`），日期來自 canonical＋snippet（`2106-2109`）。同一場執行中 notes／transcript 是常數 ⇒ 身分字串跨輪不變（[VERIFIED] 程式碼＋`tests/test_t20260923_p7a_refine_no_regression.py:381-394` 對照）。
- 真正會翻的是「該項目這輪算不算已涵蓋」：`_refinement_regression_reason()` 的 `newly_missing = candidate - best`（`backend/services/summarization.py:3235-3255`，集合差在 `3252`）判的是「best 有寫到、candidate 判定沒寫到」的項目集合。

以產品實際函式實跑反例（`/tmp/p7a_probe/probe_q5.py`，無模型）：
- 反例 A（數字換寫法，等量互換）：
  - BEST＝「發文康禮券 600 元」（漏 17 人）；CAND＝「發文康禮券**六百元**，共 17 人」（語意上兩個事實都在）。
  - 實測快照：BEST missing=4（含 `number:17`）、CAND missing=4（含 `number:600`）；`_refinement_regression_reason` 回「**等量互換（原本已寫到的事實被寫掉 1 項）**」⇒ 產品會回退到 BEST——而 BEST 反而整條漏了 17。〔根因：`_number_literal_is_covered` 只認阿拉伯數字（NFKC 全形→半形＋千分位等價），不認中文數字「六百」：`backend/services/summarization.py:1775-1800`。〕
- 反例 C（議題換句話說，計數變多）：BEST 寫完整議題句→covered；CAND 改寫成「搬遷時程與經費分攤方式仍待確認」→判缺 ⇒ reason「未涵蓋數變多」⇒ 回退。〔議題比對＝LCS 門檻＋詞級第二接受規則：`backend/services/summarization.py:2030-2038`、`_topic_terms_cover` `1229` 起。〕
- 對照 B（日期有等價展開）：`11/1` vs `11月1號` 不翻面（reason `None`），因 `_date_canonical_is_covered` 有等價展開（`backend/services/summarization.py:1903-1934`）。

影響評估：
- 會回退「其實沒有變差、甚至更好」的候選版本；但回退本身是**換回前一版**，不會弄壞內容或產生錯誤紀錄，最壞代價＝放棄候選在其他維度（忠實度、長度、其他類別）的淨改善。
- 觸發機率取決於模型是否改寫數字／議題措辭；若嚴格照補強提示「依逐字稿原文寫數字」，主要殘餘風險在議題標題改寫（換句話說）。
- 注意：這是**繼承既有對帳器的精度上限**（P4-A 已知），本波把它的後果從「多一輪提示」升級為「交付版本選擇」——風險面放大但方向正確（寧可保守回退，不讓事實變少）。

信心：[VERIFIED]（產品純函式實跑重現）。

## Q6. 既有功能是否可能被誤傷？

**結論：無誤傷；成本極小且可解釋。**

- 回退路徑成本：多一次 `_validate_local_record()`（`backend/services/summarization.py:3486-3488`）＝同一組 5 個確定性字串檢查（`3181-3207`），**零 LLM 呼叫**；log 增一組覆蓋率 info 行＋1 行 warning（`3474-3483`）。只在「真的判定回退」時發生。
- 呼叫端一致性（無「最後一版＝交付版本」的隱性依賴）：
  - `summarize()` 回傳交付版本（`backend/services/summarization.py:533`；pipeline `return summary` `3522`）；
  - 任務層拿回傳值格式化／存檔（`backend/services/task_processor.py:333-338`、`350-357`）；
  - DOCX 由「已存檔的 md」轉換（`backend/api/routes.py:404-410`、`440-443`）⇒ 一定是最終交付版本；
  - e2e runner 亦以回傳值寫檔（`scripts/e2e/rerun_local_summarize.py:174-181`）。
- `_record_coverage_stats` 全 repo 產品讀點只有兩處：`_record_coverage_metrics_fields`（`backend/services/summarization.py:2133-2154`）與 `_core_coverage_snapshot`（`3219-3232`）；回退後**立即重算**（`3486-3488`），問題清單與 `cov_*` 對齊交付版本（測試 T07：`tests/test_t20260923_p7a_refine_no_regression.py:272-292`）。無其他讀取者。
- 不收斂保護互動良好：回退後重算的問題集合與觸發該輪的簽章相同 ⇒ 下一圈命中 `3410-3417` 的不收斂 break，**不會多燒 LLM 輪**。
- 未動：雲端路徑（`526-527`、`4604` 其自身迴圈 `4647` 無覆蓋率檢查，屬本波宣告範圍之外）；共用訊息 builder 一字未動（`git show 3e9311a`）。

信心：[VERIFIED]。

## Q7. 跨平台

**結論：本波新增程式碼無任何平台相依。**

- 本波只改 `backend/core/config.py` 與 `backend/services/summarization.py`（`git show 3e9311a --name-only`）。新區段（守衛／快照／判定／設定欄位）無 `os.`／`signal`／`subprocess`／`zoneinfo`／編碼／路徑分支（[VERIFIED]，`sed -n '3181,3522p' | grep` 與 diff 對照）。
- 唯一平台分支是既有的 provider 解析（`backend/core/platform_config.py:23-29`、`46-55`），只決定「用 LM Studio 還是 Ollama」，不影響守衛（見 Q2）。
- **Windows＋Ollama 實機未驗證**：本機只有 macOS，依指示明說 `[UNVERIFIED]`。

---

## 3. 「守衛不作用」的所有已知情境

| # | 情境 | 原因 | 證據（檔案:行號） | 是否可接受 |
|---|---|---|---|---|
| 1 | `LOCAL_LLM_REFINEMENT_NO_REGRESSION=false`（或環境覆蓋） | 使用者顯式關閉 | `backend/core/config.py:636-644`；`backend/services/summarization.py:3404-3407` | 可接受（設計開關；T04/T12） |
| 2 | `LOCAL_LLM_RECORD_COVERAGE_MODE=off` | 對帳完全不跑 ⇒ 無統計 ⇒ 快照 `None` | `backend/services/summarization.py:1959-1963`、`3219-3232`、`3407` | 可接受（byte 級逃生門；代價＝守衛靜默不作用） |
| 3 | 期望集合全為 0 | 無比較基準 | `backend/services/summarization.py:3230-3231`；類別空警告 `2049`、`2079`、`2111` | 半可接受：無基準＝無保護；長期為 0 代表對帳機制失效（手冊已有辨識法，屬使用者痛點） |
| 4 | 萃取筆記缺「議題／決議事項」結構 | topic／decision 期望 0 | `backend/services/summarization.py:1710-1740`（抽取器）、`2046-2049` | 半可接受（僅這兩類失效） |
| 5 | 逐字稿非「`[start-end] 發言者：`」段落列 | number／date 期望 0 | `backend/services/summarization.py:1809-1822`、`1840-1901` | 半可接受（僅這兩類失效） |
| 6 | `LOCAL_LLM_RECORD_COVERAGE_CATEGORIES` 設成子集 | 只保護子集（其餘類別不比） | `backend/services/summarization.py:1937-1941`、`3223-3228` | 可接受（設定者須知情＝縮小保護範圍） |
| 7 | 同上設成空字串／全未知類別 | 無 expected 鍵 ⇒ 快照 `None` | `backend/services/summarization.py:1937-1941`；探針 E | 可接受（設定錯誤＝等於關掉） |
| 8 | 期望集合中途變動 | 基準不同不可比 ⇒ 停用比較（log＋交付最後一版） | `backend/services/summarization.py:3463-3470`；測試 T06 `253-270` | 可接受（防禦路徑；輸入常數下不易發生） |
| 9 | 執行中快照消失 | 同上 | `backend/services/summarization.py:3456-3462`；測試 T08 `295-315` | 可接受（防禦） |
| 10 | 完全沒有補強輪（初稿零問題；或 `LOCAL_LLM_MAX_REFINEMENT_ROUNDS=0`） | 只有一版，無需比較 | `backend/services/summarization.py:3408`；`backend/core/config.py:280-283` | 可接受 |
| 11 | `LOCAL_LLM_RECORD_COVERAGE_ITEM_LIMIT` 截斷 | **不會**使守衛不作用：身分清單為完整清單；`ITEM_LIMIT` 只截「問題字串／log 顯示」 | 完整清單：`backend/services/summarization.py:2046`、`2074-2077`、`2106-2109`；顯示截斷：`1995-1999`；探針 D（`ITEM_LIMIT=1` 仍得 3 筆身分） | 非失效情境（特別澄清） |
| 12 | 雲端（Gemini/Ollama Cloud）路徑 | 守衛只掛地端 pipeline | `backend/services/summarization.py:526-529`；雲端迴圈 `4647` 無此守衛 | 已知範圍（本波設計限定） |
| 13 | 非核心維度回退（忠實度／長度／待辦） | 刻意只比核心四類（防「用捏造換事實」） | `backend/services/summarization.py:3402-3403`、`3235-3255` | 已知界線（設計） |
| 14 | `observe` 模式且無其他問題觸發補強 | 沒有任何輪次 ⇒ 無候選可比 | `backend/services/summarization.py:3408`（`while issues`）；`2131` | 可接受（單一版本無回退問題） |

## 4. 殘餘風險與建議（本審查不動手）

1. **R1（最大）｜不作用時缺乏單一總結訊號**：期望集合為 0／`off` 時守衛靜默（無守衛自身 log；只有既有類別 warning）。使用者可能誤以為「有保護」。最小修法（additive、低風險）：在 pipeline metrics 行（`backend/services/summarization.py:3506-3519`）加一個 `guard=` 欄位（`active`／`disabled_no_expected`／`disabled_mode_off`／`disabled_by_config`）。
2. **R2｜換句話說造成的回退誤判**（Q5）：誤判發生時最壞是「維持前一版」。若要再降：在回退前做二次複核（例如數字加中文數字正規化、議題用 `_topic_terms_cover` 放寬重判）——但會放寬洗白風險，建議先累積觀察資料再校準，不要貿然調門檻。
3. **R3｜保證上限＝對帳器精度**：守衛只保證「對帳器看得出來的事實」不變少；判定器認不得的寫法（中文數字、特殊單位）不在保證內。此為機制本質，建議在驗收文件明示。
4. **不建議**：改預設值（`enforce`／`True`）、或把忠實度／長度一起納入回退比較（會引入反向交易風險，`3402-3403` 已說明）。

## 5. 未驗證項

- Windows＋Ollama 實機：本機只有 macOS ⇒ `[UNVERIFIED]`（依指示明說）。
- 真 E2E／ASR／模型推論：未跑（依指示）；`data/cache/e2e/p7a-gemma31b-e7c/` 未觸碰。
- 「`off` 模式真機 backend.log 逐字等於 P6-A 基線」：靜態上本波未在 off 路徑新增任何 log 寫點，且 T05/T10/T12 覆蓋交付版本／無守衛 log／與無守衛 stub 的逐字一致（wall-clock 除外）⇒ 高信心 [VERIFIED]；但**未**做真機全 log diff（低風險殘餘）。
- 真實模型上「換寫法 → 誤判回退」的發生率：機制已證實（Q5），機率未量測 ⇒ `[UNVERIFIED]`。
- `observe` 模式「問題清單零變化但交付版本可被守衛更換」的契約修訂：程式碼與設定描述一致（`backend/core/config.py:636-644`、`backend/services/summarization.py:3214-3217`、測試 T09）——[VERIFIED]，但屬**語意變更**事項，建議在驗收文件明示已獲使用者確認（不由本審查判斷）。

