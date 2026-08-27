# Stage 04 執行紀錄 — 最新音檔空摘要：驗收器與 runtime provenance 強化（Revision 3）

- TASK_ID: T20260827-1127-01-lmstudio-e2e-empty-summary
- STAGE: 04_IMPLEMENT → READY_FOR_STAGE_05
- PLAN_REVISION: 3
- PLAN_SHA256: d76e236204e53a298741f02e012a3d96e7de12cb89be072c77cdc0a9b9d7dafd（執行前以 `shasum -a 256` 實測相符）
- HANDOFF: `.agent/tasks/T20260827-1127-01-lmstudio-e2e-empty-summary/handoff.md`（STATUS: READY_FOR_IMPLEMENTATION；PLAN_REVISION: 3；REVIEW_REQUIRED: NO）
- 執行模式: Fleet（WAVE-01a/01b/02/03a 由各實作子代理完成，WAVE-03b 由最終 packaging 子代理執行全文驗證、本檔與 scoped commit）
- 執行時間: 2026-08-27T20:00–20:10+08:00（Asia/Taipei）
- Branch: main；commit 前 HEAD: `31fb43cfb413c4efc92deef9c47f13c820ac1199`（docs-only Revision 3 handoff commit）；本 execution.md 與 scoped 實作/證據於同一 packaging commit 落檔，commit 後 HEAD 請以 `git log -1` 為準（Stage 05 即以該 SHA 作為 accepted candidate 進行 exact-revision E2E）

## 已完成 Waves（一句話結果）

- **WAVE-01a**：新增 `tests/test_owned_e2e_acceptance.py` 23 案（importlib 載入 runner、pure helpers/fake client，不啟 ASR、不上傳音檔）；首個有效 red `20 failed, 3 passed`，全數因批准中行為缺失而 red。
- **WAVE-01b**：`tests/test_macos_scripts.py` +232 行 fail-first launcher 契約測試；首個有效 red `8 failed, 4 passed`（revision derive/inject/verify、writable DATA_DIR、health JSON exact-match、owned-only cleanup、實際 port/root/DATA_DIR/revision logging）。
- **WAVE-02**：`scripts/e2e/run_owned_e2e.py` 強化（+887 行區間）：pure validation helpers（SHA/repo/revision/data/model/task/formal DOCX/metrics）、fail-closed preflight（clean HEAD/revision/audio/data 於任何 start/upload 前）、固定 gate 順序、`--upload-mode api|browser`、`--runtime-dir`、`BROWSER_E2E_READY` flush、API/browser 共用 formal 判定、DEC-EVIDENCE tracked-redacted vs gitignored-raw 分層、owned-only cleanup；CLI `--help`/`--smoke --dry-run`/actual smoke 全部驗證。
- **WAVE-03a**：`scripts/macos/start-mac-native.sh` +89/-5（revision derive/inject/verify、dirty 可區分、requested-revision preflight、writable DATA_DIR probe、health JSON exact-match 後才 ready、EXIT trap owned-only cleanup、無 pkill/killall）；`bash -n` 通過。
- **WAVE-03b（本階段）**：全文驗證（regression/focused/full suite/diff 檢查/runner CLI/actual smoke/LM Studio 觀察）、寫本檔、scoped clean commit。

## 實際執行的驗證指令與觀察結果

隔離測試根（runtime 禁止 mktemp -d，改用 gitignored `data/cache/`）：
`TEST_DATA_ROOT=data/cache/wave03b-testroot`、`DATA_DIR="$PWD/data/cache/wave03b-testroot/data"`（shell 原值為 unset，明確覆寫避免任何繼承）。

| # | 指令 | 觀察結果 |
|---|------|---------|
| 1 | `DATA_DIR=… uv run pytest -q tests/test_wave01_merge_budget_separation.py tests/test_wave01_recovery_sequence.py tests/test_wave01_merge_convergence.py tests/test_wave01_overlap_provenance.py tests/test_t20260827_regression.py` | **33 passed, 2 warnings, 0 failed**（與 WAVE-02 記錄一致） |
| 2 | `DATA_DIR=… uv run pytest -q tests/test_owned_e2e_acceptance.py tests/test_macos_scripts.py` | **35 passed**（23 + 12，與 WAVE-01/02 預期完全一致），0 failed |
| 3 | `DATA_DIR=… uv run pytest tests/ -q --ignore=tests/test_mlx_direct.py` | **549 passed, 2 skipped, 0 failed**（3 warnings）。skip 為 `test_whisper_fix.py:38` 兩個「測試音檔不存在」（`tests/test_audio/` 為 gitignored 環境狀態），與 Revision 2 報告記錄的 2/3 環境性 skip 變異一致 |
| 4 | 全 suite 數量歸因：以 `git worktree add --detach data/cache/wave03b-headwt HEAD`（驗後即刪）對 HEAD 狀態 `--collect-only`，並 diff 兩邊收集 ID | HEAD 收集 **519**；現 working tree 收集 **551**；排除兩個核准測試檔後 ID diff 為**空**。delta = +23（新檔）+9（test_macos_scripts.py 3→12；WAVE-01b red 記錄的「4 passed」含 1 個立即通過的新控制測試，故原既有為 3 而非 4）。**全套件數量完全歸因，0 失敗，無未解釋差異** |
| 5 | `bash -n scripts/macos/start-mac-native.sh` | OK |
| 6 | `git diff --check`（staging 前） | CLEAN |
| 7 | `uv run python scripts/e2e/run_owned_e2e.py --help` | 正常輸出全部旗標（`--upload-mode api|browser`、`--runtime-dir` 等） |
| 8 | `uv run python scripts/e2e/run_owned_e2e.py --smoke --dry-run` | EXIT=0；「未啟動 backend、未建立任何目錄」；目錄檢查確認未建 dir；expected_build_revision=當下 HEAD |
| 9 | `uv run python scripts/e2e/run_owned_e2e.py --smoke --artifacts-dir data/cache/e2e/smoke-rev3/attempt-20260827-200636` | **verdict=PASS，EXIT=0**：free port 51361、health 200 且 build_revision 與 expected（`31fb43cf…`）exact match、`unique_loaded_llm_count=1`、owned child exit=0 |
| 10 | smoke 後 `ps -p 42438` | CHILD_GONE_OK（owned child 已清除，無殘留） |
| 11 | LM Studio 觀察（read-only GET `/v1/models` + smoke `model_snapshot.json`） | reachable=True；唯一 loaded LLM = `qwen3.6-35b-a3b-mlx`（單一 instance，context 183296）；另有 2 個 embedding model，runner 的 unique-LLM 計數正確排除之。與 planning-time facts 一致，未更動 inventory |
| 12 | `git status --short --branch` / `git diff --stat` / `git diff --check`（最終範圍檢查） | 僅含核准檔案：runner、launcher、2 個測試檔、rev3-wave01/02/03a/03b 證據目錄；**無 backend/frontend/dependency/lockfile/API-schema 變更**；diff 內容掃描確認 runner diff 無 `backend/*` 引用、pkill/killall 僅出現於「禁止使用」的測試斷言 |

未執行（依 handoff 禁令）：真實音檔上傳（`/Users/hsiaojohnny/Downloads/盤點工具討論.m4a`）、port 9527 啟動/切換、LM Studio inventory 變更、`result.md`。

## 測試調整說明

- **WAVE-02 的 `git_status_porcelain` stub（tests/test_owned_e2e_acceptance.py L372–375，5 行）**：該正向控制測試以 runner 既有的注入點 `monkeypatch.setattr(runner, "git_status_porcelain", lambda: "")` stub 成 clean。理由：fake subprocess shim 無 `subprocess.run`，且該測試驗收的是 acceptance 語意（上傳/文件/metrics gates），不應受「測試當下 worktree 是否 dirty」的環境事實干擾。clean-worktree gate 本身另有專屬測試與 WAVE-02 `runner-preflight-dirty.txt` 實測（dirty 時 fail closed、backend 未啟動）覆蓋。屬合理測試設計，非對產品行為的放寬。

## 證據索引（`.agent/tasks/T20260827-1127-01-lmstudio-e2e-empty-summary/evidence/`）

- `rev3-wave01/`：`runner-fail-first-red.txt`（20 failed, 3 passed）、`launcher-fail-first-red.txt`（8 failed, 4 passed）
- `rev3-wave02/`：`tests-green.txt`（33 passed）、`runner-help.txt`、`runner-dry-run.txt`、`runner-preflight-dirty.txt`（dirty → fail closed）、`runner-smoke.txt`（PASS + child gone + LM Studio 觀察）
- `rev3-wave03a/`：`launcher-contract-green.txt`（bash -n OK + 12 passed）、`launcher-functional-smokes.txt`
- `rev3-wave03b/`（本階段）：`regression.txt`、`focused-suites.txt`、`full-suite.txt`、`runner-help-dryrun.txt`、`runner-smoke.txt`（含 child-gone 與 LM Studio 觀察）、`final-diff-stat.txt`

## 殘餘風險

- **Primary outcome 尚未證明**：current HEAD 對 exact latest audio 是否能產出非 fallback 正式會議紀錄，仍屬 `UNKNOWN-01/H-2`；只有 Stage 05 Browser true E2E 可裁決。
- Runner 的 Browser mode（`BROWSER_E2E_READY` → 開頁上傳 → bounded log poll）路徑尚未以真實 Browser 執行過；若 Stage 05 發現 verifier/harness 缺陷，依 plan `DEGRADATION_AND_GATE_TESTS` 修 verifier 並建立新 append-only attempt，不得誤報為 product defect。
- 完整套件的 skip 數隨環境（gitignored `tests/test_audio/`）在 2/3 間變異；本輪觀察為 2 skipped，均已歸類為環境性。
- Stage 05 執行時須重驗 mutable facts（9527 listener ownership、LM Studio inventory/context、worktree clean、exact audio SHA `5ffba744…6683d0`）。

## 結語

**READY_FOR_STAGE_05，尚未證明 primary outcome。** Browser true E2E 與 9527 rollout 由 Stage 05 fresh verifier 依 plan `CM-04`/`CM-05` 執行；本階段不宣稱使用者 primary outcome 已修復，亦不寫 `result.md`。