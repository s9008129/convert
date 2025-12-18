# MeetingScribe - 會議轉錄系統

[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Version](https://img.shields.io/badge/version-3.5.5-green)](CHANGELOG.md)
[![Platform](https://img.shields.io/badge/platform-macOS%20|%20Windows%20|%20Linux-informational)](doc/guides/)
[![Stability](https://img.shields.io/badge/stability-stable-brightgreen)](doc/v3.5.5_系統修復驗證報告.md)

> 將會議錄音自動轉換為結構化會議記錄的智能系統

## 🆕 v3.5.5 系統修復版本（2025-12-18）

### 🔧 環境統一與日誌系統升級

**修復內容**：
- ✅ 解決 `No module named 'av'` 持續性錯誤
- ✅ 統一所有啟動腳本使用 conda meetingscribe 環境
- ✅ 新增環境驗證腳本 `scripts/verify_env.py`
- ✅ 升級日誌系統至 v2.0（檔案輪轉 + JSON 結構化）
- ✅ 新增完整管線測試 `scripts/test_full_pipeline.py`

**快速啟動**：
```bash
# 使用環境驗證確保一切正常
/opt/anaconda3/envs/meetingscribe/bin/python scripts/verify_env.py

# 啟動服務
./start_service.sh
```

詳見：[v3.5.5 系統修復驗證報告](doc/v3.5.5_系統修復驗證報告.md)

---

## ✨ 核心特性

### 🎯 雙模式部署
- **本地模式** (Native)：完整離線，資料不外傳，使用 Ollama/LM Studio + Whisper
- **雲端模式** (Cloud)：高品質輸出，使用 Gemini API

### 🚀 性能優化
- **GPU 加速**：支援 Apple MPS、NVIDIA CUDA、ROCm
- **智能降級**：GPU 不可用時自動切換至 CPU
- **並行處理**：任務排隊系統，支援批次上傳

### 📋 功能完整
- 支援多種音訊格式（MP3、MP4、WAV、M4A、MKV、WebM 等）
- 自動生成會議記錄（決議事項、行動項目等）
- 實時轉錄進度顯示
- RESTful API + WebSocket 支援

### 🔒 隱私安全
- 本地模式：100% 離線，零資料上傳
- 加密儲存：敏感資訊本地加密
- 自動清理：過期檔案自動刪除

## 🆕 v3.5.4-stable 穩定版本（2025-12-07）

### 🛡️ 版本控制強化

#### 1. GPU 滿載時新 Session 無法開啟網頁問題完全修復 ✅

**問題描述**: 當 GPU 使用率達到 100% 時，新用戶開啟網頁會一直轉圈圈，無法訪問服務。

**根本原因**: 後端沒有實作請求級別的超時限制，導致等待 GPU 資源時阻塞整個 HTTP 請求。

**修復方案**:
1. ✅ 新增 **TimeoutMiddleware**（30 秒超時保護）
   - 所有 HTTP 請求加入超時限制
   - 超時後返回 503 Service Unavailable
   - 防止長時間阻塞影響其他用戶

2. ✅ **Health Check 支援快速模式**
   - `?quick=true`: 使用快取資訊，不重新偵測裝置
   - `?quick=false`: 完整健康檢查（預設）
   - 避免 GPU 滿載時阻塞

3. ✅ **前端使用快速健康檢查**
   - 定期健康檢查使用快速模式
   - 避免阻塞用戶體驗

**修復後狀態**:
```
✅ GPU 滿載時新用戶可正常開啟網頁
✅ 超時後顯示友善錯誤訊息（而非轉圈圈）
✅ 系統保持響應性
```

#### 2. 統一版本號管理 📦

**問題描述**: 版本號硬編碼在多處，服務顯示不一致。

**修復方案**:
1. ✅ 創建 **VERSION 檔案**（Single Source of Truth）
2. ✅ 創建 `backend/core/version.py` 版本號管理模組
3. ✅ 所有版本號引用統一（main.py, routes.py）
4. ✅ 服務重啟後自動同步版本號

#### 3. 服務管理工具 🛠️

**新增功能**:
1. ✅ `scripts/service_manager.sh` - 互動式服務管理工具
   - 查看服務狀態
   - 啟動/停止/重啟服務
   - 查看日誌
   - 顯示重啟指南

2. ✅ 明確重啟時機文件
   - Python 程式碼（.py）→ 自動重載
   - 環境變數/配置檔 → 需要重啟
   - 靜態檔案/版本號 → 需要重啟

### 🎯 Windows 兼容性保證

**深度分析結果**: ✅ **完全不影響 Windows 版本**

**證據**:
1. ✅ 所有變更在應用層（HTTP、API、版本管理）
2. ✅ 零觸及基礎設施層（裝置偵測、GPU 運算）
3. ✅ Windows GPU 關鍵檔案完全未修改:
   - `backend/core/platform_config.py` ❌ 未修改
   - `backend/services/device_detector.py` ❌ 未修改
   - `backend/services/transcription.py` ❌ 未修改
   - `config.yaml` ❌ 未修改
   - `docker/docker-compose-windows-gpu.yml` ❌ 未修改

詳細分析請參閱: [v3.5.4 穩定版本深度分析報告](doc/v3.5.4_穩定版本深度分析報告.md)

### 🧪 測試驗證

```bash
✅ 253/254 測試通過（99.6% 通過率）
✅ 所有核心功能驗證通過
✅ GPU/MPS/CPU 裝置偵測正常
✅ WebSocket 錯誤處理完善
✅ 排隊系統穩定運作
```

---

## 📚 歷史更新

<details>
<summary>點擊展開歷史版本</summary>

### v3.5.4-stable（2025-12-07）
- GPU 滿載時新 Session 無法開啟網頁問題修復
- 統一版本號管理
- 服務管理工具

### v3.5.3（2025-12-06）
- 服務連線異常問題解決
- Docker 清理腳本

### v3.5.2（2025-12-06）
- MLX-Whisper 模型載入問題修復

</details>

詳細更新紀錄請參閱：[CHANGELOG.md](CHANGELOG.md)

## 🚀 快速開始

### 系統需求

#### macOS (推薦)
- **OS**: macOS 12.0+ (Apple Silicon 優先)
- **RAM**: 16GB+ (本地模式需要)
- **Storage**: 20GB (模型 + 資料)
- **GPU**: Apple MPS (自動)

#### Windows
- **OS**: Windows 10/11
- **RAM**: 16GB+
- **Storage**: 20GB
- **GPU**: CUDA (NVIDIA) 或 DirectML

#### Linux
- **OS**: Ubuntu 20.04+
- **RAM**: 16GB+
- **Storage**: 20GB
- **GPU**: CUDA 或 ROCm

### 安裝步驟

#### 1. 克隆專案
```bash
git clone https://github.com/s9008129/convert.git
cd convert
```

#### 2. 建立虛擬環境（推薦）
```bash
# macOS / Linux
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate
```

#### 3. 安裝依賴

```bash
pip install -r requirements.txt --prefer-binary
```

**依賴修復（v3.5.4-stable-patch）**：
- PyAV 已升級到 16.0.1，支援 FFmpeg 7.1+
- faster-whisper 已升級到 1.2.1，兼容新版 PyAV
- 詳見 [CHANGELOG.md](CHANGELOG.md#v354-stable-patch---2025-12-07)

如遇到編譯問題，可使用以下方式：
```bash
# 方式 1：使用預編譯 wheels（推薦）
pip install -r requirements.txt --prefer-binary

# 方式 2：如果還有問題，用此命令更新虛擬環境
pip install --upgrade -r requirements.txt
```

#### 4. 配置環境變數
```bash
# macOS
export DATA_DIR=/Users/hsiaojohnny/dev/convert/data
export PYTHONPATH=/Users/hsiaojohnny/dev/convert:$PYTHONPATH

# 或編輯 .env 檔案
cp .env.example .env
```

#### 5. 下載 LM Studio（本地模式）
- 官網：https://lmstudio.ai
- 載入模型：`gemma-3-27b-it-qat` 或其他模型
- 啟動本地 API：http://localhost:1234

#### 6. 啟動服務
```bash
# 使用 uvicorn
uvicorn backend.main:app --host 0.0.0.0 --port 9527 --reload

# 或使用提供的腳本
./start_service.sh
```

#### 7. 開啟瀏覽器
```
http://localhost:9527
```

## 📖 使用說明

### Web 介面

1. **選擇模式**
   - 本地模式：完全離線，無需網路
   - 雲端模式：需要 Gemini API 金鑰

2. **上傳音檔**
   - 支援格式：MP3, MP4, WAV, M4A, MKV, WebM, FLAC, OGG, AVI, MOV
   - 最大檔案：200MB
   - 批次上傳：可同時上傳多個檔案

3. **自動處理**
   - 實時進度顯示
   - 逐字稿轉錄
   - 會議記錄生成
   - 結果下載

### API 使用

#### 健康檢查
```bash
curl http://localhost:9527/api/health
```

**回應**：
```json
{
  "status": "healthy",
  "version": "3.5.0",
  "gpu_available": true,
  "gpu_name": "Apple MPS (Metal Performance Shaders)",
  "ollama_available": false,
  "lmstudio_available": false,
  "gemini_available": true
}
```

#### 上傳檔案
```bash
curl -F "file=@meeting.mp3" \
     -F "mode=local" \
     http://localhost:9527/api/upload
```

#### WebSocket 連接
```javascript
const ws = new WebSocket('ws://localhost:9527/api/ws');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.progress, data.status);
};
```

## ⚙️ 配置說明

### 環境變數

| 變數名 | 預設值 | 說明 |
|-------|--------|------|
| `DATA_DIR` | `/Users/hsiaojohnny/dev/convert/data` | 資料儲存目錄 |
| `LOG_LEVEL` | `INFO` | 日誌等級 (DEBUG/INFO/WARNING/ERROR) |
| `MAX_FILE_SIZE_MB` | `200` | 單檔最大大小（MB） |
| `LMSTUDIO_BASE_URL` | `http://localhost:1234/v1` | LM Studio 端點 |
| `GEMINI_API_KEY` | - | Gemini API 金鑰 |
| `WHISPER_MODEL` | `medium` | Whisper 模型 (tiny/base/small/medium/large) |

### 配置檔案

#### macOS (`config.mac.yaml`)
```yaml
platform: macos
deployment_mode: native
llm:
  provider: lmstudio
  base_url: http://localhost:1234/v1
  model: gemma-3-27b-it-qat
whisper:
  backend: mlx
  device: mps
```

#### Windows (`config.yaml`)
```yaml
platform: windows
deployment_mode: native
llm:
  provider: lmstudio
  base_url: http://localhost:1234/v1
whisper:
  backend: faster-whisper
  device: cuda
```

## 📊 性能指標

### 轉錄速度
- **Apple MPS**: 1 分鐘音頻 ≈ 6-10 秒
- **CUDA**: 1 分鐘音頻 ≈ 3-5 秒
- **CPU**: 1 分鐘音頻 ≈ 30-60 秒

### 記憶體用量
- **本地模式 (LM Studio + MLX)**:
  - 閒置: 2-3GB
  - 處理中: 14-16GB

- **雲端模式 (Gemini API)**:
  - 約 1-2GB

### GPU 使用率
- **Apple MPS**: 文字處理時最高 80%
- **CUDA**: 記憶體最高 12GB (RTX 4090)

## 🔧 故障排除

### 常見問題

#### Q: 服務無法啟動
```bash
# 檢查連接埠
lsof -i:9527

# 檢查依賴
pip install -r requirements.txt

# 檢查 DATA_DIR
export DATA_DIR=/path/to/data
mkdir -p $DATA_DIR/uploads $DATA_DIR/outputs
```

#### Q: LM Studio 連接失敗
```bash
# 確認 LM Studio 正在運行
curl http://localhost:1234/v1/models

# 檢查防火牆設定
# 確保 1234 連接埠可用
```

#### Q: 轉錄結果不佳
- 檢查音訊品質（建議 16kHz, mono）
- 調整 Whisper 模型大小（更大 = 更準確但更慢）
- 檢查 system prompt 設定

#### Q: 記憶體不足
- 降低 Whisper 模型等級（large → medium）
- 關閉其他應用程式
- 檢查 LM Studio 模型是否過大

### 日誌檔案
```bash
# 檢查服務日誌
tail -f /tmp/service.log

# 檢查應用日誌
cat data/logs/app.log
```

## 📚 文件

- [部署指南](docs/DEPLOYMENT.md) - 詳細部署說明
- [API 文件](docs/API.md) - 完整 API 參考
- [系統架構](docs/ARCHITECTURE.md) - 系統設計文件
- [貢獻指南](CONTRIBUTING.md) - 開發指南

## 🏗️ 技術棧

### 後端
- **框架**: FastAPI + Uvicorn
- **轉錄**: Whisper (OpenAI) + MLX (Apple)
- **LLM**: LM Studio (本地) + Gemini API (雲端)
- **資料庫**: 檔案系統 (可擴展至 SQLite/PostgreSQL)

### 前端
- **框架**: HTML5 + CSS3 + Vanilla JavaScript
- **功能**: 拖放上傳、實時進度、結果預覽

### 環境支援
- **Python**: 3.8+
- **OS**: macOS 12+, Windows 10+, Ubuntu 20.04+
- **GPU**: Apple MPS, CUDA, ROCm, CPU

## 📝 版本歷史

### [v3.5.0] - 2025-12-06
- ✅ macOS Native 部署支援
- ✅ GPU 路徑修復（DATA_DIR）
- ✅ Ollama 完全移除
- ✅ 版本號同步至 3.5.0

### [v3.4.6] - 2025-12-05
- 優化 system prompt

### [v2.3.6] - 2025-12-01
- FastAPI 整合

[查看完整歷史](CHANGELOG.md)

## 📄 授權

本專案採用 MIT 授權條款。詳見 [LICENSE](LICENSE) 檔案。

## 🤝 貢獻

歡迎貢獻！請參閱 [CONTRIBUTING.md](CONTRIBUTING.md)

## 📧 聯絡方式

- Issues: https://github.com/s9008129/convert/issues
- Email: support@example.com

## 🙏 致謝

感謝以下開源專案：
- [OpenAI Whisper](https://github.com/openai/whisper)
- [FastAPI](https://github.com/tiangolo/fastapi)
- [LM Studio](https://lmstudio.ai)
- [Google Gemini](https://ai.google.dev)

---

**Made with ❤️ by the MeetingScribe Team**

Last updated: 2025-12-06
