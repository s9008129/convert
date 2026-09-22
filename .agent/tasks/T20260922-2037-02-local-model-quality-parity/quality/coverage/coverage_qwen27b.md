# 事實涵蓋率報告：qwen27b

- 量尺版本：`coverage-1.0.0`
- 受測紀錄：`data/cache/e2e/p2-27b-fix-01/backend_data/outputs/0903-科務會議_dc3c8f7a.md`（sha256 `b0ac8563c190e0c6ccd6e0726a63aa8a0bd57868d71c5591d87c686a1aa44e09`；字元數 4062，正規化後 2931）
- 事實清單：`data/cache/staging/quality/fact_checklist.json`（sha256 `cf012d1f6983f67ecb47cc7a6486e48c110a6b2782ad94cccf0332a4ec6ec001`；checklist_version `1.0.0`；meeting `0903-科務會議`；共 67 條＝core 28＋supporting 39）
- 正規化：unicode_nfkc、casefold、opencc_fold_s2twp、strip_whitespace_and_newlines、strip_punctuation_and_symbols；OpenCC 可用（`opencc-s2twp`）；fuzzy 停用
- 逐字稿（觀察值）：`data/cache/e2e/p2-27b-fix-01/backend_data/outputs/0903-科務會議_dc3c8f7a_逐字稿.txt`；coverage_all 0.9701（97.0%；65/67）、coverage_core 0.9643（96.4%；27/28）

## 總覽

| 指標 | 數值 |
| --- | --- |
| coverage_all | 0.8209（82.1%；55/67） |
| coverage_core | 0.8929（89.3%；25/28） |
| coverage_supporting | 0.7692（76.9%；30/39） |

## 分類涵蓋率

| category | total | covered | coverage |
| --- | --- | --- | --- |
| decision | 9 | 9 | 1.0000（100.0%；9/9） |
| name | 3 | 3 | 1.0000（100.0%；3/3） |
| action_item | 9 | 7 | 0.7778（77.8%；7/9） |
| number | 4 | 2 | 0.5000（50.0%；2/4） |
| constraint | 13 | 12 | 0.9231（92.3%；12/13） |
| topic | 25 | 19 | 0.7600（76.0%；19/25） |
| date | 4 | 3 | 0.7500（75.0%；3/4） |

## 漏寫事實（core；3 條）

1. `F021` 下週一要辦內稽，本科是下午受檢（對方整天內稽）。
2. `F025` 今年文康活動經費為每人800元、共17人，合計13600元。
3. `F055` 上次颱風（上班日）三樓嚴重淹水，水溢流到禮堂與走廊。

## 漏寫事實（supporting；9 條）

`F008`、`F016`、`F017`、`F024`、`F030`、`F032`、`F057`、`F058`、`F064`

## 警告（0 條）

（無）

## 事實明細

| id | tier | category | 涵蓋 | matched group | matched positions | 備註 |
| --- | --- | --- | --- | --- | --- | --- |
| `F001` | core | decision | ✅ | 2 | 553, 558 |  |
| `F002` | core | decision | ✅ | 0 | 574, 163 |  |
| `F003` | core | name | ✅ | 0 | 592 |  |
| `F004` | core | decision | ✅ | 0 | 155, 163 |  |
| `F005` | core | name | ✅ | 1 | 611 |  |
| `F006` | core | name | ✅ | 4 | 196, 184 |  |
| `F007` | core | decision | ✅ | 0 | 671 |  |
| `F008` | supporting | action_item | ❌ | - | - | no_probe_group_matched |
| `F009` | supporting | decision | ✅ | 0 | 681, 688 |  |
| `F010` | core | number | ✅ | 0 | 697, 701 |  |
| `F011` | supporting | constraint | ✅ | 0 | 735 |  |
| `F012` | supporting | action_item | ✅ | 0 | 210, 216 |  |
| `F013` | supporting | topic | ✅ | 0 | 852 |  |
| `F014` | supporting | number | ✅ | 0 | 870, 875 |  |
| `F015` | supporting | date | ✅ | 0 | 896 |  |
| `F016` | supporting | topic | ❌ | - | - | no_probe_group_matched |
| `F017` | supporting | topic | ❌ | - | - | no_probe_group_matched |
| `F018` | supporting | topic | ✅ | 2 | 940 |  |
| `F019` | core | topic | ✅ | 0 | 567, 966, 968 |  |
| `F020` | core | action_item | ✅ | 0 | 239, 233 |  |
| `F021` | core | date | ❌ | - | - | no_probe_group_matched |
| `F022` | core | constraint | ✅ | 0 | 271, 296 |  |
| `F023` | supporting | topic | ✅ | 0 | 271, 505 |  |
| `F024` | supporting | number | ❌ | - | - | no_probe_group_matched |
| `F025` | core | number | ❌ | - | - | no_probe_group_matched |
| `F026` | supporting | decision | ✅ | 0 | 265, 275 |  |
| `F027` | supporting | topic | ✅ | 1 | 275, 313 |  |
| `F028` | supporting | action_item | ✅ | 0 | 330, 334 |  |
| `F029` | supporting | topic | ✅ | 0 | 291, 288 |  |
| `F030` | supporting | constraint | ❌ | - | - | no_probe_group_matched |
| `F031` | supporting | topic | ✅ | 0 | 446, 893 |  |
| `F032` | supporting | topic | ❌ | - | - | no_probe_group_matched |
| `F033` | supporting | constraint | ✅ | 2 | 356, 1095 |  |
| `F034` | supporting | constraint | ✅ | 2 | 362, 1148 |  |
| `F035` | supporting | constraint | ✅ | 0 | 1157 |  |
| `F036` | supporting | constraint | ✅ | 0 | 366, 1161 |  |
| `F037` | supporting | constraint | ✅ | 1 | 1216 |  |
| `F038` | supporting | constraint | ✅ | 1 | 1167 |  |
| `F039` | supporting | topic | ✅ | 1 | 1247 |  |
| `F040` | supporting | topic | ✅ | 0 | 1269 |  |
| `F041` | supporting | constraint | ✅ | 0 | 1306, 1309 |  |
| `F042` | core | decision | ✅ | 1 | 1372, 598 |  |
| `F043` | supporting | constraint | ✅ | 0 | 375, 379 |  |
| `F044` | core | constraint | ✅ | 0 | 392, 1171 |  |
| `F045` | core | topic | ✅ | 0 | 1481 |  |
| `F046` | core | constraint | ✅ | 0 | 427 |  |
| `F047` | supporting | topic | ✅ | 0 | 66, 1581 |  |
| `F048` | core | topic | ✅ | 1 | 446, 448 |  |
| `F049` | core | decision | ✅ | 0 | 441, 448 |  |
| `F050` | supporting | action_item | ✅ | 0 | 463, 477 |  |
| `F051` | supporting | topic | ✅ | 3 | 1777, 1806 |  |
| `F052` | core | action_item | ✅ | 0 | 477, 66 |  |
| `F053` | core | action_item | ✅ | 0 | 484, 490 |  |
| `F054` | core | date | ✅ | 1 | 1842, 1856 |  |
| `F055` | core | topic | ❌ | - | - | no_probe_group_matched |
| `F056` | core | topic | ✅ | 0 | 1882, 1885 |  |
| `F057` | supporting | action_item | ❌ | - | - | no_probe_group_matched |
| `F058` | supporting | topic | ❌ | - | - | no_probe_group_matched |
| `F059` | supporting | topic | ✅ | 0 | 508, 1938 |  |
| `F060` | core | topic | ✅ | 0 | 1944, 508 |  |
| `F061` | core | date | ✅ | 3 | 2020, 2023 |  |
| `F062` | supporting | action_item | ✅ | 0 | 1968, 1966 |  |
| `F063` | supporting | topic | ✅ | 0 | 2090, 505 |  |
| `F064` | supporting | topic | ❌ | - | - | no_probe_group_matched |
| `F065` | core | decision | ✅ | 1 | 2016, 2020 |  |
| `F066` | core | topic | ✅ | 0 | 2033 |  |
| `F067` | supporting | topic | ✅ | 0 | 2023, 567 |  |

## 指標定義

- **metric_version**：量尺版本（coverage-1.0.0）；欄位語意變更時遞增，不得就地改義。
- **coverage_all**：已涵蓋事實數／事實總數（0~1）。
- **coverage_core**：core 事實涵蓋率；分母＝fact_core_total（0 筆時為 0.0）。
- **coverage_supporting**：supporting 事實涵蓋率；分母＝fact_supporting_total（0 筆時為 0.0，請以計數欄判讀）。
- **covered_total**：至少命中一個 probe group 的事實數（group 內 AND、group 間 OR）。
- **missing_core_ids**：未涵蓋的 core fact id（清單順序）。
- **missing_core_statements**：對應 missing_core_ids 的 statement（同序）。
- **by_category**：每類 category 的 total／covered／coverage（類別順序＝清單首次出現順序）。
- **record_char_count**：受測紀錄 Markdown 全文 len(text)（含換行）；與 measure_record_quality.py 的 char_count 同定義。
- **record_normalized_char_count**：正規化後字元數；matched_positions 的索引以此字串為準。
- **matched_group_index**：第一個命中的 probe group index（0 起算）；命中即停。
- **matched_positions**：該 group 內各 token 在正規化後紀錄的首次出現起始索引（依 token 宣告順序，最多前 3 個）。
- **reason**：未涵蓋時固定為 no_probe_group_matched（所有 probe group 皆未全數命中）。
- **normalization**：實際套用的正規化步驟與 OpenCC 可用性；受測紀錄與 checklist token 一律套同一條管線（雙向對稱）。
- **warnings**：輸入或 probes 品質告警（空清單、token <2 字、正規化後為空、tier 未知、重複 id、OpenCC／pypinyin 不可用…）。
- **transcript**：觀察值：同一組 probes 對逐字稿的涵蓋率；未提供 --transcript 時為 null。

## 已知限制

- 字面量尺：換句話說、語序重排、同義改寫的事實可能被計為漏寫（false negative），漏寫清單必須人工抽查再定案。
- 反向風險：紀錄中零散出現關鍵詞即算涵蓋，關鍵詞堆砌或表格殘留可能造成 false positive。
- 不判否定與數字正確性：『同意』與『不同意』在 token 層面同分；probe 只要求數字 token 出現，不檢查數值是否正確。
- fuzzy 只處理同音近音錯字，不處理 ASR 漏字／斷詞錯誤；此類差異會落在漏寫清單。
- 清單品質（fact 是否真的來自逐字稿）不由本量尺保證；--transcript 觀察值是第一層交叉檢查。
- 單次抽樣限制（temperature 0.7），跨模型差異解讀仍需搭配重跑次數。
