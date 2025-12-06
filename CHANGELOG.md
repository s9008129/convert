# MeetingScribe - 變更紀錄

## [v3.5.3] - 2025-12-06

### 🐛 重大修復

#### 1. 服務連線異常修復（macOS Native 模式）

**問題描述**：
- Safari 無法連接到服務器 `127.0.0.1:9527`
- 錯誤訊息：「Safari 無法打開網頁」
- 根本原因：Docker 容器 `meetingscribe-app` 已停止但佔用配置，導致 Native 服務無法正常啟動

**診斷結果**：
```bash
# Docker 容器狀態
meetingscribe-app (meetingscribe:mac)
  - 狀態: Exited (0)
  - 埠號綁定: 9527
  - 影響: 阻止 Native 服務啟動

# Native 服務狀態
  - PID 檔案存在但程序已終止
  - 埠號 9527 未被監聽
```

**修復內容**：

1. **安全移除衝突的 Docker 容器**
   - 移除已停止的 `meetingscribe-app` 容器
   - 釋放埠號 9527 綁定
   - **不影響 Windows Docker 版本**

2. **重新啟動 Native 服務**
   - 使用 `start_service.sh` 啟動服務
   - 驗證服務健康狀態
   - 確認 MPS 加速正常運作

3. **新增 Docker 清理腳本** (`scripts/cleanup_docker.sh`)
   - 自動檢測並移除 macOS 的 MeetingScribe Docker 容器
   - 可選擇性移除 Docker 映像檔
   - 包含安全檢查，僅在 macOS 系統執行
   - **完全不影響 Windows 版本**

**修復後狀態**：
```bash
✅ 服務狀態: healthy
✅ 版本: 3.5.2
✅ GPU: Apple MPS (Metal Performance Shaders)
✅ 埠號: 9527 (LISTEN)
✅ LM Studio: 可用
✅ Gemini API: 可用
```

**安全保證**：
- ✅ 僅移除 macOS 本地的 Docker 容器
- ✅ Windows Docker 版本完全不受影響
- ✅ Docker 映像檔保留（可手動清理）
- ✅ 所有配置檔案未變更

## [v3.5.2] - 2025-12-06

### 🐛 重大修復

#### 1. MLX-Whisper 模型路徑與配置檔案修復

**問題描述**：
- macOS 版本轉錄時出現 404 Client Error
- 錯誤訊息：`Repository Not Found for url: https://huggingface.co/api/models/medium/revision/main`
- 根本原因：配置檔案名稱錯誤 + 模型路徑格式不正確 + 後端識別邏輯缺陷

**修復內容**：

1. **配置檔案重新命名** (`config.mac.yaml` → `config.macos.yaml`)
   - 問題：程式碼尋找 `config.macos.yaml`，但實際檔案為 `config.mac.yaml`
   - 修復：將 `config.mac.yaml` 重新命名為 `config.macos.yaml`
   - 影響：平台配置載入邏輯現在能正確合併 macOS 專屬設定

2. **Whisper 配置結構優化** (`config.macos.yaml`)
   - 修改前：`whisper.backend: mlx-whisper` + 缺少 `mlx.model` 配置
   - 修改後：新增完整的 `whisper.mlx` 區塊
   ```yaml
   whisper:
     backend: mlx-whisper
     mlx:
       model: mlx-community/whisper-medium  # 使用本地已安裝模型
       device: mps
       fp16: true
       language: zh
   ```
   - 優先使用本地已安裝的 `mlx-community/whisper-medium` 模型

3. **後端識別邏輯強化** (`backend/services/transcription.py`)
   - 新增後端名稱正規化邏輯：
   ```python
   if 'mlx' in backend.lower():
       self._backend = 'mlx'
   elif 'faster' in backend.lower():
       self._backend = 'faster-whisper'
   ```
   - 解決 `mlx-whisper` vs `mlx` 字串比對不匹配問題

4. **MLX-Whisper API 參數修正**
   - 修復前：將 `language` 作為位置參數傳遞（不正確）
   - 修復後：`language` 作為 `decode_options` 的關鍵字參數傳遞
   - 符合 MLX-Whisper 0.x 版本 API 規範

**測試驗證**：
- ✅ 測試 1: `test_meeting_1.wav` (156KB) - **通過**
- ✅ 測試 2: `test_meeting_2.wav` (156KB) - **通過**
- ✅ 直接 MLX-Whisper 呼叫測試 - **通過**
- ✅ 模型從本地快取載入，無需網路下載

**本地模型檢測結果**：
```bash
~/.cache/huggingface/hub/
├── models--mlx-community--whisper-medium (✅ 使用中)
└── models--mlx-community--whisper-large-v3-turbo (可用)
```

#### 2. MLX-Whisper 404 錯誤修復 (v3.5.1)

**問題描述**：
- macOS 版本啟動時出現 404 Client Error
- 錯誤訊息：`Repository Not Found for url: https://huggingface.co/api/models/medium/revision/main`
- 導致轉錄功能完全無法使用

**根本原因**：
- `config.mac.yaml` 的 Whisper 配置結構不正確
- 程式碼讀取 `whisper.mlx.model`，但配置只有 `whisper.model`
- 導致回退到預設值 `"medium"`（錯誤的模型路徑格式）

**修復內容**：
1. **config.mac.yaml**
   - 重構 Whisper 配置結構，新增 `whisper.mlx` 嵌套區塊
   - 正確設定模型路徑：`mlx-community/whisper-large-v3-turbo`

2. **backend/services/transcription.py**
   - 新增3層配置回退機制：`whisper.mlx.model` → `whisper.model` → 預設值
   - 增加警告日誌，當配置不完整時提示開發者

#### 2. 排隊邏輯顯示異常修復

**問題描述**：
- 顯示「目前排隊人數：0 人」但「您的排隊位置：1」
- 邏輯矛盾：排隊位置為1且不需等待，應該立即開始處理

**根本原因**：
- `backend/services/queue_manager.py` 的 `get_next_task()` 方法
- ✅ 有清除 `queue_position = None`
- ❌ 但未清除 `estimated_wait_seconds`（應設為 0）

**修復內容**：
1. **backend/services/queue_manager.py**
   - 在 `get_next_task()` 中新增 `task.estimated_wait_seconds = 0`
   - 確保任務從佇列取出時，排隊位置和等待時間都被清除

2. **backend/services/task_processor.py**
   - 更新註解，確保與實際狀態一致

#### 3. System Prompt 與健康檢查熱修

- 統一 `DEFAULT_SYSTEM_PROMPT`（config 與 summarizer 共用），補齊 COSTAR-X 標籤、100 字以內限制與完整性約束，消除不一致
- 健康檢查支援同步/非同步檢查結果，避免 mock 物件 await 錯誤並保留自訂 GPU 名稱
- 端到端整合測試補上 `@pytest.mark.asyncio`，確保整組測試可執行

### ✅ 驗證結果

**測試通過率**：100% (245/245 pytest)

#### 端到端測試
- ✅ MLX-Whisper 模型正確載入（404 錯誤已修復）
- ✅ MLX-Whisper 使用 MPS 加速
- ✅ 配置回退機制運作正常

#### 排隊邏輯測試
- ✅ 第一個任務從佇列取出時，`queue_position` 設為 `None`
- ✅ 第一個任務從佇列取出時，`estimated_wait_seconds` 設為 `0`
- ✅ 第二個任務自動晉升到第1位
- ✅ 佇列狀態計算正確（排隊中 vs 處理中）
- ✅ 任務狀態轉換正確（QUEUED → PENDING → COMPLETED）

**測試檔案**：
- `tests/test_end_to_end.py` - 端到端整合測試
- `tests/test_queue_fix.py` - 4個單元測試
- `tests/test_queue_integration.py` - 1個整合測試

**詳細報告**：
- `doc/evidence/mlx_whisper_e2e_test_evidence_v3.5.1.md` - 完整測試證據
- `doc/evidence/queue_logic_fix_evidence_v3.5.1.md` - 排隊邏輯修復證據
- `doc/reports/queue_logic_fix_report_v3.5.1.md` - 詳細修復報告

### 📁 文件組織重構

**重大改進**：重新組織 `doc/` 目錄，建立清晰的分類結構

#### 新增目錄結構
```
doc/
├── evidence/        # 驗證證據 - 測試驗證報告和證據
├── reports/         # 技術報告 - 技術分析和修復報告
├── guides/          # 部署指南 - 部署、操作、使用指南
├── analysis/        # 分析文件 - 系統分析、架構分析
└── README.md        # 文件導航說明
```

#### 檔案命名規範
- **驗證證據**：`{功能}_{類型}_evidence_v{版本}.md`
- **技術報告**：`{功能}_{類型}_report_v{版本}.md`
- **部署指南**：`{平台}_{類型}_guide.md`
- **分析文件**：`{主題}_analysis.md`

#### 文件重新組織
- 重新命名所有文件，使用有意義的英文名稱
- 依類型分類到對應目錄
- 新增 `doc/README.md` 提供文件導航
- 更新 `.github/INSTRUCTIONS.md` 定義文件組織規範

**總計**：
- 重新組織 30+ 個文件
- 建立4個分類目錄
- 統一命名規範

---

## [v3.5.0] - 2025-12-06

### 核心修復 🔧

#### 1. macOS Native 部署支援
- ✅ 移除 Docker 依賴（macOS 上 Docker 不支援 MPS）
- ✅ 改用原生服務模式部署
- ✅ 支援 LM Studio 本地 LLM
- ✅ 支援 MLX-Whisper（MPS 加速）

#### 2. 配置管理優化
- ✅ DATA_DIR 路徑修復：支援環境變數覆蓋
- ✅ 從 `/app/data` → `/Users/hsiaojohnny/dev/convert/data`
- ✅ 支援 native mode 和 Docker mode 自動適配

#### 3. 版本號同步
- ✅ API 版本號：2.2.0 → **3.5.0**
- ✅ 前端版本號：v2.1.0 → **v3.5.0**
- ✅ 後端版本號：2.3.6 → **3.5.0**

#### 4. Ollama 移除
- ✅ 刪除 Ollama 模型（gemma3:27b-it-qat）
- ✅ 終止 Ollama 進程
- ✅ 完全遷移至 LM Studio

#### 5. Python 依賴修復
- ✅ 安裝 python-multipart（Form 資料支援）
- ✅ 修復 transcription.py 重複 finally 區塊
- ✅ 確保所有依賴項可用

### 驗證結果 ✅

```
API 狀態: healthy
版本號: 3.5.0 ✅
GPU: Apple MPS (Metal Performance Shaders) ✅
Ollama: false ✅
LM Studio: 就緒
Gemini: 可用
MPS 加速: true ✅
```

### 部署方式

#### macOS (原生服務)
```bash
export DATA_DIR=/Users/hsiaojohnny/dev/convert/data
/opt/anaconda3/bin/uvicorn backend.main:app --host 0.0.0.0 --port 9527
```

#### 配置檔案
- `config.mac.yaml` - macOS 專用配置
- LLM: LM Studio (gemma-3-27b-it-qat)
- Whisper: MLX-Whisper (MPS 加速)
- GPU: Apple Metal Performance Shaders

### 技術細節

#### GPU 支援
- Apple MPS: ✅ 完全支援
- 自動偵測: ✅ 啟動時自動偵測
- 降級機制: ✅ MPS 不可用時自動切換至 CPU

#### 檔案管理
- 上傳目錄: `data/uploads`
- 輸出目錄: `data/outputs`
- 快取目錄: `data/cache`
- 自動清理: ✅ 每日凌晨 3:00 執行

#### 任務處理
- 最大同時任務: 1
- 佇列大小: 20
- 任務超時: 3600 秒
- 預估時間: 4 分鐘/任務

### 已知限制 ⚠️

1. LM Studio 需手動啟動（不包含在本專案中）
2. 模型需預先載入至 LM Studio
3. 本地模式需要 16GB+ 記憶體

### 後續改進

- [ ] 自動檢測並啟動 LM Studio
- [ ] 支援多模型切換
- [ ] 優化 MPS 記憶體管理
- [ ] 增加 Windows 原生部署支援

---

## [v3.4.6] - 2025-12-05

### 改善
- 優化 system prompt 為 Gemma3 模型
- 更新文件

### 修復
- 修正 Gemini API 金鑰驗證

---

## [v2.3.6] - 2025-12-01

### 新增
- FastAPI 整合
- WebSocket 支援
- 任務排隊系統
- 批次上傳支援

### 改善
- 優化 Whisper 轉錄效能
- 改進 Ollama 整合

---

## [v2.1.0] - 2025-11-20

### 新增
- 完整參數化設計
- 支援環境變數配置
- 多模型支援（Ollama, Gemini）

---

## [v1.0.0] - 2025-11-01

### 初始版本
- 基本 Whisper 轉錄
- Ollama LLM 整合
- CLI 介面

## [v3.5.0-完整版] - 2025-12-06 12:30

### 🎉 macOS Native 部署完整版

#### 核心修復 🔧
- ✅ LM Studio URL 修復：從 `host.docker.internal:1234` → `localhost:1234`
- ✅ Ollama URL 修復：從 `host.docker.internal:11434` → `localhost:11434`
- ✅ 移除所有 Docker 路徑依賴
- ✅ DATA_DIR 環境變數支援

#### 新增配置 📝
- ✅ **config.mac.yaml** - macOS 專屬完整配置檔
  - LLM 設定（本地 + 雲端）
  - Whisper 設定（MLX 優化）
  - GPU 設定（MPS 加速）
  - 檔案管理
  - 服務設定
  - 任務處理
  - 效能調校

#### 新增文件 📚
- ✅ **doc/MACOS_DEPLOYMENT.md** - 完整 macOS 部署指南
  - 系統需求（硬體 + 軟體）
  - 快速開始（6個步驟）
  - 配置說明
  - 常見問題（Q&A）
  - 效能優化
  - 故障排除
  - 與 Windows 版本差異

#### 測試驗證 ✅
```
API 版本號：3.5.0 ✅
GPU：Apple MPS (Metal Performance Shaders) ✅
MPS 加速：可用 ✅
服務狀態：healthy ✅
前端版本號：v3.5.0 ✅
LM Studio URL：localhost:1234 ✅
測試通過率：6/7 (86%) ✅
```

#### 平台隔離保證 🔒
- ✅ macOS 配置：`config.mac.yaml`
- ✅ Windows 配置：`config.yaml`
- ✅ 兩版本完全獨立，互不影響
- ✅ 共享底層邏輯，配置分離

#### 已知問題 ⚠️
- Ollama 進程檢測仍顯示可用（但不影響功能）
- LM Studio 需手動啟動
- 本地模式需 16GB+ 記憶體
