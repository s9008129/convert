# 獨立計畫審查 — T20260922-2037-02-local-model-quality-parity（Stage 02，attempt-08）

- 受審對象：`.agent/tasks/T20260922-2037-02-local-model-quality-parity/plan.md`（自稱 `PLAN_REVISION 9`，`plan.md:4`）。
- `REVIEWED_PLAN_REVISION`: **9**
- `REVIEWED_PLAN_SHA256`: **`f83a76878eba90524139412d7720c328e58a66e838369bab352ed90133294fe8`**（開審量測；收審複量見文末「收尾」）。
 - 審查時間：2026-09-23 01:48–01:56（Asia/Taipei）。
- 審查者：獨立 Stage 02（fresh context；read-only）。未參與本計畫修訂；未修改 `plan.md`、產品碼、測試、`review/attempt-01`～`07`、`e2e/*`、`quality/*`、`doc/*`。
- 唯一寫入：本檔（＋同目錄 `snapshot_plan.sha256`）。所有重現實驗寫 `/tmp/rev08/`，未在 repo 留暫存檔。
- 受審版本環境事實（本次綁定已提交修訂）：HEAD＝`c298cc8`；`git status --porcelain` 除平行執行中的未追蹤項 `e2e/attempt-D1-gemma31b-p3/` 外為空（本審查未觸碰該目錄、未搶 LM Studio `127.0.0.1:1234` 與 port 9527）。
- 受測實作 hash（本次審查所用，HEAD）：`backend/core/text_postprocess.py` `35d440bae26cea9347fadb2d9f11f56b5253f4fb0dbfd74072e22591d8785409`；`backend/services/summarization.py` `678017f5ae08d8587faccb030d6f53d9ec33493cde46a4ef13c035ea7921b955`；`tests/test_t20260922_2037_p3_parity.py` `87bfae9222a045ff3cb59742c21100d035f3f08fafea2c32a518507748362a56`；`tests/test_measure_coverage.py` `14d7b40c92659e2cbe429e139304c9731eea2a78bb7b4c182ff1376d22b87c94`。
- 已讀（依角色契約）：`~/.codex/prompts/02_plan_review_prompt.md`（存在）；`policies/plan-review-gate.md`、`policies/goal-alignment-design-economy.md`（`HARNESS_HOME` 對應位置）；`plan.md` rev 9；`review/attempt-05`～`07`（含 attempt-07 全文與其 `snapshot_plan.sha256`）；`quality/snap_interval_variant_check.md`、`quality/guard_calibration.md` 之 §rev 9 段（rev 8 段不混用）；`e2e/attempt-C2-cloud-baseline/`；`backend/core/text_postprocess.py`、`backend/services/summarization.py`、`backend/core/config.py`、`tests/*`；`data/cache/e2e/p2-*/backend_data/outputs/*`（真實素材）。

## Goal Baseline（先於計畫框架、從權威來源重建）

1. 使用者第一性痛點：Mac＋LM Studio 地端模型（`qwen3.8-27b-splash`；另要求實測 `gemma-4-31B-it-MLX-4bit`）生成的會議紀錄「品質非常不夠理想、跟雲端 Gemini 差很多」→ 要**接近雲端品質且可被證明**。
2. 硬性附加需求：優化機制**模型無關**；**macOS（LM Studio）與 Windows 11＋RTX 4090（Ollama）都要適用**；使用者明示**不測** `qwen3.6-35b-a3b-splash`。
3. 本波（P3）已宣告的界線：先把「可查核性與涵蓋率」量到、把機制缺陷修好、公開缺口；**不宣稱**已達雲端品質（`PRIMARY_OUTCOME` 仍 `NOT_ACHIEVED`）。
4. 依此，本波成功標準＝「修復有量尺證明（閘門有鑑別力、缺陷被量到並歸零）＋缺口被量到且公開＋沒有與實測不符的宣稱」。任何「保證」的文字都必須與實測域一致。

## Top-down（目標對齊／必要性／關鍵路徑／閘門比例／失效圍堵／耦合／設計經濟）

- 目標對齊：rev 9 的三項動作（R1 絆索重設、R3 規則 0、R2 守衛局部化）都對準「讓修復可被證明」的關鍵路徑；經本輪複核，三者在**含秒標註**輸入域內收斂成立（見「前輪三阻斷項收斂查核」）。
- 關鍵路徑：CORE-5 的量尺（回歸絆索）經實測**已非恆真**（v1.0 對照 23 筆；機械移除規則 0 後 A1 9 筆＋fixture 1 筆），前輪 R1 的「恆真閘門」問題真正解除。
- 閘門比例：§8.6-4 的四項都可對到實作／測試（詳 Bottom-up）；§8.3 驗收③有一句與 rev 9 門檻／實作／測試**互斥的殘文**（本輪 R2）＝驗收欄位本身失效，非單純錯字。
- 失效圍堵：R2 的「方向一律往更嚴＋不收斂保護」圍堵成立（代價有硬上限且已量化，見下）；**冪等宣稱的失效域（分鐘精度）沒有任何圍堵，且不在 §8.7 清單**（本輪 R1）。
- §8.7 rev 9 三項新風險檢視（使用者指定）：①「規則 0 保護的是『已為段首』這個事實、不是內容歸屬」——誠實、範圍正確，但同節 `:491`「本波只保證『不跨段後退』與『冪等』」把「冪等」再以無條件語氣宣告，正是 R1 的衝突點；②守衛盲區（含 `[UNKNOWN]` 標記）——誠實；③樣本代表性——誠實。**三項新風險本身未掩蓋阻斷**；阻斷來自①旁那句無條件「冪等」＋分鐘精度缺口缺席（R1），以及驗收③殘文（R2）。
- 設計經濟：三阻斷項的最小修正皆為局部（一句文件、幾行防護＋1 個 fixture），無新依賴、無架構變更。
- 耦合：規則 0 與 `on_start_tag_ratio` 量尺的耦合方向為「保留段首值＝分子天然成立」；不構成新的阻斷（理由見「如實註記 M4」）。

## Bottom-up（repo 接地、契約、安全、序列、驗證）

- 接地（吸附）：規則 0 在 `replace_tag` 入口（`text_postprocess.py:931-937`）先於 `_pick_containing_segment`（呼叫點僅 `:945`／`:953`）。因此：(a) `_pick_containing_segment` 的「段首優先」分支在現行呼叫圖**不可達**（任何會命中它的輸入都先被規則 0 攔下）——與實測「v1order 變體 byte 相同」一致；plan 自述其為「輔助」屬誠實，但「修正由兩層構成（單層不足）」的措辭可再精確（M1）。
- 接地（契約）：`SOURCE_TAG_PATTERN`（`:479`）與 `SOURCE_TAG_TIME_PATTERN`（`:756`）明示接受 `HH:MM`（秒可省略）；`_seconds_to_hms(target, with_seconds=False)`（`:816-822`）對無秒標註**無條件捨去秒數**（`:966-967`）。§8.4:383-385 的冪等論證（「落點一律是真實段首，第二輪必落入規則 0」）隱含假設 `parse(render(target)) == target`，此假設在無秒標註不成立（本輪 R1 反例）。
- 量尺：`measure_tag_traceability` 與吸附共用同一份閉區間語意（`:1026-1035` 區段）；`metric_version` 規則在 §8.4 明示。
- 契約（CORE-4）：`ACTION_NEGATION_TERMS`（`summarization.py:161`）、`_ACTION_NUMBER_PATTERN = re.compile(r"\d{2,}")`（`:162`）、局部句切分（`:1028`）、守衛與 log（`:1044`／`:1103`）——與 §8.3 rev 9 文字一致（除 §8.3 驗收③殘文，R2）。
- 不收斂保護（CORE-4 圍堵）：實作在 `summarization.py:2373-2395`，雙向測試成立（`tests/test_t20260922_2037_p3_parity.py:348`／`:381`）；補強總輪數硬上限＝`LOCAL_LLM_MAX_REFINEMENT_ROUNDS=2`（`backend/core/config.py:270`）。
- 安全：本次未見隱私／安全面變更；C2 失敗屬外部（Gemini 503），如實。
- 驗證：本審查實跑完整測試 `933 passed／2 skipped`（10.66s）；自寫探針見附錄。

## 逐項判定

### R1（阻斷｜類型：語意契約＋如實性）無條件冪等宣稱被「分鐘精度標註」否證
判定：**部分收斂**（含秒域收斂；宣稱域不收斂）。

- 已成立部分（新絆索非恆真、前輪 R1 真解除）：見「前輪三阻斷項收斂查核」第一條。
- **未收斂（本輪新最小反例）**：
  - 逐字稿：`[00:00:12-00:00:42] 發言者1` ／ `[00:00:42-00:02:42] 發言者2` ／ `[00:02:42-00:04:42] 發言者2` ／ `[00:03:18-00:03:19] 發言者1` ／ `[00:04:48-00:04:49] 發言者2`；紀錄含 `（科長，00:03）`。
  - 實測（`/tmp/rev08/probe5_minute_minimal.py`）：`f(x)=（科長，00:02）` → `f(f(x))=（科長，00:00）` → `f³(x)=（科長，00:00）`；`changed1=1、changed2=1`，**`f(f(x)) ≠ f(x)`**。
  - 機理：`00:03`（180s）先被規則 3 吸到段首 `162s`（`00:02:42`）；`with_seconds=False` 渲染捨去 `:42` → `00:02`（120s）；第二輪 120s 又落在較前段 `[42,162]` → 段首 `42s` → `00:00`。鏈式後退直到 `00:00`（不在任何段內、非段首）才停。
  - 隨機化 fuzz（`/tmp/rev08/probe2_fuzz.py`，4000 回合，含亂序／零長度／重疊／無秒）：非冪等 **5/4000**，全部同型（無秒標註）；「段首被改寫」反例 **0/4000**。
  - 真實素材現況（本輪掃描 `data/cache/e2e/p*/backend_data/outputs/*.md`）：**228 個標註、0 個無秒**——**今日 E2E 不受影響**；但宣稱是無條件的，影響面不改變宣稱真值。
- **宣稱衝突點**：`plan.md:383-385`（「保證 `f(f(x)) == f(x)`：吸附後再套用一次**必須** byte 級不變……冪等的**保證來源是規則 0**」＋`[VERIFIED]`，未限定含秒標註）；`plan.md:491`（§8.7「本波只保證『不跨段後退』與『冪等』」再次無條件宣稱）；`text_postprocess.py:796`（docstring「落點因此是不動點（`f(f(x)) == f(x)`）」）。
- **是否應阻斷（明確回答）**：**是**。理由：①這是本波自標 `[全域阻斷]` 的 CORE-5 之語意契約（冪等）被**可達輸入類**（產品自身樣式允許 `HH:MM`）否證；②計畫文字與程式註解以無條件語氣對外提供保證，且該保證是 §8.6-4① 驗收的根據——不修就等於核准一份已知為假的宣稱（與 attempt-03 處理「絕對語氣與實測不符」同一判準）。**不需**據此停下平行 D1 E2E（真實標註 0/228 無秒、D1 閘門仍可照跑）；阻斷的是「以現行文字核准 rev 9」。
- 最小充分修正（二擇一之組合，皆局部）：
  1. **修行為**：`replace_tag` 只在 round-trip 成立時採用 replacement（`parse(render(target)) == target`），否則原樣保留（與 `kept_far` 同精神）或改以 `HH:MM:SS` 呈現；＋ 回歸測試「無秒標註二次套用 `changed == 0`」（建議同步納入 `quality/snap_interval_variant_check.md` 的變體矩陣）。
  2. **修宣稱**：把 §8.4:383-385、`:796` docstring、§8.7:491 的冪等敘述限定「含秒（`HH:MM:SS`）標註」；在 §8.7 新增已知限制「無秒標註（`HH:MM`）：目前渲染會捨秒，重複套用可能鏈式後退；真實素材 0/228」。
  （推薦 1＋2 同時；若只做 2，至少需加 fixture 固定「鏈退」為已知行為。）

### R2（阻斷｜類型：驗收一致性／如實性）§8.3 驗收③ 與 rev 9 門檻／實作／測試互斥
判定：**未收斂（殘文）**。

- 最小實驗（唯讀）：
  ```bash
  grep -n "不到三位數" .agent/tasks/T20260922-2037-02-local-model-quality-parity/plan.md
  grep -n "_ACTION_NUMBER_PATTERN = re" backend/services/summarization.py
  sed -n '319,326p' tests/test_t20260922_2037_p3_parity.py
  ```
- 如實觀察：`plan.md:363`（§8.3 驗收③末句）仍寫「且不到三位數的數字（例 17 台）**不納入**守衛」；但同節 rev 9（`:345-346`）寫「數字門檻由 3 位**放寬為 2 位**」、實作 `summarization.py:162` 為 `re.compile(r"\d{2,}")`、測試 `tests/test_t20260922_2037_p3_parity.py:319-325` 斷言 `盤點17台冷氣運轉狀況` 對「共十七台」**必須判遺漏**（且 `17` 必須被樣式命中）。三者與 §8.3 驗收③**直接互斥**。此句位於「驗收（單元測試）」清單，屬驗收欄位語意，不是純文字。
- 最小充分修正：把 `plan.md:363` 改為「且**不到兩位數**的數字（例 9 時）不納入守衛」（可加註「國字書寫的兩位數（17 台→十七台）是已宣告代價，見 §8.7」）。

### R3（阻斷｜類型：如實性）§8.8 對 `review/attempt-05` 的記錄不實
判定：**不實（單點）**。

- 最小實驗（唯讀）：
  ```bash
  sed -n '438p' .agent/tasks/T20260922-2037-02-local-model-quality-parity/plan.md
  sed -n '4p;101,102p' .agent/tasks/T20260922-2037-02-local-model-quality-parity/review/attempt-05/review.md
  ```
- 如實觀察：`plan.md:438` 寫「`review/attempt-05`（fresh context；受審＝rev 7 快照）→ `PLAN_REVISION_REQUIRED`」；但 `review/attempt-05/review.md:4` 為 `REVIEWED_PLAN_REVISION: 6`，`:101-102` 判「**PLAN_APPROVED**」（核准綁定 rev 6，屬 P2 波；該目錄僅有 `review.md`）。rev 7 的第一份審查是 `review/attempt-06`（`:4` 亦記 rev 7）。§8.8 全節標題是「獨立審查（P3，如實）」，此列同時錯記受審修訂與判決，屬如實性缺陷。
- 最小充分修正：改為「`review/attempt-05`（fresh context；受審＝rev 6 快照）→ 判 `PLAN_APPROVED`（P2 波；P3 起自 attempt-06）」，或將該列移出 §8.8。

## 前輪三阻斷項收斂查核（attempt-07 → 本輪）

- attempt-07 **R1**（恆真絆索 `snapped_across_segment`）：**收斂**。產品碼／腳本／測試已無該值（`grep` 0 命中）；新絆索實測非恆真——
  - HEAD：5 素材「原值∈全域段首卻被改寫」＝**0/0/0/0/0**、二次套用 `changed=0`（冪等）、A1 `changed=3`（三筆皆 `00:25:21→00:24:11`、Δ70s，段內邊界吸附）。
  - v1.0（`b3db34a`）：**4/4/3/11/1＝23 筆**（與 plan `:402` 宣稱一致）；27B 二次套用 `changed=4`（非冪等）。
  - rev8sim（機械移除規則 0）：A1 `changed=12`、其中 **9 筆∈全域段首**（與 attempt-07 記載 12／9 一致）；跨發言者 fixture 被改寫 1 筆；`00:18:40` 鏈退非冪等。
  - v1order（僅把 `_pick_containing_segment` 換回 v1.0 第一命中、規則 0 保留）：4 素材輸出與 HEAD **byte 相同** → 該層在現行呼叫圖不可觀測；新絆索對「可觀察的行為退化」會亮，對「不可觀察的實作退化」不亮（M1）。
- attempt-07 **R3**（跨發言者交界退化／非冪等）：**含秒域收斂**。`[00:14:40-00:16:40] 發言者2` ／ `[00:16:40-00:23:20] 發言者1` ＋ `（發言者2，00:18:40）`：HEAD `f(x)=00:16:40`、`f(f(x))=00:16:40`（冪等）；v1.0／rev8sim 仍 `00:16:40→00:14:40`（非冪等）。邊界 fixture（同一秒被多段共用／零長度段／段表亂序／同發言者重疊）：HEAD 全數冪等；真實逐字稿零長度段 **104 筆**均正確處理。**但**無秒標註域出現新的非冪等反例（本輪 R1）。
- attempt-07 **R2**（守衛可被洗白）：**收斂（含已宣告代價）**。兩反例皆攔：語意反轉＋他處仍有「嚴禁」→ 判遺漏（實測 ratio 0.6154；未反轉原句 ratio 0.6923 放行）；`9月30日→9月20日` → 判遺漏（實測 ratio 0.9333）。真實材料：主探針 37 keys **額外假陽性 0**（18/8/11 全走 rule-1 命中，結構性 0）；真實 log 14 keys 全判涵蓋、**額外假陽性 0**（`嚴禁轉傳科內群組訊息至外部` ratio 0.6923 放行）。合成合法改寫批次 11 筆中 9 筆誤判遺漏（其中 4 筆為守衛新增：否定同義×2、避免→請勿、國字兩位數）——**全屬 §8.3／§8.7 已宣告的已知代價類**；detect 3/3 全攔。→ 無「未宣告的新 false-negative 群」；殘餘誤攔成本方向往更嚴、有硬上限（不收斂保護＋輪數上限 2，`config.py:270`），符合 §8.7 圍堵敘述。

## 本輪驗證成立的正面事實（本次查核）

- 完整測試實跑：`pytest tests/ -q --ignore=tests/test_end_to_end.py` → **933 passed／2 skipped**（與 §8.6-1 rev 9 實測值一致）；兩支 P3 測試檔 collect 34 項（19＋15）。
- §8.6-3 不收斂保護：實作＋雙向測試（`:348` 擋第 2 輪；`:381` 問題集合改變不得誤擋）；守衛攔下時 log 實帶 LCS 比例（實跑樣本：「待辦召回守衛攔下（LCS 0.62 已達門檻…）」）。
- §8.6-4 四項對實作：（①）二次套用測試 `:90`／`:109`；（②）鑑別力對照 23 vs 0（本輪複核）；（③）`backward_moves`／`max_backward_seconds` 觀察值與 A1 三筆診斷一致；（④）`measure_tag_traceability` 的 `on_start` 計數與吸附共用同一份段表語意（`:1031`）。D1 綁定項（①④於 D1 紀錄）本審查不涉入（平行執行中）。
- §8.8 對 attempt-06／attempt-07 的其餘摘要（R1「換回 v1.0 時 changed=14 它仍為 0」、R3「changed=12、其中 9 筆∈段首、例 00:13:37→00:13:12」、R2「別子句有『嚴禁』就放行」）逐點與原文一致（attempt-07 `:46`／`:76`／`:59`）。
- C2 雲端基線 FAIL（Gemini 503）如實回填（§8.2；`e2e/attempt-C2-cloud-baseline/`）；§8.6-7 明示「不把地端 vs 雲端缺口設為阻斷閘門、且不得宣稱品質已達雲端水準」維持前輪「合理」判定。

## 如實註記（非阻斷）

- M1：`_pick_containing_segment`「段首優先」在現行呼叫圖不可達（規則 0 先行；呼叫點僅 `:945`／`:953`）——v1order 變體 4 素材 byte 相同。plan 已自述其為「輔助」，建議把 §8.4「修正由兩層構成」措辭精確化為「規則 0 為保證；段首優先為防禦性輔助（現行呼叫圖不可觀測）」。
- M2：日期反例的 LCS 值：plan `:50`／`:348`／`:446` 寫 **0.9375**，attempt-07 原文（`:62`）記 **0.9333**；本輪以相同 pair 複量＝**0.9333**（多個自然 pair 皆 ≠0.9375）；0.9375 恰為 `quality/guard_calibration.md:162`「否定同義替換（嚴禁→禁止）」列之值，疑為張冠李戴。行為結論不受影響（放寬後判遺漏＝實測真），建議改引 0.9333 或標註重新量測。
- M3（carried；attempt-07 已提、rev 9 未修）：§8.7「不收斂保護（最多 1 輪）」措辭不精確——保護只擋「問題集合相同」；補強總輪數上限來自 `LOCAL_LLM_MAX_REFINEMENT_ROUNDS=2`（`config.py:270`）。不影響圍堵有效性。
- M4（使用者指定查核：規則 0 對「標註可查核性」閘門的語意風險）：**不阻斷**。理由：①`on_start_tag_ratio` 分子＝「時間戳∈任一真實段首」，規則 0 保留的值**本身即滿足**此條件，規則 0 無從壓低它（也不虛增：被保留者仍以同一分子定義計入）；②`body_source_tag_count ≥17` 是「正文標註數」計數，規則 0 不刪標註；③真正的風險是「保留但歸屬錯」，屬既有指標盲區（R25 類），§8.7 風險①已明示、§8.6-7 已禁止把閘門全綠表述為品質達標。建議 §8.7 風險①補一句「保留值同樣計入 `on_start` 分子，該閘門對『保留但歸屬錯』不敏感」即可。

## 收尾

- 開審量測：`f83a76878eba90524139412d7720c328e58a66e838369bab352ed90133294fe8`（2026-09-23 01:49 CST）。
- 收審複量（本檔寫入後）：同值（見同目錄 `snapshot_plan.sha256`）。
- 本審查未修改任何其他檔案；`review/attempt-08/` 僅含本檔與 `snapshot_plan.sha256`。全部探針寫入 `/tmp/rev08/`。

## 附錄：可重現指令（節錄）

（1）R1 分鐘精度最小反例：

```bash
cd /Users/hsiaojohnny/dev/convert && DATA_DIR=/tmp/probe_scratch uv run --frozen python /tmp/rev08/probe5_minute_minimal.py
```

（2）絆索鑑別力＋跨發言者交界（HEAD／v1.0／rev8sim／v1order 四變體）：

```bash
cd /Users/hsiaojohnny/dev/convert && DATA_DIR=/tmp/probe_scratch uv run --frozen python /tmp/rev08/probe1_snap.py
```

（3）R2 守衛真實／合成批次：`/tmp/rev08/probe3_guard.py`、`/tmp/rev08/probe4b_logkeys.py`；邊界 fixture＋fuzz：`/tmp/rev08/probe2_fuzz.py`。

（4）R2 殘文互斥三點：`grep -n "不到三位數" plan.md`；`grep -n "\\d{2,}" backend/services/summarization.py`；`sed -n '319,326p' tests/test_t20260922_2037_p3_parity.py`。

（5）R3 不實列：`sed -n '438p' plan.md` vs `sed -n '4p;101,102p' review/attempt-05/review.md`。

## 判決

PLAN_REVISION_REQUIRED
