# Windows／非 Mac 零 Apple 矩陣複驗（rev2）— 獨立對抗式驗證報告

- TASK_ID：T20260912-2242-01-apple-speech-analyzer-asr
- 角色：獨立驗證者（Stage 04 委派之獨立驗證；唯讀產品碼；**本報告為唯一寫入檔**）
- 驗證時間：2026-09-13 00:38–00:48（Asia/Taipei）
- 受審修訂：HEAD `88e136dce4a3e6e2ff1c69d504dc01483e05b334`（`88e136d`）＋未提交工作樹
  （Mac「僅 Apple SpeechAnalyzer」語意變更 ＋ `mlx-whisper` 平台相依及其 MLX/numba/scipy/tiktoken 傳遞鏈移除）
- 對照基準：**pre-change 樹**＝`git archive HEAD` → `/tmp/win-audit-rev2/pre-change`
  （已驗證該樹 `APPLE_AUTO_FALLBACK == ("apple", "mlx_whisper")` 且 `should_fallback` 仍存在＝本次語意變更前的狀態）
- 方法說明：原前次稽核臨時檔 `/tmp/win-audit/`（含 `audit5_reverse.json` 等）於本次驗證期間被系統清理，
  故不依賴舊 JSON，改以 **同一套腳本對 pre-change 樹重跑並逐呼叫比對**（更可重現；平台／變體／函式清單與前次完全相同）。
- 本報告為新增檔；未編輯既有 `verification/windows-matrix-audit.md`（append-only 歷史）；未 `git add`／`git commit`；未動產品碼、測試與 `data/cache/**`。

## 0. 判定總表

| # | 驗證項 | 判定 | 備註 |
|---|---|---|---|
| 1 | 相依移除後 Windows/Linux 零 Apple 仍成立（檔案掃描＋`uv pip compile` 真實解析） | **PASS** | Windows/Linux 解析輸出與 pre-change **逐字節相同**；零 mlx/apple 命中 |
| 2 | 非 Mac legacy 引擎解析完全不變（前次 8 平台 × 9 變體 × 3 函式矩陣＋legacy/auto 區塊） | **PASS** | 非 Mac 8 平台與 pre-change **逐呼叫相同**；apple 216/216 拒絕、單一訊息 |
| 3 | 相依移除僅限 Darwin/arm64，非 Mac 不可受影響 | **PASS** | 9 個移除 package 全部 darwin-gated；新 lock 零殘留；`uv lock --check` exit 0 |
| 4 | 非 Mac 執行期零 Apple 洩漏（provider 不載入；contract/dispatcher 純淨） | **PASS（含字面偏離 F1′）** | provider（`apple.py`／`apple_cli.py`）全程 0 載入；2 個純模組（package、contract）因既有頂層 import 被載入 |
| 5 | 前端：Windows/Linux 渲染字串不變、mlx-metal 分支保留、Windows 不可能出現 Apple ASR 字串 | **PASS（觀察 F4 續存）** | `app.js` 自前次稽核以來未變（sha256 相同）；windows cuda/cpu 渲染與前次一致 |

**WINDOWS_ZERO_APPLE_REV2: PASS**

未發現任何「移除 MLX 相依後 Windows/Linux 可解析到 Apple/MLX 套件」或「非 Mac 執行期載入 Apple provider／重型引擎」的漏洞。未能驗證項見 §8。

---

## 1. 受審修訂指紋（sha256，量測於 00:47）

| 檔案 | sha256 | 窗內穩定 |
|---|---|---|
| `backend/core/platform_config.py` | `145ef922afccf266e8b87749ee898dd4fafe440a9f5f9000b1c2120850c7f3c9` | ✔（00:38＝00:47） |
| `backend/core/asr_model_resolver.py` | `c49e23b0c804d35cbf199a1a7569b64260f3a7dd56177dc1a0a835ce526f3886` | ✔ |
| `backend/api/routes.py` | `e475f1d9342d1d644af8b80f8915a8eb540006bafdc23c50fef1c775ce3edfed` | ✔ |
| `backend/services/transcription.py` | `8cc1dc247e5b9c0e643382464383240d51430d14dbd7ea794ea083ec2b7749a9` | ✔ |
| `backend/services/asr_apple/contract.py` | `2021ddb04a43c98b4a823caaebc6a290f2cf85c3a4d786d99213fb7e626beb01` | ✔ |
| `backend/services/asr_apple/dispatcher.py` | `ec46613ef8d62534a068dc8d1d0bd1d40f5de8a8eb0cdbca28aab7aeaf8e207b` | ✔ |
| `backend/services/asr_apple/apple.py` | `3e2d42654e56a0e70f9b7e0fb647a7e45a6687228e3a36fa639350244c8e6165` | ✔ |
| `backend/services/asr_apple/apple_cli.py` | `10a3f8d68f2a42b35576698167e6e1fdb62b4be9974b5f0a15c82da6bde38078` | ✖ 窗內漂移（見下） |
| `pyproject.toml` | `3a957cf7e2baa9e3a5642f551f7b729f99fe871dd7474de8a1c09e46245e2129` | ✔ |
| `requirements.txt` | `45cfa5887c9d35f9fba3962cbc7839dd3ca57b9de360fa4e944a348d4585c0a5` | ✔ |
| `uv.lock` | `fadc199b6c1fc8c0b2b2eaed854dd36b327c5bc6b56c9518b6a986002da88f8f` | ✔（`uv lock --check` 後重量亦同） |
| `frontend/js/app.js` | `ea4f3a5121d05806dcea189b0adb3ee8b1d798d594facabe46d5f0824d440915` | ✔（且與前次稽核量測值相同） |
| `install_deps.py` | `16ae1aebb1ff6a30fa3e85103c47fe7f3f99ab0c04b5f45b349c907039bccc1f` | ✔ |
| `scripts/verify_env.py` | `08c6b87927e7c140b2ada16f248a97eeb0f6368d0d116d8e0dda6d8d6dc328a5` | ✔ |
| `docker/Dockerfile` | `467ff2de0ad21bb0155a2cfb27c26352cfed67b6bdfefd6f5482e40be8769f82` | — |

- **窗內樹漂移（非本報告所為）**：
  1. `backend/services/asr_apple/apple_cli.py` 由 `c15b3ae…` → `10a3f8d…`；實際 diff 僅一行 docstring（`APPLE_OUTPUT_INVALID` 描述由「可參與 auto fallback」改為「Mac 已無 fallback：一律 fail-closed」），無功能變更。該檔在生產碼中只被 provider `apple.py`（`from . import apple_cli`）載入（其餘為測試檔），而 provider 在非 Mac 全程未載入（§5），故不影響本報告任何非 Mac 判定。
  2. 其他 agent 於本窗把 `tests/test_mlx_direct.py` 加入 index 刪除（`git status` 顯示 `D `）並更新 `.agent/.../execution.md`；本驗證者未執行任何 `git add`。
- 若上述載入判定之檔案在報告後再變更，本報告須重跑（腳本見 §9）。

---

## 2. 驗證項 1：依賴移除後 Windows/Linux 零 Apple（PASS）

### 2.1 檔案對抗式掃描（實際命令＋實際輸出）

```bash
cd /Users/hsiaojohnny/dev/convert
grep -rniE "apple|swift|xcode" docker/ pyproject.toml requirements.txt requirements-correction.txt requirements.windows-cuda.txt
# →（無輸出，exit 1）
grep -rniE "mlx" docker/ pyproject.toml requirements.txt requirements-correction.txt requirements.windows-cuda.txt
# →（無輸出，exit 1）
uv --version
# → uv 0.9.24 (Homebrew 2026-01-09)
```

`install_deps.py --check`（同前次方法，`main(["--check"], system)` 實跑）實際輸出摘要：

| 平台 | exit | needle hits | 備註 |
|---|---|---|---|
| Windows | 0 | `[]` | 零 Apple/Swift/Xcode 字樣 |
| Linux | 0 | `[]` | 同上 |
| Darwin（對照組） | 0 | `.build, apple, apple-speech-cli, speechanalyzer, swift, xcode` | 守衛未過度攔截（Mac 提示照常） |

同次掃描另得：`pyproject_apple_deps=[]`、`pyproject_mlx_dep=[]`、`docker_hits={}`、`requirements_hits={}`、
`uv_lock_mentions={"apple":0,"swift":0,"xcode":0,"mlx-whisper":0}`（`/tmp/win-audit-rev2/logs/audit2_rev2.json`）。

### 2.2 真實 `uv` 解析（與前次相同 args）

```bash
uv pip compile pyproject.toml --python-platform windows --python-version 3.12 --no-header -o /tmp/win-audit-rev2/logs/uv_compile_windows_rev2.txt
# → Resolved 64 packages in 696ms
uv pip compile pyproject.toml --python-platform linux   --python-version 3.12 --no-header -o /tmp/win-audit-rev2/logs/uv_compile_linux_rev2.txt
# → Resolved 63 packages in 311ms
uv pip compile pyproject.toml --python-platform aarch64-apple-darwin --python-version 3.12 --no-header -o /tmp/win-audit-rev2/logs/uv_compile_mac_arm64_rev2.txt
# → Resolved 65 packages in 8ms
for f in windows linux mac_arm64; do grep -ciE "mlx|numba|tiktoken|scipy|llvmlite|more-itertools|apple" /tmp/win-audit-rev2/logs/uv_compile_${f}_rev2.txt; done
# → 0 / 0 / 0
```

**與 pre-change 樹逐字節比對**（pre-change 樹同一命令產出 `uv_compile_*_pre.txt`）：

```bash
diff /tmp/win-audit-rev2/logs/uv_compile_windows_pre.txt  /tmp/win-audit-rev2/logs/uv_compile_windows_rev2.txt   # → IDENTICAL
diff /tmp/win-audit-rev2/logs/uv_compile_linux_pre.txt    /tmp/win-audit-rev2/logs/uv_compile_linux_rev2.txt     # → IDENTICAL
diff /tmp/win-audit-rev2/logs/uv_compile_mac_arm64_pre.txt /tmp/win-audit-rev2/logs/uv_compile_mac_arm64_rev2.txt # → 僅 MLX 鏈移除（27 個 <／> 行）
```

**判定：PASS。** Windows/Linux 解析結果與相依移除前完全相同且零 mlx/apple；mac-arm64 對照組僅少了 MLX 鏈（證明移除確實生效、非無效變更）。

---

## 3. 驗證項 2：非 Mac legacy 引擎解析完全不變（PASS）

### 3.1 方法（與前次稽核相同的矩陣 ＋ 逐呼叫 pre-change 比對）

```bash
# 1) 從 HEAD 取出 pre-change 樹（本次變更前的檔案版本）
git archive HEAD | tar -x -C /tmp/win-audit-rev2/pre-change
# 2) 對「現行樹」與「pre-change 樹」各跑同一支矩陣腳本（平台／變體／函式與前次 audit5_reverse.py 相同）
.venv/bin/python /tmp/win-audit-rev2/matrix_rev2.py /Users/hsiaojohnny/dev/convert > /tmp/win-audit-rev2/logs/matrix_current.json
.venv/bin/python /tmp/win-audit-rev2/matrix_rev2.py /tmp/win-audit-rev2/pre-change        > /tmp/win-audit-rev2/logs/matrix_pre.json
.venv/bin/python /tmp/win-audit-rev2/compare_rev2.py > /tmp/win-audit-rev2/logs/compare_rev2.json
```

矩陣內容：10 個平台列（Windows/AMD64、Windows/ARM64、Linux/x86_64、Linux/aarch64、Darwin/x86_64、
Darwin/arm64、Darwin/ARM64、FreeBSD/amd64、UnknownOS/mystery、空平台）× 9 個 apple 大小寫/空白變體
（`apple, Apple, APPLE, " APPLE ", "apple ", "  Apple  ", ApPlE, "\tAPPLE\n", "apple\t"`）× 3 個入口函式
（`resolve_platform_asr_backend`／`infer_asr_backend`／`resolve_engine_chain`）＋ auto 區塊（4 呼叫）
＋ **legacy 區塊（`auto/transformers/faster_whisper/mlx_whisper` × 3 函式）**；`is_darwin_arm64` 以
`platform.system`／`platform.machine` monkeypatch 控制（其原始碼即以這兩個函式判定，`platform_config.py:23-28`），
非 Mac 列等效 `is_darwin_arm64() == False`。

### 3.2 實際輸出（矩陣計數）

現行樹非 Mac 判定（`/tmp/win-audit-rev2/logs/matrix_current.json`）：

| 平台 | 判定 | 拒絕對數 | distinct message | auto 引擎鏈 |
|---|---|---|---|---|
| Windows/AMD64 | PASS | 27/27 | 1 | `("transformers",)` |
| Windows/ARM64 | PASS | 27/27 | 1 | `("transformers",)` |
| Linux/x86_64 | PASS | 27/27 | 1 | `("transformers",)` |
| Linux/aarch64 | PASS | 27/27 | 1 | `("transformers",)` |
| Darwin/x86_64（Intel Mac） | PASS | 27/27 | 1 | `("transformers",)` |
| FreeBSD/amd64 | PASS | 27/27 | 1 | `("transformers",)` |
| UnknownOS/mystery | PASS | 27/27 | 1 | `("transformers",)` |
| 空平台（`platform.system()==""`） | PASS | 27/27 | 1 | `("transformers",)` |

- **8 平台 × 27 = 216／216 全數拒絕**，全部共用同一訊息：
  `ASR_BACKEND=apple 僅 macOS 支援（Apple Silicon、macOS 26+）`
- auto（含空字串）在全部非 Mac 平台皆為 `("transformers",)`，不含 apple。
- legacy 區塊（非 Mac 96 呼叫）值：`transformers → ("transformers",)`、`faster_whisper → ("faster_whisper",)`、
  `mlx_whisper → ("mlx_whisper",)`、`auto → ("transformers",)`。
- 與 pre-change 樹逐呼叫比對（`compare_rev2.json`）：**8 個非 Mac 平台全部 identical=True**（apple 變體、auto、legacy 三區塊皆同）。
- Mac 列差異僅為本次刻意的語意變更（供對照，非本項範圍）：
  `auto` 鏈 pre `["apple","mlx_whisper"]` → cur `["apple"]`；顯式 `transformers/faster_whisper/mlx_whisper`
  pre 接受 → cur `ValueError("ASR_BACKEND=<x> 在 macOS 已不支援：Mac 僅提供 Apple SpeechAnalyzer（auto 或 apple）")`；
  apple 變體在 Mac 前後皆 fail-closed 不變。
- 環境變數路徑 `get_whisper_backend()`（3 平台 × 9 apple 變體）：三平台（Windows/AMD64、Linux/x86_64、Darwin/arm64）均與 pre-change 相同。
- `scripts/verify_env.py` 非 Mac 3 組合（Windows/AMD64、Linux/x86_64、Darwin/x86_64）前後皆 `None`（零輸出）identical；
  Darwin/arm64 文字有預期變更（前次訊息含「失敗回退 MLX-Whisper」敘述，現行版本已無 fallback 敘述）。

**判定：PASS。** 非 Mac legacy（`transformers`／`faster_whisper`／`mlx_whisper`／`auto`）行為與本次變更前逐呼叫一致；
`apple` 在非 Mac 全部拒絕且訊息穩定；前次稽核所述 `("apple","mlx_whisper")` 之 stale 描述已由本 rev2 取代。

---

## 4. 驗證項 3：相依移除僅限 Darwin/arm64（PASS）

### 4.1 移除的 marker（實際命令）

```bash
git diff uv.lock | head -80        # 節錄（完整輸出：/tmp/win-audit-rev2/logs/uv_lock_diff_head80.txt）
```

實際輸出節錄（皆為刪除行）：

```diff
-    { name = "mlx-whisper", marker = "platform_machine == 'arm64' and sys_platform == 'darwin'" },
-    { name = "mlx-whisper", marker = "platform_machine == 'arm64' and sys_platform == 'darwin'", specifier = "==0.4.3" },
-    { name = "mlx-metal", marker = "sys_platform == 'darwin'" },
-    { name = "numba", marker = "sys_platform == 'darwin'" },
-    { name = "tiktoken", marker = "sys_platform == 'darwin'" },
-    { name = "scipy", version = "1.18.1", ..., marker = "python_full_version >= '3.12' and sys_platform == 'darwin'" },
-    { name = "more-itertools", marker = "sys_platform == 'darwin'" },
```

`git diff --stat`：`pyproject.toml | 1 -`、`requirements.txt | 1 -`、`uv.lock | 172 -----`（172 行內容刪除、**0 行內容新增**）。
`pyproject.toml`／`requirements.txt` 被移除的那一行同為：
`mlx-whisper==0.4.3 ; platform_system == "Darwin" and platform_machine == "arm64"`。

移除的 9 個 `[[package]]` block（名稱／版本）：

| package | version |
|---|---|
| llvmlite | 0.49.0 |
| mlx | 0.32.2 |
| mlx-metal | 0.32.2 |
| mlx-whisper | 0.4.3 |
| more-itertools | 11.1.0 |
| numba | 0.67.0 |
| scipy | 1.17.1 與 1.18.1（兩個 python-full-version 分支） |
| tiktoken | 0.14.0 |

### 4.2 殘留與一致性

```bash
grep -nE '^name = "(mlx|mlx-metal|mlx-whisper|numba|tiktoken|scipy|llvmlite|more-itertools)"' uv.lock   # → 無輸出
grep -ciE 'mlx|numba|tiktoken|llvmlite|more-itertools' uv.lock                                          # → 0 0 0 0 0
uv lock --check      # → Resolved 73 packages in 3ms；exit 0（lock 與 pyproject 一致；未寫入，uv.lock sha256 前後相同）
```

新 lock 中 `faster-whisper`／`ctranslate2`／`torch`／`transformers` 仍各自帶著自己的依賴副本，且無任何一條指向被移除套件：

- `faster-whisper` → `av, ctranslate2, huggingface-hub, onnxruntime, tokenizers, tqdm`
- `ctranslate2` → `numpy, pyyaml, setuptools`
- `torch` → `filelock, fsspec, jinja2, networkx, setuptools, sympy, typing-extensions`
- `transformers` → `filelock, huggingface-hub, numpy, packaging, pyyaml, regex, requests, safetensors, tokenizers, tqdm`

非 Mac 安全性（**已證明，非推定**）：

1. Windows/Linux `uv pip compile` 在移除前後輸出**逐字節相同**（§2.2）——移除對非 Mac 解析零影響。
2. 被移除的 8 個套件在 pre-change 的 Windows/Linux 解析本來就不存在（前後皆 64／63 包且相同）；它們只出現在 pre-change 的 mac-arm64 解析（73 → 65 包）。
3. pre-change mac-arm64 解析中，`tiktoken` 的共享下游僅 `regex`／`requests`（`# via tiktoken, transformers`），移除後由 `transformers` 續用；`numba`／`scipy`／`llvmlite`／`more-itertools` 的唯一上游是 `mlx-whisper`（lock diff 內 `# via mlx-whisper` 可證），`numpy` 由其他套件續用故保留。
4. 新 lock 對上述套件為「零提及」且 `uv lock --check` 通過 → 不存在未解析的殘留相依。

**判定：PASS。** 移除僅作用於 Darwin/arm64 平台鏈；非 Mac 之解析與既有引擎（transformers/faster-whisper/ctranslate2/torch）各自獨立，無共享被刪套件。

---

## 5. 驗證項 4：非 Mac 執行期零 Apple 洩漏（PASS，含字面偏離 F1′）

### 5.1 import 稽核（Windows 模擬子程序；`platform` monkeypatch＋spawn 阻斷）

```bash
.venv/bin/python /tmp/win-audit-rev2/audit4_rootcause_rev2.py
```

實際輸出（`asr_apple` 模組清單；重型引擎全部 `false`，含 torch/transformers/faster_whisper/mlx/numba/scipy/tiktoken/llvmlite/ctranslate2）：

| import 對象 | `backend.services.asr_apple.*` | provider 載入？ |
|---|---|---|
| `backend.core.platform_config` | `[]` | no |
| `backend.core.asr_model_resolver` | `[]` | no |
| `backend.api.routes` | `[asr_apple, asr_apple.contract]`（2 個純模組） | `apple.py`=false、`apple_cli.py`=false |
| `backend.services.transcription` | 同上（2 個） | no |
| `backend.services`、`backend.main` | 同上（2 個） | no |

另外，實際解析引擎鏈時（Windows 模擬 `resolve_engine_chain("auto", …) → ("transformers",)`）會載入第 3 個純模組
`backend.services.asr_apple.dispatcher`（`asr_model_resolver.py:122` 函式內延後 import）；provider 與重型引擎仍全部未載入
（`/tmp/win-audit-rev2/logs/audit4_purity_rev2.json` 的 `chain_resolution`）。

- **F1′（字面偏離，較前次縮小）**：前次稽核時載入 health 路由會出現 3 個純模組（package／contract／dispatcher）；
  現行 `should_fallback` 已刪除、transcription 不再頂層 import dispatcher，故降為 **2 個純模組**（package／contract）。
  「非 Mac 路徑零 `asr_apple.*` 載入」的字面要求仍不成立；provider 層則完全成立（0 載入）。風險判等前次：低（純模組、零第三方依賴、import 期無副作用）。

### 5.2 純淨度（AST＋獨立封裝 import）

- AST（`audit4_purity_rev2.py`）：`contract.py` 僅 import `__future__`／`dataclasses`／`typing`；
  `dispatcher.py` 僅 import `__future__` 與 `.contract`。
- 把 `asr_apple` 封裝複製成獨立套件後直接 import（`audit4_purity2_rev2.py`）：`contract`／`dispatcher` 的 sys.modules 增量
  **無** `device_detector`、`torch`、`transformers`、`faster_whisper`、`mlx`、`numba`、`scipy`、`tiktoken`、`numpy`、`subprocess`、`pathlib`（全部 false）。
- **精確註記（對抗式）**：以一般路徑 `import backend.services.asr_apple.contract` 時，`backend.services.device_detector` 會是
  `true`——這是既有 `backend/services/__init__.py` 的頂層 import 拓樸所致（與 Apple 模組無關），並非 `contract` 自身純淨度問題；
  規格（NFR-03／SI-11）要求的「不拉重型依賴」成立（torch=false）。

### 5.3 全 app ASGI 實打（Windows 模擬、真實 lifespan）

```bash
.venv/bin/python /tmp/win-audit-rev2/audit1_asgi_rev2.py   # 00:47 最終狀態重跑亦同
```

| 檢查 | 實際結果 |
|---|---|
| 端點 | `/api/health?quick=true` 200、`/api/health` 200、`/api/config` 200 |
| 回應掃描（排除凍結 `apple_helper` 區段） | `apple|swift|xcode|speechanalyzer|apple-speech-cli|.build` → **0 hits**（3 端點＋lifespan 啟動日誌） |
| `apple_helper` 凍結欄位 | `{supported:false, available:false, path:null, probe:null, reason:"非 macOS：Apple SpeechAnalyzer 僅支援 macOS"}` |
| lifespan | `booted=true`、health 200、啟動日誌 needle 0 行 |
| loader spy（`routes._load_apple_helper_status` 替換為會回報 supported=true 的 spy） | 呼叫次數 **0**（證明非事後過濾） |
| provider 載入 | `apple.py=false`、`apple_cli.py=false`（import 後與全場結束皆同） |
| 子程序 spawn | 僅 `nvidia-smi --query-gpu=...` ×2（既有 Windows CUDA 偵測）；apple/helper 相關 spawn = 0 |
| device/config 觀測 | `accelerator=cpu`、`current_device=cpu`、`mps_available=false`、`asr_backend=transformers`；config `effective_asr_backend=transformers`、無任何 `apple*` key |

### 5.4 非 Mac 不可達 provider 之證明

- 生產 import 僅 4 處：`routes.py:58`（`_load_apple_helper_status` 內，僅 Darwin 分支呼叫）、`transcription.py:32`
  （頂層 contract，即 F1′）、`transcription.py:664`（`_transcribe_with_apple_engine` 內，只有 `chain[0]=="apple"` 才可達）、
  `asr_model_resolver.py:122`（鏈解析用 dispatcher，純模組）。`grep should_fallback` 僅命中測試中「斷言其不存在」的案例。
- 非 Mac 之 `chain[0]=="apple"` 不可能：216/216 顯式 apple 被拒、legacy/auto 鏈值為 `transformers|faster_whisper|mlx_whisper`（§3）。

**判定：PASS（含 F1′ 字面偏離）。**

---

## 6. 驗證項 5：前端（PASS）

### 6.1 檔案與方法

- `frontend/js/app.js` sha256 `ea4f3a51…`＝本次變更前＝前次稽核量測值（未變更）；repo 無 build 步驟，磁碟檔即服務內容。
- 以 Node v26.7.0 `vm` harness 實跑 `loadConfig()`＋`checkHealth()`，收集所有渲染 chunk（54 個）掃 needle：
  `/apple/i`、`/Apple 神經/`、`/apple-speech-cli/i`、`/swift/i`、`/xcode/i`、`/神經/`（`audit5_frontend_rev2.js`）。

### 6.2 實際渲染輸出

| 情境（accelerator / gpu_available） | 渲染文字 | needle hits |
|---|---|---|
| Windows cuda（`cuda` / true，RTX 4090） | `CUDA：NVIDIA GeForce RTX 4090` | **0**（與前次稽核值一致） |
| Windows cpu（`cpu` / false） | `CPU（未使用硬體加速）` | **0**（與前次一致） |
| 非 Mac legacy（`mlx-metal` / true，`asr_backend=mlx_whisper`） | `Apple Silicon（MLX/Metal）` | 1（僅此分支；見下） |
| Mac 對照（`apple-neural` / true） | `Apple 神經引擎（本機）` | —（僅供對照） |

- 兩個 Windows 預設情境渲染字串與前次稽核完全相同；`mlx-metal → 「Apple Silicon（MLX/Metal）」` 分支仍在且可渲染。
- **mlx-metal 分支可達性（精確化）**：Mac 上已不可達（Mac 無法再選 mlx_whisper）；但**非 Mac legacy 仍可達**——
  實測 Windows 模擬 + 顯式 `ASR_BACKEND=mlx_whisper` → `device_info.accelerator="mlx-metal"`、`asr_backend="mlx_whisper"`
  （`audit5b_accel_rev2.json`）。此為未變更的既有行為，正是本分支必須保留的原因。
- **Windows 不可能出現 Apple ASR 字串**：`apple-neural` 分支需 `asr_backend=="apple"`；Windows + `ASR_BACKEND=apple`
  在 `device_info` 解析即 `ValueError: ASR_BACKEND=apple 僅 macOS 支援（Apple Silicon、macOS 26+）`
  （`platform_config.py:69`，fail-loud；矩陣 216/216 拒絕），故 Windows 預設/合法設定下不可能渲染 Apple 字串。
- 靜態檔掃描：`frontend/index.html` 0 hits；`frontend/css/style.css` 與 `frontend/prototype/redesign-preview.html`
  命中 `-apple-system` 字型堆疊（**前次 F4 續存**；兩檔未被本任務修改、非渲染文字）。
- `app.js` 原始碼內含分支字面（`apple-neural`／`Apple 神經引擎（本機）`／`mlx-metal`／`Apple Silicon（MLX/Metal）`）；
  這些是分支程式碼，Windows 預設設定不會渲染（見上）。

**判定：PASS。**

---

## 7. 我嘗試過但未能攻破的清單（本次實跑）

1. 非 Mac 8 平台 × 9 apple 變體 × 3 函式（216 次）全數拒絕、訊息唯一；auto／空字串鏈全不含 apple。
2. 對 pre-change 樹重跑同矩陣：非 Mac 全平台、全區塊（apple/auto/legacy）逐呼叫相同——「legacy 行為不變」有直接對照證據。
3. 移除 MLX 相依後：Windows/Linux `uv pip compile` 輸出逐字節不變（64／63 包），新 lock 零 mlx/numba/tiktoken/scipy/llvmlite/more-itertools，`uv lock --check` exit 0。
4. 全 app Windows 模擬：3 端點 200、回應與啟動日誌零 needle、loader spy 0 呼叫、provider 0 載入、無 apple spawn。
5. 宿主 Apple 訊號無法經由本次依賴路徑外洩：非 Mac 分支完全不 import provider（§5.4）；`apple_helper` 區段為凍結的非 Mac 拒絕 JSON。
6. 前端以真實 Windows payload（含凍結 `apple_helper` 區段）實渲染：54 chunk 掃描 0 命中；mlx-metal／apple-neural 分支僅在其對應 accelerator 下渲染。
7. `import backend.services.asr_apple.contract`／`.dispatcher` 單模組純淨（AST＋獨立封裝 import：無 device_detector、無重型引擎）。

## 8. 殘留風險與未能驗證（UNVERIFIED）

- **R1（真機覆蓋，UNVERIFIED）**：無 Windows/Linux 實機；本矩陣為 `platform` monkeypatch＋spawn 阻斷之模擬（`sys.platform` 未改，原因同前次稽核；全 repo 無 `sys.platform` 分支）。真機完整轉錄 E2E（含模型）未執行（屬既有 WAVE-05 範圍）。
- **R2（樹漂移）**：驗證窗內 `apple_cli.py` 有 docstring-only 變更、其他 agent 將 `tests/test_mlx_direct.py` 加入 index 刪除（見 §1）。判定所用檔案皆 hash-stable；若受審檔再變更需重跑 §9 腳本。
- **R3（既有運維觀察）**：非 Mac 顯式 `ASR_BACKEND=mlx_whisper` 會讓 UI 顯示 `Apple Silicon（MLX/Metal）`（既有、未變更；因該設定在非 Mac 本無實際 MLX 能力）。另 Windows 顯式 `ASR_BACKEND=apple` 為 fail-loud（前次 F2），非本任務 regression。
- **R4（未執行面）**：未實際 `pip install`（requirements*.txt 僅靜態掃描）與 Docker build（僅檔案掃描）；未在真實 pip resolver 下重算（uv 已覆蓋）。
- **R5（Mac 面）**：`verify_env.py` Darwin/arm64 文案由「失敗回退 MLX-Whisper」改為無 fallback 敘述（§3.2）；Mac 真機驗收由本任務另一份 `mac-apple-only-audit.md` 覆蓋，不在本 rev2 範圍。

## 9. 證據附錄（臨時檔；供重跑）

- 腳本（`/tmp/win-audit-rev2/`）：`matrix_rev2.py`、`compare_rev2.py`、`audit1_asgi_rev2.py`、`audit2_deps.py`（原版重跑）、`audit4_rootcause_rev2.py`、`audit4_purity_rev2.py`、`audit4_purity2_rev2.py`、`audit5_frontend_rev2.js`、`audit5b_accel_rev2.py`、`audit5c_progress_rev2.py`
- 輸出（`/tmp/win-audit-rev2/logs/`）：`matrix_current.json`、`matrix_pre.json`、`compare_rev2.json`、`audit1_asgi_rev2.json`、`audit1_asgi_rev2_final.json`、`audit2_rev2.json`、`audit4_rootcause_rev2.json`、`audit4_purity2_rev2.json`、`audit5_frontend_rev2.json`、`audit5b_accel_rev2.json`、`audit5c_progress_rev2.json`、`uv_compile_{windows,linux,mac_arm64}_{pre,rev2}.txt`、`uv_compile_resolved_lines.txt`、`uv_lock_diff_head80.txt`、`hashes.txt`、`hashes_final.txt`
- pre-change 對照樹：`/tmp/win-audit-rev2/pre-change/`（`git archive HEAD` 展開；`APPLE_AUTO_FALLBACK == ("apple","mlx_whisper")`、`should_fallback` 存在）
