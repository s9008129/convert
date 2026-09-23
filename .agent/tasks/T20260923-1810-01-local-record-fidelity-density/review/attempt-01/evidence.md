# 附錄：attempt-01 審查證據（原始輸出摘要；all read-only）

## A. 版本與環境
- `shasum -a 256 plan.md` → `caa3ea0262047cd5710f2f75760966ebcf2ebf5b06f403fd3da8cf2ca350d7b0`（=登錄值）。
- `git status --short` 進場：只有本任務未追蹤研究/證據檔；`HEAD=0254c7a`（P7-B plan rev1 已 commit）。
- 無 `.env`；E7C attempt 目錄無 `LOCAL_LLM_*` 覆寫 → 後端讀 `config.py` 預設。

## B. 「階段歸因」關鍵證據
- E7C `backend.log:177`：`本地摘要上下文規劃：context_window=71936(lmstudio_instance), estimated_tokens=11711, ..., needs_chunking=False`（⇒ 萃取 1 塊）。
- E7C `backend.log:249`：`萃取筆記零損串接（略過有損整併）：1 份、1669 tokens ≤ 下游可承接上限 62794 tokens`。
- `config.py:234` `LOCAL_LLM_TRANSCRIPT_IN_FINAL_GENERATION=True`（雙輸入）；`:239` `LOCAL_LLM_ZERO_LOSS_NOTES_PASSTHROUGH=True`。
- E7C log **無**「不足以在最終生成階段附上完整逐字稿」退回 WARNING（grep 零命中）⇒ 最終生成含完整逐字稿。
- 筆記未落檔：`rg -l "萃取筆記" data/cache/e2e --glob '!backend.log'` → 零命中。
- probe 未執行：`evidence/tail-extraction-probe/` 僅 `probe_tail_extraction.py`，無輸出檔。

## C. 缺失事實與逐字稿位置（E7C 逐字稿 `0903-科務會議_bb492356_逐字稿.txt`）
| 事實 | 行 | 時間碼 |
|---|---|---|
| F044 選舉政治敏感 | 145 | `[00:25:23-00:26:08]`（距片尾 44:15 ⇒ 42.6%） |
| F055 三樓淹水溢流禮堂 | 177 | `[00:33:57-00:34:38]` |
| F056 防水刨除／排水管 | 181-185 | `[00:34:51-00:39:44]` |
| F060 空辦公室黴味 | 187 | `[00:39:47-00:42:51]` |
| F054/F065/F066 搬遷兩階段/單位/移交 | 189 | `[00:43:03-00:44:15]` |

## D. 覆蓋率（`facts_checklist coverage-1.0.0`；core 28）
- E7C（gemma）：`coverage_core=0.75`，`missing_core=[F044,F054,F055,F056,F060,F065,F066]`。
- E6（gemma）：`0.75`，`missing=[F001,F044,F054,F056,F060,F065,F066]`。
- E1/E2（gemma）：`0.8214`，缺 `{F044,F054,F056,F066,F019/F048,F060,F065}`。
- E6b（qwen）：`0.9643`，`missing_core=[F055]`（＝qwen 也漏一條尾段事實）。
- 交集（gemma 4 場全漏）：`{F044,F054,F056,F060,F065,F066}`。

## E. 既有對帳／補強迴圈實證（E7C）
- `backend.log:336`（第 1 輪問題；含「議題遺漏 2 項：其他行政裁示、辦公室搬遷與環境問題」＝**筆記有**該議題）。
- `backend.log:430`：`地端補強不回退守衛：第 1 輪核心未涵蓋 11 → 4 項（期望 34 項）（更好，取本輪）`。
- `backend.log:525`：`第 2 輪核心未涵蓋 4 → 2 項`；`:526` 殘留問題警告；`:527` metrics：`chunk_count=1, logical_generations=4, ... cov_expected_topic=10 cov_missing_topic=1 cov_expected_decision=11 cov_missing_decision=1 cov_expected_number=9 cov_missing_number=0 cov_expected_date=4 cov_missing_date=0`。
- `config.py:280`：`LOCAL_LLM_MAX_REFINEMENT_ROUNDS` 預設 **2**。

## F. qwen 破碎／重複證據（`p6a-qwen27b-e6b` 交付 `.md`）
- 全文條目 `grep -c '^\s*[0-9]+\.'` = **78**；`record_quality.json`：`instruction_item_count=22`（章節限定定義，`measure_record_quality.py:306`）、`cross_section_duplicate_pairs=0`、`char_count=4853`。
- 跨節重複實例：`:39-40` 與 `:97-98`（「確認抽到『瑞里』…排班 10月14日（科長，00:06:14）」「各單位皆報3人（科長，00:06:50）」）。
- qwen E6b 有 1 輪補強（`logical_generations=3`；`backend.log` 14:57 第 1 輪、15:02 metrics `cov_*_missing=0`）。

## G. 去重函式與量尺（general-only，section_meeting 無效）
- `text_postprocess.py:587-600`：`_DONOR_SECTION_KEYWORD="主席裁示事項"`、`_DECISIONS_HEADING_PATTERN`（整行「決議：」）、`_CHAPTER_HEADING_PATTERN`（主席裁示事項/報告事項/…）。
- `text_postprocess.py:680` `dedupe_cross_section_items`：`template.id != "general"` → 原樣回傳；判準為正規化後**完全相等**。
- `measure_record_quality.py:256`（`dedupe_cross_section_items(record_text, template)`）、`:377`（`cross_section_duplicate_pairs`＝回報移除數）⇒ section_meeting 恆 0。

## H. placeholder／normalize 現況
- `text_postprocess.py:367-376`：`_UNFILLED_PLACEHOLDER_PATTERN` 只匹配**骨架型**（年/月/日/星期/時分/次…）＋欄位/標題行白名單；不處理模型自填的相鄰「（待確認）」、不處理表格儲存格。
- E7C `.md:3`：「（待確認）（待確認）年（待確認）月份第（待確認）次…」（相鄰重複×1）；表格「辦理情形」欄 `（待確認）：`×11。
- qwen E6b `.md:3-4`：相鄰重複×2（`（待確認）（待確認）`）。

## I. 前波紀律（權威引用）
- `T20260922-2037-02/plan.md:723-724`：「聚合門檻＝觀察值…須 ≥2 次取中位數才可宣稱支持；單次結果一律註明『單次抽樣、不可歸因』」。
- `T20260922-2037-02/handoff.md:64/111/167`：不改既有閘門門檻、`off` 語意、雲端提示詞、`task_processor.py:259/262`。
- `CHANGELOG.md` v4.10.3:72：不得宣稱「地端已達雲端 Gemini 水準」。

## J. 其他
- `qwen3.6-35b-a3b-splash`：本次審查**未**讀取其執行資料、未觸發任何測試（禁測遵守）。
- 本次審查未修改任何產品檔案；`review/attempt-01/` 為新增。
