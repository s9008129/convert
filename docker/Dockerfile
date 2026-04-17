# ============================================
# MeetingScribe - 會議轉錄工具 Docker 映像
# v2.2 - 多階段建置優化
# ============================================

# ========== 建置階段 ==========
FROM python:3.11-slim-bookworm AS builder

# 安裝編譯依賴 (使用 Debian bookworm 的 FFmpeg 6.x)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    pkg-config \
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libswscale-dev \
    libswresample-dev \
    libavfilter-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# 複製依賴檔案並安裝到虛擬環境
COPY requirements.txt .
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# 先安裝與 FFmpeg 6.x 兼容的 av 版本，然後再安裝其他依賴
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir av==12.0.0 && \
    pip install --no-cache-dir -r requirements.txt

# ========== 運行階段 ==========
FROM python:3.11-slim-bookworm

# 設定環境變數
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Taipei \
    PATH="/opt/venv/bin:$PATH" \
    # 預設配置
    MAX_FILE_SIZE_MB=100 \
    ENABLE_BATCH_UPLOAD=false \
    MAX_CONCURRENT_TASKS=1 \
    QUEUE_MAX_SIZE=50 \
    HF_HOME=/app/models/huggingface \
    XDG_CACHE_HOME=/app/models/cache \
    TRANSFORMERS_CACHE=/app/models/transformers

# 安裝運行時依賴（只需要 ffmpeg runtime，不需要開發套件）
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 建立非 root 用戶
RUN useradd -m -u 1000 appuser

# 設定工作目錄
WORKDIR /app

# 從建置階段複製虛擬環境
COPY --from=builder /opt/venv /opt/venv

# 複製應用程式碼
COPY --chown=appuser:appuser . .

# 建立資料目錄
RUN mkdir -p /app/data/uploads /app/data/outputs /app/data/cache /app/models && \
    chown -R appuser:appuser /app/data /app/models

# 切換到非 root 用戶
USER appuser

# 暴露端口
EXPOSE 9527

# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:9527/api/health || exit 1

# 啟動命令
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "9527"]
