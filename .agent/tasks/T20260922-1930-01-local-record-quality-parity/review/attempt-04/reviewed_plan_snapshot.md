# T20260922-1930-01-local-record-quality-parity — PLAN（P1 品質波）

- TASK_ID: `T20260922-1930-01-local-record-quality-parity`
- PLAN_REVISION: 6（rev 1＝v4.8.0；rev 2＝初版 P1；rev 3＝依 attempt-01 十項重寫；rev 4＝依 attempt-02 四項 MF；rev 5＝依 attempt-03 基線縮小範圍；**rev 6＝依 attempt-03 複審三項一句話級 MF（MF-A/B/C）＋NB-B 措辭精確化**）
- TASK_CLASS: STANDARD｜REVIEW_REQUIRED: YES｜INDEPENDENT_ACCEPTANCE_REQUIRED: YES｜E2E_REQUIRED: YES（真實音檔 ＋ `section_meeting`）
- 分支：`fix/local-lmstudio-record-quality`
- 審查：`review/attempt-01/`、`review/attempt-02/`（皆 `PLAN_REVISION_REQUIRED`）
- 基線 E2E：`e2e/attempt-03/`（clean HEAD `01e14f4`、`section_meeting`、MoE 35B、439.8 s、verdict FAIL＝驗收器誤判）

## 0. 基線實測（決定本波特性的第一性原理證據）

使用者真實路徑＝Mac ＋ LM Studio ＋ `section_meeting` 模板（其手動產物皆為該格式；且其 app 實例為 9c5057b 舊版，
所以「0 出處標註」是舊版＋general 模板的合成假象，不是現行碼的能力）。

**attempt-03 基線（現行碼、單次抽樣）**：

| 指標 | 數值 | 判讀 |
|---|---|---|
| 出處標註 | 全檔 46 處＝正文 33 ＋ **彙整表 13** | 正文 33/34 = **97.1%**（可查核性已達標） |
| **彙整表標註** | **13/13 列都有** | **違反 `section_meeting.forbidden_patterns`（`templates.py:400-410`），且會原樣流入「列管資料」附件** |
| 重複條目 | **0 對** | section_meeting 無「決議 vs 主席裁示」問題（該問題僅 general） |
| 硬性捏造專名 | 0（3 筆未落地者皆為 ASR 變體重建：`稽徵股`、`徵收股`、`煙酒業務股`） | 確定性專名絆索無法區分「ASR 重建」與「捏造」→ 本波不硬做 |
| 已知 ASR 誤辨字串 | 紀錄 0 命中（逐字稿 9 命中） | 語意校正層已處理大部分；**無需**大量確定性修正 |
| 未清的補強問題 | 2 輪燒完仍有：`彙整表內出現發言來源標註`、`待辦事項遺漏 15 項` | 前者可由確定性後處理根治；後者＝覆蓋率缺口（本波只登記） |
| 耗時 | 439.8 s（extraction 58.6 / final+refine 176.6 / pipeline 235.2） | — |
| DOCX 正式性 | **FAIL（誤判）**：runner 寫死 general 章節（`run_owned_e2e.py:96`、`564-566`），實際 DOCX 是完整 section_meeting 紀錄 | 驗收器須修，否則 `--template section_meeting` 永遠不可能 PASS |

## 1. Goal Contract

**主要目標（CORE）**：地端 `section_meeting` 紀錄的**契約一致性與忠實度**，且**可被確定性量測**：

- **CORE-1**：最終紀錄的**彙整表內出處標註 = 0**（基線 13），且**正文出處標註 ≥ 1**（基線 33）。
  退化防線（明訂）：`body_source_tag_count` < **17**（基線 33 的一半）→ 視為退化，回 Stage 01 重規劃（不得由實作者自行放寬）。
- **CORE-2**：可確證的 ASR 同音誤辨不得原樣流入紀錄（`征收股/增收股→徵收股`、`人事總處` 情境、`瑞裏→瑞里`）。

**次要（SUPPORTING）**：
- SUPPORTING-1：E2E 以 `section_meeting` 為驗收場（W1 完成）＋ runner DOCX 檢查器模板感知（W8；沒有它不可能 PASS）。
- SUPPORTING-2：`general` 模板的「決議 vs 主席裁示」逐條重複抑制（W5；使用者 13:49 失敗場用的是 general）。
- SUPPORTING-3：覆蓋率（`待辦事項遺漏 15 項`）本波只登記、不閘門（需擁有者人工評分）。
- SUPPORTING-4：正文出處標註覆蓋率維持 ≥50%（基線 97.1%）＋地端 few-shot 範例導引（W2，local-only）。

**僅盡力（BEST_EFFORT）**：27B E2E（需切換 LM Studio 已載入模型）、溫度 A/B、雲端同版重跑。

**全域阻斷**：只有 CORE-1／CORE-2 具阻斷力；SUPPORTING／BEST_EFFORT 失敗不得阻擋 CORE 收斂。

**本波明確放棄（並說明理由）**：確定性「捏造專名／歸屬」絆索（原 W4）。基線顯示真實路徑的未落地專名是
**ASR 變體重建**（`稽徵股`／`徵收股`／`煙酒業務股`；逐字稿為同音錯形），字面比對必然誤判、會燒掉 2 輪補強額度；
可靠做法需要讀音層（注音／拼音近似）或語意判定，屬下一波（研究文件 P1-6），本波只由 W6 以**觀察值**輸出，不進閘門。

## 2. 根因

| ID | 根因 | 證據 | 對應 |
|---|---|---|---|
| R12 | 模型把來源標註寫進彙整表，違反模板契約；2 輪補強燒完仍留著（提示詞層無效） | attempt-03：13/13 列帶標註；log L138/L154/L170 | **CORE-1（W2b）** |
| R10 | ASR 同音誤辨（部分仍會殘留） | `征收股`（zh-TW 應為 `徵收股`）、`人事總數`、`瑞裏` | **CORE-2（W3）** |
| R13 | runner DOCX 正式性檢查寫死 general 章節 → 非 general 模板必然 FAIL | `run_owned_e2e.py:96/564-566`；attempt-03 | SUPPORTING-1（W8） |
| R6 | E2E 未跑使用者真實模板 | 已修（W1，`--template`＋`template_applied`） | SUPPORTING-1 |
| R7 | general 模板「決議 vs 主席裁示」逐條重複 | attempt-01：10/10（切除尾端 metadata 後相等） | SUPPORTING-2（W5） |
| R9 | 覆蓋率缺口（`待辦事項遺漏 15 項`未清） | attempt-03 log L170 | SUPPORTING-3（只登記） |
| R11 | 「地端 0 出處標註」是舊版 app ＋ general 模板的合成假象 | 使用者 app 環境變數 `9c5057b-dirty-e2e`；attempt-03 = 46 處 | 已釐清 |

## 3. 工作項（最小完整集）

### W2b（CORE-1，local-only）— 彙整表標註確定性移除
- `backend/core/text_postprocess.py` 新增 `strip_source_tags_from_table_rows(text, template) -> tuple[str, int]`：
  只對 `^\s*\|` 開頭的表格列移除 `_SOURCE_TAG_PATTERN` 形式的標註（含其前面的空白／頓號），其餘文字 byte 級不動。
- 接線：`_finalize_record_text(..., mode="local")`（生成後 `summarization.py:2093`、每輪補強後 `:2128` 共用）。
- **啟用條件（明訂）**：僅當模板契約本身禁止彙整表標註時才啟用——判定方式為 `template.forbidden_patterns` 中存在
  標籤含「發言來源標註」者（即 `section_meeting`；`general` 等無此契約者**完全不動表格內容**）。
- 理由：模板契約已明文禁止、提示詞 2 輪無效、且標註會原樣流入「列管資料」附件（確定性抽取不清洗）。
- 附帶效益：`_validate_summary_quality` 的 forbidden 問題消失 → 2 輪補強額度留給真正的缺口。

### W3（CORE-2，local-only）— 可確證的 ASR 誤辨確定性修正
- `SECTION_MEETING_RECORD_TERM_FIXES`（放 `backend/core/prompt_templates/section_meeting.py`，**與共用的
  `SECTION_MEETING_GLOSSARY_CORRECTIONS` 分離**，後者注入逐字稿校正層、雲端也吃）＋
  `text_postprocess.py::apply_record_term_fixes(text, fixes)`（純函式，形狀同 `apply_official_term_fixes`:201）。
- 規則（全部確定性、逐條可測）：
  1. `征收股 → 徵收股`（zh-TW 用字，非猜測）
  2. `增收股 → 徵收股`（ASR 同音；三次獨立模型輸出皆為 `徵收股`）
  3. `人事總數(?=\s*(?:Email|E-mail|電子郵件|郵件|寄|偽造|釣魚)) → 人事總處`（**語境錨定**，避免誤傷「人事總數為 45 人」）
  4. `瑞裏 → 瑞里`（嘉義縣梅山鄉地名，逐字稿層誤辨）
- **不收**（改列 §6 待擁有者確認）：`雞查股/雞茶股`（`稽查股` vs `稽徵股` 無法由證據判定；三次模型輸出不一致）、
  `煙酒為神穀/煙酒文神穀`、`潛水管理股`、`科原`（attempt-01 為「土地稅科原址」假陽性子字串）。

### W2（SUPPORTING-4，local-only）— 出處標註導引
- `_build_record_generation_message`（1268）／`_build_record_refinement_message`（1314）新增 `mode: str = "cloud"`；
  僅地端呼叫端（`_resolve_final_generation_message` 1626／`_resolve_final_refinement_message` 1649）傳 `mode="local"`。
  **雲端呼叫端不改 → 雲端提示詞 byte 級不變**。
- 地端追加 ≤3 行範例，示範標註寫在**正文句末**，並明講「**不得寫進彙整表四欄表格**」（與 W2b 互補：一個防、一個修）。
- 同時修正 `_speaker_traceability_rule`（1258）過時 docstring。

### W5（SUPPORTING-2，local-only）— general 模板跨章節重複抑制
- `text_postprocess.py::dedupe_cross_section_items(text, template, mode="local") -> tuple[str, int]`。
- 判準：只在「決議」節與「主席裁示事項」節之間；正規化＝去行首編號／項目符號→標點統一→去空白→
  **切除行尾「（主辦單位…協辦單位…辦理期程…）」metadata 區塊**→去標點；僅完全相等、含實詞、非標題時判重；
  **保留 donor（主席裁示，metadata 較完整）**，移除 target（決議節）的重複條目並以「（與主席裁示事項重複，詳見該節）」取代；
  全節皆重複寫「無」。必須是 `_finalize_record_text` 的**最後一步**。
- 期望值（內嵌 fixture，來源 `data/cache/p1-fixtures/fixtures.py`；決議 L111-120、主席裁示 L123-132）：
  `FIXTURE_A_RECORD` 移除 **10** 條、`FIXTURE_B_RECORD` 移除 **0** 條；回歸測試：dedupe 後
  `_validate_summary_quality` issues **不增加**。

### W6（量測儀器，deterministic）
- 新增 `scripts/e2e/measure_record_quality.py`（路徑依既有 `scripts/e2e/` 慣例，取代 plan rev3 的 `scripts/quality/`）。
- `--record <md>`（MD 為權威；DOCX 段落合併會失真 → SKIP 並註明）、`--transcript`、`--template`；輸出 JSON：
  `char_count`、`body_source_tag_count`（**排除表格列與開頭欄位**：`^(時間|地點|主持人|出席人員|紀錄)`，
  與 `summarization.py:1026-1061` 既有排除同語意）、`table_source_tag_count`、`instruction_item_count`、`tagged_item_ratio`、
  `cross_section_duplicate_pairs`、`known_term_fix_hits`、`unsupported_entities`（**觀察值**，不進閘門）。
- 白名單與樣式與 W3 共用同一份（不得各寫一套）。不改 `run_owned_e2e.py` 的 required 檢查語意。

### W8（SUPPORTING-1）— runner DOCX 檢查器模板感知
- `scripts/e2e/run_owned_e2e.py::validate_formal_docx_bytes` 新增 `template_id` 參數（新增模組層對照表
  `TEMPLATE_REQUIRED_SECTIONS`，目前僅列 `section_meeting`）：
  - `general`、未指定、**或未列於對照表的其他模板** → **行為 byte 級不變**（沿用 `GENERAL_REQUIRED_SECTIONS`
    ＋ `_section_has_substance`；其他模板另記一行 log 說明沿用 general 契約，屬已知限制）。
  - `section_meeting` → 取 `backend/core/templates.py:390-400` `required_section_patterns` 中**章節級**的 4 項
    （`一、科長轉知`、`二、科長指示及提醒事項`、`案由及承辦單位`、`散會`），以同語意（容忍空白樣式＋其後非空內容）判定。
- 測試：`tests/test_owned_e2e_acceptance.py` 新增 2 測試（section_meeting DOCX 不因 general 章節缺失而 FAIL；general 行為不變）。

### W7（測試與收斂）
- 新測試：`tests/test_record_dedupe.py`（W5）、`tests/test_record_term_fixes.py`（W3/W6）、
  `tests/test_record_table_tags.py`（W2b/W2）。
- 既有檔增補：`tests/test_owned_e2e_acceptance.py`（W8）、`tests/test_t20260922_record_quality.py`（W2 local-only 斷言：
  雲端訊息不得含新範例）。
- 基準指令與實測值：`DATA_DIR="$PWD/data" uv run --no-sync pytest tests/ -q --ignore=tests/test_end_to_end.py -p no:randomly`
  → **823 passed / 2 skipped**；`bash scripts/check_docs.sh` → 0 errors / 0 warnings。

## 4. 共用路徑語意決策
W2／W2b／W3／W5 全部以 `mode="local"` 閘門（雲端呼叫端不傳），**雲端提示詞與輸出 byte 級不變** →
研究文件 §8.3 雲端基準仍有效，無需同版重跑。若實作時發現做不到 → 停止回 Stage 01（不得臨場放寬）。

## 5. 驗收判準與備案

| 判準 | 內容 | 儀器 | 模型 | 未達備案（事先定義） |
|---|---|---|---|---|
| CORE-1 | E2E：`table_source_tag_count = 0`（基線 13）**且** `body_source_tag_count ≥ 1`（基線 33；**退化防線 < 17**） | W6 | MoE 35B | 表格為純確定性 → 未達即實作缺陷，修到綠燈；正文 = 0 或 < 17 → **回 Stage 01 重規劃**，不得臨場改規則 |
| CORE-2 | E2E：`known_term_fix_hits` 左側詞命中 = 0；單元測試含正／負案例（含「人事總數為 45 人」不得被改） | W6＋單元測試 | MoE 35B | 補強輪寫回 → 確認補強輪亦走同一 `_finalize_record_text`（設計已覆蓋）；否則修 |
| SUPPORTING-1 | `--template section_meeting` 生效 ＋ DOCX 正式性 PASS（verdict PASS） | runner | MoE 35B | W8 修到綠燈 |
| SUPPORTING-2 | W5：fixture A 刪 10、fixture B 刪 0、issues 不增加 | 單元測試 | — | 收緊為僅切除尾端括號後完全相等，不得放寬為模糊比對 |
| SUPPORTING-3 | 覆蓋率（`待辦事項遺漏` 項數）：**只登記**，由擁有者人工評分 | log／人工 | MoE 35B | 無 |
| SUPPORTING-4 | `tagged_item_ratio ≥ 50%`（基線 97.1%） | W6 | MoE 35B | 只登記 |
| BEST_EFFORT | 27B E2E | runner | 27B | 需擁有者授權切換載入模型；否則標記 `not_run` |

**單次抽樣限制**：溫度 0.7 變異大；CORE 判定以本波 E2E 單次結果＋W6 確定性指標為準，evidence 必須標注「單次抽樣」。

## 6. 明確不做（含本波放棄項目與理由）
- 確定性捏造／歸屬絆索（原 W4）：ASR 變體重建會誤判（見 §1），需讀音層或語意判定 → 下一波（P1-6）。
- 無法確證的誤辨（`雞查股/雞茶股`、`煙酒為神穀`、`潛水管理股`、`科原`）→ **需擁有者確認正確股名**（`稽查股` vs `稽徵股`）。
- 覆蓋率自動閘門、雲端同版重跑、溫度 A/B。
- 不改 `LOCAL_LLM_GENERATION_TEMPERATURE`、任何門檻值、`COMPLETED + summary_failed` 語意。
- 不動 `task_processor.py:262`（逐字稿校正層，雲端共用輸入）與 `:259`（P1-9 另案）。
- 不新增硬攔輸出閘門（絆索只產生補強問題，最終 fail-soft）。
- 不重構 runner 與 `check_record_output.py` 的結構檢查重複（列為 P1-11）。

## 7. 風險與緩解
| 風險 | 緩解 |
|---|---|
| W2b 誤刪正文／動到其他模板 | 只處理 `^\s*\|` 表格列；**僅在模板契約禁止彙整表標註時啟用**（`section_meeting`）；單元測試含「正文標註不動」與「general 表格不動」兩案例 |
| W3 改錯字 | 只收可確證者；`人事總數` 加語境錨定；負案例測試；其餘全部不收 |
| W5 誤刪合法內容 | 完全相等才判重；標題／佔位欄位不動；期望值寫死（10／0）＋ issues 不增加回歸 |
| W8 改壞 general | general 走原分支、既有測試不得修改；新增兩測試 |
| 固定順序錯 | `finalize_record` → `apply_record_term_fixes` → `strip_source_tags_from_table_rows` → `normalize_unfilled_placeholders` → `dedupe_cross_section_items`（最後一步） |
| 單次抽樣不穩 | evidence 標注單次；CORE 以確定性指標為主；不以外推全模型結論 |

## 8. 模型覆蓋
- CORE-1／CORE-2：以目前唯一已載入的 `qwen3.6-35b-a3b-splash`（MoE 35B-A3B）執行（runner 要求 `model_inventory_unique`）。
- 27B：BEST_EFFORT（需擁有者同意切換載入模型）；未執行即標記 `not_run`。
