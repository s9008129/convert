# MeetingScribe - 變更紀錄

## [v3.5.1] - 2025-12-06

### 🐛 排隊邏輯修復

#### 問題描述
用戶回報排隊邏輯顯示異常：
- 顯示「目前排隊人數：0 人」
- 顯示「您的排隊位置：1」
- 顯示「預計等待：0 分鐘」
- 邏輯矛盾：如果是第1位且不需等待，應該立即開始處理，不應顯示排隊位置

#### 根本原因
`backend/services/queue_manager.py` 的 `get_next_task()` 方法中：
- ✅ 有清除 `queue_position = None`
- ❌ 但未清除 `estimated_wait_seconds`（應設為 0）

#### 修復內容
1. **backend/services/queue_manager.py**
   - 在 `get_next_task()` 中新增 `task.estimated_wait_seconds = 0`
   - 確保任務從佇列取出時，排隊位置和等待時間都被清除

2. **backend/services/task_processor.py**
   - 更新註解，確保與實際狀態一致

#### 驗證結果
✅ **單元測試**：`tests/test_queue_fix.py` - 4個測試全部通過
- 第一個任務立即處理（queue_position = None, estimated_wait = 0）
- 第二個任務正確等待並自動晉升
- 任務狀態轉換正確（QUEUED → PENDING → COMPLETED）
- 佇列狀態統計準確

✅ **整合測試**：`tests/test_queue_integration.py` - 1個測試通過
- 模擬2個音訊檔案上傳完整流程
- 驗證排隊位置、等待時間、狀態轉換全部正確

#### 核心驗證點
1. ✅ 第一個任務從佇列取出時，`queue_position` 立即設為 `None`
2. ✅ 第一個任務從佇列取出時，`estimated_wait_seconds` 設為 `0`
3. ✅ 第二個任務在第一個開始處理後，自動晉升到第1位
4. ✅ 佇列狀態計算正確（排隊中 vs 處理中）
5. ✅ 任務狀態轉換正確（QUEUED → PENDING → COMPLETED）

#### 測試通過率
- **5/5 測試通過** (100%)
- 詳細報告：`doc/QUEUE_LOGIC_FIX_REPORT.md`

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

