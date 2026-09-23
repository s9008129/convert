# attempt-E4-qwen27b-p4-final — `run_notes.md` 更正與補登錄（append-only addendum）

> 觸發：Stage 05 獨立驗收（`verify_independent.md` §6.2）點名 `run_notes.md` 兩處內部錯誤與一處登錄缺口。
> 本檔為 **append-only 更正**，不改寫原檔（比照 E3 的 `run_notes_addendum.md` 慣例）。
> 另併記一件必須揭露的事實：**同一路徑在 2026-09-23 11:28–11:29 之間有兩個並行寫入版本**
> （11:28 主執行 agent 版 15,113 bytes；11:29 另一寫入者版 7,080 bytes，目前留在磁碟上的是後者）。
> 凡本 addendum 與該檔衝突處，**以本檔為準**（每項都附可重跑的證據命令與原始 log 行號）。

---

## A. 更正 1：摘要三階段的標籤對調（`run_notes.md` §二）

原檔寫成：

| 原檔標籤 | 秒數 | 原檔關鍵數字 |
|---|---|---|
| 摘要 round 0（紀錄生成） | 258.9 | `prompt_tokens=12474`、`completion_tokens=3482` |
| 摘要（萃取筆記） | 231.7 | 產出 3220 tokens 筆記、零損串接 |

**正確對應為**：

| 正確階段 | 秒數 | 請求（`_summarize_with_lmstudio` L95／L99／L106） | 回應診斷（L96／L100／L107） |
|---|---|---|---|
| **萃取（notes extraction）** | **258.95**（11:09:27.109→11:13:46.059） | `temperature=0.6`、`max_tokens=8192`、`prompt_tokens=12583` | `prompt_tokens=12474`、`content_chars=4776`、`completion_tokens=3482`、`reasoning_chars=0` |
| **首版最終生成（final）** | **231.71**（11:13:46.064→11:17:37.771） | `temperature=0.7`、`prompt_tokens=17956` | `prompt_tokens=17983`、`content_chars=2706`、`completion_tokens=2051` |
| **補強第 1 輪** | **256.30**（11:17:37.851→11:21:54.153） | `temperature=0.7`、`prompt_tokens=20140` | `prompt_tokens=20296`、`content_chars=2706`、`completion_tokens=2051`（**與首版逐字相同長度**） |

三項獨立證據（皆可重跑）：

1. **pipeline metrics**（`app_2026-09-23.log:114`）：
   `duration_seconds={'extraction': 259.0, 'merge': 0.0, 'final_and_refine': 488.2, 'total': 747.1}`；
   而 `231.71 + 256.30 = 488.01 ≈ 488.2` → **259.0 只能是萃取，231.7 只能是首版最終生成**。
2. **prompt 增量**：12,583 →（+3,220 筆記）→ 17,956 →（+問題清單）→ 20,140；`萃取筆記零損串接…1 份、3220 tokens`
   出現在 11:13:46.061，緊接在第一次呼叫之後（`_consolidate_notes:2583`）。
3. **輸出內容對比**：`content_chars` 4,776（筆記，`≈3.2k` tokens）vs 2,706（成品紀錄，磁碟上 `.md` = `char_count 2717`）。

> 影響：原檔的錯誤標籤會讓人誤判「紀錄生成只花 258.9 s、筆記才 231.7 s」。
> 正確結論不變：**本機 LLM 推論仍是瓶頸**（校正 68.4 s ＋ 生成 747.1 s ＝ 815.5 s／985.2 s ＝ 82.8%）。

## B. 更正 2：E3 的補強輪數誤值（`run_notes.md` §四）

原檔寫「E3 補強輪數 1（收斂後停）」。**正確：E3 跑了 2 輪且**跑滿上限（`MAX_REFINEMENT_ROUNDS=2`）**，
第 2 輪是被上限截斷、非收斂**：

```
$ grep -o "品質補強（第 [0-9] 輪）" data/cache/e2e/p4-qwen27b-e3/backend_data/logs/app_2026-09-23.log | sort -u
品質補強（第 1 輪）
品質補強（第 2 輪）
```

E4 才是**第 1 輪後由「問題集合與上一輪相同」停損**（`app_2026-09-23.log:112`），兩者不可混為一談。
這也正是本場時間下降（−28.9%）的主因之一：省下 1 輪 ≈ 256.3 s。

## C. 補登錄：`決議期望集合為空` WARNING ×2（決議類對帳 no-op）

原檔全篇未提。實際 log：

- `app_2026-09-23.log:102`（11:17:37.802）與 `:109`（11:21:54.183），皆為
  `_validate_record_source_coverage:1868 | 紀錄覆蓋率檢查：決議期望集合為空（來源：萃取筆記「議題與決議」區塊）→ 本類別不產生補強問題`。
- 對應欄位：`cov_expected_decision=0`、`cov_missing_decision=0`（L114）→ **決議類在本場是 no-op**，
  最終 decision 8/9 的成績應歸模型本身，不得計給 P4-A。

## D. 追加揭露：本場的 B1（歸屬絆索）證據力受限（獨立驗收 §四-2）

- E4 紀錄的 **29 個出處標註全部使用角色名「科長」**（`grep -o '（[^）]*，[0-9:]*）' <md> | sed 's/，.*//'`
  → `29 （科長`），因此 `exact_tag_ratio=0.000`、`same_speaker=0/29`；
  而 B1 的可檢命名空間是逐字稿的「發言者N」→ **本場「歸屬待確認 0 筆」只是字面成立，不是有效對照**。
- `eb9dfeb` 修補的有效證據是**離線重播 E3 素材**（舊碼 14 筆 → 新碼 0 筆，且 16 份語料零新增），
  加上 E3 in-run log 的 14 筆；**不得宣稱「E4 已 in-run 驗證 B1」**。

## E. 本 addendum 之後，E4 可對外引用的凍結數字

`verdict=PASS`／16/16 checks；牆鐘 **992.243 s**、任務 **985.156 s**；補強 **1 輪（停損）**；
`logical_generations=3`；`coverage_all 0.7015`／`core 0.8214`（23/28）；`char_count 2717`；
`cov_missing_topic=0`、`cov_missing_number=2`（15、600）、`cov_missing_date=1`（週一）；
`number_fabricated=0`、`unsupported_entities_count=3`；真缺口＝15%／600／100 元／下週一內稽／社交工程郵件／搬遷細節。
