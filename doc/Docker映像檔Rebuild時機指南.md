# 🐳 Docker 映像檔 Rebuild 時機指南

> **版本**: v2.1（v3.4.0 更新）  
> **適用專案**: MeetingScribe  
> **最後更新**: 2025-01-27
> **⚠️ 重要提示**: 自 v3.4 起，請改用 **[Docker 零重建部署指南](Docker零重建部署指南.md)** 獲得更好的開發體驗

---

## 📋 概述

本指南解答一個常見問題：**「我修改了程式碼，到底需不需要重建 Docker 映像檔？」**

**⚡ v3.4.0 更新重點**：
- 修復 GPU 加速失效問題（動態偵測）
- 實現 VRAM 資源釋放機制
- 重構自訂格式功能
- **以上修改都需要 Rebuild**

> 如果您正在尋求更快的開發體驗，建議直接跳轉到新的 [Docker 零重建部署指南](Docker零重建部署指南.md)，它提供了一套完整的零重建方案，可將開發效率提升 **60-180 倍**。

本指南仍保持更新，用於以下場景：
1. **生產部署環境**（不使用 override.yml）
2. **理解 Docker 基本原理**
3. **Dockerfile 和系統級修改**

---

## 🔥 v3.4.0 需要 Rebuild

本版本修改了以下後端檔案，**必須重建 Docker 映像檔**：

| 修改檔案 | 修改內容 | 影響 |
|----------|---------|------|
| `backend/services/transcription.py` | GPU 動態偵測 + VRAM 釋放 | Whisper 轉錄行為改變 |
| `backend/services/summarization.py` | 自訂格式重構 + Ollama VRAM 釋放 | 摘要生成邏輯改變 |

```bash
# Windows GPU 版本重建命令
docker-compose -f docker/docker-compose-windows-gpu.yml up -d --build

# 其他版本重建命令
docker-compose -f docker/docker-compose.yml up -d --build
```

---

## 🎯 快速判斷表

| 修改類型 | v3.3 及更早 | v3.4 零重建方案 | 說明 |
|----------|------------|---------------|------|
| **Python 程式碼** (backend/*.py) | ❌ 需要 rebuild | ✅ 只需 restart | Volume Mount 實時同步 |
| **前端檔案** (HTML/CSS/JS) | ❌ 需要 rebuild | ✅ 瀏覽器刷新 | 前端即時生效 |
| **config.yaml** | ❌ 需要 rebuild | ✅ 只需 restart | 配置文件動態注入 |
| **requirements.txt** | ✅ 需要 rebuild | ✅ 只需 restart | entrypoint 自動安裝 |
| **.env 環境變數** | ✅ 需要 down+up | ✅ 只需 restart | .env.local 優先級覆蓋 |
| **docker-compose.yml** | ❌ 需要 down+up | ❌ 需要 down+up | 服務配置變更 |
| **Dockerfile** | ✅ 需要 rebuild | ✅ 需要 rebuild | 映像定義變更 |
| **系統依賴** (apt-get) | ✅ 需要 rebuild | ✅ 需要 rebuild | 映像系統級變更 |

---

## 🔧 本專案的 Volume Mount 設定

在 `docker/docker-compose.yml` 中：

```yaml
volumes:
  # 開發模式：掛載本地程式碼，無需重建即可測試
  - ../backend:/app/backend:ro
  - ../frontend:/app/frontend:ro
  - ../config.yaml:/app/config.yaml:ro
```

### 這代表什麼？

| 目錄 | 狀態 | 效果 |
|------|------|------|
| `backend/` | ✅ 已掛載 | Python 程式碼變更只需 restart |
| `frontend/` | ✅ 已掛載 | HTML/CSS/JS 變更只需 restart |
| `config.yaml` | ✅ 已掛載 | 配置變更只需 restart |
| `requirements.txt` | ❌ 未掛載 | 依賴變更需要 rebuild |

---

## 📊 詳細情境說明

### 情境 1：修改 Python 程式碼

```bash
# 例如修改 backend/services/transcription.py

# 因為有 Volume Mount，只需 restart
docker compose -f docker/docker-compose.yml restart
```

### 情境 2：修改 requirements.txt

```bash
# 例如新增 opencc-python-reimplemented 套件

# 必須 rebuild，因為依賴在 build 階段安裝
docker compose -f docker/docker-compose.yml build
docker compose -f docker/docker-compose.yml up -d
```

### 情境 3：修改前端 CSS/JS

```bash
# 例如修改 frontend/css/style.css

# 因為有 Volume Mount，只需 restart
docker compose -f docker/docker-compose.yml restart

# 💡 提示：瀏覽器可能有快取，按 Cmd+Shift+R 強制刷新
```

### 情境 4：修改 Dockerfile

```bash
# 例如新增 apt-get 安裝套件

# 必須 rebuild
docker compose -f docker/docker-compose.yml build --no-cache
docker compose -f docker/docker-compose.yml up -d
```

### 情境 5：修改 .env 環境變數

```bash
# 例如修改 GEMINI_API_KEY

# 需要 down + up（restart 不會重新讀取 env_file）
docker compose -f docker/docker-compose.yml down
docker compose -f docker/docker-compose.yml up -d
```

### 情境 6：修改 docker-compose.yml

```bash
# 例如調整 ports 或新增 volumes

# 需要 down + up
docker compose -f docker/docker-compose.yml down
docker compose -f docker/docker-compose.yml up -d
```

---

## ⚡ 快速指令速查

```bash
# 只重啟（程式碼變更，有 Volume Mount）
docker compose -f docker/docker-compose.yml restart

# 重新讀取配置（.env 或 docker-compose.yml 變更）
docker compose -f docker/docker-compose.yml down && docker compose -f docker/docker-compose.yml up -d

# 重建映像（依賴、Dockerfile、模型變更）
docker compose -f docker/docker-compose.yml build
docker compose -f docker/docker-compose.yml up -d

# 完全重建（清除快取）
docker compose -f docker/docker-compose.yml build --no-cache
docker compose -f docker/docker-compose.yml up -d

# 查看日誌
docker logs meetingscribe-app --tail 50

# 進入容器除錯
docker exec -it meetingscribe-app /bin/bash
```

---

## 🔄 Restart vs Down+Up vs Rebuild

| 指令 | 效果 | 使用時機 |
|------|------|---------|
| `restart` | 重啟容器，保持映像和配置 | Volume Mount 的程式碼變更 |
| `down` + `up` | 銷毀並重建容器，重新讀取配置 | .env、docker-compose.yml 變更 |
| `build` | 重新建構映像 | requirements.txt、Dockerfile 變更 |
| `build --no-cache` | 完全重建，不使用快取 | 依賴問題、映像損壞 |

---

## 🎯 最佳實踐

### 開發階段
1. **啟用 Volume Mount**（預設已啟用）
2. 修改程式碼後只需 `restart`
3. 節省大量重建時間

### 部署階段
1. **移除 Volume Mount**（註解掉 volumes）
2. 每次部署都 `build` 新映像
3. 確保映像是自包含的

### 切換方式

```yaml
# docker-compose.yml

# 開發模式（啟用 Volume Mount）
volumes:
  - ../backend:/app/backend:ro
  - ../frontend:/app/frontend:ro

# 生產模式（註解掉，使用映像內的程式碼）
# volumes:
#   - ../backend:/app/backend:ro
#   - ../frontend:/app/frontend:ro
```

---

## ❓ 常見問題

### Q: 為什麼我改了程式碼但沒有生效？

**A:** 檢查以下幾點：
1. Volume Mount 是否正確設定？
2. 是否執行了 `restart`？
3. 瀏覽器是否有快取？（Cmd+Shift+R 強制刷新）

### Q: 為什麼 rebuild 要這麼久？

**A:** 因為 Whisper 模型 (large-v3) 約 3GB，在 build 階段下載。
- 使用快取可跳過（若 requirements.txt 沒變）
- 使用 `--no-cache` 會重新下載

### Q: 如何確認容器使用的是最新程式碼？

```bash
# 查看容器內的檔案
docker exec meetingscribe-app cat /app/backend/services/transcription.py | head -10

# 對比本地檔案
head -10 backend/services/transcription.py
```

### Q: Volume Mount 有什麼限制？

**A:** 
- 只能覆蓋「已存在」的檔案路徑
- 新增的依賴（requirements.txt）不會自動安裝
- 效能略低於映像內建檔案

---

## 📝 本專案異動檢查清單

在提交前，根據修改的檔案判斷是否需要 rebuild：

- [ ] `backend/*.py` → restart ✅
- [ ] `frontend/*.html/css/js` → restart ✅
- [ ] `config.yaml` → restart ✅
- [ ] `.env` → down + up ✅
- [ ] `docker-compose.yml` → down + up ✅
- [ ] `requirements.txt` → **rebuild** ⚠️
- [ ] `Dockerfile` → **rebuild** ⚠️
- [ ] 變更 Whisper 模型 → **rebuild** ⚠️

---

> 💡 **黃金法則**：如果不確定，先試 `restart`，不行再 `rebuild`。
