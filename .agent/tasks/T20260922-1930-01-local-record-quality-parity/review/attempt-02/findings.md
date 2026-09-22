# Stage 02 獨立計畫審查 — attempt-02（對 PLAN_REVISION 3）

- 審查者：獨立子代理（fresh context，唯讀）
- 受審標的：`.agent/tasks/T20260922-1930-01-local-record-quality-parity/plan.md`（PLAN_REVISION 3）
- 受審快照：`reviewed_plan_snapshot.md`（`cp` 複本）
  - sha256（plan.md 與快照相同）：`3c27c540151f64a4636ff7f1f83efbe2f8611947a782222ebe2f95d51a1942ac`
- 前一輪：`review/attempt-01/findings.md`（`PLAN_REVISION_REQUIRED`，10 項必要修改）
- 閘門結論：**`PLAN_REVISION_REQUIRED`**（4 項必要修改：2 項核心、1 項權限語意、1 項事實更正）
- 研究方法：先由權威來源重建 Goal Baseline；再上而下（目標/必要性/閘門/隔離/耦合/設計經濟）與下而上（程式碼接地/契約/安全/順序/可驗證性）審查；逐項回驗 attempt-01 十項；抽樣對照程式碼行號與事實。

---

## 0. Goal Baseline（審查者重建；來源＝使用者需求、研究文件、plan §0/§1）

- 使用者在 Mac 用 LM Studio（`qwen3.8-27b-splash` 27B、`qwen3.6-35b-a3b-splash` 35B）跑**科務會議 `section_meeting`** 正式會議紀錄；痛點是品質明顯不如雲端 Gemini。
- 最痛的缺口（研究文件 §2.3/§8.5）：
  1. **可查核性**：地端出處標註 0 vs 雲端 24（人工清單 25）；現行碼是否已改善**尚未被任何 section_meeting 執行量測**（v4.8.0 規則 18:42 才進地端；兩份使用實檔 17:47/17:59 產生於之前）。
  2. **忠實度**：捏造／無據指稱（3→6，自創會議名稱、自創股名、來源錯置）＋ASR 同音誤辨原樣沿用（`雞查股`、`增收股`、`人事總數`、`瑞裏`）。
  3. 次要：重複膨脹（general 的決議＝主席裁示 10/10）、覆蓋率退步（66.5%，無可重跑儀器）。
- 使用者真實路徑＝local 模式 ＋ `section_meeting` ＋真實音檔；**E2E 驗收場必須等於使用場**。
- 期待：以確定性、fail-soft（不得硬攔輸出、不破壞既有 `COMPLETED + summary_failed` 語意）的手段，把地端 section_meeting 的可查核性與忠實度收斂到接近雲端基準。

## 1. 上而下（目標對齊、必要性、閘門、隔離、設計經濟）

- **目標對齊 ✓**：W2（提示詞 few-shot）→ CORE-1；W3（固定誤辨確定性修正）→ CORE-2；W4（禁捏造規則＋絆索）→ CORE-3；W6（可重跑量測）為 CORE 判定之必需；W1 已完成且被本波基線（attempt-03）實際使用；W5（general 去重）對應 13:49 失敗場，降為 SUPPORTING 合理。
- **必要性 ✓**：W2/W3/W4 是三個 CORE 的最小手段集；W1、W5、SUPPORTING-3 均不阻塞 CORE（§1 veto 原則正確）。
- **臨界路徑 ✓**：W6 必須先落地，Stage 05 才能引用 JSON；W2→CORE-1、W3→CORE-2、W4→CORE-3 平行；W5 可延後。W1「已完成實作，待測試收斂」與程式碼事實一致（見 §2）。
- **閘門與 veto 比例 ⚠（兩處破口）**：
  - CORE-1 的「≥50% 條目」以指定工具（W6 `source_tag_count`）**算不出來**，且備案只覆蓋「tags=0」；「tags>0 但落在彙整表」正是進行中基線已出現的失效模式（見 §4）。
  - CORE-3 備案允許「降為 SUPPORTING」——CORE 降級＝required/optional 語意變更，依 Harness 不得由實作/驗證端自我豁免（見 MF-3）。
- **失敗隔離 ✓（一處例外）**：§4 明示本波所有紀錄級變更 local-only，且「若無法在不改雲端行為下接線 → 停止並回 Stage 01」；此決策在程式面可實作（呼叫點已枚舉，見 §2）。例外：W3 的修正結果會被 W4/W6 判為「未落地專名」——此耦合未申報且會讓 CORE-3 自相矛盾（見 MF-1）。
- **耦合**：W5 與 general 模板耦合（僅 general 有「決議／主席裁示」兩節）已被正確隔離為 SUPPORTING；W3 與 W4/W6 判準耦合未處理（MF-1）。
- **設計經濟 ✓（一處小建議）**：去重放既有 `backend/core/text_postprocess.py`、驗證器作 `summarization.py` 方法正確；W6 新腳本未聲明重用既有 helpers（建議見 NB-2）。

## 2. 下而上（程式碼接地、契約、安全、順序、可驗證性）

- **行號/簽名抽樣全部吻合**（12/12）：
  - `backend/core/templates.py:384` `speaker_traceability=True`（general 未開；預設在 169）✓
  - general `決議` 樣式 `templates.py:210`、`三、主席裁示事項` 211、`extra_field_patterns`（主辦單位/辦理期程）213-215、`record_sections` 226 起 ✓（plan 寫 211/256，屬 ±2 行同段範圍）
  - section_meeting `required_section_patterns` `templates.py:391-398`（含「案由及承辦單位」表頭、「指示及提醒」、「散會」）✓
  - **section_meeting `forbidden_patterns`（templates.py:400-410）：彙整表列不得出現發言來源標註** ✓（與 CORE-1 量測設計衝突，見 MF-2）
  - `backend/services/summarization.py`：`_SOURCE_TAG_PATTERN` 129、`_validate_summary_quality` 952（`缺少{label}資訊` 檢查在 973-978）、`_speaker_traceability_rule` 1258（docstring 已過時＝plan W2 所述，成立）、builders 1268/1314、cloud wrappers 1365-1385、resolvers 1626/1649、local pipeline 問題組裝 2098-2102 與每輪重驗 2129-2133、`_finalize_record_text` 2157、`_finalize_cloud_record_text` 2186 呼叫、gemini 驗證 3177-3179/3204-3206 ✓
  - `backend/core/text_postprocess.py:201` `apply_official_term_fixes` ✓；`finalize_record` 462→`ensure_record_structure` 469、`normalize_unfilled_placeholders` 379 → W5「最後一步（在 ensure_record_structure 與 normalize_unfilled_placeholders 之後）」可實作 ✓
  - `backend/services/task_processor.py:262` `template_glossary_block`（逐字稿校正層、雲端也吃）✓；`summarization.py:619` 規劃用 refinement 骨架估算（見 NB-4）
  - `scripts/e2e/run_owned_e2e.py`：737-738（表單帶 `meeting_template`）、827-835（`template_id` 不符即 FAIL）、1248-1249（`--template` 進 required）、1258（run_summary 既有 `meeting_template` 欄位）✓；`tests/test_owned_e2e_acceptance.py:1130/1158` 兩條 W1 測試存在 ✓
  - `scripts/e2e/check_record_output.py`：`MIN_DECISION_CJK=20`（61）、`decision_patterns`（278-283）、`check_has_decisions`（525-549）✓
- **共用路徑契約**：cloud 呼叫端（3168/3198＋3177-3179/3204-3206）與 `_finalize_cloud_record_text`（2186）皆不傳 `mode="local"`；新增參數以 `= "cloud"` 預設可讓**雲端提示詞/輸出 byte 級不變**（可實作）✓；`_validate_summary_quality` 本波不改 ✓；不改 `COMPLETED + summary_failed`（§6 明示）✓。
- **`_finalize_record_text` 順序**：現行＝`normalize_unfilled_placeholders(finalize_record(...))`；W3/W5 皆掛在此函式內、驗證之前——與現行「驗證是最後一關」註記（summarization.py:2092-2093）一致 ✓。
- **可驗證性**：
  - **fixture A 實測可達 10/10**：以 W5 判準（去編號→標點統一→去空白→切除行尾 metadata 括號→去標點）重跑 attempt-01 的「決議」10 條 vs「主席裁示」10 條＝**10/10 相等**（腳本輸出，見 §8）✓；metadata 確實在 donor（主席）側較完整（多「辦理期程」）✓。
  - fixture B（attempt-02 標題＋（待確認）欄位）→0 與 W5 判準自洽（非標題＋排除純管考佔位）✓；attempt-02 型巢狀結構另有小建議（NB-3）。
  - 去重後不觸發 artifact 檢器：以模擬去重後（決議節→「無」）之 attempt-01 紀錄跑 `check_record_output.py`，仍 **VERDICT: ACCEPTED**（required_sections 14/14、has_decisions 945 字、主辦單位欄位仍在）✓。
- **安全**：無 secrets／破壞性操作；local-only 邊界明確 ✓。

## 3. 逐項對照 attempt-01 十項必要修改（rev 3 實際狀態）

| # | attempt-01 要求 | rev 3 是否解決 | 證據/備註 |
|---|---|---|---|
| 1 | W2 去重判準對真實 fixture 命中 0/10 → 定義正規化/判準/donor/target/寫死期望值 | **✓ 已解決** | plan.md:103-107（判準）、106（donor=主席裁示、target=決議）、110-113（fixture 10/0＋反例）；本審查實測 10/10 可達（§8） |
| 2 | 去重製造新補強問題（辦理期程）→ 保留 metadata＋issues 不增加回歸＋去重是最後一步 | **✓ 已解決** | plan.md:106（保留 donor metadata）、108（issues 不增加）、109（最後一步）；與 text_postprocess 結構一致 |
| 3 | R7/CORE 證據來源 general vs CORE E2E section_meeting → 依模板拆判準 | **✓ 已解決** | plan.md:51（R7 降 SUPPORTING/W5）、141-145（CORE 以 section_meeting E2E 量測）、97（attempt-02 片段僅作單元 fixture） |
| 4 | CORE-1 缺可重跑量測與失敗備案 → 新增確定性計數＋定義下一步 | **⚠ 部分解決** | plan.md:115-121（W6）＋143（備案）；但「≥50% 條目」無分母、未排除彙整表、0<tags<50% 無備案（MF-2） |
| 5 | CORE-4（覆蓋率）不可驗證 → 降 SUPPORTING 或定義可重跑代理 | **✓ 已解決** | plan.md:39、148（SUPPORTING-3，人工、不閘門） |
| 6 | 共用路徑隱性語意變更 → 申報 local-only 或 both | **✓ 已解決** | plan.md:132-137（local-only＋停止規則）；程式面可行（§2） |
| 7 | W4 未聲明模型覆蓋 → 明示 | **✓ 已解決** | plan.md:175-179（35B 為 CORE 模型；27B BEST_EFFORT；不外推） |
| 8 | 捏造絆索能力邊界＋CORE-3 量測 | **✓ 已解決（量測受 MF-1 影響）** | plan.md:96（能力邊界）、97（W6 量測）；但白名單未含 W3 修正右側（MF-1） |
| 9 | 設計經濟：去重位置、重用既有 helpers | **✓ 大致解決** | plan.md:100-101（text_postprocess）；W6 未聲明重用（NB-2，不阻斷） |
| 10 | 事實修正：(a) issues 無上限/僅 12 待辦預覽 (b) 基準指令與數字 (c) 過時行號 (d) fixture 內嵌 | **(a)(c)(d)✓；(b) 小錯** | (a) plan.md:93（FIDELITY 上限 8、更正 rev 2 說法）；(c) plan 已無 `run_owned_e2e.py:734` 引用；(d) plan.md:110（內嵌；.gitignore:54-55 證實不可引用 data/*）；(b) 實測 823/2 vs plan.md:129 寫 821/2（MF-4） |

## 4. rev 3 新矛盾與指定檢查

1. **新閘門可量測性**：CORE-1 的比值不可由 W6 產出（MF-2）；CORE-3 的 E2E 判準在 W3 修正後**必然失敗**（MF-1）；CORE-2 的「左側字串=0」由後處理保證，近乎同義反覆（NB-6，不阻斷）。
2. **local-only 可實作性**：✓ 可行（呼叫端已全部枚舉；預設參數可保雲端 byte 不變；計畫已寫「做不到就停」）。唯一注意：規劃用估算（`summarization.py:619`）不會吃到 local-only 增量，安全邊界 256 tokens 可吸收（NB-4）。
3. **W3 誤辨表是否會改錯**：方向正確（transcript context 證實 `人事總數` 處語意為「人事總處」，逐字稿 line 155）；最弱項為 `人事總數→人事總處`——「人事總數」本身是可成立的中文詞（總員額），建議語境錨定（NB-1，不阻斷）。
4. **W5 fixture 期望值自洽性**：✓ 10/0 與判準自洽（本審查實測）；巢狀結構（attempt-02 型）之「條目/標題/欄位行」界定建議補反例測試（NB-3）。
5. **W4 假陽性 bounded 程度**：機制上有界（fail-soft、只進問題清單、自訂上限 8、最多 2 輪補強）；但 (i) 白名單破口使「偽問題」變成必然（MF-1）、(ii) 降級權限未定（MF-3）。
6. **單一波完成性**：✓ 可行（W1 已完成；W2-W6 皆在既有檔案；新增 1 個量測腳本＋3 個測試檔；E2E runner 已具 `--template`）。**無工作項必須拆到下一波**；若要縮風險，W5（SUPPORTING-2、與 CORE 無耦合）可延後。

## 5. 必須修改清單（每項附可查證證據）

### MF-1（核心）W3 修正結果會被 W4/W6 判成「未落地專名」——CORE-3 自相矛盾
- 問題：W3 把紀錄改寫成 `稽查股／徵收股／人事總處`（plan.md:80），W4 絆索與 W6 `unsupported_entities` 判準是「未出現於逐字稿**與白名單**者」（plan.md:90-92、118），白名單只含既有 `glossary_terms`＋`glossary_corrections` 右側——**不含新表右側**。逐字稿裡只有錯形（`雞茶股/雞查股`、`增收股`、`人事總數`），正確形 0 次；同一支音檔的既有紀錄 `data/outputs/0903-科務會議_b20c90a7.md` 已出現「稽查股」1 次。→ 每輪驗證都會把 W3 的修正判成未落地（觸發偽補強問題、可能被要求改回誤辨），且 CORE-3 的 E2E 判準（未落地=0，plan.md:145）在現行設計下不可能達成。
- 證據：
  - `plan.md:80`（修正表）、`plan.md:90-92`（白名單）、`plan.md:118-121`（W6 判準）、`plan.md:145`（CORE-3 判準）
  - `grep -o 稽查股 data/outputs/0903-科務會議_*_逐字稿.txt | wc -l` → 0；`data/outputs/0903-科務會議_b20c90a7.md` → 1（見 §8 指令）
- 最小改法：把 W4 白名單定義改為 `template.glossary_terms ∪ glossary_corrections 右側 ∪ SECTION_MEETING_RECORD_TERM_FIXES 右側`，並明訂 W6 `unsupported_entities` 用同一白名單；加註「修正後詞與逐字稿不同屬預期，應在 evidence 標記」。

### MF-2（核心）CORE-1 的「≥50% 條目」以指定工具（W6）無法計算，且未排除彙整表標註
- 問題：(a) 判準是比值（plan.md:143），W6 只輸出 `source_tag_count`（plan.md:118-119）——沒有分母（正文指示/裁示條目數），也沒有分子（帶標註條目數），Stage 05 無從判定；(b) `_SOURCE_TAG_PATTERN` 直接掃全文會把彙整表列的標註計入，與產品契約（`section_meeting.forbidden_patterns`「彙整表內出現發言來源標註」＝補強問題；templates.py:400-410）相衝；(c) 備案只覆蓋「tags=0」，0<tags<50% 無處置——而**進行中基線已出現「tags 落入彙整表」的實況**（19:39:50 第 2 輪補強問題含「疑似機敏資訊洩漏：彙整表內出現發言來源標註」）。
- 證據：`plan.md:118`、`plan.md:143`、`backend/core/templates.py:400-410`、`data/cache/e2e/p1-baseline-01/backend.log`（19:39:50 行，見 §8）。
- 最小改法：W6 JSON 增列確定性欄位——`body_source_tag_count`（排除表格列與開頭欄位；可重用 `_validate_cloud_speaker_traceability` 的排除邏輯）與 `instruction_item_count`（例：二、科長指示及提醒事項之 `1.` 條目數）；CORE-1 判準改由此兩欄計算；補上「0<tags<50%」備案（例：回 Stage 01）。

### MF-3（權限語意）CORE-3 不得由實作/驗證端自我降級
- 問題：plan.md:145 備案寫「…若仍失效，**降為 SUPPORTING 並回報**」。CORE 降級＝ required/optional／gating 語意變更（plan.md:44：本波只有 CORE-1～CORE-3 具阻斷力），依 Harness 屬規劃決策，不得由 Stage 04/05 自我豁免；對照 CORE-1 備案（plan.md:143）已正確要求「停止並回 Stage 01 重規劃」。
- 證據：`plan.md:145` vs `plan.md:143`、`plan.md:44`。
- 最小改法：改為「降級須回 Stage 01／經擁有者核可」；或分離語意——「絆索機制」可 fail-soft（機制層），「E2E 未落地專名=0」為結果閘門（不得自我降級，未達即 replan）。

### MF-4（小，事實更正）測試基準數
- 問題：plan.md:129 寫「本波開工前實測：`821 passed / 2 skipped`」；現 tree 以同一指令實測 **823 passed / 2 skipped**（差額＝同一 commit `01e14f4` 新增的 W1 兩條測試）。
- 證據：見 §8 指令輸出。
- 最小改法：更新為 823（或註明「821＝W1 測試加入前；含 W1 測試為 823」）。

## 6. 非阻斷建議

- **NB-1（W3）**：`人事總數→人事總處` 建議加語境錨定（如「人事總數(總會|來函|寄|公告)」）或於 evidence 標記；其餘四條（雞茶股/雞查股/增收股/瑞裏）風險低。
- **NB-2（W6）**：明訂重用既有 helper（`_SOURCE_TAG_PATTERN`、`_validate_cloud_speaker_traceability` 的排除邏輯；若需條目鍵則重用 `_normalize_action_key`／`_extract_action_table_keys`），避免量測與產品判準漂移。
- **NB-3（W5）**：attempt-02 型巢狀結構中「帶值欄位行」（如 `辦理期程：10 月 14 日`）是否算「條目」未明；建議補一條反例測試（帶值欄位行不得被判重移除），或把判準文字改為「僅整行實詞條目；純欄位行不判重」。
- **NB-4（W2）**：規劃估算 `summarization.py:619` 走 cloud 預設，未計入 local-only 增量（安全邊界 256 tokens 內，非必須；若要精確可在該處傳 `mode="local"`）。
- **NB-5（事實）**：plan.md:171「1,200 token system prompt」不準：實測 `section_meeting` 系統提示詞 ≈ 1,936 tokens（`general` ≈ 1,543）；結論（餘裕充足）不變。
- **NB-6（CORE-2）**：E2E「左側字串=0」由後處理結構保證；建議 W6 增列「修正發生次數」作為輔助證據，讓 CORE-2 的 E2E 證據更有資訊量。
- **NB-7（文獻一致性）**：研究文件 §6.2 P1-2 建議「自主席裁示移除、保留決議」；rev 3 反向（保留主席裁示，因 metadata 較完整，plan.md:106）——已驗證可行（10/10、artifact 檢器仍 ACCEPTED），建議在計畫中明寫與研究文件差異之理由。
- **NB-8（基線）**：attempt-03 基線（`--template section_meeting`，19:33 起跑）完成後請存檔；W2 few-shot 的 evidence 應記錄「基線 vs 增益」，尤其要區分「正文標註」與「彙整表標註」。

## 7. 風險與仍不確定事項

- **最大不確定（未量測）**：section_meeting 地端是否把標註穩定放在**正文**。進行中基線顯示現行碼已會產生標註、但落入彙整表（觸發 forbidden 問題）——最終紀錄尚未產出；W2 是否足以把標註導回正文，仍待 E2E。
- 溫度 0.7 的 run-to-run 變異：單次 E2E ＋確定性指標的 CORE 判定可能翻盤（研究 §8.5 結論 5；計畫已揭露單次抽樣）。
- W4 假陽性（合法改寫／substring 判定寬鬆）：會消耗最多 2 輪補強預算；bounded 但真實（且 MF-1 未修前為必然發生）。
- W3 與逐字稿不一致（預期）：紀錄正確形 ≠ 逐字稿錯形；若 Stage 05 以逐字稿為「真實來源」比對，需在 evidence 明示 W3 修正對照，避免誤判為捏造。
- 27B 僅 BEST_EFFORT：未執行即在 evidence 標 `not_run`（計畫已聲明）。
- W5 在真實 general 產物（巢狀結構）之行為：fixture B 只涵蓋標題＋佔位欄位，未涵蓋帶值欄位行（NB-3）。

## 8. 查證證據（指令與輸出摘要）

```
shasum -a 256 plan.md reviewed_plan_snapshot.md
→ 3c27c540151f64a4636ff7f1f83efbe2f8611947a782222ebe2f95d51a1942ac（兩者相同）

DATA_DIR="$PWD/data" uv run --no-sync pytest tests/ -q --ignore=tests/test_end_to_end.py -p no:randomly
→ 823 passed, 2 skipped in 10.84s

bash scripts/check_docs.sh
→ 所有檢查通過（0 errors / 0 warnings）

# fixture A 實測（W5 判準）：
python3 …（去編號→標點統一→去空白→切除行尾（主辦單位…）→去標點）
→ decision items: 10 chair items: 10；after-normalization equal pairs: 10 / 10

# artifact 檢器（去重模擬）：
python scripts/e2e/check_record_output.py --md /tmp/dedupe_sim.md（決議節→「無」）
→ VERDICT: ACCEPTED；required_sections 14/14；has_decisions 945 字

# 逐字稿／實檔字串計數：
grep -o 稽查股 data/outputs/0903-科務會議_*_逐字稿.txt | wc -l → 0（徵收股／人事總處同為 0）
data/outputs/0903-科務會議_b20c90a7.md → 稽查股 1
data/outputs/0903-科務會議_836fcae7_逐字稿.txt:12（雞茶股/雞查股/增收股）、:15（瑞裏）、:155（人事總數）

# 基線跑動中（唯讀觀察）：
ps aux → run_owned_e2e.py --processing-mode local --template section_meeting …attempt-03
data/cache/e2e/p1-baseline-01/backend.log 19:39:50 → 第 2 輪補強問題含
「疑似機敏資訊洩漏：彙整表內出現發言來源標註」

# 行號抽樣（12 處）與 git 時間戳：
templates.py:169/384/391-398/400-410；summarization.py:129/952/1258/1268/1314/1626/1649/2098-2102/2129-2133/2157/2186/3177-3179；
text_postprocess.py:201/379/462/469；task_processor.py:262；run_owned_e2e.py:737-738/827-835/1248-1249/1258；
git log → 48ad6d6 18:42、01e14f4 19:33
```

---

## 閘門結論

**`PLAN_REVISION_REQUIRED`**

理由：rev 3 已解決 attempt-01 十項中的八項（#4 部分、#10(b) 小錯），方向、local-only 決策、fixtures、設計經濟與單一波可行性均成立；但 **MF-1 使 CORE-3 在設計上不可能通過且讓補強輪被偽問題佔用**、**MF-2 使 CORE-1 的比值閘門無儀器可證**、**MF-3 的 CORE 自我降級條款違反閘門權限語意**——三者皆為修訂可解（不需重規劃），修訂後即可進入 Stage 03/04。
