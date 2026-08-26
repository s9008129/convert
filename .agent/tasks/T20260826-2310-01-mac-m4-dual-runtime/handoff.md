# Handoff — Mac MLX 與 NVIDIA 雙平台原生推論

## TASK
- TASK_ID: T20260826-2310-01-mac-m4-dual-runtime
- STATUS: READY_FOR_IMPLEMENTATION
- PLAN_PATH: .agent/tasks/T20260826-2310-01-mac-m4-dual-runtime/plan.md
- PLAN_REVISION: 1
- PLAN_SHA256: 20ba410c1a3ed5a87b8b5af92b93512550d831fa4279981bf402534a74b54927
- REVIEW_REQUIRED: YES
- REVIEW_REPORT: .agent/tasks/T20260826-2310-01-mac-m4-dual-runtime/review/attempt-01/review_report.md
- REVIEWED_PLAN_REVISION: 1
- REVIEWED_PLAN_SHA256: 20ba410c1a3ed5a87b8b5af92b93512550d831fa4279981bf402534a74b54927
- INDEPENDENT_ACCEPTANCE_REQUIRED: YES
- E2E_REQUIRED: YES
- ACCEPTANCE_MODE: E2E
- Fresh Implementer required: YES
- Planner/Reviewer transcript required: NO

## GOAL_ANCHOR

**PRIMARY_OUTCOME**：`convert` 能在 48GB Mac M4 Pro 上以原生程序執行——用 Apple MLX/Metal 加速既有 Breeze ASR 權重做轉錄，並透過 LM Studio 對「當下唯一載入的 LLM」生成摘要；同一份程式仍維持 NVIDIA/CUDA 執行能力。

**SUCCESS_EVIDENCE**（缺一不可）：
1. Mac 在「未裝/未啟動 Docker、未用 NVIDIA、未呼叫 Ollama」下完成 upload → MLX ASR → LM Studio summary → export。
2. 執行期健康資訊明確回報 `mlx_whisper` 與 `mlx-metal`，而非 CPU fallback 或誤標成 PyTorch MPS。
3. `HF_HUB_OFFLINE=1` 下命中既有 Breeze-ASR-26-MLX snapshot 完成轉錄，**沒有第二份模型副本**。
4. LM Studio 更換 loaded model 後，不改程式/設定即可讓下一個摘要工作採用新模型；零個或多個 loaded LLM 時明確失敗且不任意選擇。
5. 現有 NVIDIA backend 選擇、CUDA 行為與 regression tests 維持相容。

**MUST_NOT_BREAK**（絕對不可違反）：
- `MNB-01`：不得新增/修改/刪除/由工具產生任何 `/Users/hsiaojohnny/dev/yt_down_txt` 內容；若實作需要改動，**立即停止並取得使用者明確同意**。
- `MNB-02`：不得把 `yt_down_txt` 程式碼、絕對路徑或 `.venv` 變成 `convert` 的必要 runtime dependency。
- `MNB-03`：不得硬編碼目前或未來 LM Studio LLM 名稱；`LMSTUDIO_MODEL` 僅可作 optional explicit override。
- `MNB-04`：保留 Windows/Linux/NVIDIA 的 Transformers、faster-whisper、CUDA 與既有 Ollama 選項。
- `MNB-05`：摘要失敗時必須延續既有「保留逐字稿並輸出僅逐字稿結果」的局部降級契約。
- `MNB-06`：不得宣稱 Apple 加速或測試通過，除非實際 backend/device 與執行證據支持。

## CRITICAL_PATH

`平台設定 → MLX adapter/cache reuse → LM Studio deterministic selection → native Mac startup → Mac offline ASR integration → Mac full E2E → NVIDIA regression`

最小安全路徑：先讓 Mac 的 `ASR_BACKEND=auto` 真正走 MLX/Metal 並離線命中既有 snapshot，再讓 `LOCAL_LLM_PROVIDER=auto` 走 LM Studio 動態選模，最後以原生 uv 啟動跑完整 E2E，再回頭跑 NVIDIA regression。CORE 驗收未通過前，**不投入 UI polish 或真實會議品質統計**。

## SEMANTIC_INVARIANTS

以下語意契約是 Executor **不得擅自改變**的（即使 code diff 很小）：

1. **required/optional 分類**：`LMSTUDIO_MODEL` 從「具硬編碼 default 的必填字串」改為 `Optional[str] = None`（空字串正規化成 `None`）。它是 optional override，不是必要設定，也不得變回硬編碼。
2. **VALID/readiness 語意**：LM Studio readiness **不是**全域啟動 gate。唯一全域啟動 gate 是「backend 自身必要依賴可載入」。服務在 LM Studio 不可用時仍須能 upload、ASR、輸出逐字稿、回報健康診斷。
3. **gating/veto**：
   - ASR 工作 gate：所選 backend 與 model 必須可載入（無逐字稿即無任何後續輸出，局部降級不足）。
   - 摘要工作 gate：LM Studio 必須可連線且選出唯一 loaded LLM（只阻擋摘要，不使已完成逐字稿失效）。
4. **穩定錯誤語意**（經既有 exception/description 管道落到 task summary error 與 health detail，**不新增 task state 或公開 retry API**）：
   - `ASR_BACKEND_UNAVAILABLE`：平台選定 backend 缺少 runtime package 或硬體能力。
   - `ASR_MODEL_UNAVAILABLE`：repo/revision/path 無法在目前 online/offline 政策下解析。
   - `LMSTUDIO_UNREACHABLE`：server 無法連線或 timeout。
   - `LMSTUDIO_NO_LOADED_LLM`：排除 embedding 後沒有 loaded LLM instance。
   - `LMSTUDIO_MULTIPLE_LOADED_LLMS`：未提供 override 且 loaded LLM instance 超過一個。
   - `LMSTUDIO_MODEL_NOT_LOADED`：override 無法唯一匹配已載入 instance。
5. **fallback/降級**：摘要失敗沿用既有 `summary_failed` 降級——逐字稿先落檔、DOCX 明確標示僅逐字稿。不得讓摘要失敗擴散使已完成 ASR 無效。
6. **priority/決策權**：`LMSTUDIO_MODEL` override 完全覆蓋自動選擇，但 veto=否（未設定時用唯一 loaded 規則；不匹配時摘要失敗）。選模結果綁定整次摘要工作，工作中不得切換。
7. **平台語意**：`ASR_BACKEND=auto` 在 Darwin ARM64 從 CPU/Transformers 改為 `mlx_whisper`/MLX-Metal；`LOCAL_LLM_PROVIDER=auto` 在 Darwin ARM64 必然解析為 `lmstudio`。**明確設定 `ASR_BACKEND=transformers|faster_whisper` 時不因平台自動改寫**；**明確設定非 Mac `LOCAL_LLM_PROVIDER=ollama` 時保留既有 Ollama 行為**。

## BEST_EFFORT_DO_NOT_GATE

以下 SUPPORTING/BEST_EFFORT 元素的失敗**必須保持局部**，不得阻擋 backend 或推論：

- Health/UI 新欄位（accelerator/asr_backend/asr_model/llm readiness）——顯示層故障不得阻擋推論。
- `LMSTUDIO_MODEL` override——未設定時用唯一 loaded 規則。
- LM Studio context length——無法取得時用既有保守 token budget 並標示未知。
- 原生啟動腳本、verify_env 的 platform-aware 判定——不把未使用的 faster-whisper 或 Ollama 當 Mac global blocker。

## DEFERRED_NOT_THIS_TASK

- 真實會議錄音 CER/WER 計算與 NVIDIA 結果比較（現有 synthetic Taigi evidence 僅證明可行性）。
- LM Studio GPU offload、context/KV cache tuning、長會議效能 benchmark。
- NVIDIA 主機恢復後的真實 CUDA E2E（RTX 4090 目前不可用，不得宣稱 hardware E2E）。
- 更豐富的模型選擇 UI、model lifecycle 控制、摘要獨立重試 API。
- Mac Docker、Ollama on Mac、LM Studio SDK/server control/模型下載載入卸載、ASR 模型訓練/量化/轉換。

## REPO_ANCHOR
- Project root: `/Users/hsiaojohnny/dev/convert`
- Branch: `main`
- Anchor HEAD: `712d37831dbbee47fbbd600120f88b3d774230fb`（review commit；plan 落檔 commit 為 `9bc3081365713c5e53deaf3a1fb233db12e61324`）
- Relevant dirty state: clean（handoff 落檔前）
- Drift since plan/review: 無。plan revision 1 未變，review attempt-01 已 APPROVED 且 SHA 一致。

## CURRENT_STATE_DELTA

（plan 的 VERIFIED_CURRENT_STATE 已由 reviewer 逐一驗證，以下為實作起點事實，非待辦）

- `backend/services/transcription.py`：`_detect_runtime()` 在 `DeviceType.MPS` 時降級 CPU（line 96-97）；`_backend` 只走 transformers/faster_whisper。
- `backend/core/asr_model_resolver.py`：`infer_asr_backend()` 只接受 `transformers`/`faster_whisper`（line 63-71）。
- `backend/services/summarization.py`：`_select_local_engine()` 先探 Ollama 再探 LM Studio（line 797-810）；`_get_lmstudio_client()` 用同步 `OpenAI`（line 150-163），會阻塞 async event loop。
- `backend/core/config.py`：`LMSTUDIO_MODEL` 預設 `gpt-oss-20b`（硬編碼）、`LMSTUDIO_BASE_URL` 預設 `http://host.docker.internal:1234/v1`；`LOCAL_LLM_PROVIDER` 目前**不存在**（需新增）。
- `config.macos.yaml` 與 `scripts/macos/start-mac-native.sh`：含過時 `device: mps`、`use_mps: true`、`model: gemma-3-27b-it-qat`、`mlx-community/whisper-large-v3-turbo`、conda meetingscribe、`ollama pull` 等假設。
- `backend/services/task_processor.py`：已把摘要失敗局部降級為「僅逐字稿」（line 233-235），**不需新增 task state machine 或 retry API**。
- 既有 Breeze-ASR-26-MLX snapshot：`doggy8088/Breeze-ASR-26-MLX`（約 2.9GB），revision `619860a64925c0f0dfecdbb5f8d9a2da2df1bc12`，已位於標準 Hugging Face shared cache。

## MUST_READ_PLAN

在 FIRST_ACTION 前**必須**先讀 plan.md 的以下段落（其餘可依需查閱）：

- `GOAL_CONTRACT`（PRIMARY_OUTCOME / SUCCESS_EVIDENCE / MUST_NOT_BREAK / NON_GOALS）
- `REQUIREMENTS_AND_CRITICALITY`（REQ-01~09、NFR-01~04 的 trace 與 criticality）
- `DECISIONS`（DEC-01~06，尤其 DEC-02 shared-cache reuse、DEC-04 唯一 loaded instance 選模）
- `SEMANTIC_CONTRACT`（不變契約 / 改變契約 / 穩定錯誤語意）
- `TARGET_CONTRACT`（設定、LM Studio 選模、ASR、Health/API/UI、原生啟動的具體規格）
- `CHANGE_MAP`（各 boundary 對應的檔案）
- `IMPLEMENTATION_WAVES`（WAVE-01~04 的 scope/exit criteria/rollback）
- `TEST_AND_ACCEPTANCE`（requirement-to-evidence mapping、Mac native integration、degraded scenarios、True Mac E2E）
- `MIGRATION_COMPATIBILITY_ROLLBACK`、`RISKS`、`RISKIEST_ASSUMPTIONS`、`DEFINITION_OF_DONE`

## SETTLED_DO_NOT_REOPEN

以下決策已定案，**不得重新討論**（除非觸發 STOP_AND_ESCALATE_IF）：

- `DEC-01`：Mac ASR 用 mlx-whisper（第三個 ASR adapter），不用 faster-whisper 或 Transformers/MPS 作 auto 預設。
- `DEC-02`：重用 shared HF cache（`huggingface_hub.snapshot_download`），不引用 `yt_down_txt` model directory。
- `DEC-03`：LM Studio 用現有 httpx + AsyncOpenAI，不新增 LM Studio SDK。
- `DEC-04`：動態選模採「唯一 loaded instance，否則 fail explicit」，排除 embedding，override 唯一匹配優先。
- `DEC-05`：Mac 原生 uv 執行（Python 3.12 + `.python-version` + `uv sync --frozen`），不用 Docker/conda fallback。
- `DEC-06`：大型模型循序執行，不主動卸載 LM Studio。
- 全域 gate 設計（LM Studio readiness 非全域 gate；ASR/摘要 gate 各自局部）。
- 穩定錯誤語意（六個 LM Studio/ASR 錯誤碼）。

## REVERIFY_ON_START

僅以下「可變事實」需在開始時重新確認（其餘以 plan 為準）：

1. LM Studio 本機 `/api/v1/models` 的實際 payload 欄位（model key、loaded instance identifier、`type=llm` vs embedding 的區分方式）——WAVE-01 用唯讀 response 固化 fixture。
2. `doggy8088/Breeze-ASR-26-MLX@619860a64925c0f0dfecdbb5f8d9a2da2df1bc12` 能否由 `huggingface_hub` 在 `HF_HUB_OFFLINE=1` 下解析（WAVE-02 前置；若不成立則 STOP 並 replan，不得改 `yt_down_txt`）。
3. 平台 marker 是否讓 MLX 依賴不進入非 Darwin ARM64 安裝圖（`uv lock --check` 驗證）。
4. 目前 LM Studio server 未啟動且無 loaded model——這是 Stage 05 外部前置，非產品缺陷。

## TRIGGERED_POLICIES

- `goal-alignment-design-economy.md`
- `plan-review-gate.md`
- `testing-verification.md`（若存在，用於驗收）
- `dependencies-contracts.md`（若存在，用於 config/依賴語意變更）
- `git-change-hygiene.md`（若存在，用於 commit 紀律）

## FIRST_ACTION

執行 **WAVE-01** 的第一步：建立平台感知且向後相容的 config/provider 語意契約，並以唯讀方式固化 LM Studio `/api/v1/models` fixture。

具體：
1. 在 `backend/core/config.py` 新增 `LOCAL_LLM_PROVIDER: str = "auto"`（`auto|lmstudio|ollama`），把 `LMSTUDIO_MODEL` 改為 `Optional[str] = None`，把 `LMSTUDIO_BASE_URL` 改為平台感知（native Mac 預設 `http://127.0.0.1:1234`，container 保留 `host.docker.internal`），並做 `/v1` normalization。
2. 在 `backend/core/platform_config.py` 加入 Darwin ARM64 的 provider/backend 平台預設。
3. 在 `backend/services/summarization.py` 建立 loaded-instance selector（`httpx.AsyncClient` 查 `/api/v1/models`，`AsyncOpenAI` 做 completion），移除硬編碼 LLM default，保留非 Mac Ollama 路徑。
4. 以本機唯讀 response 固化 `/api/v1/models` fixture，寫 zero/one/multiple/embedding/override 的 focused tests。

> 建議（來自 review RV-02，非強制）：在 WAVE-01 期間或之前，先以唯讀方式做一次輕量 MLX offline-load spike（`HF_HUB_OFFLINE=1` 載入 pinned snapshot 轉錄短音檔），提前確認 RISKIEST_ASSUMPTION #1；若失敗立即 replan。

## IMPLEMENTATION_WAVES

- `WAVE-01`（CORE）：鎖定設定與 LM Studio 語意契約。Serves REQ-03/04/07、NFR-02。Exit：所有 LM Studio 決策場景有 deterministic result/error；未新增 SDK；現有 Ollama tests 不退化。
- `WAVE-02`（CORE）：實作 MLX ASR 與 shared-cache 重用。Serves REQ-01/02/06、NFR-01/03/04。Exit：Mac integration 實際回報 `mlx_whisper`/`mlx-metal` 並產生非空逐字稿；無 project-local model copy；CUDA tests 維持通過。
- `WAVE-03`（SUPPORTING）：修復 Mac 原生操作與可觀測性。Serves REQ-05/08/09、MNB-06。Exit：Mac setup/start 不呼叫 Docker/Ollama、不自動安裝/下載；health 能分辨 MLX/CUDA/CPU 與 LM Studio selection errors。
- `WAVE-04`（CORE 收斂）：完整驗收與相容性收斂。Serves 全部 CORE REQ 與 SUCCESS_EVIDENCE。Exit：Mac E2E PASS、required test suite PASS、`yt_down_txt` 狀態與基準一致、diff 僅含核准範圍。

## ACCEPTANCE_CONTRACT

**CORE（先驗證，缺一即失敗）**：
- REQ-01：Darwin ARM64 selection unit test + 實際 Mac MLX transcription 回報 `mlx_whisper`/`mlx-metal`。
- REQ-02：`HF_HUB_OFFLINE=1` 用 pinned snapshot 完成短音檔轉錄，且無第二份權重。
- REQ-03：provider tests 證明 Mac auto 不探測 Ollama；完整 E2E 僅 LM Studio。
- REQ-04：zero/one/multiple/override/embedding contract tests + E2E 記錄實際 loaded model identifier。
- REQ-05：未使用 Docker 的 fresh native uv setup/start 與完整 journey。
- REQ-06：現有 ASR/device/summarization tests + mocked NVIDIA/CUDA contract；RTX 不可用時不得宣稱硬體 E2E。
- REQ-07：LM Studio unreachable/ambiguous integration 證明 task 保留 transcript 並標示 summary failure。
- NFR-01：task sequence/subprocess test；ASR worker exit 後無殘留 child process。
- NFR-03：不同 backend/model/revision 產生不同 cache signature。
- NFR-04：實作前後 `yt_down_txt` Git 狀態一致，產品碼無其絕對路徑或 `.venv` 引用。

**SUPPORTING / degraded-mode（次要）**：
- REQ-08：health response contract 與 frontend component/status test。
- REQ-09：scripts shell syntax、從非 repo cwd 啟動的 path test、platform-aware verify_env test。
- NFR-02：async mocked latency/timeout/retry test，決定性 4xx/selection error 不重試。

**驗證指令**（依實際新增 test module 名稱調整）：
```bash
uv lock --check
uv run pytest tests/test_device_detector.py tests/test_transcription_service.py tests/test_asr_subprocess.py -q
uv run pytest <LM-Studio-provider-focused-tests> -q
HF_HUB_OFFLINE=1 uv run pytest <MLX-cache-integration-test> -q
uv run pytest tests/ -q
uv pip check
git diff --check
```

**Mac native integration**：用 macOS `say` 在系統 temp 建固定短語音 → ffmpeg 前處理 → `HF_HUB_OFFLINE=1` 真實 MLX adapter/subprocess 轉錄 → 驗證逐字稿非空含關鍵詞、backend=`mlx_whisper`、accelerator=`mlx-metal`、snapshot revision 正確、無 project-local duplicate、`yt_down_txt` 狀態未變。

**True Mac E2E**：使用者手動啟動 LM Studio server 並載入恰一個 LLM；實作者只讀取狀態，不下載/載入/卸載模型。原生 uv 啟動 → upload 短語音 → 等 task 完成 → 下載逐字稿與會議紀錄 → 驗證逐字稿/摘要/DOCX 均非空、LLM identifier 等於當時唯一 loaded model、log 無 Ollama request/無新模型下載/無 `yt_down_txt` 寫入。

## STOP_AND_ESCALATE_IF

遇到以下任一情況，**立即停止並回報**（不得自行繞過或改語意）：

1. 需要修改 `/Users/hsiaojohnny/dev/yt_down_txt` 的任何內容（MNB-01）。
2. LM Studio `/api/v1/models` 無法判斷 loaded instances 或區分 LLM/embedding。
3. offline snapshot 無法由 `huggingface_hub` 解析（RISKIEST_ASSUMPTION #1 失敗）。
4. 平台 marker 破壞非 Mac install（`uv lock --check` 或 Windows/Linux resolution 失敗）。
5. 實作要求改變 fallback/gating/error 語意、required/optional 分類、或任何 SEMANTIC_INVARIANTS 條款。
6. 發現 plan 的 PRIMARY_OUTCOME 與使用者實際意圖不符。
7. 循序執行在 48GB unified memory 下仍出現常態性記憶體壓力（需 replan，不得偷偷管理 LM Studio lifecycle）。

## HISTORICAL_TASK_DEPENDENCIES

NONE
