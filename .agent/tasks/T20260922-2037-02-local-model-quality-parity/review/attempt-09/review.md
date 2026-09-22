# 獨立計畫審查 — T20260922-2037-02-local-model-quality-parity（Stage 02，attempt-09）

- 受審對象：`.agent/tasks/T20260922-2037-02-local-model-quality-parity/plan.md`。
- `REVIEWED_PLAN_REVISION`：**11**（開審時為 **rev 10**；審查期間 Planner 於 02:31 依修訂單調遞增為 rev 11——delta 經本審查 **byte 級機械反推證明**＝§8.9 三列標籤＋header＋修訂紀錄，語意零變更，見「rev 11 delta 驗證」節）。
- `REVIEWED_PLAN_SHA256`：**`cc5d1ae844392e4b133db1515198eaf0d68ef510c6eb3103a855e3826f2b6a85`**（收審量測＝遞增後版）。
  - 開審量測（rev 10）：**`0243ea0d3791364c5e0a39ef21fb6d76299058c2bc8a9a2e300a64e4ffc8a538`**（該版於審查期間被 Planner 遞增取代；收審複量見文末「收尾」）。
- 審查時間：2026-09-23 02:15–02:50（Asia/Taipei）。
- 審查者：獨立 Stage 02（fresh context；read-only）。未參與本計畫修訂、未參與實作／驗收。
- 唯一寫入：`review/attempt-09/`（本檔＋`snapshot_plan.sha256`）。未修改 `plan.md`、產品碼、測試、`e2e/*`、`quality/*`、`doc/*`、`review/attempt-01`～`08`；重現實驗全寫 `/tmp/rev09/`，repo 無暫存檔。
- 環境事實：分支 `fix/qwen-local-quality-parity`、HEAD＝`c298cc8`。工作樹含 **rev 10 未提交實作**：`backend/core/text_postprocess.py`（sha `44a5de3c…`）、`backend/services/summarization.py`（`0c988b9d…`）、`tests/test_t20260922_2037_p3_parity.py`（`f0e1c7c4…`）；`quality/snap_interval_variant_check.md`（`86f323bb…`）與 `doc/規格與設計/地端會議紀錄品質對齊雲端-研究與優化規劃.md`（`ed4c2050…`）亦為工作樹版。全程未碰 port 9527、未重啟 LM Studio、未重跑 E2E（離線審查）。
- 已讀（依角色契約）：`~/.codex/prompts/02_plan_review_prompt.md`、`policies/plan-review-gate.md`、`policies/goal-alignment-design-economy.md`；`plan.md` rev 10／11（重點 §8 全節，含 §8.9）；`review/attempt-05`～`08`；`backend/core/text_postprocess.py`、`backend/services/summarization.py`、`backend/core/config.py`、`tests/test_t20260922_2037_p3_parity.py`；`quality/snap_interval_variant_check.md`（§rev 9＋§rev 10）、`quality/rev9_independent_reproduction.md`、`quality/guard_calibration.md`（§rev 9）；`e2e/attempt-D1-gemma31b-p3/*`（含 `run_notes.md`、`verify_independent.md`、`record_quality.json`、`sha256_manifest.json`）、`e2e/attempt-C1/B1/B2-*`；`quality/coverage/coverage_gemma31b_d1.md`；研究文件 §11。

## rev 11 delta 驗證（開審 rev 10 → 審查期間遞增 rev 11）

- **機械反推（byte 級）**：以 `/tmp/rev09/verify_delta.py` 對現行 rev 11 逆套用 Planner 宣稱的五處（①`:1` header `rev 11`→`rev 10`；②`:4` `PLAN_REVISION: 11`→`10`；③移除 rev 11 條目整塊（`:64-67`）；④§8.9 三列標籤還原）→ 重建檔 sha256 ＝ `0243ea0d3791364c5e0a39ef21fb6d76299058c2bc8a9a2e300a64e4ffc8a538`＝**開審實測 rev 10 值**；unified diff 恰 4 hunks（header／PLAN_REVISION／新條目 4 行／三列標籤），**數字與語意零變更**。
- **事實核（標籤更正的正確性）**：`e2e/attempt-C1-gemma31b-fix/run_notes.md` 標題＝「Gemma 4 31B **修復後** E2E」、`run_summary.json` `verdict=PASS`、runtime `data/cache/e2e/p2-gemma31b-fix-01`；`attempt-B1-moe-fix`／`attempt-B2-27b-fix` run_notes 標題亦為「**修復後** E2E」、verdict 皆 PASS；「修復前」舊樣本為 A1（`plan.md:563` 自述；A1 `actual_build_revision=4f1fb23`＝本波開出前 HEAD）。→ rev 10 的「C1＝修復前樣本」確為不實標籤，**rev 11 更正符合事實**。
- 處置：**不需另起一輪審查**（純標籤更正且已 byte 級證明）；本輪全部結論以 **rev 11** 為受審版本，R1–R3／M1–M4 之複核在 rev 11 下同樣成立（delta 不觸及該等段落）。

## Goal Baseline（先於計畫框架、從權威來源重建）

1. 使用者痛點＝Mac＋LM Studio 地端模型（`qwen3.8-27b-splash` 27B dense、`qwen3.6-35b-a3b-splash` MoE 35B-A3B；另指定實測 `gemma-4-31B-it-MLX-4bit`）用 `section_meeting` 生成的會議紀錄「品質跟雲端 Gemini 差很多」→ 要**接近雲端且可被證明**。
2. 硬性附加需求：修復機制**模型無關**、macOS（LM Studio）與 Windows 11＋Ollama 都適用；本輪使用者指定只測 27B＋Gemma。
3. 本波（P3 可查核性波）成功標準＝「修復有量尺證明（絆索有鑑別力、缺陷被量到並歸零）＋缺口被量到且公開＋**所有宣稱與實測域一致**」；不宣稱已達雲端品質（C2 雲端基線因 Gemini 503 未取得）。
4. 不得折損既有綠線：`mode="cloud"` byte 不變、閘門不低於 rev 6（`on_start_tag_ratio ≥0.95`）、測試全綠。
5. 如實性紀律：單次抽樣不得外推；不得把閘門全綠表述成品質達標；未取得雲端基線不得發布地端 vs 雲端比較。

## Top-down（目標對齊／必要性／關鍵路徑／閘門比例／失效圍堵／耦合／設計經濟）

- 目標對齊：rev 10 的三項收斂（規則 4 精度保護／§8.3 門檻／§8.8 更正）＋ M1–M4 全數對準「讓修復可被證明」的關鍵路徑，經本輪複核**收斂成立**（逐項見下）。
- 閘門比例：§8.6-7 明示**不把**地端 vs 雲端缺口設為阻斷閘門（單樣本＋近似量尺會製造 system-wide false FAIL）＝正確的閘門比例決策；反之，CORE-5（自標 `[全域阻斷]`）的驗收③與「如實界線」是本波核心宣稱，其真值必須成立（否則驗收欄位失效）——本輪 R4 即此類。
- 失效圍堵：規則 4 的域條件（`HH:MM`）＋如實界線（真實素材無秒 0 筆）圍堵成立；**規則 2 的跨段類沒有圍堵、未列已知限制、也未納入觀察值**（R4）。
- 設計經濟：R4 的最小修正為**措辭收斂＋最小 fixture／已知限制＋doc/docstring 同步**，無新依賴、無架構變更（若欲改行為則屬另一決策，見 R4）。
- 耦合與優先序：D1 證據鏈（紀錄／逐字稿／log／量尺檔）完整可重算（本輪全部重算）；未見新的不當耦合或優先序倒置。

## Bottom-up（repo 接地、契約、安全、序列、驗證）

- 實作對計畫：常數 `TAG_SNAP_TOLERANCE_SECONDS=180`／`TAG_SNAP_MAX_SHIFT_SECONDS=120`（`text_postprocess.py:758/:762`）；規則 0（`:950-952`）、規則 2（`:963-966`）、規則 4（`:986-989`）與 §8.4 文字逐條一致；守衛 `\d{2,}`（`summarization.py:162`）與 §8.3:380 一致；`LOCAL_LLM_MAX_REFINEMENT_ROUNDS=2`（`config.py:270`）與 §8.7:545-546 一致。
- 契約：`SOURCE_TAG_PATTERN` 明示接受 `HH:MM`（秒可省）→ 規則 4 的「可達輸入類」論證成立；`measure_tag_traceability` 與吸附共用閉區間語意（§8.4:445-447 的 metric_version 同步規則）。
- 驗證（本輪實跑）：`DATA_DIR=/tmp/probe_scratch uv run --frozen python -m pytest tests/ -q --ignore=tests/test_end_to_end.py` → **935 passed／2 skipped（9.53 s）**，與 §8.6-1 rev 10 實測值一致。
- 時序：D1 於 `c298cc8`（rev 9 語意）執行；rev 10 只動無秒路徑；D1 紀錄 24 個標註**全含秒** → 規則 4 對 D1 無影響（本輪自算）。rev 11 僅標籤更正。
- 安全／隱私：本波未涉；C2 失敗屬外部（Gemini 503）已如實回填。

## 逐項判定

### R1（前置 attempt-08 R1：無秒標註非冪等）— **收斂** `[VERIFIED]`

- ①無秒＋目標非整分鐘：`（科長，00:03）` 原樣保留、`kept_precision=1`、`changed=0`，二次套用 **byte 相同**（`/tmp/rev09/probe_r1.py`）。
- ②無秒＋目標為整分鐘：`00:03→00:02`（`snapped=1`），二次套用 `kept_on_start=1`、`changed=0`。
- ③含秒標註：`00:03:00→00:03:18`，二次套用 byte 相同。
- **規則 4 必要性（非恆真擺設）**：機械移除規則 4 重建 rev9sim（`HEAD_equals_rev9sim=True`，byte 同 HEAD rev 9）→ ①型案例 `00:03→00:02→00:00`＝`f(f(x))≠f(x)`；fuzz 4000 回合：真函式非冪等 **0**／rev9sim **167**（全為無秒型）。
- 實作對照：`text_postprocess.py:986-989`；宣稱域（§8.4:407-417「所有被接受的值都是不動點」＋域條件）與實測一致。

### R2（§8.3 驗收③ 數字門檻互斥）— **收斂** `[VERIFIED]`

- `plan.md:380`「不到兩位數（例『9 時』）不納入守衛（門檻＝`\d{2,}`）」；`summarization.py:162`；`tests/test_t20260922_2037_p3_parity.py:378-386`（`13600`／`17` 命中、`上午9時開始`→`[]`「個位數不納入」）。三處一致；`rg -n "不到三" plan.md` 僅剩修訂紀錄與 §8.3:381 的「rev 10 更正」說明，**無殘文互斥**。

### R3（§8.8 對 `review/attempt-05` 的記載）— **收斂** `[VERIFIED]`

- `plan.md:476-478`「受審＝**rev 6**，sha256 `3b89a437…` → `PLAN_APPROVED`」＝`review/attempt-05/review.md:4`（自稱 `PLAN_REVISION 6`、sha `3b89a437d01d9dccf7dd160b6a531815d649066a5f1375bbd134b3d8339943d6`）與 `:101-102`（`PLAN_APPROVED`）一致；且已標明係 rev 10 更正。

### R4（本輪新發現｜**阻斷**｜類型：如實性＋CORE-5 語意契約）規則 2（`snapped_nearest`）可跨段後退——與驗收③及「如實界線」互斥

- **最小重現**（`/tmp/rev09/probe_r4_final.py`；逐字稿格式與真實逐字稿相同）：
  - `[00:00:02-00:00:32] 發言者2` ／ `[00:00:32-00:01:02] 發言者1`；紀錄含 `（發言者2，00:00:34）` → `f(x)=（發言者2，00:00:02）`；落點段＝`(2, 32, 發言者2)`、**不含原時間戳 34**、Δ=**32 s 後退**、`snapped_nearest=1`、`backward_moves=1`、二次套用 byte 相同（冪等）。
  - 同型第二例 Δ=45 s（`probe_r4_final.py`）、第三例 Δ=55 s（`probe_rule2_cross.py`）；三例皆 `snapped_nearest=1`、`backward_moves=1`、冪等。
  - 對照：`HEAD`（`c298cc8`）與 `v1.0`（`b3db34a`）**輸出相同** → 非 rev 10 引入、非回歸；不影響冪等、不影響既有素材數字。
- **機理**：規則 2 的落點必為「同發言者最近段的 `start`」，而該段**必然不含**原時間戳（若含，規則 1 早已接住）→ 依**計畫自己的定義**（`plan.md:425`：跨段＝落點段落「不含」原時間戳），**所有規則 2 位移皆為跨段**；後退者即跨段後退，可套用幅度上限＝`TAG_SNAP_MAX_SHIFT_SECONDS=120`（超過則 `kept_far`）。已知五次真實執行（27B／MoE／Gemma C1／D1；log 皆 `最近段落 0`）→ 該類**未在既有材料觸發**；問題在「一般輸入」宣稱與未來判讀。
- **被否證的宣稱（rev 11 行號）**：§8.4:434（後退解釋只寫「段落內吸附」）、§8.4:441、**§8.7:556（如實界線「本波只保證『不跨段後退』與『冪等』」）**、§8.7:564（「一般輸入的保證由規則 0 的建構性論證」）、**§8.6-4③:523（驗收項「`backward_moves` 只出現在段落內吸附」）**、`plan.md:47`；程式 docstring `text_postprocess.py:893`、`:994-996`；研究文件 `doc/規格與設計/地端會議紀錄品質對齊雲端-研究與優化規劃.md:946／973／1023`。
- **計畫文字自證邊界**：§8.4:426 對已移除觀察值 `snapped_across_segment` 的「恆 0／無鑑別力」論證**只涵蓋規則 1／3**；而該觀察值的定義恰會對規則 2 亮（非結構性恆真）——顯示規則 2 從未被納入「不跨段」論證。
- **可能的辯解與本審查立場**：規則 2 落點確為該發言者的真實段首（不造假）且保冪等；本審查**不否認其善意、不要求改行為**。阻斷點是**宣稱與驗收文字**（「不跨段後退」「只出現在段落內吸附」）在可達輸入上為假。
- **影響（具體失效機制）**：①**驗收③失效**——未來 E2E／重跑若出現規則 2 後退（可達輸入：模型把某發言者時間寫在其段落尾端後數秒），驗證者依現行文字無從判 PASS／FAIL；②§8.7「如實界線」為本波對外信任根據，現為假；③W12 會把同款假宣稱 commit 進研究文件。
- **最小修正（不要求改行為）**：把宣稱限縮為「**規則 1／3 的後退落點不跨段；規則 2（同發言者最近段 ≤180 s）可能跨段後退，落點必為該發言者真實段首、且為不動點（次輪由規則 0 接住）**」——同步 §8.4:434／441、§8.6-4③、§8.7:556／564、docstring、研究文件；並以最小 fixture（如上述 case1）固定規則 2 的跨段行為（含冪等與幅度），或列為已宣告已知限制並附反例。若計畫判定此類位移是缺陷而欲消除（如「規則 2 僅在時間戳不落在**任何**真實段落內時生效」＝與規則 3 換序），屬**語意變更**，需在 §8.4 明示決策並重算受影響素材；本審查不預設該結論。
- **是否阻斷：是**。與 attempt-08 R1 同一判準：自標 `[全域阻斷]` 的 CORE 保證在**可達輸入類**被否證，且其正是驗收③的根據 → 以現行文字核准即為核准已知為假的宣稱與失效的驗收欄位。**不**阻斷 D1 證據有效性、不阻斷其他工作項、不停任何已完成之執行。

### M1–M4（attempt-08 MINOR）— **全部收斂** `[VERIFIED]`

- **M1（絆索措辭）**：§8.4:430-436＝具鑑別力絆索為①冪等②規則 0 有作用；`kept_on_start`／後退幅度／`kept_precision` 列**觀察值**；「段首命中優先」列**輔助（不可觀測）**——與 attempt-08 及獨立重現 N9 一致。本輪重跑支持：rev8sim A1 `changed=12`、其中 **9∈全域段首**、跨發言者 fixture 亮（`probe_rule0.py`）。
- **M2（`0.9333`）**：以 attempt-07 同 pair（`確認9月30日辦理瑞里發放活動` vs `本單位擬確認9月20日辦理瑞里發放活動與宣導單發放事宜`）複量＝**0.9333、判遺漏**（預設與 rev 10 local 簽名皆同，`probe_m2_verify.py`）；`0.9375` 確出自 `quality/guard_calibration.md:162`（否定同義替換「嚴禁→禁止」）→ 「誤植更正」成立。
- **M3（輪數）**：`config.py:270` `LOCAL_LLM_MAX_REFINEMENT_ROUNDS: int = Field(default=2, …)`；`plan.md:545-546`「實務上至多一輪；硬上限＝config `LOCAL_LLM_MAX_REFINEMENT_ROUNDS`＝2 輪」一致。
- **M4（可查核性閘門不受阻斷）**：`plan.md:573-574`「規則 0 保留值本身即滿足 `on_start` 分子 → 對查核性閘門不阻斷」；D1 實測 `kept_on_start=23/24`、`on_start=0.9583` 自洽（本輪重算）。
- **新互斥敘述掃描**：除 R4 外未發現新的互斥（§8.6-3「D1 ≤1 輪（C1 1／B2 2）」屬沿革文字、D1＝0 輪自洽；§8.6-4⑤與探針一致）。

### 前輪已收斂項抽樣複核（本次全部重跑，非文件抄寫）

- 冪等：D1 二次套用 `changed=0`、byte 相同；五素材 `changed=0/0/0/3/0`、二次皆 byte 相同（`probe_materials.py`）。
- 規則 0 有作用：rev8sim A1 `changed=12`／其中 9 筆∈全域段首；跨發言者 fixture 亮（`probe_rule0.py`）。
- 守衛反例與殘留：數字失真 0.5→攔；日期 `9月30日→9月20日`→判遺漏；合法改寫 0.9444→放行；殘留緊鄰反轉 1.0→放行（**已宣告**，`probe_guard.py`）。另：F3 逗號子句洗白（0.6000，已由 §8.3:368-372 宣告）與月份改寫（0.7273，未列—見 N2）實測仍放行。
- v1.0 對照 23 筆：27B／Gemma／MoE／A1／fixture＝**4/4/3/11/1＝23**（全為後退）（`probe_materials.py`）。

### D1 證據在新修訂下的有效性（本輪獨立重算）

- 標註格式：D1 紀錄 **24 個標註、無秒 0 筆**（自寫解析）→ 規則 4 對 D1 零影響。
- 產品重跑（真函式）：`changed=0／kept_on_start=23／kept_far=1／kept_precision=0`、二次套用 byte 相同。
- 閘門重算：`on_start_tag_ratio=23/24=0.9583`；`excluding_zero=18/19=0.9474`；zero tags=5。
- log 逐字對帳：`出處標註吸附 7 處（段落內 0／最近段落 0／跨發言者 7；全域段首保護 16 筆不動；往前收 7 筆／最大 75 s；不可回溯保留 0）`；`logical_generations=2`、`extraction 346.4＋final_and_refine 392.4＝738.8`；log 無「補強」字樣（＝補強 0 輪）。
- 覆蓋率：`coverage_gemma31b_d1.md`＝0.6786／0.5075（missing core 9）✓；C1 列 0.7500／0.5672（`coverage_gemma31b.md`、runtime `p2-gemma31b-fix-01`）✓；B2 0.8929／0.8209（`coverage_qwen27b.md`）✓；B1 0.8214／0.6269（`coverage_qwen35b-moe.md`）✓。
- 判定：**§8.9 全部數字與 artifacts 對得上；rev 10／11 不改變 D1 的任何數字**。

### 如實性掃描

- F2–F5（`quality/rev9_independent_reproduction.md`）皆已被**列為已知限制**、未宣稱已修好：§8.7:565-574①＝F2＋F5、②＝F3（部分）、③＝F4、④＝規則 0 語意界線；「緊鄰反轉」子案另見 §8.3:368-372（實測仍放行，與宣告一致）✓。
- `kept_precision`／`coverage` 未被講成品質改善 ✓；C2 未取得、不得發布比較 ✓；§8.6-7 禁止把閘門全綠表述為品質達標 ✓。
- 未發現其他「無條件」式過度宣稱（例外＝R4 的跨段保證）。

## 如實註記（非阻斷）

- **N1（delta 流程）**：開審後受審物被遞增（rev 10→11）；本審查以 byte 級機械反推證明 delta 集合且語意零變更，故不影響任何結論；惟「審查期間受審物變動」本身是流程風險（舊核准不得沿用）。本判定綁定 **rev 11＋`cc5d1ae8…`**。
- **N2（F3 子案清單完整性）**：§8.7:565-574② 未列「月份／單位數字改寫（`9月30日→10月30日`，實測 ratio 0.7273 洗白）」；逗號子句案已由 §8.3:368-372 宣告但未在④交叉引用。建議補入（文件完備性）。
- **N3（掃描筆數新鮮度）**：§8.4:407「真實素材（0903 各次執行，228 個標註）無秒 0 筆」＝**D1 產生前**之掃描；本輪全 records 掃描＝**252 個、仍 0 無秒**。建議標註掃描時點或更新（實質結論不變）。
- **N4（D1 觀測域）**：D1 的 7 筆吸附全屬 `cross-speaker`（規則 3）、`nearest` 0 筆——R4 的可達類未在既有材料觸發，屬**宣稱域**問題。

## 收尾

- 開審量測（rev 10，02:1x CST）：`0243ea0d3791364c5e0a39ef21fb6d76299058c2bc8a9a2e300a64e4ffc8a538`。
- 遞增後量測（rev 11，02:44 CST）：`cc5d1ae844392e4b133db1515198eaf0d68ef510c6eb3103a855e3826f2b6a85`。
- 本檔寫入後複量：**同值**（見同目錄 `snapshot_plan.sha256`）。
- 本審查未修改任何其他檔案；`review/attempt-09/` 僅含本檔與 `snapshot_plan.sha256`；全部探針寫入 `/tmp/rev09/`。

## 附錄：可重現指令（節錄）

（1）rev 10→11 delta 機械反推：

```bash
cd /Users/hsiaojohnny/dev/convert && DATA_DIR=/tmp/probe_scratch uv run --frozen python /tmp/rev09/verify_delta.py
```

（2）R1 三案＋規則 4 必要性＋fuzz：`… python /tmp/rev09/probe_r1.py`。

（3）R4 最小重現：`… python /tmp/rev09/probe_r4_final.py`；三例擴充：`… python /tmp/rev09/probe_rule2_cross.py`。

（4）五素材／v1.0 對照 23：`… python /tmp/rev09/probe_materials.py`；規則 0：`… python /tmp/rev09/probe_rule0.py`；守衛：`… python /tmp/rev09/probe_guard.py`。

（5）D1 重算：`… python /tmp/rev09/probe_d1_evidence.py`。

（6）M2 複量：`… python /tmp/rev09/probe_m2_verify.py`；門檻三處一致：

```bash
rg -n '\\d{2,}' backend/services/summarization.py tests/test_t20260922_2037_p3_parity.py
sed -n '380p' .agent/tasks/T20260922-2037-02-local-model-quality-parity/plan.md
```

（7）全套測試：

```bash
cd /Users/hsiaojohnny/dev/convert && DATA_DIR=/tmp/probe_scratch uv run --frozen python -m pytest tests/ -q --ignore=tests/test_end_to_end.py
```

## 判決

**PLAN_REVISION_REQUIRED**

阻斷項清單：**R4**（1 項；規則 2 跨段後退 vs §8.6-4③ 驗收項、§8.7:556 如實界線等多處宣稱互斥）。其餘前置項 R1／R2／R3／M1–M4 全部收斂；N1–N4 為如實註記（非阻斷）。本判定綁定 **rev 11**（sha256 `cc5d1ae844392e4b133db1515198eaf0d68ef510c6eb3103a855e3826f2b6a85`）；`plan.md` 再修訂後需 `review/attempt-10` 重新審查。
