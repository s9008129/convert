# 政府智慧會議紀錄生成系統 Copilot 最高準則

> 適用範圍：本專案所有 AI 輔助開發與維護工作  
> 文件版本：v4.0  
> 更新日期：2026-02-28

---

## 1. 角色定義

### 人類（Product Owner / Operator）
- 定義需求目標、業務情境、驗收優先級。  
- 提供部署環境、操作限制與風險容忍度。  
- 最終核准功能範圍與上線時程。

### AI（Copilot / Engineering Partner）
- 先讀規格、再動程式碼，避免盲改。  
- 根據現有架構提出最小可行變更（smallest safe change）。  
- 將需求轉為可驗證產物：程式碼、測試、文件、風險說明。

### 分工原則
- 人類負責「要做什麼與為何做」。  
- AI 負責「怎麼做、如何驗證、如何降低風險」。

---

## 2. 環境規範

- 語言與框架：Python + FastAPI（後端）、Vanilla JavaScript（前端）。  
- 主要服務：Whisper / Breeze-ASR-25 轉錄、Ollama / LM Studio（本地 LLM）、Gemini API（雲端）。  
- 依賴安裝：以 `requirements.txt` 為準。  
- **MUST 使用 conda 環境**（`conda activate meetingscribe`）進行安裝與執行。  
- 預設服務入口：`http://localhost:9527`。  
- **MUST 使用台北時間（Asia/Taipei, UTC+8）** 作為所有時間戳記、日誌檔案命名、commit 訊息的時區標準。

### 重要目錄

| 目錄 | 說明 |
|------|------|
| `backend/` | FastAPI 後端（API、服務、模型） |
| `frontend/` | 前端（HTML/JS/CSS） |
| `tests/` | pytest 測試 |
| `scripts/macos/` | macOS 專用腳本 |
| `scripts/windows/` | Windows 專用腳本 |
| `docker/` | Docker 配置 |
| `doc/` | 文件、規格、研究資料 |
| `config*.yaml` | 配置檔（根目錄） |

**規範**：任何環境差異（路徑、GPU、模型）都必須文件化，不得只留在對話或腦中假設。

---

## 3. SDD 開發法（Specification-Driven Development）

1. **Spec First**：先更新 `doc/spec.md` 的 User Story / FR / SC，再改碼。  
2. **Contract Aware**：API 行為變更必須同步更新端點文件與錯誤語意。  
3. **Test Traceable**：每個需求至少對應一個可執行測試（單元/整合/E2E 其一）。  
4. **Doc Sync**：功能、設定、流程一旦變更，README/指南/變更紀錄同步更新。  
5. **Small Batch**：單次修改聚焦單一問題，降低回歸風險。

### SDD 文件即可執行資產

| 文件 | 可執行性 | 說明 |
|------|---------|------|
| `doc/spec.md` | ✅ 可驗證 | 驗收標準可直接轉換為測試案例 |
| `CHANGELOG.md` | ✅ 可追蹤 | 版本變更可審計 |
| `README.md` | ✅ 可執行 | 啟動步驟可直接複製執行 |

---

## 4. 人機協作溝通原則

- 先講結論，再列證據（檔案路徑、測試結果、限制）。  
- 對非技術使用者採「行動導向」描述：做什麼、為什麼、預期結果。  
- 遇到不確定性要明確標示假設，不可偽裝成事實。  
- 回報格式固定：**變更內容 → 影響範圍 → 驗證結果 → 風險與下一步**。

---

## 5. 編碼規範

### Python（後端）
- 優先使用型別標註與 Pydantic 模型。  
- I/O 與 CPU 密集任務分離（async + executor），避免阻塞事件迴圈。  
- 檔案操作必做路徑安全檢查（`basename`、白名單、禁止 traversal）。  
- 錯誤需分級：可恢復（降級/重試）與不可恢復（明確失敗）。

### JavaScript（前端）
- 維持狀態單一來源（`state` 物件），避免隱式共享狀態。  
- 所有 API/WebSocket 錯誤都要有 UI 反饋。  
- 以可理解性優先，不引入不必要框架。

### 一般原則
- 不做無關重構。  
- 不硬編碼祕密資訊。  
- 日誌保留業務上下文但不可洩漏敏感資料。

---

## 6. 測試策略

- 測試框架：`pytest`。  
- 測試分層：
  - 單元測試：模型、驗證、工具函數。  
  - 整合測試：API 路由、佇列、WebSocket 行為。  
  - E2E 測試：完整上傳→排隊→完成流程。

### 測試執行原則
- 先跑基線測試，了解現況，再做修改。  
- 修改後至少重跑受影響模組測試。  
- 若因環境缺依賴導致失敗，需在回報中清楚註記（例如 `aiofiles`、`mlx_whisper` 缺失）。

### 穩定測試指令
```bash
python -m pytest tests/ --ignore=tests/test_mlx_direct.py -v
```

### 覆蓋率建議
- 核心路徑（upload/queue/task/result/websocket）應維持高覆蓋。  
- 安全相關邏輯（檔名驗證、路徑限制）必有測試。

---

## 7. CI/CD 與部署

- 現有 `.github/workflows/build-windows.yml` 為停用狀態（`if: false`），不可假設有完整 CI 保護。  
- 部署前必做：
  1. `scripts/verify_env.py` 確認依賴與目錄。  
  2. 關鍵 API 健康檢查（`/api/health`）。  
  3. 實測上傳與結果下載流程。  
- 啟動建議使用 `start_service.sh`，避免多套啟動腳本造成環境飄移。

---

## 8. 版本控制規範（Non-Negotiable）

### Auto Commit 機制

**每次完成任務後，MUST 執行 git commit。**

#### Commit 訊息格式

```
<type>(<scope>): <簡短摘要>

## 執行內容
- 具體做了哪些修改
- 新增/修改/刪除了哪些檔案

## 決策理由
- 為什麼選擇這個方案

## 執行結果
- 達成了什麼效果
- 驗證結果（通過/失敗）
```

#### Commit Type

| Type | 用途 |
|------|------|
| `feat` | 新功能 |
| `fix` | 錯誤修復 |
| `docs` | 文件更新 |
| `refactor` | 重構（不改變功能） |
| `test` | 測試相關 |
| `chore` | 雜項（設定、依賴等） |

#### 語言要求

- Commit 訊息 **MUST 使用繁體中文（zh-TW）**
- 技術術語可保留英文（如 API、MCP、LLM、DOCX）

### .gitignore 規範

以下類型的檔案 **禁止** 加入版本控制：
- 圖片檔案（`*.png`, `*.jpg`, `*.jpeg`, `*.gif`, `*.bmp`）
- 測試音檔（`tests/test_audio/`）
- 環境檔案（`.env`, `.env.local`）
- 快取與暫存（`__pycache__/`, `.pytest_cache/`, `temp/`）
- 日誌檔案（`logs/`, `*.log`）
- 備份檔案（`*.bak`, `*.backup`）
- 敏感資訊（`*.pem`, `*.key`, `secrets.yaml`）

---

## 9. 文件維護

每次需求變更都要檢查下列文件是否需同步：

- `doc/spec.md`（需求與驗收標準）  
- `README.md`（使用方式、模式說明）  
- `CHANGELOG.md`（版本變更）  
- `doc/使用者手冊.md`（操作指南）

**規則**：若程式與文件衝突，以「修正文件到真實行為」或「修正程式達到文件規格」二擇一，禁止長期不一致。

---

## 10. 錯誤處理與可觀測性

- 以結構化日誌為預設（一般/錯誤/JSON）。  
- 長任務必須可觀測：進度、階段、排隊位置、最終狀態。  
- API 錯誤訊息需可行動（告訴使用者下一步，而非只丟 exception）。  
- 對外部依賴（Ollama/LM Studio/Gemini）需提供健康檢查與失敗回退策略。  
- 超時、取消、失敗皆須有明確狀態碼與任務狀態落地。

---

## 11. 技術選型原則

**語言選擇不重要，架構選擇才重要。**

| 優先級 | 原則 | 說明 |
|--------|------|------|
| 1 | **穩定性** | 生產環境驗證、成熟度高 |
| 2 | **可靠性** | 錯誤率低、行為可預測 |
| 3 | **可讀性** | AI 和人類都能理解 |
| 4 | **可維護性** | 社群活躍、文件完善 |
| 5 | **最佳實例** | 有成功案例可參考 |
| 6 | **可被檢驗** | 有測試方法可驗證 |

**禁止**：基於「熟悉度」或「最新」選擇技術

---

## 12. Context7 MCP 使用規範

**所有技術決策 MUST 透過 Context7 MCP 取得最新官方文件。**

### 使用流程

1. 先呼叫 `resolve-library-id` 取得正確的 library ID
2. 再呼叫 `get-library-docs` 取得文件
3. 基於官方文件做出技術決策

### 禁止事項

- ❌ 憑記憶或猜測使用 API
- ❌ 使用過時的技術文件
- ❌ 不驗證就使用第三方範例

---

## 附：執行準則（快速版）

1. 先讀 `doc/spec.md` 再改碼。  
2. 只做最小必要變更。  
3. 所有變更可追溯到需求與測試。  
4. 測試失敗要說清楚是程式問題還環境問題。  
5. 文件與程式保持同步，避免知識債。  
6. 每次完成任務後 MUST git commit（繁體中文 log）。  
7. 技術決策 MUST 使用 Context7 MCP 取得最新文件。
