# 功能規格：MeetingScribe（會議轉錄與會議記錄生成系統）

**功能分支**: `main`  
**建立日期**: 2026-02-13  
**最後更新**: 2026-02-13  
**狀態**: Draft（以程式碼為準；已有單元與整合測試，詳見 tests/）  
**輸入**: 音訊/視訊檔案（MP3/MP4/WAV/M4A/MKV/WebM/FLAC/OGG/AVI/MOV 等），或由前端/API/排程上傳之檔案路徑

> 專案定位：MeetingScribe 是一套以 Whisper 為語音轉錄引擎，並以本地/雲端 LLM（Ollama/LM Studio/Gemini）生成結構化會議記錄的系統。  
> 三大核心：可靠的檔案上傳與安全驗證、可擴展的任務排隊與處理、以 LLM 與 prompt-driven 規則生成高品質繁體中文會議紀錄。  
> 設計原則：分層解耦（API / 排隊 / 處理 / 模型 / 檔案）、可觀測性（結構化日誌、WebSocket 進度）、可測試性（模組化、mockable LLM/Whisper）、安全（路徑與輸入驗證）。

---

## 0. 摘要（結論與可驗證事實）
- 運行入口：backend.main: FastAPI 應用（uvicorn backend.main:app --host 0.0.0.0 --port 9527）。（參考：backend/main.py）
- 核心子系統：API 層（backend/api/routes.py）、WebSocket（backend/api/websocket.py）、排隊（backend/services/queue_manager.py）、任務處理（backend/services/task_processor.py）、轉錄（backend/services/transcription.py / src/whisper_transcriber.py）、摘要（backend/services/summarization.py / src/summarizer.py）、檔案管理（backend/services/file_manager.py）。（可於 repo 對應檔案驗證）
- 主要行為保證：上傳檔案經驗證（副檔名、大小、路徑安全）→ 加入 FIFO 排隊（QUEUE_MAX_SIZE、MAX_CONCURRENT_TASKS）→ 轉錄（選擇 MLX 或 faster-whisper）→ LLM 摘要→ 儲存 Markdown 輸出與 WebSocket 推播進度。此流程在程式碼中以 TaskQueue + TaskProcessor 明確實作（可透過 tests 模擬/整合驗證）。

---

## 1. 專案簡介與目標
- 目標：將會議錄音自動轉為格式化、在地化（繁體中文）的會議記錄，並支援本地（Ollama/LM Studio）與雲端（Gemini）兩種 LLM 模式。  
- 成功標準（可驗證）：
  - 上傳→處理→輸出流程在 95% 情況下能正常完成（自動化測試可複現）。
  - 轉錄在合理硬體（MPS/CUDA/CPU）下有時間界線；系統在 GPU 滿載情況仍能為新請求提供 30s 超時回應（見 TimeoutMiddleware）。
  - 生成的會議記錄符合系統提示詞（DEFAULT_SYSTEM_PROMPT）之格式與語言限制（繁體中文、100 字內執行摘要、必填欄位等）。

---

## 2. 範圍與假設
- 範圍：
  - 包含檔案上傳 API、排隊與任務處理、Whisper 轉錄、多段 LLM 摘要（分段合併）、結果格式化儲存（Markdown）、Web 前端進度顯示（WebSocket）。
  - 不包含商業資料庫（目前使用檔案系統），但設計可擴展至 SQLite/Postgres。
- 假設：
  - 環境以 Python 3.8+ 運行，依賴於 requirements.txt（faster-whisper、httpx、fastapi、uvicorn 等）。（參考 requirements.txt）
  - 本地 LLM（Ollama / LM Studio）或雲端 API（金鑰）為可用/已配置，否則依設定降級或回報錯誤（routes.py 中檢查）。

---

## 3. 高階系統架構（文字描述）
- 元件與關係（文字圖）：
  - 客戶端（前端 / curl / 上傳腳本）
    → HTTP REST API (/api/upload, /api/health, /api/tasks/...)
    → TaskQueue（backend/services/queue_manager.py）
      → TaskProcessor（backend/services/task_processor.py）
        → FileManager（backend/services/file_manager.py）↔ 檔案系統 (DATA_DIR)
        → TranscriptionService（backend/services/transcription.py / src/whisper_transcriber.py）
        → SummarizationService（backend/services/summarization.py / src/summarizer.py）↔ OllamaClient（src/ollama_client.py）或 Gemini API
    → WebSocket 推播進度（backend/api/websocket.py）
- 部署節點：單機（Native）或容器；支援 GPU（MPS/CUDA/ROCm）或 CPU。啟動指令 /start_service.sh / uvicorn 說明見 README。

---

## 4. 子系統 / 模組清單與檔案對應（mapping）
- API 層
  - backend/main.py — 應用入口、中間件（TimeoutMiddleware）、靜態檔、lifespan
  - backend/api/routes.py — REST API：/api/health, /api/upload, /api/tasks, /api/queue, config endpoints
  - backend/api/websocket.py — WebSocket 連接管理與推播
- 核心服務
  - backend/services/queue_manager.py — 任務排隊 (FIFO)、佇列/處理狀態
  - backend/services/task_processor.py — 任務執行流程與進度更新
  - backend/services/file_manager.py — 上傳儲存、驗證、快取與清理策略
  - backend/services/transcription.py — 平台抽象的轉錄服務（MLX / Faster-Whisper）
  - backend/services/summarization.py — 摘要生成控制（llm 健康檢查、分段合併）
  - backend/services/__init__.py — 聚合導出
- 核心庫 / 工具
  - backend/core/config.py — settings（pydantic-based），包含 DEFAULT_SYSTEM_PROMPT 與上限設定（MAX_FILE_SIZE_MB 等）
  - backend/core/logger.py — loguru 結構化日誌設定（JSON + daily rotation）
  - backend/core/version.py — 從 VERSION 檔讀取版本
  - backend/core/platform_config.py — 平台/裝置偵測（視系統存在）
- 模型與客戶端
  - src/ollama_client.py — 本地 Ollama/LM 客戶端（重試、串流、context fit）
  - src/whisper_transcriber.py — Windows/跨平台轉錄器（faster-whisper / exe）
  - src/summarizer.py — MeetingSummarizer、MarkdownFormatter（分段、合併、品質驗證）
- 前端
  - frontend/index.html, frontend/js/app.js, frontend/css/style.css
- 測試
  - tests/* — 單元與整合測試（已有多個測試案例）
- 配置/腳本
  - config*.yaml, .env.example, start_service.sh, scripts/*

---

## 5. 資料流程（input → processing → output）與介面定義

1. 上傳（/api/upload, POST multipart/form-data）
   - Input: file (UploadFile), processing_mode (local/cloud), user_prompt (optional)
   - Validation:
     - 檔名不得含路徑遍歷字符（".."、"/"、"\\"）或 NUL。
     - 副檔名需在 settings.allowed_extensions_list（backend/core/config.py）。
     - 檔案大小 <= settings.max_file_size_bytes（由 settings.MAX_FILE_SIZE_MB 決定）。
   - Responses:
     - 200 (UploadResponse): { task_id, filename, file_size, queue_position, estimated_wait_seconds, message }
     - 400: 驗證失敗（格式/模式）
     - 413: 檔案過大
     - 503: 佇列已滿

2. 任務排隊與狀態
   - TaskInfo model（backend/models/schemas.py）定義所有狀態欄位（task_id, filename, status, progress, stage, ...）
   - 狀態機（簡化）：
     - QUEUED → PENDING → TRANSCRIBING → SUMMARIZING → COMPLETED | FAILED | CANCELLED
   - 排隊估時：_calculate_wait_time = max(0, position - MAX_CONCURRENT_TASKS) * ESTIMATED_MINUTES_PER_TASK*60

3. 轉錄
   - 接口：TranscriptionService.transcribe(audio_path, progress_callback)
   - Backend selection:
     - MLX (if platform MPS + config points to mlx) → mlx_whisper.transcribe（_transcribe_with_mlx）
     - Else faster-whisper (WhisperModel.transcribe)（_transcribe_with_faster_whisper）
   - Post-condition: always _unload_model() to free VRAM

4. 摘要與格式化
   - MeetingSummarizer.summarize(transcript, custom_prompt?)
   - 若 input token 次數超過 max_input_tokens，採分段 _split_text → 分段摘要 → merge（_summarize_long_text）
   - System prompt constraints（settings.DEFAULT_SYSTEM_PROMPT）：強制繁體中文、100 字內執行摘要、不得虛構、字段必填等。

5. 輸出
   - FileManager.save_result 以 "{safe_base_name}_{task_id}.md" 儲存在 settings.outputs_dir
   - WebSocket 發送 ProgressMessage（backend/models/schemas.ProgressMessage）與完成時包含 result preview

---

## 6. 重要演算法 / 模型 與行為說明

- Transcription Backend 選擇與資源管理
  - 決策（來源：backend/services/transcription.py）：
    - get_whisper_backend() 決定 'mlx' 或 'faster-whisper'。
    - MLX 適用 macOS MPS（fp16），faster-whisper 適用 CUDA/CPU。
  - 資源策略：
    - 每次轉錄前載入模型，轉錄後 _unload_model() 並執行 gc.collect()；若 CUDA，嘗試清空 torch.cuda.empty_cache()。

- Summarization（MeetingSummarizer）
  - Token/字元估算：
    - OllamaClient.estimate_tokens：中文約 1.5 字元 / token，英文約 4 字元 / token（src/ollama_client.py）。
    - MeetingSummarizer.CHARS_PER_TOKEN = 1.5；max_input_tokens 預設 24000。
  - 分段策略：
    - _split_text 優先在換行與句號分割，保留語意完整性；分段後對每段單獨生成摘要，再合併並用 LLM 產生最終記錄（_summarize_long_text）。
  - 品質檢核：
    - _validate_summary 會檢查最小長度（>100 字）、結構標記與英文比例（<=10%）等，若不合格會記錄警告或觸發 fallback。

- OllamaClient（LLM 客戶端）
  - 支援 generate/chat、stream 與自動重試（MAX_RETRIES、RETRY_DELAY）。
  - 對溫度 (temperature) 進行多語言自動降溫（effective_temperature <= 0.15）以穩定繁中輸出。
  - can_fit_context(text, safety_margin) 用於決定是否需分段。

- 安全與格式化策略
  - FileManagerService.validate_file 與 validate_file_size 對上傳做嚴格檢查（禁止路徑遍歷、黑/白名單副檔、NUL 字元檢測）。
  - MarkdownFormatter / TaskProcessor._format_result 包含「移除英文段」與「詞彙替換」策略以維持繁體中文品質。

---

## 7. 設定 / 部署 / 執行流程（可驗證步驟）
- 主要檔案與命令（快速）
  1. 建置環境（建議 venv / conda）
     - python3 -m venv venv && source venv/bin/activate
     - pip install -r requirements.txt --prefer-binary
  2. 配置環境變數或 .env（範例見 README）
     - export DATA_DIR=/Users/hsiaojohnny/dev/convert/data
     - export PYTHONPATH=/Users/hsiaojohnny/dev/convert:$PYTHONPATH
     - 設定 GEMINI_API_KEY 若使用 cloud mode
  3. 啟動（開發）
     - uvicorn backend.main:app --host 0.0.0.0 --port 9527 --reload
     - 或 ./start_service.sh （如有）
  4. 測試健康端點
     - curl "http://localhost:9527/api/health?quick=true"
- 重要設定（預設值來源 backend/core/config.py）
  - MAX_FILE_SIZE_MB=200；DEFAULT_MODE="local"；MAX_CONCURRENT_TASKS=1；QUEUE_MAX_SIZE=50；WHISPER_MODEL="whisper-large-v3-turbo"；DEFAULT_SYSTEM_PROMPT = COSTAR-A 範本（已內建驗證限制）
- 部署建議
  - 生產環境啟用 HTTPS、設定 CORS allow_origins 為白名單、在 Kubernetes 或 systemd 管理 uvicorn 進程、將 DATA_DIR 指向受控儲存，並設置備份/保留策略。

---

## 8. 規則驅動開發 (SDD) 區塊 — 系統規則、優先順序、觸發條件、狀態機、測試範例

- 狀態機（Task 狀態）
  - QUEUED → PENDING → TRANSCRIBING → SUMMARIZING → COMPLETED
  - 失敗分支：任一步驟 Exception → FAILED（若設定 continue_on_error=True，可選擇跳過或嘗試 fallback）

- 規則表（可直接轉為規則引擎表格）

| 規則 ID | 條件 / 觸發 | 優先 (P1/P2) | 系統行為 / 動作 | 預期狀態轉換 | 驗證範例 (unit/integration) |
|---|---:|:---:|---|---|---|
| R1 | 上傳檔案副檔不在 allowed_extensions | P1 | 拒絕上傳，HTTP 400 | 無 | POST /api/upload with .exe → 400 |
| R2 | 檔案大小 > MAX_FILE_SIZE_MB | P1 | 拒絕，HTTP 413 | 無 | 上傳 > 200MB → 413 |
| R3 | 佇列長度 >= QUEUE_MAX_SIZE | P1 | 拒絕新任務，HTTP 503 | 無 | 模擬填滿 queue → 上傳回 503 |
| R4 | 任務從 QUEUED 取出且 processing < MAX_CONCURRENT_TASKS | P1 | 設為 PENDING 並開始處理 | QUEUED→PENDING | 檢查 task_queue.get_next_task() 行為 |
| R5 | 音檔 path 不在 uploads_dir 範圍 | P1 | 驗證失敗，拋錯 | FAILED | TaskProcessor handle with manipulated filename → error |
| R6 | 轉錄成功但摘要失敗 | P2 | 使用逐字稿作為結果並標記警告 | TRANSCRIBING→COMPLETED(但摘要為 transcript) | 模擬 summarizer.summarize 拋錯 |
| R7 | MLX 可用且平台為 macos → 使用 MLX，否則 faster-whisper | P1 | 選擇後端 | internal | 模擬 platform 與後端選擇，驗證 transcribe 選路徑 |
| R8 | 轉錄後必卸載模型 | P1 | 調用 _unload_model 並清理 GPU | internal | 用 Spy 檢查 _unload_model 被呼叫 |
| R9 | system_prompt 不存在/不符合語言規則 | P2 | log error 並依設定決定是否中止（main.py） | internal | config 無 prompt → log error 與退出（main CLI） |
| R10 | WebSocket 心跳超時 (30s) | P2 | 發送當前狀態；若任務完成則關閉連線 | internal | 連接後不發送 ping，觀察伺服端每 30s 發送更新 |

- 將規則落地為測試（策略）
  - 單元測試（pytest + monkeypatch）
    - Mock FileManager.validate_file / validate_file_size 測試 R1/R2。
    - Mock task_queue 以測試 R3、R4 queue 行為。
    - Spy / monkeypatch transcription_service._unload_model() 檢查 R8。
    - Mock OllamaClient.generate 以測試 summarizer 的分段合併與驗證流程（R6）。
  - 整合測試（pytest + TestClient / uvicorn）
    - 啟動 FastAPI TestClient 或在 CI 啟動 uvicorn，提交小檔案（tests/test_audio/test1_5sec.wav），等待 WebSocket 進度至 100，並檢查 outputs 檔案存在。
    - 模擬 Gemin­a API 不可用並驗證 /api/upload 在 cloud 模式會返回 400（routes.py 有該檢查）。
  - E2E（CI）
    - 使用 scripts/test_full_pipeline.py（若存在）或 tests/test_end_to_end.py，覆蓋真實 transcribe + summarizer 行為（或使用受控 model mock）。

---

## 9. 測試與驗證策略（建議）
- 單元測試重點
  - file_manager.validate_file、validate_file_size、get_file_hash、save_transcript_cache
  - queue_manager.add_task / get_next_task / cancel_task / get_queue_status（競態情境）
  - transcription_service._get_backend 與 _load/_unload 行為（模擬不同平台）
  - summarizer 的 _split_text、_summarize_long_text 與 _validate_summary（對長短文本驗證）
- 整合測試重點
  - 上傳檔案（/api/upload）→ 取得 task_id → 使用 WebSocket 監聽 /ws/tasks/{task_id} → 檢查最終 outputs 檔案
  - health check quick=true 與 quick=false 的差異（避免長時間裝置偵測阻塞）
- Mock 與隔離
  - 使用 monkeypatch 替換 OllamaClient.generate 與 transcription_service.transcribe 以穩定測試與避免外部依賴（模型下載、GPU）。
- 性能測試
  - 單檔 1 分鐘音訊在 MPS/CUDA/CPU 分別的處理時間，作為基準（README 中有估值）。
- 測試資料
  - 使用 tests/test_audio/* 的短音檔作為上傳樣本，並在 CI 中設置小型 LLM mock。

---

## 10. 安全、錯誤處理、限制與運維建議

- 已實作安全措施（可驗證）
  - 路徑安全檢查（禁止 .. 與斜線）、副檔過濾、NUL 檢查（backend/services/file_manager.py）
  - 請求超時（TimeoutMiddleware，30s），避免 GPU 滿載阻塞 HTTP handler（backend/main.py）
  - 日誌結構化與獨立 error 日誌（backend/core/logger.py）
- 建議增強項目
  - API 身份驗證（API Key / OAuth）保護 /api/upload 與 /storage/cleanup 等管理端點
  - CORS 白名單（目前 allow_origins=["*"]，生產環境務必限制）
  - Rate limiting（上傳次數、IP 限流）
  - 把 Gemini API Key 與機敏資訊放入 secrets manager（不要放 .env 或 commit）
  - 加入監控與 alert（失敗率超過閾值、queue 長度持續增加）
  - 實作更細緻的儲存加密（若會保存敏感會議資料）
- 錯誤回復/容錯
  - 轉錄或摘要失敗 → TaskProcessor 會將任務標記為 FAILED 並推播 WebSocket；摘要失敗時會 fallback 為逐字稿（可接受且可測試）
  - 建議新增後台重試策略（exponential backoff），並在錯誤類型上區分可重試 / 不可重試

---

## 11. 附錄：主要檔案清單、重要設定、常用指令

- 主要檔案（最小集合）
  - backend/main.py — FastAPI 啟動點
  - backend/api/routes.py — REST API
  - backend/api/websocket.py — WebSocket
  - backend/services/queue_manager.py — 排隊邏輯
  - backend/services/task_processor.py — 任務協調
  - backend/services/transcription.py — 轉錄抽象
  - backend/services/summarization.py — 摘要控制
  - backend/services/file_manager.py — 檔案管理與清理
  - backend/core/config.py — 設定（DEFAULT_SYSTEM_PROMPT 等）
  - src/ollama_client.py — Ollama 客戶端
  - src/whisper_transcriber.py — Whisper 轉錄跨平台支援
  - src/summarizer.py — MeetingSummarizer 與 MarkdownFormatter
  - tests/ — 單元與整合測試範例
- 重要設定（快速取用）
  - DATA_DIR（預設 /Users/hsiaojohnny/dev/convert/data）
  - MAX_FILE_SIZE_MB（預設 200）
  - QUEUE_MAX_SIZE（預設 50）
  - MAX_CONCURRENT_TASKS（預設 1）
  - DEFAULT_SYSTEM_PROMPT（內含繁體中文輸出約束）
- 常用指令
  - 安裝依賴：pip install -r requirements.txt --prefer-binary
  - 啟動開發伺服器：uvicorn backend.main:app --host 0.0.0.0 --port 9527 --reload
  - 執行測試：pytest -q
  - 產生環境驗證（repo 中 scripts 可能存在）：python scripts/verify_env.py
  - 啟動/停止服務：./start_service.sh

---

## 12. 交接與後續建議（短期／中期）
- 短期（可立即執行）
  - 新增 API 身份驗證（API Key）；在 routes.py 中加入依賴驗證中介層。
  - 在 CI 中加入 LLM 與 Whisper 層的 mocks，確保 PR 驗證快速且穩定。
  - 把 CORS 從 "*" 改為白名單環境變數驅動。
- 中期（產品化）
  - 支援水平擴展（排隊與任務分散至工作者層），可用 Redis / Celery 改造 TaskQueue。
  - 加入儲存金鑰管理（Secrets Manager）、日誌上報（ELK / Datadog）與自動備份策略。
  - 提供 RBAC 與多租戶隔離（若需）。

---

### 第一性原理分析（結論式、可驗證）
- 需求最小單位：將語音轉文字（可驗證：transcribe 返回非空文字）→ 再以語意模型生成結構化文檔（可驗證：輸出包含 # 會議記錄 標頭與「待辦事項」表格）。
- 核心約束：資源（GPU/RAM）有限、LLM 呼叫延遲不可預知、輸入檔案可變。結果：系統採取「排隊 + 模型載入/卸載 + 超時保護 + 本地快取」策略（在程式碼中皆有實作）。
- 測試可驗證假設：以小音檔在不同裝置上測試轉錄時間與輸出完整性；以 mock LLM 驗證 prompt 約束（繁中、欄位必填）是否落實。

