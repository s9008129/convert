# CHECK-14 基線報告（T20260912-2242-01）

- 角色：Stage-04 CHECK-14 基線建立者
- 對象：Apple SpeechAnalyzer ASR 任務改動前的基線（未含本任務任何變更）
- HEAD（主 repo `main` = worktree）：`1bd54fb0c953dff75321a063216bb79686b33dd4`
- Worktree：`/tmp/convert-baseline-1789224406`（detached HEAD、工作區乾淨；跑完已 `worktree remove --force`）
- 執行時間：2026-09-12（Asia/Taipei），全程只在 worktree 內執行，避免受主 repo 平行編輯影響

## 環境

| 項目 | 值 |
|---|---|
| Python | 3.12.12（uv 管理之 `cpython-3.12.12-macos-aarch64-none`） |
| pytest | 9.1.1（pytest-asyncio 1.4.0，`asyncio_mode=auto`） |
| 平台 | macOS 26.6.2（Darwin, arm64） |
| 解譯器 | 主 repo venv `/Users/hsiaojohnny/dev/convert/.venv/bin/python`（site-packages 無 editable/.pth 指向主 repo；測試由 worktree 根目錄匯入 repo 內 `backend` 模組，無交叉污染） |

## 執行指令與耗時

1. 完整基線：
   `cd <worktree> && /Users/hsiaojohnny/dev/convert/.venv/bin/python -m pytest tests/ -q -p no:cacheprovider`
   - 收集：553 tests in 2.24s
   - pytest 內部耗時 4.72s；實際 wall（含直譯器啟動與 tee）約 6 秒
   - Exit code：0
2. 聚焦基線（同指令再加 `-k "dispatcher or transcription or platform or apple"`）
   - pytest 內部耗時 2.00s；實際 wall 約 3 秒
   - Exit code：0

## 結果統計

- 完整：**pass 550 / fail 0 / skip 3**（3 warnings）
- 聚焦：**pass 20 / fail 0 / skip 3 / deselected 530**（命中 23 個、2 warnings）
- 備註：「dispatcher / apple / platform」關鍵字在基線無專屬測試命中（命中的 23 個皆為 transcription 系列）；apple 相關測試屬本任務後續新增。

## 失敗測試清單

無失敗測試（0 failed）。

### Skipped（3 筆，均非失敗；供日後比對）

分類：**environment blocker**（設計上 opt-in 或測試資料檔缺席，非 regression）

1. `tests/test_mlx_direct.py::test_mlx_whisper_direct_transcription`
   - 原因：`live MLX model test is opt-in; use the offline adapter test for normal CI`（需實體 MLX 模型的 opt-in 測試）
2. `tests/test_whisper_fix.py::test_transcription[test1_5sec.wav-測試 1 - 5秒音訊]`
   - 原因：`測試音檔不存在: <worktree>/tests/test_audio/test1_5sec.wav`（`tests/test_audio/` 受 `.gitignore:113` 忽略，主 repo 與乾淨 worktree 皆無此檔）
3. `tests/test_whisper_fix.py::test_transcription[test2_3sec.wav-測試 2 - 3秒音訊]`
   - 原因：同上（`test2_3sec.wav` 不存在）

skip 明細取自相同 HEAD 之輔助執行（同指令加 `-rs`）：`550 passed, 3 skipped, 3 warnings in 3.86s`。

## 關鍵 summary 行（日後比對用）

- `553 tests collected in 2.24s`
- `550 passed, 3 skipped, 3 warnings in 4.72s`（PYTEST_EXIT=0）
- `20 passed, 3 skipped, 530 deselected, 2 warnings in 2.00s`（PYTEST_EXIT=0）
- 3 筆 SKIPPED 行（如上方清單）

## 產出檔案

- `pytest-full.txt` — 完整輸出（含結尾 summary）；sha256 `a9bf438714a7356544ea4092b71a6dedce23042182b582f019aa504cf42e1690`
- `pytest-focused.txt` — 聚焦輸出；sha256 `ad74b9caaaea8bce69c266e17b7da0e48b54c2e7c2c89265714cc31bc60bf817`

## 環境問題

- 無阻擋性問題；worktree 執行即為 HEAD `1bd54fb` 之程式碼狀態。
- worktree 為 detached HEAD 的乾淨 checkout，不含被 gitignore 的 `tests/test_audio/`（此即 2 筆 skip 來源；主 repo 亦無此資料夾，故與主 repo 行為一致）。
- 主 repo 由其他 agent 平行編輯中；本次未修改/刪除 repo 任何其他檔案，僅新增 `baseline/` 三檔（未 git add/commit）。
