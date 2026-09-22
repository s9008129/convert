# Stage 02 獨立計畫審查 — attempt-03（聚焦複審：PLAN_REVISION 5）

- 審查者：獨立子代理（fresh context，唯讀；未修改產品程式碼、測試或 plan.md）
- 受審標的：`.agent/tasks/T20260922-1930-01-local-record-quality-parity/plan.md`（PLAN_REVISION 5，160 行）
- 受審快照：`review/attempt-03/reviewed_plan_snapshot.md`（`cp` 複本）
  - sha256（plan.md 與快照相同）：`a9e52cc955920cca67ec6ffd454cad01925ce88da0c7262fb2b2e88a1ff4537e`
- 前一輪：`review/attempt-02/findings.md`（對 rev3；`PLAN_REVISION_REQUIRED`，4 項 MF）
- 本輪閘門：**`PLAN_REVISION_REQUIRED`**（3 項最小必改：MF-A／MF-B／MF-C；皆為一至兩句的定義補齊，無結構性重工）
- 研究方法：先以權威來源重建 Goal Baseline；逐項回驗 attempt-02 四項 MF；再檢查 rev5 新增項（W2b／W8／§7 順序／基線事實）與程式碼、attempt-03 實檔逐項對帳（重算標註數、模擬 W8 檢查、重跑測試）。

---

## 0. Goal Baseline（審查者重建；來源＝使用者需求、attempt-03 實測、plan §0/§1）

- 使用者真實路徑＝Mac ＋ LM Studio（`qwen3.6-35b-a3b-splash`）＋ **`section_meeting`** 模板，痛點是「品質明顯不如雲端 Gemini」。
- attempt-03 基線（現行碼、單次抽樣）已把「缺口」重畫為：
  1. 契約一致性破口：**彙整表 13 處來源標註**違反 `section_meeting.forbidden_patterns`，2 輪補強燒完仍留著（提示詞層無效）。
  2. 驗收基建破口：runner DOCX 檢查器寫死 general 章節 → `--template section_meeting` 永遠不可能 PASS（誤判）。
  3. 可查核性其實**已達標**：正文標註 33/34＝97.1%（現行碼能力，非本波新增）。
- 因此 rev5 的有效 CORE 應為：**彙整表標註確定性歸零（契約一致性）＋正文標註不退步（可查核性）＋可確證 ASR 誤辨歸零（忠實度）**，且三者皆須有可重算儀器。

## 1. 總判定（回應問題 a、b）

**(a) 是否仍有「CORE 判準不可量測／自相矛盾／誤傷既有契約」的阻斷問題？**
→ **無阻斷**。CORE-1 的兩個計數（表 13／正文 33）與 97.1% 皆可由實檔重算（§7）；W2b 與既有 forbidden 契約同構；§7 順序與 `_finalize_record_text` 現況相容；W8 讓 attempt-03 可望轉 PASS（已模擬）。
→ **但** CORE-1 儀器與 W2b 適用邊界仍有 3 個一句話級定義缺口（MF-A/B/C），依「小瑕疵→REVISION」準則判 `PLAN_REVISION_REQUIRED`。

**(b) 縮小範圍（放棄 W4 捏造／歸屬絆索）是否仍對準使用者目標？**
→ **對準，且基線證據支持此決策**：3 筆未落地專名（`稽徵股`／`徵收股`／`煙酒業務股`）逐字稿 0 命中，但逐字稿同段落有 ASR 錯形（L11 的 `雞查股/雞茶股`、`增收股/征收股`、`煙酒及稅務管理科`；L14 `瑞裏`）→ 字面白名單必然把模型的重建判成捏造並燒掉 2 輪補強，改列 P1-6（讀音層）是合理分批。
→ **需保留的補償（rev5 已具備，僅需在 evidence 明示）**：W6 `unsupported_entities` 觀察值、§6 待擁有者確認清單、Stage 05 evidence 標明「本波不閘門的不捏造殘餘風險」。

## 2. MF-1～MF-4 逐項回驗（attempt-02 → rev5）

### MF-1（W3 修正結果被 W4/W6 判成「未落地」；CORE 自相矛盾）→ **已解決（設計層）**
- rev5 移除 W4 絆索與 CORE-3 閘門（`plan.md:45-47`、`140-141`）；W6 `unsupported_entities` 明列「**觀察值**，不進閘門」（`plan.md:103`）。
- 逐項核對：`稽查股/徵收股/人事總處`（W3 右側）不再被任何閘門依賴白名單；CORE-2 的儀器用「左側詞命中」（`plan.md:130`），與修正表同源（`plan.md:104`）→ rev3 的矛盾不復存在。
- 殘留（不阻斷，NB-A）：`plan.md:104`「白名單與樣式與 W3 共用同一份」是 W4 時代用語的遺跡（W3 沒有白名單）；建議改為明確定義，避免 W6 觀察值把 W3 修正結果列成「未落地」。

### MF-2（CORE-1 比例判準無儀器、未排除彙整表）→ **閘門軸已解決；附 2 個必補定義**
- 儀器已就位：W6 輸出 `body_source_tag_count`／`table_source_tag_count`／`instruction_item_count`／`tagged_item_ratio`（`plan.md:103`）；CORE-1 閘門＝「表=0 ∧ 正文>0」（`plan.md:129`）；比例降為 SUPPORTING-4「只登記」（`plan.md:134`）。
- 可重算性已驗證（§7）：全檔 46＝正文 33＋表格 13；表格 13/13 資料列帶標註；34 條編號條目中 33 條帶標註＝97.1%。
- 彙整表排除：**✓**（獨立欄位）。開頭欄位排除：**✗ 未載明** → **MF-A**。「>0」與「不得退步（基線 33）」中間帶未定義 → **MF-B**。

### MF-3（CORE 不得由實作/驗證端自我降級）→ **已解決**
- 無 CORE-3；CORE-1 未達備案＝「表格：修到綠燈；正文 0：回 Stage 01 重規劃」（`plan.md:129`）；CORE-2＝「否則修」（`plan.md:130`）；比例僅 SUPPORTING-4「只登記」＝Plan 層決策（`plan.md:134`）。
- 全域阻斷聲明（`plan.md:43`）只列 CORE-1／CORE-2，與 §5 一致。

### MF-4（測試基準數 823）→ **已解決**
- `plan.md:119` 寫 **823 passed / 2 skipped**；本輪實測 `823 passed, 2 skipped in 9.68s`；`bash scripts/check_docs.sh` → 0 errors / 0 warnings（指令見 §7）。

## 3. rev5 新增項與指定檢查

### 3.1 W2b（彙整表標註確定性移除，local-only）
- **與 `forbidden_patterns` 同構 ✓**：forbidden＝`^\|.*（…HH:MM…）`（`backend/core/templates.py:402-410`）；strip 用 `_SOURCE_TAG_PATTERN`（`backend/services/summarization.py:129`）＝同一「括號內含時間」樣式 → strip 命中集合 ⊇ forbidden 命中集合。基線表格列中的其他括號（「（含瑞里等遠區…）」「（禮券或現金…）」）不含 HH:MM，不會被動到。
- **「驗證是最後一關」相容 ✓**：W2b 掛在 `_finalize_record_text`（產生後 `summarization.py:2093`、每輪補強後 `:2128`），其後才跑 `_validate_summary_quality`（`:2098`／`:2129`）→ forbidden 問題在進入補強前消失（附帶效益成立），驗證不會看到未定稿內容。
- **誤刪正文已圍堵 ✓**：只處理 `^\s*\|` 表格列；風險表已列單元測試「正文標註不動」（`plan.md:151`）。
- **缺口（MF-C）**：`strip_source_tags_from_table_rows(text, template)` 的 `template` 參數用途與適用模板未定義；§4 只承諾「雲端不變」（`plan.md:122-123`）。

### 3.2 W8（runner DOCX 檢查器模板感知）
- **general byte 級不變可行 ✓**：現 signature `validate_formal_docx_bytes(docx_bytes, content_disposition)`（`scripts/e2e/run_owned_e2e.py:529`）；唯一呼叫點 `:862` 位於已持有 `meeting_template` 的函式（`:695`、`:737-738`、`:1204`）；既有測試以 2 參數呼叫（`tests/test_owned_e2e_acceptance.py:570/583/608`）→ 第三參數加預設即相容；保留原分支與原訊息字串即可 byte 級不變。
- **四章節 vs `templates.py:390-400`：不完全一致**。`templates.py:391-397` 的六條＝科務會議紀錄／時間／主持人／案由及承辦單位／指示及提醒／散會；`plan.md:108-109` 的四條＝一、科長轉知／二、科長指示及提醒事項／案由及承辦單位／散會（多「科長轉知」、少標題/時間/主持人）。
- **實檔模擬（DOCX 文字抽取＋容忍空白樣式＋「其後非空」判定）**：
  - 四章節版：4/4 章節存在且其後非空（1433／595／789／6 字）→ 通過。
  - 以六條模板樣式版：亦全數通過。
  → **兩種實作都能使 attempt-03 轉 PASS**（該場唯一 failure＝DOCX 誤判＋`formal_docx_valid` 未成立）。
- 措辭與「其他模板」（procurement／isms_meeting）未定義 → **NB-B**（不阻斷）。

### 3.3 §7 固定執行順序
- **相容、可實作 ✓**：現行 `_finalize_record_text`＝`normalize_unfilled_placeholders(finalize_record(...), template)`（`summarization.py:2157-2175`；呼叫於 2093／2128；雲端 `_finalize_cloud_record_text` `:2177` 共用同一函式）。
- rev5 順序（`plan.md:155`）＝`finalize_record` → `apply_record_term_fixes` → `strip_source_tags_from_table_rows` → `normalize_unfilled_placeholders` → `dedupe_cross_section_items`（末）：
  - `finalize_record` 內含 `ensure_record_structure`（`backend/core/text_postprocess.py:462-469`）→ dedupe 必須最後，與 W5 註記一致；
  - 驗證讀 finalize 後文字（2093→2098、2128→2129）→ 不會看到未定稿內容；
  - mode 閘門：local 呼叫端傳 `mode="local"`，雲端走預設 → 雲端輸出 byte 級不變。

### 3.4 基線事實（§0、§2 R11/R12/R13）逐項與實檔核對

| 計畫宣稱 | 重算結果 | 判定 |
|---|---|---|
| 出處標註 全檔 46＝正文 33＋彙整表 13 | 46＝33＋13（`_SOURCE_TAG_PATTERN` 逐行重算） | ✓ |
| 正文 33/34＝97.1% | 編號條目（行首 `1.`／`(1)`）34 條、33 條帶標註；唯一未帶＝「1. 局長特別點名注意事項：」 | ✓（定義見 NB-C） |
| 彙整表 13/13 列都有 | 15 個 `\|` 列中 13 個資料列全部帶標註（表頭/分隔列除外） | ✓ |
| 重複條目 0 對 | `section_meeting` 無「決議 vs 主席裁示」兩節 → 結構上 0 | ✓ |
| 硬性捏造 0；3 筆未落地＝`稽徵股`／`徵收股`／`煙酒業務股` | 三字串紀錄各 1、逐字稿各 0 | ✓ |
| 已知 ASR 誤辨 紀錄 0／逐字稿 9 | 9＝{雞查股,雞茶股,增收股,征收股,煙酒為神穀,煙酒文神穀,潛水管理股}（L11）＋瑞裏（L14）＋人事總數（L154）；紀錄全 0 | ✓（可重現集合） |
| 未清補強問題＝彙整表標註＋待辦事項遺漏 15 項 | `backend.log` L138／L154（第 1/2 輪補強問題）、L170（WARNING）逐字相符 | ✓ |
| 耗時 439.8 s＝58.6／176.6／235.2 | run_summary 19:33:35→19:40:55＝439.8 s；log metrics 逐字相符 | ✓ |
| DOCX FAIL＝誤判 | 抽取 DOCX 文字含 科務會議紀錄×2／時間：／主持人：／一、科長轉知／二、科長指示及提醒事項／案由及承辦單位／散會；**無** general 三章節 | ✓ |
| R11「舊版＋general 合成假象」 | attempt-02（general）紀錄標註 0（body/table 皆 0）＋使用者 app `9c5057b` 舊版 → 兩個 0 標註來源可分離 | ✓（措辭建議 NB-D） |

## 4. 必須修改清單（每項附最小改法與可查證證據）

### MF-A（CORE-1 儀器邊界）`body_source_tag_count` 需明訂「排除表格列與開頭欄位」
- 風險：把「時間／地點／主持人／出席人員／紀錄」行內的帶時間標註計入正文 → CORE-1(a)（>0）可能被 header-only 標註騙過。基線剛好無此情形（header 行只有不帶時間的「（發言者1）」），但該行正是模型實測會放標籤的位置。
- 證據：`backend/services/summarization.py:1026-1061`（既有同契約工具刻意排除 `|` 列與 `_RECORD_HEADER_FIELD_PATTERN` 開頭欄位）；`plan.md:103` 未載排除；attempt-02 MF-2 的原始最小改法即含「排除表格列與開頭欄位」。
- 最小改法：W6 一行——「`body_source_tag_count`＝排除表格列與開頭欄位（時間／地點／主持人／出席人員／紀錄）後之 `_SOURCE_TAG_PATTERN` 計數；排除邏輯與 `_validate_cloud_speaker_traceability` 共用」。

### MF-B（CORE-1 閘門語意）統一一「>0」與「不得退步（基線 33）」
- 風險：Stage 05 對 1..32 的中間帶無判定依據（§5 備案只寫 0→回 Stage 01；§1 卻寫不得退步）。
- 證據：`plan.md:32` vs `plan.md:129`、`plan.md:134`。
- 最小改法：改為「閘門＝正文 > 0；基線 33 僅為參考值；0→回 Stage 01；1..32→僅由 SUPPORTING-4 登記、不阻斷」；或明訂「≥33 為閘門」並補上 1..32 的備案。

### MF-C（W2b 適用邊界）明訂只在模板契約含「彙整表標註禁止」時啟用
- 風險：`_finalize_record_text` 是地端／雲端共用函式（`summarization.py:2157`、`:2172-2186`），只靠 `mode="local"` 閘門；若 strip 對所有 local 模板生效，local general（或其他模板）表格內帶時間括號會被移除——§4 只承諾雲端不變，未申報此 local 範圍變更。
- 證據：`plan.md:63-69`（W2b 未定義 `template` 參數用途／適用模板）、`plan.md:122-123`（僅雲端不變）、`plan.md:151`（以模板契約作理由）。
- 最小改法：W2b 加一句「僅當 `template` 的契約含彙整表標註禁止（本波＝`section_meeting`）時啟用；其他模板 local 行為不變」＋一個非目標模板的負向測試。

## 5. 非阻斷建議（不必須修改，但建議一併處理）

- **NB-A（W6）**：`unsupported_entities` 白名單句子（`plan.md:104`）是 W4 遺跡；建議寫明「`glossary_terms` ∪ `glossary_corrections` 右側 ∪ `SECTION_MEETING_RECORD_TERM_FIXES` 右側」，否則觀察值可能把 W3 修正結果列成「未落地」（僅影響 evidence 可讀性，不影響閘門）。
- **NB-B（W8）**：措辭「對齊 `templates.py:390-400`」不精確（見 §3.2）；「其他模板」未定義——建議明訂本波僅 `section_meeting` 分支，其餘沿用現行 general 分支（procurement／isms 未在 E2E 範圍）。
- **NB-C（W6）**：`instruction_item_count`（正文條目）定義未寫；基線 97.1% 對應「行首 `1.`／`(1)` 編號條目」34 條；建議在 W6 載明（ratio 不進閘門，僅影響可重算性）。
- **NB-D（§0）**：`plan.md:12-13`「舊版＋general 模板的合成假象」建議拆成兩個來源敘述（使用者實檔＝舊版 app；attempt-02 E2E＝general 模板、標註 0），避免誤讀。

## 6. 風險與不確定（含本波已接受者）

- **單次抽樣**：溫度 0.7 的 run-to-run 變異；CORE-1(a) 的 >0 與 ratio 皆單次（計畫已揭露，`plan.md:137`）。
- **W2 few-shot 增益未測**：正文 33/34 已是現行碼能力；W2 為「維持不退步＋導引」，其效果僅能由本波 E2E（單次）觀察。
- **不捏造不再有閘門**：本波以 W6 觀察值＋P1-6 承接；Stage 05 evidence 需明示此殘餘風險（owner-visible）。
- **W8 僅修 `section_meeting`**：其他模板（procurement／isms_meeting）若未來跑 E2E 仍會誤判（本波範圍外）。
- **W5（SUPPORTING-2）**：沿用 rev4 已驗證判準（fixtures.py:19-21 註解與計畫 L111-120／L123-132 一致），本輪不重複實測。

## 7. 查證證據（指令與輸出摘要）

```
shasum -a 256 plan.md review/attempt-03/reviewed_plan_snapshot.md
→ a9e52cc955920cca67ec6ffd454cad01925ce88da0c7262fb2b2e88a1ff4537e（兩者相同）

# 標註重算（python，_SOURCE_TAG_PATTERN 等價樣式）：
→ 全檔 46＝正文 33＋表格 13；表格列 13/13 資料列帶標註（15 列含表頭/分隔）
→ 編號條目 34（行首 1./(1)），33 帶標註＝97.1%；唯一未帶＝「1. 局長特別點名注意事項：」

# 基線字串（record / transcript）：
→ 稽徵股 1/0、徵收股 1/0、煙酒業務股 1/0（＝3 筆未落地）
→ 增收股 0/1、征收股 0/1、人事總數 0/1、瑞裏 0/1、雞查股 0/1、雞茶股 0/1、煙酒為神穀 0/1、煙酒文神穀 0/1、潛水管理股 0/1（逐字稿 9 命中；L11×7、L14、L154）

# backend.log（130-180 行段）：
→ L138 第 1 輪補強問題「…彙整表內出現發言來源標註; 待辦事項遺漏 15 項…」
→ L154 第 2 輪同上；L170 WARNING「本地摘要仍有待補強問題: …」
→ metrics：duration_seconds={'extraction': 58.6, 'final_and_refine': 176.6, 'total': 235.2}

# e2e/attempt-03/run_summary.json：
→ meeting_template=section_meeting；expected==actual="01e14f4d…"；19:33:35→19:40:55＝439.8 s
→ verdict FAIL；failure_reasons＝3 條 general 章節缺失＋缺少必要檢查 ['formal_docx_valid']

# DOCX 文字抽取（w:t 串接）＋W8 模擬：
→ 含 科務會議紀錄×2／時間：／主持人：／一、科長轉知／二、科長指示及提醒事項／案由及承辦單位／散會；無 general 三章節
→ 四章節版 4/4「存在且其後非空」（1433/595/789/6 字）；六條模板樣式版亦全過

# attempt-02（general）紀錄：
→ data/cache/e2e/v480-attempt-02/...md：標註 0（body/table 皆 0）→ 支撐 R11 的可分離來源

# 測試與文件：
DATA_DIR="$PWD/data" uv run --no-sync pytest tests/ -q --ignore=tests/test_end_to_end.py -p no:randomly
→ 823 passed, 2 skipped in 9.68s
bash scripts/check_docs.sh → 0 errors / 0 warnings

# 程式碼行號抽樣：
templates.py:381/391-397/402-410；summarization.py:129/952/1026-1061/2093/2098/2128/2129/2157-2175/2177；
text_postprocess.py:201/379/462/469；run_owned_e2e.py:96/506-527/529/564-566/695/737-738/862/1204/1244/1248-1249；
tests/test_owned_e2e_acceptance.py:570/583/608；data/cache/p1-fixtures/fixtures.py:19-21
```

---

## 閘門結論

**`PLAN_REVISION_REQUIRED`**

理由：rev5 已把 CORE 收斂為可重算、可實作的兩軸（表=0、正文>0；＋ASR 修正），基線數字與程式碼全數吻合，MF-1／MF-3／MF-4 已解決、MF-2 的閘門軸已解決；但 CORE-1 儀器（開頭欄位排除，MF-A）、CORE-1 閘門語意（>0 vs 不得退步，MF-B）、W2b 適用邊界（MF-C）仍有證據可查的定義缺口 → 依「小瑕疵→REVISION」準則不可直接放行；三項皆為一至兩句的補齊，補完後即可進入 Stage 03。

過程觀察（唯讀發現）：本輪審查期間（19:50）任務目錄出現 `handoff.md`（標題引用「review/attempt-03＝本版審查（見 gate.txt）」）。但本次 gate.txt 實為 `PLAN_REVISION_REQUIRED`；依 Harness §9，Stage 03 handoff 僅在「當前 plan revision 已滿足其 Review gate」後才成立——該 handoff 不得在 MF-A／MF-B／MF-C 修正並取得新一輪 PLAN_APPROVED 前被 Stage 04 取用。
