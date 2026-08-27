# WAVE-03b evidence index — runtime provenance 與 owned-process E2E runner

任務：T20260827-1127-01-lmstudio-e2e-empty-summary（CHANGE_MAP 第 5 項、RC-5）
執行時間：2026-08-27 15:00–15:20（台北時間），HEAD 2e446ed

## 變更檔案

- `backend/models/schemas.py`：`HealthStatus` 新增 nullable `build_revision: Optional[str] = None`（additive 向後相容）。
- `backend/core/config.py`：新增 `MEETINGSCRIBE_BUILD_REVISION`（Optional，預設 None）與 `SERVICE_PORT`（AliasChoices 接受 `SERVICE_PORT`/`MEETINGSCRIBE_PORT`，預設 9527）。
- `backend/api/routes.py`：`_resolve_build_revision()`（settings → env，空值視為 unknown/null）並填入 health response；既有欄位與狀態碼不變。
- `backend/main.py`：startup log 改讀 `settings.SERVICE_PORT`（移除固定 9527）＋新增 Build revision log；`__main__` uvicorn.run 改用 `settings.SERVICE_PORT`。
- `scripts/e2e/run_owned_e2e.py`（新增）：owned-process E2E runner。
- `README.md`：health response 範例、常用環境變數表、runner 用法段落。

## 驗證結果

| 檔案 | 說明 |
|------|------|
| `baseline-tests.txt` | 修復前 baseline：TestHealthBuildRevision 3 個測試以預期原因（RC-5）失敗；api_routes 52 passed |
| `post-fix-health-revision-tests.txt` | 修復後：TestHealthBuildRevision **3 passed** |
| `post-fix-wave01-tests.txt` | wave01 全檔：1 failed（TestChunkOverlapBound，WAVE-03a 平行 agent 範圍）、5 passed |
| `post-fix-api-routes-tests.txt` | 52 passed，無回歸 |
| `runner-help.txt` / `runner-dry-run.txt` | runner `--help` 與 `--dry-run`（不啟動、不建目錄） |
| `runner-smoke-ok-console.txt` | 煙霧驗證 PASS（verdict=PASS，exit 0） |
| `runner-smoke-mismatch-console.txt` | gate 自我驗證：不注入 revision → actual=null → verdict=FAIL（exit 1），證明 gate 具鑑別力 |
| `smoke-ok-attempt-01/`、`smoke-ok-attempt-02/` | 煙霧 artifacts（backend.log / health_snapshot.json / model_snapshot.json / run_summary.json）；attempt-02 含改善後 model snapshot（qwen3.6-35b-a3b-mlx，context_length 183296，unique_loaded_llm_count=1） |
| `smoke-mismatch-attempt-02/` | gate FAIL 路徑的 artifacts（run_summary.json failure_reasons 記錄 mismatch） |

## runner 煙霧驗證要點

- free port（53103/53167/53138 等）＋隔離 temp DATA_DIR（於 attempt 目錄下）＋注入 `MEETINGSCRIBE_BUILD_REVISION=$(git rev-parse HEAD)`。
- backend.log 第 16-17 行：`服務已就緒，監聽端口: 53103`＝uvicorn 實際 `Uvicorn running on http://127.0.0.1:53103`（RC-5 actual port logging 一致）；`Build revision: 2e446ed…`。
- child 以 `start_new_session` 獨立 process group 啟動、僅 kill 自己的 group；煙霧後無殘留 process（已驗證 pgrep）。
- append-only：attempt 目錄已存在即拒絕（曾實測擋下重複使用）。
- LM Studio `/api/v1/models` 唯讀快照，不相容兩種 shape（native `models[]`/OpenAI `data[]`）。

## 分類註記

- `TestChunkOverlapBound::test_chunk_boundary_carry_tokens_within_220_token_budget` 失敗：WAVE-03a（平行 agent）summarization.py chunking 範圍，非本 wave 回歸；WAVE-03a 曾於 15:14 出現暫態 syntax error（summarization.py:161），穩定後（15:16+）其餘測試恢復。
- pre-existing：無（api_routes 52 passed 與 baseline 相同）。