# 在 NVIDIA CUDA 與 Mac M4 Pro 上提供原生雙平台推論

## META

- Plan status: READY_FOR_REVIEW
- Task mode: NEW_PLAN
- Task class: STANDARD
- TASK_ID: T20260826-2310-01-mac-m4-dual-runtime
- PLAN_REVISION: 1
- REVIEW_REQUIRED: YES
- INDEPENDENT_ACCEPTANCE_REQUIRED: YES
- E2E_REQUIRED: YES
- ACCEPTANCE_MODE: E2E
- Branch: `main`
- Anchor HEAD: `8c7ebe95bc9390ae5a4412b57fbc654d96c189fd`
- Working tree: Phase B 落檔前為 clean；本 revision 僅新增本 `plan.md`
- Canonical request/spec: 本任務對話中使用者於 2026-08-26 提出的 Mac M4 Pro／LM Studio／既有 ASR 模型重用需求、後續釐清，以及明確禁止修改 `/Users/hsiaojohnny/dev/yt_down_txt` 的約束

## OWNER_CHECK

1. **實際目標**：在 RTX 4090 主機不可用時，讓目前專案能直接在 48GB Mac M4 Pro 上完成語音轉錄與摘要，同時保留 NVIDIA/CUDA 支援。
2. **真正必要**：Mac ASR 必須實際使用 Apple MLX/Metal；Mac LLM 必須經由 LM Studio 並動態採用已載入模型；Mac 不使用 Docker；既有 NVIDIA 路徑不得退化。
3. **支援／最佳努力**：健康狀態與前端顯示、原生啟動腳本、真實會議品質比較屬可運維性與信心提升；不能取代 CORE E2E 證據。
4. **可阻擋的條件**：ASR backend 或權重不可用會阻擋轉錄，因為逐字稿無法產生；LM Studio 無可唯一決定的已載入 LLM 只阻擋摘要，不得阻擋服務啟動或使已完成逐字稿失效。
5. **刻意不建置**：Mac Docker、Ollama fallback、LM Studio 模型下載／載入／卸載管理、跨專案共用虛擬環境，以及任何對 `yt_down_txt` 的修改。

## GOAL_CONTRACT

### PRIMARY_OUTCOME

`convert` 能在 Mac M4 Pro 上以原生程序執行：使用 MLX/Metal 加速既有 Breeze ASR 權重，並透過 LM Studio 對當下唯一載入的 LLM 生成摘要；同一份程式仍維持 NVIDIA/CUDA 執行能力。

### SUCCESS_EVIDENCE

- Mac 在未安裝／未啟動 Docker、未使用 NVIDIA、未呼叫 Ollama 的情況下完成 upload → MLX ASR → LM Studio summary → export。
- 執行期健康資訊明確回報 `mlx_whisper` 與 `mlx-metal`，而非 CPU fallback 或錯誤標示成 PyTorch MPS。
- 在 `HF_HUB_OFFLINE=1` 下命中既有 Breeze-ASR-26-MLX snapshot 並完成轉錄，沒有第二份模型副本。
- LM Studio 更換 loaded model 後，不修改程式與設定即可讓下一個摘要工作採用新模型；零個或多個 loaded LLM 時明確失敗且不任意選擇。
- 現有 NVIDIA backend 選擇、CUDA 行為與 regression tests 維持相容。

### MUST_NOT_BREAK

- `MNB-01`：不得新增、修改、刪除或由工具產生任何 `/Users/hsiaojohnny/dev/yt_down_txt` 內容；若實作需要改動，必須停止並取得使用者明確同意。
- `MNB-02`：不得把 `yt_down_txt` 程式碼、絕對路徑或 `.venv` 變成 `convert` 的必要 runtime dependency。
- `MNB-03`：不得硬編碼目前或未來 LM Studio LLM 名稱；`LMSTUDIO_MODEL` 僅可作 optional explicit override。
- `MNB-04`：保留 Windows/Linux/NVIDIA 的 Transformers、faster-whisper、CUDA 與既有 Ollama 選項。
- `MNB-05`：摘要失敗時必須延續既有「保留逐字稿並輸出僅逐字稿結果」的局部降級契約。
- `MNB-06`：不得宣稱 Apple 加速或測試通過，除非實際 backend/device 與執行證據支持。

### NON_GOALS

- 在 Mac 上建置或維護 Docker/Compose 流程。
- 由 `convert` 控制 LM Studio server lifecycle、模型下載、JIT load、GPU offload 或 unload。
- 將所有 ASR backend 統一重寫成 MLX，或移除 CPU/CUDA fallback。
- 建立新的通用 provider framework、模型管理 UI 或獨立摘要重試 API。
- 在本次工作中重新訓練、量化或轉換 ASR/LLM 權重。

### CRITICAL_PATH

1. 建立平台感知且向後相容的 ASR/LLM runtime 設定。
2. 在現有 ASR subprocess 邊界加入 `mlx_whisper` adapter，從 shared Hugging Face cache 解析既有權重。
3. 在現有摘要服務加入 LM Studio loaded-model discovery 與每工作固定選模。
4. 修正 Mac 原生 uv 啟動與 readiness，完全排除 Docker/Ollama 依賴。
5. 以離線 ASR integration 與一個真實的 Mac 原生完整工作流證明結果，再跑 NVIDIA regression。

## SOURCE_OF_TRUTH

- **使用者目標與限制**：本任務最新對話；較新的釐清覆蓋較早假設，尤其是「Mac 使用 LM Studio，不使用 Ollama」、「LLM 與 ASR model 是兩類模型」、「Mac 不使用 Docker」及「`yt_down_txt` 只能讀取」。
- **現況行為**：`backend/core`、`backend/services`、`backend/workers`、啟動腳本與相鄰 tests 的目前實作。
- **依賴與執行環境**：`pyproject.toml`、`uv.lock`、本機 Python/LM Studio/MLX 狀態，以及唯讀檢視取得的共享 Hugging Face cache 狀態。
- **外部契約**：
  - [LM Studio Models API](https://lmstudio.ai/docs/developer/rest/list)
  - [LM Studio REST quickstart](https://lmstudio.ai/docs/developer/rest/quickstart)
  - [LM Studio unified MLX engine](https://lmstudio.ai/blog/unified-mlx-engine)
  - [Apple MLX Whisper](https://github.com/ml-explore/mlx-examples/blob/main/whisper/README.md)
  - [CTranslate2 hardware support](https://opennmt.net/CTranslate2/hardware_support.html)
  - [MediaTek Breeze-ASR-26](https://huggingface.co/MediaTek-Research/Breeze-ASR-26)

## VERIFIED_CURRENT_STATE

- `[VERIFIED]` Repository 位於 `/Users/hsiaojohnny/dev/convert`，branch `main`，anchor HEAD 如 META，落檔前 working tree clean，`uv lock --check` 已通過。
- `[VERIFIED]` `device_detector` 可偵測 MPS，但 `TranscriptionService._detect_runtime()` 明確把 MPS 降級為 CPU；現有 Mac ASR 尚未真正加速。
- `[VERIFIED]` ASR resolver 只接受 `transformers` 與 `faster_whisper`；現有 subprocess isolation 已能在工作結束時釋放模型程序記憶體。
- `[VERIFIED]` CTranslate2 預建 GPU backend 僅支援 NVIDIA；Apple ARM64 上的 faster-whisper 不是 Metal GPU 解法。
- `[VERIFIED]` `config.macos.yaml` 與 macOS scripts 含過時的 MPS/Ollama/模型名稱及 conda/project-root 假設，與目前程式讀取的設定鍵不一致。
- `[VERIFIED]` `summarization` 目前先探測 Ollama 再探測 LM Studio，且 LM Studio 使用同步 OpenAI client；這不符合 Mac 的 provider 意圖並會阻塞 async event loop。
- `[VERIFIED]` `settings.LMSTUDIO_MODEL` 目前預設為固定模型名稱；Mac native 的 `LMSTUDIO_BASE_URL` 預設也不是 `127.0.0.1`。
- `[VERIFIED]` 目前 task processor 已把摘要失敗局部降級成「保留逐字稿／輸出僅逐字稿」，因此不需要新增 task state machine 或 retry API。
- `[VERIFIED]` Mac 有 LM Studio app/CLI，但目前 server 未啟動且沒有 loaded model；這是驗收前置狀態，不是產品程式缺陷。
- `[VERIFIED]` 可重用的 `doggy8088/Breeze-ASR-26-MLX` 約 2.9GB，revision `619860a64925c0f0dfecdbb5f8d9a2da2df1bc12` 已位於標準 Hugging Face shared cache。
- `[VERIFIED]` `yt_down_txt` 的 Python 3.12 環境曾使用 `mlx-whisper 0.4.3` 與 MLX 0.32；該事實只作相容性證據，不形成 runtime coupling。
- `[VERIFIED]` `convert` 目前直接依賴 `huggingface_hub`，可在不增加另一套 cache library 的前提下解析 snapshot。

## CURRENT_FLOW

1. Upload 建立 task，task processor 計算 transcript cache signature。
2. ASR 透過 worker/subprocess 載入 Transformers 或 faster-whisper；MPS 被降級至 CPU。
3. 逐字稿完成後立即保存；摘要失敗仍可輸出逐字稿。
4. Local summarization 自動探測 Ollama 後才探測 LM Studio，LM Studio model 來自硬編碼 default/config。
5. macOS scripts 宣稱 MLX/MPS，但實際包含 Ollama pull、conda 路徑與不正確 project root，不能作為可靠 native entrypoint。

## REQUIREMENTS_AND_CRITICALITY

| ID | Requirement | Trace | Criticality | 可阻擋 core？ | 理由 |
|---|---|---|---|---|---|
| `REQ-01` | Darwin ARM64 的 `ASR_BACKEND=auto` 必須選擇 `mlx_whisper` 並回報 MLX/Metal | PRIMARY_OUTCOME | CORE | 是 | 沒有 Apple 加速就沒有達成 Mac 替代 RTX 的核心目的 |
| `REQ-02` | 以 shared HF cache 重用 Breeze-ASR-26-MLX，支援 repo/revision 或本機唯讀路徑 override | PRIMARY_OUTCOME, MNB-01/02 | CORE | 是 | 無可用權重就不能轉錄；共享 cache 避免重複空間與跨專案耦合 |
| `REQ-03` | Mac local LLM provider 固定為 LM Studio，不探測或 fallback 到 Ollama | PRIMARY_OUTCOME, MNB-03 | CORE | 摘要階段是 | 選錯 provider 會違反明確使用者意圖 |
| `REQ-04` | 依 LM Studio loaded instances 動態且確定性地選模；零／多個時明確錯誤 | PRIMARY_OUTCOME, MNB-03 | CORE | 僅摘要 | 任意模型選擇會使結果不可重現且可能使用錯誤模型 |
| `REQ-05` | Mac 以 uv/Python 3.12 原生啟動，完全不要求 Docker | PRIMARY_OUTCOME | CORE | 是 | Docker 不在使用者的 Mac 執行方式內 |
| `REQ-06` | NVIDIA/CUDA、Transformers、faster-whisper 及非 Mac provider 行為維持相容 | MNB-04 | CORE | 是 | 雙平台支援不能以破壞 NVIDIA 為代價 |
| `REQ-07` | LM Studio 失敗維持局部降級，保留逐字稿及可操作錯誤 | MNB-05 | CORE | 否 | LLM 失敗不應擴散並使已完成 ASR 無效 |
| `REQ-08` | Health/UI 顯示 accelerator、ASR backend/model 與 LM Studio readiness | SUCCESS_EVIDENCE | SUPPORTING | 否 | 改善可驗證性與操作，但不決定轉錄本身是否有效 |
| `REQ-09` | 修正 Mac setup/verify scripts 的 conda、Ollama、MPS 與路徑假設 | REQ-05 | SUPPORTING | 僅 native 啟動是 | 提供可重現入口並移除錯誤操作指示 |
| `NFR-01` | Mac 大型推論循序執行，ASR 保持 subprocess 隔離 | 48GB unified-memory 約束 | CORE | 是 | 限制同時駐留與資源洩漏風險 |
| `NFR-02` | LM Studio 網路呼叫採 async、具 timeout 與有限 transient retry | 服務可靠性 | SUPPORTING | 否 | 避免阻塞 event loop；決定性錯誤不應重試 |
| `NFR-03` | 所有 model/backend/revision 納入 cache signature | 正確性 | CORE | 是 | 防止沿用不相容逐字稿快取 |
| `NFR-04` | 對 `yt_down_txt` 保持零寫入與零 runtime coupling | MNB-01/02 | CORE | 是 | 使用者明確資料邊界 |

## DECISION_CONTRIBUTION_MATRIX

| Element | Goal/decision contribution | Criticality | Influence/weight | Global veto? | Missing/failure behavior | Rationale |
|---|---|---|---|---|---|---|
| MLX runtime package | 在 Mac 執行 Metal ASR | CORE | N/A | 僅 ASR 是 | `ASR_BACKEND_UNAVAILABLE`，不偽裝成加速成功 | 無它無法完成 Mac ASR |
| Breeze-ASR-26-MLX snapshot | 產生逐字稿 | CORE | N/A | 僅 ASR 是 | offline cache miss 回 `ASR_MODEL_UNAVAILABLE`；online 模式寫入標準 HF cache | 無模型時 ASR 決策未定義 |
| LM Studio server | 產生摘要 | CORE | N/A | 否 | 服務及 ASR 可用；摘要局部失敗 | 摘要不可用不使逐字稿失效 |
| 唯一 loaded LLM | 決定摘要模型 | CORE | N/A | 否 | 零／多個時明確拒絕該次摘要 | 任意選擇無法保證意圖與重現性 |
| `LMSTUDIO_MODEL` override | 使用者明確消除多模型歧義 | SUPPORTING | 完全覆蓋自動選擇 | 否 | 未設定時使用唯一 loaded 規則；不匹配時摘要失敗 | 不是必要設定，也不得變成硬編碼 |
| LM Studio context length | 規劃摘要 chunk budget | SUPPORTING | 上限約束 | 否 | 無法取得時使用既有保守 token budget 並標示未知 | 影響效率／溢位風險，不影響 ASR 有效性 |
| Health/UI 新欄位 | 操作與驗收可觀測性 | SUPPORTING | N/A | 否 | API 核心功能繼續；readiness 顯示 degraded | 不應因顯示層故障阻擋推論 |
| Docker | 無 Mac 目標貢獻 | OOS | N/A | 否 | Mac 完全忽略 | 使用者明確不需要 |
| `yt_down_txt` 程式／venv | 僅作規劃證據 | OOS | N/A | 否 | runtime 不引用 | 避免跨專案寫入與脆弱耦合 |

### GLOBAL_GATES_AND_RATIONALE

- **唯一全域啟動 gate**：Web/backend 自身必要依賴可載入。LM Studio readiness 不得成為全域 gate，因為服務仍能提供 upload、ASR、逐字稿與健康診斷。
- **ASR 工作 gate**：所選 backend 與 model 必須可載入；局部降級不足，因為沒有逐字稿就無法完成任何後續輸出。
- **摘要工作 gate**：LM Studio 必須可連線且選出唯一 loaded LLM；只阻擋摘要，因為任意挑選會讓摘要的模型身份與使用者意圖不成立。

## CONSTRAINTS_NON_GOALS_AND_OUT_OF_SCOPE

- `OOS-01`：Mac Dockerfile、Compose、container networking 與 image optimization。
- `OOS-02`：LM Studio SDK、server control、下載／載入／卸載模型及模型管理 UI。
- `OOS-03`：Ollama on Mac；不得因本機 Ollama process 存在而選中它。
- `OOS-04`：修改或安裝任何內容到 `/Users/hsiaojohnny/dev/yt_down_txt`。
- `OOS-05`：ASR 模型訓練、重新量化、轉換及本次全面品質調校。
- `OOS-06`：移除 NVIDIA Docker 或現有 CUDA/CPU fallback。
- 依賴以 `uv` 與 `pyproject.toml` 為主，`requirements.txt` 只依 repository 現有 Docker 相容約定同步必要 marker；lockfile 必須由 uv 產生，不手改。
- Python 3.12 是 Mac canonical runtime；先用 `.python-version` 固定，不主動收窄 `requires-python >=3.11`，除非 lock/install 證據證明必要並觸發 plan review。

## SEMANTIC_CONTRACT

### 不變契約

- Upload、task progress、transcript cache、逐字稿保存、摘要失敗後輸出僅逐字稿及 NVIDIA backend 的公開行為維持不變。
- ASR subprocess 仍是一個工作一個隔離程序；呼叫端接收統一 `DetailedTranscriptionResult`。
- 明確設定 `ASR_BACKEND=transformers|faster_whisper` 時，不因平台自動改寫。
- 明確設定非 Mac `LOCAL_LLM_PROVIDER=ollama` 時，保留既有 Ollama 行為與資源管理。

### 改變契約

- `ASR_BACKEND=auto` 在 Darwin ARM64 的結果從 CPU/Transformers 路徑改為 `mlx_whisper`/MLX-Metal。
- `LOCAL_LLM_PROVIDER=auto` 在 Darwin ARM64 必然解析為 `lmstudio`；其他平台保留既有優先順序。
- `LMSTUDIO_MODEL` 從具硬編碼 default 的必填字串改為 optional explicit override。
- LM Studio 模型於每次摘要工作開始時解析並固定；工作中不得切換。
- LM Studio 零個或多個 loaded LLM 是穩定、可診斷的摘要錯誤，不再由探測順序或 default 名稱掩蓋。
- Health 保留既有欄位並 additive 增加 accelerator/backend/provider/model readiness；不得移除或重解釋既有 consumer 依賴欄位。

### 穩定錯誤語意

- `ASR_BACKEND_UNAVAILABLE`：平台選定 backend 缺少 runtime package 或硬體能力。
- `ASR_MODEL_UNAVAILABLE`：repo/revision/path 無法在目前 online/offline 政策下解析。
- `LMSTUDIO_UNREACHABLE`：server 無法連線或 timeout。
- `LMSTUDIO_NO_LOADED_LLM`：排除 embedding 後沒有 loaded LLM instance。
- `LMSTUDIO_MULTIPLE_LOADED_LLMS`：未提供 override 且 loaded LLM instance 超過一個。
- `LMSTUDIO_MODEL_NOT_LOADED`：override 無法唯一匹配已載入 instance。

錯誤碼須透過既有 exception/description 管道落到 task summary error 與 health detail；本次不新增 task state 或公開 retry API。

## DECISIONS

### `DEC-01` Mac ASR 使用 mlx-whisper，而非 faster-whisper 或現有 Transformers/MPS

- **證據／限制**：CTranslate2 Apple ARM64 無 GPU backend；現有 ASR 明確把 MPS 降級 CPU；`mlx-whisper` 與既有權重已有本機相容性證據。
- **選擇**：新增第三個 ASR adapter，直接使用 MLX/Metal。
- **替代方案**：Transformers `device=mps` 可作明確手動 fallback，但不是 `auto` 預設；其 operation coverage 與目前 pipeline 尚未驗證。

### `DEC-02` 重用 shared HF cache，不引用 `yt_down_txt` model directory

- **證據／限制**：Breeze-ASR-26-MLX 已在標準 cache；使用者要求節省空間且禁止修改另一專案。
- **選擇**：用 `huggingface_hub.snapshot_download(repo_id, revision=...)` 解析 cache，再把 snapshot path 傳給 MLX adapter；offline 時設定 `local_files_only`。
- **替代方案**：直接指向 `yt_down_txt/models` 雖可讀取，但會造成機器特定耦合且存在第三方套件寫入鄰近路徑的風險，因此不作預設或文件建議。

### `DEC-03` LM Studio 用現有 HTTP/OpenAI-compatible stack，不新增 LM Studio SDK

- **證據／限制**：現有依賴已有 `httpx` 與 `openai`；LM Studio 提供 native models REST 與 OpenAI-compatible generation。
- **選擇**：`httpx.AsyncClient` 查 `/api/v1/models`，`AsyncOpenAI` 執行 chat completion，集中在現有 summarization service/provider 邊界。
- **替代方案**：LM Studio SDK 可提供更多管理功能，但這些功能屬 OOS，新增依賴無法通過 deletion test。

### `DEC-04` 動態選模採「唯一 loaded instance，否則 fail explicit」

- **證據／限制**：使用者頻繁換模型且已明確選擇歧義時失敗，不接受任意選擇。
- **選擇**：排除 embedding；override 唯一匹配優先；否則 loaded LLM count 必須等於一；選擇結果綁定整次摘要工作。
- **替代方案**：第一個、最新載入或自動載入都會引入不可預測 side effect，拒絕採用。

### `DEC-05` Mac 原生 uv 執行，不以 Docker 或 conda 作 fallback

- **證據／限制**：使用者明確不需要 Mac Docker；現有 conda 路徑不存在且 scripts project-root 計算錯誤。
- **選擇**：Python 3.12 + `.python-version` + `uv sync --frozen` + repo-root-aware `uv run`；啟動不自動安裝或下載。
- **替代方案**：保留舊 scripts 只改模型名稱會繼續留下錯誤 runtime 與 provider 假設。

### `DEC-06` 大型模型循序執行但不主動卸載 LM Studio

- **證據／限制**：48GB unified memory 需控制峰值；ASR subprocess exit 已能釋放 MLX 狀態；LM Studio lifecycle 由使用者管理。
- **選擇**：ASR 完成且 subprocess 結束後才進入摘要；不呼叫 LM Studio unload/warm-up。
- **替代方案**：自動 unload/reload 會增加 side effect、延遲與模型識別風險，且超出使用者授權。

## COUPLING_AND_FAILURE_CONTAINMENT

- ASR runtime detection 只決定 ASR；LM Studio readiness 不參與 device detector 的全域可用性。
- MLX adapter 遵守現有 transcription result boundary，避免讓 task processor 知道 MLX 特定資料結構。
- Provider selection 與 loaded-model selection 集中在 summarization boundary，避免散落到 task/UI/start scripts。
- LM Studio 失敗沿用既有 `summary_failed` 降級：逐字稿已先落檔，DOCX 明確標示僅逐字稿。
- Health/UI 只消費 normalized status，不直接探測套件、模型目錄或外部 process。
- Mac dependencies 使用平台 marker，避免改變非 Darwin ARM64 的套件集合。
- `yt_down_txt` 只存在於 evidence/acceptance safety check，不出現在產品 runtime config/default。

## COMPLEXITY_BUDGET

| 新增／調整項目 | 支付的 CORE outcome／風險 | Deletion test |
|---|---|---|
| 一個 `mlx_whisper` ASR adapter | REQ-01/02 Apple 加速與統一輸出 | 刪除後 Mac 只剩 CPU，PRIMARY_OUTCOME 失敗 |
| 一個 MLX cache resolver branch | NFR-03、節省空間及 revision 可重現 | 刪除後可能重複下載或使用不明 revision |
| 一個 local-provider setting | REQ-03 跨平台 provider 意圖 | 刪除後 Mac 仍可能選到 Ollama |
| 一個 LM Studio loaded-model selector | REQ-04 動態且確定性選模 | 刪除後必須硬編碼或任意選模型 |
| Additive readiness fields | REQ-08 可操作性與驗收證據 | 刪除後 CORE 仍可跑，但難以判斷是否真用 MLX；故為 SUPPORTING |
| 平台 marker dependency 與 Python pin | REQ-01/05 可重現原生環境 | 刪除後 Mac 安裝結果不可靠 |

不新增 provider plugin framework、模型 registry、持久化 model selection、scheduler、Docker 分支或新 task states。

## TARGET_CONTRACT

### 設定

- `LOCAL_LLM_PROVIDER=auto|lmstudio|ollama`
  - Darwin ARM64 `auto` → `lmstudio`。
  - 其他平台 `auto` 維持目前 Ollama 優先、LM Studio 次之的相容策略。
- `LMSTUDIO_BASE_URL`
  - native Mac default：`http://127.0.0.1:1234`。
  - normalization 同時接受有／無 `/v1` 的舊值；models API 使用 normalized root，OpenAI client 使用 `${root}/v1`。
  - `host.docker.internal` 只存在於實際 container env。
- `LMSTUDIO_MODEL: Optional[str] = None`；空字串正規化成 `None`。
- `ASR_BACKEND=auto|transformers|faster_whisper|mlx_whisper`。
- 既有 ASR model/revision 設定保持 public name 與 precedence；Darwin ARM64 `auto` 在未 override 時使用 `doggy8088/Breeze-ASR-26-MLX@619860a64925c0f0dfecdbb5f8d9a2da2df1bc12`。

### LM Studio 選模

1. GET normalized root 的 `/api/v1/models`。
2. 僅取 `type=llm` 且有 loaded instance 的項目，embedding 永久排除。
3. 有 `LMSTUDIO_MODEL` 時，只接受對 model key 或 loaded instance identifier 的唯一 exact match；不觸發 JIT load。
4. 無 override 時，loaded instance count 必須恰為一。
5. 回傳 immutable selection：provider、chat model identifier、context length、inventory timestamp；同一次摘要的所有 chunk/refinement call 共用。
6. context length 存在時作為既有 chunk budget 的硬上限；不存在時使用既有保守設定，不推測數字。

### ASR

- `infer_asr_backend()` 接受 `mlx_whisper`，Darwin ARM64 auto 選 MLX；明確 backend 永遠優先。
- MLX adapter 接受 snapshot/local path、language、initial prompt、timestamps 等現有 normalized options，輸出現有 text/chunks/duration/backend contract。
- backend metadata 使用 `mlx_whisper`；accelerator 使用 `mlx-metal`，不得使用含義不同的 `mps`。
- default repo cache miss：online 模式由 Hugging Face 寫入標準 cache；`HF_HUB_OFFLINE=1` 時 fail explicit，不寫到 project model directory。
- cache signature 至少包含 backend、model identifier、revision 及影響文字輸出的關鍵設定。

### Health/API/UI

- 保留既有 top-level health/device fields。
- 在既有 `device_info`／local model health 結構中 additive 增加：
  - `accelerator: cuda | mlx-metal | mps | cpu`
  - `asr_backend`
  - `asr_model.identifier`、`asr_model.revision`
  - `llm.provider`、`server_reachable`、`selection_status`、`loaded_llm_count`、`selected_model`、`context_length`
- 不回傳絕對 model/cache path。
- UI 顯示 Apple MLX/Metal 與 LM Studio 的 actionable zero/multiple/unreachable 狀態；顯示失敗不得阻擋 backend。

### 原生啟動

- canonical setup：`uv sync --frozen`；canonical start：`uv run uvicorn backend.main:app --host 0.0.0.0 --port 9527`。
- startup scripts 從 script location 解析 repo root，不依賴呼叫者 cwd；不得自動 `pip install`、`ollama pull`、啟動 Docker 或修改 LM Studio。
- `verify_env` 依 effective platform/backend 判定 critical dependencies，不把未使用的 faster-whisper 或 Ollama 當 Mac global blocker。

## CHANGE_MAP

- **Runtime/config boundary**：`backend/core/config.py`、`backend/core/platform_config.py`、`backend/core/asr_model_resolver.py`、`backend/services/device_detector.py`；加入平台預設、model/provider 正規化與可觀測 metadata。
- **ASR boundary**：`backend/services/transcription.py`、既有 subprocess/worker payload 與相鄰 tests；加入 MLX load/transcribe/normalize，但保持呼叫端 contract。
- **LLM boundary**：`backend/services/summarization.py` 與 task processor 相鄰 tests；使用 async LM Studio discovery/generation，保留摘要局部降級。
- **Environment/operations**：`pyproject.toml`、由 uv 更新的 `uv.lock`、必要時同步 Docker 用 requirements、Mac native scripts、`scripts/verify_env.py` 與 `config.macos.yaml`。
- **Observability**：health API 與既有 frontend status consumer；只做 additive schema/UI 變更。
- **不得變更**：`/Users/hsiaojohnny/dev/yt_down_txt/**`。

## CRITICAL_PATH

`平台設定 → MLX adapter/cache reuse → LM Studio deterministic selection → native Mac startup → Mac offline ASR integration → Mac full E2E → NVIDIA regression`

CORE 驗收未通過前，不優先投入 UI polish 或真實會議品質統計。

## IMPLEMENTATION_WAVES

### `WAVE-01` 鎖定設定與 LM Studio 語意契約

- **Scope**：config/platform settings、summarization provider/model selection、LM Studio client 邊界及 focused tests。
- **Serves**：REQ-03、REQ-04、REQ-07、NFR-02。
- **Preconditions**：確認 LM Studio 目前 API response fixture；不得要求 server 於 unit tests 真實啟動。
- **Change intent**：新增 provider enum/normalization、移除 hardcoded LLM default、建立 loaded-instance selector、改用 async generation；保留 Ollama 非 Mac 路徑。
- **Focused verification**：zero/one/multiple/embedding/override fixtures、Mac never-Ollama assertion、async timeout/retry、summary failure preserves transcript contract。
- **Exit criteria**：所有 LM Studio 決策場景有 deterministic result/error；未新增 SDK；現有 Ollama tests 不退化。
- **Rollback**：移除 provider override/selector 並恢復原 client，不涉及資料 migration；若 reviewer 改變選模語意，先 replan。

### `WAVE-02` 實作 MLX ASR 與 shared-cache 重用

- **Scope**：ASR resolver、transcription adapter、subprocess payload/result、dependency manifests/lock 與 focused tests。
- **Serves**：REQ-01、REQ-02、REQ-06、NFR-01、NFR-03、NFR-04。
- **Preconditions**：以唯讀方式確認 default snapshot/revision 可由 `huggingface_hub` offline 解析；若不成立則停止並 replan，不得修改 `yt_down_txt`。
- **Change intent**：平台 marker 加入 mlx-whisper；Darwin auto 選 MLX；將 MLX output normalize 成現有 result；cache signature 加 backend/model/revision。
- **Focused verification**：mocked adapter unit tests、Darwin/NVIDIA selection tests、`HF_HUB_OFFLINE=1` local snapshot integration、subprocess exit/error propagation。
- **Exit criteria**：Mac integration 實際回報 `mlx_whisper`/`mlx-metal` 並產生非空逐字稿；沒有 project-local model copy；CUDA tests 維持通過。
- **Rollback**：明確 `ASR_BACKEND=transformers` 可回到既有路徑；MLX dependency marker 不影響非 Mac。

### `WAVE-03` 修復 Mac 原生操作與可觀測性

- **Scope**：Mac scripts、`.python-version`、verify_env、macOS example config、health API/UI 與 tests。
- **Serves**：REQ-05、REQ-08、REQ-09、MNB-06。
- **Preconditions**：WAVE-01/02 的 normalized status 已穩定，避免 UI 反向定義語意。
- **Change intent**：移除 conda/Ollama/Docker/錯誤路徑與 MPS 假宣稱；原生 uv start；additive health fields/actionable UI。
- **Focused verification**：shell syntax、repo-root invocation、platform-aware verify_env fixtures、health schema compatibility、frontend status rendering。
- **Exit criteria**：Mac setup/start 不呼叫 Docker/Ollama、不自動安裝或下載；health 能分辨 MLX、CUDA、CPU 與 LM Studio selection errors。
- **Rollback**：scripts/health additive changes 可獨立回復，不影響 ASR/LLM 核心 adapter。

### `WAVE-04` 完整驗收與相容性收斂

- **Scope**：Mac native integration/E2E、完整 pytest、dependency consistency、NVIDIA contract regression、文件與 final diff。
- **Serves**：全部 CORE REQ 與 SUCCESS_EVIDENCE。
- **Preconditions**：LM Studio server 由使用者啟動且恰載入一個 LLM；實作者不得自動改變該外部狀態。
- **Change intent**：證明完整使用者旅程、離線模型重用、失敗降級與雙平台相容，而非增加功能。
- **Focused verification**：見 TEST_AND_ACCEPTANCE。
- **Exit criteria**：Mac E2E PASS、required test suite PASS、`yt_down_txt` 狀態與基準一致、diff 僅含核准範圍。
- **Rollback**：若 MLX 品質或記憶體風險不符，保留明確 Transformers fallback 並進入 replan；不可靜默改預設模型。

## TEST_AND_ACCEPTANCE

### Requirement-to-evidence mapping

| Requirement | 最低充分證據 |
|---|---|
| REQ-01 | Darwin ARM64 selection unit test + 實際 Mac MLX transcription 回報 backend/accelerator |
| REQ-02 | `HF_HUB_OFFLINE=1` 使用 pinned snapshot 完成短音檔轉錄，且無第二份權重 |
| REQ-03 | provider tests 證明 Mac auto 不探測 Ollama；完整 E2E 僅 LM Studio |
| REQ-04 | zero/one/multiple/override/embedding contract tests + E2E 記錄實際 loaded model identifier |
| REQ-05 | 未使用 Docker 的 fresh native uv setup/start 與完整 journey |
| REQ-06 | 現有 ASR/device/summarization tests + mocked NVIDIA/CUDA contract；RTX 不可用時不得宣稱硬體 E2E |
| REQ-07 | LM Studio unreachable/ambiguous integration 證明 task 保留 transcript 並標示 summary failure |
| REQ-08 | health response contract 與 frontend component/status test |
| REQ-09 | scripts shell syntax、從非 repo cwd 啟動的 path test、platform-aware verify_env test |
| NFR-01 | task sequence/subprocess test；ASR worker exit 後無殘留 child process |
| NFR-02 | async mocked latency/timeout/retry test，決定性 4xx/selection error 不重試 |
| NFR-03 | 不同 backend/model/revision 產生不同 cache signature |
| NFR-04 | 實作前後 `yt_down_txt` Git 狀態一致，產品碼無其絕對路徑或 `.venv` 引用 |

### Focused and broad commands

實作者依實際新增 test module 名稱執行相鄰 focused tests，至少涵蓋：

```bash
uv lock --check
uv run pytest tests/test_device_detector.py tests/test_transcription_service.py tests/test_asr_subprocess.py -q
uv run pytest <LM-Studio-provider-focused-tests> -q
HF_HUB_OFFLINE=1 uv run pytest <MLX-cache-integration-test> -q
uv run pytest tests/ -q
uv pip check
git diff --check
```

不得把 mock-only 測試稱為 Apple hardware E2E。

### Mac native integration

1. 以 macOS `say` 在系統 temp directory 建立固定短語音，再經現有 ffmpeg 前處理；不把 fixture 寫進 `yt_down_txt`。
2. 設定 `HF_HUB_OFFLINE=1`，透過真實 MLX adapter/subprocess 轉錄。
3. 驗證逐字稿非空且包含固定關鍵詞、backend=`mlx_whisper`、accelerator=`mlx-metal`、snapshot revision 正確。
4. 驗證 cache/model directory 沒有 project-local duplicate，`yt_down_txt` 狀態未變。

### LM Studio degraded scenarios

- Server off → `LMSTUDIO_UNREACHABLE`；ASR/逐字稿仍完成。
- Server on、零 loaded LLM → `LMSTUDIO_NO_LOADED_LLM`；不得 JIT load。
- 多 loaded LLM、無 override → `LMSTUDIO_MULTIPLE_LOADED_LLMS` 且提供候選。
- 多 loaded LLM、有效 override → 使用唯一匹配 instance。
- 工作中 model 被卸載 → 該摘要失敗，不切換另一個 model；逐字稿保留。

### True Mac E2E

前置：使用者手動啟動 LM Studio server 並載入恰一個任意 LLM。實作者只讀取狀態，不下載、載入或卸載模型。

1. 以原生 uv 啟動 backend/frontend，不執行任何 Docker command。
2. 透過公開 upload API/UI 提交短語音。
3. 等待 task 完成，下載逐字稿與會議紀錄輸出。
4. 驗證逐字稿、摘要、DOCX/export 均存在且非空。
5. 驗證 task/health 記錄的 LLM identifier 等於 LM Studio 當時唯一 loaded model。
6. 驗證 log/spy 無 Ollama request、無新模型下載、無 `yt_down_txt` 寫入。

### NVIDIA acceptance boundary

目前 RTX 4090 不可用，因此本 task 的 Stage 05 不得宣稱 NVIDIA hardware E2E。現階段以現有 CUDA backend contract tests、dependency/compose validation 與 static regression 保護；未來 NVIDIA 主機恢復後，將真實 GPU smoke test列為發布前 follow-up，而不阻擋本次 Mac 核心成果。

## MIGRATION_COMPATIBILITY_ROLLBACK

- 無資料 schema、database 或既有 transcript migration。
- Health/API 只 additive；現有 consumer 欄位保持原意。
- Transcript cache signature 更新後，舊 cache 可保留但不得在 backend/model/revision 不匹配時誤命中。
- `LMSTUDIO_MODEL` 舊硬編碼 default 被移除是刻意的 config semantic change；部署若需要固定模型必須顯式設定且該 model 已 loaded。
- Mac 可用 `ASR_BACKEND=transformers` 作明確回復；不得在 `auto` 下靜默退回 CPU 並仍宣稱 Apple 加速。
- 非 Mac 可用 `LOCAL_LLM_PROVIDER=ollama` 保留現有 provider；NVIDIA Compose 行為不因 Mac native setup 改變。
- 若 lockfile 的 Apple marker 影響非 Mac resolution，先回復 dependency wave 並 replan，不以全平台安裝 MLX 解決。

## DEFERRED_OR_BEST_EFFORT

- 使用代表性真實會議錄音計算 CER/WER 與與 NVIDIA 結果比較；現有 synthetic Taigi evidence 僅證明可行性。
- LM Studio GPU offload、context/KV cache tuning 與長會議效能 benchmark；這些由 LM Studio runtime 管理。
- NVIDIA 主機恢復後的真實 CUDA E2E。
- 更豐富的模型選擇 UI、model lifecycle 控制與摘要獨立重試 API。

## RISKS

1. **轉換模型品質**：第三方 MLX conversion 與官方 Transformers 權重可能有輸出差異；以 pinned revision、短語音 E2E 與後續真實樣本檢查控制，不以無關模型 fallback 掩蓋。
2. **Unified memory 壓力**：LM Studio loaded LLM、context/KV cache 與 MLX ASR 共用 48GB；以循序推論和 ASR subprocess exit 控制，避免新增自動 unload side effect。
3. **LM Studio API shape/version**：本機版本的 models payload 可能與文件細節不同；WAVE-01 先建立真實 read-only fixture，未知欄位 fail safely。
4. **跨平台 lock resolution**：MLX dependency 必須嚴格標記 Darwin ARM64；錯誤 marker 可能影響 Windows/Linux install。
5. **Mac scripts 歷史漂移**：多份 root/mac scripts 有重疊過時邏輯；只建立一個 canonical native path，其餘轉為薄 wrapper 或明確 deprecated，避免再次分叉。

## BLOCKING_UNKNOWNS

- 無。核心設計與使用者偏好已確認；LM Studio server/model 目前未啟動是 Stage 05 外部前置條件，不阻擋 Stage 02 plan review 或 Stage 04 實作。

## NON_BLOCKING_UNKNOWNS

- LM Studio 真實 `/api/v1/models` payload 中 model key 與 loaded instance identifier 的精確欄位組合；WAVE-01 用本機 read-only response 固化 fixture，不改變「唯一 loaded LLM」決策。
- 長會議在 48GB unified memory 下的最佳 LM Studio context 設定；使用實際 loaded context 上限及既有保守 chunk budget，效能調優延後。
- RTX 4090 真實硬體恢復日期；不影響 Mac E2E，但 NVIDIA hardware smoke 必須誠實列為未執行。

## DEAD_ENDS

- **Mac faster-whisper GPU**：CTranslate2 Apple ARM64 沒有預建 GPU backend，無法滿足 Apple 加速。
- **沿用現有 MPS detection**：ASR 實作會降級 CPU，健康資訊會造成錯誤信心。
- **在 Mac 先探測 Ollama**：本機 Ollama process 即使存在也不是使用者指定入口。
- **硬編碼 LM Studio model**：與頻繁換模需求衝突，且可能觸發錯誤/JIT load。
- **直接共用 `yt_down_txt/.venv` 或 import 其程式碼**：跨專案版本與寫入風險高；shared HF cache 已提供更小耦合方案。
- **Mac Docker**：使用者明確排除，且會引入 host networking/Metal passthrough 的無效複雜度。

## RISKIEST_ASSUMPTIONS

1. 已 cache 的 Breeze-ASR-26-MLX snapshot 能由 `mlx-whisper` 在 `convert` 的 Python 3.12 環境完全離線載入。
2. LM Studio 本機版本能以官方 `/api/v1/models` 提供足以區分 LLM、embedding 與 loaded instances 的資料。
3. 現有 task processor 的逐字稿先保存／摘要局部失敗契約在 provider refactor 後仍可原樣維持。
4. 平台 marker 可讓 MLX dependencies 不進入 NVIDIA/Windows 安裝圖。
5. 循序執行足以在 48GB unified memory 下避免常態性記憶體壓力；若實證不成立需 replan，而不是偷偷管理 LM Studio lifecycle。

## DEFINITION_OF_DONE

- 所有 CORE requirements 有實際對應證據，Mac native true E2E 完成。
- `ASR_BACKEND=auto` 在 Mac 使用 MLX/Metal，且 offline 命中既有 pinned model snapshot。
- Mac `LOCAL_LLM_PROVIDER=auto` 只使用 LM Studio；LLM model 動態選擇且整個工作固定。
- zero/multiple/unreachable LM Studio scenarios 按契約局部降級並保留逐字稿。
- Mac setup/start 不需要 Docker、conda 或 Ollama，且不自動管理模型。
- NVIDIA focused/full regressions 通過；未執行的 RTX hardware E2E 被明確標示。
- dependencies/lock 一致，health changes 向後相容，最終 diff 無無關修改。
- `/Users/hsiaojohnny/dev/yt_down_txt` 前後狀態完全一致，產品程式不存在對其路徑或環境的必要依賴。
- Stage 02 對本 revision 回傳 `PLAN_APPROVED` 後，才能產生 Stage 03 handoff；任何語意契約變更都必須回到同一 TASK_ID 的新 plan revision。

## HANDOFF_HINTS

- Stage 02 必須 top-down 挑戰：Mac auto provider 是否確實排除 Ollama、LM Studio ambiguity 是否只局部阻擋、shared-cache reuse 是否真正不耦合 `yt_down_txt`，以及 MLX dependency marker 是否足夠隔離 NVIDIA。
- Reviewer 應特別核對 `DEC-02`、`DEC-04`、`GLOBAL_GATES_AND_RATIONALE` 與 NVIDIA compatibility，不能只檢查檔案清單。
- Stage 03 僅在 revision/hash 符合最新 `PLAN_APPROVED` 後建立 handoff，並保留以下 stop conditions：需要修改 `yt_down_txt`、LM Studio API 無法判斷 loaded instances、offline snapshot 不可解析、平台 marker 破壞非 Mac install、或實作要求改變 fallback/gating/error 語意。
- Stage 04 應依 WAVE-01 → WAVE-04 執行，先完成 CORE path；不得在 MLX/LM Studio 核心未通過時先投入 UI polish。
