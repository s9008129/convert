# 🚨 MeetingScribe 開發最高指導原則

> **版本**: v1.0  
> **建立日期**: 2025-12-05  
> **目的**: 避免重複犯同樣的錯誤，確保每次修改都能正確運作

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
