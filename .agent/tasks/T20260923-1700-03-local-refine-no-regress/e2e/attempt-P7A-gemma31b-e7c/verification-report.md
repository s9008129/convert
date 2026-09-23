# Stage 05 獨立驗收報告 — attempt-P7A-gemma31b-e7c（P7-A 地端補強輪「不回退」守衛）

- 任務：`T20260923-1700-03-local-refine-no-regress`
- 受驗場次：`e2e/attempt-P7A-gemma31b-e7c`（正式 E2E 自宣 `verdict=PASS`）
- 驗收者：Stage 05（fresh context）。**每一項判定都來自我自己的指令輸出**，不採信任何轉述。
- 我的界線：產品程式／測試／文件／既有證據一律唯讀；只新增本檔與 `result.md`；未跑新 E2E、
  未呼叫 LM Studio、未 git commit。驗收時間 2026-09-23 17:18–17:30（Asia/Taipei）。

## 結論（我的 gate）

- **獨立複驗＝PASS**（與正式 E2E 宣稱一致）。
- 主要使用者成果（能正常生成會議紀錄檔案）＝**達成**（§1、§2）。
- 一項**文件勘誤**（不構成 FAIL，但建議登錄 commit 前修正）：attempt README 的任務耗時數字錯誤（§10）。
- 回退分支本場**未實戰觸發**（如實登記，見 §4）。

## §1 檔案真實性（sha256 全部自己重算）

`shasum -a 256` 重算結果（左＝我重算，右＝宣稱值）：

| 對象 | 我重算的 sha256 | 宣稱來源 | 一致 |
|---|---|---|---|
| 來源音檔 `/Users/hsiaojohnny/Downloads/0903-科務會議.m4a` | `982151f4…2828` | `sha256_manifest.json` → `source_audio_sha256` | ✓ |
| 上傳落地 `backend_data/uploads/1dcea1c30fe5.m4a` | `982151f4…2828` | `sha256_manifest.json` → `stored_upload_sha256` | ✓ |
| 逐字稿 `transcript.txt`（與 `outputs/…_逐字稿.txt` 同 hash） | `fd40a201…72bf` | `sha256_manifest.json` → `transcript_sha256` | ✓ |
| 交付 DOCX `backend_data/outputs/0903-科務會議_bb492356.docx`（＝證據目錄 `meeting_record.docx`，兩者同 hash、同 40,026 bytes） | `df00ae0b…26cc` | `sha256_manifest.json` → `meeting_record_docx_sha256` | ✓ |
| 交付 MD `backend_data/outputs/0903-科務會議_bb492356.md` | `86667160…3801` | `run_summary.json` → `quality.record_markdown.sha256` | ✓ |

檔案大小（`stat -f %z`）：來源音檔＝上傳落地＝`task_final.file_size`＝`upload_response.file_size`＝45,107,503 bytes，四方一致。

DOCX 用 `python-docx` 實開（`uv run --frozen python`），並以 `unzip -t` 驗 OOZIP 完整性（通過）：

- 段落數 **45**、表格數 **1**（13 列 × 4 欄）、sections **1**。
- 正式欄位：`主持人`、`出席人員`、`決議事項`、`臨時動議`、`散會`、逐項列管表
  （表頭＝`案由及承辦單位 / 辦理情形 / 解除列管 / 繼續列管`）；標題列為「科務會議紀錄」。
  「主席」「待辦事項」**字面**未出現（分別以「主持人」「決議事項辦理情形彙整表」承載）；
  簽到資訊以「出席人員：如後附簽到表」表示。
- `會議紀錄生成失敗`：DOCX 與 MD **皆無**。runner 的 fallback 標記
  （`逐字稿（會議紀錄生成失敗）`／`摘要生成失敗`／`Traceback`／`RuntimeError`／`錯誤訊息`）也全數未出現。
- 另用 runner 同一份 `section_meeting` 章節契約（`scripts/e2e/run_owned_e2e.py:125-131`）獨立重驗：
  「一、科長轉知」「二、科長指示及提醒事項」「案由及承辦單位」「散會」四項**皆存在且有非空後續內容**。

## §2 revision 與任務終態

- `run_summary.json`：`expected_build_revision == actual_build_revision == b2f11cafae2bb5ba0a0ff3713f78c579a7ac2199`。
  `health_snapshot.json` 的 `raw_response.build_revision` 同值；`status=healthy`。
- git 佐證（我自己跑）：
  - `git merge-base --is-ancestor 3e9311a b2f11ca` ⇒ **YES**（守衛程式已在受測修訂內）。
  - `git diff b2f11ca 53de4e4 --stat` ⇒ 只有文件與任務證據 6 檔（CHANGELOG、手冊、規劃文件、
    execution／review-02／generality-audit），**無任何產品程式**；`backend/core/config.py`、
    `backend/services/summarization.py`、`backend/services/task_processor.py` 在 `3e9311a..HEAD` 全等（diff 為空）。
    ⇒ **受測程式＝現行交付程式**。
- `task_final.json`：`status=completed`、`summary_failed=false`、`error_message=null`、`task_id=bb492356`
  （與 `upload_response.json.task_id` 一致）。
- `run_summary.json` 的 `checks`：我用程式重數＝**16 個鍵全 true**、`failure_reasons=[]`、`verdict=PASS`。

## §3 模型歸因

- `model_snapshot.json` 與 `model_snapshot_end.json`（`captured_at` 16:42:19 與 17:17:39）：
  `loaded_instance_ids=["gemma-4-31b-it-mlx"]`、`unique_loaded_llm_count=1`，且兩份 `raw_response` **逐位元組相等**
  ⇒ 整場同一顆且唯一 loaded LLM。
- `qwen3.6-35b-a3b-splash` 只出現在**清單**（`raw_response.models`），`loaded_instances: []`；`openai_compat_model_ids: []`。
- `backend.log`：`grep -c -i qwen` ⇒ **0**。16 次「使用 LM Studio 生成摘要」行（行 52／65／76／86／96／105／114／123／133／144／155／165／178／250／337／432）
  **全部** `model=gemma-4-31b-it-mlx`；成功行亦為「模型: gemma-4-31b-it-mlx」。
- `backend_data/logs/app_2026-09-23.log`、`structured_2026-09-23.jsonl` 的 qwen 比對亦為 **0 筆**。
- `gemini` 全場只出現 1 次＝啟動組態行（`backend.log:23`，`cloud_provider=gemini, cloud=gemini-3.5-flash-lite`），
  屬組態宣告；本場 `run_summary.json` 的 `engine.mode_used=local`、`task_final.processing_mode=local`。
- ⇒ **使用者明文禁止的 `qwen3.6-35b-a3b-splash` 整場未被使用**（也未載入）。

## §4 守衛證據（如實判定）

- `grep -n '地端補強不回退守衛' backend.log` ⇒ 恰 **2 行**：
  - `backend.log:430`（17:10:27）`第 1 輪核心未涵蓋 11 → 4 項（期望 34 項）（更好，取本輪）`
  - `backend.log:525`（17:17:35）`第 2 輪核心未涵蓋 4 → 2 項（期望 34 項）（更好，取本輪）`
- `grep '造成事實回退'` ⇒ **0 行**；「停用比較」「取不到核心覆蓋快照」「基準不同不可比」亦 **0 行**。
- 全場唯一 WARNING（`backend.log:526`）是迴圈結束後的殘留問題提示（既有行為，兩輪跑完仍在清單上），**不是回退事件**。
- **判定：本場兩輪都更好（11 → 4 → 2），回退分支未被實戰觸發**（本場無「丟棄本輪輸出」發生；如實登記，不記 FAIL）。
- 回退分支的證據來源（我**自己動手重跑**，非只讀結論）：
  - `tests/test_t20260923_p7a_refine_no_regression.py`：`DATA_DIR=/tmp/… pytest` ⇒ **12 passed**（T01–T12）。
  - `e2e/attempt-P7A-offline-replay/replay_guard.py`：我重跑 ⇒ `guard_would_revert: true`、
    `guard_reason: 未涵蓋數變多`，且 `better 26/46（2,193 字）`、`final 27/46（2,184 字）` 與登錄的 `output.json` 完全一致。
- 守衛行語意出處（現行碼）：`backend/services/summarization.py:3406-3496`（逐輪 best 追蹤；better/持平取本輪、
  回退則 `summary = best_summary` 並印 warning；行 3475 為 warning 格式、3490 為 info 格式）。

## §5 獨立覆蓋率重算

- 我跑 `uv run --frozen python scripts/e2e/measure_coverage.py --record 交付MD --checklist .agent/tasks/T20260922-2037-02-local-model-quality-parity/quality/fact_checklist.json --transcript transcript.txt --no-timestamp`。
- 我重算：`coverage_all=0.5821`、`coverage_core=0.75`、`covered_core=21/28`、
  `missing_core_ids=[F044,F054,F055,F056,F060,F065,F066]`、`record_sha256=86667160…`。
- 與 `coverage_observation.json`（`coverage_all:9 行`、`coverage_core:10 行`、`missing_core_ids:15-23 行`）**逐欄一致**；
  checklist 我重算 sha256＝`cf012d1f…6ec001`，與兩處登錄值一致。
- 附加（此輪順手量，供交叉檢查）：逐字稿觀察值 `coverage_core=1.0`（缺 F058 supporting）
  ⇒ 交付紀錄的 7 條 core 漏寫不是清單瑕疵；但也提醒量尺是**字面**比對（換句話說會偽陰性，
  F001／F054 在 P6-A 已知是此類，見 `quality/README_measure_coverage.md`）。

## §6 交付版本＝最佳版本？

- 由 log 可唯一推定：本次執行最佳＝**核心未涵蓋 2 項／期望 34 項**
  （`backend.log:525` 第 2 輪「4 → 2」＋ `backend.log:527` metrics 行
  `cov_expected_topic=10 cov_missing_topic=1 cov_expected_decision=11 cov_missing_decision=1 cov_expected_number=9 cov_missing_number=0 cov_expected_date=4 cov_missing_date=0`
  ⇒ 缺 1+1＝2、期望 10+11+9+4＝34）。
- 交付紀錄自身的對帳行（`backend.log:523,524`）：議題缺 1（其他行政裁示）＋決議缺 1（提醒承辦人員…早點出發）＝2。
- ⇒ **一致：交付版本＝本次執行最佳版本（2/34）**；第 1 輪的 4 項已被更好的第 2 輪取代，無回退發生。

## §7 歷史對照（如實、不誇大）

- 本場：`coverage_all 0.5821`／`coverage_core 0.75`（`coverage_observation.json`；我重算一致）。
- P6-A gemma E6：`coverage_all 0.6269`／`coverage_core 0.75`
  （`.agent/tasks/T20260922-2037-02-local-model-quality-parity/e2e/attempt-P6A-gemma31b-e6/coverage_observation.json` 第 9–10 行）。
  ⇒ **核心覆蓋相同、`all` 略低**；漏 core 集合不完全相同（E6：F001,F044,F054,F056,F060,F065,F066；本場：F044,F054,F055,F056,F060,F065,F066）。
  **這是單場抽樣比較（temperature 0.7），不可當成機制成效的證據。**
- 雲端可比基線：`coverage_core 0.8929`（`e2e/attempt-C5-cloud-baseline/coverage.json`；
  亦見 `research/p7-gap-analysis.md:42-46`）⇒ 本場 0.75 **尚未達**雲端 Gemini 水準。

## §8 範圍與不變式抽查

- `git show 3e9311a --stat`：`backend/core/config.py`（+17）、`backend/services/summarization.py`（+167）、
  `tests/test_t20260923_p4a_record_coverage.py`（±13）、`tests/test_t20260923_p7a_refine_no_regression.py`（新 +407）、
  餘為 `.agent` 任務檔（plan／handoff／research／review-01／offline-replay）。
- 新增程式碼**無模型名分支**：`3e9311a` 的 backend diff 中「+」行含 gemma/qwen 者只有 **2 行註解**；
  檔內其餘 gemma4 分支（如 `summarization.py:4906／4983`）是舊有 Ollama 正規化程式（`e21ba4e` 引入），非本波。
- `backend/services/task_processor.py` **未被本波修改**：不在 `3e9311a`／`53de4e4` 變更清單，
  `git log` 最後一次修改為 `48ad6d6`（本波之前）。
- 工作樹現況：`git status` 僅一個 untracked 目錄（本 attempt 證據，含本報告）⇒ 證據**尚未 commit**（登錄屬下一步）。

## §9 殘餘風險清單

1. **回退分支未在本次 E2E 實戰觸發**（兩輪都更好）：機制在真實場次的觸發效果仍屬 `[UNVERIFIED]`；
   現有證據＝12 個單元測試＋離線重播（真實素材，判定 would-revert）。
2. **等量互換偽陽性**：換句話說可能被判成「換項」而回退（最壞後果＝維持前一版、不弄壞內容）；
   已由 `verification/p7a-generality-audit.md` 登錄為已知界線。
3. **Windows 11＋Ollama 實機 `[UNVERIFIED]`**（本場為 macOS＋LM Studio 路徑）。
4. **本波不提升初始生成品質**：支持性覆蓋（`coverage_supporting 0.4615`）、大量 `（待確認）` 等主要落差仍在，
   距雲端水準的槓桿仍是萃取筆記資訊量與逐條化收斂。
5. **文件與登錄**：attempt README 耗時 typo（§10）；證據需 commit 後才進版控。
6. 覆蓋量尺本身限制（字面比對；偽陰性／偽陽性），漏寫清單僅為「待人工抽查的線索」。

## §10 勘誤（登錄 commit 前建議修正）

- `README.md`（本 attempt）寫「任務本身：`16:42:19.68 → 17:17:35.75`＝**1,916.1 s（31 分 56 秒）**」，
  正確為 **2,116.1 s（35 分 16 秒）**：我以 `task_final.json` 的 `started_at/completed_at` 自行計算＝2,116.06 s；
  `backend.log:539` 亦載「任務 bb492356 處理完成，耗時: 2116.1秒」。（數字位數誤植，屬登錄瑕疵，不影響 PASS。）
- README 其餘數字（runner wall 2,125.5 s、sha256、40,026 bytes、16/16、守衛節錄與時間）我逐項核對**皆正確**。

## 附錄：本報告所有判定對應的指令（重跑可復現）

- `shasum -a 256`（來源音檔／落地音檔／逐字稿／DOCX／MD）＋ `stat -f %z` 檔案大小。
- `uv run --frozen python` ＋ `python-docx`（45 段／1 表／欄位掃描／fallback 標記掃描）＋ `unzip -t`。
- `git merge-base --is-ancestor`／`git show 3e9311a --stat`／`git diff b2f11ca 53de4e4 --stat`／
  `git diff 3e9311a HEAD -- backend/…`／`git log -S`。
- `grep -n`（守衛行、造成事實回退、qwen、模型行、metrics 行）、`json` 程式重數 checks。
- `DATA_DIR=/tmp/p7a_verify_data uv run --frozen python -m pytest tests/test_t20260923_p7a_refine_no_regression.py -q` ⇒ 12 passed。
- `uv run --frozen python .agent/…/attempt-P7A-offline-replay/replay_guard.py` ⇒ 與 `output.json` 一致。
- `uv run --frozen python scripts/e2e/measure_coverage.py --record … --checklist … --transcript … --no-timestamp` ⇒ 與 `coverage_observation.json` 一致。
