# attempt-P6A-qwen27b-e6b（**PASS**，16/16）

> **登錄性質：驗收後補登（post-acceptance backfill）。** 本 README 是在驗收完成後才補寫的說明文件，
> 用來補齊本目錄原本缺的「人可讀說明」。**既有證據檔案（`run_summary.json`、`task_final.json`、
> `record_quality.json`、`coverage_observation.json`、`model_snapshot*.json`、`provider_info.json`、
> `health_snapshot.json`、`upload_response.json`、`sha256_manifest.json`）一字未改、未被覆寫**；
> 本檔只在同目錄新增，不影響任何 verdict。

- 目的：驗證 P6-A 修補（決議類逐條對帳不再「整類靜默 no-op」）在**主測模型**上生效，並取得
  對照組（gemma31B）用的同一把尺數據。
- 場景：`--audio /Users/hsiaojohnny/Downloads/0903-科務會議.m4a`
  （sha256 `982151f4…2828`）、`--template section_meeting`（**科務會議版型**）、
  `--quality-mode observe`、`--upload-mode api`、`--coverage-checklist .agent/tasks/…/quality/fact_checklist.json`
  （sha256 `cf012d1f…`）。
- 模型：`qwen3.8-27b-splash`（LM Studio；instance `context_length=128000`；載入的 llm 恰好 1 個，
  start／end snapshot 一致 → 本場歸因明確）。
- HEAD：`277531b`（runner `expected_build_revision == actual_build_revision`）。
- 時間：2026-09-23 14:45:32 → 15:02:35（台北）＝**1,023.2 s**（runner wall；**task 1,015.4 s**）
  （約 17 分鐘）。
- 結果：verdict **PASS**、**16/16** checks、`failure_reasons=[]`；
  **DOCX 正常產出**（`meeting_record_docx_sha256=e7bde206…b113`、42,508 bytes；
  紀錄 Markdown sha256 `5db6859f…0326`／4,853 字）。

## pipeline 指標（`<runtime>/backend.log` 尾端 `pipeline metrics`）

- 九個對帳欄位（`observe` 模式＝只記錄、不改品質）：
  `cov_expected_topic=14 / cov_missing_topic=0`、
  **`cov_expected_decision=27 / cov_missing_decision=0`**、
  `cov_expected_number=9 / cov_missing_number=0`、
  `cov_expected_date=4 / cov_missing_date=0`、
  `cov_issues_added=0`（最終輪不需再補）。
- 生成：`logical_generations=3`（＝1 萃取＋1 生成＋**1 輪補強**；log 只有一次
  「本地摘要品質補強（第 1 輪）」，`backend.log:217`）；`extraction 166.8 s`、
  `merge 0.0 s`、`final_and_refine 602.7 s`、`total 769.6 s`。
- 歷程（真的抓到漏項才補強）：14:57:01 首輪對帳同時長出 **待辦 1 項**＋**決議 3 項**（含「建議辦公室
  下午茶形式…」、「提醒需考慮 3 位工程師無法請假…」、「建議向行政課確認…示範點…」）＋**數字 4 項**
  （`600／800／17／13600`）→ 第 1 輪補強後（15:02）**全部歸零**：最終 metrics 九欄無一遺漏，
  且 `backend.log` 沒有 `本地摘要仍有待補強問題` warning（該 warning 的產生點 `summarization.py:3373`）
  ＝**收斂**，不是把問題帶進成品。
- 品質（observe）：`coverage_all=0.8657`、`coverage_core=0.9643`（核心 28 項命中 27、缺 `F055`；
  雲端對照場 `0.8060／0.8929`、地端舊場 E3 `0.7761／0.8571`）；
  `tagged_item_ratio=1.0`、`traceable_tag_ratio=1.0`、`on_start_tag_ratio=1.0`、
  `cross_section_duplicate_pairs=0`、`unsupported_entities_count=0`、
  已登錄誤辨修正命中 `right_hits=8`；`warnings=[]`、`errors=[]`、`check_failures=[]`。

## 與本家族其他場次的關係

| 場次 | 模型 | 決議期望／遺漏 | 紀錄字元 | `coverage_all`／`core` | wall／task |
| --- | --- | --- | ---: | --- | ---: |
| E6（**中止**，`7139d44`） | qwen3.8-27b | —（無 verdict） | — | — | — |
| **E6b（本場，`277531b`）** | qwen3.8-27b | **27／0** | 4,853 | **0.8657／0.9643** | **1,023.2／1,015.4 s** |
| E6（gemma 場，`efa8997`） | gemma-4-31b | 11／0 | 2,184 | 0.6269／0.75 | 2,086.3／2,076.4 s |

- 中止場（`attempt-P6A-qwen27b-e6/`）跑的是 `7139d44`，不是最終 HEAD → 不作驗收證據；
  本場（E6b）才是 qwen 的正式驗收場。
- 同一支 runner、同一模板、同一支音檔、同一份 checklist，只換模型 → 兩顆模型的決議遺漏都是 0；
  但 gemma 的紀錄明顯較短、核心覆蓋較低（**單場差，不作趨勢宣稱**）。
- 耗時落差主因是**模型單次生成速度**（gemma 場 `logical_generations=4`＝多一輪補強），
  不是本修補造成；修補前後同模型同素材由 1,670.5／1,662.1 s → 1,023.2／1,015.4 s（未膨脹，反降）。

## 檔案

- tracked 證據（本目錄）：`run_summary.json`、`task_final.json`、`record_quality.json`、
  `coverage_observation.json`、`model_snapshot.json`、`model_snapshot_end.json`、
  `provider_info.json`、`health_snapshot.json`、`upload_response.json`、`sha256_manifest.json`。
- raw runtime（gitignored）：`data/cache/e2e/p6a-qwen27b-e6b/`（`backend.log`、
  `backend_data/outputs/0903-科務會議_c605df1a.{md,docx}`）。
