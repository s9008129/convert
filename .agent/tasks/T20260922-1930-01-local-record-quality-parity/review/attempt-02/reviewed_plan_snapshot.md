# T20260922-1930-01-local-record-quality-parity — PLAN（第三波：P1 品質修正）

- TASK_ID: `T20260922-1930-01-local-record-quality-parity`
- PLAN_REVISION: 3（rev 1＝v4.8.0 修正波、rev 2＝初版 P1 計畫、rev 3＝依 Stage 02 審查十項必要修改重寫）
- TASK_CLASS: STANDARD
- REVIEW_REQUIRED: YES（新增紀錄級後處理、新型補強問題、提示詞規則＝影響輸出行為）
- INDEPENDENT_ACCEPTANCE_REQUIRED: YES
- E2E_REQUIRED: YES（真實音檔 ＋ 使用者真實模板 `section_meeting`）
- 對應分支：`fix/local-lmstudio-record-quality`
- 審查記錄：`.agent/tasks/T20260922-1930-01-local-record-quality-parity/review/attempt-01/`（`PLAN_REVISION_REQUIRED`，本版逐項回應）

## 0. 使用者場景（本波的第一性原理錨點）

使用者在 Mac 上用 LM Studio 跑 `qwen3.8-27b-splash`（dense 27B）與 `qwen3.6-35b-a3b-splash`（MoE 35B-A3B），
以 **科務會議（`section_meeting`）模板**產出正式會議紀錄，痛點是「品質明顯不如雲端 Gemini」。

**已驗證的場景事實（本版新增，rev 2 未載）**：
- 使用者手動產出的兩份實檔 `data/outputs/0903-科務會議_b20c90a7.md`（27B, 17:47）、`0903-科務會議_836fcae7.md`（MoE, 17:59）
  都是 **`section_meeting` 格式**（標題「科務會議紀錄」＋四欄彙整表＋「一、科長轉知」＋「二、科長指示及提醒事項」）。
  → 使用者的真實模板就是 `section_meeting`，不是 `general`。
- 這兩份實檔都在 **v4.8.0（commit `48ad6d6`, 18:42）之前**產生，也就是「地端一體適用雲端紀錄契約（出處標註規則）」
  尚未進到地端路徑時跑出來的。→ **「地端 0 出處標註」目前仍未被任何一次 section_meeting 執行量測過**（本波 attempt-03 基線正在量）。
- 兩份實檔的確定性量測：`_SOURCE_TAG_PATTERN` 命中數 = **0**（b20c90a7 2,394 字 / 836fcae7 2,739 字）。
- 兩份實檔的可見錯誤是 **ASR 同音誤辨的原樣沿用**：`雞查股`（正：稽查股）、`增收股`（正：徵收股）、
  `潛水管理股`、`煙酒為神穀`、`科原`、`人事總數`（正：人事總處）、`瑞裏/瑞里`。

## 1. Goal Contract（白話）

**主要目標（CORE）**：地端 `section_meeting` 紀錄的**可查核性與忠實度**接近雲端 Gemini 基準：

- CORE-1 出處標註：正文指示／裁示條目帶「（發言者N，hh:mm:ss）／（科長，hh:mm:ss）」標註（目前 = 0）。
- CORE-2 專名忠實度：ASR 同音誤辨不得原樣流入正式紀錄（以可確證的固定誤辨表確定性修正）。
- CORE-3 不得捏造：紀錄不得出現逐字稿與詞彙表都沒有的機關／股別／單位專名，也不得把建議錯歸給某人。

**次要（SUPPORTING）**：

- SUPPORTING-1 驗收基建：E2E 以 `section_meeting` 為驗收場（W1，**已實作＋已測**，見 §3）。
- SUPPORTING-2 `general` 模板的「決議 vs 主席裁示」逐條重複抑制（使用者 13:49 失敗場用的是 `general`）。
- SUPPORTING-3 覆蓋率：**降級為 SUPPORTING**（無可重跑的儀器；需擁有者人工評分），不作為本波閘門。

**僅盡力（BEST_EFFORT）**：27B 模型的 E2E（單場約 17 分鐘，且需切換 LM Studio 已載入模型）；
`temperature 0.7 vs 0.3` 的 A/B；雲端基準同版重跑。

**全域阻斷（veto）原則**：本波只有 CORE-1～CORE-3 具阻斷力；SUPPORTING／BEST_EFFORT 項目失敗不得阻擋 CORE 收斂。

## 2. 根因（修訂版）

| ID | 根因 | 關鍵證據 | 目標 |
|---|---|---|---|
| R6 | **E2E 驗收場用 `general`，不是使用者的 `section_meeting`**；`speaker_traceability` 只在模板開啟時注入 | `templates.py:384` `section_meeting=True`／`general=False`；attempt-02 `task_final.json` `template_id=general`；使用者實檔是 section_meeting | SUPPORTING（W1） |
| R7 | 紀錄級後處理沒有跨章節重複抑制；「決議」與「主席裁示事項」逐條重複 | attempt-01：10/10 逐條重複（切除尾端 metadata 後相等，約佔全文 26%）；**僅 general 模板有此兩節**（`templates.py:211/256`；`section_meeting` 無） | SUPPORTING（W5） |
| R8 | 無「禁捏造」規則與專名／歸屬絆索 | attempt-02 捏造 6（自創會議名稱「科內行政會議紀錄」、自創股名「美聯股」）；評分 1→6 | CORE-3（W4） |
| R9 | 覆蓋率退步（77.8%→66.5%）無回歸防治 | 缺口：組織編制／瑞里宣導／廉政人事／搬遷黴味 | SUPPORTING-3（本波僅登記，不閘門） |
| R10 | **ASR 同音誤辨原樣流入正式紀錄**（本版新增） | 使用者實檔：`雞查股`／`增收股`／`人事總數`／`瑞裏`；`SECTION_MEETING_GLOSSARY_CORRECTIONS` 只有 8 條通用詞（課務會議、列冠…），不含本案誤辨；校正引擎注入的是**逐字稿**層（`task_processor.py:262` `template_glossary_block`），本波不動共用校正層 | CORE-2（W3） |
| R11 | 地端出處標註遵循度**未被量測**（規則 18:42 才進地端；唯一地端 section_meeting 實檔在 17:47/17:59） | 兩份使用者實檔 tags=0 但皆為 v4.8.0 之前產物；attempt-03 基線（現行碼 + section_meeting）正在量測 | CORE-1（W2） |

## 3. 工作項（最小完整集）

### W1（SUPPORTING・**已完成實作，待測試收斂**）
`scripts/e2e/run_owned_e2e.py` 新增 `--template`（送 `meeting_template` 表單欄位）＋終態驗證 `task_final.template_id` 相符才 `template_applied=True`（不符即 FAIL；`--template` 時進入 required）。
`tests/test_owned_e2e_acceptance.py` 已有兩個測試（`test_template_argument_is_posted_and_verified`、`test_template_mismatch_must_fail_verdict`）。
**修訂**：rev 2 誤記為「未實作」，本版改記實作完成，Stage 04 只需重跑該檔測試確認綠燈。

### W2（CORE-1：出處標註強化，**local-only**）
- 位置：`backend/services/summarization.py` `_build_record_generation_message`（1268）與 `_build_record_refinement_message`（1314）。
- **明示本波為 local-only**：兩支 builder 新增 `mode: str = "cloud"`（或等價旗標 `local_examples: bool = False`）參數；
  僅地端呼叫端（`_resolve_final_generation_message` 1626／`_resolve_final_refinement_message` 1649）傳 `mode="local"`。
  雲端 `_summarize_with_gemini` 呼叫端不改 → **雲端提示詞 byte 級不變**，§8.3 的雲端 C 欄基準仍有效。
- 內容：地端追加**一個具體樣例**（3 行內），示範「句末標註」的正確寫法，例如：
  `1.各股須於下週一下午完成內機檢查。（科長，00:12:04）`
  理由（第一性原理）：規則只有抽象描述時，27B/35B 的遵循率不穩；Gemini 的 A/B 顯示「格式化描述」有效，
  但地端模型需要**範例**（few-shot）才能對齊輸出分佈。
- 同時修正 `_speaker_traceability_rule`（1258）已過時的 docstring（現寫「地端生成訊息完全不呼叫本方法」，v4.8.0 起已不成立）。
- 量測：新工具（W6）對下載回來的紀錄計數 `_SOURCE_TAG_PATTERN`。

### W3（CORE-2：ASR 固定誤辨的確定性修正，**local-only**）
- 新註冊表：`backend/core/prompt_templates/section_meeting.py` 新增 `SECTION_MEETING_RECORD_TERM_FIXES`（**與共用 `SECTION_MEETING_GLOSSARY_CORRECTIONS` 分離**，後者注入的是逐字稿校正層、雲端也會吃到；本波不得改動雲端輸入）。
- 新函式：`backend/core/text_postprocess.py` 新增 `apply_record_term_fixes(text, fixes) -> tuple[str, list[tuple[str, str]]]`（純函式、可單測；沿用 `apply_official_term_fixes`（201）的形狀）。
- 首波只收**可確證**的同音誤辨（來源＝使用者實檔＋逐字稿交叉比對，且修正後術語為真實機關用語）：
  `雞茶股→稽查股`、`雞查股→稽查股`、`增收股→徵收股`、`人事總數→人事總處`、`瑞裏→瑞里`（`瑞里` 為嘉義縣梅山鄉地名）。
  **不收**無法確證者（`煙酒為神穀`、`潛水管理股`、`科原`）→ 列入 §6 殘餘缺口，需擁有者確認後另案。
- 接線：`SummarizationService._finalize_record_text(..., mode="local")` 內、`finalize_record` 之後呼叫；
  雲端 `_finalize_cloud_record_text` 不啟用 → 雲端輸出 byte 級不變。
- 量測：W6 工具回報「已知誤辨字串命中數」；CORE-2 通過條件＝E2E 輸出中上述誤辨字串為 0。

### W4（CORE-3：禁捏造規則＋忠實度絆索，**local-only**）
- 提示詞：地端生成／補強訊息追加 2 行規則（會議名稱／機關／股別／單位專名必須逐字取自逐字稿，否則寫「（待確認）」；
  不得為未具名的建議指定單位或發言人）。同樣以 `mode="local"` 閘門，雲端不變。
- 絆索：`summarization.py` 新增 `_validate_local_fidelity(summary, transcript, template) -> list[str]`：
  以既有詞彙表（`template.glossary_terms` ＋ `glossary_corrections` 右側）為白名單，掃描紀錄中的
  「機關／科室／股別／單位」樣式（`[^\s]{2,8}(股|科|室|處|局|總處|管理科)`）與「X 表示／建議／指出」歸屬，
  兩者皆未出現於逐字稿與白名單者 → 產生問題字串（沿用 `list[str]` 機制，**fail-soft，只產生補強問題、不硬攔**）。
- **自訂上限**（rev 2 錯誤地宣稱沿用了 12 項上限；實際上只有待辦預覽有上限）：新增 `FIDELITY_ISSUE_PREVIEW_LIMIT = 8`，
  依「出現次數」排序後截斷，避免稀釋提示詞。
- 呼叫點：地端 `_summarize_with_local_pipeline`（2097-2104 的問題組裝處）與每輪重驗（2129-2133）。
- 能力邊界（明列，不做）：逐字稿內已存在的錯誤專名（如 `煙酒為神穀`）攔不到 → 屬 W3 的確定性修正或 §6 殘餘缺口。
- 量測：W6 工具回報「未落地專名數」；CORE-3 通過條件＝E2E 輸出的未落地專名數 = 0（白名單外），且單元測試對 attempt-02 片段命中「科內行政會議紀錄」「美聯股」。

### W5（SUPPORTING-2：跨章節重複抑制，`general` 模板・**local-only**）
- 位置：`backend/core/text_postprocess.py`（既有紀錄級後處理的家）新增
  `dedupe_cross_section_items(text, template, mode="local") -> tuple[str, int]`。
- **判準（依 Stage 02 要求寫死）**：
  1. 只在同一份輸出的「決議」節與「主席裁示事項」節之間比對（donor＝主席裁示事項，target＝決議節的重複條目）；
  2. 正規化＝去行首編號／項目符號 → 全形/半形標點統一 → 去空白 → **切除行尾「（主辦單位…協辦單位…辦理期程…）」括號 metadata 區塊** → 去所有標點；
  3. 僅在正規化後**完全相等**、且條目含實詞（排除「（待確認）」與純管考欄位）、且**非標題**時判重；
  4. **保留 donor（主席裁示）條目（其 metadata 較完整），只移除 target（決議節）的重複條目**；被移除區塊改為單行「（與主席裁示事項重複，詳見該節）」；
  5. 全節皆重複時，該節寫「無」。
- **不製造新補強問題**：`general` 的 `extra_field_patterns` 含「辦理期程」（只在 donor 側）；因 donor 保留，`_validate_summary_quality` 的 issues **不得增加** → 以此寫回歸測試。
- **順序**：`_finalize_record_text` 內必須是**最後一步**（在 `ensure_record_structure` 與 `normalize_unfilled_placeholders` 之後），否則骨架補全會把重複寫回來。
- **實測期望值（內嵌 fixture，不可引用被 gitignore 的檔案路徑）**：
  - fixture A（取自 attempt-01 的 10 組「決議」子句與「三、主席裁示事項」條目）→ `removed == 10`，且 10 組語意相同（0 誤刪）；
  - fixture B（取自 attempt-02 的標題＋（待確認）管考佔位欄位）→ `removed == 0`（標題與佔位欄位一律不動）；
  - 反例測試：「正規化相同就刪」會誤刪 12 個標題 → 必須有測試確保標題不動、區塊內不去重。

### W6（SUPPORTING-1 延伸：可重跑的品質量測工具）
- 新增 `scripts/quality/measure_record_quality.py`（deterministic、無 LLM、可單測）：
  輸入 `--record <md|docx> [--transcript <txt>] [--template <id>]`，輸出 JSON：
  `source_tag_count`（`_SOURCE_TAG_PATTERN`）、`heading_list`、`cross_section_duplicate_pairs`（W5 判準）、
  `unsupported_entities`（W4 判準）、`known_term_fix_hits`（W3 註冊表）、`char_count`。
- 與 `check_record_output.py`（DOCX 結構）互補；**不改 `run_owned_e2e.py` 的 required 檢查語意**（不新增閘門，只在 run_summary 記 `meeting_template` 既有欄位）。
- 用途：CORE-1／CORE-2／CORE-3 的判定證據由本工具的 JSON 產出（Stage 05 直接引用）。

### W7（測試與收斂）
- 新測試檔：`tests/test_record_dedupe.py`（W5）、`tests/test_record_term_fixes.py`（W3/W6）、`tests/test_local_fidelity_tripwire.py`（W4）。
- 既有檔增補：`tests/test_t20260922_record_quality.py`（W2 提示詞規則 local-only 斷言：雲端訊息不得含新範例）、
  `tests/test_owned_e2e_acceptance.py`（W1 已存在）。
- 基準指令（實際執行、非下限）：
  `DATA_DIR="$PWD/data" uv run --no-sync pytest tests/ -q --ignore=tests/test_end_to_end.py -p no:randomly`
  （本波開工前實測：`821 passed / 2 skipped`；2 個 skip＝缺測試音檔 fixture）。
  `bash scripts/check_docs.sh`（實測 0 errors / 0 warnings）。

## 4. 共用路徑語意決策（Stage 02 第 6 項）

**本波所有紀錄級變更皆為 local-only**（W2 提示詞範例、W3 誤辨修正、W4 絆索與禁捏造規則、W5 去重）：
- 雲端呼叫端（`_summarize_with_gemini` 3140／`_finalize_cloud_record_text` 2186）**不傳** `mode="local"`；
- 因此雲端提示詞與輸出 byte 級不變，研究文件 §8.3 的雲端 C 欄（24 出處／62.5% 覆蓋）基準**仍然有效**，不需同版重跑。
- 若 Stage 04 實作時發現無法在不改雲端行為的前提下接線，即為語意契約變更 → 停止並回 Stage 01 重規劃（不得臨場放寬）。

## 5. 驗收判準與備案（Stage 02 第 4、5、7、8 項）

| 判準 | 內容 | 量測工具 | 模型 | 未達時的備案（事先定義，不在實作階段臨場改） |
|---|---|---|---|---|
| CORE-1 | section_meeting E2E 紀錄：出處標註 > 0，且 ≥50% 正文指示／裁示條目帶標註 | W6 `source_tag_count` | MoE 35B（已載入） | tags 仍為 0 → **停止並回 Stage 01 重規劃**（候選：few-shot 多樣例、標註格式簡化為「（科長 12:04）」、或語意契約變更）；不得在 Stage 04 逕自改規則 |
| CORE-2 | E2E 紀錄中 `SECTION_MEETING_RECORD_TERM_FIXES` 左側字串命中數 = 0；單元測試 fixture 由誤→正 | W6 `known_term_fix_hits` | MoE 35B | 若模型輸出仍含誤辨 → 檢查是否為**修正後又被模型於補強輪寫回**（補強輪亦須套用同一後處理；已在 W3 接線涵蓋） |
| CORE-3 | E2E 紀錄的未落地專名／歸屬數 = 0；單元測試對 attempt-02 片段命中「科內行政會議紀錄」「美聯股」 | W6 `unsupported_entities` ＋ 單元測試 | MoE 35B | 假陽性吃掉 2 輪補強預算 → 收緊白名單樣式（僅 `股|科|室|處|局`）並記錄；若仍失效，降為 SUPPORTING 並回報（不得硬攔輸出） |
| SUPPORTING-1 | `--template section_meeting` 生效（`task_final.template_id` 相符、`template_applied=True`） | 既有 runner | MoE 35B | 無（已實作） |
| SUPPORTING-2 | W5 對 fixture A 刪 10、fixture B 刪 0；`issues` 不增加 | 單元測試 | — | 若 fixture A 命中 <10 → 收緊為「僅切除尾端括號後完全相等」，不得放寬為模糊比對 |
| SUPPORTING-3 | 覆蓋率：**由擁有者人工評分**（本波不閘門、只登記） | 人工 | MoE 35B | 無 |
| BEST_EFFORT | 27B 模型同音檔 E2E | 既有 runner | 27B（需切換載入） | 需擁有者授權切換 LM Studio 已載入模型；否則記錄為未執行 |

**單次抽樣的限制（明列）**：溫度 0.7 下 run-to-run 變異大（研究 §8.5）；CORE 判定以**本波 E2E 單次結果 ＋ W6 確定性指標**為準，
並在 evidence 明確標注「單次抽樣」。要更強結論需 2 次取樣（BEST_EFFORT，另案）。

## 6. 明確不做（本波）

- 不改 `LOCAL_LLM_GENERATION_TEMPERATURE` 預設、不改任何門檻值、不改 `COMPLETED + summary_failed` 語意。
- 不動 `task_processor.py:262` 的 `template_glossary_block`（逐字稿校正層為雲端共用的輸入）。
- 不動 `task_processor.py:259` 校正引擎硬寫 `generate_local`（P1-9 另案）。
- 不新增硬攔輸出的閘門（所有絆索只產生補強問題，最終 fail-soft）。
- 不處理無法確證的誤辨（`煙酒為神穀`／`潛水管理股`／`科原`）與「逐字稿內即錯誤的專名」（留待 P1-6 或擁有者確認）。
- 不做雲端基準同版重跑（local-only 決策使其非必要）。
- 不做 coverage 自動閘門（降級為 SUPPORTING-3）。

## 7. 風險與緩解

| 風險 | 緩解 |
|---|---|
| W3 修正表寫錯（把正確詞改成錯的） | 只收「修正後為真實機關用語且與逐字稿同音」者；其餘一律不收並列為殘餘缺口 |
| W5 誤刪合法內容 | 逐字正規化＋metadata 切除後完全相同才判重；標題／佔位欄位／區塊內一律不去重；fixture 期望值寫死（10／0） |
| W4 假陽性吃掉補強輪 | 問題清單自訂上限 8 並排序；只進問題清單不硬攔；失敗即降級回報 |
| W2 提示詞膨脹 | 新增內容 ≤4 行；既有 1,200 token system prompt 內仍有餘裕（context 128K） |
| 去重／修正與骨架補全順序錯 | 明訂去重是 `_finalize_record_text` 最後一步，並以「issues 不增加」回歸測試釘住 |
| 單次 E2E 抽樣不穩 | evidence 標注單次；CORE 判準以確定性指標為主；不據單次結果宣稱全模型結論 |

## 8. 模型覆蓋聲明（Stage 02 第 7 項）

- CORE-1／CORE-2／CORE-3：以**目前唯一已載入**的 `qwen3.6-35b-a3b-splash`（MoE 35B-A3B）執行（runner 要求 `model_inventory_unique`）。
- 27B（`qwen3.8-27b-splash`）：BEST_EFFORT，需擁有者同意切換 LM Studio 載入模型；未執行即在 evidence 標記 `not_run`。
- 本波不以單一模型結果外推另一模型；兩模型的差異結論沿用既有四版本評分表（單次抽樣）。
