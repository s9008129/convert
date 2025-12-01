# 變更日誌

所有本專案的重要變更都會記錄在此檔案。

本檔案遵循 [Keep a Changelog](https://keepachangelog.com/zh-TW/1.0.0/) 格式，
本專案遵循 [語義化版本控制](https://semver.org/lang/zh-TW/) 規範。

## [2.3.7] - 2025-12-01

### 重大修復 🔧

此版本修復雲端模式連線問題並新增自動清理機制，確保系統長期穩定運行。

### 修復 🐛
- **修復雲端模式 Gemini API 連線失敗問題**
  - Docker Compose 環境變數載入順序問題
  - `env_file` 正確載入 `.env` 檔案中的 `GEMINI_API_KEY`
  - 移除 `environment` 中覆蓋 `.env` 的變數設定

### 新增功能 ✨
- **自動檔案清理機制** - 避免上傳和暫存檔塞爆空間
  - 上傳檔案保留 1 天後自動清理
  - 輸出結果保留 7 天後自動清理
  - 快取檔案保留 30 天後自動清理
  - 每日凌晨 3:00 自動執行清理任務
  - 服務啟動時執行一次清理（清理重啟前的過期檔案）

- **儲存空間管理 API**
  - `GET /api/storage/stats` - 查看儲存空間使用統計
  - `POST /api/storage/cleanup` - 手動觸發檔案清理

### 技術改進 🔧
- `file_manager.py`: 新增 `cleanup_old_files()`、`run_cleanup()`、`start_cleanup_scheduler()` 方法
- `main.py`: 整合檔案清理排程器到應用程式生命週期
- `routes.py`: 新增儲存空間統計和手動清理 API 端點
- `docker-compose-mac.yml`: 修復環境變數載入問題

### 驗證測試 ✅
- Gemini API 連線測試通過
- 自動清理排程器正常運作
- 儲存空間統計 API 正常回應

---

## [2.3.6] - 2025-12-01

### 模型升級與簡化 🚀

此版本升級 Whisper 模型並簡化系統架構，移除不必要的簡繁轉換步驟。

### 變更 🔄
- **Whisper 模型從 large-v3 改為 medium** 
  - medium 模型直接輸出台灣繁體中文，無需後處理
  - 模型大小從約 3GB 降至約 1.5GB，更節省資源
  - 轉錄速度提升，品質依然優秀

- **本地 LLM 模型從 gemma3:12b 改為 gemma3:27b-it-qat**
  - 使用 QAT (Quantization Aware Training) 量化版本
  - 更佳的繁體中文摘要品質
  - 更好的台灣用語理解

### 移除功能 ❌
- **移除 OpenCC 簡繁轉換模組** 
  - whisper-medium 已直接輸出繁體中文，無需額外轉換
  - 減少依賴項目，簡化系統架構
  - 移除 `opencc-python-reimplemented` 套件

### 技術改進 🔧
- `transcription.py`: 移除 OpenCC 相關程式碼
- `requirements.txt`: 移除 OpenCC 依賴
- `config.yaml`: 更新模型建議說明
- `docker-compose*.yml`: 更新環境變數設定
- `Dockerfile*`: 預載 medium 模型

### 驗證測試 ✅
- 模擬政府會議音檔測試通過
- 繁體中文逐字稿輸出正確
- Ollama 摘要生成正常

---

## [2.3.5] - 2025-12-01

### 重大修復 🔧
- **修復處理結果顯示** - 任務完成後正確顯示完整摘要和逐字稿
  - 新增 `preview` 欄位到 `ProgressMessage` schema
  - 修改 `task_processor.py` 在任務完成時發送結果預覽
  - 前端限制預覽顯示長度為 2000 字元，避免效能問題

- **修復雲端模式進度條和排隊顯示** - 與本地模式行為一致
  - 修改 `handleProgressUpdate()` 正確處理排隊狀態
  - 當狀態為 `queued` 時顯示排隊區塊而非進度條
  - 提取 `updateQueueDisplay()` 函數減少代碼重複

### 移除功能 ❌
- **移除重新處理功能** - 將「重新處理」按鈕改為「重新開始」按鈕

### 技術改進 🔧
- `schemas.py`: 新增 `preview` 欄位到 `ProgressMessage`
- `task_processor.py`: 修改 `_update_progress()` 支援 `preview` 參數
- `app.js`: 提取 `updateQueueDisplay()` 函數，改善代碼可維護性
- `index.html`: 更新 cache busting 版本號

---

## [2.3.4] - 2025-12-01

### 移除功能 ❌
- **移除重試功能** - 簡化 UX，移除複雜且不穩定的重試機制
  - 移除 `retryBtn` 按鈕
  - 移除 `lastFile`、`retryAttempts`、`maxRetryAttempts` 狀態
  - 錯誤頁面改為「重新開始」按鈕，直接重置 UI

### 技術改進 🔧
- `app.js`: 簡化 `uploadFile()` 函數，移除 `isRetry` 參數
- `app.js`: 簡化 `showError()` 函數，移除 `allowRetry` 參數
- `index.html`: 將「重試」按鈕改為「重新開始」按鈕

---

## [2.3.3] - 2025-12-01

### UX 優化：雲端狀態顯示與模式鎖定 🎨

### 新增功能 ✨
- **雲端模式狀態顯示** - 動態檢測 Gemini API 連線狀態
  - 已就緒：綠色「使用：Gemini API（已就緒）」
  - 連線失敗：紅色「使用：Gemini API（連線失敗）」

- **模式鎖定機制** - 上傳檔案後自動鎖定模式選擇
  - 🔒 處理中顯示鎖頭圖示
  - 防止使用者誤操作切換模式
  - 完成或失敗後自動解鎖

### 改進 🔧
- 前端 UI 一致性：本地/雲端模式都顯示連線狀態
- CSS 新增 `.mode-card.locked` 和 `.mode-lock-hint` 樣式

---

## [2.3.2] - 2025-12-01

### UX 優化：本地模式抽象化 🎨

此版本簡化使用者介面，移除底層技術細節，讓使用者只需關注「本地模式」vs「雲端模式」。

### 改進 🔧
- **本地模式自動偵測** - 後端自動選擇可用的本地 LLM 引擎
  - 優先使用 Ollama
  - 若 Ollama 不可用，自動切換到 LM Studio
  - 使用者無需了解底層技術細節

- **前端 UI 抽象化**
  - 移除「Ollama」字樣，改為「本地 LLM」
  - 動態顯示「已就緒」或「未偵測」狀態
  - 統一的本地/雲端模式選擇體驗

### 技術改進 ✅
- `summarization.py`: 新增 `_summarize_with_local_llm()` 自動選擇引擎
- `schemas.py`: 簡化 `ProcessingMode` 為 `LOCAL`/`CLOUD` 兩種
- `app.js`: 動態更新本地模式狀態顯示

---

## [未發布] - TBD

### 重要修復 🔧
- **修復重新處理功能無效** - 失敗後的重試機制
  - `retryBtn` 現在能正確重新上傳檔案
  - 支援最多 3 次智能重試
  - 指數退避策略防止過度請求
  - UI 清晰顯示重試次數和進度

### 新增功能 ✨
- **LM Studio API 支援** - 新增第三種本地 LLM 選項
  - OpenAI 相容 API 介面
  - 預設模型：`gpt-oss-20b`
  - 透過 `host.docker.internal:1234` 連接主機服務
  - 與 Ollama 和 Gemini 無縫整合

### 改進 🔧
- **前端重試邏輯優化**
  - 保存最後上傳的檔案以支援重試
  - 完整的錯誤處理和用戶反饋
  - 遵循業界最佳實踐（p-retry 標準）

---

## [2.3.0] - 2025-11-30

### 台灣繁體中文轉錄支援 🇹🇼

此版本重點修正 Whisper 轉錄輸出簡體中文的問題，確保輸出為台灣繁體中文（正體中文）。

### 新增功能 ✨
- **OpenCC 簡繁轉換器** - 添加 `opencc-python-reimplemented` 套件
  - 使用 `s2twp` 模式（簡體 → 台灣繁體 + 詞彙轉換）
  - 自動將 Whisper 輸出轉換為台灣用語

### 改進 🔧
- **Whisper 轉錄參數優化**
  - 新增 `language="zh"` 明確指定中文語言
  - 新增 `initial_prompt` 使用繁體中文句子引導輸出
  - 提示詞: "以下是台灣繁體中文的會議逐字稿，請使用正體中文輸出。"

### 技術說明 📝
- **問題根因**: Whisper 不區分 zh-TW/zh-CN，預設輸出傾向簡體中文
- **解決方案**: 雙重保障
  1. `initial_prompt` 引導 Whisper 輸出繁體
  2. `OpenCC` 後處理確保 100% 繁體中文輸出

---

## [2.2.2] - 2025-11-30

### CI/CD 修正 🔧

- **GitHub Actions 升級** - 修正 `actions/upload-artifact@v3` 已棄用導致 CI 失敗的問題
  - 升級 `actions/upload-artifact` 從 v3 到 v4
  - 符合 GitHub 2024-04-16 棄用公告要求

---

## [2.2.1] - 2025-11-30

### 前端優化與 UX 改善 🎨

此版本重點優化前端使用者體驗，改善排隊狀態顯示和 WebSocket 即時進度推送。

### 新增功能 ✨
- **WebSocket 即時進度推送** - 後端主動推送進度更新到前端
  - `task_processor.py` 新增 `_update_progress()` 方法
  - 進度更新時自動推送 WebSocket 訊息
  - 任務完成/失敗時推送最終狀態

- **開發模式 Volume Mount** - 前端/後端程式碼即時同步
  - 前端變更只需刷新瀏覽器
  - 後端變更只需重啟容器
  - 不需重建 Docker 映像檔

### 改進 🔧
- **排隊狀態顯示優化**
  - 移除不準確的「預估等待時間」
  - 改為顯示「狀態」(即將處理/排隊中)
  - 更直覺的使用者體驗

- **前端 JavaScript 穩定性**
  - 所有 DOM 操作添加 null 安全檢查
  - 避免元素不存在時的 JavaScript 錯誤
  - Cache Busting 版本號確保載入最新資源

- **Docker Compose 優化**
  - 移除過嚴格的資源限制
  - 新增 `env_file` 設定支援環境變數
  - Volume Mount 支援開發模式

### 修正 🐛
- 修正 WebSocket 進度不即時更新的問題
- 修正 `Cannot set properties of null` JavaScript 錯誤
- 修正 Gemini API Key 環境變數未載入問題
- 修正 Docker 容器記憶體不足導致 Whisper 模型載入失敗

### 技術改進 ✅
- WebSocket 連接管理器 (`connection_manager`) 整合到任務處理器
- 使用 `asyncio.run_coroutine_threadsafe()` 實現同步回調觸發異步推送
- 靜態資源添加版本號防止瀏覽器快取

---

## [2.2.0] - 2025-11-29

### 🔒 重大變更：Docker 服務完全隔離

此版本重點解決 Docker 服務與其他專案混合的問題，確保 MeetingScribe 完全獨立運行。

### 新增功能 ✨
- **macOS 專用部署** - 新增 MAC Docker 部署指南和專用配置檔案
  - `docker/Dockerfile.mac` - macOS 專用映像
  - `docker/docker-compose-mac.yml` - macOS 專用編排
  - `scripts/start-mac.sh` - macOS 一鍵啟動腳本
  - `scripts/restart-mac.sh` - macOS 服務重啟腳本

### 安全性修正 🔐 (首要任務)
- **Docker 服務完全隔離**
  - 使用獨立的 `COMPOSE_PROJECT_NAME` (meetingscribe)
  - 使用獨立的 Docker 網路 `meetingscribe-network` (172.30.0.0/16)
  - 所有容器、Volume、網路都使用 `meetingscribe-` 前綴
  - 設定資源限制 (CPU: 8核心, 記憶體: 16GB)
  - 確保絕對不影響 Docker 中其他運行的服務

### 技術改進 ✅
- Docker Compose 配置升級到 v2.2 版本
- 新增獨立 IP 範圍設定，避免與其他專案衝突
- 新增容器標籤 (labels) 方便識別和管理
- 優化健康檢查配置

### 文件更新 📚
- 新增 `doc/MAC_Docker部署指南.md` - macOS 完整部署文件
- 更新 README.md 新增隔離保證說明
- 更新系統開發及實作規劃.md

---

## [2.1.3] - 2025-11-29

### 新增功能 ✨
- **快速部署指南** - 新增專為非技術人員設計的 Windows Docker 部署指南
  - 完整的 Docker Desktop 安裝步驟
  - Ollama 安裝與模型下載說明
  - NVIDIA GPU 驅動設定指引
  - 圖文並茂的操作流程
  - 常見問題與解決方案

### 文件更新 📚
- 更新 README.md 新增快速部署指南連結
- 更新系統開發及實作規劃.md 至最新狀態
- 同步 GitHub 最新程式碼修正

---

## [2.1.2] - 2025-11-29

### 安全性修正 🔐
- [High] **路徑遍歷攻擊防護強化** - 新增空字節注入檢查，防止更多類型的路徑攻擊
- [High] **檔案刪除路徑驗證** - 限制刪除操作只能在允許的目錄內（uploads/outputs/cache）
- [High] **結果檔案路徑安全處理** - 清理檔名，只保留安全字符（英數字、底線、連字號、空格、點號和中文）
- [Medium] **快取檔案 Hash 格式驗證** - 驗證 hash 必須是 64 字元的十六進位字串
- [Medium] **API Key 格式驗證強化** - 使用正則表達式驗證，只允許英數字符、底線和連字號
- [Medium] **Hash 演算法升級** - whisper_transcriber 中的檔案 hash 從 MD5 改為 SHA256

### 邏輯錯誤修正 🐛
- **WebSocket 心跳記憶體洩漏修正** - 使用獨立變數追蹤 interval ID，連線關閉或重置時清理
- **空摘要結果檢查** - LLM 回傳空結果時拋出明確的錯誤訊息
- **任務取消邏輯完善** - 正在處理中的任務無法取消，API 回傳明確錯誤訊息
- **轉錄結果空值檢查** - 避免空逐字稿進入摘要階段
- **檔案存在性檢查** - 處理任務前驗證檔案是否存在
- **CPU 降級無限遞迴防護** - 加入 max_retries 參數限制重試次數
- **摘要品質驗證強化** - 加入錯誤指標檢查，避免錯誤訊息被當作有效摘要

### 程式碼品質改善 ✅
- **CORS 設定安全提醒** - 加入 TODO 註解提醒生產環境應設定特定域名
- **前端檔案輸入重置** - 重置 UI 時清空檔案輸入，避免重複上傳
- **結果載入錯誤處理** - 加入 HTTP 回應狀態檢查

### 文件更新 📚
- 更新 CHANGELOG.md 記錄所有變更
- 更新 README.md 版本號

---

## [2.1.1] - 2025-11-29

### 新增功能 ✨
- 🐳 **Docker 跨平台部署支援** - 一包帶走，直接部署至 Windows/macOS/Linux
- 🔒 **雙模式處理系統**
  - 本地模式：Ollama + Gemma3:12B（完全離線，資料不外傳）
  - 雲端模式：Gemini API（高品質摘要，需網路）
- 📝 **User Prompt 自訂功能** - 使用者可自訂會議記錄格式和內容
- 📊 **智能排隊系統** - FIFO 公平排隊，前端即時顯示排隊位置和預估時間
- 🎛️ **自動裝置偵測與降級** - CUDA GPU / Apple MPS / CPU 智能選擇和自動降級
- 🛡️ **資源隔離設計** - Docker 容器完全隔離，不影響宿主機和其他服務
- 🔧 **非技術人員友善管理腳本**
  - `setup-api-key.ps1` - 圖形化 API Key 設定工具
  - `restart-service.ps1` - 安全重啟服務，自動檢測健康狀態
  - `health-check.ps1` - 系統健康檢查和診斷
  - `deploy.ps1` - 一鍵部署管理工具

### 變更 🔄
- 🏗️ **架構重構** - 採用模組化後端設計（FastAPI），提高可維護性
- 🎨 **全新前端介面** - Apple 風格簡約設計，支援 Markdown 預覽
- ⚙️ **參數化配置系統** - 所有設定可透過環境變數調整，支援動態配置
- 📦 **Docker Compose** - 支援服務隔離和多容器協調

### 安全性修正 🔐
- [Critical] 修正前端 XSS 漏洞 - 使用 `textContent` 替代 `innerHTML`
- [High] 強化 API Key 驗證 - 新增格式和長度檢查，防止無效配置
- [High] 修復路徑遍歷漏洞 - 檔案名稱驗證防止目錄脫逃攻擊
- [Medium] API Key 安全存儲 - 使用 Pydantic `SecretStr` 保護敏感資料
- [Medium] Hash 演算法升級 - 從 MD5 改為 SHA256，增強完整性驗證
- [Medium] 檔案上傳驗證強化 - 副檔名白名單和檔案大小檢查

### 技術改進 ✅
- 消除程式碼重複，提高可維護性（DRY 原則）
- API Key 檢查邏輯統一，集中管理驗證流程
- 改善異常處理的一致性和完整性
- WebSocket 心跳機制確保連線穩定性
- Ollama 和 Gemini API 超時保護和自動降級
- 改善大檔案上傳的記憶體使用效率

### 文件更新 📚
- 完整重寫 README.md，包含完整的快速開始、部署指南、API 文件
- 新增快速入門指南
- 更新規劃和實作計劃，補充變更日誌章節
- 新增 Docker 部署經驗分享

### 已修正的問題 🐛
- 修正 WebSocket 連線穩定性問題
- 改善大檔案上傳時的記憶體洩漏
- 修正 GPU 記憶體不足時的降級邏輯
- 解決排隊系統中的競態條件

---

## [2.1.0] - 2025-11-01

### 新增功能 ✨
- 初始版本發布
- Whisper 語音轉文字功能
- 基本的會議摘要生成
- FastAPI 後端架構
- 簡單的前端介面

---

## [1.0.0] - 2025-10-15

### 新增功能 ✨
- 專案初始化
- 基本的語音處理流程

---

## 版本對比

| 版本 | 發布日期 | 主要特色 | 狀態 |
|------|---------|----------|------|
| 2.2.0 | 2025-11-29 | Docker 服務完全隔離、macOS 專用部署 | ✅ 現行版本 |
| 2.1.3 | 2025-11-29 | 快速部署指南、文件更新 | 📦 已棄用 |
| 2.1.2 | 2025-11-29 | 安全性加固、邏輯錯誤修正、程式碼品質改善 | 📦 已棄用 |
| 2.1.1 | 2025-11-29 | Docker 跨平台、雙模式、排隊系統、安全加固 | 📦 已棄用 |
| 2.1.0 | 2025-11-01 | 初始版本、基本功能 | 📦 已棄用 |

---

## 升級指南

### 從 2.1.3 升級到 2.2.0

1. **重要**：此版本重新設計 Docker 配置以確保隔離
   ```powershell
   # 先停止舊服務
   docker compose down
   
   # 重新建構並啟動
   cd scripts
   .\deploy.ps1 build
   .\deploy.ps1 up
   ```

2. **驗證隔離**
   ```powershell
   # 確認容器名稱正確
   docker ps --filter "name=meetingscribe"
   
   # 確認網路獨立
   docker network ls | findstr meetingscribe
   ```

### 從 2.1.1 升級到 2.1.2

1. **直接升級**
   ```powershell
   cd scripts
   .\deploy.ps1 build
   .\deploy.ps1 restart
   ```

2. **驗證升級**
   ```powershell
   .\health-check.ps1
   ```

### 從 2.1.0 升級到 2.1.1

1. **備份資料**
   ```bash
   cp -r data/uploads data/uploads.backup
   cp -r data/outputs data/outputs.backup
   ```

2. **更新 Docker 映像**
   ```powershell
   cd scripts
   .\deploy.ps1 build
   ```

3. **重啟服務**
   ```powershell
   .\deploy.ps1 restart
   ```

4. **驗證升級**
   ```powershell
   .\health-check.ps1
   ```

### 向後相容性
- ✅ 舊版 .env 檔案向後相容
- ✅ data/ 目錄結構保持一致
- ✅ API 端點保持穩定

---

## 已知問題

### 當前版本 (2.1.1)
- 暫無已知問題

### 計劃修復
- [ ] 支援批次上傳（目前禁用）
- [ ] Web UI 暗黑模式支援
- [ ] 多語言支援（目前僅中文）
- [ ] 自訂摘要模版

---

## 未來計劃 🚀

### 短期 (1-3 個月)
- [ ] 整合更多本地 LLM 模型（Llama 2, Mistral 等）
- [ ] 支援更多音訊格式（FLAC, AAC 等）
- [ ] 性能最佳化和效能測試

### 中期 (3-6 個月)
- [ ] 整合 OpenAI Whisper API
- [ ] 支援視訊檔案摘要
- [ ] 用戶帳號和歷史記錄
- [ ] 高級排隊和優先級系統

### 長期 (6+ 個月)
- [ ] 多語言支援
- [ ] 實時直播轉錄
- [ ] AI 驅動的討論分析
- [ ] 商業版本和付費功能

---

## 貢獻者

感謝所有為本專案貢獻的人員！

---

## 授權

本專案採用 MIT 授權。詳見 [LICENSE](LICENSE)。

---

**最後更新**: 2025-12-01  
**維護者**: hsiaojohnny
