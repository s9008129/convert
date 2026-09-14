# 政府智慧會議紀錄生成系統 v4.0.0 實作計畫

> 🗄️ **歷史文件**：本文是 v4.0.0（2025-12）時期的實作計畫，僅保留當時的規劃紀錄，**不代表現行系統**。
> 現行版本請以根目錄 `VERSION`／`CHANGELOG.md` 為準；現行架構與模組職責請見[系統架構與程式設計書](系統架構與程式設計書.md)。

> **版本**：v1.1  
> **建立日期**：2025-12-19  
> **最後更新**：2025-12-19  
> **狀態**：✅ CEO 已批准  
> **前置文件**：`doc/升級計畫.md`（已批准）  
> **目標版本**：v3.5.5 → v4.0.0

---

## 📋 文件目的

本文件是 SDD（Specification-Driven Development）流程的「階段 2：實作計劃」產出物。
詳細說明技術實作規格，待 CEO 審閱批准後，將進入「階段 3：深度檢查」。

---

## 🎯 升級目標回顧

| 目標 | 現況 | 升級後預期 | 驗收標準 |
|------|------|------------|----------|
| 長語音轉錄品質 | 重複字樣嚴重 | 錯誤率降低 50% 以上 | 1 小時音檔無重複幻覺 |
| 會議記錄格式遵從性 | 格式不一致 | 100% 遵循指定格式 | 5 次測試格式完全正確 |
| 跨平台參數化 | 設定分散 | 一個設定檔，全平台通用 | 設定檔驗證通過 |

> **2026-04 現況補充**：本地預設模型已改為 `gemma4:31b`，並以 `tests\亞洲無人機AI創新應用研發中心.m4a` 完成 Windows 11 + RTX 4090 + Ollama 的 E2E 驗證；macOS 透過 `LOCAL_LLM_MODEL_MAC` 保留較小 Gemma4 標籤的覆寫路徑，前端結果頁則改為僅保留 Markdown / DOCX 下載。

---

## 🏗️ 技術架構總覽

### 升級前後對比

```
【升級前 v3.5.5】                    【升級後 v4.0.0】
                                    
音訊輸入                             音訊輸入
    │                                   │
    ▼                                   ▼
┌─────────────────┐              ┌─────────────────┐
│ Whisper-medium  │              │  Silero VAD v6  │  ← 新增！語音活動偵測
│ （直接轉錄）      │              └─────────────────┘
└─────────────────┘                     │
    │                                   ▼
    │                             ┌─────────────────┐
    │                             │ Breeze-ASR-25   │  ← 升級！台灣專用模型
    │                             │ (Faster-Whisper)│
    │                             └─────────────────┘
    │                                   │
    ▼                                   ▼
┌─────────────────┐              ┌─────────────────┐
│ Gemma3-27B      │              │ Gemma4-31B      │  ← 現況：Gemma4 + Gemma4 標籤自動解析
│ (歷史配置)      │              │ (預設 / q4 相容)│
│ temp: 0.1       │              │ temp: 0.2       │
└─────────────────┘              └─────────────────┘
    │                                   │
    ▼                                   ▼
會議記錄輸出                        會議記錄輸出
```

### 模組變更摘要

| 模組 | 變更類型 | 說明 |
|------|----------|------|
| `backend/services/transcription.py` | 🔄 重構 | 整合 VAD + Breeze-ASR-25 |
| `backend/services/summarization.py` | 🔧 修改 | 調整 LLM 參數 |
| `backend/core/config.py` | 🔄 重構 | 新配置系統 |
| `config/` | ✨ 新增 | 階層式配置目錄 |
| `docker/Dockerfile.gpu` | 🔧 修改 | 更新依賴版本 |
| `requirements.txt` | 🔧 修改 | 新增/更新套件 |

---

## 📦 模組一：ASR 升級（Breeze-ASR-25 + VAD）

### 1.1 技術規格

| 項目 | 規格 |
|------|------|
| ASR 模型 | `SoybeanMilk/faster-whisper-Breeze-ASR-25` |
| 模型來源 | Hugging Face (Faster-Whisper 格式) |
| VAD 引擎 | Silero VAD v6 (Faster-Whisper 內建) |
| 量化方式 | INT8_FLOAT16（混合精度） |
| VRAM 需求 | ~2GB |
| 支援語言 | zh-TW, en, zh-TW+en 混合 |

### 1.2 程式碼變更

#### `backend/services/transcription.py`

**變更項目**：
1. 替換模型名稱從 `whisper-medium` 為 `Breeze-ASR-25`
2. 整合 Silero VAD 預處理
3. 新增批次推理（Batched Inference）支援
4. 優化長音檔處理邏輯

**新增參數**：

```python
# VAD 設定
vad_filter: bool = True
vad_parameters: dict = {
    "threshold": 0.5,
    "min_speech_duration_ms": 250,
    "min_silence_duration_ms": 2000,
    "speech_pad_ms": 400
}

# 轉錄設定
beam_size: int = 5
temperature: float = 0.0
initial_prompt: str = "以下是台灣繁體中文的會議記錄。"
condition_on_previous_text: bool = True
no_speech_threshold: float = 0.6
```

### 1.3 驗收標準

| 編號 | 測試案例 | 預期結果 | 優先級 |
|------|----------|----------|--------|
| ASR-01 | 10 分鐘會議音檔轉錄 | 無重複幻覺，CER < 10% | 🔴 高 |
| ASR-02 | 1 小時會議音檔轉錄 | 無重複幻覺，CER < 15% | 🔴 高 |
| ASR-03 | 中英混用音檔轉錄 | 英文詞彙正確識別 | 🟡 中 |
| ASR-04 | 靜音段落處理 | 不產生填充文字 | 🔴 高 |
| ASR-05 | GPU 加速驗證 | 使用 CUDA，速度 > 10x real-time | 🟡 中 |

---

## 📦 模組二：LLM 參數優化

### 2.1 技術規格

| 項目 | 現況 | 升級後 |
|------|------|--------|
| 模型 | `gemma3:27b-it-qat` | `gemma4:31b` |
| 量化 | 4-bit QAT | 依已安裝 Gemma4 標籤自動解析 |
| temperature | 0.1 | 0.2（最終摘要） |
| top_k | 未設定 | 64 |
| top_p | 未設定 | 0.95 |
| repeat_penalty | 未設定 | 1.08 |
| num_ctx | 32768 | 8192 |
| max_output_tokens | 未設定 | 3072 |
| VRAM 需求 | ~20GB | ~20GB |

> ⚠️ **現況修正**：專案已統一改為 `gemma4:31b`，Windows / RTX 4090 可直接驗證；若 Ollama 實際安裝的是 `gemma4:31b-it-q4_K_M` 等 Gemma4 標籤，後端會自動解析並使用，macOS 則可透過 `LOCAL_LLM_MODEL_MAC` 覆寫較小模型。

### 2.2 程式碼變更

#### `config.yaml`

**變更項目**：

```yaml
llm:
  ollama:
    model: "gemma4:31b"
    num_ctx: 8192
    temperature: 0.2                # 最終摘要；程式內另有 extraction / merge / refine 低溫控制
    top_k: 64
    top_p: 0.95
    repeat_penalty: 1.08
    max_output_tokens: 3072
```

#### `backend/services/summarization.py`

**變更項目**：
1. 讀取新的 LLM 參數
2. 加強 system prompt 的繁中約束
3. 新增輸出格式驗證

### 2.3 驗收標準

| 編號 | 測試案例 | 預期結果 | 優先級 |
|------|----------|----------|--------|
| LLM-01 | 標準會議逐字稿摘要 | 100% 遵循指定格式 | 🔴 高 |
| LLM-02 | 長逐字稿（20000 字）處理 | 正確產生摘要，無截斷 | 🔴 高 |
| LLM-03 | 繁體中文輸出驗證 | 無簡體中文、無英文混雜 | 🔴 高 |
| LLM-04 | VRAM 使用驗證 | ASR + LLM 總計 < 20GB | 🟡 中 |
| LLM-05 | 回應時間驗證 | 首 token < 5 秒 | 🟢 低 |

---

## 📦 模組三：配置系統重構

### 3.1 新配置目錄結構

```
config/
├── base.yaml                 # 基礎共用設定
├── platforms/
│   └── windows.yaml          # Windows 特定設定
├── models/
│   ├── asr/
│   │   └── breeze-asr-25.yaml
│   └── llm/
│       └── gemma4-31b.yaml
└── prompts/
    └── meeting_summary.yaml
```

### 3.2 配置載入優先順序

```
1. base.yaml（基礎預設值）
      ↓
2. platforms/{platform}.yaml（平台特定設定）
      ↓
3. 環境變數（最高優先權）
      ↓
4. 最終配置
```

### 3.3 程式碼變更

#### `backend/core/config.py`

**變更項目**：
1. 新增階層式配置載入器
2. 支援 `extends` 語法
3. 環境變數覆蓋機制
4. 配置驗證（使用 Pydantic）

### 3.4 驗收標準

| 編號 | 測試案例 | 預期結果 | 優先級 |
|------|----------|----------|--------|
| CFG-01 | 載入 base.yaml | 成功載入預設值 | 🔴 高 |
| CFG-02 | 載入 platform 覆蓋 | 正確覆蓋平台設定 | 🔴 高 |
| CFG-03 | 環境變數覆蓋 | ENV 優先於檔案 | 🟡 中 |
| CFG-04 | 舊版 config.yaml 相容 | 可正常讀取 v3 配置 | 🔴 高 |

---

## 📦 模組四：Docker 最小成本部署

### 4.1 Volume 掛載策略

```yaml
volumes:
  # 資料目錄
  - ../data/uploads:/app/data/uploads
  - ../data/outputs:/app/data/outputs
  
  # ASR 模型持久化
  - meetingscribe-asr-models:/app/models
  
  # 開發模式：程式碼同步
  - ../backend:/app/backend
  - ../frontend:/app/frontend
  - ../config:/app/config
```

### 4.2 Dockerfile.gpu 變更

**變更項目**：
1. 基底映像：`nvidia/cuda:12.3.2-cudnn9-runtime-ubuntu22.04`
2. 使用 BuildKit cache mount 加速 pip install
3. 模型目錄設定為 Volume（不含在映像中）

### 4.3 驗收標準

| 編號 | 測試案例 | 預期結果 | 優先級 |
|------|----------|----------|--------|
| DKR-01 | 首次 build | 成功建置，映像 < 5GB | 🔴 高 |
| DKR-02 | 修改後端程式碼後重啟 | 無需 rebuild，重啟即生效 | 🔴 高 |
| DKR-03 | 修改前端後刷新 | 無需重啟，刷新即生效 | 🟡 中 |
| DKR-04 | Rebuild 後模型保留 | Named Volume 中的模型不重新下載 | 🔴 高 |
| DKR-05 | GPU 加速驗證 | 容器內可使用 CUDA | 🔴 高 |

---

## 📦 模組五：requirements.txt 更新

### 5.1 依賴變更

```python
# 升級
faster-whisper==1.1.0      # 從 1.0.1 升級，支援更多 VAD 選項
ctranslate2==4.5.0         # 從 4.0.0 升級

# 新增
silero-vad==5.0.0          # VAD 獨立使用（可選）
```

### 5.2 驗收標準

| 編號 | 測試案例 | 預期結果 | 優先級 |
|------|----------|----------|--------|
| DEP-01 | pip install | 所有依賴安裝成功 | 🔴 高 |
| DEP-02 | 版本相容性 | 無版本衝突警告 | 🟡 中 |

---

## 🔄 實作順序

### 建議順序（依風險和依賴關係）

```
Week 1: 配置系統重構
  ├── Task 1.1: 建立 config/ 目錄結構
  ├── Task 1.2: 實作配置載入器
  └── Task 1.3: 驗證舊版相容性

Week 2: ASR 模組升級
  ├── Task 2.1: 整合 Breeze-ASR-25 模型
  ├── Task 2.2: 整合 VAD 預處理
  └── Task 2.3: 長音檔測試與調整

Week 3: LLM 優化 + Docker 更新
  ├── Task 3.1: 調整 LLM 參數
  ├── Task 3.2: 更新 Dockerfile.gpu
  └── Task 3.3: 驗證 Volume 策略

Week 4: 整合測試與上線
  ├── Task 4.1: 端對端測試
  ├── Task 4.2: 效能基準測試
  └── Task 4.3: 上線準備
```

---

## ⚠️ 風險與緩解措施

### 高風險項目

| 風險 | 可能性 | 影響 | 緩解措施 |
|------|--------|------|----------|
| Breeze-ASR 模型下載失敗 | 低 | 高 | 準備 Whisper Large-v3 備用 |
| VRAM 不足 | 低 | 高 | 維持 QAT，順序執行（現有機制） |
| 新配置與舊版不相容 | 中 | 高 | 實作相容層 |

### 回滾計劃

1. **立即回滾**：`git checkout main`
2. **資料保護**：所有資料在 Volume 中，不受影響
3. **配置保留**：舊版 config.yaml 保留不刪除

---

## 📊 資源需求估算

### VRAM 配置（RTX 4090 = 24GB）

| 元件 | VRAM 需求 | 運行時機 |
|------|-----------|----------|
| Breeze-ASR-25 (INT8) | ~2GB | 轉錄階段 |
| Gemma4-31B（預設 / 相容 q4 標籤） | ~20GB | 摘要階段 |
| 系統保留 | ~2GB | 持續 |
| **總計** | ~22GB | - |
| **剩餘** | ~2GB | 緩衝空間 |

> ⚠️ **關鍵設計：順序執行** - ASR 完成後釋放 VRAM，LLM 再載入使用。現有程式碼已實作此機制。

### 時間估算

| 階段 | 預估時間 |
|------|----------|
| 配置系統重構 | 2-3 天 |
| ASR 模組升級 | 3-4 天 |
| LLM 優化 | 1-2 天 |
| Docker 更新 | 1-2 天 |
| 整合測試 | 2-3 天 |
| **總計** | 約 2-3 週 |

---

## ✅ CEO 批准清單

請審閱以下項目並確認：

- [ ] **1. ASR 升級方案**：Breeze-ASR-25 + VAD 是否符合需求？
- [ ] **2. LLM 優化方案**：維持 QAT + 參數調整 (temp 0.1→0.5, 新增 top_k/top_p/repeat_penalty) 是否可接受？
- [ ] **3. 配置系統重構**：階層式配置是否過於複雜？
- [ ] **4. Docker 策略**：Volume 掛載策略是否清晰？
- [ ] **5. 實作順序**：4 週時程是否合理？
- [ ] **6. 風險緩解**：回滾計劃是否足夠？

---

## 📌 下一步行動

**待 CEO 批准本計畫後，將進入：**

→ **階段 3：深度檢查（Check & Clarify）**
  - 驗證所有技術方案的可行性
  - 確認 Hugging Face 模型可下載
  - 測試 VRAM 配置是否符合預期

→ **階段 4：任務分解**
  - 產生 `doc/規格與設計/tasks.md`（含詳細實作步驟）

---

## 📝 文件版本記錄

| 日期 | 版本 | 變更內容 |
|------|------|----------|
| 2025-12-19 | v1.0 | 初版建立 |
| 2025-12-19 | v1.1 | 根據深度檢查修正：維持 QAT，調整 VRAM 估算，修正 LLM 參數 |

---

> 📌 **重要提醒**：在您明確批准之前，不會進行任何程式碼修改。
