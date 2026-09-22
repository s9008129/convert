# HANDOFF — T20260922-1930-01-local-record-quality-parity（P1 品質波）

- PLAN_REVISION: **6**｜plan.md sha256 `bbfcd0243a89c87651d32031b12133262bb6d82685158a6d3bbb78803d24f95b`
- 審查閘門：`review/attempt-04/gate.txt` = **`PLAN_APPROVED`**（僅適用 rev6／上述 sha；attempt-01～03 皆為 REVISION_REQUIRED，已 superseded）
- 前一版 handoff：`handoff.rev5.superseded.md`（已封存）
- 分支：`fix/local-lmstudio-record-quality`｜實作＝Stage 04（fresh session，三個互斥寫入集並行）

## GOAL_ANCHOR
使用者在 Mac＋LM Studio（`qwen3.8-27b-splash` 27B、`qwen3.6-35b-a3b-splash` MoE 35B）以 **`section_meeting`**
模板產出科務會議紀錄，品質須接近雲端 Gemini。本波只有兩個 CORE：
**(1) 紀錄契約一致**：彙整表內出處標註 = 0（基線 13）、正文出處標註 ≥ 1（基線 33，退化防線 < 17）；
**(2) 可確證 ASR 同音誤辨不得原樣流入紀錄**（`征收股/增收股→徵收股`、語境錨定 `人事總數→人事總處`、`瑞裏→瑞里`）。

## 寫入集（互斥，三軌並行；不得跨軌改檔）
- **軌 A**：`backend/core/text_postprocess.py`、`backend/core/prompt_templates/section_meeting.py`、`backend/core/templates.py`、
  `tests/test_record_term_fixes.py`、`tests/test_record_table_tags.py`、`tests/test_record_dedupe.py`
- **軌 B**：`backend/services/summarization.py`、`tests/test_t20260922_record_quality.py`
- **軌 C**：`scripts/e2e/run_owned_e2e.py`、`scripts/e2e/measure_record_quality.py`、`tests/test_owned_e2e_acceptance.py`、
  `tests/test_record_quality_metrics.py`

## 軌 A 介面（軌 B／C 依此呼叫，名稱不得改）
```python
# backend/core/prompt_templates/section_meeting.py
SECTION_MEETING_RECORD_TERM_FIXES: tuple[tuple[str, str], ...]  # (regex, replacement)，local-only、紀錄級
# 4 條：r"征收股"→"徵收股"; r"增收股"→"徵收股";
#       r"人事總數(?=\s*(?:Email|E-mail|電子郵件|郵件|寄|偽造|釣魚))"→"人事總處"; r"瑞裏"→"瑞里"
# （與 SECTION_MEETING_GLOSSARY_CORRECTIONS 分離：後者注入逐字稿校正層、雲端也吃，本波不得改）

# backend/core/templates.py
# MeetingTemplate 新增 record_term_fixes: tuple[tuple[str, str], ...] = ()（預設空＝其他模板不受影響）
# _SECTION_MEETING_TEMPLATE 指派 record_term_fixes=section_meeting.SECTION_MEETING_RECORD_TERM_FIXES

# backend/core/text_postprocess.py
SOURCE_TAG_PATTERN = re.compile(r"（[^）]{0,24}?\d{1,2}:\d{2}(?::\d{2})?[^）]{0,12}?）")  # 與 SummarizationService._SOURCE_TAG_PATTERN 同式
def template_forbids_table_source_tags(template) -> bool: ...        # forbidden_patterns 標籤含「發言來源標註」
def apply_record_term_fixes(text: str, fixes: tuple[tuple[str, str], ...]) -> tuple[str, list[tuple[str, str]]]: ...
def strip_source_tags_from_table_rows(text: str, template=None) -> tuple[str, int]: ...   # 只動 ^\s*\| 的表格列
def dedupe_cross_section_items(text: str, template=None) -> tuple[str, int]: ...
```

## 軌 B 接線要求
- `_finalize_record_text(summary, template=None, *, mode: str = "cloud")`：
  - `mode == "cloud"` → **現行順序 byte 級不變**（`normalize_unfilled_placeholders(finalize_record(...))`）。
  - `mode == "local"` → `finalize_record` → `apply_record_term_fixes(..., template.record_term_fixes)` →
    `strip_source_tags_from_table_rows(..., template)` → `normalize_unfilled_placeholders` → `dedupe_cross_section_items(..., template)`（**最後一步**）。
- 地端兩個呼叫點（`summarization.py:2093`、`:2128`）傳 `mode="local"`；`_finalize_cloud_record_text`（2186）不改。
- W2：`_build_record_generation_message`（1268）／`_build_record_refinement_message`（1314）新增 `mode: str = "cloud"`；
  地端 resolver（1626／1649）傳 `mode="local"`；雲端呼叫端（`_build_cloud_*` wrappers）不改。
  地端追加 ≤3 行範例：標註寫在**正文句末**、「**不得寫進彙整表四欄表格**」。
  另修正 `_speaker_traceability_rule`（1258）過時 docstring。

## 軌 C 要求
- W8：`validate_formal_docx_bytes(docx_bytes, content_disposition, template_id=None)`；新增模組層
  `TEMPLATE_REQUIRED_SECTIONS`（目前僅 `section_meeting`＝`一、科長轉知`、`二、科長指示及提醒事項`、`案由及承辦單位`、`散會`）；
  `general`／未指定／**未列於對照表者一律走現行 general 分支（byte 級不變）**；呼叫端 `:862` 傳 `args.template`。
- W6：`scripts/e2e/measure_record_quality.py`（`--record`（MD 權威；DOCX → SKIP 並註明）、`--transcript`、`--template`），
  輸出 JSON：`char_count`、`body_source_tag_count`（排除表格列與 `^(時間|地點|主持人|出席人員|紀錄)`）、
  `table_source_tag_count`、`instruction_item_count`、`tagged_item_ratio`、`cross_section_duplicate_pairs`、
  `known_term_fix_hits`、`unsupported_entities`（**觀察值，不得當閘門**）。
  白名單／樣式與軌 A 共用（import，不得複製一份）。

## 語意不變量
`COMPLETED + summary_failed`、所有門檻值、`LOCAL_LLM_GENERATION_TEMPERATURE` 不動；絆索只產生補強問題、最終 fail-soft；
驗證永遠在後處理之後；雲端提示詞與輸出不得改變；`data/outputs/*`、`data/cache/*` 為 gitignored → 測試 fixture 必須**內嵌字面**。

## 可驗證期望值
- `FIXTURE_A_RECORD` dedupe → 移除 **10** 條；`FIXTURE_B_RECORD` → **0** 條；dedupe 後 `_validate_summary_quality` issues **不增加**。
- 基線實檔 `data/cache/e2e/p1-baseline-01/backend_data/outputs/0903-科務會議_70a58030.md`：標註 46＝表格 13＋正文 33
  → 修正後表格 0、正文 > 0。同場 DOCX：`validate_formal_docx_bytes(..., template_id="section_meeting")` → `[]`。
- 全套：`DATA_DIR="$PWD/data" uv run --no-sync pytest tests/ -q --ignore=tests/test_end_to_end.py -p no:randomly` → ≥823 passed；
  `bash scripts/check_docs.sh` → 0 errors / 0 warnings。

## STOP / ESCALATION
1. 無法在不改雲端行為下接線 → 停止回 Stage 01。2. CORE-1 正文標註於 E2E 變 0 或 <17 → 停止回 Stage 01。
3. 需要放寬判準／白名單／去重條件才能綠燈 → 停止回 Stage 01。4. 需要改動 general 分支既有測試 → 停止並回報。
