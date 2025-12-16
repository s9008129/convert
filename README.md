# MeetingScribe — 會議轉錄系統

簡短定義
- 目標：將會議錄音自動轉為結構化會議記錄（逐字稿、決議、行動項目），支援本地與雲端部署，兼顧隱私與效能。
- 輸入：音訊檔（MP3/MP4/WAV/M4A/MKV/WebM/FLAC/OGG/...）
- 輸出：逐字稿（文本）、結構化會議摘要（決議、待辦）、可下載結果檔案與 API/WebSocket 實時進度通知
- 設計原則（第一性原則）
  - 最小可信邊界：本地模式下資料不外傳，僅在必要時使用雲端 LLM。
  - 可替換的處理層：轉錄、LLM 推理與排隊系統彼此解耦，便於在不同硬體/供應商間切換。
  - 漸進式降級：優先使用 GPU，加速不可用時自動回退到 CPU，保持可用性。
  - 可觀察性與安全：健康檢查、超時保護與本地加密儲存。

快速功能總覽
- 本地（Native） / 雲端（Cloud）雙模式：LM Studio（本地 LLM）或 Gemini（雲端 API）
- 轉錄引擎：Whisper / faster-whisper / MLX（依平台選擇）
- 支援 GPU：Apple MPS、NVIDIA CUDA、ROCm；自動降級至 CPU
- REST API + WebSocket：上傳檔案、查進度、取得結果
- 多檔批次上傳、實時進度、結果下載

---

## 技術棧

後端
- 框架：FastAPI + Uvicorn
- 轉錄：OpenAI Whisper / faster-whisper / MLX（本地模型）
- LLM：LM Studio（本地） / Google Gemini（雲端 API）
- 排隊/任務：內建任務隊列（輕量排隊與並發控制）
- 儲存：檔案系統（可擴充至 SQLite/PostgreSQL）

前端
- HTML5 + CSS3 + Vanilla JS（拖放上傳、實時進度顯示）

環境與依賴
- Python 3.8+
- 主要第三方：whisper / faster-whisper / pyav / 相關 ML 推理套件（見 requirements.txt）
- OS：macOS 12+（建議 Apple Silicon）、Windows 10+/Ubuntu 20.04+
- GPU：支援 Apple MPS、CUDA、ROCm（視平台）

安全與隱私
- 本地部署時：資料不外傳、支援本地模型與本地 LLM
- 支援環境變數與 .env 配置以隱藏 API 金鑰（例如 GEMINI_API_KEY）
- 可設定資料過期自動清理與敏感資料加密儲存

---

## 系統需求（建議）
- RAM: 16GB+
- Storage: 20GB（模型與資料）
- macOS: 12.0+（Apple Silicon 建議）
- Windows: 10/11
- Linux: Ubuntu 20.04+
- 若使用本地大型模型，請評估額外 GPU/記憶體需求

---

## 安裝與部署（精簡步驟）

1) 取得原始碼
```bash
git clone https://github.com/s9008129/convert.git
cd convert
```

2) 建議建立虛擬環境
- macOS / Linux
```bash
python3 -m venv venv
source venv/bin/activate
```
- Windows
```bash
python -m venv venv
venv\Scripts\activate
```

3) 安裝 Python 依賴
```bash
pip install -r requirements.txt --prefer-binary
```
若遇到編譯問題，先嘗試 --prefer-binary，或更新 pip 與 wheel，再重試。

4) 配置環境變數（範例）
- 直接在 shell 設定：
```bash
export DATA_DIR=/path/to/convert/data
export LOG_LEVEL=INFO
export LMSTUDIO_BASE_URL=http://localhost:1234/v1   # 若使用 LM Studio（本地）
export GEMINI_API_KEY=your_gemini_api_key           # 若使用雲端 Gemini
```
- 或建立 .env：
```bash
cp .env.example .env
# 編輯 .env 填入實際值
```

5) 若使用本地 LLM（LM Studio）
- 下載並啟動 LM Studio（或其他本地 LLM 提供者），確認 API 可用（預設 http://localhost:1234/v1）
- 載入並啟用所需模型（例如 gemma-3-27b…），確認模型能被呼叫

6) 啟動服務（開發）
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 9527 --reload
```
或使用專案提供的啟動腳本（若存在）
```bash
./start_service.sh
```

7) 瀏覽器開啟
- 預設介面: http://localhost:9527

---

## 常用 API 範例

健康檢查
```bash
curl http://localhost:9527/api/health
```

上傳檔案（local 模式範例）
```bash
curl -F "file=@meeting.mp3" \
     -F "mode=local" \
     http://localhost:9527/api/upload
```

WebSocket 實時進度
```javascript
const ws = new WebSocket('ws://localhost:9527/api/ws');
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log(data.progress, data.status);
};
```

回傳範例（health）
```json
{
  "status": "healthy",
  "version": "3.5.x",
  "gpu_available": true,
  "gpu_name": "Apple MPS",
  "lmstudio_available": true,
  "gemini_available": false
}
```

---

## 核心配置概念（快速說明）
- DATA_DIR：儲存上傳檔案與輸出結果的位置
- LMSTUDIO_BASE_URL / GEMINI_API_KEY：LLM 提供者設定
- WHISPER_MODEL：轉錄模型大小（tiny/base/medium/large）— 大模型更準確但佔用更多資源
- MAX_FILE_SIZE_MB：單檔上限，預設 200

配置檔範例（簡化）
- macOS / native (config.mac.yaml)
```yaml
platform: macos
deployment_mode: native
llm:
  provider: lmstudio
  base_url: http://localhost:1234/v1
whisper:
  backend: mlx
  device: mps
```

---

## 部署考量（運維要點）
- 可觀察性：啟用健康檢查與請求超時（服務端應配置 TimeoutMiddleware）
- 資源管理：大模型與 GPU 使用時要限制同時執行的推理數量，使用排隊/速率限制避免資源耗盡
- 隱私：若要求 100% 本地處理，禁用任何雲端 LLM 金鑰並確保 LM Studio 本地可用
- 備份與清理：設定 DATA_DIR 的過期檔案自動清理與必要的備份策略

---

## 故障排除（常見問題）
- 服務無法啟動：檢查 9527 埠是否被佔用（lsof -i:9527），確認依賴已安裝
- LM Studio 連接失敗：確認 LM Studio 正在運行並可從 ML API 列表讀到模型（curl http://localhost:1234/v1/models）
- 轉錄品質差：檢查輸入音訊品質（建議 16kHz、mono），或選擇更大的 Whisper 模型
- 記憶體不足：降低 Whisper/LLM 模型等級或增加記憶體/GPU

---

## 檔案與文件
- requirements.txt — 依賴清單
- backend/ — 主要後端程式碼（FastAPI 應用）
- config*.yaml — 平台/部署設定範例
- docs/ 或 doc/ — 部署、API、架構指南（詳細操作請參閱 docs 目錄中的具體指南）

---

許可與聯絡
- 授權：MIT（見 LICENSE）
- Issues / 支援：https://github.com/s9008129/convert/issues
- 聯絡信箱：support@example.com

---
