# 政府智慧會議紀錄生成系統 文件中心

> **版本**：v4.7.3
> **最後更新**：2026-09-14
> **這裡是什麼**：全專案文件的導航入口。根目錄只保留 `README.md`（專案總覽）與 `CHANGELOG.md`（變更紀錄），其餘文件依用途分為「操作手冊」與「規格與設計」兩類，放在下列子資料夾。

> ⚠️ 系統版本一律以根目錄 `VERSION` 檔為準。若本頁版本落後於 `VERSION`，代表導航頁未同步（回報即可），不影響系統行為。

---

## 📂 文件分類導航

### 📖 操作手冊（給日常使用與部署的人）

| 文件 | 說明 |
|------|------|
| [使用者手冊](操作手冊/使用者手冊.md) | 網頁操作指南（非技術人員友善，已更新至 v4.3.x 新介面） |
| [部署更新手冊_v4.1](操作手冊/部署更新手冊_v4.1.md) | 正式環境更新部署逐步教學（含 v4.3.3 更新專用捷徑：兩行指令、零下載） |
| [uv管理說明](操作手冊/uv管理說明.md) | Python 環境改用 uv 的白話說明（vs conda、離線內網用法） |

### 📐 規格與設計（給開發者）

| 文件 | 說明 |
|------|------|
| [spec](規格與設計/spec.md) | 功能規格（需求、驗收標準） |
| [implement_plan](規格與設計/implement_plan.md) | 實作計畫 |
| [tasks](規格與設計/tasks.md) | 任務清單 |
| [系統架構與程式設計書](規格與設計/系統架構與程式設計書.md) | 系統架構、處理管線、API、部署設計的完整技術文件（開發者必讀） |
| [發言者分離與主席裁示 研究與設計](規格與設計/發言者分離與主席裁示-研究與設計.md) | 說話者分離（sherpa-onnx）、發言者標註逐字稿與主席裁示歸屬：選型實測、fail-soft 契約、風險與驗收方式 |
| [Apple SpeechAnalyzer 維運手冊](apple-speech-analyzer-operations.md) | macOS 26+／Apple Silicon 唯一 ASR 引擎的維運視角：平台矩陣、錯誤碼、fail-closed 與排障 |
| [Apple Speech CLI 建置說明](apple-speech-cli-build.md) | `apple_speech_cli/` Swift helper 的建置、產物位置與版控注意事項（macOS＋Xcode 限定） |
| [Apple SpeechAnalyzer 移植上下文](apple-speech-analyzer-porting-context.md) | 上游母本對照與移植地雷（開發／維護者參考） |

---

## 🧭 情境查找

| 我想… | 看這份 |
|---|---|
| 第一次認識這個系統 | [../README.md](../README.md) |
| 學會用網頁產出會議紀錄 | [操作手冊/使用者手冊.md](操作手冊/使用者手冊.md) |
| 更新正式環境（GPU 主機） | [操作手冊/部署更新手冊_v4.1.md](操作手冊/部署更新手冊_v4.1.md) 的「v4.3.3 更新專用捷徑」 |
| 在 Mac 上跑系統／看懂 Apple 轉錄引擎 | [apple-speech-analyzer-operations.md](apple-speech-analyzer-operations.md)（建置 helper 另見 [apple-speech-cli-build.md](apple-speech-cli-build.md)） |
| 知道各版本改了什麼 | [../CHANGELOG.md](../CHANGELOG.md) |
| 開發者想搞懂系統怎麼運作 | [規格與設計/系統架構與程式設計書.md](規格與設計/系統架構與程式設計書.md) |
| 設定/重建 Python 開發環境 | [操作手冊/uv管理說明.md](操作手冊/uv管理說明.md) |
| 加機關專有名詞讓轉錄更準 | 編輯 `data/glossary/公務詞彙.txt`（一行一詞，支援「錯字=>正確」寫法，重啟生效） |

---

## 📝 維護規則

1. 新文件一律放入上述分類子資料夾，**不要**放專案根目錄（根目錄只留 README/CHANGELOG）。
2. 文件過時後**直接刪除即可**（git 歷史可追溯），不再設歷史封存資料夾。
3. 舊版 CLI（`main.py`＋`src/`）已標記為 deprecated，功能以後端服務（`backend/`）為準。
