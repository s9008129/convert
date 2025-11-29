# ============================================
# MeetingScribe - 會議轉錄工具 Docker 映像
# v2.1 - 支援 CUDA GPU 加速 + 智能降級 + 排隊系統
# ============================================

# 基礎映像：NVIDIA CUDA + cuDNN
FROM nvidia/cuda:12.1-cudnn8-runtime-ubuntu22.04

# 設定環境變數
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Taipei \
    # 預設配置
    MAX_FILE_SIZE_MB=100 \
    ENABLE_BATCH_UPLOAD=false \
    MAX_CONCURRENT_TASKS=1 \
    QUEUE_MAX_SIZE=50

# 安裝系統依賴
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-venv \
    python3.11-dev \
    python3-pip \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.11 /usr/bin/python3 \
    && ln -sf /usr/bin/python3.11 /usr/bin/python

# 建立非 root 用戶
RUN useradd -m -u 1000 appuser

# 設定工作目錄
WORKDIR /app

# 複製依賴檔案
COPY requirements.txt .

# 安裝 Python 依賴（包含 CUDA 支援 + Gemini API）
RUN pip3 install --no-cache-dir --upgrade pip && \
    pip3 install --no-cache-dir -r requirements.txt

# 複製應用程式碼
COPY --chown=appuser:appuser . .

# 預載 Whisper 模型（建構時下載，打包進映像）
RUN python3 -c "from faster_whisper import WhisperModel; WhisperModel('large-v3', device='cpu', compute_type='int8')" || true

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
CMD ["python3", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "9527"]
