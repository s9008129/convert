# escalation.md — T20260912-2242-01（Owner 指示的凍結語意變更）

- 提出者：Stage-04 Implementer
- 日期：2026-09-13
- 狀態：**OWNER_DIRECTED / RESOLVED**（使用者即 Owner，於同一工作階段內以明示指令授權變更）

## 1. 觸發原因（為何這不是 bounded fix）

`handoff.md` 的 SI-02 凍結語意原為：

| requested | is_apple_platform | 凍結鏈 |
|---|---|---|
| `auto` | True | `("apple", "mlx_whisper")`（Apple 失敗時 fallback 一次） |
| `apple` | True | `("apple",)`（fail-closed） |

Owner 於 2026-09-13 明示：

> 本專案 mac 版本已經沒有 Whisper 模型這一個選項，也沒有 Fallback 的選項，
> 只能有唯一 Apple 內建的 Apple SpeechAnalyzer 這一個模型。
> 所以相關程式碼片段還有相關文件都要進行修改並且確認。

依全域 harness 規則（§3「Semantic changes are planning changes」、§10「Any change to
semantic … fallback … meaning triggers `escalation.md` and a replan loop」），
此變更改動 **fallback 邊界**（SI-02）與 **Mac 顯式 legacy 值的可接受性**
（新的硬性拒絕），不得視為 bounded fix 直接提交。

## 2. 裁決（Authority）

- 使用者即 Owner，且於當前回合以明示指令提出，**優先於** Stage-03 handoff 的凍結語意
  （全域 harness §2 衝突優先序：explicit current user instruction > handoff artifact）。
- Owner 已 waive 獨立審查（`PLAN_REVIEW_REQUIRED: NO`），故不重跑 Stage 02；
  改以 escalation 記錄 + 真機 E2E 證據 + 全量測試作為語意變更的守門證據。
- 未變更的紅線：SI-03（取消永不換手）、SI-04/05（錯誤碼與 schema）、SI-06（逾時）、
  SI-07（Windows 零 Apple）、SI-08（暫存衛生）、SI-09（Mac 無本機模型載入）、
  SI-10（`transcribe_isolated` tuple 介面）、SI-11（錯誤字串／類型穩定性）、
  SI-12（gating）。

## 3. 變更後的正式語意（取代 SI-02 原表）

| requested | is_apple_platform | 新語意 |
|---|---|---|
| `auto` | True | `("apple",)` — **單一引擎、永不 fallback** |
| `apple` | True | `("apple",)` — fail-closed |
| `transformers` / `faster_whisper` / `mlx_whisper` | True | `ValueError`（穩定訊息，硬性拒絕） |
| `auto` | False | `(default_backend,)` — 與改動前完全一致 |
| 其他顯式值 | False | `(normalized,)` — 與改動前完全一致 |
| `apple` | False | `resolve_platform_asr_backend` 仍硬性拒絕 |

配套語意變更：

1. `backend/services/asr_apple/dispatcher.py` 的 `should_fallback()` **刪除**
   （不再有任何「錯誤碼 → 可 fallback」的分類）。
2. `APPLE_AUTO_FALLBACK` 常數保留但長度為 1：`("apple",)`。
3. `backend/core/platform_config.py` 新增 `APPLE_PLATFORM_ASR_BACKENDS = {"auto","apple"}`；
   Mac 上顯式 legacy backend 一律 `ValueError`（與非 Mac 拒絕 `apple` 對稱）。
4. `TranscriptionService._transcribe_with_apple_chain()` 不再有 fallback 分支；
   任何 `AppleSpeechError` 都 `raise self._apple_failure(error)`（訊息含「未 fallback」）。
5. `get_platform_defaults()` 的 Mac accelerator：`mlx-metal` → `apple-neural`。
6. `resolve_asr_model()` 在 Mac + `auto` + 預設 Breeze 模型時回 **空字串**
   （＝本機沒有 Whisper 模型），不再映射到 `doggy8088/Breeze-ASR-26-MLX`。

## 4. 影響與風險

- **正向**：Mac 執行路徑不再需要任何 Whisper 依賴／權重；失敗一律 fail-loud，
  不會再出現「Apple 壞掉卻靜默改用較差模型」的品質事故。
- **風險 1（fail-loud 啟動）**：舊 `.env` 若殘留 `ASR_BACKEND=mlx_whisper`，
  服務會在 startup 直接失敗（`ValueError`），而非靜默降級。這是刻意的 fail-loud；
  已於文件中明示修復方式（改回 `auto` 或 `apple`）。
- **風險 2（覆蓋率）**：刪除 `should_fallback` 使「錯誤碼 → 換手」的分類覆蓋消失；
  已以「Mac × 三種 legacy backend → ValueError」「Mac auto 鏈長 1」
  「Apple 失敗時 legacy 引擎呼叫次數為 0」等新案例補回更強的 fail-closed 覆蓋。
- **風險 3（相依）**：`pyproject.toml` 的 `mlx-whisper ; Darwin/arm64` 平台依賴
  在 Mac 已無消費端（見 §5）。

## 5. 後續追蹤（不阻斷本次變更）

- `pyproject.toml`／`requirements.txt` 的 `mlx-whisper==0.4.3 ; Darwin/arm64`
  已無 Mac 消費端，**本回合已實際移除**（`uv lock` 收斂 172 行刪除、0 行新增；
  一併移除 `mlx`／`mlx-metal`／`llvmpipe`／`numba`／`scipy`／`tiktoken` 等傳遞相依）。
  `tests/test_apple_packaging_guard.py` 的守衛契約同步反轉為「不得再有 MLX 相依」，
  `scripts/verify_env.py` 在 Apple 路徑不再列出 MLX supporting 模組。
  Windows/Linux 相依本來就不含 MLX 平台套件 → 不受影響（仍待真機矩陣複驗）。
- 若 Owner 之後要「連 `apple_speech_cli/` 也不進版控」等更嚴格的封裝邊界，另開任務。
