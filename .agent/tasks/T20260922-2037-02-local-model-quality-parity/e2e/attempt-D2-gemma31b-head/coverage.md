# 事實涵蓋率報告：D2-gemma31b-head

- 量尺版本：`coverage-1.0.0`
- 受測紀錄：`data/cache/e2e/p3-gemma31b-d2/backend_data/outputs/0903-科務會議_52cf64f1.md`（sha256 `734e66e1bc3e54fe28b4b392e35daa5167cdb2a854927cddbff2abf1acfb1254`；字元數 1951，正規化後 1367）
- 事實清單：`.agent/tasks/T20260922-2037-02-local-model-quality-parity/quality/fact_checklist.json`（sha256 `cf012d1f6983f67ecb47cc7a6486e48c110a6b2782ad94cccf0332a4ec6ec001`；checklist_version `1.0.0`；meeting `0903-科務會議`；共 67 條＝core 28＋supporting 39）
- 正規化：unicode_nfkc、casefold、opencc_fold_s2twp、strip_whitespace_and_newlines、strip_punctuation_and_symbols；OpenCC 可用（`opencc-s2twp`）；fuzzy 停用
- 逐字稿（觀察值）：`data/cache/e2e/p3-gemma31b-d2/backend_data/outputs/0903-科務會議_52cf64f1_逐字稿.txt`；coverage_all 0.9851（98.5%；66/67）、coverage_core 1.0000（100.0%；28/28）

## 總覽

| 指標 | 數值 |
| --- | --- |
| coverage_all | 0.5075（50.7%；34/67） |
| coverage_core | 0.6786（67.9%；19/28） |
| coverage_supporting | 0.3846（38.5%；15/39） |

## 分類涵蓋率

| category | total | covered | coverage |
| --- | --- | --- | --- |
| decision | 9 | 7 | 0.7778（77.8%；7/9） |
| name | 3 | 3 | 1.0000（100.0%；3/3） |
| action_item | 9 | 6 | 0.6667（66.7%；6/9） |
| number | 4 | 1 | 0.2500（25.0%；1/4） |
| constraint | 13 | 6 | 0.4615（46.2%；6/13） |
| topic | 25 | 9 | 0.3600（36.0%；9/25） |
| date | 4 | 2 | 0.5000（50.0%；2/4） |

## 漏寫事實（core；9 條）

1. `F025` 今年文康活動經費為每人800元、共17人，合計13600元。
2. `F044` 年底選舉將近，涉及本機關的議題要特別小心、注意政治敏感。
3. `F048` 先前辦公室的照片被外流到臉書，留言至今沒有撤下。
4. `F054` 辦公室搬遷時程可能會拖很久。
5. `F056` 淹水主因：樓上施作防水工程刨除舊防水層，使早期埋設的排水管外露、破損後水沿管線滲出。
6. `F060` 政風室旁邊的空辦公室（未來要給工產科使用）霉味很重。
7. `F061` 工產科與財管科預計10月底就要搬進（現址）。
8. `F065` 財政四科搬遷分兩階段，第一階段由工產科、財管科先遷入。
9. `F066` 原空間將移交新聞行銷處：局長室改為新聞行銷處處長辦公室、隔壁會議室改為副處長辦公室。

## 漏寫事實（supporting；24 條）

`F008`、`F014`、`F016`、`F017`、`F018`、`F024`、`F026`、`F029`、`F030`、`F031`、`F032`、`F034`、`F036`、`F037`、`F040`、`F041`、`F043`、`F051`、`F057`、`F058`、`F059`、`F062`、`F064`、`F067`

## 警告（0 條）

（無）

## 事實明細

| id | tier | category | 涵蓋 | matched group | matched positions | 備註 |
| --- | --- | --- | --- | --- | --- | --- |
| `F001` | core | decision | ✅ | 2 | 387, 392 |  |
| `F002` | core | decision | ✅ | 0 | 402, 407 |  |
| `F003` | core | name | ✅ | 0 | 456 |  |
| `F004` | core | decision | ✅ | 0 | 416, 407 |  |
| `F005` | core | name | ✅ | 1 | 484 |  |
| `F006` | core | name | ✅ | 4 | 530, 514 |  |
| `F007` | core | decision | ✅ | 0 | 552 |  |
| `F008` | supporting | action_item | ❌ | - | - | no_probe_group_matched |
| `F009` | supporting | decision | ✅ | 0 | 559, 563 |  |
| `F010` | core | number | ✅ | 0 | 579, 583 |  |
| `F011` | supporting | constraint | ✅ | 0 | 599 |  |
| `F012` | supporting | action_item | ✅ | 3 | 157, 159, 149 |  |
| `F013` | supporting | topic | ✅ | 0 | 837 |  |
| `F014` | supporting | number | ❌ | - | - | no_probe_group_matched |
| `F015` | supporting | date | ✅ | 0 | 822 |  |
| `F016` | supporting | topic | ❌ | - | - | no_probe_group_matched |
| `F017` | supporting | topic | ❌ | - | - | no_probe_group_matched |
| `F018` | supporting | topic | ❌ | - | - | no_probe_group_matched |
| `F019` | core | topic | ✅ | 0 | 196, 878, 880 |  |
| `F020` | core | action_item | ✅ | 1 | 185, 180 |  |
| `F021` | core | date | ✅ | 0 | 209, 929 |  |
| `F022` | core | constraint | ✅ | 0 | 231, 263 |  |
| `F023` | supporting | topic | ✅ | 0 | 231, 657 |  |
| `F024` | supporting | number | ❌ | - | - | no_probe_group_matched |
| `F025` | core | number | ❌ | - | - | no_probe_group_matched |
| `F026` | supporting | decision | ❌ | - | - | no_probe_group_matched |
| `F027` | supporting | topic | ✅ | 1 | 270, 999 |  |
| `F028` | supporting | action_item | ✅ | 0 | 1021, 241 |  |
| `F029` | supporting | topic | ❌ | - | - | no_probe_group_matched |
| `F030` | supporting | constraint | ❌ | - | - | no_probe_group_matched |
| `F031` | supporting | topic | ❌ | - | - | no_probe_group_matched |
| `F032` | supporting | topic | ❌ | - | - | no_probe_group_matched |
| `F033` | supporting | constraint | ✅ | 0 | 628 |  |
| `F034` | supporting | constraint | ❌ | - | - | no_probe_group_matched |
| `F035` | supporting | constraint | ✅ | 0 | 668 |  |
| `F036` | supporting | constraint | ❌ | - | - | no_probe_group_matched |
| `F037` | supporting | constraint | ❌ | - | - | no_probe_group_matched |
| `F038` | supporting | constraint | ✅ | 2 | 256, 687, 696 |  |
| `F039` | supporting | topic | ✅ | 1 | 729 |  |
| `F040` | supporting | topic | ❌ | - | - | no_probe_group_matched |
| `F041` | supporting | constraint | ❌ | - | - | no_probe_group_matched |
| `F042` | core | decision | ✅ | 1 | 1055, 471 |  |
| `F043` | supporting | constraint | ❌ | - | - | no_probe_group_matched |
| `F044` | core | constraint | ❌ | - | - | no_probe_group_matched |
| `F045` | core | topic | ✅ | 1 | 1132 |  |
| `F046` | core | constraint | ✅ | 0 | 337 |  |
| `F047` | supporting | topic | ✅ | 0 | 60, 284 |  |
| `F048` | core | topic | ❌ | - | - | no_probe_group_matched |
| `F049` | core | decision | ✅ | 1 | 542, 1174 |  |
| `F050` | supporting | action_item | ✅ | 0 | 278, 291 |  |
| `F051` | supporting | topic | ❌ | - | - | no_probe_group_matched |
| `F052` | core | action_item | ✅ | 0 | 291, 60 |  |
| `F053` | core | action_item | ✅ | 0 | 1272, 367 |  |
| `F054` | core | date | ❌ | - | - | no_probe_group_matched |
| `F055` | core | topic | ✅ | 2 | 874, 1303 |  |
| `F056` | core | topic | ❌ | - | - | no_probe_group_matched |
| `F057` | supporting | action_item | ❌ | - | - | no_probe_group_matched |
| `F058` | supporting | topic | ❌ | - | - | no_probe_group_matched |
| `F059` | supporting | topic | ❌ | - | - | no_probe_group_matched |
| `F060` | core | topic | ❌ | - | - | no_probe_group_matched |
| `F061` | core | date | ❌ | - | - | no_probe_group_matched |
| `F062` | supporting | action_item | ❌ | - | - | no_probe_group_matched |
| `F063` | supporting | topic | ✅ | 0 | 1322, 657 |  |
| `F064` | supporting | topic | ❌ | - | - | no_probe_group_matched |
| `F065` | core | decision | ❌ | - | - | no_probe_group_matched |
| `F066` | core | topic | ❌ | - | - | no_probe_group_matched |
| `F067` | supporting | topic | ❌ | - | - | no_probe_group_matched |

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
