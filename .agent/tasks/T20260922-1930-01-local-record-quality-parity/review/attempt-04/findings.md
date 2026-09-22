# Stage 02 獨立計畫審查 — attempt-04（聚焦複審：PLAN_REVISION 6）

- 審查者：獨立子代理（fresh context，唯讀；未修改產品程式碼、測試或 plan.md）
- 受審標的：`.agent/tasks/T20260922-1930-01-local-record-quality-parity/plan.md`（PLAN_REVISION 6）
- 受審快照：`review/attempt-04/reviewed_plan_snapshot.md`（`cp` 複本，byte 相同）
  - sha256（plan.md 與快照相同）：`bbfcd0243a89c87651d32031b12133262bb6d82685158a6d3bbb78803d24f95b`（與委託指定值一致）
- 前一輪：`review/attempt-03/findings.md`（對 rev5；`PLAN_REVISION_REQUIRED`，3 項一句話級 MF＋NB-B）
- 本輪閘門：**`PLAN_APPROVED`**（僅適用 rev6 此 sha；任何後續 plan 變更即失效）
- 研究方法：以 `diff` 取得 rev5→rev6 全部 6 處 hunk；逐項回驗 MF-A/B/C 與 NB-B；對新定義逐條與程式碼接地對帳（`templates.py`、`summarization.py`）。

## 0. Goal Baseline（承 attempt-03，不變）

使用者真實路徑＝Mac ＋ LM Studio ＋ **`section_meeting`**；CORE＝彙整表標註確定性歸零（契約一致性）＋正文標註不退步（可查核性）＋可確證 ASR 誤辨歸零（忠實度）。rev6 未動 Goal Contract 與範圍。

## 1. 指定三項 MF 逐項結論

### MF-A（W6 `body_source_tag_count` 排除開頭欄位）→ **已解決**

- 證據：`plan.md:105-106`——`body_source_tag_count`（**排除表格列與開頭欄位**：`^(時間|地點|主持人|出席人員|紀錄)`，與 `summarization.py:1026-1061` 既有排除同語意）。
- 程式碼接地：`summarization.py:130` `_RECORD_HEADER_FIELD_PATTERN＝^(?:時間|地點|主持人|出席人員|紀錄)[:：]`；`summarization.py:1052-1055` 既有排除 `|` 列與開頭欄位 → 欄位集合一致，儀器不再可能被 header-only 標註騙過（>0 閘門保護成立）。
- 附註（非阻斷）：plan 記法未帶冒號，排除面為既有常數的超集（保守方向），見 §4。

### MF-B（CORE-1 閘門語意統一）→ **已解決**

- 證據：`plan.md:32-33`——閘門＝`table=0 ∧ body ≥ 1`（基線 33）；**退化防線（明訂）**：`body_source_tag_count < 17`（基線一半）→ 視為退化，回 Stage 01 重規劃（不得由實作者自行放寬）。
- `plan.md:135`（§5）同語：判準「`≥ 1`；退化防線 < 17」；未達備案「正文 = 0 或 < 17 → **回 Stage 01 重規劃**，不得臨場改規則」。
- 中間帶判定已完備：0／1..16 → Stage 01 重規劃（退化）；≥17 → PASS（比例僅 SUPPORTING-4 登記、非阻斷，`plan.md:140`）。rev5「不得退步 vs 僅 0 備案」的不一致已消失；`plan.md:44` 全域阻斷聲明與 §5 一致。

### MF-C（W2b 適用邊界）→ **已解決**

- 證據：`plan.md:68-69`——**啟用條件（明訂）**：僅當 `template.forbidden_patterns` 存在標籤含「發言來源標註」者才啟用（即 `section_meeting`；`general` 等無此契約者**完全不動表格內容**）。
- `plan.md:157`——風險表同步更新：僅模板契約禁止時啟用；單元測試含「正文標註不動」與「**general 表格不動**」兩案例（負向測試已補，符 attempt-03 最小改法）。
- 程式碼接地：`templates.py:402-410`，標籤位於 `:404`「彙整表內出現發言來源標註」，為 section_meeting 專屬 → local `general` 表格內容確定不受影響。

## 2. NB-B（W8 措辭精確化＋其他模板行為明訂）→ **已處理**（殘留 1 行引用偏差，非阻斷）

- 其他模板行為明訂 ✓：`plan.md:112-114`——新增 `TEMPLATE_REQUIRED_SECTIONS`（僅列 `section_meeting`）；`general`、未指定、**或未列於對照表的其他模板** → 行為 byte 級不變（沿用 `GENERAL_REQUIRED_SECTIONS`＋`_section_has_substance`；其他模板另記一行 log 屬已知限制）。
- 4 章節明列 ✓：`plan.md:115-116`（`一、科長轉知`、`二、科長指示及提醒事項`、`案由及承辦單位`、`散會`）。
- 殘留（非阻斷）：`一、科長轉知` 不在 `templates.py:390-400` 的 `required_section_patterns`（該處 `:391-398` 六項＝科務會議紀錄／時間／主持人／案由及承辦單位／指示及提醒／散會），實際出處為 `templates.py:440`（`RecordSectionSpec.presence_pattern`）與 `:457-461`（`docx_section_pattern`）。4 項字面已寫死、attempt-03 已以實檔模擬 4/4 通過 → 不影響實作與驗收，**不列必改**。

## 3. 新矛盾掃描（rev5→rev6，`diff` 全 6 處 hunk）

- hunk：版本註記／CORE-1＋退化防線／W2b 啟用條件／W6 排除定義＋W8 改寫／§5 CORE-1 列／§7 W2b 列。
- 交叉檢查：CORE-1 數值三方一致（13／33／17≈50% of 34）；W2b 與 §4 local-only 一致；W6 排除欄位與 `summarization.py:130` 同集合；W8 四章節與實檔一致。**未發現新矛盾**；無 scope 擴張、無 CORE/SUPPORTING 語意漂移。

## 4. 非阻斷觀察（不影響閘門，不列必改）

- W6 記法 `^(時間|地點|...)` 較 `_RECORD_HEADER_FIELD_PATTERN`（需緊接 `[:：]`）略寬：排除方向保守，實作可逕用既有常數。
- §5 未達備案「正文 = 0 或 < 17」中「0」為「< 17」子集（冗語，非矛盾）。
- NB-A（W6 白名單語句）／NB-C（`instruction_item_count` 定義）／NB-D（§0 措辭）未處理，均非阻斷、不涉 CORE 判定。

## 5. 過程觀察（唯讀發現）

- `handoff.md`（19:50）仍綁 **PLAN_REVISION 5**／sha `a9e52cc9…`，且其「正文必須 > 0」與 rev6 語意不符 → 依 Harness §9/§10，Stage 03 必須在本輪 `PLAN_APPROVED` 後**重新編譯 handoff 對齊 rev6（sha `bbfcd024…`）**，否則 Stage 04 的 revision/hash 一致性檢查必然失敗。
- 本輪閘門僅適用於 rev6（sha `bbfcd024…`）。

## 6. 查證證據（指令與輸出摘要）

```
shasum -a 256 plan.md review/attempt-04/reviewed_plan_snapshot.md
→ bbfcd0243a89c87651d32031b12133262bb6d82685158a6d3bbb78803d24f95b（兩者相同；與委託值一致）

diff review/attempt-03/reviewed_plan_snapshot.md plan.md → 6 處 hunk
（版本註記／CORE-1＋退化防線／W2b 啟用條件／W6＋W8／§5 CORE-1 列／§7 W2b 列）

backend/core/templates.py:391-398 required_section_patterns；:402-410 forbidden（標籤 :404）；
:430／:440／:446／:453 RecordSectionSpec 的存在樣式；:457-461 docx_section_pattern

backend/services/summarization.py:129 _SOURCE_TAG_PATTERN；:130 _RECORD_HEADER_FIELD_PATTERN；
:1046-1057 _validate_cloud_speaker_traceability（1052 排除 `|` 列、1054 排除開頭欄位）；
:2093／:2128 呼叫點；:2156-2175 _finalize_record_text(summary, template)

scripts/e2e/ 存在（run_owned_e2e.py）；git status：無產品程式碼／測試變更（本審查唯讀）
```

---

## 閘門結論

**`PLAN_APPROVED`**

理由：MF-A／MF-B／MF-C 三項皆已解決（各附檔案行號與程式碼接地），NB-B 已處理（僅殘留 1 行引用偏差，非阻斷），rev5→rev6 diff 全查未引入新矛盾。本核准僅適用於 PLAN_REVISION 6（sha `bbfcd0243a89c87651d32031b12133262bb6d82685158a6d3bbb78803d24f95b`）；Stage 03 需重新編譯 handoff 後方可進入 Stage 04。
