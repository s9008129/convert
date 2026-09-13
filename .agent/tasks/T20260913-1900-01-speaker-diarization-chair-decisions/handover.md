# 交接文件（Handover）— 多人會議「發言者分離」＋「主席裁示歸屬」

- **TASK_ID**：`T20260913-1900-01-speaker-diarization-chair-decisions`
- **Repo**：`/Users/hsiaojohnny/dev/convert`（branch `main`；remote `origin = https://github.com/s9008129/convert.git`）
- **交接時間**：2026-09-13 20:3x（Asia/Taipei）
- **交接者**：前一輪 Codex CLI 主線（雲端 LLM = Ollama Cloud `deepseek-v4.1-flash`）
- **接手者**：新對話的 Codex CLI Agent（同一台 Mac、同一個 repo、同一個 provider）
- **權威需求來源**：`.agent/tasks/T20260913-1900-01-speaker-diarization-chair-decisions/plan.md`（PLAN_REVISION 1；TASK_CLASS=STANDARD；REVIEW_REQUIRED=YES；INDEPENDENT_ACCEPTANCE_REQUIRED=YES；E2E_REQUIRED=YES）

---

## 0. 給新對話接手 Agent 的啟動 Prompt（請把整段貼進新對話第一則訊息）

```
你是接手 T20260913-1900-01 的 Codex CLI Agent，工作目錄 /Users/hsiaojohnny/dev/convert（branch main）。
上一輪主線已完成實作與真實音檔 E2E，現在由你接手「收尾＋獨立驗收」。請先做這五件事，再動任何檔案：

1. 讀這份交接文件：.agent/tasks/T20260913-1900-01-speaker-diarization-chair-decisions/handover.md
   再讀權威計畫：.agent/tasks/T20260913-1900-01-speaker-diarization-chair-decisions/plan.md
2. 用唯讀指令確認現況（不要相信文件勝過指令輸出）：
   - git -C /Users/hsiaojohnny/dev/convert log --oneline -3 && git status --short
   - curl -s -m 20 'http://localhost:9527/api/tasks/3d7f76d3'
   - curl -s -m 20 'http://localhost:9527/api/health'（看 cloud_llm_provider / cloud_llm_model / asr_backend）
   - cd /Users/hsiaojohnny/dev/convert && DATA_DIR=./data .venv/bin/python -m pytest tests/ -q
3. 依交接文件 §5「待辦」逐項完成。優先序：Stage 05 獨立驗收（fresh-context 子代理）→ 文件 §9 證據 → 一致性複核 → 收尾 → 最終回報。
4. 硬性限制（違反即算做錯）：
   - 雲端 LLM 一律用 Ollama Cloud（deepseek-v4.1-flash）；**不要用 Gemini**。
   - 地端 LM Studio 沒開，不要測地端模型；`LOCAL_LLM_PROVIDER=auto` 解析到 lmstudio 失敗是預期現象，不得當成 bug。
   - 不得印出任何 API key；不得 git reset/stash/覆寫使用者的工作；不得 commit 未經確認的無關檔案。
   - diarization 是 fail-soft 加值層：任何失敗都要退回純文字逐字稿、任務照常完成（C4）。
   - 「發言者N」是自動分群編號，不是姓名；文件與紀錄都不得當人名。
5. 回報規範：每條結論標 [VERIFIED]/[INFERRED]/[UNVERIFIED]，並附實際指令與輸出。完成時回報：primary outcome（發言者標籤＋裁示歸屬的證據）→ 任務閉環狀態 → 殘留風險。

需要我（使用者）決策時，只問一個聚焦問題並給建議預設值。除非使用者明確要求，不要自行 commit 或 push。
```

---

## 1. 使用者目標（最新版，含中途修訂）

**原始目標**
1. 45 分鐘多人會議錄音：逐字稿要能分辨誰在說話（發言者分群標籤＋時間戳）。
2. **最重要**：可靠辨識「主席（科長）裁示／決議」；**非主席發言不得寫成主席裁示**。
3. 以真實音檔 `~/Downloads/0903-科務會議.m4a`（2695s）＋「科務會議」模板（`section_meeting`）完成雲端模式 E2E，並留下證據。

**中途修訂（當前最高優先）**
4. 雲端 LLM **改用 Ollama Cloud `deepseek-v4.1-flash`**（使用者同時在跑另一個任務，Gemini 免費層會 429）。Gemini 保留為可切回的 provider，但**本任務一律用 Ollama Cloud**。
5. 使用者允許（並鼓勵）大量使用 subagent 平行處理來加速；額度充足。

---

## 2. 目前狀態快照（全部 [VERIFIED]，2026-09-13 20:27–20:35）

| 項目 | 狀態 |
|---|---|
| 實作 | 完成（後端＋前端＋提示詞＋測試＋文件＋下載腳本） |
| 全套測試 | `DATA_DIR=./data .venv/bin/python -m pytest tests/ -q` → **784 passed, 2 skipped**（3 warnings；2 skipped 為既有缺少 fixture 音檔） |
| 服務 | uvicorn **PID 54026**（detached，`--port 9527`），`build_revision=eb88677f6f887dbf9adf1d5b14cf85f111b155f3-dirty`（= HEAD `eb88677` + 本任務 dirty 變更） |
| 雲端 provider | `cloud_llm_provider=ollama_cloud`、`cloud_llm_model=deepseek-v4.1-flash`、`cloud_llm_available=true` |
| ASR | `asr_backend=apple`（Apple SpeechAnalyzer；本機 macOS 26 / Apple Silicon 唯一引擎） |
| 真實音檔 E2E | 任務 **`3d7f76d3`**：`status=completed`、`progress=100`、`summary_failed=false`、`completed_at=2026-09-13T20:27:17`、總耗時 **709.1s** |
| diarization 實測 | 682 段、**8 位發言者**、151.2s、RTF 0.056（45 分鐘全檔，CPU） |
| 發言者標註逐字稿 | 8 個標籤；`發言者1` 佔 85%（84 段）、`發言者2` 9%（49 段）、`發言者3` 5%（34 段）；`發言者4–8` 為零星短句（6/4/3/2/1 段） |
| 輸出檔 | `data/outputs/0903-科務會議_3d7f76d3.md`（26,797 B）、`..._3d7f76d3.docx`（49,584 B）、`..._3d7f76d3_attachment.docx`（40,541 B）、`..._3d7f76d3_逐字稿.txt`（38,149 B） |
| baseline（舊版 Gemini、無標籤） | `data/outputs/0903-科務會議_42fbaee7.md`（10,598 B）＋`..._逐字稿.txt`（0 個「發言者」標籤） |
| 模型檔 | `models/diarization/3dspeaker_speech_campplus_sv_zh-cn_16k-common.onnx`（28 MB）＋`models/diarization/sherpa-onnx-pyannote-segmentation-3-0/`；`models/` 已被 `.gitignore` 忽略 |
| git | 本任務變更**尚未 commit**（19 個 modified ＋ 新增檔；見 §10） |
| Stage 05 獨立驗收 | **已完成（attempt-01）：總 gate = `ACCEPTED`**（C1 PASS／C2 PARTIAL／C3 PASS／C4 PASS）；證據：`e2e/attempt-01/e2e_report.md`、`result.md` |
| git commit | `4768e4a`（feat(diarization,cloud)…）已 push 至 `origin/main`；Stage 05 證據與本文件更新為第二個 commit |

---

## 3. 本輪完成了什麼（依 C1–C4 對應）

### C1 說話者分群逐字稿（[VERIFIED] 已完成）
- 新模組 `backend/services/diarization.py`：sherpa-onnx（pyannote segmentation-3.0 ＋ 3D-Speaker CAM++ 中文 embedding）離線 diarization；ffmpeg 解 16k mono；**fp32 `model.onnx` 優先**（實測 int8 覆蓋率 81.3%、最大群 85.9% 較差）。
- 新模組 `backend/services/speaker_transcript.py`：ASR segment 以「時間重疊最大」對位到 turn；同發言者 gap < 1.5s 合併；輸出 `[hh:mm:ss-hh:mm:ss] 發言者N：…`＋開頭統計區塊（發言量 %、段數、首次發言）。低重疊時依時間比例拆句（不丟字）。
- `backend/services/task_processor.py::_obtain_transcript/_label_speakers`：ASR 後跑 diarization → 有標籤就存標籤版逐字稿，失敗就維持純文字。
- 快取正確性：`backend/core/asr_model_resolver.py::build_asr_cache_signature(..., diarization=...)`＋`backend/services/file_manager.py::get_unlabeled_asr_cache_signature()`——**diarization 失敗只寫「無標註」key，不污染標註快取**。
- 參數定案（45 分鐘全檔實測，非切片推估）：`DIARIZATION_NUM_CLUSTERS=8`（threshold 自動路線 0.6/0.8/0.9 → 120/73/51 群不可用；k=8 → 8 群、覆蓋率 86.8%、最大群 79.8%、0 個 <5 秒碎群）。

### C2 主席裁示歸屬（[VERIFIED] 提示詞層已落地；結構化證據欄位尚未實作）
- `backend/core/prompt_templates/section_meeting.py`、`backend/core/prompts.py`、`config.yaml` 三處同步新增規則（CI 強制配對）：發言者N 非姓名；«科長指示及提醒事項» 與 «決議彙整表» 只收主席裁示；轉述上級需寫來源；無法確認填「（待確認）」；他人發言另列討論內容。
- 實測效果（本次輸出 vs baseline）：
  - 新紀錄把「與會同仁意見」獨立成 `三、（二）臨時動議及與會同仁意見`（baseline 該節是「（待確認）」）。
  - 主席段落擴充為 13 個主題／47 條＋決議彙整表 63 筆資料列（baseline 為 4 子節／11 條＋空白表）。
  - 抽驗 3 案例：①組織規程/編制表變動 → 逐字稿 `[00:00:00-00:05:36] 發言者1`（主席）；②瑞里 10/14 發放 → `[00:06:14-00:06:48] 發言者1`；③文康活動 800 元/17 人/13,600 元 → 金額細節出自 `發言者2`（非主席），紀錄同時出現在 `二、（六）` 與 `三、（二）1 與會同仁意見`。
  - **反向證據（必須誠實記錄）**：最終紀錄本身**完全沒有**「發言者N」字樣（`二、` 47 條、決議彙整表 65 列皆無；全檔只有 `一、` 有 4 處零星引註如「發言者3建議…」）。也就是說：**標籤只存在於逐字稿**，紀錄的裁示歸屬目前只能靠人工比對逐字稿推斷。
  - **殘留問題**：`二、科長指示及提醒事項` 仍混入非主席提供的操作細節；且**尚無**「每項裁示 → 發言者＋時間＋quote」的結構化欄位（研究文件 §4.4 已載明尚未實作；計畫中屬 SUPPORTING S3，非 CORE）。

### C3 真實音檔 E2E（[VERIFIED] 已完成）
- 任務 `3d7f76d3` 全流程：ASR 15.8s（helper，2695s 音檔）→ diarization 151.2s → 標註 183 段發言 → 雲端摘要（Ollama Cloud，分段萃取＋2 輪品質補強）→ 完成。
- 可下載：`/api/tasks/3d7f76d3/transcript`、`/api/tasks/3d7f76d3/result?format=md|docx&doc=record`、`...&doc=attachment`（`doc=attachment&format=md` 回 `{"detail":"附件僅支援 docx 格式"}`，屬預期）。
- 證據副本：`/tmp/e2e-artifacts/`（transcript.txt、result_record.md、record.docx、attachment.docx）。
- **注意（非阻擋）**：log 20:18:31 顯示語意校正步驟 `LMSTUDIO_UNREACHABLE` → 熔斷後跳過（地端 LM Studio 沒開，屬預期 fail-soft；本次未做 LLM 校正）。

### C4 fail-soft（[VERIFIED] 已完成）
- `diarize_async()` 對**逾時**（`asyncio.wait_for(..., DIARIZATION_TIMEOUT_SECONDS=900)`）與**任何例外**都回 `None`＋warning。
- `_label_speakers` 在 diarization **之前**做時間軸守門：有效時間區段 < 一半直接跳過（Apple null→0.0 全零時間軸不再產生錯誤標籤）。
- 失敗路徑有測試覆蓋：`tests/test_diarization_failsoft.py`（20 測試）、`tests/test_speaker_transcript.py`（24 測試）。

### 雲端 provider 切換（使用者中途要求，已完成）
- `backend/core/config.py`：`CLOUD_LLM_PROVIDER`（預設 `ollama_cloud`）、`OLLAMA_API_KEY`、`OLLAMA_CLOUD_BASE_URL=https://ollama.com/v1`、`OLLAMA_CLOUD_MODEL=deepseek-v4.1-flash`；衍生屬性 `cloud_llm_*`（所有雲端呼叫統一由此取值）。
- `backend/services/summarization.py`：client/model/端點改讀 `cloud_llm_*`；streaming 可處理 reasoning-only chunk（`delta.reasoning`）並在只有 reasoning 時給明確錯誤；健康檢查修掉 `response.models`（舊寫法永遠 false）。
- `backend/api/routes.py`＋`backend/models/schemas.py`：`/api/config`、`/api/gemini/health`、`/api/health` 新增 additive `cloud_llm_*` 欄位（`gemini_available` 保留為相容欄位，語意＝目前 provider 金鑰已設定）。
- `frontend/js/app.js`：新增 `isCloudLlmAvailable()`（`cloud_llm_available ?? gemini_available`），文案 provider 中立（`node --check` 通過）。
- `.env.example` / `.env.local.example`：新增 Ollama Cloud 段；`GEMINI_API_KEY=` 那行**必須保持未註解**（`scripts/windows/setup-api-key.ps1` 正則依賴）。
- 測試：`tests/test_cloud_provider_switch.py`（16）、`tests/test_api_routes.py` 斷言改 provider-aware。

### 其他
- `requirements.txt`＋`pyproject.toml` 加 `sherpa-onnx>=1.13.8`；`uv.lock` 已 `uv lock` 更新。
- `scripts/download_diarization_models.py`（新）：冪等下載/驗證模型。
- 文件：`doc/規格與設計/發言者分離與主席裁示-研究與設計.md`（§0–§9；§9 為 E2E 證據）、`README.md`（發言者標註功能＋provider 中立說明）、`doc/README.md` 索引。
- 研究證據（**在 /tmp，重開機即失**）：`/tmp/research/diar_e2e_params.md`（k 掃描）、`diarization_landscape.md`、`role_decision_extraction.md`、`ollama_cloud_smoke.md`、`e2e_runbook.md`；`/tmp/e2e-artifacts/`。

---

## 4. 尚未完成 / 待辦（新對話的主線工作）

| # | 待辦 | 具體做法 | 完成定義 |
|---|---|---|---|
| 1 | ~~Stage 05 獨立驗收~~ **已完成** | 產物：`.agent/tasks/<TASK_ID>/e2e/attempt-01/e2e_report.md`、`result.md`；總 gate `ACCEPTED`（C2=PARTIAL：7 抽驗中 3 例非主席內容被寫成科長指示；`[00:42:51] 發言者3` 示範點、`[00:06:56] 發言者3` 公文會辦、文康活動細節） | 已完成；如需複驗，重派 fresh-context 子代理 |
| 2 | 文件 §9 補 E2E 證據 | 若接手時 §9 仍是「待主線補填」，用 §2/§3 的實測數字與抽驗案例補上 | §9 有 task id、標籤樣本、裁示抽驗 3 案例、輸出檔名與大小 |
| 3 | 文件一致性複核 | 對照 `doc/規格與設計/發言者分離與主席裁示-研究與設計.md` §2/§3/§5/§6 與程式碼現況（預設值、fp32、逾時/守門/快取、provider） | 無與程式碼矛盾的敘述；`doc/README.md` 有索引 |
| 4 | 收尾清理 | 已刪 `data/uploads/minicheck-deadbeef.wav`；確認 `data/outputs/` 無重複殘檔（目前有 `_record.md/.docx` 兩份與 `_3d7f76d3.md/.docx` 相同的副本，可清可留） | 無測試殘檔 |
| 5 | 最終回報使用者 | primary outcome → 閉環 → 殘留風險（見 §9） | 使用者可據此驗收 |
| 6 | （可選，需使用者同意） | ① 對「品質補強仍回報『待辦事項遺漏 71 項』」調參或加警告；② 修正 log 誤導訊息（`device_detector` 在 Apple ASR 路徑仍印「使用 MPS 加速」，但 `mps_available=false`）；③ 實作 S3（裁示→quote/time 結構化欄位） | 需先問使用者，不可自行擴張範圍 |
| 7 | （建議另開新任務）ASR 語意／錯字校正移植 | 使用者另一專案完成校正後，把關鍵修正邏輯移植回本專案（可能落點：ASR 後處理層或提示詞層）；**不屬本 GOAL 範圍** | 移植後以同一支音檔重跑 E2E 回歸，比對標籤／裁示歸屬／輸出檔差異 |

---

## 5. 進行中／未回收的舊對話資源（新對話可能已無法存取）

- Stage 05 稽核子代理（舊對話）：`01a09abf-c545-7150-8688-49b75e73a2a4`（Goodall）→ 產物路徑 `.agent/tasks/<TASK_ID>/e2e/attempt-01/e2e_report.md`、`result.md`。
- E2E 證據抽取子代理（舊對話）：`01a09abd-898f-7ae1-9598-c7bf1cfb6796`（Laplace）→ 產物在 `/tmp/e2e-artifacts/`。
- 文件整理子代理（舊對話）：`01a09a98-b961-7b91-b98a-da3067bfa375` → 正在更新研究文件 §2/§3/§5/§6 與 README。
- **新對話請以檔案為準**：先看 `.agent/tasks/<TASK_ID>/` 與 `/tmp/e2e-artifacts/` 是否有上述產物；沒有就自己重做（指令見 §7）。

---

## 6. 關鍵決策與凍結語意（不可自行更改）

1. **provider**：預設 `ollama_cloud`；Gemini 僅在 `CLOUD_LLM_PROVIDER=gemini` 時使用。雲端呼叫一律走 `settings.cloud_llm_*`。
2. **發言者標籤語意**：自動分群編號，**不是姓名**；不得寫入紀錄當人名；`發言者1` = 發言量最大者（通常是主持人，但仍須內容證據判斷）。
3. **裁示歸屬**：主席裁示只收主席（科長）裁決與交辦；轉述上級要寫來源；無法確認 → 「（待確認）」。他人發言 → 討論內容。
4. **fail-soft 契約**：diarization 不可用／逾時／ASR 無時間軸 → 逐字稿退回純文字，任務必須照常完成；失敗**不得**寫入標註快取 key。
5. **參數凍結**：`DIARIZATION_NUM_CLUSTERS=8`、`DIARIZATION_TIMEOUT_SECONDS=900`、`ENABLE_DIARIZATION=true`、fp32 模型優先、`DIARIZATION_MIN_SEGMENT_COVERAGE=0.6`、`DIARIZATION_MERGE_GAP_SECONDS=1.5`。
6. **additive API 設計**：`cloud_llm_*` 為新增欄位；`gemini_available` 保留（語意改為「目前 provider 金鑰已設定」），舊測試與前端相容。

---

## 7. 常用指令（照抄可用）

```bash
# 全套測試（DATA_DIR 必須在 import backend 之前設定）
cd /Users/hsiaojohnny/dev/convert && DATA_DIR=./data .venv/bin/python -m pytest tests/ -q

# 聚焦測試
cd /Users/hsiaojohnny/dev/convert && DATA_DIR=./data .venv/bin/python -m pytest \
  tests/test_diarization_failsoft.py tests/test_speaker_transcript.py \
  tests/test_cloud_provider_switch.py -q

# 服務狀態／provider 觀測
curl -s -m 20 http://localhost:9527/api/health
curl -s -m 20 http://localhost:9527/api/config
curl -s -m 20 'http://localhost:9527/api/gemini/health?force_refresh=true'

# 任務與輸出
curl -s -m 20 http://localhost:9527/api/tasks/3d7f76d3
curl -sS -m 120 -o /tmp/e2e-artifacts/transcript.txt  http://localhost:9527/api/tasks/3d7f76d3/transcript
curl -sS -m 120 -o /tmp/e2e-artifacts/record.md      'http://localhost:9527/api/tasks/3d7f76d3/result?format=md&doc=record'
curl -sS -m 120 -o /tmp/e2e-artifacts/record.docx    'http://localhost:9527/api/tasks/3d7f76d3/result?format=docx&doc=record'
curl -sS -m 120 -o /tmp/e2e-artifacts/attachment.docx 'http://localhost:9527/api/tasks/3d7f76d3/result?format=docx&doc=attachment'

# 重新上傳跑一次 E2E（multipart 欄位名：file / processing_mode / meeting_template / user_prompt）
curl -s -m 120 -X POST http://localhost:9527/api/upload \
  -F 'file=@/Users/hsiaojohnny/Downloads/0903-科務會議.m4a' \
  -F 'processing_mode=cloud' -F 'meeting_template=section_meeting'
```

**重啟服務（重要）**：`scripts/macos/start-mac-native.sh` 直接從工具 session 執行會被 SIGTERM 帶走；用 detach helper：
`python3 /tmp/detach_run.py scripts/macos/start-mac-native.sh`（helper 內容：fork＋setsid 兩次後 `Popen(["bash", script])`，輸出寫 `/tmp/svc_start.out`）。
`OLLAMA_API_KEY` 目前由 launchctl 提供（`launchctl getenv OLLAMA_API_KEY` 有值），新 shell 亦有；**不要印出金鑰**。

---

## 8. 精確事實：GPU / CPU / NPU（使用者問過，回答必須一致且不得誇大）

- **[VERIFIED] Apple SpeechAnalyzer 是本專案的唯一 ASR 路徑**（macOS 26＋Apple Silicon）：`apple_speech_cli`（SwiftPM executable，使用 `SpeechAnalyzer`/`SpeechTranscriber`）由 Python 以 subprocess 呼叫；本次 45 分鐘音檔 helper 實測 **15.8s**（RTF≈0.006）。
- **[VERIFIED] 本專案沒有任何程式碼能指定或量測 Apple ASR 使用哪個 compute unit**（ANE／GPU／CPU 由 Apple 框架內部決定）。`/api/health` 的 `accelerator: "apple-neural"` 是**專案自訂標籤**（`backend/core/platform_config.py`、`backend/services/device_detector.py`），不是硬體量測。
- **[VERIFIED] Activity Monitor 沒有 ANE 欄位**；macOS 只用 `powermetrics`（需 sudo）能看 ANE（本機 `powermetrics -h` 已確認有 ANE sampler 字樣，例如 `--samplers ane_power`）。**我們沒有實際量測過 ANE**（需 sudo，本任務未執行）。
- **[VERIFIED] 先前 GPU 飆高**＝研究用的 pyannote（PyTorch MPS）baseline 實驗；該程序已結束（`pgrep` 無 pyannote/MPS）。
- **[VERIFIED] CPU 偏高**＝sherpa-onnx diarization（ONNX Runtime **CPU** 路徑；`diarization.py` 未指定任何 GPU provider）＋同時段的平行全檔參數掃描子代理。E2E 實測 151.2s / 2695s = RTF 0.056。
- **[VERIFIED] 已知誤導訊息**：`backend/services/device_detector.py` 在 Apple ASR 路徑仍印「✅ 偵測到 Apple Silicon，使用 MPS 加速」，但同一份 health 顯示 `mps_available=false`——這是**既有**的訊息缺陷（非本任務引入），可列為後續小修。
- 對使用者的正確說法：**Apple 的 on-device 模型一般以 ANE 為主，但開發者無法指定、也無法從 Activity Monitor 觀察；本專案的能量測量只到 CPU/GPU（Activity Monitor）。**

---

## 9. 殘留風險與不確定性（回報時必須誠實列出）

1. **無人工 ground truth**：無法證明「8 群＝真實人數」。`發言者4–8`（6/4/3/2/1 段、0%）極可能是碎裂或短插話；文件不得把它們當成 5 個不同的人。
2. **C2 屬部分達成（Stage 05 判定 = PARTIAL）**：提示詞層已落地；Stage 05 抽驗 7 案例中 4 例可回溯到主席、**3 例非主席內容被寫成科長指示**（`[00:42:51] 發言者3` 示範點被列為科長交辦且彙整表承辦寫「科長」、`[00:06:56] 發言者3` 公文會辦、文康活動形式細節）。紀錄內 `[hh:mm:ss]` 時間戳數 = 0，且**沒有**結構化的「裁示→發言者＋時間＋quote」欄位（S3 未實作）。
3. **摘要完整性驗證未通過**：品質補強兩輪都回報「待辦事項遺漏 71 項」，最後一次生成後的驗證**仍回報遺漏 47 項**（`LOCAL_LLM_MAX_REFINEMENT_ROUNDS=2` 上限後照常輸出）；最終紀錄仍有多處「（待確認）」。此為既有品質議題，非本任務引入，但會影響使用者觀感。
4. **ASR 文字品質（已向使用者完整說明；結論：不阻擋本任務）**：
   - 逐字稿有大量同音錯字（例如「編織錶」「雞茶股」）——成因在 ASR 層，不是 diarization/LLM 層；本次語意校正因 LM Studio 未開而熔斷跳過（屬預期 fail-soft）。
   - 風險判定：C1/C3/C4 **低風險**（標籤與時間軸不依賴用字正確）；成品可讀性屬**中風險**（錯字會直接進紀錄）；C2 的 3 個反例屬歸屬邏輯問題，與錯字無因果關係。
   - 建議路徑：ASR 校正留在使用者另一專案獨立處理；移植回本專案後，**用同一支 `0903-科務會議.m4a` 重跑 E2E 當回歸**，比對標籤、裁示歸屬與輸出檔差異。
5. **重疊語音**（B1，BEST_EFFORT）：未處理。
6. **相依性**：`sherpa-onnx` 已進 `requirements.txt`／`pyproject.toml`／`uv.lock`；Docker／Windows 首次使用需執行 `scripts/download_diarization_models.py`（缺模型時 fail-soft）。
7. **`/tmp` 資源易失**：研究報告與 E2E 證據副本都在 `/tmp`；重開機即消失。重要結論已寫入 repo 文件。

---

## 10. 檔案座標（本任務變更清單）

**新增**
- `backend/services/diarization.py`、`backend/services/speaker_transcript.py`
- `scripts/download_diarization_models.py`
- `tests/test_speaker_transcript.py`、`tests/test_diarization_failsoft.py`、`tests/test_cloud_provider_switch.py`
- `doc/規格與設計/發言者分離與主席裁示-研究與設計.md`
- `.agent/tasks/T20260913-1900-01-speaker-diarization-chair-decisions/`（plan.md、handover.md、goal.md、e2e/…）

**修改（19 檔）**
`backend/core/config.py`（CLOUD_LLM_*、DIARIZATION_*）、`backend/core/asr_model_resolver.py`（快取簽章）、`backend/services/task_processor.py`（標註流程）、`backend/services/file_manager.py`（unlabeled 快取 key）、`backend/services/summarization.py`（provider 切換／reasoning chunk／健康檢查）、`backend/api/routes.py`、`backend/models/schemas.py`、`backend/main.py`、`backend/core/prompts.py`、`backend/core/prompt_templates/section_meeting.py`、`config.yaml`、`frontend/js/app.js`、`.env.example`、`.env.local.example`、`README.md`、`requirements.txt`、`pyproject.toml`、`uv.lock`、`tests/test_api_routes.py`

**輸出（git 忽略）**
`data/outputs/0903-科務會議_3d7f76d3.{md,docx}`、`..._attachment.docx`、`..._逐字稿.txt`、`data/uploads/f7582ca195a7.m4a`
