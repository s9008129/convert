# MeetingScribe 文件中心

> **版本**：v3.5.5  
> **最後更新**：2025-12-18  
> **維護者**：MeetingScribe 開發團隊

---

## 📚 文件導航

### 🚀 快速開始（5 分鐘上手）

| 文件 | 適合對象 | 說明 |
|------|---------|------|
| [快速開始指南](guides/quick_start_guide.md) | 所有使用者 | 3 步驟快速部署 |
| [Mac 快速部署](guides/mac_native_deployment_guide.md) | macOS 使用者 | 原生服務部署（推薦） |
| [Windows 快速開始](guides/windows_quick_start_guide.md) | Windows 使用者 | 批次檔一鍵部署 |

### 📖 完整部署指南

| 平台 | 文件 | 特色 |
|------|------|------|
| **macOS** | [macOS 原生部署](guides/mac_native_deployment_guide.md) | Apple MPS 加速、MLX-Whisper |
| **Windows** | [Windows 完整部署](guides/windows_deployment_guide.md) | NVIDIA GPU 加速、Docker |
| **Linux** | [Docker 部署經驗](guides/docker_deployment_guide.md) | 跨平台容器化 |

### 🔧 管理與維護

| 文件 | 用途 |
|------|------|
| [管理者操作指南](guides/administrator_guide.md) | 系統架構、配置、維護 |
| [GPU 加速指南](guides/gpu_acceleration_guide.md) | CUDA、MPS 加速設定 |
| [Docker 重建時機](guides/docker_rebuild_guide.md) | 何時需要重建映像 |

### 📊 技術文件與報告

| 類型 | 目錄 | 說明 |
|------|------|------|
| **驗證報告** | [evidence/](./evidence/) | 測試驗證證據 |
| **技術報告** | [reports/](./reports/) | 技術分析與修復報告 |
| **系統分析** | [analysis/](./analysis/) | 架構設計與系統分析 |
| **版本報告** | 根目錄 | v{version}_系統修復驗證報告.md |

---

## 📁 目錄結構說明

```
doc/
├── README.md                      # 📄 文件導航中心（本文件）
├── 系統改善計劃.md                 # 🎯 系統改善與重構計畫
├── implement_and_tasks.md          # 📋 實施計畫與任務清單
├── v3.5.5_系統修復驗證報告.md      # ✅ 最新版本驗證報告
│
├── guides/                         # 📖 使用指南
│   ├── quick_start_guide.md       # 快速開始
│   ├── mac_native_deployment_guide.md  # Mac 原生部署
│   ├── mac_whisper_guide.md       # Mac Whisper 設定
│   ├── windows_deployment_guide.md     # Windows 完整部署
│   ├── windows_quick_start_guide.md    # Windows 快速開始
│   ├── docker_deployment_guide.md      # Docker 部署
│   ├── gpu_acceleration_guide.md       # GPU 加速
│   ├── administrator_guide.md          # 管理者指南
│   └── upgrade/                    # 升級指南
│       └── windows_v3.5.4_upgrade_guide.md
│
├── evidence/                       # 🧪 驗證證據
│   ├── queue_logic_fix_evidence_v3.5.1.md
│   ├── mac_migration_evidence_v3.5.0.md
│   ├── task_completion_evidence_v3.5.0.md
│   ├── windows_rtx4090_migration_evidence.md
│   └── ... (更多驗證報告)
│
├── reports/                        # 📊 技術報告
│   ├── code_review_report.md
│   ├── fix_summary_report.md
│   ├── migration_verification_report.md
│   └── llm_quality_comparison_report.md
│
├── analysis/                       # 🔬 系統分析
│   ├── system_development_analysis.md
│   ├── windows_deployment_analysis.md
│   └── windows_deployment_solution.md
│
├── architecture/                   # 🏗️ 架構設計
│   └── plans/
│       └── project_restructure_plan.md
│
└── old/                           # 🗄️ 歷史文件（封存）
    ├── v3.5.4_穩定版本深度分析報告.md
    ├── v3.5.4_critical_issues_analysis.md
    └── ... (舊版本文件)
```

---

## 🎯 根據情境找文件

### 情境 1：我是第一次使用 MeetingScribe

**推薦路徑：**
1. 閱讀專案根目錄的 [README.md](../README.md)（5 分鐘）
2. 根據您的作業系統選擇快速開始指南：
   - macOS → [Mac 快速部署](guides/mac_native_deployment_guide.md)
   - Windows → [Windows 快速開始](guides/windows_quick_start_guide.md)
3. 測試上傳一個音訊檔案
4. 如有問題，查看 [疑難排解](#疑難排解)

### 情境 2：我想使用 GPU 加速

**推薦路徑：**
1. 確認您的 GPU 類型：
   - NVIDIA GPU → [Windows 部署指南](guides/windows_deployment_guide.md)
   - Apple Silicon → [Mac Whisper 指南](guides/mac_whisper_guide.md)
2. 閱讀 [GPU 加速指南](guides/gpu_acceleration_guide.md)
3. 執行環境驗證腳本：`python scripts/verify_env.py`

### 情境 3：我需要管理和維護系統

**推薦路徑：**
1. 閱讀 [管理者操作指南](guides/administrator_guide.md)
2. 瞭解 [Docker 重建時機](guides/docker_rebuild_guide.md)
3. 查看 [系統開發分析](analysis/system_development_analysis.md)

### 情境 4：我遇到問題需要解決

**推薦路徑：**
1. 查看 [疑難排解](#疑難排解) 章節
2. 搜尋 [evidence/](./evidence/) 目錄中的驗證報告
3. 查看最新的 [版本修復報告](./v3.5.5_系統修復驗證報告.md)
4. 如仍未解決，查看 GitHub Issues

### 情境 5：我想了解技術細節

**推薦路徑：**
1. 閱讀 [系統開發分析](analysis/system_development_analysis.md)
2. 查看 [架構設計](architecture/plans/project_restructure_plan.md)
3. 閱讀 [技術報告](reports/)
4. 查看 `.github/INSTRUCTIONS.md`（開發指導原則）

---

## 📖 文件命名規範

### 通用規則

1. **全小寫字母**：使用小寫字母（中文除外）
2. **底線分隔**：英文單字使用底線 `_` 分隔
3. **有意義名稱**：檔案名稱清楚描述內容
4. **版本標記**：重要文件包含版本號（`_v3.5.5`）

### 檔案類型格式

| 類型 | 格式 | 範例 |
|------|------|------|
| 驗證證據 | `{功能}_evidence_v{版本}.md` | `queue_logic_fix_evidence_v3.5.1.md` |
| 技術報告 | `{主題}_report.md` | `code_review_report.md` |
| 部署指南 | `{平台}_{類型}_guide.md` | `mac_deployment_guide.md` |
| 系統分析 | `{主題}_analysis.md` | `system_development_analysis.md` |
| 版本報告 | `v{版本}_{主題}.md` | `v3.5.5_系統修復驗證報告.md` |

---

## 📋 文件維護規則

### 新增文件

1. **確定文件類型**
   - 使用指南 → `guides/`
   - 驗證報告 → `evidence/`
   - 技術報告 → `reports/`
   - 系統分析 → `analysis/`

2. **遵循命名規範**
   - 使用正確的格式
   - 包含版本號（若適用）

3. **更新導航文件**
   - 在本 README.md 中新增連結
   - 更新相關章節

4. **Git commit 說明**
   - 清楚描述新增的文件用途
   - 使用繁體中文

### 更新文件

1. **保持檔案名稱一致**
2. **重大變更時升級版本號**
3. **在文件頂部標註更新日期**
4. **更新 CHANGELOG.md**

### 封存文件

1. **移至 `old/` 目錄**（而非刪除）
2. **更新本 README.md**（移除過時連結）
3. **在 CHANGELOG.md 中說明**

---

## 🔍 疑難排解

### 找不到我需要的文件

**Q：我想瞭解 macOS 如何部署，但找不到文件？**

A：請查看 `guides/` 目錄：
- `mac_native_deployment_guide.md` - 原生服務部署
- `mac_whisper_guide.md` - Whisper 設定
- `mac_deployment_guide.md` - 基本部署

**Q：我想查看之前版本的修復報告？**

A：舊版本報告已移至 `old/` 目錄，包含：
- v3.5.4 穩定版本分析
- v3.5.3 服務連線修復
- v3.5.2 MLX-Whisper 修復

### 文件中的範例無法執行

**Q：我按照文件中的步驟操作，但出現錯誤？**

A：請檢查：
1. 您的系統版本是否與文件版本一致
2. 是否執行了環境驗證：`python scripts/verify_env.py`
3. 是否查看了該文件的「疑難排解」章節
4. 查看最新的 [版本修復報告](./v3.5.5_系統修復驗證報告.md)

### 版本號不一致

**Q：為什麼有些文件標示 v3.5.4，有些是 v3.5.5？**

A：
- 最新版本：v3.5.5（2025-12-18）
- 舊版本文件已移至 `old/` 目錄
- 使用 `grep -r "v3.5.4" .` 檢查是否有遺漏

---

## 📞 支援與反饋

### 回報問題

1. **文件問題**：在 GitHub 開 Issue，標籤 `documentation`
2. **功能問題**：在 GitHub 開 Issue，標籤 `bug` 或 `enhancement`
3. **安全問題**：私下聯繫維護者

### 貢獻文件

我們歡迎文件貢獻！請：
1. Fork 專案
2. 建立文件分支：`git checkout -b docs/improve-xxx`
3. 遵循命名規範和撰寫規範（見 `.github/INSTRUCTIONS.md`）
4. 提交 Pull Request

---

## 📅 版本歷史

| 版本 | 日期 | 更新內容 |
|------|------|----------|
| v3.5.5 | 2025-12-18 | 徹底更新所有文件，新增文件驅動開發原則 |
| v3.5.4 | 2025-12-07 | 新增版本控制強化文件 |
| v3.5.1 | 2025-12-06 | 重新組織文件結構 |
| v1.0 | 2025-12-05 | 初版文件導航 |

---

## 📚 相關資源

- [專案根目錄 README](../README.md)
- [變更紀錄](../CHANGELOG.md)
- [開發指導原則](../.github/INSTRUCTIONS.md)
- [GitHub Repository](https://github.com/hsiaojohnny/meetingscribe)

---

**維護者**：MeetingScribe 開發團隊  
**最後更新**：2025-12-18  
**版本**：v3.5.5
