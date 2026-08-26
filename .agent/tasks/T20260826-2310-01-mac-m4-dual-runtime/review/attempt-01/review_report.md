# Plan Review Report

## REVIEW_METADATA
- TASK_ID: T20260826-2310-01-mac-m4-dual-runtime
- REVIEW_ATTEMPT: 01
- REVIEWED_PLAN_REVISION: 1
- REVIEWED_PLAN_SHA256: 20ba410c1a3ed5a87b8b5af92b93512550d831fa4279981bf402534a74b54927
- PLAN_SNAPSHOT_PATH: .agent/tasks/T20260826-2310-01-mac-m4-dual-runtime/review/attempt-01/plan_snapshot.md
- Repository anchor observed: HEAD `9bc3081365713c5e53deaf3a1fb233db12e61324`（plan.md 落檔 commit），working tree clean
- Reviewer runtime/model: deepseek-v4-pro:0813（與 Planner 不同 runtime，符合獨立審查偏好）

## OWNER_VERDICT

**目標**：讓 `convert` 在 48GB Mac M4 Pro 上以原生程序完成語音轉錄（Apple MLX/Metal 加速既有 Breeze ASR 權重）與摘要（LM Studio 動態採用唯一已載入 LLM），同時不破壞既有 NVIDIA/CUDA 路徑。

**真正必要**：Mac ASR 用 MLX/Metal、Mac LLM 用 LM Studio、Mac 不用 Docker、NVIDIA 不退化。這四項是 CORE，缺一即無法達成核心目的。

**可選／延後**：健康狀態與前端顯示、原生啟動腳本、真實會議品質比較（CER/WER）屬可運維性與信心提升，不取代 CORE E2E 證據。

**全域阻擋**：唯一全域啟動 gate 是「backend 自身必要依賴可載入」。LM Studio readiness 正確地**不是**全域 gate（服務仍能 upload/ASR/逐字稿/健康診斷）；ASR gate（backend+model 可載入）與摘要 gate（LM Studio 可連線且唯一 loaded LLM）都只在各自工作邊界阻擋，符合「局部降級」原則。

**複雜度判定**：新增一個 MLX adapter、一個 cache resolver branch、一個 local-provider setting、一個 loaded-model selector、additive readiness 欄位，每項都有 deletion test 且可追溯到 CORE outcome 或 MNB 不變量。未引入 provider framework、模型 registry、scheduler、Docker 分支或新 task state。設計經濟良好。

**最大風險**：RISKIEST_ASSUMPTION #1——已 cache 的 Breeze-ASR-26-MLX snapshot 能否在 `convert` 的 Python 3.12 環境完全離線載入。此風險有 WAVE-02 硬性 stop condition 與既有相容性證據（snapshot 存在、yt_down_txt 曾用 mlx-whisper 0.4.3），但未在 WAVE-01 之前以 spike 提前去風險（見 RV-02）。

## GOAL_BASELINE

`[UNVERIFIED]` — 本審查在全新上下文執行，cloud session store 不可用、local store 無對應的 2026-08-26 Mac M4 Pro 原始請求 turn，因此**無法獨立還原權威使用者請求原文**。以下 GOAL_BASELINE 係由 plan.md 的 OWNER_CHECK / GOAL_CONTRACT 反推，並以 repository 現況交叉驗證，**不視為已證明使用者意圖**：

- PRIMARY_OUTCOME：Mac M4 Pro 原生執行 MLX/Metal ASR + LM Studio 摘要，同時保留 NVIDIA/CUDA。
- 關鍵約束：不得修改 `/Users/hsiaojohnny/dev/yt_down_txt`（MNB-01）、不得硬編碼 LM Studio 模型名（MNB-03）、Mac 用 LM Studio 不用 Ollama、Mac 不用 Docker。
- 驗收：真實 Mac E2E（upload → MLX ASR → LM Studio summary → export），offline 命中既有 snapshot，NVIDIA regression 不退化。

> 此 [UNVERIFIED] 是審查環境限制，非 plan 缺陷。plan 的約束（尤其 MNB-01 對 yt_down_txt 的零寫入）具體且貫穿全文，可信度高；但 Stage 03 handoff 前應由 owner 再次確認意圖與優先級。

## GOAL_ALIGNMENT

PRIMARY_OUTCOME 與使用者目標一致：以 Mac 原生替代 RTX 4090 不可用時的轉錄/摘要能力，且不犧牲 NVIDIA。SUCCESS_EVIDENCE 是**結果導向**（實際 MLX 轉錄回報 `mlx_whisper`/`mlx-metal`、offline 命中 snapshot、LM Studio 換模後下一工作自動採用、NVIDIA 相容），而非僅「實作完成度」。未發現支援工具/來源/schema 細節反客為主成為專案目標。**對齊良好。**

## NECESSITY_AND_TRACEABILITY

REQUIREMENTS_AND_CRITICALITY 表完整，每項 REQ/NFR 皆可追溯到 PRIMARY_OUTCOME 或 MNB 不變量：

- CORE：REQ-01~07、NFR-01/03/04 均直接服務核心 outcome 或 must-not-break 不變量，分類正確。
- SUPPORTING：REQ-08（health/UI）、REQ-09（scripts）、NFR-02（async/timeout）正確標為 SUPPORTING，不阻擋核心。
- 無 untraceable 的顯著工作。COMPLEXITY_BUDGET 每項新增元件都有 deletion test。

**無不必要需求。**

## GATE_AND_VETO_AUDIT

GLOBAL_GATES_AND_RATIONALE 設計正確：

- 唯一全域啟動 gate（backend 依賴可載入）合理，LM Studio readiness 明確排除在全域 gate 外。
- ASR 工作 gate（backend+model 可載入）有明確語意理由：無逐字稿即無任何後續輸出，局部降級不足。
- 摘要工作 gate（LM Studio 可連線 + 唯一 loaded LLM）只阻擋摘要，理由為「任意挑選會使模型身份與使用者意圖不成立」——這是正確性/可重現性語意，非 schema 完整性。

DECISION_CONTRIBUTION_MATRIX 中，`LMSTUDIO_MODEL` override 標為 SUPPORTING 且「完全覆蓋自動選擇」但 veto=否，權重與否決權分離清楚。**無不當全域 gate。**

## COUPLING_AND_FAILURE_CONTAINMENT

- MLX adapter 遵守既有 `DetailedTranscriptionResult` 邊界，task processor 不感知 MLX 特定結構。
- Provider/loaded-model selection 集中在 summarization boundary，不散落 task/UI/scripts。
- LM Studio 失敗沿用既有 `summary_failed` 降級（逐字稿先落檔、DOCX 標示僅逐字稿），已由 task_processor.py 現況驗證（line 233-235）。
- Health/UI 只消費 normalized status，不直接探測套件/目錄/外部 process。
- `yt_down_txt` 只存在於 evidence/acceptance safety check，不出現在 runtime config/default。

**失敗被收斂在最窄安全邊界，無單一低價值 adapter 成為單點故障。**

## DESIGN_ECONOMY

COMPLEXITY_BUDGET 每項新增元件都「付租金」：MLX adapter（REQ-01/02）、cache resolver（NFR-03/省空間）、local-provider setting（REQ-03）、loaded-model selector（REQ-04）、additive readiness（REQ-08）。明確「不新增 provider plugin framework、模型 registry、持久化 model selection、scheduler、Docker 分支或新 task states」。**無過度工程。**

## CRITICAL_PATH_AND_PRIORITY

CORE 驗收未通過前不投入 UI polish 或真實會議品質統計，優先級正確。但存在兩處可改善的排序問題（見 RV-02、RV-03），均為 MINOR，不影響 CORE 先行的整體方向。

## REQUIREMENT_FIDELITY

REQ-01~09、NFR-01~04 與 MNB-01~06 完整對應。OOS-01~06 明確排除 Mac Docker、LM Studio SDK/lifecycle、Ollama on Mac、yt_down_txt 修改、模型訓練/量化、移除 NVIDIA fallback。**範圍忠實。**

## GROUNDING_AND_DRIFT

VERIFIED_CURRENT_STATE 的關鍵宣稱已逐一在 repository 驗證：

- ✅ `transcription.py:_detect_runtime`（line 96-97）明確把 MPS 降級 CPU。
- ✅ `asr_model_resolver.py:infer_asr_backend`（line 63-71）只接受 transformers/faster_whisper。
- ✅ `summarization.py:_select_local_engine`（line 797-810）先探 Ollama 再探 LM Studio；`_get_lmstudio_client`（line 150-163）用同步 `OpenAI`。
- ✅ `config.py`：`LMSTUDIO_MODEL` 預設 `gpt-oss-20b`（硬編碼）、`LMSTUDIO_BASE_URL` 預設 `host.docker.internal:1234/v1`。
- ✅ `config.macos.yaml` 含 `device: mps`、`use_mps: true`、`model: gemma-3-27b-it-qat`、`mlx-community/whisper-large-v3-turbo` 等過時假設。
- ✅ `scripts/macos/start-mac-native.sh` 含 conda meetingscribe、`ollama pull`、MPS 加速宣稱。
- ✅ `LOCAL_LLM_PROVIDER` 目前不存在於 backend/（確為新增設定）。
- ✅ task_processor.py 已把摘要失敗局部降級為「僅逐字稿」。

**無 anchor drift，grounding 精確。**

## ARCHITECTURE_AND_CONTRACTS

- 不變契約（upload/progress/cache/逐字稿保存/摘要失敗降級/NVIDIA backend）維持不變。
- 改變契約（`ASR_BACKEND=auto` Darwin→mlx_whisper、`LOCAL_LLM_PROVIDER=auto` Darwin→lmstudio、`LMSTUDIO_MODEL` 改 optional、LM Studio 每工作固定選模、zero/multiple 為穩定錯誤）皆在 SEMANTIC_CONTRACT 明確列出，非以「bounded executor fix」偷渡。
- 穩定錯誤語意（ASR_BACKEND_UNAVAILABLE / ASR_MODEL_UNAVAILABLE / LMSTUDIO_UNREACHABLE / NO_LOADED_LLM / MULTIPLE_LOADED_LLMS / MODEL_NOT_LOADED）定義清楚，經既有 exception/description 管道落地，不新增 task state 或 retry API。

**契約變更透明且語意完整。**

## DATA_SECURITY_RELIABILITY

- 無資料 schema/database/transcript migration。
- Health/API 只 additive，既有 consumer 欄位保持原意。
- cache signature 加入 backend/model/revision，避免不相容快取誤命中。
- 不回傳絕對 model/cache path（避免洩漏機器特定路徑）。
- `yt_down_txt` 零寫入、零 runtime coupling（NFR-04），有前後 Git 狀態一致驗證。
- 平台 marker 隔離 MLX 依賴，避免污染非 Darwin ARM64 安裝圖。

**安全/隱私/可靠性邊界合理。**

## IMPLEMENTATION_SEQUENCE

WAVE-01（config/LM Studio）→ WAVE-02（MLX ASR）→ WAVE-03（native ops/observability）→ WAVE-04（E2E/regression）。每 wave 有 scope/serves/preconditions/change intent/focused verification/exit criteria/rollback。rollback 路徑明確（`ASR_BACKEND=transformers` 回復、provider override 移除、scripts additive 獨立回復）。**序列完整，rollback 可執行。**

## TESTABILITY_AND_ACCEPTANCE

Requirement-to-evidence mapping 完整，每項 REQ/NFR 有最低充分證據。明確「不得把 mock-only 測試稱為 Apple hardware E2E」。Mac native integration 用 `say` 產生固定短語音、`HF_HUB_OFFLINE=1` 驗證 snapshot 命中、驗證無 project-local duplicate。NVIDIA 邊界誠實標示「RTX 4090 不可用，不宣稱 hardware E2E，以 contract tests + static regression 保護」。**可測性與驗收可觀測性良好。**

## SCOPE_AND_COMPLEXITY

範圍聚焦，OOS 明確，無 scope creep。複雜度最小且每項可追溯。**通過 deletion test。**

## FINDINGS

### RV-01 — GOAL_BASELINE 無法獨立還原（MINOR / GROUNDING）
- 影響：GOAL_CONTRACT / OWNER_CHECK。
- 證據：cloud session store 不可用、local store 無 2026-08-26 Mac M4 Pro 原始請求 turn。
- 機制：審查無法獨立驗證使用者意圖，只能以 plan 內部一致性 + repository 現況交叉驗證。
- 最小修正：Stage 03 handoff 前由 owner 確認意圖與優先級；無需修改 plan。

### RV-02 — 最高風險假設未在 WAVE-01 前以 spike 去風險（MINOR / SEQUENCING）
- 影響：WAVE-02 Preconditions、RISKIEST_ASSUMPTIONS #1。
- 證據：RISKIEST_ASSUMPTION #1（offline MLX snapshot 載入）是 PRIMARY_OUTCOME 最大風險，但只在 WAVE-02 開始時驗證，晚於 WAVE-01 的 LM Studio 工作。
- 機制：若 offline MLX 載入失敗需 replan，WAVE-01 已投入的 LM Studio 工作雖獨立且仍必要，但延後了對核心風險的確認。
- 最小修正：在 WAVE-01 期間或之前，以唯讀方式執行一次輕量 MLX offline-load spike（`HF_HUB_OFFLINE=1` 載入 pinned snapshot 並轉錄短音檔），提前確認 RISKIEST_ASSUMPTION #1；若失敗立即 replan，不投入後續 wave。

### RV-03 — CRITICAL_PATH 與 IMPLEMENTATION_WAVES 排序不一致（MINOR / SEQUENCING）
- 影響：CRITICAL_PATH（兩處）與 IMPLEMENTATION_WAVES。
- 證據：CRITICAL_PATH 兩處皆列「MLX adapter/cache reuse」在「LM Studio deterministic selection」之前，但 WAVE-01 是 LM Studio、WAVE-02 才是 MLX。
- 機制：文件層級排序矛盾，可能誤導實作者對核心路徑優先級的判斷。
- 最小修正：統一兩者排序，或在 WAVE 說明中明確「WAVE-01 先建立 config/provider 語意契約作為 WAVE-02 的基礎」的理由，消除歧義。

## REQUIRED_PLAN_CHANGES

無 BLOCKER/MAJOR，無強制修改。建議（非阻擋）：
1. 於 WAVE-01 前/期間加入 MLX offline-load spike（RV-02）。
2. 統一 CRITICAL_PATH 與 WAVE 排序或補述理由（RV-03）。

## RESIDUAL_MINOR_NOTES

- `LMSTUDIO_BASE_URL` 預設從 `host.docker.internal:1234/v1` 改為平台感知（native Mac `127.0.0.1:1234`）是 load-bearing config 語意變更；plan 已於 TARGET_CONTRACT 說明 normalization 與 container env 保留，但實作時須確保 Docker/NVIDIA 路徑的 base_url 預設不被誤改（MNB-04）。
- `LMSTUDIO_MODEL` 從必填硬編碼字串改為 optional override 是刻意 config semantic change，已於 MIGRATION_COMPATIBILITY_ROLLBACK 說明；部署若需固定模型須顯式設定且該模型已 loaded。

FINAL_STATUS: PLAN_APPROVED
NEXT_ACTION: 進入 Stage 03 Handoff，針對 revision 1（SHA-256 `20ba410c1a3ed5a87b8b5af92b93512550d831fa4279981bf402534a74b54927`）建立 handoff.md；handoff 前由 owner 確認意圖（RV-01），並保留 plan 已列出的 stop conditions。
