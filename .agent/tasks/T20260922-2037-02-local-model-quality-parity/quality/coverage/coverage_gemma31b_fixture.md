# 事實涵蓋率報告：gemma31b-fixture

- 量尺版本：`coverage-1.0.0`
- 受測紀錄：`data/cache/e2e/p2-gemma31b-fix-01/backend_data/outputs/0903-科務會議_ac1edcec.md`（sha256 `7d2de68463ada245b211b78e88e67ade1caa730059d527956afa442d2f158485`；字元數 1927，正規化後 1382）
- 事實清單：`data/cache/staging/coverage/fixture_checklist.json`（sha256 `0aad631bacb4b90bbeb5d54aec4b48ed03f223dffaf99a19fad3336e5d4c3fa5`；checklist_version `1.0.0`；meeting `0903-科務會議`；共 8 條＝core 6＋supporting 2）
- 正規化：unicode_nfkc、casefold、opencc_fold_s2twp、strip_whitespace_and_newlines、strip_punctuation_and_symbols；OpenCC 可用（`opencc-s2twp`）；fuzzy 停用
- 逐字稿（觀察值）：`data/cache/e2e/p2-gemma31b-fix-01/backend_data/outputs/0903-科務會議_ac1edcec_逐字稿.txt`；coverage_all 0.8750（87.5%；7/8）、coverage_core 0.8333（83.3%；5/6）

## 總覽

| 指標 | 數值 |
| --- | --- |
| coverage_all | 1.0000（100.0%；8/8） |
| coverage_core | 1.0000（100.0%；6/6） |
| coverage_supporting | 1.0000（100.0%；2/2） |

## 分類涵蓋率

| category | total | covered | coverage |
| --- | --- | --- | --- |
| decision | 3 | 3 | 1.0000（100.0%；3/3） |
| number | 1 | 1 | 1.0000（100.0%；1/1） |
| action_item | 2 | 2 | 1.0000（100.0%；2/2） |
| date | 1 | 1 | 1.0000（100.0%；1/1） |
| constraint | 1 | 1 | 1.0000（100.0%；1/1） |

## 漏寫事實（core；0 條）

（無）

## 漏寫事實（supporting；0 條）

（無）

## 警告（0 條）

（無）

## 事實明細

| id | tier | category | 涵蓋 | matched group | matched positions | 備註 |
| --- | --- | --- | --- | --- | --- | --- |
| `F001` | core | decision | ✅ | 0 | 368, 373 |  |
| `F002` | core | decision | ✅ | 0 | 386 |  |
| `F003` | core | decision | ✅ | 0 | 454, 458 |  |
| `F004` | supporting | number | ✅ | 0 | 493 |  |
| `F005` | core | action_item | ✅ | 0 | 173, 185 |  |
| `F006` | supporting | action_item | ✅ | 0 | 246, 1043 |  |
| `F007` | core | date | ✅ | 0 | 226, 221 |  |
| `F008` | core | constraint | ✅ | 0 | 749, 752 |  |

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
