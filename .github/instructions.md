# 政府智慧會議紀錄生成系統 專案最高指導原則

> **版本**：v1.2.0  
> **建立日期**：2025-12-19  
> **最後更新**：2026-09-13  
> **狀態**：✅ 生效中  
> **專案代號**：政府智慧會議紀錄生成系統 ASR/LLM Upgrade 2025
> **當前版本**：v4.7.2（唯一來源：根目錄 `VERSION`）

---

## 🎯 核心使命

將雜亂的會議錄音轉化為結構清晰、符合台灣政府機關公文風格的繁體中文會議記錄。

---

## ⚠️ 不可違反的強制約束

### 1. 🚫 禁止使用中國模型

**本專案嚴禁使用任何中國開發的 LLM 模型**

| 模型 | 開發者 | 狀態 |
|------|--------|------|
| Qwen / Qwen2 / Qwen2.5 | Alibaba 阿里巴巴 | 🚫 禁止 |
| DeepSeek / DeepSeek-V2 / DeepSeek-V3 | DeepSeek | 🚫 禁止 |
| Baichuan | Baichuan Intelligence | 🚫 禁止 |
| ChatGLM | 智譜 AI (Zhipu) | 🚫 禁止 |
| Yi / Yi-1.5 | 零一萬物 (01.AI) | 🚫 禁止 |
| InternLM | 上海人工智能實驗室 | 🚫 禁止 |
| MOSS | 復旦大學 | 🚫 禁止 |

### 2. 🔧 維持 Ollama 架構

- 經評估後，**維持現有 Ollama 推理引擎**，不升級至 vLLM
- 理由：維護友善、單一使用者場景足夠、您可獨立處理日常維護

### 3. 📦 最小成本 Docker 部署原則

```
「不重複下載、不重複建置」
```

| 變更類型 | 需要 Rebuild? | 需要重啟容器? |
|----------|---------------|---------------|
| Python 依賴 (requirements.txt) | ✅ 是 | - |
| 後端程式碼 (backend/*.py) | ❌ 否 | ✅ 是 |
| 前端檔案 (frontend/*) | ❌ 否 | ❌ 否 |
| 設定檔 (config.yaml) | ❌ 否 | ✅ 是 |
| ASR 模型 | ❌ 否 | ✅ 是 |

---

## 📋 SDD 開發流程（Specification-Driven Development）

### 開發階段順序

```
📋 規劃階段 → 📝 設計階段 → ✅ 檢查階段 → 🔧 實作階段 → 🧪 測試階段 → 🚀 上線階段
```

### 必須遵守的流程

1. **階段 1：規劃與討論**
   - 產出：`升級計畫.md` → CEO 審閱並批准

2. **階段 2：實作計劃**
   - 產出：`implement_plan.md` → CEO 審閱並批准

3. **階段 3：深度檢查（Check & Clarify）**
   - 驗證技術可行性、邊界情況、邏輯矛盾

4. **階段 4：任務分解**
   - 產出：`tasks.md` → CEO 審閱並批准

5. **階段 5：程式碼實作**
   - 依 tasks.md 逐一實作
   - 每完成一個 Task 進行單元測試

6. **階段 6：測試與驗證**
   - 產出：`Test_Report.md`

7. **階段 7：人工驗收與上線**
   - CEO 進行人工測試
   - 合併至 main 分支，正式上線

### ⚠️ 關鍵規則

- **未經 CEO 批准，不得進入下一階段**
- **每個階段都必須產生清晰的文件供 CEO 確認**
- **隨時可以暫停，每個階段都有明確的交付物和檢查點**

---

## 🔀 Git 版本控制策略

### 分支策略

```
main（穩定版）
  │
  ├── develop（開發主線）
  │     │
  │     ├── feature/asr-breeze-upgrade
  │     ├── feature/llm-gemma-optimize
  │     ├── feature/config-v2
  │     └── feature/vad-pipeline
  │
  └── release/v4.0.0（發布候選版）
```

### 分支保護規則

| 分支 | 用途 | 保護規則 |
|------|------|----------|
| `main` | 生產環境穩定版 | 禁止直接推送，需 PR + 審核 |
| `develop` | 開發整合分支 | 功能分支合併目標 |
| `feature/*` | 功能開發分支 | 完成後合併至 develop |

### Commit 規範（Conventional Commits）

```
<類型>(<範圍>): <描述>
```

| 類型 | 說明 | 範例 |
|------|------|------|
| `feat` | 新功能 | `feat(asr): 新增 Breeze-ASR-25 模型支援` |
| `fix` | 錯誤修復 | `fix(vad): 修正長音檔靜音偵測問題` |
| `docs` | 文件更新 | `docs: 更新升級計劃文件` |
| `refactor` | 重構 | `refactor(config): 重構配置載入邏輯` |
| `test` | 測試 | `test(asr): 新增 Breeze 模型整合測試` |
| `chore` | 雜項 | `chore: 更新 Docker 基底映像` |

### 版本號規則（Semantic Versioning）

```
v主版本.次版本.修訂版本

例如：v4.0.0
 │ │ │
 │ │ └── 修訂版本：向下相容的錯誤修復
 │ └──── 次版本：向下相容的新功能
 └────── 主版本：不相容的 API 變更
```

---

## 🛠️ 技術棧選型原則

### ASR（語音轉錄）

| 環境 | 引擎 | 說明 |
|------|------|------|
| macOS 26+ / Apple Silicon | **Apple SpeechAnalyzer**（唯一引擎） | macOS 內建模型、免下載 HF 模型；`ASR_BACKEND=auto` 即 `apple`；fail-closed、**永不 fallback**；顯式 Whisper 值一律拒絕（T20260912-2242-01） |
| Windows / Linux | **Breeze-ASR-26**（transformers 路徑，預設）／faster-whisper ＋ Breeze-ASR-25（回滾路徑） | 專為台灣繁體中文設計，中英混用最佳 |

### LLM（大語言模型）

| 優先順序 | 模型 | 理由 |
|----------|------|------|
| 1️⃣ | **Gemma3-27B-it-QAT** (v4.0.0 已啟用) | Google 開發，QAT 量化適合 24GB VRAM |
| 2️⃣ | Gemma3-12B | 備用，VRAM 不足時使用 |

> ℹ️ 上表為 v4.0.0 的選型紀錄。**現行實際預設**請以 `backend/core/config.py` 為準：Ollama `LOCAL_LLM_MODEL=gemma4:31b`（`config.py:53-56`）、LM Studio 備援 `LMSTUDIO_MODEL=gpt-oss-20b`（`config.py:68-71`）。

### LLM 參數設定 (v4.0.0)

| 參數 | 值 | 說明 |
|------|-----|------|
| temperature | 0.5 | 平衡穩定性與創意 |
| top_k | 64 | Google 推薦 |
| top_p | 0.95 | Google 推薦 |
| repeat_penalty | 1.1 | 減少重複輸出 |
| num_ctx | 32768 | 完整上下文視窗 |

### VAD（語音活動偵測）

- 使用 **Silero VAD v6**（faster-whisper 路徑內建；macOS Apple 路徑不使用 VAD——helper 直接處理整檔，`use_vad=False` 語意）

---

## 💻 目標環境

- **作業系統**：Windows 11
- **GPU**：NVIDIA RTX 4090 (24GB VRAM)
- **部署方式**：Docker + Ollama

### VRAM 配置

| 用途 | 預估 VRAM |
|------|-----------|
| Breeze-ASR-25 (INT8) | ~2GB |
| Gemma3-27B (QAT, Q4_0) | ~20GB |
| **總計** | ~22GB ✅ |

> ⚠️ **關鍵設計**：ASR 和 LLM 順序執行，不同時載入。ASR 完成後釋放 VRAM，LLM 再載入使用。

---

## 📌 CTO 職責

作為您的首席技術官（CTO），我的核心責任是：

1. **引導您依據計畫完成整個升級作業**
2. **提醒您所有的細節和應注意的地方**
3. **確保每個階段都有清晰的文件供您審閱**
4. **用白話解釋每個技術決策**
5. **在您批准前，不進行任何程式碼修改**

---

## 📄 文件版本記錄

| 日期 | 版本 | 變更內容 |
|------|------|----------|
| 2025-12-19 | v1.0.0 | 初版建立 |
| 2025-12-19 | v1.1.0 | 更新為 v4.0.0 實際部署配置：Breeze-ASR-25 + Gemma3 QAT + 優化參數 |
| 2026-09-13 | v1.2.0 | ASR 技術棧改為平台分流：macOS 26+ 唯一引擎 Apple SpeechAnalyzer（無 Whisper 選項、永不 fallback）；Windows/Linux 維持 Breeze-ASR-26／faster-whisper；VAD 僅 faster-whisper 路徑；當前版本改以 `VERSION` 檔為準（v4.7.2） |
