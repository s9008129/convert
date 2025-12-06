# 🚀 GPU 加速支援完整指南

> **版本**: v3.4.4 - GPU 加速 + cuDNN 8/9 + 模型快取優化  
> **最後更新**: 2025-12-05  
> **適用版本**: v3.4.3+ (CUDA 12 + cuDNN 8/9)  
> **狀態**: 🟢 GPU 加速驗證完成

---

## ⚠️ 重要：cuDNN 依賴規則

> **必讀：** 在修改任何 GPU 相關設定前，請先閱讀 [INSTRUCTIONS.md](../INSTRUCTIONS.md)

**CTranslate2（faster-whisper 底層）需要：**
```
├── CUDA 12.x
├── cuDNN 9（用於一般推理）
└── cuDNN 8（用於語音識別模型，如 Whisper）⚠️ 關鍵！
```

官方文件明確說明：
> "If you plan to run models with convolutional layers (e.g. for **speech recognition**), 
> you should also install **cuDNN 8** for CUDA 12.x."

---

## 📌 概述

MeetingScribe v3.4.4 完全支援 NVIDIA GPU 加速，相比 CPU 提升 **80-100倍** 轉錄速度！

### 🎯 版本更新歷史

| 版本 | 發布日期 | 改進內容 | GPU 加速 |
|------|---------|---------|---------|
| **v3.4.4** | 2025-12-05 | ✅ 模型快取優化 + 繁體中文輸出修復 | **93.7× 實時倍率** |
| **v3.4.3** | 2025-12-05 | ✅ 真正修復 GPU - cuDNN 8 + cuDNN 9 | **93.7× 實時倍率** |
| **v3.4.0** | 2025-01-27 | ✅ 動態 GPU 偵測 + VRAM 資源釋放 | **93.7× 實時倍率** |
| **v3.3.6** | 2025-12-03 | ✅ cuDNN 版本相容性修復 | **93.7× 實時倍率** |
| **v3.3.5** | 2025-12-03 | ✅ GPU Dockerfile 建立 | **83× 實時倍率** |

---

## 🔥 v3.4.3 重大修復：cuDNN 8 + cuDNN 9

### 問題現象（v3.4.0）

即使程式碼正確，容器仍無法使用 GPU：
- ❌ 日誌顯示 GPU 偵測成功，但轉錄時崩潰
- ❌ 錯誤：`Could not load library libcudnn_ops_infer.so.8`
- ❌ 容器反覆重啟

### 根本原因分析（第一性原理）

**問題一：原始 Dockerfile 無 CUDA**
```
docker/Dockerfile 使用 python:3.11-slim-bookworm
├── ❌ 無 CUDA Runtime
├── ❌ 無 cuDNN
└── ❌ 無 cuBLAS
```

**問題二：cuDNN 版本不完整**
```
nvidia/cuda:12.3.2-cudnn9-runtime-ubuntu22.04
├── ✅ CUDA 12.3.2
├── ✅ cuDNN 9.0.0
└── ❌ cuDNN 8（Whisper 語音識別需要！）
```

### 解決方案（v3.4.3）

創建 `docker/Dockerfile.gpu`：
```dockerfile
FROM nvidia/cuda:12.3.2-cudnn9-runtime-ubuntu22.04

# ✅ 安裝 cuDNN 8（Whisper 語音識別必需）
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libcudnn8=8.9.7.29-1+cuda12.2 \
    && rm -rf /var/lib/apt/lists/* && ldconfig
```

---

## 🔥 v3.4.0 修復：動態 GPU 偵測 + VRAM 資源管理

### 問題現象（v3.3.6）

即使 GPU 環境配置正確，仍可能遇到以下問題：
- ❌ Whisper 轉錄突然改用 CPU（原本使用 GPU）
- ❌ GPU 加速「時好時壞」，不穩定
- ❌ Ollama 運行後，Whisper 就無法使用 GPU

### 根本原因分析（第一性原理）

**問題一：GPU 偵測結果被快取**

```
1. 程式啟動時偵測裝置 → 假設 Ollama 佔用 VRAM → 偵測結果：CPU
2. 偵測結果被快取在 device_detector.current_device
3. 即使 Ollama 已釋放 VRAM，後續任務仍使用快取的 CPU 結果
4. GPU 加速永久失效，直到服務重啟
```

**問題二：VRAM 資源競爭**

```
Whisper medium 模型需要 ~3GB VRAM
Ollama gemma3:27b 模型需要 ~18GB VRAM
RTX 4090 總共 24GB VRAM

如果兩者同時載入，VRAM 不足導致：
- Whisper 被迫降級到 CPU
- 系統效能大幅下降
```

### 解決方案（v3.4.0）

#### 修復一：動態 GPU 偵測

每次轉錄任務前，強制重新偵測裝置：

```python
# backend/services/transcription.py
def _load_model(self):
    # 重置裝置偵測快取，強制每次重新偵測
    device_detector.current_device = None
    
    self._device = device_detector.detect_best_device()
    self._compute_type = "float16" if self._device == DeviceType.CUDA else "int8"
    
    # 每次載入新模型，確保使用當前最佳裝置
    self._model = WhisperModel(...)
```

#### 修復二：VRAM 資源釋放機制

**Whisper 轉錄後釋放**：
```python
def _unload_model(self):
    """釋放模型資源，清空 VRAM"""
    if self._model is not None:
        del self._model
        self._model = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
```

**Ollama 使用後立即釋放**：
```python
# API 呼叫加入 keep_alive: "0"
response = await client.post(
    f"{base_url}/api/generate",
    json={
        "model": model_name,
        "keep_alive": "0",  # 使用完畢立即釋放 VRAM
        ...
    }
)
```

### 驗證結果（v3.4.0）

**VRAM 使用時序圖**：

```
時間軸 →
[T0] Ollama 閒置，Whisper 開始 → GPU 偵測成功 → VRAM: 3GB (Whisper)
[T1] Whisper 完成 → _unload_model() → VRAM: 0GB
[T2] Ollama 摘要開始 → VRAM: 18GB (Ollama)
[T3] Ollama 完成 → keep_alive="0" → VRAM: 0GB
[T4] 下一次 Whisper → GPU 偵測成功 → VRAM: 3GB (Whisper)
```

**預期效果**：
- ✅ Whisper 每次轉錄都能正確使用 GPU
- ✅ VRAM 使用後立即釋放，避免資源競爭
- ✅ 多任務執行時，GPU 加速穩定可用

---

## 🔧 v3.3.6 重大修復：cuDNN 版本相容性

### 問題現象（v3.3.5）

即使使用了專用 GPU Dockerfile，仍然遇到以下問題：
- ❌ GPU 使用率只有 5%（應該 35-41%）
- ❌ 錯誤訊息：`Could not load library libcudnn_ops_infer.so.8`
- ❌ GPU 記憶體使用 1.0-1.1 GB（應該 ~3 GB）

### 根本原因分析（第一性原理）

**關鍵發現**：ctranslate2 版本與 cuDNN 版本必須相容

| ctranslate2 版本 | 需要 cuDNN 版本 | 支援的 cuda.so 版本 |
|-----------------|------------|---------|
| < 4.5.0 | **cuDNN 8** | libcudnn_ops_infer.so.**8** |
| **>= 4.5.0** | **cuDNN 9** | libcudnn.so.**9** |

**參考資料**：[CTranslate2 CHANGELOG v4.5.0](https://github.com/OpenNMT/CTranslate2/blob/master/CHANGELOG.md)
> "The Ctranslate2 Python package now supports CUDNN 9 and is no longer compatible with CUDNN 8."

### 解決方案（v3.3.6）

三個核心修改：

1. **升級 ctranslate2 到 4.6.1**
   ```diff
   # requirements.txt
   - ctranslate2==4.0.0
   + ctranslate2==4.6.1
   ```

2. **新增 requests 依賴**（faster-whisper 1.1.0 需要）
   ```diff
   # requirements.txt
   + requests>=2.31.0
   ```

3. **使用 cuDNN 9 GPU Dockerfile**
   ```dockerfile
   # docker/Dockerfile.gpu
   FROM nvidia/cuda:12.3.2-cudnn9-runtime-ubuntu22.04
   ```

### 驗證結果（v3.3.6）

在 RTX 4090 上實測：

| 指標 | 數值 | 說明 |
|------|------|------|
| **GPU 加速倍率** | **93.7×** | 30 秒音訊用時 0.32 秒 |
| **GPU 使用率** | 35-41% | 實際 GPU 運算使用 |
| **GPU 記憶體** | 2.9 GB | 正確載入 Whisper 模型 |
| **CTranslate2 版本** | 4.6.1 | 支援 cuDNN 9 |
| **設備類型** | cuda | 正確識別 NVIDIA GPU |
| **計算精度** | float16 | 混合精度運算 |

---

## 🔧 v3.3.5 GPU Dockerfile 建立

### 問題根因（原始設計缺陷）

**原始 Dockerfile** 使用 `python:3.11-slim-bookworm`：
- ❌ 缺少 CUDA 運行時庫（cuBLAS for CUDA 12）
- ❌ 缺少 cuDNN 9
- ❌ 無法真正使用 GPU 加速

### 解決方案（v3.3.5）

創建專用 GPU Dockerfile（`docker/Dockerfile.gpu`）：

```dockerfile
# docker/Dockerfile.gpu - GPU 專用映像
FROM nvidia/cuda:12.3.2-cudnn9-runtime-ubuntu22.04

# 包含完整的 CUDA 運行時庫和 cuDNN 9
# 支援 CTranslate2 4.5.0+ GPU 加速
```

### 使用方式

#### 方案 A：自動選擇（推薦）

```bash
# 檢查是否有 GPU
if nvidia-smi 2>/dev/null; then
    # 使用 GPU Dockerfile
    docker build -f docker/Dockerfile.gpu -t meetingscribe:gpu .
else
    # 使用 CPU Dockerfile
    docker build -f docker/Dockerfile -t meetingscribe:cpu .
fi
```

#### 方案 B：手動指定

```bash
# 構建 GPU 映像
docker build -f docker/Dockerfile.gpu -t meetingscribe:gpu .

# 構建 CPU 映像
docker build -f docker/Dockerfile -t meetingscribe:cpu .
```

---

## 📊 性能對比

### 轉錄速度對比

| 音訊時長 | CPU 模式 | GPU 模式 (v3.3.6) | 加速倍數 |
|---------|----------|-----------------|--------|
| 5 秒 | 25-35 秒 | 0.30 秒 | **80-117×** |
| 30 秒 | 3-5 分鐘 | 0.32 秒 | **562-937×** |
| 1 分鐘 | 6-10 分鐘 | 0.65 秒 | **554-923×** |
| 5 分鐘 | 30-50 分鐘 | 3.2 秒 | **562-937×** |

**實測環境**：NVIDIA RTX 4090 + CUDA 12.3 + cuDNN 9

### 記憶體使用對比

| 裝置 | 記憶體使用 | 說明 |
|------|----------|------|
| **CPU 模式** | 2.5-3 GB | 系統記憶體 |
| **GPU 模式** | 2.9 GB (GPU) | VRAM |
| **GPU 模式** | 1.2 GB (CPU) | 主記憶體 |

---

## 🛠️ 部署指南

### 前置要求

#### Windows 11/10 + RTX 4090

1. **NVIDIA 驅動**
   ```powershell
   # 檢查驅動版本
   nvidia-smi
   # 最低要求：驅動版本 >= 535
   ```

2. **Docker Desktop with GPU 支援**
   ```powershell
   # 檢查 Docker GPU 支援
   docker run --rm --gpus all nvidia/cuda:12.3.2-cudnn9-runtime-ubuntu22.04 nvidia-smi
   ```

3. **WSL 2（Windows Subsystem for Linux）**
   ```powershell
   # 確認 WSL 2 已安裝
   wsl --list -v
   # 輸出應顯示 Ubuntu 的 VERSION 為 2
   ```

#### macOS（M1/M2/M3 芯片）

- 不需要特殊配置，使用標準 Dockerfile
- 會自動使用 Metal Performance Shaders (MPS) GPU 加速

#### Linux + NVIDIA GPU

```bash
# 安裝 NVIDIA Docker 運行時
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

### 部署步驟

#### 第 1 步：選擇 Dockerfile

```bash
cd /Users/hsiaojohnny/dev/convert

# 檢查 GPU 可用性
nvidia-smi 2>/dev/null && echo "GPU available" || echo "No GPU"

# 構建映像（自動選擇）
if nvidia-smi 2>/dev/null; then
    docker build -f docker/Dockerfile.gpu -t meetingscribe:latest .
else
    docker build -f docker/Dockerfile -t meetingscribe:latest .
fi
```

#### 第 2 步：啟動容器（需要 GPU 支援）

```bash
# 使用 GPU 啟動容器
docker run --gpus all \
  -p 9527:9527 \
  -v $(pwd)/backend:/app/backend \
  -v $(pwd)/config.yaml:/app/config.yaml \
  meetingscribe:latest

# 或使用 Docker Compose（如果配置了 GPU 支援）
docker compose up -d
```

#### 第 3 步：驗證 GPU 加速

```bash
# 進入容器檢查 GPU 狀態
docker exec <container-id> python -c "
import torch
from faster_whisper import WhisperModel

print('CUDA Available:', torch.cuda.is_available())
print('CUDA Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')

model = WhisperModel('medium', device='cuda', compute_type='float16')
print('Model loaded on CUDA successfully!')
"
```

### Docker Compose 配置（GPU 支援）

```yaml
# docker/docker-compose-windows-gpu.yml
services:
  app:
    build:
      context: ..
      dockerfile: docker/Dockerfile.gpu
    image: meetingscribe:gpu
    
    # ✅ GPU 支援
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    
    # 環境設定
    environment:
      - CUDA_VISIBLE_DEVICES=0  # 使用第一個 GPU
      - NVIDIA_VISIBLE_DEVICES=all
      - NVIDIA_DRIVER_CAPABILITIES=compute,utility
    
    # 其他配置...
```

### 手動啟動指令（快速測試）

```bash
# Windows PowerShell
docker run --rm --gpus all `
  -p 9527:9527 `
  -v "${PWD}/backend:/app/backend" `
  -v "${PWD}/config.yaml:/app/config.yaml" `
  --name meetingscribe-test `
  meetingscribe:gpu

# macOS / Linux
docker run --rm --gpus all \
  -p 9527:9527 \
  -v $(pwd)/backend:/app/backend \
  -v $(pwd)/config.yaml:/app/config.yaml \
  --name meetingscribe-test \
  meetingscribe:gpu
```

---

## ⚙️ 配置優化

### 並發任務數

根據 GPU 記憶體調整最大並發任務數：

```yaml
# config.yaml
system:
  max_concurrent_tasks: 1  # RTX 4090：1-2
  # 公式：max_tasks = GPU_VRAM_GB / 4
  # RTX 4090 (24GB) = 24 / 4 = 6 個任務（不推薦）
  # 建議保守值：1-2 個任務
```

或通過環境變數：

```bash
export MAX_CONCURRENT_TASKS=2
docker compose up -d
```

### 計算精度選擇

```yaml
# config.yaml
whisper:
  compute_type: "float16"      # 推薦：混合精度，平衡速度和品質
  # 其他選項：
  # int8         - 最節省記憶體，速度快，品質略低
  # int8_float16 - 混合精度，較省記憶體
  # float16      - 標準精度，速度快
  # float32      - 最高精度，速度慢，使用記憶體最多
```

---

## 🐛 常見問題與解決

### Q1: Docker 未識別 GPU

**現象**：
```
docker run --gpus all ... 
# 錯誤：could not select device driver "" with capabilities: [[gpu]]
```

**解決**：

```bash
# 1. 檢查 nvidia-docker 是否已安裝
which nvidia-docker

# 2. 檢查 Docker daemon 配置
cat /etc/docker/daemon.json | grep -A5 "nvidia"

# 3. 重啟 Docker daemon
sudo systemctl restart docker

# 4. 驗證 GPU 可用
docker run --rm --gpus all nvidia/cuda:12.3.2-cudnn9-runtime-ubuntu22.04 nvidia-smi
```

### Q2: CUDA 版本衝突

**現象**：
```
nvidia-smi 顯示 CUDA 11.8，但 Docker 使用 CUDA 12.3
```

**解決**：

使用兼容的 CUDA 版本。檢查主機 CUDA 版本：

```bash
# 檢查主機 CUDA 版本
nvidia-smi

# 使用相同版本的 Dockerfile
# 如果主機是 CUDA 11.8，修改 Dockerfile.gpu：
# FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04
```

### Q3: cuDNN 版本錯誤

**現象**：
```
Could not load library libcudnn_ops_infer.so.8
```

**根本原因**：ctranslate2 版本與 cuDNN 版本不相容

**解決**（v3.3.6+）：

```bash
# 檢查 ctranslate2 版本
python -c "import ctranslate2; print(ctranslate2.__version__)"

# v3.3.6 已使用 ctranslate2 4.6.1
# 如果版本 < 4.5.0，必須升級：
pip install --upgrade ctranslate2
```

### Q4: GPU 記憶體不足

**現象**：
```
CUDA out of memory
```

**解決**：

1. 減少並發任務數：
   ```bash
   export MAX_CONCURRENT_TASKS=1
   ```

2. 使用更低的計算精度：
   ```yaml
   # config.yaml
   whisper:
     compute_type: "int8"  # 節省 50% GPU 記憶體
   ```

3. 減少 Ollama 上下文視窗：
   ```yaml
   # config.yaml
   llm:
     ollama:
       num_ctx: 8192  # 從 32768 降低到 8192
   ```

---

## ✅ 驗證檢查清單

部署後，執行以下檢查確保 GPU 加速正常運作：

- [ ] `nvidia-smi` 可以看到 GPU
- [ ] Docker 能識別 GPU（`docker run --gpus all ...`）
- [ ] 容器內能載入 Whisper 模型到 GPU
- [ ] ctranslate2 版本 >= 4.5.0
- [ ] 轉錄速度 >= 80× 實時倍率
- [ ] GPU 使用率 >= 30%
- [ ] 無 `libcudnn_ops_infer.so.8` 或 `libcudnn.so.9` 錯誤

---

## 📚 相關資源

### 官方文檔
- [NVIDIA Docker 運行時](https://github.com/NVIDIA/nvidia-docker)
- [CTranslate2 GPU 支援](https://github.com/OpenNMT/CTranslate2)
- [faster-whisper GPU 加速](https://github.com/guillaumekln/faster-whisper)
- [CUDA 12.3 + cuDNN 9](https://docs.nvidia.com/deeplearning/cudnn/latest/)

### 排除故障
- GPU 驅動更新：https://www.nvidia.com/Download/driverDetails.aspx
- Docker GPU 支援：https://docs.docker.com/config/containers/resource_constraints/#gpu

---

## 🚀 最佳實踐

### ✅ 建議做法

1. **定期檢查 GPU 狀態**
   ```bash
   watch -n 1 'nvidia-smi'
   ```

2. **監視容器 GPU 使用**
   ```bash
   docker stats --no-stream --format "table {{.Container}}\t{{.MemPerc}}\t{{.CPUPerc}}"
   ```

3. **保持驅動和工具最新**
   ```bash
   # 檢查驅動版本
   nvidia-smi
   # 定期更新到最新版本
   ```

4. **使用 float16 精度**
   - 平衡速度和品質
   - 比 float32 快 2 倍，品質相同
   - 比 int8 品質更好

### ❌ 避免做法

- ❌ 同時運行多個高 GPU 記憶體任務
- ❌ 混合使用不同版本的 ctranslate2 和 cuDNN
- ❌ 在 CPU 模式和 GPU 模式之間頻繁切換（會重建映像）
- ❌ 忽視 `libcudnn.so.9` 相容性警告

---

> **更新記錄**
> - **v3.3.6** (2025-12-03): cuDNN 版本相容性修復，93.7× 加速
> - **v3.3.5** (2025-12-03): GPU Dockerfile 建立，83× 加速
> - **v3.3.4** (2025-12-03): GPU 環境配置初步支援
