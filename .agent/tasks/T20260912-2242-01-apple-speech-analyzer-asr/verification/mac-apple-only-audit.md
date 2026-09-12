# Mac Apple-Only 對抗式驗證報告（T20260912-2242-01）

**MAC_APPLE_ONLY: PARTIAL** — 可執行行為面全部通過（無 Mac fallback、legacy 值硬拒絕、非 Mac 不變、無 MLX 相依、test suite 全綠）；殘留 1 個產品碼內的正向 fallback 敘述（docstring）與數個 scope 邊界觀察，見「反例與觀察」。

- 稽核角色：獨立 Verifier（產品碼 read-only；本回合唯一寫入＝本檔；所有一次性腳本置於 `/tmp`）
- 環境：`Darwin arm64`（真 Mac）、branch `main`、工作樹含未提交變更；`git rev-parse HEAD` = `88e136d`
- 方法：靜態追蹤 + 真機 monkeypatch 實測 + 全量 pytest

## 反例與觀察（先列）

| # | 位置 | 類型 | 判定 |
|---|---|---|---|
| C1 | `backend/services/asr_apple/apple_cli.py:449` | 正向 fallback 敘述：`"""建立 ``APPLE_OUTPUT_INVALID`` 錯誤（可參與 auto fallback）。"""`（本任務未修改此檔；與 `git show HEAD:...` 逐字相同） | **(a) 真矛盾（僅註解，無行為影響）→ item 5 FAIL** |
| C2 | `rg --no-ignore -n "should_fallback" backend/ scripts/ tests/` 非空（4 命中，全在 `tests/test_apple_dispatcher.py`，皆為「已刪除且不得加回」的負向斷言／註解） | 字面期望不符，語意無矛盾 | MISMATCH（item 1 字面）/ PASS（語意） |
| C3 | `doc/apple-speech-analyzer-porting-context.md:120,187`（`AUTO_FALLBACK_ORDER = ("apple","breeze","mlx")`、`可參與 auto fallback`） | 文件開頭明示「來源專案 `yt_down_txt`」之移植上下文，§3.2 尾端已加會議專案覆寫（永不 fallback） | (b) 歷史/參考脈絡，但該句缺 inline 上游限定詞（讀者風險，建議補字） |
| C4 | repo 根 `main.py` + `src/whisper_transcriber.py`（legacy CLI，faster-whisper；`main.py` 自述「Windows 版本（也支援 macOS/Linux）」） | backend 服務（本次 scope）之外仍有可於 macOS 執行的 Whisper CLI | scope 邊界觀察（非本次凍結語意 scope；提請 Owner 注意） |
| C5 | `tests/test_mlx_direct.py:12`（`pytest.importorskip("mlx_whisper")`） | 永遠 skip 的死測試模組，保留 MLX 字樣 | 觀察（item 4 的三道指令均通過；此檔僅被跳過） |

---

## Item 1 — Mac 無 fallback 程式路徑：PASS（語意）／MISMATCH（字面）

**指令（要求：必須為空）**

```
$ rg --no-ignore -n "should_fallback" backend/ scripts/ tests/
tests/test_apple_dispatcher.py:12:（``APPLE_ONLY_BACKENDS_ERROR``）。``should_fallback`` 已刪除且不得加回。
tests/test_apple_dispatcher.py:226:# CHECK-03（路由半部）＋SI-03：Mac 無 fallback 選項（should_fallback 已刪除）
tests/test_apple_dispatcher.py:231:    """SI-03：``should_fallback`` 已刪除且不得加回（Mac 已無 Whisper 備援）。"""
tests/test_apple_dispatcher.py:233:    assert not hasattr(dispatcher_module, "should_fallback")
EXIT=0
```

- `backend/`／`scripts/` 零命中；4 命中全在測試檔，且 :233 是**負向斷言**（屬性不得存在）。無任何定義、匯入或呼叫。→ 字面 MISMATCH、語意 PASS。

**靜態追蹤（`backend/services/transcription.py` 行號）**

- `transcribe_detailed`（:575）→ `chain = resolve_engine_chain(...)`（:601，來自 `backend/core/asr_model_resolver`）→ `if chain[0] == "apple":`（:602）→ `_transcribe_with_apple_chain`（:603）else `_transcribe_with_legacy_engine`（:610）。
- `_transcribe_with_apple_chain`（:618）：`del max_retries, force_cpu`；僅呼叫 `_transcribe_with_apple_engine`（:635）；`except AppleSpeechError`（:636）→ `raise self._apple_failure(error)`（:638）。無鏈迭代、無下一引擎分支。
- 呼叫點普查：`_transcribe_with_legacy_engine` 僅 :610（Mac 不可達，見 Item 2/3）與 :747（legacy 內部 CPU 降級遞迴）；`_load_model` 僅 :722（legacy 內）；`_transcribe_with_mlx_whisper` 僅 :731（legacy 內）。`rg -n "_transcribe_with_legacy_engine|_transcribe_with_mlx_whisper|_load_model\(" backend/ --glob '!backend/services/transcription.py'` → 無命中（exit 1）。
- `backend/workers/asr_worker.py:66` 與 `backend/services/asr_subprocess.py:52` 都只呼叫 `transcribe_detailed`（繼承同一鏈語意）。

**動態 falsification（/tmp script；monkeypatch 5 個 legacy 邊界為 `AssertionError("called")`）**

`/tmp/audit_item1_failclosed.py`（`uv run python` 實跑）：

- SCENARIO A（注入 `AppleSpeechError(APPLE_UNAVAILABLE)` 於真 chain）：
  `SCENARIO A RESULT: AppleSpeechError code='APPLE_UNAVAILABLE' user_message='Apple 引擎失敗（未 fallback）：helper 缺失（audit 注入）'`
  `SCENARIO A legacy/whisper invocations: []`
- SCENARIO B（真 provider、真 helper 缺席路徑，`APPLE_SPEECH_CLI_PATH=/nonexistent/...`）：
  `SCENARIO B RESULT: AppleSpeechError code='APPLE_INPUT_ERROR' user_message="Apple 引擎失敗（未 fallback）：… AVAudioFile cannot read 'audit.wav' …"`
  `SCENARIO B legacy/whisper invocations: []`
- 追加 adversarial（`/tmp/audit_extra.py`）：
  - `settings.ASR_BACKEND="mlx_whisper"` 走真 `transcribe_detailed` → `ValueError: ASR_BACKEND=mlx_whisper 在 macOS 已不支援：Mac 僅提供 Apple SpeechAnalyzer（auto 或 apple）`；invocations `[]`
  - 手工偽造鏈 `("apple","mlx_whisper")` 直呼 `_transcribe_with_apple_chain` → `AppleSpeechError(APPLE_UNAVAILABLE, 'Apple 引擎失敗（未 fallback）：…')`；invocations `[]`（證明即使鏈中含 mlx 也不會被執行）
  - `ASR_BACKEND=" Apple "` → Apple 鏈、fail-closed；invocations `[]`

## Item 2 — Mac 拒絕所有 legacy backend：PASS

實跑（真 Mac，`/tmp/audit_item23_matrix.py`）：7 變體 × {`asr_model_resolver.resolve_engine_chain`、`platform_config.resolve_platform_asr_backend`、`dispatcher.resolve_engine_chain(is_apple_platform=True)`} 全部 `ValueError`，訊息皆等於 `APPLE_ONLY_BACKENDS_ERROR.format(backend=<normalized>)`（原始輸出逐項 `RAISED ValueError <label> <variant> -> '<message>' | matches APPLE_ONLY_BACKENDS_ERROR: True`）。下表為同一批觀測之逐變體訊息（僅 `<normalized>` 不同，非重新排版之原始格式）：

```
transformers      → ValueError: ASR_BACKEND=transformers 在 macOS 已不支援：Mac 僅提供 Apple SpeechAnalyzer（auto 或 apple）
faster_whisper    → ValueError: ASR_BACKEND=faster_whisper 在 macOS 已不支援：Mac 僅提供 Apple SpeechAnalyzer（auto 或 apple）
mlx_whisper       → ValueError: ASR_BACKEND=mlx_whisper 在 macOS 已不支援：Mac 僅提供 Apple SpeechAnalyzer（auto 或 apple）
MLX-Whisper       → ValueError: ASR_BACKEND=mlx_whisper 在 macOS 已不支援：Mac 僅提供 Apple SpeechAnalyzer（auto 或 apple）
 mlx_whisper      → ValueError: ASR_BACKEND=mlx_whisper 在 macOS 已不支援：Mac 僅提供 Apple SpeechAnalyzer（auto 或 apple）
TRANSFORMERS      → ValueError: ASR_BACKEND=transformers 在 macOS 已不支援：Mac 僅提供 Apple SpeechAnalyzer（auto 或 apple）
faster-whisper    → ValueError: ASR_BACKEND=faster_whisper 在 macOS 已不支援：Mac 僅提供 Apple SpeechAnalyzer（auto 或 apple）
APPLE_ONLY_BACKENDS_ERROR literal: 'ASR_BACKEND={backend} 在 macOS 已不支援：Mac 僅提供 Apple SpeechAnalyzer（auto 或 apple）'
```

## Item 3 — 非 Mac 行為不變：PASS

Monkeypatch 後 `pc.is_darwin_arm64 = amr.is_darwin_arm64 = lambda: False`（re-check 印出 `False False`），完整矩陣（節錄實際輸出）：

```
requested='auto'            resolve_engine_chain(model='') -> ('transformers',)          platform_config -> 'auto'
requested='transformers'    -> ('transformers',)                                          -> 'transformers'
requested='faster_whisper'  -> ('faster_whisper',)                                        -> 'faster_whisper'
requested='mlx_whisper'     -> ('mlx_whisper',)                                           -> 'mlx_whisper'
requested='apple'           -> ValueError: ASR_BACKEND=apple 僅 macOS 支援（Apple Silicon、macOS 26+）   -> 同訊息 ValueError
requested='MLX-Whisper'     -> ('mlx_whisper',)                                           -> 'mlx_whisper'
requested=' mlx_whisper '   -> ('mlx_whisper',)                                           -> 'mlx_whisper'
requested='TRANSFORMERS'    -> ('transformers',)                                          -> 'transformers'
requested='faster-whisper'  -> ('faster_whisper',)                                        -> 'faster_whisper'
requested='whisperx'/'bogus'-> ValueError（既有 fail-fast 訊息，未變）
auto default_backend check: infer_asr_backend('', 'auto') = 'transformers'
resolve_engine_chain('auto', BREEZE) = ('transformers',) == (infer_asr_backend(BREEZE,'auto'),)
```

- `auto → (infer_asr_backend(...),)`：成立（'' 與 Breeze 模型兩組）。
- 顯式 legacy → passthrough（含大小寫／空白／`-` 變體，normalized 後原樣）。
- `apple` → 兩函式皆 `ValueError`（router 層 `is_apple_platform=False` 回 `("apple",)` 屬凍結語意，由 `resolve_platform_asr_backend` 拒絕）。
- `resolve_asr_model("MediaTek-Research/Breeze-ASR-26","auto")`：非 Mac（patch 後）＝ `'MediaTek-Research/Breeze-ASR-26'`（非空字串、非 MLX id）；真 Mac ＝ `''`。

## Item 4 — 無 Whisper 相依：PASS

```
$ rg -n "mlx" pyproject.toml requirements.txt uv.lock
(無輸出) ; rg_exit=1
$ ls .venv/lib/python3.12/site-packages | grep -i mlx
(無輸出) ; ls_grep_exit=1
$ uv run python -c "import mlx_whisper"
Traceback (most recent call last):
  File "<string>", line 1, in <module>
ModuleNotFoundError: No module named 'mlx_whisper'
import_exit=1
```

輔助佐證：`git diff HEAD -- pyproject.toml` 移除 `"mlx-whisper==0.4.3 ; platform_system == \"Darwin\" ..."`；`requirements.txt` 同步移除該行；`requirements.windows-cuda.txt`／`requirements-correction.txt` 無 mlx（rg exit 1）。`tests/test_mlx_direct.py` 因 `importorskip` 被 skip（屬 C5 觀察，非相依殘留）。

## Item 5 — 文檔/程式碼一致性：FAIL（1 個 (a) 命中）

指定 sweep（原樣執行）：

```
$ rg --no-ignore -n -g '*.md' -g '*.py' -g '*.yaml' -g '*.yml' -g '*.example' "回退.{0,6}(MLX|Whisper|mlx)|fallback.{0,20}mlx|改用 mlx|備援引擎.{0,6}mlx" -- . | grep -v '\.agent/'
./.env.example:58: # ASR_BACKEND=auto 或 apple；Apple 失敗一律 fail-closed（直接失敗，不回退 Whisper）。
./doc/apple-speech-analyzer-operations.md:170: 症狀：`auto` 與 `apple` 皆直接失敗（fail-closed；任務 failed，不會回退 MLX/Whisper）。
./tests/test_apple_helper_absent_e2e.py:232: # REAL-ABSENT-02：Mac auto ＋ 真 helper 缺席 → fail-closed（不再 fallback mlx）
./backend/services/task_processor.py:42: 文案屬觀測/UX 層（非 gating）：解析失敗一律回退既有 Whisper 文案，
./backend/services/task_processor.py:48: log.debug(f"ASR 引擎鏈解析失敗（進度文案回退 Whisper 文案）: ...")
./install_deps.py:57: " 未建置時 Apple 路徑直接失敗（fail-closed，不會回退 Whisper）；",
./tests/test_apple_packaging_guard.py:145: # 沒有 Whisper 選項也沒有 fallback，因此 mlx-whisper／mlx 不得再是本專案的
./scripts/verify_env.py:186: "helper 缺失時直接失敗、不會回退 Whisper）。建置指令："
./README.md:138: > 回退舊 Whisper 行為須回退版本（Mac 已無 `ASR_BACKEND` 環境變數回滾開關）。
```

分類：

| 命中 | 分類 |
|---|---|
| `.env.example:58`、`operations.md:170`、`test_apple_helper_absent_e2e.py:232`、`install_deps.py:57`、`test_apple_packaging_guard.py:145`、`verify_env.py:186`、`README.md:138` | (c) 否定句／「不得再有」守衛／回退版本說明 |
| `task_processor.py:42,48` | (d) 非 macOS／非引擎：解析失敗時的**進度文案**回退，且明示非 gating |

擴大 sweep（`apple.{0,40}(fallback|回退|備援)|(fallback|回退|備援).{0,40}apple|...`）另發現：

- **(a) `backend/services/asr_apple/apple_cli.py:449`**：`"""建立 ``APPLE_OUTPUT_INVALID`` 錯誤（可參與 auto fallback）。"""` — 正向聲稱 Apple 錯誤可參與 auto fallback；與凍結語意（任何 `AppleSpeechError` 含 `APPLE_OUTPUT_INVALID` 一律 fail-closed 上拋）矛盾。`git diff --stat HEAD -- backend/services/asr_apple/apple_cli.py` 為空、`git show HEAD:...` 亦含同句 → 本任務未清理。行為影響：僅註解。
- (b) `doc/apple-speech-analyzer-porting-context.md:120`（`AUTO_FALLBACK_ORDER`）、`:187`（`可參與 auto fallback`）：皆位於「來源專案 `yt_down_txt`」參考碼段；同檔 §3.2 尾端、§5、§6 已載明會議專案「單一 `("apple",)`、永不 fallback」。判定 (b)（歷史/參考），惟 :187 缺 inline 上游限定詞，列 C3 讀者風險。
- (d) `apple_cli.py:957`（metadata 向後相容 fallback）、`frontend/js/app.js:186`（`mlx-metal` accelerator 狀態標籤；Mac 已改 `apple-neural`，屬 UI 顯示分支非 ASR 選項）。

## Item 6 — 測試證據：PASS

```
$ uv run pytest tests/ -q
730 passed, 3 skipped, 3 warnings in 8.67s
```

- 0 failed；baseline 為 726 passed / 3 skipped（本輪 +4 passed）。
- skips（`-rs`）：`test_mlx_direct.py:12`（mlx_whisper 不存在）、`test_whisper_fix.py:38` ×2（測試音檔不存在）。
- 聚焦實跑（15 passed）：

```
$ uv run pytest tests/test_apple_dispatcher.py::test_mac_auto_engine_chain_is_single_apple \
  tests/test_apple_dispatcher.py::test_mac_explicit_legacy_backends_are_rejected \
  tests/test_apple_chain_integration.py::test_explicit_apple_failure_never_falls_back \
  tests/test_apple_chain_integration.py::test_auto_apple_failure_fails_closed_without_mlx \
  tests/test_apple_helper_absent_e2e.py::test_auto_mac_real_helper_absence_fails_closed \
  tests/test_apple_helper_absent_e2e.py::test_explicit_apple_real_helper_absence_fails_closed \
  tests/test_apple_dispatcher.py::test_non_mac_explicit_backends_unchanged \
  tests/test_apple_dispatcher.py::test_non_mac_auto_never_resolves_to_apple \
  tests/test_apple_dispatcher.py::test_dispatcher_non_mac_regression_guards -q
15 passed, 2 warnings in 0.37s
```

四項契約對應測試函式（全數存在且通過）：

1. **Mac auto 鏈長 1**：`tests/test_apple_dispatcher.py::test_mac_auto_engine_chain_is_single_apple`（:84；`chain == ("apple",)`、`len(chain)==1`、`"mlx_whisper" not in chain`；另 `test_mac_auto_resolves_to_apple`）。
2. **Mac legacy 拒絕**：`tests/test_apple_dispatcher.py::test_mac_explicit_legacy_backends_are_rejected`（:109；8 變體 × resolver/dispatcher，逐字比對 `APPLE_ONLY_BACKENDS_ERROR`）。
3. **fail-closed 且 legacy 引擎呼叫次數 0**：`tests/test_apple_chain_integration.py::test_explicit_apple_failure_never_falls_back`（:223）、`::test_auto_apple_failure_fails_closed_without_mlx`（:258，參數 4/6/1）、`::test_auto_cancelled_apple_never_falls_back`（:289）；`tests/test_apple_helper_absent_e2e.py::test_explicit_apple_real_helper_absence_fails_closed`（:195）、`::test_auto_mac_real_helper_absence_fails_closed`（:236）。皆斷言 `legacy_calls == []`／`mlx_calls == []`（含 `_load_model` 未被呼叫）。
4. **非 Mac passthrough**：`tests/test_apple_dispatcher.py::test_non_mac_explicit_backends_unchanged`（:189）、`::test_dispatcher_non_mac_regression_guards`（:197）、`::test_non_mac_auto_never_resolves_to_apple`（:160）、`::test_non_mac_model_resolution_is_unchanged`（:138）。

## 結論

- 可執行語意：**VERIFIED**（Item 1 動態、Item 2、Item 3、Item 4、Item 6 全數通過；無 Mac fallback、無 legacy 可達路徑、無 MLX 相依）。
- 文件/註解一致性：**1 個 (a) 命中**（C1 `apple_cli.py:449` docstring，未修改檔）→ 整體判 `PARTIAL`，建議刪除/改寫該句後可升為 VERIFIED。
- 建議同時處理（非阻斷）：C3 porting doc 的 inline 上游限定詞、C5 死測試檔、C4 legacy CLI scope 是否納入 Owner 的「Mac 版本」定義。
