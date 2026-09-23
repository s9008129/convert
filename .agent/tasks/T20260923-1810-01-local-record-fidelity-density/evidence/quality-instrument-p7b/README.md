# P7-B 量測儀器擴充：全文條目與近似重複（觀測值）

- 任務：`T20260923-1810-01-local-record-fidelity-density`（P7-B）
- 產出：2026-09-23（Asia/Taipei）
- 目的：回應 Stage 02 attempt-01 審查 **I4（指標定義與儀器不符）** 與 **I3（去重量尺恆 0）**：
  在動手改產品之前，先把「條目數／平均條目字數／近似重複對」釘死成**可重現的儀器欄位**。

## 1. 為什麼要新增（不是既有欄位不夠，是既有欄位量不到）

- `instruction_item_count` 的定義是**「科長指示及提醒事項」章節內的 leaf item 數**
  （`scripts/e2e/measure_record_quality.py` 的 `notes.definitions`）——
  rev1 計畫寫的「78→≤45」其實是**全文** leaf item，兩者是**不同的尺**。
- `cross_section_duplicate_pairs` 是 `dedupe_cross_section_items()` 的回報值；
  該函式需要「決議」＋「主席裁示事項」章節，且 `template.id != "general"` 直接 `return`
  （`backend/core/text_postprocess.py:680-712`）⇒ 對 `section_meeting` **結構性恆 0**，
  量不到 qwen 交付紀錄裡肉眼可見的重複。

## 2. 新增欄位（`scripts/e2e/measure_record_quality.py`；additive、observation-only）

| 欄位 | 定義 |
|---|---|
| `full_document_item_count` | 全文行首為 `N.`／`（N）` 的 leaf item 數（排除表格列） |
| `full_document_avg_item_chars` | 同一批條目去掉編號後的平均字元數 |
| `near_duplicate_items.count` | 全文 leaf item 兩兩比較，正規化（去編號→去行尾 metadata→去標點與空白）後 `difflib` 相似度 ≥ 門檻（預設 0.80，CLI `--near-duplicate-threshold`）的對數 |
| `near_duplicate_items.exact_count` | 正規化後完全相等的對數 |
| `near_duplicate_items.top` | 相似度最高的前 5 對（附行號與原文前 60 字） |

三個欄位在 `notes.definitions` 都明訂 **「永不作為閘門」**；且明訂與 `instruction_item_count`
**定義不同、不得混用**（測試 `tests/test_record_quality_metrics.py` 已同步把 schema 釘死並加上上述斷言）。

## 3. 命令（可重現）

```bash
DATA_DIR=/tmp/measure_scratch uv run --frozen python scripts/e2e/measure_record_quality.py \
  --record <交付 .md> --transcript <逐字稿.txt> --template section_meeting
```

## 4. 基線（同一支音檔、同一模板、同一支儀器）

| 紀錄 | `char_count` | `instruction_item_count` | `full_document_item_count` | `avg_item_chars` | `near_duplicate_items.count` | `exact_count` | `cross_section_duplicate_pairs` |
|---|---:|---:|---:|---:|---:|---:|---:|
| qwen 3.8 27B（E6b） | 4,853 | 22 | **78** | **42.5** | **3** | 2 | 0（恆 0，量不到） |
| gemma 4 31B（E7C） | 2,325 | 14 | 23 | 49.7 | 0 | 0 | 0 |
| 雲端 gemini-3.5-flash-lite（C5） | 2,593 | 15 | 28 | **65.1** | 0 | 0 | 0 |

判讀：qwen 的「破碎」是可量化的——**78 條**（雲端 28 條）、平均 **42.5 字**（雲端 65.1 字）、
並有 3 對近似重複（其中 2 對**完全相同**，例如「確認各單位皆報3人」同時出現在 L40 與 L98）。

## 5. 與 `research/format-density-comparison.md` 的 7 對差異（如實揭露）

研究報告用**另一套方法**（跨節近似段落比對）得到 7 對；本儀器用**全文 leaf item 兩兩比對、
去 metadata、≥0.80** 得到 3 對。兩者不是同一個量尺，數字不可互換；本波驗收一律以**本儀器**為準
（定義已釘死在第 2 節），研究報告的 7 對僅作定性佐證。

## 6. 不變的部分

- 儀器**不改任何產品行為**，也不新增任何閘門語意；既有欄位與既有 `notes` 內容未動。
- 舊 E2E artifact 的 `record_quality.json` 沒有新欄位屬正常（additive，非回溯改寫）。
