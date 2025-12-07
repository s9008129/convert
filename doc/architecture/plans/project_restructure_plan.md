# 🏗️ 專案架構重整計劃

> **文件版本**：v1.0  
> **建立日期**：2025-12-07  
> **分析基準**：v3.5.4 (Stable)  
> **目標**：建立清晰、可維護、跨平台友善的專案架構

---

## 📋 目錄

1. [問題分析](#問題分析)
2. [現有架構盤點](#現有架構盤點)
3. [目標架構設計](#目標架構設計)
4. [重整計劃](#重整計劃)
5. [執行時程](#執行時程)
6. [風險評估](#風險評估)

---

## 🔍 問題分析

### 第一性原理分析

**核心問題**：專案經過多次迭代，累積了大量檔案，造成：

1. **檔案分散混亂**
   - 配置檔散落多處（根目錄、config/、docker/）
   - 腳本檔案平台混雜（.sh/.bat/.ps1）
   - 文件組織缺乏系統性

2. **平台版本混淆**
   - macOS 和 Windows 配置分散
   - Docker 相關檔案命名不一致
   - 難以判斷哪些檔案適用哪個平台

3. **冗餘檔案累積**
   - 舊版本配置檔未清理
   - 測試和驗證報告過多
   - 暫存目錄未管理

### 量化問題

```
目前專案結構：
├── 根目錄配置檔：5+ 個
├── docker/ 目錄：5 個 Dockerfile/compose
├── scripts/ 目錄：12+ 個腳本
├── doc/ 目錄：50+ 個文件
├── config/ 目錄：10+ 個配置
└── 估計冗餘率：30%
```

---

## 📁 現有架構盤點

### 根目錄檔案

| 檔案 | 類型 | 用途 | 建議 |
|------|------|------|------|
| `config.yaml` | 配置 | Windows 主配置 | 保留 |
| `config.macos.yaml` | 配置 | macOS 配置 | 移至 config/ |
| `.env.example` | 範本 | 環境變數範例 | 保留 |
| `requirements.txt` | 依賴 | Python 依賴 | 保留 |
| `environment.yml` | 依賴 | Conda 環境 | 保留或整合 |
| `main.py` | 進入點 | 應用程式入口 | 保留 |
| `start_service.sh` | 腳本 | macOS 啟動 | 移至 scripts/mac/ |

### scripts/ 目錄

| 檔案 | 平台 | 用途 | 建議 |
|------|------|------|------|
| `deploy.bat` | Windows | 部署工具 | 移至 scripts/windows/ |
| `start.bat` | Windows | 快速啟動 | 移至 scripts/windows/ |
| `stop.bat` | Windows | 快速停止 | 移至 scripts/windows/ |
| `health-check.bat` | Windows | 健康檢查 | 移至 scripts/windows/ |
| `start-mac-native.sh` | macOS | 原生啟動 | 移至 scripts/mac/ |
| `restart-mac-native.sh` | macOS | 原生重啟 | 移至 scripts/mac/ |
| `stop-mac-native.sh` | macOS | 原生停止 | 移至 scripts/mac/ |
| `service_manager.sh` | 通用 | 服務管理 | 移至 scripts/common/ |
| `cleanup_docker.sh` | Docker | 清理工具 | 移至 scripts/docker/ |

### docker/ 目錄

| 檔案 | 用途 | 建議 |
|------|------|------|
| `Dockerfile` | 通用 CPU 版 | 保留 |
| `Dockerfile.gpu` | GPU 加速版 | 保留 |
| `docker-compose.yml` | 預設配置 | 保留 |
| `docker-compose-windows-gpu.yml` | Windows GPU | 保留 |
| `docker-compose.override.yml` | 覆蓋配置 | 評估是否需要 |

### doc/ 目錄

**問題**：文件過多、組織不清、部分過時

建議分類：
- `guides/` - 使用者指南
- `reports/` - 技術報告
- `evidence/` - 驗證證據
- `analysis/` - 分析文件
- `archive/` - 歷史文件

---

## 🎯 目標架構設計

### 新架構圖

```
meetingscribe/
│
├── 📁 backend/              # 後端程式碼（不變）
│   ├── api/
│   ├── core/
│   ├── models/
│   ├── services/
│   └── middleware/
│
├── 📁 frontend/             # 前端程式碼（不變）
│   ├── css/
│   ├── js/
│   └── index.html
│
├── 📁 config/               # 所有配置檔案
│   ├── base/                # 基礎配置
│   │   ├── llm.yaml
│   │   ├── whisper.yaml
│   │   └── paths.yaml
│   ├── platform/            # 平台配置
│   │   ├── windows.yaml
│   │   └── macos.yaml
│   └── profiles/            # 環境配置
│       ├── development.yaml
│       └── production.yaml
│
├── 📁 docker/               # Docker 相關
│   ├── Dockerfile
│   ├── Dockerfile.gpu
│   ├── compose/
│   │   ├── base.yml
│   │   ├── windows-gpu.yml
│   │   └── mac.yml
│   └── README.md
│
├── 📁 scripts/              # 腳本分類
│   ├── windows/             # Windows 專用
│   │   ├── deploy.bat
│   │   ├── start.bat
│   │   └── health-check.bat
│   ├── mac/                 # macOS 專用
│   │   ├── start.sh
│   │   ├── stop.sh
│   │   └── health-check.sh
│   ├── docker/              # Docker 相關
│   │   └── cleanup.sh
│   ├── hooks/               # Git hooks
│   │   └── pre-push
│   └── common/              # 通用腳本
│       └── service_manager.sh
│
├── 📁 doc/                  # 文件（精簡後）
│   ├── guides/              # 使用者指南
│   │   ├── quick-start/
│   │   ├── deployment/
│   │   ├── upgrade/
│   │   └── git/
│   ├── reports/             # 技術報告
│   ├── architecture/        # 架構文件
│   └── archive/             # 歷史文件
│
├── 📁 data/                 # 資料目錄
│   ├── uploads/
│   ├── outputs/
│   ├── cache/
│   └── templates/
│
├── 📁 tests/                # 測試
│
├── 📄 config.yaml           # 預設配置（Windows）
├── 📄 .env.example          # 環境變數範例
├── 📄 requirements.txt      # Python 依賴
├── 📄 README.md             # 專案說明
├── 📄 CHANGELOG.md          # 變更日誌
└── 📄 VERSION               # 版本號
```

### 設計原則

1. **平台隔離**：不同平台的腳本和配置分開存放
2. **職責單一**：每個目錄只負責一件事
3. **層次清晰**：最多 3 層目錄深度
4. **命名一致**：統一使用小寫 + 底線命名

---

## 📋 重整計劃

### 階段 1：腳本整理（低風險）

**目標**：將腳本依平台分類

**操作**：
```bash
# 建立平台目錄
mkdir -p scripts/{windows,mac,docker,common}

# 移動 Windows 腳本
mv scripts/*.bat scripts/windows/
mv scripts/*.ps1 scripts/windows/

# 移動 macOS 腳本
mv scripts/*-mac*.sh scripts/mac/
mv start_service.sh scripts/mac/

# 移動 Docker 腳本
mv scripts/*docker*.sh scripts/docker/
```

**驗證**：
- [ ] Windows 腳本可正常執行
- [ ] macOS 腳本可正常執行
- [ ] Docker 腳本可正常執行

### 階段 2：配置檔整理（中風險）

**目標**：整合配置檔到 config/ 目錄

**操作**：
1. 將 `config.macos.yaml` 移至 `config/platform/macos.yaml`
2. 更新程式碼中的配置載入路徑
3. 測試配置載入功能

**驗證**：
- [ ] macOS 配置正常載入
- [ ] Windows 配置正常載入
- [ ] 環境變數覆蓋正常

### 階段 3：文件整理（低風險）

**目標**：精簡並分類文件

**操作**：
1. 移動過時文件到 `doc/archive/`
2. 整合重複內容的指南
3. 更新文件索引 `doc/README.md`

**驗證**：
- [ ] 文件連結有效
- [ ] 分類合理

### 階段 4：Docker 整理（中風險）

**目標**：整理 Docker 配置

**操作**：
1. 建立 `docker/compose/` 目錄
2. 移動 compose 檔案
3. 更新部署腳本中的路徑

**驗證**：
- [ ] Docker build 正常
- [ ] Docker compose up 正常
- [ ] GPU 功能正常

---

## 📅 執行時程

| 階段 | 內容 | 預計時間 | 優先級 |
|------|------|---------|-------|
| 1 | 腳本整理 | 2 小時 | 高 |
| 2 | 配置檔整理 | 4 小時 | 中 |
| 3 | 文件整理 | 3 小時 | 低 |
| 4 | Docker 整理 | 2 小時 | 中 |
| - | **總計** | **11 小時** | - |

**建議執行順序**：1 → 3 → 2 → 4

---

## ⚠️ 風險評估

### 高風險項目

| 項目 | 風險 | 緩解措施 |
|------|------|---------|
| 配置路徑變更 | 程式碼載入失敗 | 建立向後相容層 |
| Docker 路徑變更 | 部署腳本失效 | 完整測試後再變更 |

### 中風險項目

| 項目 | 風險 | 緩解措施 |
|------|------|---------|
| 腳本路徑變更 | 使用者操作習慣改變 | 在舊位置放置提示腳本 |
| 文件移動 | 連結失效 | 建立重定向或更新連結 |

### 低風險項目

| 項目 | 風險 | 緩解措施 |
|------|------|---------|
| 歷史文件歸檔 | 無 | 保留在 archive/ |
| 目錄建立 | 無 | 無 |

---

## 📝 執行前檢查清單

- [ ] 確認在 develop 分支上執行
- [ ] 備份目前專案
- [ ] 確認沒有未提交的變更
- [ ] 準備好測試環境（Windows + macOS）

---

## 📌 版本歷史

| 日期 | 版本 | 說明 |
|------|------|------|
| 2025-12-07 | v1.0 | 初版架構重整計劃 |

---

> **注意**：此計劃應在 develop 分支上執行，完成測試後再合併到 main。  
> 執行過程中如遇問題，請及時記錄並調整計劃。
