# 事實涵蓋率報告：gemma31b

- 量尺版本：`coverage-1.0.0`
- 受測紀錄：`data/cache/e2e/p2-gemma31b-fix-01/backend_data/outputs/0903-科務會議_ac1edcec.md`（sha256 `7d2de68463ada245b211b78e88e67ade1caa730059d527956afa442d2f158485`；字元數 1927，正規化後 1382）
- 事實清單：`data/cache/staging/quality/fact_checklist.json`（sha256 `cf012d1f6983f67ecb47cc7a6486e48c110a6b2782ad94cccf0332a4ec6ec001`；checklist_version `1.0.0`；meeting `0903-科務會議`；共 67 條＝core 28＋supporting 39）
- 正規化：unicode_nfkc、casefold、opencc_fold_s2twp、strip_whitespace_and_newlines、strip_punctuation_and_symbols；OpenCC 可用（`opencc-s2twp`）；fuzzy 停用
- 逐字稿（觀察值）：`data/cache/e2e/p2-gemma31b-fix-01/backend_data/outputs/0903-科務會議_ac1edcec_逐字稿.txt`；coverage_all 0.9851（98.5%；66/67）、coverage_core 1.0000（100.0%；28/28）

## 總覽

| 指標 | 數值 |
| --- | --- |
| coverage_all | 0.5672（56.7%；38/67） |
| coverage_core | 0.7500（75.0%；21/28） |
| coverage_supporting | 0.4359（43.6%；17/39） |

## 分類涵蓋率

| category | total | covered | coverage |
| --- | --- | --- | --- |
| decision | 9 | 7 | 0.7778（77.8%；7/9） |
| name | 3 | 3 | 1.0000（100.0%；3/3） |
| action_item | 9 | 6 | 0.6667（66.7%；6/9） |
| number | 4 | 2 | 0.5000（50.0%；2/4） |
| constraint | 13 | 7 | 0.5385（53.8%；7/13） |
| topic | 25 | 11 | 0.4400（44.0%；11/25） |
| date | 4 | 2 | 0.5000（50.0%；2/4） |

## 漏寫事實（core；7 條）

1. `F001` 組織規程與編制表修正案已經縣府法規審查小組審查通過，自今年11月1日生效。
2. `F022` 文康活動必須真的辦理活動、拍照佐證，才能發禮品、禮券或現金；沒辦活動就發會有問題。
3. `F025` 今年文康活動經費為每人800元、共17人，合計13600元。
4. `F044` 年底選舉將近，涉及本機關的議題要特別小心、注意政治敏感。
5. `F054` 辦公室搬遷時程可能會拖很久。
6. `F056` 淹水主因：樓上施作防水工程刨除舊防水層，使早期埋設的排水管外露、破損後水沿管線滲出。
7. `F066` 原空間將移交新聞行銷處：局長室改為新聞行銷處處長辦公室、隔壁會議室改為副處長辦公室。

## 漏寫事實（supporting；22 條）

`F008`、`F015`、`F016`、`F017`、`F018`、`F024`、`F026`、`F027`、`F030`、`F031`、`F032`、`F037`、`F039`、`F040`、`F041`、`F043`、`F051`、`F057`、`F058`、`F059`、`F062`、`F064`

## 警告（0 條）

（無）

## 事實明細

| id | tier | category | 涵蓋 | matched group | matched positions | 備註 |
| --- | --- | --- | --- | --- | --- | --- |
| `F001` | core | decision | ❌ | - | - | no_probe_group_matched |
| `F002` | core | decision | ✅ | 0 | 368, 373 |  |
| `F003` | core | name | ✅ | 0 | 386 |  |
| `F004` | core | decision | ✅ | 0 | 392, 373 |  |
| `F005` | core | name | ✅ | 1 | 423 |  |
| `F006` | core | name | ✅ | 4 | 458, 442 |  |
| `F007` | core | decision | ✅ | 0 | 480 |  |
| `F008` | supporting | action_item | ❌ | - | - | no_probe_group_matched |
| `F009` | supporting | decision | ✅ | 0 | 487, 491 |  |
| `F010` | core | number | ✅ | 0 | 498, 502 |  |
| `F011` | supporting | constraint | ✅ | 0 | 518 |  |
| `F012` | supporting | action_item | ✅ | 0 | 383, 156 |  |
| `F013` | supporting | topic | ✅ | 0 | 185 |  |
| `F014` | supporting | number | ✅ | 0 | 173, 807 |  |
| `F015` | supporting | date | ❌ | - | - | no_probe_group_matched |
| `F016` | supporting | topic | ❌ | - | - | no_probe_group_matched |
| `F017` | supporting | topic | ❌ | - | - | no_probe_group_matched |
| `F018` | supporting | topic | ❌ | - | - | no_probe_group_matched |
| `F019` | core | topic | ✅ | 0 | 361, 929, 931 |  |
| `F020` | core | action_item | ✅ | 1 | 207, 200 |  |
| `F021` | core | date | ✅ | 0 | 226, 221 |  |
| `F022` | core | constraint | ❌ | - | - | no_probe_group_matched |
| `F023` | supporting | topic | ✅ | 0 | 246, 620 |  |
| `F024` | supporting | number | ❌ | - | - | no_probe_group_matched |
| `F025` | core | number | ❌ | - | - | no_probe_group_matched |
| `F026` | supporting | decision | ❌ | - | - | no_probe_group_matched |
| `F027` | supporting | topic | ❌ | - | - | no_probe_group_matched |
| `F028` | supporting | action_item | ✅ | 0 | 252, 257 |  |
| `F029` | supporting | topic | ✅ | 0 | 1038, 1035 |  |
| `F030` | supporting | constraint | ❌ | - | - | no_probe_group_matched |
| `F031` | supporting | topic | ❌ | - | - | no_probe_group_matched |
| `F032` | supporting | topic | ❌ | - | - | no_probe_group_matched |
| `F033` | supporting | constraint | ✅ | 0 | 594 |  |
| `F034` | supporting | constraint | ✅ | 2 | 613, 627 |  |
| `F035` | supporting | constraint | ✅ | 0 | 637 |  |
| `F036` | supporting | constraint | ✅ | 0 | 634, 642 |  |
| `F037` | supporting | constraint | ❌ | - | - | no_probe_group_matched |
| `F038` | supporting | constraint | ✅ | 0 | 657 |  |
| `F039` | supporting | topic | ❌ | - | - | no_probe_group_matched |
| `F040` | supporting | topic | ❌ | - | - | no_probe_group_matched |
| `F041` | supporting | constraint | ❌ | - | - | no_probe_group_matched |
| `F042` | core | decision | ✅ | 1 | 1314, 409 |  |
| `F043` | supporting | constraint | ❌ | - | - | no_probe_group_matched |
| `F044` | core | constraint | ❌ | - | - | no_probe_group_matched |
| `F045` | core | topic | ✅ | 0 | 704 |  |
| `F046` | core | constraint | ✅ | 0 | 717 |  |
| `F047` | supporting | topic | ✅ | 0 | 59, 278 |  |
| `F048` | core | topic | ✅ | 1 | 744, 735 |  |
| `F049` | core | decision | ✅ | 0 | 742, 735 |  |
| `F050` | supporting | action_item | ✅ | 0 | 272, 285 |  |
| `F051` | supporting | topic | ❌ | - | - | no_probe_group_matched |
| `F052` | core | action_item | ✅ | 0 | 285, 59 |  |
| `F053` | core | action_item | ✅ | 1 | 1175, 329 |  |
| `F054` | core | date | ❌ | - | - | no_probe_group_matched |
| `F055` | core | topic | ✅ | 2 | 925, 1213 |  |
| `F056` | core | topic | ❌ | - | - | no_probe_group_matched |
| `F057` | supporting | action_item | ❌ | - | - | no_probe_group_matched |
| `F058` | supporting | topic | ❌ | - | - | no_probe_group_matched |
| `F059` | supporting | topic | ❌ | - | - | no_probe_group_matched |
| `F060` | core | topic | ✅ | 3 | 1266, 1225 |  |
| `F061` | core | date | ✅ | 3 | 1266, 1270 |  |
| `F062` | supporting | action_item | ❌ | - | - | no_probe_group_matched |
| `F063` | supporting | topic | ✅ | 0 | 1243, 620 |  |
| `F064` | supporting | topic | ❌ | - | - | no_probe_group_matched |
| `F065` | core | decision | ✅ | 3 | 1266, 1270 |  |
| `F066` | core | topic | ❌ | - | - | no_probe_group_matched |
| `F067` | supporting | topic | ✅ | 0 | 1270, 361 |  |

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
