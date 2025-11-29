# 🍎 MeetingScribe - macOS Docker 部署指南

> **版本**: v2.1.3  
> **適用對象**: 非技術人員  
> **預計時間**: 首次部署約 15-30 分鐘  
> **最後更新**: 2025-11-29

---

## 📑 目錄

1. [前言：這份指南能幫助您什麼？](#前言這份指南能幫助您什麼)
2. [部署前準備](#部署前準備)
3. [第一步：安裝 Docker Desktop](#第一步安裝-docker-desktop)
4. [第二步：安裝 Ollama（本地 AI 模型）](#第二步安裝-ollama本地-ai-模型)
5. [第三步：啟動 MeetingScribe](#第三步啟動-meetingscribe)
6. [開始使用](#開始使用)
7. [常見問題解答](#常見問題解答)
8. [進階設定](#進階設定)

---

## 前言：這份指南能幫助您什麼？

### 🎯 我們的目標

讓您在 Mac 電腦上，**不需要任何程式設計知識**，就能夠：

```
📁 會議錄音檔 → 🤖 自動處理 → 📝 完整會議記錄
```

### 💡 您會得到什麼？

| 功能 | 說明 |
|------|------|
| **語音轉文字** | 自動將會議錄音轉換為逐字稿 |
| **智能摘要** | AI 自動整理出會議重點、決議事項、待辦事項 |
| **隱私保護** | 可選擇完全離線處理，資料不會上傳到任何伺服器 |
| **簡單操作** | 只需要拖放檔案，其他全部自動完成 |

### 🖥️ macOS 特別說明

這份指南專為 **macOS** 設計，支援：

- **Intel Mac** (2020 年前的 Mac)
- **Apple Silicon Mac** (M1/M2/M3/M4 晶片)

> **Apple Silicon (M系列晶片) 的優勢**：  
> 如果您使用的是 M1/M2/M3/M4 晶片的 Mac，系統會自動利用 Apple 的 MPS (Metal Performance Shaders) 加速 AI 運算，處理速度會更快！

---

## 部署前準備

### 📋 檢查清單

在開始之前，請確認您具備以下條件：

| 項目 | 最低需求 | 建議配置 |
|------|---------|---------|
| **macOS 版本** | macOS 12.3 (Monterey) 以上 | macOS 14 (Sonoma) 以上 |
| **記憶體 (RAM)** | 8 GB | 16 GB 以上 |
| **儲存空間** | 20 GB 可用空間 | 30 GB 以上 |
| **網路** | 首次安裝需要網路 | 首次安裝需要穩定網路 |

### 🔍 如何檢查您的 Mac 規格？

1. 點擊螢幕左上角的 **蘋果圖示** 
2. 選擇 **「關於這台 Mac」**
3. 您會看到：
   - **晶片**：顯示 M1/M2/M3 或 Intel
   - **記憶體**：顯示 RAM 大小
   - **macOS**：顯示版本號

---

## 第一步：安裝 Docker Desktop

### 什麼是 Docker？

簡單來說，Docker 就像是一個「虛擬電腦」，讓我們的程式可以在一個獨立的環境中運行，不會影響您 Mac 上的其他軟體。

### 📥 下載與安裝

1. **開啟瀏覽器**，前往 Docker 官網：
   
   👉 [https://www.docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop)

2. **點擊下載按鈕**
   - 如果您是 **Apple Silicon Mac** (M1/M2/M3/M4)，選擇 **「Mac with Apple chip」**
   - 如果您是 **Intel Mac**，選擇 **「Mac with Intel chip」**

3. **安裝 Docker Desktop**
   - 下載完成後，打開 `Docker.dmg` 檔案
   - 將 Docker 圖示拖到「應用程式」資料夾
   - 從「應用程式」中啟動 Docker

4. **首次啟動設定**
   - Docker 會要求您輸入電腦密碼以完成安裝
   - 等待 Docker 啟動（狀態列會出現鯨魚圖示 🐳）

### ✅ 驗證安裝

打開 **終端機**（在「應用程式」→「工具程式」中），輸入：

```bash
docker --version
```

如果看到類似 `Docker version 24.x.x` 的訊息，表示安裝成功！

---

## 第二步：安裝 Ollama（本地 AI 模型）

### 什麼是 Ollama？

Ollama 是一個讓您在自己電腦上運行 AI 模型的工具。有了它，您的會議內容可以完全在本機處理，**不需要上傳到雲端**。

### 📥 下載與安裝

1. **開啟瀏覽器**，前往 Ollama 官網：
   
   👉 [https://ollama.ai](https://ollama.ai)

2. **點擊「Download」下載**
   - 選擇 macOS 版本
   - 下載完成後打開安裝檔

3. **安裝 Ollama**
   - 將 Ollama 拖到「應用程式」資料夾
   - 從「應用程式」中啟動 Ollama
   - Ollama 會在背景運行（狀態列會出現 Ollama 圖示）

### 📦 下載 AI 模型

Ollama 安裝完成後，我們需要下載會議摘要使用的 AI 模型。

打開 **終端機**，輸入以下指令：

```bash
ollama pull gemma3:12b
```

> ⏳ **請耐心等待**：這個模型大約 8GB，下載時間視您的網路速度而定（可能需要 10-30 分鐘）

### ✅ 驗證安裝

下載完成後，輸入以下指令確認模型已安裝：

```bash
ollama list
```

您應該會看到 `gemma3:12b` 出現在列表中。

---

## 第三步：啟動 MeetingScribe

### 📂 準備專案檔案

確保您已經有 MeetingScribe 的專案資料夾。如果還沒有：

```bash
cd ~/dev/convert
```

### 🚀 一鍵啟動

我們提供了簡單的啟動腳本，讓您輕鬆啟動服務。

#### 方法一：使用腳本啟動（推薦）

1. 打開 **終端機**
2. 切換到專案目錄：
   ```bash
   cd ~/dev/convert
   ```
3. 執行啟動腳本：
   ```bash
   ./scripts/start-mac.sh
   ```

#### 方法二：使用 Docker Compose 手動啟動

1. 打開 **終端機**
2. 切換到專案目錄：
   ```bash
   cd ~/dev/convert
   ```
3. 建構並啟動服務：
   ```bash
   docker compose -f docker/docker-compose-mac.yml up -d --build
   ```

### ⏳ 首次啟動說明

首次啟動會需要較長時間，因為系統需要：

1. **下載基礎映像** (~2GB)
2. **安裝 Python 套件** (~1GB)
3. **下載 Whisper 語音模型** (~3GB)

> 💡 **提示**：這些只需要下載一次，之後啟動會非常快速。

### ✅ 確認服務已啟動

等待約 2-3 分鐘後，執行：

```bash
docker ps
```

您應該會看到 `meetingscribe-app` 正在運行。

或者，直接開啟瀏覽器訪問：

👉 **http://localhost:9527**

如果看到 MeetingScribe 的網頁介面，恭喜您，安裝成功！

---

## 開始使用

### 🎉 開啟 MeetingScribe

1. 打開瀏覽器（Safari、Chrome 等）
2. 在網址列輸入：**http://localhost:9527**
3. 您會看到一個簡潔的上傳介面

### 📤 上傳會議錄音

1. **選擇處理模式**
   - **🔒 本地模式**：完全離線處理，適合機密會議
   - **☁️ 雲端模式**：使用 Google Gemini，品質較高（需設定 API Key）

2. **上傳檔案**
   - 直接將錄音檔拖放到上傳區域
   - 或點擊選擇檔案
   - 支援格式：MP3, MP4, WAV, M4A, MKV 等

3. **等待處理**
   - 系統會顯示即時處理進度
   - 包含：上傳 → 轉錄 → 生成摘要

4. **下載結果**
   - 處理完成後，您可以：
   - 直接在網頁上檢視會議記錄
   - 複製文字到剪貼簿
   - 下載 Markdown 檔案

### 💡 使用技巧

- **檔案大小**：建議單檔不超過 100MB
- **音訊品質**：錄音品質越好，轉錄效果越準確
- **會議語言**：系統自動偵測語言，支援中文、英文等多種語言

---

## 常見問題解答

### ❓ Q1: Docker Desktop 無法啟動？

**解決方案**：

1. 確認您的 macOS 版本是 12.3 以上
2. 重新啟動電腦後再試
3. 如果問題持續，嘗試重新安裝 Docker Desktop

### ❓ Q2: 服務啟動後無法訪問 http://localhost:9527？

**解決方案**：

1. 確認 Docker 正在運行（狀態列有鯨魚圖示）
2. 執行 `docker ps` 確認容器狀態
3. 如果容器未運行，執行：
   ```bash
   docker compose -f docker/docker-compose-mac.yml logs
   ```
   查看錯誤訊息

### ❓ Q3: 本地模式無法使用？

**可能原因**：Ollama 服務未啟動

**解決方案**：

1. 確認 Ollama 正在運行（狀態列有圖示）
2. 在終端機執行 `ollama list` 確認模型已下載
3. 如果沒有模型，執行 `ollama pull gemma3:12b`

### ❓ Q4: 處理速度很慢？

**可能原因**：系統資源不足或未使用 GPU 加速

**解決方案**：

1. 關閉其他佔用大量資源的應用程式
2. 如果您使用 Intel Mac，處理速度會較 Apple Silicon 慢，這是正常的
3. 確認 Docker Desktop 有分配足夠的資源（在 Docker 設定中調整）

### ❓ Q5: 如何停止服務？

在終端機執行：

```bash
cd ~/dev/convert
docker compose -f docker/docker-compose-mac.yml down
```

### ❓ Q6: 如何更新到最新版本？

```bash
cd ~/dev/convert
git pull
docker compose -f docker/docker-compose-mac.yml down
docker compose -f docker/docker-compose-mac.yml up -d --build
```

---

## 進階設定

### 🔑 設定 Gemini API Key（雲端模式）

如果您想使用雲端模式獲得更高品質的摘要：

1. **取得 API Key**
   - 前往 [Google AI Studio](https://makersuite.google.com/app/apikey)
   - 登入您的 Google 帳號
   - 點擊「Create API Key」

2. **設定環境變數**
   
   在專案根目錄建立 `.env` 檔案：
   
   ```bash
   cd ~/dev/convert
   echo "GEMINI_API_KEY=您的API金鑰" > .env
   ```

3. **重啟服務**
   
   ```bash
   docker compose -f docker/docker-compose-mac.yml restart
   ```

### ⚙️ Docker 資源設定

如果處理速度不理想，可以增加 Docker 的資源分配：

1. 點擊狀態列的 Docker 圖示
2. 選擇 **Settings** (設定)
3. 選擇 **Resources** (資源)
4. 調整：
   - **CPUs**: 建議設為可用核心數的一半以上
   - **Memory**: 建議設為 8GB 以上
5. 點擊 **Apply & Restart**

### 📁 資料儲存位置

- **上傳的檔案**：`~/dev/convert/data/uploads/`
- **處理結果**：`~/dev/convert/data/outputs/`
- **快取**：`~/dev/convert/data/cache/`

---

## 🆘 需要幫助？

如果您遇到任何問題，可以：

1. 查看 [常見問題解答](#常見問題解答)
2. 檢查服務日誌：
   ```bash
   docker compose -f docker/docker-compose-mac.yml logs -f
   ```
3. 聯繫技術支援

---

## 📋 快速指令參考

| 動作 | 指令 |
|------|------|
| 啟動服務 | `docker compose -f docker/docker-compose-mac.yml up -d` |
| 停止服務 | `docker compose -f docker/docker-compose-mac.yml down` |
| 查看狀態 | `docker ps` |
| 查看日誌 | `docker compose -f docker/docker-compose-mac.yml logs -f` |
| 重新建構 | `docker compose -f docker/docker-compose-mac.yml up -d --build` |
| 健康檢查 | `curl http://localhost:9527/api/health` |

---

> 🎉 **恭喜您完成安裝！**  
> 現在您可以開始使用 MeetingScribe 將會議錄音轉換為結構化會議記錄了。
