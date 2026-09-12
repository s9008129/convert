# Windows 零 Apple 矩陣 ＋ 包裝守衛 — 獨立對抗式驗證報告

- TASK_ID：T20260912-2242-01-apple-speech-analyzer-asr（PLAN_REVISION 1）
- 角色：獨立驗證者（Stage 04 委派之獨立驗證，非實作者；不修改產品碼與既有測試）
- 驗證時間：2026-09-12 23:27–23:40（Asia/Taipei）
- 受審修訂：HEAD `1bd54fb0c953dff75321a063216bb79686b33dd4`（`1bd54fb`）＋ 未提交工作樹
  - 工作樹於驗證期間被其他 agent 平行寫入（新增／修改 `backend/workers/asr_worker.py`、`backend/services/asr_subprocess.py`、`tests/test_apple_helper_absent_e2e.py` 等）；受審核心檔雜湊於 23:27 與 23:35 兩次量測一致，最終 ASGI 重跑於 23:37 完成。若受審檔再變更，本報告須重跑（見 §8 R5）。
- 宿主環境：macOS（Darwin/arm64）、Python 3.12.12（`.venv`）、fastapi 0.109.2／httpx 0.26.0、Node v26.7.0、uv 0.9.24、git 工作樹 dirty（本任務未提交變更）
- 模擬限制聲明：無 Windows 實機。模擬＝`platform.system`→`Windows`、`platform.machine`→`AMD64` ＋ 阻斷並記錄 `subprocess.run/Popen`（模擬無 helper／無 nvidia-smi）＋ `torch.backends.mps.is_available()` 強制 `False`（模擬非 Apple 硬體）。`sys.platform` **未**改（宿主為 macOS，改動會讓 stdlib `asyncio` 載入 `windows_events` 崩潰）；已 grep 確認 `backend/`、`scripts/`、`install_deps.py`、`main.py` 中無任何 `sys.platform` 分支，故此偏離不影響本矩陣結論（見 §8 R1）。
- 本報告為新增檔；未 `git add`／`git commit`／未改產品碼與既有測試。

## 0. 判定總表

| # | 驗證項 | 判定 | 備註 |
|---|---|---|---|
| 1 | 模擬 Windows 全 app ASGI 實打（health/config 零 Apple、sys.modules、spawn、凍結欄位） | **PASS（含字面偏離 F1）** | 功能語意全成立；僅「`backend.services.asr_apple.*` 全程為 0」字面不成立（3 個純模組被 `transcription.py` 頂層匯入） |
| 2 | 依賴解析（pyproject／docker／install_deps／真實 uv 解析） | **PASS** | Windows/Linux 依賴與輸出零 Apple/Swift/Xcode；mac-arm64 對照組有 mlx（marker 有效） |
| 3 | repo 無 tracked binary | **PASS** | 215 個 tracked 檔全為文字；建置產物實存於磁碟但被 ignore、不在 index |
| 4 | 前端產物（Windows cuda/cpu 實渲染字串） | **PASS（含觀察 F4）** | Node vm 實跑渲染字串零 apple/swift/xcode/神經；CSS 有既有 `-apple-system` 字型堆疊（非渲染文字、非本任務新增） |
| 5 | 反向檢查（顯式 apple 大小寫/空白變體 × 各平台） | **PASS（含觀察 F2）** | 8 非 Mac 平台 × 9 變體 × 3 函式 = 216 次呼叫全數拒絕且訊息一致；auto 全平台不含 apple |

**STATUS（總結論）：PASS。** 未發現任何「Windows（含 Docker/WSL）可解析到 apple」或「repo 追蹤 Apple binary」的漏洞；另有 1 條字面偏離（F1，非阻斷、非產品缺陷）與 3 條觀察（F2/F3/F4）供 Owner/Planner 知悉。

## 1. 受審修訂指紋（sha256）

| 檔案 | sha256 | 量測時間對照 |
|---|---|---|
| `backend/core/platform_config.py` | `d8dcd3f68f85a7d6e010e780904fa563d453193975b22c9940aa54a3902fad87` | 23:27＝23:35 一致 |
| `backend/core/asr_model_resolver.py` | `1c425d97eb28d58724e337fbeefc22dd5613af2e492e20a4848afb3ed6076d1d` | 23:27＝23:35 一致 |
| `backend/api/routes.py` | `f5c1da10a7c20ce0ed76a481ab3d145dc6afff4b6e91d3b55b4585af780039e0` | 23:27＝23:35 一致 |
| `backend/services/device_detector.py` | `8c05fe46b74dc3bb22268ef254afe07b3ffe6f252f3cd4cc041e5cf15a66e2bd` | 23:27＝23:35 一致 |
| `backend/services/transcription.py` | `5b038d095e73ea14573bf9e6c688dd0ab2716b61157272deb7b711e24fd01644` | 23:35 量測 |
| `backend/services/asr_apple/contract.py` | `629c3ee24102a8a0b3581e3ff495be3b3f110f3d0cd1d3d94bc20f6a30a34788` | 23:35 量測 |
| `backend/services/asr_apple/dispatcher.py` | `f3c3ea6defdff6d6cda8dec56434a34a0637d0edd35c079ca1fa4ef808ab72be` | 23:35 量測 |
| `backend/services/asr_apple/apple.py` | `3e2d42654e56a0e70f9b7e0fb647a7e45a6687228e3a36fa639350244c8e6165` | 23:35 量測（未載入驗證） |
| `backend/services/asr_apple/apple_cli.py` | `c15b3aeffb306cd56eaf9dbd4ec27ae2b1a93e9de3b2a2936d19e1e2e03146bf` | 23:35 量測（未載入驗證） |
| `frontend/js/app.js` | `ea4f3a5121d05806dcea189b0adb3ee8b1d798d594facabe46d5f0824d440915` | 23:27＝23:35 一致 |
| `install_deps.py` | `757b16dfa274dfdd2b9b728e27d2c7bbed1b36d2fae707a621b2052b0313f075` | 23:27＝23:35 一致 |
| `scripts/verify_env.py` | `edaa6e1c184ed9d9a411219de2fe81136b9e30eda53a664b370e352ab58cf740` | 23:35 量測 |
| `pyproject.toml` | `84a6169f1484f755afa86a7ffa7502bb378e53ac3c41f14b11063b44d39a179d` | 23:27＝23:35 一致（tracked、未修改） |

---

## 2. 驗證項 1：模擬 Windows 全 app ASGI 實打

### 2.1 實際命令與方法

```bash
cd /Users/hsiaojohnny/dev/convert
# 獨立腳本（自寫，非複用 repo 測試）：
#   在 import backend 之前：platform.system→"Windows"、platform.machine→"AMD64"、
#   DATA_DIR→mktemp、subprocess.run/Popen→記錄後 raise FileNotFoundError、
#   torch.backends.mps.is_available→False；載入 backend.main:app 後以 TestClient 實打。
.venv/bin/python /tmp/win-audit/audit1_asgi_windows.py          # 主要情境（mps-off）
.venv/bin/python /tmp/win-audit/audit1_asgi_windows.py --mps-available  # 加碼：宿主 MPS 可見
.venv/bin/python /tmp/win-audit/audit1c_spy.py                  # 加碼：loader spy
.venv/bin/python /tmp/win-audit/audit1d_rootcause.py            # sys.modules 根因
.venv/bin/python /tmp/win-audit/audit1b_progress_text.py        # 進度文案
```

### 2.2 觀察輸出摘要（皆為實跑）

- **端點**：`/api/health?quick=true` → **200**、`/api/health` → **200**、`/api/config` → **200**（含 `with TestClient(app)` 觸發 lifespan 的真實啟動流程：啟動成功、`裝置偵測完成: cpu, 精度: int8`、關閉流程正常）。
- **全回應字串掃描**：移除凍結的 `apple_helper` 區段後，對 3 個端點 JSON 掃 `apple|swift|xcode|speechanalyzer|apple-speech-cli|.build|xcodebuild`（不分大小寫）→ **0 hits**（quick、full、config 三份皆零；lifespan 啟動 stdout 日誌同為 0 hits）。
- **凍結 additive 欄位稽核**（quick 與 full 相同）：
  - keys 恰為 `{supported, available, path, probe, reason}`；`supported=false`、`available=false`、`path=null`、`probe=null`
  - `reason="非 macOS：Apple SpeechAnalyzer 僅支援 macOS"`
  - `reason` 不含 `/`、`\`（無路徑）、不含 `apple-speech-cli`（無 helper 執行檔名）、不含 `swift`／`xcode`、不含 `.build`（無建置資訊）。**除產品名與平台限制說明外，無新增可攻擊資訊**（見 F3）。
- **device/config 觀測**：`accelerator=cpu`、`current_device=cpu`、`mps_available=false`、`asr_backend=transformers`；`/api/config`：`asr_backend=auto`、`effective_asr_backend=transformers`、回應 key 無任何 `apple*`。
- **sys.modules 稽核（逐層）**：

  | import 對象 | `backend.services.asr_apple.*` |
  |---|---|
  | `backend.core.platform_config` | `[]`（0 個） |
  | `backend.core.asr_model_resolver` | `[]`（0 個） |
  | `backend.api.routes` | `[asr_apple, .contract, .dispatcher]`（3 個純模組） |
  | `backend.services.transcription` | 同上（3 個） |
  | `backend.services`、`backend.main` | 同上（3 個） |

  - **`backend.services.asr_apple.apple`（provider）與 `.apple_cli` 在所有階段皆為 `False`（未載入）**。
  - 根因：`backend/services/transcription.py:31`（`from backend.services.asr_apple.contract import …`）與 `:36`（`from backend.services.asr_apple.dispatcher import should_fallback`）為**頂層 import**；transcription 又被 `backend/services/__init__.py` 匯入，故任何載入 API/主程式的路徑都會帶入這 3 個純模組。provider 匯入則在函式內延後（`transcription.py:670`），Windows 永不觸發。
- **loader spy（加碼攻擊）**：把 `backend.api.routes._load_apple_helper_status` 換成「若被呼叫就回 `supported=true`」的 spy → Windows quick＋full health 呼叫次數 = **0**（回應仍為 `supported=false`，證明非靠欄位過濾）；只掛 router 的獨立 app 亦 200。
- **子程序稽核**：整場只有 `nvidia-smi --query-gpu=...` ×2（既有 CUDA 偵測，屬 Windows 正常行為）；**與 apple/swift/helper 相關的 spawn = 0**。
- **進度文案**（`task_processor._asr_stage_message()`）：Windows auto → `載入 Whisper 模型...`；Windows 被硬塞 `settings.ASR_BACKEND="apple"` → 解析例外被吞、回退 `載入 Whisper 模型...`（無 Apple 字樣、不崩）；macOS auto 對照 → `Apple 本機轉錄中…`。
- **加碼情境（不強制關閉宿主 MPS）**：`accelerator=mps`、`mps_available=true`（宿主 artifact；真 Windows 不會有），全回應掃描仍 **0 apple hits**、無 apple spawn。→ 即使宿主 Apple 硬體訊號外洩到模擬 Windows，Apple ASR 欄位仍不出現。

### 2.3 判定

- 零 Apple 欄位/字串（除凍結欄位）＝**PASS**；凍結欄位內容稽核＝**PASS**；provider 不載入／loader 不呼叫／無 spawn＝**PASS**。
- 字面檢查「`backend.services.asr_apple.*` 於載入 health 路由後應為 0」＝**FAIL（字面）**：實際為 3 個純模組（package＋contract＋dispatcher）。此偏離列為 **F1**；未達產品缺陷等級（純模組、零第三方依賴、無 import 期副作用；repo 既有 CHECK-05/NFR-03/SI-11 的規格文字為「`import contract` 不拉重型依賴／Windows import 無副作用」，非「health 路徑全程零載入」）。
- 驗證項 1 總判定：**PASS（含字面偏離 F1）**。

---

## 3. 驗證項 2：依賴解析（Windows 不解析 Apple 套件）

### 3.1 實際命令與觀察

```bash
cd /Users/hsiaojohnny/dev/convert
# (a) install_deps.py --check 走 main(argv, system_name) 實跑三平台
.venv/bin/python /tmp/win-audit/audit2_deps.py
# (b) 檔案掃描（實際命令）
grep -rniE "apple|swift|xcode" docker/ pyproject.toml requirements.txt requirements-correction.txt requirements.windows-cuda.txt
# (c) 真實解析（uv 0.9.24，真下載解析、非讀檔）
uv pip compile pyproject.toml --python-platform windows --python-version 3.12 --no-header -o uv_compile_windows.txt
uv pip compile pyproject.toml --python-platform linux   --python-version 3.12 --no-header -o uv_compile_linux.txt
uv pip compile pyproject.toml --python-platform aarch64-apple-darwin --python-version 3.12 --no-header -o uv_compile_mac_arm64.txt
```

- **(a) `install_deps.py`**：
  - `system_name="Windows"` → exit **0**、輸出 needle `apple|swift|xcode|speechanalyzer|apple-speech-cli|.build` 命中 **0 個**（只印檢查模式與清單檔名）。
  - `system_name="Linux"` → exit **0**、命中 **0 個**。
  - `system_name="Darwin"`（對照組）→ exit **0**、命中 **6 個**（含 `cd apple_speech_cli && swift build -c release`、`.build/release/apple-speech-cli`）→ 證明守衛是「mac-only」而非「永不輸出」。
- **(b) 檔案掃描**：`grep_exit=1`（**零命中**）於 `docker/`（含 Dockerfile、Dockerfile.gpu、docker-compose*.yml）、`pyproject.toml`、`requirements*.txt`。
- `pyproject.toml`：無任何 `apple/swift/xcode` 依賴；`mlx-whisper==0.4.3 ; platform_system == "Darwin" and platform_machine == "arm64"`（marker 正確）；無 optional-dependencies。`uv.lock`：字串 `apple/swift/xcode` 出現次數 **0／0／0**。
- **(c) 真實 uv 解析**：
  - `--python-platform windows` → 輸出 **207 行、exit 0**；`mlx|apple|swift|xcode` **0 hits**；含 `win32-setctime==1.2.0`（Windows-only 依賴，證明解析確實以 Windows 為目標）、`torch==2.14.0+cpu`、`faster-whisper==1.2.1`、`transformers==4.57.6`、`ctranslate2==4.8.2`。
  - `--python-platform linux` → 無 `mlx/apple`。
  - `--python-platform aarch64-apple-darwin`（對照）→ `mlx==0.29.3`、`mlx-metal==0.29.3`、`mlx-whisper==0.4.3` 出現 → marker 有效、解析可信。
- **加碼（未在原要求內）**：`scripts/verify_env.py` 的 `check_apple_native_environment(system_name, machine_name)`：Windows/AMD64、Linux/x86_64、Darwin/x86_64 → **None（完全跳過、零 Apple 輸出）**；Darwin/arm64 → 回 4 項檢查（ffmpeg/ffprobe/swift/helper；positive control）。

### 3.2 判定

**PASS**：Windows 與 Linux 的依賴解析、安裝提示、docker 產物皆不含任何 Apple/Swift/Xcode 依賴或文字；macOS 對照組正常出現（守衛未過度攔截）。

---

## 4. 驗證項 3：repo 無 tracked binary

### 4.1 實際命令與觀察

```bash
cd /Users/hsiaojohnny/dev/convert
git ls-files | wc -l                                   # → 215
git ls-files | grep -Ei '(^|/)apple|swift|xcode|\.build|apple-speech-cli'   # → 無輸出，exit 1
git ls-files -z | xargs -0 file -b | grep -Ei "Mach-O|ELF|PE32|executable"  # → 僅 shell/batch script
git ls-files -s | awk '$1=="100755"{print $4}'          # → 10 個既有 shell 腳本（9 個 .sh ＋ scripts/hooks/pre-push）
git check-ignore -v apple_speech_cli/.build/arm64-apple-macosx/release/apple-speech-cli
git check-ignore -v apple_speech_cli/apple-speech-cli
git ls-files --error-unmatch apple_speech_cli/.build/arm64-apple-macosx/release/apple-speech-cli
file apple_speech_cli/.build/arm64-apple-macosx/release/apple-speech-cli
git status --porcelain --ignored=matching | grep -i apple_speech_cli
```

- **215 個 tracked 檔**，路徑 pattern 掃描 **零命中**（無 `apple-speech-cli`、無 `apple_speech_cli/.build`、無 `.swift` 編譯產物）。
- `file(1)` 全庫掃描：型別分布為 Python script（96）／Unicode text（71）／JSON（19）／ASCII（12）／shell（10）／batch（4）／HTML（2）／diff（1）；**無任何 Mach-O／ELF／PE32**。executable bit 只有 10 個既有 `.sh`。
- 磁碟上**確實存在**建置產物：`apple_speech_cli/.build/arm64-apple-macosx/release/apple-speech-cli` 為 `Mach-O 64-bit executable arm64`（515,376 bytes）→ `git ls-files --error-unmatch` 回 **"did not match any file(s) known to git"**（不在版控）。
- ignore 佐證：
  - `git check-ignore -v apple_speech_cli/.build/arm64-apple-macosx/release/apple-speech-cli` → `apple_speech_cli/.gitignore:1:.build/`
  - `git check-ignore -v apple_speech_cli/apple-speech-cli` → `.gitignore:117:apple_speech_cli/apple-speech-cli`
  - `git status --ignored` → `!! apple_speech_cli/.build/`（untracked 且 ignored）
- 附註（非缺陷）：`git check-ignore` 若以符號連結路徑 `.build/release/...` 查詢會回 `fatal: pathspec ... is beyond a symbolic link`（SwiftPM 的 `release` 是 symlink）；改用具實體路徑即正常匹配。
- 附註：`tests/0903-科務會議.m4a` 為**未追蹤**音檔（測試素材），不在 index。

### 4.2 判定

**PASS**：全庫無 tracked binary；`.gitignore`（根 `.gitignore:116-117` ＋ `apple_speech_cli/.gitignore:1`）確實排除建置產物。

---

## 5. 驗證項 4：前端產物（Windows 實渲染）

### 5.1 實際命令與方法

```bash
node /tmp/win-audit/audit4_frontend.js
```

自寫 Node `vm` harness（非複用既有測試）：載入被服務的 `frontend/js/app.js`（`backend/main.py:160` 以 `StaticFiles` 掛載 `frontend/`、`:171` 以 `FileResponse` 服務 `index.html`，**無 build/bundle 步驟**，磁碟檔即服務內容），以 mock `fetch` 餵入「真實 Windows 版型」的 `/api/health`（含真伺服器會回傳的凍結 `apple_helper` 區段）與 `/api/config`，呼叫 `loadConfig()`＋`checkHealth()`，收集所有元素（含動態建立的模板卡）的 `textContent/innerHTML/value/className/id`（54 個 chunk），再掃 `apple|Apple 神經|apple-speech-cli|swift|xcode|神經`。

### 5.2 觀察輸出摘要

- `windows_cuda`（`accelerator=cuda`、`gpu_name=NVIDIA GeForce RTX 4090`、`gpu_available=true`）：
  - 狀態列渲染 = `CUDA：NVIDIA GeForce RTX 4090`；版本列 `v4.7.2`；模型卡 `使用模型：gemma4:31b（…）`
  - **掃描 hits = 0**（Apple 相關字樣零）
- `windows_cpu`（`accelerator=cpu`、`gpu_available=false`）：
  - 狀態列 = `CPU（未使用硬體加速）`；**hits = 0**
- 靜態檔直接掃描：`frontend/index.html` → **0 hits**；`frontend/css/style.css` → 命中 `Apple`（`-apple-system` 字型堆疊與 "Apple HIG 排版" 註解，**未被本任務修改**）；`frontend/prototype/redesign-preview.html` 同（設計原型檔）。

### 5.3 判定

**PASS**：Windows cuda/cpu 兩種情境實際渲染出的字串皆無 Apple ASR 相關字樣；HTML 乾淨。CSS/原型檔的 `-apple-system` 屬既有排版字型堆疊（非渲染文字、非 Apple ASR 資訊）→ 列為觀察 **F4**。

---

## 6. 驗證項 5：反向檢查（主動攻破嘗試）

### 6.1 實際命令與方法

```bash
.venv/bin/python /tmp/win-audit/audit5_reverse.py     # 平台矩陣 × 變體（純函式）
.venv/bin/python /tmp/win-audit/audit5b_explicit_env.py apple   # Windows + ASR_BACKEND=apple（全 app）
.venv/bin/python /tmp/win-audit/audit5b_explicit_env.py banana  # 對照：既有非法值語意
```

### 6.2 觀察輸出摘要

- **顯式 apple 拒絕矩陣**（`resolve_platform_asr_backend`／`infer_asr_backend`／`resolve_engine_chain` × 變體 `apple, Apple, APPLE, " APPLE ", "apple ", "  Apple  ", ApPlE, "\tAPPLE\n", "apple\t"`）：

  | 平台 | 結果 | auto 引擎鏈 |
  |---|---|---|
  | Windows/AMD64、Windows/ARM64 | 27/27 拒絕，訊息唯一 | `("transformers",)` 不含 apple |
  | Linux/x86_64、Linux/aarch64 | 27/27 拒絕，訊息唯一 | `("transformers",)` 不含 apple |
  | Darwin/x86_64（Intel Mac） | 27/27 拒絕，訊息唯一 | `("transformers",)` 不含 apple |
  | FreeBSD/amd64、UnknownOS/mystery、空平台（`platform.system()=""`） | 27/27 拒絕，訊息唯一 | `("transformers",)` 不含 apple |
  | Darwin/arm64（真 Mac） | 全變體 → `apple`／`("apple",)`（fail-closed）；`auto` → `("apple","mlx_whisper")` | 符合 Mac 契約 |

  - 拒絕訊息（216 次呼叫中所有失敗共用同一字串）：`ASR_BACKEND=apple 僅 macOS 支援（Apple Silicon、macOS 26+）`
- **環境變數路徑**（`get_whisper_backend()`，逐變體設定 `ASR_BACKEND` 並清 config 單例）：Windows/AMD64 與 Linux/x86_64 全 9 變體 → `ValueError`；Darwin/arm64 全 9 變體 → 正規化為 `apple`（fail-closed）。
- **Windows + 顯式 `ASR_BACKEND=apple` 的全 app 行為**（加碼）：`/api/health?quick=true` → **500**、`/api/config` → **500**、lifespan 啟動直接 `ValueError`（服務拒絕啟動）；回應內含明確訊息 `ASR_BACKEND=apple 僅 macOS 支援（Apple Silicon、macOS 26+）`。
  - 對照 `ASR_BACKEND=banana`（既有非法值）→ 同型 500／啟動失敗，訊息為既有 `ASR_BACKEND 必須是 auto、…` → **同一類 pre-existing fail-fast 語意**，顯式 apple 未引入新型失效模式（見 F2）。
- **守衛繞過面檢查**：`backend.services.asr_apple.dispatcher.resolve_engine_chain("apple", is_apple_platform=False)` 會回 `("apple",)`（純函式不做平台偵測）；但 grep 全 repo 生產端僅 3 個呼叫者（`transcription.py:600`、`task_processor.py:46`、`scripts/download_models.py:48`）全部走已加守衛的 `backend.core.asr_model_resolver.resolve_engine_chain`，無生產路徑繞過守衛。

### 6.3 判定

**PASS**：未發現任何可讓 Windows／Linux／Intel Mac／未知平台解析出 `apple` 的輸入；顯式 apple 一律明確拒絕（非 Mac）或 fail-closed（Mac）。F2 為「拒絕形式是 fail-loud」的觀察，非漏洞。

---

## 7. 發現（漏洞／反例／偏離）

### F1（字面偏離，非產品缺陷；建議 Planner 裁示是否收斂）
- **現象**：載入 health 路由（或整個 app）後，`sys.modules` 內存在 `backend.services.asr_apple`、`.contract`、`.dispatcher` 三個純模組；與「載入 health 路由時應為 0」的字面要求不符。
- **重現**：
  ```bash
  cd /Users/hsiaojohnny/dev/convert
  .venv/bin/python /tmp/win-audit/audit1d_rootcause.py
  # 觀察：import backend.core.platform_config → []
  #       import backend.api.routes / backend.services / backend.main →
  #       [backend.services.asr_apple, ...contract, ...dispatcher]
  grep -n "asr_apple" backend/services/transcription.py   # 31、36 為頂層 import
  ```
- **影響評估**：contract/dispatcher 為零第三方依賴的純函式模組（dataclass／常數／路由表），import 期無 spawn、無寫檔、無平台偵測；provider（`apple.py`／`apple_cli.py`）在 Windows 全程未載入、health loader 零呼叫、零 spawn。**對 Windows 功能、效能、風險無實質影響**；但若 Owner 意圖是「模組層完全零 Apple 載入」，需回 Stage 01 調整 transcription 的 import 策略（語意/依賴契約變更，非驗證者可自行處置）。
- **判定**：字面 **FAIL**；風險等級：**低（觀察）**。不影響本報告 STATUS=PASS（CORE 語意成立），但列入待決事項。

### F2（觀察：顯式 apple 的拒絕形式）
- **現象**：Windows 上 `ASR_BACKEND=apple`（含 `Apple`／`" APPLE "` 等變體）會讓服務**拒絕啟動**、`/api/health` 與 `/api/config` 回 500（訊息明確）；`ASR_BACKEND=banana` 等既有非法值行為同型。
- **重現**：
  ```bash
  cd /Users/hsiaojohnny/dev/convert
  .venv/bin/python /tmp/win-audit/audit5b_explicit_env.py " APPLE "   # 顯式 apple（變體）
  .venv/bin/python /tmp/win-audit/audit5b_explicit_env.py banana      # 對照：既有非法值
  ```
- **影響評估**：符合 SI-02「顯式 fail-closed／非 Mac 明確拒絕」；無靜默 fallback、無 Apple 執行。屬 fail-loud 設定錯誤（運維需修正設定）；非漏洞。README§367 與 `doc/apple-speech-analyzer-operations.md` 已載明 Windows `auto` 永不含 apple；建議後續補一句「Windows 顯式 apple 會拒絕啟動」的運維說明（非驗證者職權）。

### F3（觀察：凍結欄位文字揭露範圍）
- **現象**：Windows `/api/health` 的 `device_info.apple_helper.reason` = `非 macOS：Apple SpeechAnalyzer 僅支援 macOS`，含產品名 `Apple SpeechAnalyzer`；但 `path=null`、`probe=null`、無路徑字元、無 `apple-speech-cli`、無 `swift/xcode/.build`。
- **重現**：`.venv/bin/python /tmp/win-audit/audit1_asgi_windows.py`（或任一既有 health 測試）觀察 `apple_helper`。
- **判定**：在 CHECK-11 凍結語意（Windows 回 `supported:false`＋可觀察 reason）之內；未洩漏路徑或 helper 執行檔名。觀察即可。

### F4（觀察：前端 CSS 既有 Apple 字樣）
- **現象**：`frontend/css/style.css` 與 `frontend/prototype/redesign-preview.html` 含 `-apple-system`（字型堆疊）與 "Apple HIG" 註解字樣；兩檔皆**未被本任務修改**（`git status` 未列出）。
- **重現**：`git grep -n -i apple -- frontend/`
- **判定**：非 Apple ASR 資訊、非渲染文字；Windows UI 不會因此顯示任何 Apple ASR 字樣。若 Owner 對「產物零 apple 字樣」採嚴格字面（含 CSS），此為唯一殘留命中；不建議在本任務擴大處理（超出 frozen 範圍）。

---

## 8. 我嘗試過但未能攻破的清單

1. 8 個非 Mac 平台 × 9 個大小寫/空白/定位字元變體 × 3 個入口函式（216 次）全部被拒、訊息一致；Mac 全變體 fail-closed。
2. `auto`／空字串在 Windows/Linux/Intel Mac/FreeBSD/未知/空平台之引擎鏈皆不含 apple，且與現行解析一致（`transformers`）。
3. Windows 下把 `settings.ASR_BACKEND` 硬塞 `"apple"`：進度文案解析例外被安全吞掉、回退 Whisper 文案（無 Apple 字樣、不影響轉錄流程起點）。
4. 把 `_load_apple_helper_status` 換成「會回報 supported=true」的 spy：Windows quick/full health 呼叫次數 = 0（不靠事後過濾）。
5. 全 app lifespan 真實啟動＋health/config：啟動成功、日誌零 Apple 字樣、裝置偵測 CPU、三個端點 200。
6. 讓宿主 Apple MPS 訊號外洩（`accelerator=mps`、`mps_available=true`）：health/config 掃描仍零 apple 字串、零 apple spawn。
7. `install_deps.py --check` Windows/Linux：零 Apple/Swift/Xcode 輸出、exit 0；Darwin 對照組照常提示（證明守衛不是「永遠關閉」）。
8. 真實 `uv pip compile`（Windows／Linux／mac-arm64）：Windows/Linux 解析無 mlx/apple 套件；mac-arm64 對照組有 mlx（marker 非死碼）。
9. `git ls-files` 全庫（215 檔）：無 apple/swift/.build 路徑、無 Mach-O/ELF/PE32、executable 僅 shell scripts；SwiftPM 建置產物（Mach-O arm64）實存磁碟但 `git ls-files --error-unmatch` 失敗（不在 index）＋`git check-ignore -v` 佐證 ignore 生效。
10. Node vm 實跑前端（cuda／cpu，含真實 `apple_helper` payload）：54 個渲染 chunk 掃描 0 命中。
11. `scripts/verify_env.py` 非 mac 呼叫 `check_apple_native_environment` → `None`（零輸出）；mac 對照組正常回報。

## 9. 殘留風險

- **R1（真機覆蓋）**：本矩陣為模擬（`platform` monkeypatch＋spawn 阻斷＋MPS 關閉），非 Windows 實機；`sys.platform` 未改（已確認全 repo 無 `sys.platform` 分支，影響極小）。Windows 上以真實 `ffmpeg/nvidia-smi` 的完整轉錄 E2E 未執行（需 Windows 機器與模型），屬既有 WAVE-05/後續驗收範圍。
- **R2（F1 待決）**：若 Owner 要求「health 模組層零 Apple 載入」，需回 Stage 01 調整（依賴契約變更）；目前為低風險觀察。
- **R3（F2 運維）**：Windows 顯式 `ASR_BACKEND=apple` 會 fail-loud 拒絕啟動（與既有非法值同型）；建議文件明列，避免運維誤設後誤判為 regression。
- **R4（驗證期間樹變動）**：工作樹有其他 agent 平行寫入（23:26–23:35 間新增 `asr_worker.py` 相關變更與 `tests/test_apple_helper_absent_e2e.py`）。本報告以 §1 雜湊釘住受審修訂；若受審檔再變更須重跑 `/tmp/win-audit/audit1_asgi_windows.py`、`audit1d_rootcause.py`、`audit4_frontend.js`、`audit5_reverse.py`。
- **R5（非阻斷未驗面）**：`backend/workers/asr_worker.py`（新隔離子程序）本身平台中立、未直接引用 apple／未直接呼叫 resolver，其轉錄路徑繼承 `transcription_service` → 受守衛的 `resolve_engine_chain`；我未在 Windows 模擬下實跑該 worker 子程序（缺模型且會 spawn），僅以解析層證據佐證。

## 10. 證據附錄（臨時檔，供重跑）

- 腳本：`/tmp/win-audit/audit1_asgi_windows.py`、`audit1b_progress_text.py`、`audit1c_spy.py`、`audit1d_rootcause.py`、`audit2_deps.py`、`audit4_frontend.js`、`audit5_reverse.py`、`audit5b_explicit_env.py`、`probe_modules.py`
- 輸出：`/tmp/win-audit/logs/`（`audit1_mps_off.json`、`audit1_mps_on.json`、`audit1_final.json`、`audit1b_progress.json`、`audit2*`、`audit4_frontend.json`、`audit5_reverse.json`、`audit5b_apple.json`、`audit5b_banana.json`、`uv_compile_windows.txt`、`uv_compile_linux.txt`、`uv_compile_mac_arm64.txt`）
