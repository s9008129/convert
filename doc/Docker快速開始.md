# Docker 快速開始指南

> 基於 PromptCraft 專案的成功經驗，為「會議轉錄工具」專案提供的 Docker 部署快速指南。

## 🚀 快速開始

### 1. 準備必要檔案

在專案根目錄建立以下檔案：

#### Dockerfile
```dockerfile
# ============================================
# 會議轉錄工具 Dockerfile
# Python + faster-whisper + Ollama
# ============================================

FROM python:3.11-slim AS builder

WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 建立虛擬環境
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 複製並安裝 Python 依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ============================================
FROM python:3.11-slim AS runner

WORKDIR /app

# 安裝 runtime 依賴
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 建立非 root 用戶
RUN groupadd --system --gid 1001 appgroup && \
    useradd --system --uid 1001 --gid appgroup appuser

# 複製虛擬環境
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 複製應用程式碼
COPY --chown=appuser:appgroup . .

# 建立必要目錄
RUN mkdir -p /app/input /app/output /app/temp /app/logs && \
    chown -R appuser:appgroup /app

USER appuser

# 健康檢查
HEALTHCHECK --interval=60s --timeout=10s --retries=3 \
    CMD curl -f http://host.docker.internal:11434/api/version || exit 1

CMD ["python", "main.py"]
```

#### docker-compose.yml
```yaml
services:
  transcriber:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: meeting-transcriber
    restart: "no"
    
    # 掛載目錄
    volumes:
      - ./input:/app/input
      - ./output:/app/output
      - ./temp:/app/temp
      - ./logs:/app/logs
      - ./config.yaml:/app/config.yaml:ro
    
    # 連接主機 Ollama
    extra_hosts:
      - "host.docker.internal:host-gateway"
    
    environment:
      - OLLAMA_HOST=http://host.docker.internal:11434
    
    networks:
      - transcriber-net

networks:
  transcriber-net:
    driver: bridge
    name: transcriber-net
```

#### requirements.txt
```
pyyaml>=6.0
httpx>=0.24.0
faster-whisper>=0.9.0
```

#### .dockerignore
```
.git
.gitignore
__pycache__
*.pyc
.venv
venv
*.log
logs/*
output/*
temp/*
.DS_Store
Thumbs.db
*.md
!README.md
```

### 2. Windows 部署

```powershell
# 1. 確保 Docker Desktop 已啟動
# 2. 確保 Ollama 已啟動並載入模型

# 建構映像
docker compose build

# 執行轉錄（一次性）
docker compose run --rm transcriber

# 或使用互動模式
docker compose run --rm transcriber python main.py --verbose
```

### 3. macOS/Linux 部署

```bash
# 建構映像
docker compose build

# 執行轉錄
docker compose run --rm transcriber

# 互動模式
docker compose run --rm transcriber python main.py --verbose
```

## 📂 目錄結構

```
會議轉錄工具/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .dockerignore
├── config.yaml
├── main.py
├── src/
│   ├── ollama_client.py
│   ├── whisper_transcriber.py
│   └── summarizer.py
├── input/         # 放入要轉錄的音訊/視訊檔案
├── output/        # 輸出摘要 Markdown
├── temp/          # 逐字稿快取
└── logs/          # 日誌
```

## ⚠️ 注意事項

1. **Ollama 必須在主機執行**：Docker 容器透過 `host.docker.internal` 連接主機的 Ollama

2. **faster-whisper 需要大記憶體**：建議至少 8GB RAM

3. **GPU 加速**：如需 GPU，需額外設定 NVIDIA Container Toolkit

## 🔧 疑難排解

### 無法連接 Ollama

```bash
# 確認 Ollama 服務狀態
curl http://localhost:11434/api/version

# 容器內測試
docker compose run --rm transcriber curl http://host.docker.internal:11434/api/version
```

### 記憶體不足

修改 `docker-compose.yml`：
```yaml
deploy:
  resources:
    limits:
      memory: 8G
```

---

完整說明請參考：[Docker部署經驗指南.md](./Docker部署經驗指南.md)
