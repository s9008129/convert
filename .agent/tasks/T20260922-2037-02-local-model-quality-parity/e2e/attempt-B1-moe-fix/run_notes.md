# attempt-B1-moe-fix — 修復後 E2E（MoE 35B-A3B）

- 模型：`qwen3.6-35b-a3b-splash`（LM Studio instance context=128000）
- 音檔：`/Users/hsiaojohnny/Downloads/0903-科務會議.m4a`（sha256 `982151f4…`，與前幾場同一份）
- 模板／模式：`section_meeting`／`local`；HEAD＝`f1e6bfe`（本波修復首次進場）
- verdict：**PASS**（runner required checks 全過、exit 0）
- 耗時：**runner 452 s**；任務本身 **442 s**（21:07:46 → 21:15:08）

## 本波主指標（出處標註真實性）

| 指標 | 數值 | 說明 |
|---|---|---|
| `tags_total` | 14 | 本場單次抽樣的正文標註數（前場 27；run-to-run 變異，§9.11） |
| `traceable_tag_ratio` | **1.0** | 每個時間戳都落在逐字稿真實段落內 |
| `tags_on_real_segment_start`／`on_start_tag_ratio` | **14／14 = 1.0** | 每個時間戳都**恰為**某真實段落起點（可直接在逐字稿搜尋到） |
| `tags_inside_same_speaker_segment` | 0 | 本場模型用「科長」而非「發言者N」當標籤 → 嚴格版不計入（量尺保守，非退化） |

對照（同一支音檔、不同抽樣）：

| 場次 | 模型 | 修復 | `on_start_tag_ratio` |
|---|---|---|---|
| p1-fixed-01 | MoE 35B | 無 | 4/27 = 0.148 |
| p2-27b-01 | dense 27B | 無 | 46/61 = 0.754 |
| **B1（本場）** | MoE 35B | **有** | **14/14 = 1.000** |

## 其他契約指標

- `table_source_tag_count = 0`（彙整表不得有出處標註）
- `tagged_item_ratio = 1.0`（每個正文條目都有標註）
- `known_term_fix_hits.left_hits = 0`（ASR 已知誤辨未流入；逐字稿本身 3 筆）
- `instruction_item_count = 14`（前場 2；本場「科長指示及提醒事項」有實質條目）
- 觀察值：`unsupported_entities = ["徵收股","煙酒稽徵股","稽徵股"]`（股名為逐字稿 ASR 變體，需擁有者確認正確股名；永不閘門）
- 日誌：`出處標註吸附 14 處（段落內 13／最近段落 0／跨發言者 1；不可回溯保留 0）`

## 未達／待觀察

- `body_source_tag_count = 14` < 前波退化防線 17 → 屬單次抽樣變異，登記為觀察值；本波主指標為「標註真偽」而非「標註數量」。

## errata（2026-09-22；獨立查核發現、`review/attempt-04` 複核成立）

- 上方「對照」表的欄名 `on_start_tag_ratio` 對 `p1-fixed-01`（4/27）與 `p2-27b-01`（46/61）**是錯的標籤**：
  那兩個數字是**當時儀器（v1.0）的同名欄位**，其語意＝「時間戳恰為段落起點**且**發言者標籤與該段一致」；
  在現行儀器（v1.1）下應讀為 `exact_tag_ratio`。（v1.0 的函式 docstring 未同步更新，實作已要求發言者一致。）
- **同量尺（v1.1）的正確值**：`p1-fixed-01` `on_start 10/27 = 37.0%`、`exact 4/27`；
  `p2-27b-01` `on_start 58/61 = 95.1%`、`exact 46/61`（見 `instrument_recheck_20260922.json`、研究 §10.3）。
  本場（B1）自身那列的 `14/14 = 1.000` 不受影響（v1.1 亦為 1.000）。
- 原表與數字保留不修改（append-only）；後續引用請以 v1.1 值為準，並標明 `metric_version`。
