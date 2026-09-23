# attempt-P6A-gemma31b-e6（**PASS**，16/16）

- 目的：驗證 P6-A 修補（決議類逐條對帳不再「整類靜默 no-op」）對**第二顆地端模型**
  是否同樣生效 → 回答「此機制是否模型無關」。
- 場景：`--audio /Users/hsiaojohnny/Downloads/0903-科務會議.m4a`
  （sha256 `982151f4…2828`）、`--template section_meeting`（科務會議版型）、
  `--quality-mode observe`、`--upload-mode api`。
- 模型：`gemma-4-31b-it-mlx`（LM Studio；`context_length=71936`；載入的 llm instance
  恰好 1 個，start／end snapshot 一致 → 本場歸因明確）。
- HEAD：`efa8997`（runner `expected_build_revision == actual_build_revision`）。
- 時間：2026-09-23 15:07:39 → 15:42:25（台北）＝**2,086.3 s**（runner wall；
  task 2,076.4 s）（34 分 46 秒）。
- 結果：verdict **PASS**、**16/16** checks、`failure_reasons=[]`；
  **DOCX 正常產出**（`meeting_record_docx_sha256=19f3b8f3…e5a2`、39,920 bytes）。

## pipeline 指標（backend.log 尾端 `pipeline metrics`）

- 對帳：`cov_expected_topic=9 / cov_missing_topic=0`、
  **`cov_expected_decision=11 / cov_missing_decision=0`**、
  `cov_expected_number=9 / cov_missing_number=1`（殘「600」，成因見下方觀察 3）、
  `cov_expected_date=4 / cov_missing_date=0`、`cov_issues_added=1`。
- 生成：`logical_generations=4`；`extraction 328.8 s`、`merge 0.0 s`、
  `final_and_refine 1,206.4 s`、`total 1,535.2 s`。
- 品質（observe）：`coverage_all=0.6269`、`coverage_core=0.75`
  （核心 28 項命中 21、缺 7：F001/F044/F054/F056/F060/F065/F066）；
  紀錄 2,184 字；`tagged_item_ratio=1.0`、`traceable_tag_ratio=1.0`、
  `cross_section_duplicate_pairs=0`。

## 與同家族對照（同一素材、同一模板 `section_meeting`）

| 場次 | 模型 | 決議期望／遺漏 | 紀錄字元 | `coverage_all`／`core` | wall／task |
| --- | --- | --- | ---: | --- | ---: |
| E5b（P5 對照，`ea510e5`＝修補前） | gemma-4-31b | **10／0**（本來就正常） | 2,375 | 0.5522／0.7143 | 2,138.4／2,127.6 s |
| **E6（本場）** | gemma-4-31b | **11／0** | 2,184 | **0.6269／0.75** | **2,086.3／2,076.4 s** |
| E6b | qwen3.8-27b | 27／0 | 4,853 | 0.8657／0.9643 | 1,023.2／1,015.4 s |

（E5b 的 10／0 出自 `data/cache/e2e/p4-gemma31b-e5b/backend.log:523`——該場與本場共用同一個
runtime 目錄，因為 P5 波的 gemma 場就是以該目錄重跑；時間欄一律標 runner wall／task 兩個數字。）

## 如實登錄的觀察（不得外推為通則）

1. **修補對 gemma「沒有回歸」，但不是「修補對 gemma 生效」**（**驗收後更正**）：
   本場決議期望集合非空（11 項）、最終遺漏 0；但同模型同素材的上一個 revision（E5b，`ea510e5`）
   **決議對帳本來就是 10／0** ⇒ 因果不成立。可主張的是：修補**沒有回歸**、決議抽取
   **不依賴模型名**（沒有為 qwen 特調的分支）。`coverage_all/core` 0.5522／0.7143 → 0.6269／0.75
   是**單場差**，不可單獨歸因本修補（同 build 單場擺動可達 16 pp）。
2. **gemma 紀錄明顯比 qwen 短**（2,184 vs 4,853 字）、核心覆蓋 0.75 vs 0.9643
   → 這顆模型在「完整度」上仍落後 qwen。此為**新事實**，與使用者主觀體感
   （覺得 gemma 較精準）方向不同，已如實登錄，不代為解釋成因。
3. **殘餘的 `600` 是「補強輪回退」，不是輪數不足**（**驗收後更正**）：三次對帳時點
   （`<runtime>/backend.log:328／421／511`）＝15:28（首輪）數字缺 3 項（`15／600／100`）→
   15:35（第 2 輪補強前）數字缺 **0** 項 → 15:42（第 2 輪補強後）**又缺 `600`**；
   決議類同場也是「15:35 補回一項、同時掉了另一項（`10/14 排程`）」。⇒ 每輪補強是**整份重生成**，
   會把已達標的事實寫掉（不是 no-op，也不是「輪數上限不夠」）。對症解＝重生成差異保護／局部編輯
   （P7 候選）；調高輪數只會讓同一個回退風險多跑幾次。
4. **表格欄位佔位符樣式**：決議事項表「辦理情形」欄多為「（待確認）：」，且出現
   「（（待確認））」雙層括號 → 屬家族「未修項」清單（`(待確認)` 半形／樣式正規化），
   本波未動。
5. **與雲端模型的差距仍未消除**：本場只證明「機制在 gemma 上有效」，不宣稱品質已達
   雲端水準（雲端 A/B 未在本場量測）。

## 檔案

- tracked 證據（本目錄）：`run_summary.json`、`task_final.json`、`record_quality.json`、
  `coverage_observation.json`、`model_snapshot.json`、`model_snapshot_end.json`、
  `provider_info.json`、`health_snapshot.json`、`upload_response.json`、`sha256_manifest.json`。
- raw runtime（gitignored）：`data/cache/e2e/p6a-gemma31b-e6/`（`backend.log`、
  `backend_data/outputs/0903-科務會議_f9fee652.{md,docx}`）。
