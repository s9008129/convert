# [SUPERSEDED by rev6] HANDOFF — P1 品質波

- PLAN_REVISION: **5**｜plan.md sha256 `a9e52cc955920cca67ec6ffd454cad01925ce88da0c7262fb2b2e88a1ff4537e`
- 審查：`review/attempt-01|02`＝`PLAN_REVISION_REQUIRED`；`review/attempt-03`＝本版審查（見 gate.txt）
- 分支：`fix/local-lmstudio-record-quality`｜實作需 **fresh session**（Stage 04）

## GOAL_ANCHOR（不可縮小）
使用者在 Mac＋LM Studio（`qwen3.8-27b-splash` 27B、`qwen3.6-35b-a3b-splash` MoE 35B）以
**`section_meeting`** 模板產出科務會議紀錄，品質須接近雲端 Gemini。
本波只做兩件 CORE：**(1) 最終紀錄契約一致**（彙整表不得有出處標註、正文必須有）、
**(2) 可確證的 ASR 同音誤辨不得原樣流入紀錄**。

## CRITICAL_PATH（依序）
1. W2b：`text_postprocess.py::strip_source_tags_from_table_rows(text, template) -> (text, removed:int)`，
   並在 `_finalize_record_text(mode="local")` 內呼叫（生成後 `summarization.py:2093`、每輪補強後 `:2128` 共用同一路徑）。
2. W3：`SECTION_MEETING_RECORD_TERM_FIXES`（`backend/core/prompt_templates/section_meeting.py`，與共用
   `SECTION_MEETING_GLOSSARY_CORRECTIONS` **分離**）＋ `text_postprocess.py::apply_record_term_fixes(text, fixes)`；
   4 條規則（`征收股→徵收股`、`增收股→徵收股`、語境錨定 `人事總數→人事總處`、`瑞裏→瑞里`）。
3. W8：`scripts/e2e/run_owned_e2e.py` 的 DOCX 正式性檢查模板感知（general 行為 byte 級不變）。
4. W6：`scripts/e2e/measure_record_quality.py`（CORE 的判定儀器）。
5. W2：地端 few-shot（`mode="local"` 閘門；雲端 byte 級不變）。
6. W5：`dedupe_cross_section_items`（general 模板；`_finalize_record_text` **最後一步**）。
7. W7：測試（新 3 檔＋既有 2 檔增補）與全套回歸。

## 固定順序（`_finalize_record_text`）
`finalize_record` → `apply_record_term_fixes` → `strip_source_tags_from_table_rows`
→ `normalize_unfilled_placeholders` → `dedupe_cross_section_items`（最後一步）。
W2b／W3／W5 全部只在 `mode="local"` 生效；雲端呼叫端（`_finalize_cloud_record_text` 2186）不得受影響。

## 語意不變量（不得破壞）
- `COMPLETED + summary_failed` 語意、所有門檻值、`LOCAL_LLM_GENERATION_TEMPERATURE` 預設值不變。
- 絆索只產生補強問題，最終 fail-soft（不得硬攔輸出）。
- `_finalize_record_text` 之後才跑驗證；驗證是最後一關。
- 雲端提示詞與輸出不得改變（`_build_record_generation_message` 等新增參數預設值＝現行雲端行為）。
- `data/outputs/*`、`data/cache/*` 為 gitignored → 測試 fixture 必須**內嵌**（可用 `data/cache/p1-fixtures/fixtures.py` 為來源，
  但貼進測試檔時必須是字面字串）。

## 非閘門（只登記／觀察）
SUPPORTING-3 覆蓋率（`待辦事項遺漏 15 項`，需擁有者人工評分）、SUPPORTING-4 `tagged_item_ratio`、
W6 的 `unsupported_entities`（觀察值；**不得**用它當 CORE 閘門——基線的未落地專名是 ASR 變體重建）、
27B E2E（BEST_EFFORT，需擁有者授權切換 LM Studio 載入模型）。
明確放棄項與理由見 plan.md §1／§6（原 W4 捏造絆索）。

## 可驗證期望值（實測釘住）
- `FIXTURE_A_RECORD`（general，決議 vs 主席裁示）dedupe → 移除 **10** 條；`FIXTURE_B_RECORD` → 移除 **0** 條；
  dedupe 後 `_validate_summary_quality` issues **不增加**。
- 基線實檔 `data/cache/e2e/p1-baseline-01/backend_data/outputs/0903-科務會議_70a58030.md`：
  全檔標註 46（表格 13、正文 33）→ 修正後表格必須為 0、正文必須 > 0。
- 同場 DOCX（`.../0903-科務會議_70a58030.docx`）：`validate_formal_docx_bytes(..., template_id="section_meeting")`
  必須回傳 `[]`。
- 全套測試基準：`DATA_DIR="$PWD/data" uv run --no-sync pytest tests/ -q --ignore=tests/test_end_to_end.py -p no:randomly`
  → 823 passed / 2 skipped（新測試只增不減）；`bash scripts/check_docs.sh` → 0 errors / 0 warnings。

## STOP / ESCALATION（不得臨場決定）
1. 若「不改雲端行為」無法達成 → 停止，回 Stage 01。
2. 若 CORE-1 的正文標註在 E2E 變成 0 → 停止，回 Stage 01（候選：多樣 few-shot／格式簡化）。
3. 若需要放寬任何判準、白名單或去重條件才能讓測試變綠 → 停止，回 Stage 01（語意變更不得由實作者自決）。
4. 若 `validate_formal_docx_bytes` 的 general 分支需要改動既有測試 → 停止並回報（general 行為必須 byte 級不變）。
