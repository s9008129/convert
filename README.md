# 政府智慧會議紀錄生成系統

[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![Version](https://img.shields.io/badge/version-4.3.3-green)](CHANGELOG.md)
[![Platform](https://img.shields.io/badge/platform-macOS%20|%20Windows%20|%20Linux-informational)](doc/guides/)
[![Stability](https://img.shields.io/badge/stability-stable-brightgreen)](CHANGELOG.md)

> 將會議錄音自動轉換為結構化會議記錄的智能系統，支援 Markdown 與 Word (DOCX) 雙格式下載

> 📌 **本檔案用途**：介紹本專案的**用途、架構、設計理念與簡易操作**。
> 詳細的逐版變更紀錄請見 [CHANGELOG.md](CHANGELOG.md)；正式環境的更新部署步驟請見 [部署更新手冊](doc/操作手冊/部署更新手冊_v4.1.md)。

## 🆕 最新版本：v4.1（2026-06-04）

**會議紀錄品質根治與提示詞硬化。** 解決了實測中會議紀錄混入英文、口語贅字、校正過程與杜撰內容的問題。經根因分析確認問題不在模型能力，而在 System Prompt 架構與輸出後處理，因此：

- 以「政府機關承辦人員」視角、採多代理對抗方式**全面重寫 System Prompt**，加入「只輸出本文」「未明示一律標註（待確認）、禁臆測」「去贅字／去自我更正」「台灣公務用語」等硬規則。
- **修正清理與驗證流程**，並將「驗證＋自動補強重寫」防護擴及 Gemini 雲端路徑。
- **雲端模型升級**為 `gemini-3.1-flash-lite`。

> 完整根因分析、修改檔案與驗證結果 → 詳見 [CHANGELOG.md](CHANGELOG.md#v41---2026-06-04)。
> ⚠️ Docker 部署者：System Prompt 內嵌於容器，需重新套用映像後生效，步驟見 [部署更新手冊](doc/操作手冊/部署更新手冊_v4.1.md)。

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
- **雙格式下載**：Markdown (.md) 與 Word (.docx)
- 實時轉錄進度顯示
- RESTful API + WebSocket 支援

### 🔒 隱私安全
- 本地模式：100% 離線，零資料上傳
- 加密儲存：敏感資訊本地加密
- 自動清理：過期檔案自動刪除

## 🧠 設計理念與系統架構

### 為什麼這樣設計？（專案意圖）

本系統的目標是讓**公務機關**能把會議錄音，自動轉成**符合台灣政府公文格式、有憑有據、不杜撰**的會議紀錄。
因此設計上有兩個核心堅持：

1. **忠於逐字稿**：紀錄只能根據錄音內容生成，查不到的欄位一律標註「（待確認）」，**絕不臆測或杜撰**單位、人名、決議。
2. **可離線、保護隱私**：機敏會議可走「本地模式」全程離線，資料不外傳；對品質要求高的場合可選「雲端模式」。

### 處理流程（從音檔到會議紀錄）

```
音檔  ──①語音辨識(ASR)──▶  逐字稿  ──②萃取式三階段──▶  會議紀錄(.md / .docx)
            Whisper /                    LLM
         Breeze-ASR-26              (本地或雲端)
```

**核心是「萃取優先（extraction-first）」的三階段流程**，刻意把「讀懂內容」與「寫成公文」分開，以降低杜撰風險：

| 階段 | 做什麼 | 目的 |
|---|---|---|
| ① 萃取筆記 | 從逐字稿逐段抽出「事實、決議、待辦」 | 只看得到的，不腦補 |
| ② 合併整理 | 去重、歸納、排序 | 形成結構化素材 |
| ③ 生成＋自我校驗 | 套用公文格式產出，再**自動驗證並補強重寫** | 攔截英文洩漏、贅字、簡體、杜撰 |

> 第 ③ 階段的「驗證＋補強」防護**本地與雲端路徑皆已套用**（v4.1 起），是會議紀錄品質的最後一道關卡。

### 技術組成（簡述）

- **後端**：FastAPI（提供網頁與 RESTful API，預設埠 `9527`）。
- **語音辨識**：`MediaTek-Research/Breeze-ASR-26`（台灣中文優化），可回滾 `faster-whisper`。
- **語言模型**：本地 Ollama / LM Studio，或雲端 Gemini（`gemini-3.1-flash-lite`）。
- **輸出**：Markdown 與 Word（DOCX，相容 Office 2024 / M365）。
- **部署**：Docker（GPU／標準兩種 compose）或原生服務。

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
# macOS / Linux / 無 NVIDIA GPU 的 Windows
pip install -r requirements.txt --prefer-binary
```

**Windows + NVIDIA GPU（官方 ASR-26 / Transformers 必做）**：
```bash
python install_deps.py
python -c "import torch; print(torch.__version__); print(torch.version.cuda); print(torch.cuda.is_available())"
```

`install_deps.py` 會先安裝 `requirements.txt`，再用 `requirements.windows-cuda.txt` 強制覆寫成 PyTorch 官方 CUDA wheel。

若最後一行不是 `True`，代表目前仍是 CPU-only torch；請執行一次：
```bash
python -m pip install --upgrade --force-reinstall -r requirements.windows-cuda.txt --prefer-binary
```

**依賴修復（v3.5.4-stable-patch）**：
- PyAV 已升級到 16.0.1，支援 FFmpeg 7.1+
- faster-whisper 已升級到 1.2.1，兼容新版 PyAV
- 詳見 [CHANGELOG.md](CHANGELOG.md#v354-stable-patch---2025-12-07)

> 🚀 建議先預載官方 ASR-26 模型：
> ```bash
> python scripts/download_models.py
> ```

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
   - 結果下載（Markdown 或 Word 格式）

### API 使用

#### 健康檢查
```bash
curl http://localhost:9527/api/health
```

**回應**：
```json
{
  "status": "healthy",
  "version": "4.0",
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
| `WHISPER_MODEL` | `MediaTek-Research/Breeze-ASR-26` | Whisper / ASR 模型名稱 |

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

#### Q: 有 RTX 4090，但轉錄沒有使用 GPU
- 先執行 `python -c "import torch; print(torch.__version__); print(torch.version.cuda); print(torch.cuda.is_available())"`
- 若結果是 `+cpu`、`None` 或 `False`，代表目前安裝的是 CPU-only torch
- 在 Windows + NVIDIA 環境請改執行：
```bash
python -m pip install --upgrade --force-reinstall -r requirements.windows-cuda.txt --prefer-binary
```
- 重新啟動服務後再檢查 `/api/health` 或重新上傳音檔

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
- **Python**: 3.10+
- **OS**: macOS 12+ (含 iOS 26 相關 macOS)、Windows 10/11、Ubuntu 20.04+
- **GPU**: Apple MPS, CUDA, ROCm, CPU
- **Office 相容性**: Office 2024, M365 (DOCX 輸出)

## 📝 版本歷史

### [v4.1] - 2026-06-04
- ✅ 會議紀錄品質根治：消除非必要英文、口語贅字、語意校正過程與杜撰內容
- ✅ System Prompt 多代理對抗硬化（移除評估標準/方括號模板、加入只輸出本文與不杜撰硬規則）
- ✅ 修正 `_clean_ollama_output` 裁切錨點（支援「會議名稱：」開頭格式）
- ✅ 英文/回吐偵測接入品質驗證，並將補強重寫迴圈擴及 Gemini 雲端路徑
- ✅ 修正待辦召回假陽性、強化後處理英文清理、`config.yaml` 防漂移同步測試

### [v4.0] - 2026-02-28
- ✅ 新增 DOCX (Word) 下載功能，相容 Office 2024 / M365
- ✅ 專業 CJK 排版（微軟正黑體標題、新細明體內文）
- ✅ 完整表格框線與標題灰底
- ✅ API 向後相容（`?format=docx`）
- ✅ 28 項單元測試全數通過

### [v3.5.5] - 2025-12-18
- ✅ 環境統一與日誌系統升級
- ✅ 解決 `No module named 'av'` 問題

### [v3.5.4-stable] - 2025-12-07
- GPU 滿載修復、統一版本號管理、服務管理工具

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

**Made with ❤️ by the 政府智慧會議紀錄生成系統 Team**

Last updated: 2026-06-05
