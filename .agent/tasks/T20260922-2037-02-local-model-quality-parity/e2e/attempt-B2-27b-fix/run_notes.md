# attempt-B2-27b-fix（27B dense 修復後 E2E）執行筆記

- 目的：驗證「出處標註確定性吸附」在**正式管線**對 dense 27B（`qwen3.8-27b-splash`）生效，
  並與同音檔、同模板、同管線的 A1（修復前）對照。使用者指定本輪只測 27B、不測 MoE。
- HEAD：`3fec08f`（clean worktree，E2E runner 的 clean-HEAD gate 通過）
- 音檔：`/Users/hsiaojohnny/Downloads/0903-科務會議.m4a`（sha256 `982151f4…`，與 B1／A1 同一支）
- 模板／模式：`section_meeting`／`local`；LM Studio 已載入 27B、`context_length=128000`
- verdict：**PASS**（16 項 required checks 全過、exit 0）

## 一、耗時（1710 s 全流程／1703 s 任務）

| 階段 | 時間 | 備註 |
|---|---|---|
| ASR＋diarization | 21:18:26 → 21:23:25（299 s） | diarization 153.7 s、682 段、8 位發言者、RTF 0.057 |
| 抽取（9 chunks） | 約 80 s | 每次 7–9 s、輸出 250–330 tokens |
| 整併呼叫 | 21:23:25 → 21:29:25（360 s） | 4,146 completion tokens → 11.5 tok/s |
| 最終生成 | 21:29:25 → 21:34:59（334 s） | 3,123 tokens → 9.4 tok/s |
| 補強第 1 輪 | 21:34:59 → 21:40:58（359 s） | 3,120 tokens → 8.7 tok/s |
| 補強第 2 輪 | 21:40:58 → 21:46:49（351 s） | 3,120 tokens → 8.9 tok/s |

A1（修復前）只有 2 次大呼叫（306 s／310 s）故 910 s。**B2 慢在補強輪**：品質閘門第 1 輪抓到
「待辦事項遺漏 11 項」、第 2 輪剩下 6 項，各燒一次約 6 分鐘的生成。不是後處理變慢
（吸附成本在毫秒級），也不是機器不夠力（ASR 只花 5 分鐘）。

## 二、CORE 指標

| 指標 | 值 | 門檻／判讀 |
|---|---|---|
| `on_start_tag_ratio` | **1.000**（52/52） | 主指標（speaker-agnostic）達標 |
| `on_start_tag_ratio_excluding_zero` | **1.000**（45/45） | 排除 7 筆 `00:00:00` 後仍達標 |
| `traceable_tag_ratio` | 1.000 | 標註都落在真實段落內 |
| `table_source_tag_count` | 0 | CORE-1 達標 |
| `body_source_tag_count` | 52 | ≥ 退化防線 17 |
| `tagged_item_ratio` | 1.000 | 每條都有標註 |
| `instruction_item_count` | 25 | 未退化（A1 為 21） |
| `exact_tag_ratio` | 0.019 | **僅供觀察**：本場模型多用角色名（科長）→ 嚴格版失真 |
| `zero_time_tag_ratio` | 0.135（7 筆） | 觀察值；非吸附造成（A1 亦為 7 筆） |
| `distinct_tag_time_ratio` | 0.288（15 種） | **新缺口**：同一時間戳重複張貼 → P1-16 |
| `unsupported_entities` | 3（徵收股／煙酒文神股／稽查股） | 觀察值、永不作為閘門；P1-1／P1-6 |
| 字元數 | 4,062 | A1 4,338，同級 |

## 三、吸附日誌（三次後處理，最終輸出為第三次）

- 第一次（最終生成後）：吸附 45 處（段落內 1／跨發言者 44／不可回溯 0）
- 第二、三次（補強輪後）：吸附 40 處（段落內 1／跨發言者 39／不可回溯 0）
- 「跨發言者」＝時間戳落在別的發言者段落內 → 規則 3「只改時間、不改歸屬」，符合 fail-soft 設計。

## 四、本場無法證明的事

1. **覆蓋率**：本場未重跑事實探針 → `[UNVERIFIED]`，不得由可查核性推論。
2. **忠實度／捏造率**：未做 `unsupported_entities` 之外的人工判定。
3. **與雲端 Gemini 的相對差距**：本場沒有重跑雲端對照（§8.5 的雲端基準為前一輪評分）。
4. **模型間高下**：單次抽樣（temperature 0.7），且本輪依使用者指示只測 27B。

## 五、儀器版本與證據完整性（獨立驗收指出）

- `record_quality.json` 曾於 21:48 產生一版（`on_start_tag_ratio_excluding_zero` 分母＝總標註數 52 → 0.865），
  21:50 因儀器定義改為「分母＝非 `00:00:00` 的標註數」而就地在原檔覆寫（→ 1.000）。
  本目錄所有數字皆為 **v1.1**；同一場次同名指標被就地覆寫是已知的證據完整性風險，
  後續波應在儀器輸出加 `metric_version` 並改為 append-only 檔名。
- 主指標（`on_start_tag_ratio`）在兩個版本都相同（1.000），因此不影響本場判讀。
- 獨立驗收（`verify_independent.md`）另指出：約 710 s（42% 耗時）花在兩輪**假陽性**補強
  （「待辦事項遺漏 6 項」其實都已寫入，只是字面變體）→ 新工作項 P1-17。

## 六、errata（2026-09-22；獨立查核發現、`review/attempt-04` 複核成立）

- **§一 耗時表的兩列標籤有誤，依 append-only 於此更正（原表不修改）**：
  1. 「抽取（9 chunks）約 80 s／每次 7–9 s、輸出 250–330 tokens」→ **錯**。本場
     `chunk_count=1`、**抽取是單次呼叫 360.9 s／4,146 tokens**（`backend.log:201,427`）。
     那組 7–9 s／222–326 tokens 的呼叫是 **12 次逐字稿語意校正**，不是抽取、也不是 9 次
     （`backend.log:56–123`）。
  2. 「整併呼叫 21:23:25 → 21:29:25（360 s）4,146 tokens」→ **標籤錯**，該次是**抽取**；
     本場 `merge_rounds=0`、**沒有整併呼叫**（筆記 3,886 tokens 直接零損串接，`backend.log:203,427`）。
  3. 「ASR＋diarization 21:18:26 → 21:23:25（299 s）」→ 該窗實含 **ASR 16.7 s ＋ diarization 153.7 s
     ＋ 逐字稿語意校正約 127 s**（`backend.log:42-45`）。
- **正確的耗時構成**：ASR 16.7 s → diarization 153.7 s（RTF 0.057）→ 語意校正 12 次小呼叫約 127 s
  → **抽取 360.9 s（4,146 tokens，11.5 tok/s）** → 最終 334 s（3,123，9.3 tok/s）→ 補強 359 s（3,120，8.7）
  → 補強 351 s（3,120，8.9）；pipeline total 1,404.7 s；任務 1,703 s／runner 1,710 s。
- **影響**：僅階段標籤；**不影響任何品質指標、閘門判定與總時數**。同步更正：研究文件 §10.7（就地）、
  `attempt.json` 新增 `timing_breakdown_errata_20260922`（原欄位保留）。
- 相關：`review/attempt-04` 明確判定此類產物標籤錯誤「不需為它遞增計畫修訂」；`plan.md` rev 6 §6.5
  已如實登記。
