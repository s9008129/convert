# 🚨 MeetingScribe 開發最高指導原則

> **版本**: v3.5.5  
> **建立日期**: 2025-12-05  
> **最後更新**: 2025-12-18  
> **目的**: 避免重複犯同樣的錯誤，確保每次修改都能正確運作

---

## 🎯 第零部分：文件驅動開發（SDD）核心精神 - 最高優先級

### 0.1 文件驅動開發原則

> **🔴 最高原則：文件是一切的核心，必須保持同步、最新、友善、非技術人員可以理解**

本專案採用 **Specification-Driven Development (SDD) / Documentation-Driven Development (DDD)** 核心精神：

```
文件 → 設計 → 實作 → 測試 → 文件更新
  ↑                             ↓
  └─────────── 持續同步 ─────────┘
```

**核心理念：**
1. **文件先行**：任何功能開發前，先撰寫文件說明預期行為
2. **文件即規格**：文件是產品規格的唯一真實來源（Single Source of Truth）
3. **文件可執行**：文件中的範例必須可運行，測試必須可驗證
4. **文件友善**：非技術人員必須能理解並使用系統

### 0.2 文件分類與優先順序

**第一層：使用者文件（最高優先級）**
- `README.md` - 專案首頁，5 分鐘快速上手
- `doc/guides/quick_start_guide.md` - 快速開始指南
- `doc/guides/{platform}_deployment_guide.md` - 平台部署指南

**第二層：維護者文件**
- `CHANGELOG.md` - 版本變更記錄（每次發布必更新）
- `.github/INSTRUCTIONS.md` - 開發最高指導原則（本文件）
- `doc/系統改善計劃.md` - 系統改善與重構計畫

**第三層：技術文件**
- `doc/analysis/system_development_analysis.md` - 系統開發分析
- `doc/architecture/` - 架構設計文件
- `doc/reports/` - 技術報告

**第四層：驗證文件**
- `doc/evidence/` - 測試驗證證據
- `doc/v{version}_系統修復驗證報告.md` - 版本驗證報告

### 0.3 文件同步強制規則

**每次程式碼變更後，MUST 完成以下文件同步：**

| 變更類型 | 必須更新的文件 | 檢查方式 |
|---------|---------------|---------|
| 新增功能 | README.md + 對應 guide + CHANGELOG.md | `git diff` |
| 修復 Bug | CHANGELOG.md + 驗證報告 | 測試通過 |
| 重構程式碼 | architecture/ + analysis/ | Code review |
| 配置變更 | README.md + deployment_guide.md | 部署測試 |
| 版本發布 | VERSION + CHANGELOG.md + README.md + 所有 doc/ | 版本檢查 |

**文件檢查清單（每次 commit 前必做）：**

- [ ] **版本號一致性**：`grep -r "v3.5.4" . | grep -v node_modules | grep -v .git`
- [ ] **連結有效性**：所有文件內的連結可點擊
- [ ] **範例可執行**：文件中的命令範例已測試
- [ ] **截圖最新**：若包含截圖，確保與當前版本一致
- [ ] **中文正確**：使用繁體中文（台灣正體）
- [ ] **非技術友善**：非工程師能理解核心概念

### 0.4 文件撰寫規範

**語言規範：**
- ✅ 繁體中文（台灣正體）為主要語言
- ✅ 技術術語可保留英文，但需加中文註解
- ✅ 範例程式碼使用英文，註解使用中文
- ❌ 禁止簡體中文
- ❌ 禁止中英混雜（如「這個 function 很 powerful」）

**結構規範：**
```markdown
# 標題（說明是什麼）

> 簡短摘要（一句話說明目的）

## 目標讀者
- 誰應該閱讀這份文件

## 前置需求
- 閱讀前需要知道什麼

## 核心內容
- 詳細說明（使用範例、圖表、步驟）

## 疑難排解
- 常見問題與解決方案

## 相關文件
- 連結到相關文件
```

**範例撰寫規範：**
```markdown
### 範例：上傳音訊檔案

**情境**：使用者想上傳一個會議錄音檔案

**步驟**：
1. 開啟瀏覽器，前往 `http://localhost:9527`
2. 點擊「上傳檔案」按鈕
3. 選擇音訊檔案（支援 MP3、WAV、M4A）
4. 等待處理完成（大約 2-5 分鐘）

**預期結果**：
- 顯示「處理完成」訊息
- 自動下載會議記錄 PDF 檔案

**實際測試**（驗證日期：2025-12-18）：
✅ 已測試，功能正常

**疑難排解**：
- 若出現「檔案過大」錯誤 → 確認檔案小於 200MB
- 若一直轉圈圈 → 檢查網路連線和後端服務狀態
```

### 0.5 文件維護檢查點

**每週檢查（自動化）：**
- 執行 `scripts/check_docs.sh`
- 驗證所有連結有效性
- 檢查版本號一致性

**每月檢查（手動）：**
- 重新測試所有文件中的範例
- 更新過時截圖
- 審查使用者反饋，改進文件

**每次發布檢查（強制）：**
- [ ] 所有文件版本號已更新
- [ ] CHANGELOG.md 記錄完整
- [ ] README.md 反映最新功能
- [ ] 部署指南經過實測
- [ ] 範例程式碼可執行

### 0.6 文件品質標準

**可讀性標準：**
- 段落長度：不超過 5-7 行
- 句子長度：不超過 25 字
- 列表項目：不超過 7 項（遵循 7±2 法則）
- 專有名詞：首次出現必須解釋

**完整性標準：**
- 包含「是什麼」「為什麼」「怎麼做」
- 包含正常流程和異常處理
- 包含範例和反例
- 包含疑難排解

**友善性標準：**
- 非技術人員能理解 80% 內容
- 使用圖表輔助說明
- 提供循序漸進的步驟
- 避免過度技術細節

---

## ⚠️ 第一部分：Docker 與 GPU 加速（最高優先級）

### 1.1 CUDA 與 cuDNN 依賴規則

**🔴 絕對不可遺忘的事實：**

```
CTranslate2（faster-whisper 底層）需要：
├── CUDA 12.x
├── cuDNN 9（用於一般推理）
└── cuDNN 8（用於語音識別模型，如 Whisper）⚠️ 關鍵！
```

**官方文件明確說明：**
> "If you plan to run models with convolutional layers (e.g. for **speech recognition**), 
> you should also install **cuDNN 8** for CUDA 12.x."
> 
> — [CTranslate2 Installation Guide](https://opennmt.net/CTranslate2/installation.html)

### 1.2 Dockerfile.gpu 必要內容

每次修改 GPU Dockerfile 時，**必須確保包含以下內容**：

```dockerfile
# ✅ 正確的基底映像
FROM nvidia/cuda:12.3.2-cudnn9-runtime-ubuntu22.04

# ✅ 必須額外安裝 cuDNN 8（Whisper 語音識別必需）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libcudnn8=8.9.7.29-1+cuda12.2 \
    && rm -rf /var/lib/apt/lists/* \
    && ldconfig

# ✅ 必須安裝 FFmpeg 開發庫（編譯 PyAV/av 套件需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libavfilter-dev \
    libswscale-dev \
    libswresample-dev
```

### 1.3 驗證清單（每次 GPU 相關修改後必做）

- [ ] 確認 Dockerfile.gpu 使用 NVIDIA CUDA 基底映像
- [ ] 確認安裝了 `libcudnn8`（cuDNN 8）
- [ ] 確認安裝了 FFmpeg 開發庫
- [ ] 執行 `docker exec meetingscribe-app ls -la /usr/lib/x86_64-linux-gnu/libcudnn_ops_infer.so.8`
- [ ] 執行 `docker logs meetingscribe-app | grep "裝置: cuda"`
- [ ] 上傳測試音檔並確認日誌顯示 "Whisper 模型載入成功 (裝置: CUDA)"

---

## ⚠️ 第二部分：繁體中文輸出規範（最高優先級）

### 2.1 問題根因

**Gemma 3 等多語言模型的特性：**
- 傾向於使用輸入語言作為輸出語言
- 當逐字稿包含英文時，模型可能切換到英文模式
- 僅在 system prompt 中要求中文輸出**不夠**，需要多重強化

### 2.2 強制繁體中文輸出的三道防線

**防線 1：System Prompt 中的 `<critical_rules>`**
```xml
<critical_rules>
4. **繁體中文輸出（最高優先級）**：
   - 無論逐字稿是什麼語言，輸出必須是繁體中文（台灣正體）
   - 即使逐字稿是英文或包含英文，也必須翻譯成繁體中文輸出
   - 禁止在輸出中使用英文字母（Markdown 語法除外）
</critical_rules>
```

**防線 2：System Prompt 末尾的 `<language_enforcement>`**
```xml
<language_enforcement>
【強制語言規則】
- 你的回應語言：繁體中文（台灣）
- 絕對禁止：使用英文回應
- 若輸入為英文，必須翻譯為繁體中文後輸出
</language_enforcement>
```

**防線 3：User Message 前綴**
```python
user_message = f"""【重要】請使用繁體中文（台灣正體）輸出，不要使用英文。

以下是會議的逐字稿，請整理成會議記錄：

{transcript}"""
```

### 2.3 驗證清單（每次 LLM 相關修改後必做）

- [ ] 確認 `config.py` 的 `DEFAULT_SYSTEM_PROMPT` 包含繁體中文強制規則
- [ ] 確認 `summarization.py` 的 user_message 包含繁體中文前綴
- [ ] 使用包含英文內容的測試音檔驗證輸出語言
- [ ] 輸出必須是繁體中文，不能是英文或簡體中文

---

## ⚠️ 第三部分：Docker 重建最小化

### 3.1 為何每次 rebuild 都要重新下載 Whisper 模型？

**根本原因：**
```dockerfile
# Dockerfile.gpu 中的這一行會在 build 時下載模型
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('medium', device='cpu', compute_type='int8')"
```

**問題：**
- 模型下載在 Docker image layer 中
- 每次 `--no-cache` 會重新下載
- 模型約 1.5GB，浪費時間和帶寬

### 3.2 解決方案：使用 Docker Volume 持久化模型

**在 docker-compose-windows-gpu.yml 中：**
```yaml
volumes:
  # 持久化 Whisper 模型快取
  - meetingscribe-whisper-models:/root/.cache/huggingface

volumes:
  meetingscribe-whisper-models:
```

**優點：**
- 模型只下載一次
- Rebuild 時自動使用快取
- 大幅縮短重建時間

### 3.3 快速判斷表

| 修改類型 | 需要 Rebuild? | 需要重新下載模型? |
|----------|---------------|-------------------|
| Python 程式碼 | ❌ restart | ❌ |
| 前端 HTML/CSS/JS | ❌ restart | ❌ |
| config.yaml | ❌ restart | ❌ |
| requirements.txt | ✅ build | ❌（有 volume） |
| Dockerfile | ✅ build | ❌（有 volume） |
| Dockerfile + --no-cache | ✅ build | ❌（有 volume） |
| 刪除 volume | N/A | ✅ 需要重新下載 |

---

## 📋 第四部分：每次發布前的檢查清單

### 4.1 GPU 功能檢查
```bash
# 1. 確認 cuDNN 8 存在
docker exec meetingscribe-app ls -la /usr/lib/x86_64-linux-gnu/libcudnn_ops_infer.so.8

# 2. 確認 GPU 偵測
docker logs meetingscribe-app | grep "NVIDIA GPU"

# 3. 確認 CUDA 轉錄
docker logs meetingscribe-app | grep "裝置: CUDA"
```

### 4.2 語言輸出檢查
```bash
# 上傳包含英文的測試音檔，檢查輸出是否為繁體中文
curl -X POST "http://localhost:9527/api/upload" \
  -F "file=@test_english.wav" \
  -F "enable_summarization=true"
```

### 4.3 文件更新檢查
- [ ] CHANGELOG.md 已更新
- [ ] README.md 如有需要已更新
- [ ] doc/ 資料夾相關文件已更新
- [ ] 版本號已更新

---

## 🔧 第五部分：常見錯誤與解決方案

### 5.1 錯誤：`libcudnn_ops_infer.so.8: cannot open shared object file`

**原因：** 基底映像只有 cuDNN 9，缺少 cuDNN 8

**解決：** 在 Dockerfile.gpu 中添加：
```dockerfile
RUN apt-get install -y libcudnn8=8.9.7.29-1+cuda12.2
```

### 5.2 錯誤：會議記錄輸出為英文

**原因：** 逐字稿包含英文，LLM 傾向英文輸出

**解決：** 
1. 確認 system prompt 包含 `<language_enforcement>` 區塊
2. 確認 user message 包含繁體中文前綴
3. 確認 `temperature` 設為 0.05-0.1 以提高指令遵循度

### 5.3 錯誤：av 套件編譯失敗

**原因：** 缺少 FFmpeg 開發庫

**解決：** 在 Dockerfile.gpu 中添加：
```dockerfile
RUN apt-get install -y \
    libavformat-dev libavcodec-dev libavdevice-dev \
    libavutil-dev libavfilter-dev libswscale-dev libswresample-dev
```

---

## 📋 第六部分：文件管理與同步（關鍵規則）

### 6.1 文件分類與用途

**核心文件**（必須維護）：

| 文件 | 用途 | 更新時機 |
|------|------|---------|
| `README.md` | 專案首頁，快速開始 | 每次版本發布 |
| `CHANGELOG.md` | 版本歷史記錄 | 每次 commit 前 |
| `INSTRUCTIONS.md` | 開發最高指導原則 | 發現新痛點時 |
| `doc/管理者操作指南.md` | 管理維運指南 | 架構變更時 |
| `doc/系統開發及實作規劃.md` | 完整技術文件 | 重大功能變更時 |

**平台專用文件**：

| 文件 | 適用對象 | 何時閱讀 |
|------|---------|---------|
| `doc/Windows批次檔部署指南.md` | Windows 使用者 | 部署前 |
| `doc/MAC_Docker部署指南.md` | macOS 使用者 | 部署前 |
| `doc/Docker映像檔Rebuild時機指南.md` | 所有使用者 | 修改程式前 |

**驗證報告**（歷史記錄）：

| 文件模式 | 說明 | 範例 |
|---------|------|------|
| `*_VERIFICATION_*.md` | 重大修復的驗證報告 | `GPU_ACCELERATION_VERIFICATION_v3.4.3.md` |
| 保留原則 | 不刪除，作為歷史證據 | - |

### 6.2 版本號同步規則

**強制要求**：
- 所有文件中的版本號必須一致
- 版本號格式：`v主版本.次版本.修訂號`（如 `v3.4.4`）
- 每次發布前執行全文件搜尋：`grep -r "v3.4.3" doc/`

**版本號出現位置**：
```yaml
- README.md: 第一行標題
- CHANGELOG.md: 最新版本區塊標題
- docker-compose-*.yml: labels.version
- 所有 doc/*.md: 頂部版本標註
```

### 6.3 文件更新檢查清單

每次版本發布前：

- [ ] 更新 `CHANGELOG.md` 記錄所有變更
- [ ] 更新 `README.md` 版本號和新功能說明
- [ ] 檢查所有 doc/ 文件版本號是否一致
- [ ] 確認 docker-compose-*.yml 的 version label 已更新
- [ ] 執行 `grep -r "v舊版本" .` 確認無遺漏

### 6.4 文件命名規範

**中文文件**：
- 使用繁體中文，台灣用語
- 範例：`管理者操作指南.md`、`系統開發及實作規劃.md`

**英文文件**：
- 全大寫 + 底線
- 範例：`INSTRUCTIONS.md`、`CHANGELOG.md`

**驗證報告**：
- 格式：`主題_VERIFICATION_v版本.md`
- 範例：`GPU_ACCELERATION_VERIFICATION_v3.4.3.md`

---

## 📋 第七部分：設定檔管理規範（避免混淆）

### 7.1 設定檔分類與對映

**環境變數檔**（`.env`）：

| 檔案 | 用途 | 何時使用 |
|------|------|---------|
| `.env.example` | 範本檔，進版控 | 新增參數時更新 |
| `.env` | 實際設定，不進版控 | 部署時建立 |
| `.env.local.example` | 本地覆蓋範本 | 開發環境需要時 |
| `.env.local` | 本地覆蓋，不進版控 | 本地開發時 |

**Docker Compose 檔**：

| 檔案 | 適用平台 | 何時使用 |
|------|---------|---------|
| `docker-compose.yml` | Windows/Linux CPU | 無 GPU 環境 |
| `docker-compose-windows-gpu.yml` | Windows + NVIDIA GPU | RTX 4090 等 |
| `docker-compose-mac.yml` | macOS | Mac 電腦 |

**Dockerfile**：

| 檔案 | 用途 | 何時修改 |
|------|------|---------|
| `Dockerfile` | 通用 CPU 版本 | 新增系統套件 |
| `Dockerfile.gpu` | GPU 加速版本 | cuDNN/CUDA 變更 |
| `Dockerfile.mac` | macOS 專用 | Mac 相容性問題 |

**決策樹**：
```
我要修改什麼？
├─ 調整參數（檔案大小、模型名稱）
│  → 修改 .env
│  → 重啟服務即可
│
├─ 改變 AI 行為（會議記錄格式）
│  → 修改 config.yaml
│  → 重啟服務即可
│
├─ 部署到不同平台
│  → 選擇對應 docker-compose-xxx.yml
│  → 執行 build + up
│
└─ 安裝新套件或系統依賴
   → 修改 Dockerfile
   → 執行 build --no-cache
```

### 7.2 設定檔修改後的影響範圍

| 修改內容 | 需要 Rebuild? | 需要重啟? | 影響範圍 |
|---------|--------------|----------|---------|
| `.env` 環境變數 | ❌ | ✅ | 僅影響運行時參數 |
| `config.yaml` | ❌ | ✅ | 僅影響 AI 行為 |
| `requirements.txt` | ✅ | ✅ | 需重裝 Python 套件 |
| `Dockerfile` | ✅ (--no-cache) | ✅ | 重建整個映像 |
| `docker-compose-*.yml` | ✅ | ✅ | 重建容器配置 |
| `backend/*.py` | ❌ (有 volume) | ✅ | 開發模式即時生效 |
| `frontend/*.html` | ❌ (有 volume) | ❌ | 重整瀏覽器即可 |

---

## 📋 第八部分：部署與維護規範

### 8.1 跨平台部署標準流程

**Windows（批次檔方式，推薦）**：
```batch
# 1. 環境檢查
docker --version
ollama list

# 2. 設定 API Key（雲端模式）
scripts\setup-api-key.ps1

# 3. 部署
cd scripts
deploy.bat build
deploy.bat up

# 4. 驗證
deploy.bat status
curl http://localhost:9527/api/health
```

**macOS**：
```bash
# 1. 環境檢查
docker --version
ollama list

# 2. 部署
chmod +x scripts/start-mac.sh
./scripts/start-mac.sh

# 3. 驗證
docker ps | grep meetingscribe
curl http://localhost:9527/api/health
```

### 8.2 日常維護規範

**每日檢查**（自動化）：
- 健康檢查：`curl http://localhost:9527/api/health`
- 日誌監控：`docker logs meetingscribe-app --tail 50 | grep ERROR`

**每週檢查**（手動）：
- 磁碟空間：`docker system df`
- 檔案清理：`curl -X POST http://localhost:9527/api/storage/cleanup`

**每月檢查**（手動）：
- 模型更新：`ollama pull gemma3:27b-it-qat`
- 版本更新：`git pull && scripts\deploy.bat build`

### 8.3 備份策略

**必須備份**：
```
convert/
├── .env                 # ✅ API Key 和設定
├── config.yaml         # ✅ 系統提示詞
└── data/
    ├── uploads/        # ❌ 暫存，可不備份
    └── outputs/        # ✅ 處理結果（重要）
```

**備份頻率**：
- `.env` 和 `config.yaml`：每次修改後
- `data/outputs/`：每週自動備份

---

## 📋 第九部分：自動 Git Commit 原則（Automatic Git Commit Principle）

### 9.1 強制規則

**Copilot MUST 在每次完成一項任務後自動進行 git commit，並遵循以下強制規則**：

1. **Commit MUST 包含完整且準確的變更內容**
   - 不可忽略任何重要檔案修改
   - 不可合併不相關的變更
   - 若包含多個邏輯無關的變更，應拆分為多次 commit

2. **Commit Log Message MUST 遵循要求**
   - ✅ 詳細、精確、可理解
   - ✅ 清楚描述任務目的、處理方式、產生的變更
   - ✅ 若有推論或假設，MUST 以 `[推測]` 明確標記
   - ✅ **所有 Commit Message MUST 使用繁體中文（台灣正體）撰寫**

### 9.2 Commit Message 強制格式（zh-TW）

```
<type>: <summary>

詳細分析（Detailed Analysis）:
- 變更了什麼（What was changed）
- 為什麼要改（Why it was changed）
- 決策如何衍生（How the decision was derived）
  ├─ 來自使用者輸入（From user input）
  ├─ 來自官方文件（From official documentation）
  ├─ 來自代碼分析（From code analysis）
  └─ 或 [推測] 基於最佳實踐（Based on best practices - if inference）
- 任何後續工作或 TODO
- 受影響的檔案清單
```

### 9.3 類型標籤（Type Tags）

- `[新增]`：新功能 (feat)
- `[修復]`：Bug 修復 (fix)
- `[重構]`：程式碼重構 (refactor)
- `[文件]`：文件更新 (docs)
- `[優化]`：效能優化 (perf)
- `[安全]`：安全性修復 (security)

### 9.4 完整範例

```
[新增] 管理者操作指南 - 深度梳理專案架構與配置

詳細分析:
變更內容:
- 新增 doc/管理者操作指南.md (19KB+)
- 擴充 .github/INSTRUCTIONS.md 至 v2.0
- 新增第六至九部分的開發規範

為什麼改:
根據使用者提出的核心痛點，專案經歷多次修正導致：
1. 架構混淆 - 不清楚系統組成與跨平台差異
2. 設定檔混亂 - 多種 .env、.yml、.yaml 檔不知何時用
3. Rebuild 時機不明 - 不確定何時需要重建 Docker
4. GPU 設定複雜 - cuDNN 依賴與環境變數容易出錯
5. 文件不同步 - 版本號不一致導致混淆

決策衍生:
[來自使用者輸入] 用戶明確指出需要友善、非技術人員可理解的指南
[來自代碼分析] 分析 CHANGELOG.md、README.md、所有 doc/*.md 文件
[最佳實踐] 採用第一性原理分析，建立三層知識體系

後續工作:
- [ ] 保持文件版本號同步
- [ ] 定期驗證 Docker Rebuild 指南準確性
- [ ] 根據新增功能更新 GPU 加速部分

受影響檔案:
- .github/INSTRUCTIONS.md (v2.0)
- doc/管理者操作指南.md (new)
- CHANGELOG.md
- README.md
```

### 9.5 提交時機與頻率

- **MUST 在任務完成後立即執行**
  - 完成一個獨立功能 → commit
  - 完成一個 Bug 修復 → commit
  - 完成文件更新 → commit

- **若一次任務包含多個步驟**
  - MAY 依邏輯拆分多次 commit
  - 但不可合併至難以追溯原因

- **除非有更高原則阻擋**
  - 必須在提交訊息中說明阻擋原因
  - 例：「因安全考量暫未提交敏感設定檔」

### 9.6 提交前檢查清單

**每次 commit 前 MUST 完成**：

- [ ] 執行本地測試驗證變更正確
- [ ] 更新 `CHANGELOG.md` 記錄版本變更
- [ ] 檢查所有檔案的版本號是否一致
- [ ] 確認無敏感資料（API Key、密碼、個人資訊）洩漏
- [ ] 執行 `git status` 確認文件清單正確
- [ ] 撰寫清楚、完整的繁體中文 commit message
- [ ] 驗證 commit message 包含詳細分析與決策衍生

---

## 📋 第十部分：第一性原理分析與技術文件查詢

### 10.1 問題分析原則

**遇到任何問題或要新增功能時，MUST 使用第一性原理進行深度分析**：

1. **質疑現有假設** - 為什麼會這樣？是否有更根本的原因？
2. **追溯根本原因** - 問題的本質是什麼？不是症狀。
3. **分解複雜問題** - 將問題拆解為基本單位。
4. **從基礎開始建構** - 基於基本事實重新組合解決方案。

**應用在本專案**：

- GPU 加速失效？→ 分析 CUDA/cuDNN/FFmpeg 依賴鏈（見第一部分）
- 繁體中文輸出英文？→ 分析 LLM 多語言傾向（見第二部分）
- Docker 重建時間長？→ 分析模型快取機制（見第三部分）
- 文件混淆？→ 分析設定檔優先順序與決策邏輯（本部分）

### 10.2 技術文件查詢強制要求

**MUST 使用 Context7 MCP 取得官方技術文件，而非依賴內存知識**：

```
問題 → 第一性原理分析 → Context7 查詢 → 驗證方案 → 實作 → Commit
```

**查詢優先順序**：

1. **官方文件**（最可信）
   - 例：CTranslate2 官方指南（cuDNN 8 需求來源）
   - 例：NVIDIA CUDA 官方文件
   - 例：Docker 官方參考

2. **GitHub Issues/Discussions**（社群驗證）
   - 例：faster-whisper issues
   - 例：Ollama discussions

3. **技術博客與最佳實踐**（參考實現）
   - 但必須交叉驗證官方文件

**禁止**：
- ❌ 單純依賴舊經驗
- ❌ 假設而未驗證
- ❌ 使用過時文件

### 10.3 Context7 查詢範例

```
# 查詢 CTranslate2 cuDNN 依賴
context7-resolve-library-id: "CTranslate2"
context7-get-library-docs: "/opennmt/CTranslate2/latest"
topic: "GPU support cuDNN requirements"

# 查詢 Docker Volume 最佳實踐
context7-resolve-library-id: "Docker"
context7-get-library-docs: "/docker/docs"
topic: "volumes persistent storage"

# 查詢 faster-whisper GPU 加速
context7-resolve-library-id: "faster-whisper"
context7-get-library-docs: "/faster-whisper/latest"
topic: "CUDA GPU acceleration"
```

### 10.4 決策文檔化

**每次根據第一性原理得出的決策，MUST 記錄於 INSTRUCTIONS.md**：

| 決策 | 根本原因 | 驗證來源 | 記錄位置 |
|------|---------|---------|---------|
| cuDNN 8 必須 | CTranslate2 語音識別需求 | 官方 GitHub | 第一部分 1.1 |
| 三道防線中文輸出 | Gemma3 多語言傾向 | 實測+社群 | 第二部分 2.1-2.3 |
| Volume 持久化模型 | --no-cache 清除 layer | 實測 | 第三部分 3.2 |
| 文件優先順序 | Docker Compose 規範 | 官方文件 | 第七部分 7.2 |

---

## 🔧 第九部分：Git 版本控制策略 - 雙平台管理最佳實踐

### 9.1 核心原則

根據業界最佳實踐（參考 [The Twelve-Factor App](https://12factor.net/)），我們採用以下策略：

**最高指導原則**：
1. ✅ **配置與程式碼分離**：底層程式邏輯共享，配置檔案平台隔離
2. ✅ **單一程式碼庫**：所有平台使用同一個 Git Repository
3. ✅ **環境變數優先**：敏感資訊（API Key）使用 `.env`，不進版控
4. ✅ **平台配置檔案**：平台特定設定使用 `config.{platform}.yaml`

### 9.2 檔案組織結構

```
convert/
├── .gitignore                      # 定義不進版控的檔案
├── .env.example                    # 環境變數範例（進版控）✅
├── .env                            # 實際環境變數（不進版控）⚠️
│
├── config.yaml                     # Windows/Linux 預設配置（進版控）✅
├── config.mac.yaml                 # macOS 專用配置（進版控）✅
│
├── backend/                        # 共享程式邏輯（進版控）✅
│   ├── core/
│   │   ├── config.py              # Pydantic 設定類別
│   │   └── platform_config.py     # 平台檢測與配置載入
│   ├── services/
│   │   ├── summarization.py       # LLM 服務（支援 Ollama/LM Studio/Gemini）
│   │   └── transcription.py       # Whisper 服務（支援 MLX/Faster-Whisper）
│   └── api/
│       └── routes.py               # API 路由
│
├── scripts/                        # 平台特定腳本（進版控）✅
│   ├── deploy.bat                 # Windows Docker 部署
│   ├── deploy.sh                  # Linux Docker 部署
│   ├── start-mac-native.sh        # macOS 原生服務啟動
│   ├── restart-mac-native.sh      # macOS 原生服務重啟
│   └── stop-mac-native.sh         # macOS 原生服務停止
│
├── docker/                         # Docker 配置（進版控）✅
│   ├── docker-compose.yml         # Linux 預設
│   ├── docker-compose-windows-gpu.yml  # Windows GPU
│   └── Dockerfile                 # 通用映像定義
│
├── old_mac/                        # 舊版 macOS Docker 方案（不進版控）⚠️
└── doc/                            # 文件（進版控）✅
```

### 9.3 配置載入優先順序

```
1. config.yaml          # 基礎配置（所有平台共用）
2. config.{platform}.yaml  # 平台特定配置（覆蓋基礎配置）
3. .env                 # 環境變數（覆蓋所有配置）
```

### 9.4 平台隔離保證機制

#### 自動平台檢測

```python
# backend/core/platform_config.py
def get_platform() -> str:
    """自動檢測平台"""
    system = platform.system().lower()
    if system == "darwin":
        return "macos"
    elif system == "windows":
        return "windows"
    return "linux"
```

#### 配置自動載入

```python
def load_platform_config() -> Dict[str, Any]:
    """自動載入平台配置（深度合併）"""
    config = yaml.safe_load(open('config.yaml'))
    
    platform_config_path = f'config.{get_platform()}.yaml'
    if os.path.exists(platform_config_path):
        platform_config = yaml.safe_load(open(platform_config_path))
        config = deep_merge(config, platform_config)
    
    return config
```

### 9.5 禁止事項

**Windows 使用者**：
- ❌ 禁止修改 `config.mac.yaml`
- ❌ 禁止修改 `scripts/start-mac-native.sh`

**macOS 使用者**：
- ❌ 禁止修改 `config.yaml`（除非確定不影響 Windows）
- ❌ 禁止修改 `docker/docker-compose-*.yml`

**所有使用者**：
- ❌ 禁止將 `.env` 提交到 Git
- ❌ 禁止硬編碼平台特定邏輯（使用 `if get_platform() == 'macos'`）

### 9.6 參考資料

- [The Twelve-Factor App - Config](https://12factor.net/config)
- [Git Branching Strategies](https://www.atlassian.com/git/tutorials/comparing-workflows)

---

## 📌 版本歷史

| 版本 | 日期 | 更新內容 |
|------|------|----------|
| v1.0 | 2025-12-05 | 初版：記錄 cuDNN 8 需求、繁體中文輸出規範、Docker 重建優化 |
| v2.0 | 2025-12-06 | 擴充版：新增文件管理、設定檔對映、部署維護、Git 規範 |
| v2.1 | 2025-12-06 | 強化版：新增自動 Commit 原則、第一性原理分析、Context7 查詢規範 |
| v3.5.0 | 2025-12-06 | 雙平台版：新增 Git 版本控制策略、macOS 原生模式管理 |

---

## 🎯 總結：核心原則（必記）

### 三大絕對原則

1. **GPU 加速**：Dockerfile.gpu 必須包含 cuDNN 8 + cuDNN 9
2. **繁體中文輸出**：三道防線（System Prompt + User Message + 參數約束）
3. **Docker 隔離**：獨立網路、獨立命名、不影響其他服務

### 五個關鍵決策

1. **何時 Rebuild？** → 改 Dockerfile 才 Rebuild，改程式碼只需重啟
2. **何時用哪個 compose？** → Windows GPU 用 `-windows-gpu.yml`，Mac 用 `-mac.yml`
3. **何時修改哪個設定？** → 參數改 `.env`，格式改 `config.yaml`
4. **如何驗證 GPU？** → `docker logs | grep CUDA`
5. **如何同步文件？** → 每次發布前 `grep -r "v舊版本"`

### 七個禁止事項

1. ❌ 禁止刪除 cuDNN 8 依賴（會導致 Whisper 失效）
2. ❌ 禁止移除繁體中文語言約束（會輸出英文）
3. ❌ 禁止修改 Docker 網路為共用網路（會影響其他服務）
4. ❌ 禁止將 `.env` 提交到 Git（含 API Key）
5. ❌ 禁止修改 Dockerfile 不更新 CHANGELOG（文件不同步）
6. ❌ 禁止使用 `docker system prune -a`（會刪除 Volume）
7. ❌ 禁止修改核心邏輯不測試（可能破壞現有功能）

---

> **⚠️ 最高警告：** 違反本文件規範的修改，可能導致：
> 
> 1. **GPU 加速失效**（退回 CPU 模式，速度降低 10 倍）
> 2. **會議記錄輸出英文**（需手動翻譯，失去自動化價值）
> 3. **Docker 重建時間過長**（浪費 20-30 分鐘下載模型）
> 4. **影響其他 Docker 服務**（網路衝突、埠佔用）
> 5. **資料遺失**（刪除 Volume 導致模型重新下載）
> 
> **修改前請先閱讀本文件，遵循檢查清單！**

---

## 📁 文件組織規範（2025-12-06 新增）

### 目錄結構
```
doc/
├── evidence/        # 驗證證據 - 測試驗證報告和證據
├── reports/         # 技術報告 - 技術分析和修復報告
├── guides/          # 部署指南 - 部署、操作、使用指南
├── analysis/        # 分析文件 - 系統分析、架構分析
└── README.md        # 文件導航說明
```

### 命名規範

#### 通用規則
1. **全小寫字母**：所有檔案名稱使用小寫字母
2. **底線分隔**：使用底線 `_` 分隔單字
3. **有意義的名稱**：檔案名稱應清楚描述內容
4. **版本標記**：重要文件應包含版本號（例如：`_v3.5.1`）

#### 檔案類型規範

| 類型 | 位置 | 格式 | 範例 |
|------|------|------|------|
| 驗證證據 | `doc/evidence/` | `{功能}_{類型}_evidence_v{版本}.md` | `queue_logic_fix_evidence_v3.5.1.md` |
| 技術報告 | `doc/reports/` | `{功能}_{類型}_report_v{版本}.md` | `queue_logic_fix_report_v3.5.1.md` |
| 部署指南 | `doc/guides/` | `{平台}_{類型}_guide.md` | `mac_deployment_guide.md` |
| 分析文件 | `doc/analysis/` | `{主題}_analysis.md` | `system_development_analysis.md` |

#### 新增文件流程
1. 確定文件類型（evidence/reports/guides/analysis）
2. 使用正確的命名規範
3. 放入對應的目錄
4. 更新 `doc/README.md` 的檔案清單
5. 在 Git commit 中說明新增的文件

#### 文件維護
- **更新文件**：保持檔案名稱一致，重大變更時考慮版本號升級
- **刪除文件**：考慮移至 `doc/archive/` 而非直接刪除
- **版本控制**：重要文件必須包含版本號，便於追蹤變更

### 文件分類規則

#### evidence/ - 驗證證據
- 包含所有測試驗證報告和證據
- 記錄功能驗證、測試結果、修復證明
- 檔案名稱必須包含功能名稱和版本號

#### reports/ - 技術報告
- 包含詳細的技術分析和修復報告
- 記錄問題分析、解決方案、實作細節
- 可選擇性包含版本號

#### guides/ - 部署指南
- 包含所有部署、操作、使用指南
- 依平台分類（mac/windows/docker）
- 檔案名稱應清楚標示平台和用途

#### analysis/ - 分析文件
- 包含系統分析、架構分析、需求分析
- 記錄設計決策、技術選型、架構規劃
- 長期保存，較少更新

---

## 🚨 第十一部分：版本控制最高原則（2025-12-07 新增）

### 11.1 穩定版本保護策略

> **🔴 最高原則：main 分支僅允許 Stable 等級的版本**

**穩定版本定義：**
- ✅ 經過完整功能測試
- ✅ 經過跨平台（Mac + Windows）驗證
- ✅ 無已知重大 Bug
- ✅ 文件已同步更新
- ✅ 所有相關配置檔完備

**當前穩定版本基準：**
```
Commit: 7100d81
版本：v3.5.4
狀態：Stable（穩定版本）
日期：2025-12-07
```

### 11.2 分支管理策略

```
main (穩定版本)
│
├── develop (開發整合分支)
│   ├── feature/xxx (新功能分支)
│   ├── fix/xxx (修復分支)
│   └── docs/xxx (文件分支)
│
└── release/vX.X.X (發布候選分支)
```

**分支規則：**

| 分支類型 | 來源 | 合併目標 | 用途 |
|---------|------|---------|------|
| `main` | release | - | 穩定版本，僅接受 release 合併 |
| `develop` | main | release | 開發整合，累積多個功能後整合 |
| `feature/*` | develop | develop | 新功能開發 |
| `fix/*` | develop | develop | Bug 修復 |
| `release/*` | develop | main + develop | 版本發布準備 |
| `hotfix/*` | main | main + develop | 緊急修復 |

### 11.3 Push 防呆機制

**Pre-Push Hook 強制檢查：**

每次 push 到 main 分支時，MUST 執行以下檢查：

1. **版本標記檢查**：確認 commit 包含 `[Stable]` 標記
2. **分支來源檢查**：確認是從 release/* 或 hotfix/* 分支合併
3. **測試狀態檢查**：確認所有測試通過
4. **文件同步檢查**：確認 CHANGELOG.md 已更新

**安裝 Pre-Push Hook：**

```bash
# 在專案根目錄執行
cp scripts/hooks/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

### 11.4 Copilot 自動提醒規則

**當使用者嘗試直接 push 到 main 時，Copilot MUST：**

1. ⚠️ **立即警告**：「您正在嘗試 push 到 main 分支，這是受保護的穩定版本分支」
2. 📋 **提示檢查清單**：
   - [ ] 此變更是否經過完整測試？
   - [ ] 此變更是否經過跨平台驗證？
   - [ ] CHANGELOG.md 是否已更新？
   - [ ] 版本號是否已更新？
3. 🚫 **建議替代方案**：「建議先 push 到 develop 分支，測試通過後再透過 release 分支合併到 main」

### 11.5 版本發布流程

**標準發布流程（非緊急）：**

```bash
# 1. 確保在 develop 分支
git checkout develop

# 2. 建立 release 分支
git checkout -b release/v3.5.5

# 3. 進行最終測試和調整
# ... 測試 ...

# 4. 更新版本號和 CHANGELOG
# 編輯 VERSION、CHANGELOG.md

# 5. 合併到 main
git checkout main
git merge --no-ff release/v3.5.5 -m "[Stable] 發布 v3.5.5"

# 6. 打標籤
git tag -a v3.5.5 -m "版本 v3.5.5 - 穩定版本"

# 7. 合併回 develop
git checkout develop
git merge release/v3.5.5

# 8. 清理 release 分支
git branch -d release/v3.5.5
```

**緊急修復流程：**

```bash
# 1. 從 main 建立 hotfix 分支
git checkout main
git checkout -b hotfix/critical-bug-fix

# 2. 修復問題
# ... 修復 ...

# 3. 測試驗證
# ... 測試 ...

# 4. 合併到 main
git checkout main
git merge --no-ff hotfix/critical-bug-fix -m "[Stable][Hotfix] 修復關鍵問題"

# 5. 合併到 develop
git checkout develop
git merge hotfix/critical-bug-fix

# 6. 清理
git branch -d hotfix/critical-bug-fix
```

### 11.6 禁止事項

1. ❌ **禁止直接 push 到 main**：所有變更必須透過 PR 或合併
2. ❌ **禁止跳過測試**：必須經過完整測試才能合併到 main
3. ❌ **禁止遺漏文件更新**：CHANGELOG.md 和相關文件必須同步
4. ❌ **禁止跨過 develop**：新功能不可直接從 feature 合併到 main

### 11.7 版本歷史追蹤

| 版本 | Commit | 狀態 | 日期 | 說明 |
|------|--------|------|------|------|
| v3.5.4 | 7100d81 | ✅ Stable | 2025-12-07 | 穩定版本基準 |

---

## 📌 版本歷史（INSTRUCTIONS.md）

| 版本 | 日期 | 更新內容 |
|------|------|----------|
| v1.0 | 2025-12-05 | 初版：記錄 cuDNN 8 需求、繁體中文輸出規範、Docker 重建優化 |
| v2.0 | 2025-12-06 | 擴充版：新增文件管理、設定檔對映、部署維護、Git 規範 |
| v2.1 | 2025-12-06 | 強化版：新增自動 Commit 原則、第一性原理分析、Context7 查詢規範 |
| v3.5.0 | 2025-12-06 | 雙平台版：新增 Git 版本控制策略、macOS 原生模式管理 |
| v3.5.4 | 2025-12-07 | 穩定版：新增版本控制最高原則、分支管理策略、Push 防呆機制 |

