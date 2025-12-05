# 🚀 Docker 零重建部署指南 (v3.4.0)

> **版本**: v3.4.0 - 生產級別零重建機制  
> **適用專案**: MeetingScribe  
> **最後更新**: 2025-12-04  
> **狀態**: 🟢 正式發佈  
> **相關承諾**: Docker 官方最佳實踐，Context7 生產級範例

---

## 📖 概述

本指南介紹 MeetingScribe v3.4.0 **零重建部署機制**（Zero-Rebuild Deployment）。此機制採用 Docker 官方推薦的分層式動態部署架構，實現**秒級代碼同步更新**，開發效率提升 **60-180 倍**。

### 💡 核心創新

**從前**（v2.x）：修改任何配置都需要 `rebuild` Docker 映像
```bash
# ❌ 每次修改都要10-30分鐘
docker compose build
docker compose up -d
```

**現在**（v3.0）：無損更新任何配置，只需 `restart`
```bash
# ✅ 秒級響應，無任何停機
docker compose restart
```

---

## 🎯 支援的無重建更新

| 修改項目 | 舊方案 | 新方案 | 快速 |
|---------|--------|--------|------|
| Python 程式碼 (backend/*.py) | rebuild | restart | ✅ |
| 前端檔案 (frontend/*) | rebuild | 瀏覽器刷新 | ✅ |
| config.yaml | rebuild | restart | ✅ |
| requirements.txt | rebuild | restart | ✅ |
| .env 環境變數 | down + up | restart | ✅ |
| docker-compose.yml | down + up | down + up | ⏳ |
| Dockerfile | rebuild | rebuild | ⏳ |

---

## 🔧 原理：分層部署架構

### 層級 1️⃣：映像層（容器基礎）
```dockerfile
# Dockerfile 中預先裝好所有依賴和模型
# ✅ 包含：Python、FFmpeg、Whisper 模型
# ❌ 不包含：應用程式碼、配置檔案
```

### 層級 2️⃣：程式碼層（動態注入）
```yaml
volumes:
  - ../backend:/app/backend:ro        # 即時同步後端
  - ../frontend:/app/frontend:ro      # 即時同步前端
  - ../config.yaml:/app/config.yaml:ro  # 即時同步配置
```

### 層級 3️⃣：環境層（運行時覆蓋）
```yaml
env_file:
  - ../.env           # 全局配置
  - ../.env.local     # 本地覆蓋（優先級更高）
```

### 層級 4️⃣：依賴層（動態安裝）
```bash
# 容器啟動時自動執行
pip install -r requirements.txt  # 自動檢測並安裝新依賴
```

---

## 📚 快速開始

### 第一次部署

```bash
# 1. 複製環境變數檔案
cp .env.local.example .env.local

# 2. 編輯本地配置（可選）
nano .env.local
# 修改 OLLAMA_BASE_URL、MAX_CONCURRENT_TASKS 等

# 3. 啟動服務（首次會 build）
cd docker
docker compose up -d

# 4. 檢查服務狀態
docker compose logs -f
```

### 開發中修改程式碼

#### 場景 1️⃣：修改 backend/*.py

```bash
# ✅ 只需重啟容器（秒級完成）
docker compose restart

# 驗證修改已生效
docker exec meetingscribe-app cat /app/backend/services/transcription.py | head -5
```

#### 場景 2️⃣：修改 frontend/*

```bash
# ✅ 修改 HTML/CSS/JS 後直接刷新瀏覽器
# 無需任何 Docker 操作

# 若瀏覽器有快取，按 Ctrl+Shift+R 強制刷新
```

#### 場景 3️⃣：修改 config.yaml

```bash
# ✅ 只需重啟容器
docker compose restart

# 驗證修改已生效
docker exec meetingscribe-app cat /app/config.yaml | head -10
```

#### 場景 4️⃣：修改 requirements.txt

```bash
# ✅ 新增依賴後只需重啟
# 容器啟動時會自動 pip install

docker compose restart

# 驗證新依賴已安裝
docker exec meetingscribe-app pip list | grep new-package-name
```

#### 場景 5️⃣：修改 .env 環境變數

```bash
# ✅ 編輯 .env.local
nano .env.local
# 例如修改 MAX_CONCURRENT_TASKS=2

# ✅ 重啟容器使新環境變數生效
docker compose restart

# 驗證環境變數已更新
docker exec meetingscribe-app env | grep MAX_CONCURRENT_TASKS
```

---

## 🎯 零重建工作流

### 工作流程圖

```
開發者修改程式碼
    ↓
修改類型判斷？
    ├─→ backend/*.py, frontend/*, config.yaml, requirements.txt, .env
    │   ↓
    │  docker compose restart  (10秒)
    │   ↓
    │  驗證生效 ✅
    │
    └─→ docker-compose.yml, Dockerfile
        ↓
       docker compose down && docker compose up  (2分鐘)
        ↓
       驗證生效 ✅
```

### 檢查清單

在提交程式碼前，檢查修改類型：

```bash
# ✅ 快速重啟（< 10秒）
- [ ] backend/*.py 修改
- [ ] frontend/*.html/css/js 修改
- [ ] config.yaml 修改
- [ ] requirements.txt 修改
- [ ] .env 或 .env.local 修改

# ⏳ 標準重啟（~ 2分鐘）
- [ ] docker-compose.yml 修改
- [ ] docker-compose.override.yml 修改

# 🔨 完整重建（10-30分鐘）
- [ ] Dockerfile 修改
- [ ] 系統依賴變更（apt-get packages）
```

---

## 🛠️ 進階配置

### 自訂環境變數

編輯 `.env.local` 以覆蓋全局設定：

```bash
# .env.local

# 增加並發任務數（需要足夠的 GPU 記憶體）
MAX_CONCURRENT_TASKS=2

# 增加檔案上傳限制
MAX_FILE_SIZE_MB=500

# 使用自訂 Ollama 模型
LOCAL_LLM_MODEL=llama2:13b-chat

# 啟用詳細日誌（調試用）
LOG_LEVEL=DEBUG

# 本地開發特殊設定
DEVELOPMENT_MODE=true
UVICORN_RELOAD=true
```

### 多開發者隔離

每個開發者可擁有獨立的 `.env.local`，不影響他人：

```bash
# 開發者 A
.env.local
├─ OLLAMA_BASE_URL=http://192.168.1.100:11434
└─ MAX_CONCURRENT_TASKS=1

# 開發者 B
.env.local
├─ OLLAMA_BASE_URL=http://192.168.1.101:11434
└─ MAX_CONCURRENT_TASKS=2
```

（.env.local 已在 .gitignore 中，不會提交到 Git）

---

## 📊 性能對比

### 重建時間對比

| 操作 | v3.3 時間 | v3.4 時間 | 加速倍數 |
|------|----------|----------|--------|
| 修改 backend/*.py | 10-30 分鐘 | 10 秒 | **60-180×** |
| 修改 frontend/* | 10-30 分鐘 | < 1 秒 | **600+×** |
| 修改 config.yaml | 10-30 分鐘 | 10 秒 | **60-180×** |
| 修改 .env | 2 分鐘 | 10 秒 | **12×** |

### 開發效率提升

```
v3.3 一天開發流程：
1. 修改代碼 (5分鐘)
2. docker build (20分鐘) ❌
3. docker up (5分鐘)
4. 測試 (10分鐘)
━━━━━━━━━━━━━━━━
總計：40分鐘/迴圈 × 4 迴圈 = 160分鐘（生產代碼）

v3.4 一天開發流程：
1. 修改代碼 (5分鐘)
2. docker restart (10秒) ✅
3. 測試 (10分鐘)
━━━━━━━━━━━━━━━━
總計：15分鐘/迴圈 × 4 迴圈 = 60分鐘（生產代碼）

效率提升：160 → 60 分鐘 = 節省 100分鐘/天（62.5%）
```

---

## ⚠️ 常見問題

### Q1: 修改 requirements.txt 後仍然出錯？

**A:** 檢查依賴安裝狀態：

```bash
# 查看容器日誌
docker compose logs -f

# 手動驗證依賴已安裝
docker exec meetingscribe-app pip list | grep package-name

# 若未安裝，手動安裝
docker exec meetingscribe-app pip install -r requirements.txt
```

### Q2: 修改 config.yaml 後沒有生效？

**A:** 確認有重啟容器且正確的掛載路徑：

```bash
# 驗證 config.yaml 已掛載
docker exec meetingscribe-app ls -la /app/config.yaml

# 對比本地和容器中的檔案
diff -u config.yaml <(docker exec meetingscribe-app cat /app/config.yaml)

# 若不同，重啟容器
docker compose restart
```

### Q3: .env.local 優先級？

**A:** 優先級順序（高→低）：

1. `.env.local` （最高）
2. `.env` （默認）
3. docker-compose.yml 中的 environment （最低）

```yaml
# docker-compose.yml
environment:
  - LOG_LEVEL=INFO          # 被 .env 覆蓋

# .env
LOG_LEVEL=DEBUG             # 被 .env.local 覆蓋

# .env.local
LOG_LEVEL=TRACE             # 最終使用值 ✅
```

### Q4: 如何回到特定版本？

**A:** 清空所有修改並重新部署：

```bash
# 方案 A：刪除 override 檔案（完全按映像運行）
rm docker/docker-compose.override.yml
docker compose down -v
docker compose up -d

# 方案 B：重新建立 override 檔案
docker compose down -v
docker compose up -d
```

---

## 🔒 安全性

### 敏感資訊保護

```bash
# ✅ .env.local 不會上傳 Git
cat .gitignore | grep ".env.local"
# 輸出：.env.local

# ✅ API Keys 安全存儲
# .env.local 中的 GEMINI_API_KEY 不會被提交
```

### 權限隔離

```bash
# 容器以非 root 用戶執行
docker exec meetingscribe-app whoami
# 輸出：appuser

# Volume 以 read-only 模式掛載（程式碼層）
docker inspect meetingscribe-app | grep '"Mode"' | head -3
# 輸出：ro （read-only）
```

---

## 📋 故障排除清單

| 問題 | 診斷 | 解決 |
|------|------|------|
| 修改後沒有生效 | `docker compose logs -f` | `docker compose restart` |
| 依賴衝突 | `docker exec app pip list` | `docker compose down -v && up` |
| 配置錯誤 | `docker exec app cat /app/config.yaml` | 編輯本地檔案後 restart |
| 無法連接 Ollama | `docker exec app curl http://host.docker.internal:11434` | 檢查主機 Ollama 狀態 |
| 前端快取問題 | 瀏覽器 DevTools → Network | 按 Ctrl+Shift+R 強制刷新 |

---

## 🚀 最佳實踐

### ✅ 建議做法

```bash
# 1. 使用 .env.local 存儲本地配置
cp .env.local.example .env.local

# 2. 每次修改後驗證
docker compose logs -f

# 3. 定期查看依賴變更
git diff requirements.txt

# 4. 提交前檢查 .env.local 未被提交
git status | grep ".env.local"  # 應該沒有輸出

# 5. 使用 watch 命令監視日誌
watch -n 1 'docker compose logs | tail -20'
```

### ❌ 避免做法

```bash
# ❌ 直接編輯 .env（會被提交到 Git）
# 改用 .env.local

# ❌ 修改容器內的檔案（重啟後丟失）
docker exec meetingscribe-app nano /app/config.yaml
# 應改用本地 config.yaml 文件

# ❌ 忘記 restart（新設定未生效）
# 修改任何配置後務必執行 docker compose restart

# ❌ 混淆 override.yml 和 docker-compose.yml
# docker-compose.override.yml 是自動載入的開發配置
# 不要手動指定 -f docker-compose.override.yml
```

---

## 📞 支援

### 快速指令

```bash
# 重啟服務（最常用）
docker compose restart

# 查看日誌
docker compose logs -f

# 進入容器調試
docker exec -it meetingscribe-app bash

# 檢查服務狀態
docker compose ps

# 完整重建
docker compose down -v && docker compose up -d
```

### 更多資源

- 📖 Docker 官方最佳實踐：https://docs.docker.com/develop/dev-best-practices/
- 📖 Docker Compose 文件參考：https://docs.docker.com/compose/compose-file/
- 📖 多階段構建指南：https://docs.docker.com/build/building/multi-stage/

---

> 💡 **黃金法則**：任何時候不確定，執行 `docker compose restart` 試試看！
