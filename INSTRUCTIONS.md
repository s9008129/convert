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
   - 英文專有名詞必須翻譯：AI→人工智慧、RPA→流程自動化
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

## 📌 版本歷史

| 版本 | 日期 | 更新內容 |
|------|------|----------|
| v1.0 | 2025-12-05 | 初版：記錄 cuDNN 8 需求、繁體中文輸出規範、Docker 重建優化 |

---

> **⚠️ 警告：** 每次修改 GPU 或 LLM 相關功能前，請先閱讀本文件。
> 
> 違反本文件規範的修改，可能導致：
> 1. GPU 加速失效（退回 CPU 模式）
> 2. 會議記錄輸出英文
> 3. Docker 重建時間過長
