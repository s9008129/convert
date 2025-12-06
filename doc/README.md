# 文件組織結構說明

本目錄包含 MeetingScribe 專案的所有技術文件，已根據文件類型進行分類整理。

## 📁 目錄結構

```
doc/
├── evidence/        # 驗證證據 - 包含所有測試驗證報告和證據
├── reports/         # 技術報告 - 包含詳細的技術分析和修復報告
├── guides/          # 部署指南 - 包含所有部署、操作、使用指南
├── analysis/        # 分析文件 - 包含系統分析、需求分析、架構分析
└── README.md        # 本文件
```

---

## 🗂️ 分類說明

### evidence/ - 驗證證據

包含所有功能驗證報告和測試證據文件。

**命名規範**：`{功能}_{類型}_evidence_v{版本}.md`

**檔案清單**：
- `queue_logic_fix_evidence_v3.5.1.md` - 排隊邏輯修復驗證證據
- `mac_migration_evidence_v3.5.0.md` - macOS 遷移驗證證據
- `task_completion_evidence_v3.5.0.md` - 任務完成驗證證據
- `windows_rtx4090_migration_evidence.md` - Windows RTX4090 遷移證據
- `documentation_sync_evidence_v3.4.0.md` - 文件同步驗證證據
- `gpu_acceleration_evidence_v3.4.3.md` - GPU 加速驗證證據
- `docker_zero_rebuild_evidence.md` - Docker 零重建驗證證據
- `english_fix_evidence.md` - 英文修正驗證證據
- `final_completion_evidence_v3.5.0.md` - 最終完成驗證證據

---

### reports/ - 技術報告

包含詳細的技術分析、修復報告和系統報告。

**命名規範**：`{功能}_{類型}_report_v{版本}.md` 或 `{功能}_report.md`

**檔案清單**：
- `queue_logic_fix_report_v3.5.1.md` - 排隊邏輯修復詳細報告
- `code_review_report.md` - 程式碼審查報告
- `fix_summary_report.md` - 修復總結報告
- `migration_verification_report.md` - 遷移驗證報告
- `llm_quality_comparison_report.md` - LLM 品質比對報告

---

### guides/ - 部署指南

包含所有平台的部署、操作、使用指南。

**命名規範**：`{平台}_{類型}_guide.md`

**分類**：

#### macOS 相關
- `mac_native_deployment_guide.md` - macOS 原生部署指南
- `mac_whisper_guide.md` - macOS Whisper 設定指南
- `mac_deployment_guide.md` - macOS 部署指南

#### Windows 相關
- `windows_deployment_guide.md` - Windows 完整部署指南
- `windows_batch_deployment_guide.md` - Windows 批次檔部署指南
- `windows_quick_start_guide.md` - Windows 快速開始指南

#### Docker 相關
- `docker_deployment_guide.md` - Docker 部署經驗指南
- `docker_rebuild_guide.md` - Docker 映像檔重建時機指南
- `docker_zero_rebuild_guide.md` - Docker 零重建部署指南

#### GPU 與通用指南
- `gpu_acceleration_guide.md` - GPU 加速支援指南
- `quick_start_guide.md` - 快速入門指南
- `quick_deployment_guide.md` - 快速部署指南
- `administrator_guide.md` - 管理者操作指南

---

### analysis/ - 分析文件

包含系統分析、架構分析、解決方案分析等文件。

**命名規範**：`{主題}_analysis.md` 或 `{主題}_solution.md`

**檔案清單**：
- `system_development_analysis.md` - 系統開發及實作規劃分析
- `windows_deployment_analysis.md` - Windows 部署分析
- `windows_deployment_solution.md` - Windows 部署解決方案

---

## 📝 命名規範總結

### 通用規則
1. **全小寫字母**：所有檔案名稱使用小寫字母
2. **底線分隔**：使用底線 `_` 分隔單字
3. **有意義的名稱**：檔案名稱應清楚描述內容
4. **版本標記**：重要文件應包含版本號（例如：`_v3.5.1`）

### 檔案類型規範

| 類型 | 格式 | 範例 |
|------|------|------|
| 驗證證據 | `{功能}_{類型}_evidence_v{版本}.md` | `queue_logic_fix_evidence_v3.5.1.md` |
| 技術報告 | `{功能}_{類型}_report_v{版本}.md` | `queue_logic_fix_report_v3.5.1.md` |
| 部署指南 | `{平台}_{類型}_guide.md` | `mac_deployment_guide.md` |
| 分析文件 | `{主題}_analysis.md` | `system_development_analysis.md` |

---

## 🔍 如何查找文件

### 按功能查找
1. **排隊邏輯相關**：
   - 證據：`evidence/queue_logic_fix_evidence_v3.5.1.md`
   - 報告：`reports/queue_logic_fix_report_v3.5.1.md`

2. **macOS 部署相關**：
   - 指南：`guides/mac_*_guide.md`
   - 證據：`evidence/mac_migration_evidence_v3.5.0.md`

3. **Windows 部署相關**：
   - 指南：`guides/windows_*_guide.md`
   - 分析：`analysis/windows_deployment_analysis.md`

### 按版本查找
- **v3.5.1**：`evidence/queue_logic_fix_evidence_v3.5.1.md`
- **v3.5.0**：`evidence/mac_migration_evidence_v3.5.0.md`
- **v3.4.3**：`evidence/gpu_acceleration_evidence_v3.4.3.md`

---

## 📋 維護規則

### 新增文件
1. 確定文件類型（evidence/reports/guides/analysis）
2. 使用正確的命名規範
3. 放入對應的目錄
4. 更新本 README 的檔案清單

### 更新文件
1. 保持檔案名稱一致
2. 重大變更時考慮版本號升級
3. 更新變更記錄（CHANGELOG.md）

### 刪除文件
1. 確認文件已過時且無參考價值
2. 考慮移至 `archive/` 目錄而非刪除
3. 更新本 README 的檔案清單

---

## 🎯 快速導航

### 新手入門
1. `guides/quick_start_guide.md` - 快速開始
2. `guides/quick_deployment_guide.md` - 快速部署

### macOS 用戶
1. `guides/mac_deployment_guide.md` - 基本部署
2. `guides/mac_native_deployment_guide.md` - 原生服務部署
3. `guides/mac_whisper_guide.md` - Whisper 設定

### Windows 用戶
1. `guides/windows_quick_start_guide.md` - 快速開始
2. `guides/windows_deployment_guide.md` - 完整部署
3. `guides/windows_batch_deployment_guide.md` - 批次檔部署

### 管理員
1. `guides/administrator_guide.md` - 管理者操作指南
2. `guides/docker_deployment_guide.md` - Docker 部署
3. `guides/gpu_acceleration_guide.md` - GPU 加速設定

---

## 📅 更新記錄

- **2025-12-06**：重新組織文件結構，建立分類目錄
- **2025-12-06**：統一檔案命名規範
- **2025-12-06**：新增 README.md 說明文件

---

**維護者**：MeetingScribe 開發團隊  
**最後更新**：2025-12-06  
**版本**：v1.0.0
