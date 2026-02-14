# 功能規格：MeetingScribe 會議轉錄與摘要系統

**版本**：v1.0  
**建立日期**：2026-02-14  
**適用範圍**：`/Users/hsiaojohnny/dev/convert`

---

## 1. 專案定位與核心功能

MeetingScribe 是一套將會議音訊/視訊檔案轉換為結構化會議紀錄（Markdown）的系統，目標是縮短人工整理逐字稿與會議結論的時間成本，並提供可部署於本地或雲端推理模式的彈性。  
系統核心由 FastAPI 後端、Vanilla JS 前端、Whisper 轉錄引擎、LLM 摘要引擎、FIFO 任務佇列與 WebSocket 即時進度通知構成。  
它解決的本質問題是：在資源有限（GPU/CPU）、檔案量不穩定、語音品質不一的真實情境下，如何穩定、可觀測地交付可用會議摘要。

---

## 2. Clarifications

### Session 2026-02-14

- Q: 本地模式是固定 Ollama 嗎？  
  A: 不是；程式會根據平台與健康檢查結果在 Ollama / LM Studio 之間自動選擇並回退（`backend/services/summarization.py`）。

- Q: 雲端模式是否一定可用？  
  A: 否；需先配置 `GEMINI_API_KEY`，否則 `/api/upload` 在 cloud 模式會直接拒絕請求。

- Q: 系統是同步處理多任務嗎？  
  A: 預設為單並行（`MAX_CONCURRENT_TASKS=1`）+ FIFO 排隊；同時提供任務位置與預估等待時間。

- Q: 為什麼要 WebSocket 而不是只靠輪詢？  
  A: 因為轉錄/摘要是長任務，WebSocket 讓前端即時接收狀態、排隊位置、完成預覽，降低使用者不確定感。

- Q: 任務失敗時是否整個流程作廢？  
  A: 轉錄失敗會任務失敗；摘要失敗則有降級策略，仍可輸出逐字稿結果避免完全中斷。

---

## 3. 使用者情境與測試

### User Story 1 - 上傳檔案並取得會議紀錄（Priority: P1）

作為一般使用者，我要能上傳會議音訊並在處理完成後下載 Markdown 紀錄，減少手動整理時間。

**為什麼此優先級**：這是產品主價值鏈路（上傳→處理→下載）。

**獨立測試**：呼叫 `POST /api/upload`、輪詢或 WebSocket 追蹤、最後呼叫 `GET /api/tasks/{task_id}/result`。

**Given-When-Then 驗收情境**：
1. **Given** 上傳副檔名與大小皆合法，**When** 呼叫上傳 API，**Then** 回傳 `task_id`、排隊位置與預估等待秒數。  
2. **Given** 任務完成，**When** 下載結果檔，**Then** 應取得可讀 Markdown 且檔名包含 `task_id`。  
3. **Given** 不支援檔案格式或超過大小限制，**When** 上傳，**Then** API 應回傳 4xx 與明確錯誤訊息。

---

### User Story 2 - 即時追蹤排隊與處理進度（Priority: P1）

作為等待結果的使用者，我要看到排隊位置、處理階段與進度百分比，以便決定是否等待或稍後再看。

**為什麼此優先級**：長任務若無透明進度，會大幅提升流失率與重複提交風險。

**獨立測試**：連線 `ws/tasks/{task_id}`，驗證可收到 queued / transcribing / summarizing / completed 狀態。

**Given-When-Then 驗收情境**：
1. **Given** 任務尚在佇列，**When** 建立 WebSocket，**Then** 可收到目前 queue_position 與 queue_total。  
2. **Given** 任務進入處理，**When** 進度更新，**Then** 前端應即時顯示 stage 與 progress。  
3. **Given** 連線閒置，**When** 前端送出 `ping`，**Then** 後端回 `pong` 並保持連線。

---

### User Story 3 - 選擇本地或雲端摘要模式（Priority: P2）

作為有隱私與品質需求差異的使用者，我要在 local/cloud 間切換，依情境選擇成本、隱私與品質平衡。

**為什麼此優先級**：模式切換直接影響可用性與部署場景（離線/企業內網/外網）。

**獨立測試**：分別以 local 與 cloud 模式上傳；cloud 在無 API key 時須被拒絕。

**Given-When-Then 驗收情境**：
1. **Given** 選擇 local，**When** 後端檢查本地引擎，**Then** 依平台自動使用 LM Studio 或 Ollama 並可回退。  
2. **Given** 選擇 cloud 但未設定 API key，**When** 上傳，**Then** 回傳可理解的設定錯誤訊息。  
3. **Given** 選擇 cloud 且 key 正確，**When** 摘要執行，**Then** 應可產生有效摘要並完成任務。

---

### User Story 4 - 系統在資源緊繃下維持可服務（Priority: P2）

作為平台管理者，我要在 GPU 滿載或長任務執行時，系統仍能回應新請求而非整體卡死。

**為什麼此優先級**：這是多人同時使用時的穩定性底線。

**獨立測試**：在高負載下檢查 `TimeoutMiddleware` 是否在超時時回 503。

**Given-When-Then 驗收情境**：
1. **Given** 請求處理超過超時值，**When** 中介層攔截，**Then** 回傳 503 與建議重試訊息。  
2. **Given** 任務量增加，**When** 新任務加入，**Then** 仍可得到排隊資訊而非阻塞。

---

### User Story 5 - 檔案與快取自動清理（Priority: P3）

作為維運者，我要系統自動清理過期 uploads/outputs/cache，避免磁碟被長期任務耗盡。

**為什麼此優先級**：屬維運與成本優化，不影響核心單次流程。

**獨立測試**：建立過期檔案後執行 `run_cleanup()`，驗證刪除數與釋放空間統計。

**Given-When-Then 驗收情境**：
1. **Given** 檔案超過保留天數，**When** 清理任務執行，**Then** 應自動刪除並記錄釋放容量。  
2. **Given** 清理排程器啟動，**When** 到達排程時點，**Then** 自動執行清理且不中斷主服務。

---

### 邊緣案例

- 上傳檔名包含路徑遍歷字元（`../`、`\`、`\x00`）時必須拒絕。  
- 任務完成但結果檔不存在時，`/result` 應回 404 而非空白檔。  
- WebSocket 客戶端異常斷線時，連線管理器需清理 dead connections。  
- MLX-Whisper 未安裝時，macOS 路徑需可回退至 faster-whisper。  
- 摘要引擎失敗時需降級輸出逐字稿，避免任務全失敗。

---

## 4. 需求

### 功能需求（Functional Requirements）

- **FR-001**: 系統 MUST 提供 `POST /api/upload` 接收單檔音訊/視訊上傳。  
- **FR-002**: 系統 MUST 驗證檔名安全性（禁止路徑遍歷、空字元）。  
- **FR-003**: 系統 MUST 驗證副檔名僅限白名單格式。  
- **FR-004**: 系統 MUST 驗證上傳檔案大小不超過 `MAX_FILE_SIZE_MB`。  
- **FR-005**: 系統 MUST 將合法任務放入 FIFO 佇列並回傳 `task_id`。  
- **FR-006**: 系統 MUST 提供任務查詢 API 與排隊位置查詢 API。  
- **FR-007**: 系統 MUST 提供 WebSocket 端點即時推送進度、階段與排隊資訊。  
- **FR-008**: 系統 MUST 支援任務完成後下載 Markdown 結果檔。  
- **FR-009**: 系統 MUST 支援 local/cloud 兩種摘要模式。  
- **FR-010**: 系統 MUST 在 cloud 模式缺少 API key 時拒絕任務並回傳明確訊息。  
- **FR-011**: 系統 MUST 在 local 模式依平台選擇 LLM 提供者並支援回退策略。  
- **FR-012**: 系統 MUST 具備轉錄快取（依檔案 hash）以避免重複轉錄。  
- **FR-013**: 系統 MUST 在摘要失敗時提供降級輸出（逐字稿）以提高可用性。  
- **FR-014**: 系統 MUST 提供健康檢查端點回傳版本、裝置與引擎可用性。  
- **FR-015**: 系統 MUST 透過請求超時中介層避免長請求阻塞整體服務。  
- **FR-016**: 系統 MUST 對 uploads/outputs/cache 提供保留天數清理機制。  
- **FR-017**: 系統 MUST 產出結構化日誌（含一般、錯誤、JSON logs）。

---

## 5. 關鍵實體

- **TaskInfo**：任務主體，包含 `task_id`、檔名、狀態、進度、排隊位置、模式、錯誤訊息與時間戳。  
- **QueueStatus**：佇列快照，包含排隊數、處理中數、預估等待秒數、系統容量。  
- **ProgressMessage**：WebSocket 傳輸模型，包含狀態、進度、stage、queue 資訊與結果預覽。  
- **TranscriptionResult**：處理輸出抽象，包含 transcript、summary、耗時、字數、模型資訊。  
- **SystemSettings**：環境與執行參數集合（檔案限制、LLM 端點、Whisper 模型、路徑與日誌）。

---

## 6. 成功標準

- **SC-001**: 90% 以上合法上傳請求可成功建立任務（非 5xx）。  
- **SC-002**: 任務狀態更新端到端可見性達 100%（queued → final status 皆可查）。  
- **SC-003**: WebSocket 心跳連線在 30 秒週期內維持穩定，異常斷線可自動清理。  
- **SC-004**: `TimeoutMiddleware` 在超時情境下 100% 回傳 503，而非長時間無回應。  
- **SC-005**: 有快取命中時，轉錄耗時相較首跑降低至少 60%。  
- **SC-006**: 過期檔案清理可正確回報刪除數量與釋放空間，統計誤差小於 1%。  
- **SC-007**: 在缺少 `GEMINI_API_KEY` 的情境，cloud 任務 100% 被安全拒絕。  
- **SC-008**: 任務完成後結果檔可下載成功率達 99% 以上（檔案存在條件下）。

---

## 7. 第一性原理分析

### 7.1 問題本質分解

使用者真正要的不是「語音辨識」本身，而是「可行動的會議結論」。  
因此系統的不可省略原子能力是：

1. **可靠取得輸入**：安全接收檔案且防止惡意輸入。  
2. **可擴展的處理流程**：在有限 GPU/CPU 下，任務不能互相拖垮。  
3. **可理解的輸出**：輸出需有結構、可讀、可分享。  
4. **可觀測的執行**：長任務必須對使用者透明。  
5. **可持續的維運**：長期運轉需控制磁碟、錯誤與資源。

### 7.2 技術約束推導

- **約束 A：推理模型不可永遠可用**  
  本地服務（Ollama/LM Studio）與外部 API（Gemini）都可能失效，因此架構必須內建健康檢查、回退與降級輸出。  

- **約束 B：語音轉錄是重運算任務**  
  不可讓所有請求直接競爭 GPU；必須有 FIFO 佇列、並行上限與超時保護。  

- **約束 C：使用者對等待極度敏感**  
  任務若超過數十秒，沒有進度回饋就會造成重複提交；因此 WebSocket 不是附加功能，而是核心可用性機制。  

- **約束 D：檔案型服務天生有安全風險**  
  路徑遍歷與副檔名偽裝是基本攻擊面，檔案驗證必須在任何處理前執行。

### 7.3 設計決策（由原理到實作）

- 由「資源有限」推出 `TaskQueueManager`（FIFO + max concurrency）。  
- 由「長任務不透明」推出 `ProgressMessage + WebSocket`。  
- 由「引擎不穩定」推出 local/cloud 模式切換與 provider fallback。  
- 由「結果不可丟失」推出摘要失敗時使用逐字稿降級。  
- 由「維運成本」推出排程清理與結構化日誌。

### 7.4 風險與對策

- **風險**：第三方模型服務不可用。  
  **對策**：健康檢查、快取策略、模式切換與錯誤訊息明確化。  

- **風險**：高負載時 API 體感崩潰。  
  **對策**：超時中介層 + 排隊機制 + 快速健康檢查（quick mode）。  

- **風險**：長期運行導致儲存膨脹。  
  **對策**：分目錄保留週期與每日清理排程。  

---

## 附錄：可追溯驗證來源

- 核心服務：`backend/main.py`, `backend/api/routes.py`, `backend/services/*`  
- 配置：`backend/core/config.py`, `config.yaml`, `config.macos.yaml`  
- 前端互動：`frontend/js/app.js`  
- 測試：`tests/test_api_routes.py`, `tests/test_queue_manager.py`, `tests/test_websocket.py`  
- 版本與進度：`VERSION`, `CHANGELOG.md`, `README.md`
