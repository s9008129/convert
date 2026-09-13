# 政府智慧會議紀錄生成系統 v4.0.0 深度檢查報告與任務分解

> 🗄️ **歷史文件**：本文是 v4.0.0（2025-12）時期的檢查報告與任務分解，僅保留當時的規劃紀錄，**不代表現行系統**。
> 現行版本請以根目錄 `VERSION`／`CHANGELOG.md` 為準；現行架構與模組職責請見[系統架構與程式設計書](系統架構與程式設計書.md)。

> **版本**：v1.0  
> **建立日期**：2025-12-19  
> **狀態**：📋 待 CEO 批准  
> **前置文件**：`doc/Implement_Plan.md`（已批准）  
> **目標版本**：v3.5.5 → v4.0.0

---

## 📋 階段 3：深度檢查報告（Check & Clarify）

### 3.1 環境驗證結果

| 項目 | 現況 | 狀態 |
|------|------|------|
| **GPU** | NVIDIA RTX 4090, 24564 MiB VRAM | ✅ 確認 |
| **可用 VRAM** | 23486 MiB (閒置時) | ✅ 足夠 |
| **NVIDIA Driver** | 561.09 | ✅ 確認 |
| **Docker** | v28.3.0 | ✅ 確認 |
| **Python** | 3.11.9 | ✅ 確認 |
| **Ollama** | v0.13.4 | ✅ 確認 |
| **faster-whisper** | 最新版 1.2.1 可用 | ✅ 確認 |

### 3.2 模型可用性驗證

#### ASR 模型：Breeze-ASR-25

| 驗證項目 | 結果 | 詳情 |
|----------|------|------|
| **原始模型 Hugging Face** | ✅ 可用 | `MediaTek-Research/Breeze-ASR-25` |
| **Faster-Whisper 轉換版** | ✅ 可用 | `SoybeanMilk/faster-whisper-Breeze-ASR-25` |
| **GitHub 原始碼** | ✅ 可用 | `mtkresearch/Breeze-ASR-25` (42 stars) |
| **社群使用案例** | ✅ 多個 | 25+ 專案在 GitHub 使用此模型 |

**技術細節確認**：
- 基於 Whisper-large-v2 微調
- 專門針對台灣華語 + 中英混用優化
- 支援 INT8 量化，VRAM 需求約 2GB
- 使用方式：`WhisperModel("SoybeanMilk/faster-whisper-Breeze-ASR-25")`

#### LLM 模型：Gemma4

| 驗證項目 | 結果 | 詳情 |
|----------|------|------|
| **預設模型** | `gemma4:31b` | 後端 / Docker / 設定檔已統一 |
| **Windows RTX 4090 實測** | ✅ 通過 | 指定音檔 E2E 驗證成功 |
| **相容標籤解析** | ✅ 啟用 | 若只安裝 `gemma4:31b-it-q4_K_M` 等標籤，後端會自動解析 |
| **macOS 覆寫** | ✅ 支援 | 可用 `.env.local` 的 `LOCAL_LLM_MODEL_MAC` 指定較小 Gemma4 標籤 |
| **生成策略** | ✅ 已落地 | extraction → merge → refine、num_ctx 8192、reserved_output 3072 |

**補充說明**

- `gemma4:31b` 本機安裝大小約 19GB，本專案已在 Windows 11 + RTX 4090 + Ollama 完成實測
- 若 macOS 記憶體不足，可在 `.env.local` 設定 `LOCAL_LLM_MODEL_MAC` 改用較小的 Gemma4 標籤
- 指定驗收檔案 `tests\亞洲無人機AI創新應用研發中心.m4a` 已成功生成繁體中文 Markdown / DOCX 會議記錄

### 3.3 修正後的技術方案

#### LLM 策略修正

| 原計畫 | 修正後方案 | 理由 |
|--------|------------|------|
| gemma3 量化變體 | **統一本地預設為 `gemma4:31b`** | 與目前程式碼、Docker 與 E2E 驗證結果一致 |
| 單一路徑模型設定 | **保留 `LOCAL_LLM_MODEL_MAC` 覆寫** | 確保 macOS 仍可依記憶體條件調整 |
| DOCX 直接導頁下載 | **改為 `fetch` + `blob` + 後端 ImportError 處理** | 徹底修復只拿到 JSON 的下載失敗體感 |

**核心洞察**：目前關鍵不再是 Gemma3 量化選型，而是 **Gemma4 的穩定輸出約束、下載流程可靠性與跨平台覆寫策略**。

### 3.4 VRAM 配置重新評估

| 元件 | VRAM 需求 | 運行時機 | 狀態 |
|------|-----------|----------|------|
| Breeze-ASR-25 (INT8) | ~2GB | 轉錄階段 | ✅ |
| Gemma4-31B（預設 / 相容 q4 標籤） | ~20GB | 摘要階段 | ✅ |
| 系統保留 | ~2GB | 持續 | ✅ |
| **總計** | ~22GB | - | ✅ 安全 |
| **剩餘** | ~2GB | 緩衝 | ⚠️ 緊湊 |

**關鍵設計：順序執行**
- ASR 完成後**釋放 VRAM**
- LLM 再載入使用
- 不同時運行，避免 VRAM 衝突

---

## 📋 階段 4：任務分解（Tasks）

### 任務總覽

| 週次 | 任務群組 | 預估時間 | 優先級 |
|------|----------|----------|--------|
| Week 1 | 基礎設施準備 | 2 天 | 🔴 高 |
| Week 1-2 | ASR 模組升級 | 3-4 天 | 🔴 高 |
| Week 2 | LLM 參數優化 | 1-2 天 | 🔴 高 |
| Week 2-3 | Docker 最小成本部署 | 2 天 | 🟡 中 |
| Week 3 | 整合測試 | 2-3 天 | 🔴 高 |

---

### Task 1: 建立開發分支與環境準備

**目標**：建立 feature 分支，確保開發隔離

**步驟**：
```bash
# 1.1 建立 develop 分支
git checkout -b develop

# 1.2 建立功能分支
git checkout -b feature/asr-breeze-upgrade

# 1.3 更新 .github/instructions.md（已完成）
```

**驗收標準**：
- [ ] develop 分支已建立
- [ ] feature/asr-breeze-upgrade 分支已建立
- [ ] .github/instructions.md 存在且內容正確

**預估時間**：30 分鐘

---

### Task 2: 更新 requirements.txt

**目標**：升級依賴套件以支援新模型

**變更內容**：
```python
# 升級項目
faster-whisper==1.2.1      # 從 1.0.1 升級
ctranslate2>=4.5.0         # 確保 CUDA 12 + cuDNN 9 支援

# 新增項目
huggingface_hub>=0.20.0    # 模型下載管理
```

**驗收標準**：
- [ ] requirements.txt 已更新
- [ ] Docker build 成功
- [ ] 無版本衝突

**預估時間**：30 分鐘

---

### Task 3: 升級 transcription.py - 整合 Breeze-ASR-25

**目標**：將 ASR 模型從 whisper-medium 升級到 Breeze-ASR-25

**主要變更**：

```python
# backend/services/transcription.py

# 舊版
settings.WHISPER_MODEL  # "medium"

# 新版
BREEZE_ASR_MODEL = "SoybeanMilk/faster-whisper-Breeze-ASR-25"

# VAD 參數優化
vad_parameters = {
    "threshold": 0.5,
    "min_speech_duration_ms": 250,
    "min_silence_duration_ms": 2000,
    "speech_pad_ms": 400
}

# 轉錄參數
initial_prompt = "以下是台灣繁體中文的會議記錄。"
beam_size = 5
temperature = 0.0
```

**驗收標準**：
- [ ] 模型載入成功
- [ ] 10 分鐘音檔轉錄無重複幻覺
- [ ] VAD 正確過濾靜音段落
- [ ] GPU 加速正常運作

**預估時間**：1 天

---

### Task 4: 更新 config.yaml - LLM 參數優化

**目標**：同步 Gemma4 預設值與本地摘要參數

**變更內容**：

```yaml
# 舊版
llm:
  ollama:
    model: "gemma3:27b-it-qat"
    temperature: 0.1

# 新版
llm:
  ollama:
    model: "gemma4:31b"
    num_ctx: 8192
    temperature: 0.2               # 最終摘要溫度；extract / merge / refine 由程式分階段控制
    top_k: 64
    top_p: 0.95
    repeat_penalty: 1.08
    max_output_tokens: 3072
```

**驗收標準**：
- [ ] config.yaml 已更新
- [ ] Ollama 正確讀取新參數
- [ ] 輸出格式遵從率提升，且無簡體漂移 / thought tags 殘留

**預估時間**：2 小時

---

### Task 5: 更新 summarization.py - 讀取新 LLM 參數

**目標**：確保 LLM 服務使用新的生成參數

**主要變更**：

```python
# backend/services/summarization.py

# 新增參數讀取
def _build_ollama_options(self):
    return {
        "temperature": 0.5,
        "top_k": 64,
        "top_p": 0.95,
        "repeat_penalty": 1.1,
        "num_ctx": 32768
    }
```

**驗收標準**：
- [ ] 新參數正確傳遞至 Ollama
- [ ] 會議記錄格式遵從率 >= 90%
- [ ] 無繁簡混雜問題

**預估時間**：4 小時

---

### Task 6: 更新 Dockerfile.gpu - Volume 策略

**目標**：確保模型持久化，避免重複下載

**主要變更**：

```dockerfile
# 新增環境變數
ENV HF_HOME=/app/models \
    XDG_CACHE_HOME=/app/models \
    TRANSFORMERS_CACHE=/app/models

# 確保 models 目錄存在
RUN mkdir -p /app/models && chown -R appuser:appuser /app/models
```

```yaml
# docker-compose-windows-gpu.yml
volumes:
  - meetingscribe-asr-models:/app/models  # Named Volume

volumes:
  meetingscribe-asr-models:
    name: meetingscribe-asr-models
```

**驗收標準**：
- [ ] 首次啟動自動下載模型
- [ ] Rebuild 後模型保留
- [ ] docker volume ls 可見 meetingscribe-asr-models

**預估時間**：2 小時

---

### Task 7: 建立模型預載腳本

**目標**：提供手動預載模型的選項

**新增檔案**：`scripts/download_models.py`

```python
#!/usr/bin/env python3
"""
模型預載腳本 - 首次部署使用
"""
from faster_whisper import WhisperModel

def download_breeze_asr():
    print("正在下載 Breeze-ASR-25 模型...")
    model = WhisperModel(
        "SoybeanMilk/faster-whisper-Breeze-ASR-25",
        device="cpu",  # 下載時不需要 GPU
        compute_type="int8"
    )
    print("✅ Breeze-ASR-25 下載完成")
    del model

if __name__ == "__main__":
    download_breeze_asr()
```

**驗收標準**：
- [ ] 腳本可獨立執行
- [ ] 模型下載至正確目錄
- [ ] 不需要 GPU 即可下載

**預估時間**：1 小時

---

### Task 8: 更新 core/config.py - 新增 ASR 設定

**目標**：參數化 ASR 模型設定

**主要變更**：

```python
# backend/core/config.py

class Settings(BaseSettings):
    # ...existing code...
    
    # ========================================
    # ASR 設定 (v4.0.0 新增)
    # ========================================
    ASR_MODEL: str = Field(
        default="SoybeanMilk/faster-whisper-Breeze-ASR-25",
        description="ASR 模型名稱"
    )
    ASR_COMPUTE_TYPE: str = Field(
        default="int8_float16",
        description="ASR 計算精度 (int8/int8_float16/float16)"
    )
    ASR_VAD_ENABLED: bool = Field(
        default=True,
        description="是否啟用 VAD"
    )
    ASR_VAD_THRESHOLD: float = Field(
        default=0.5,
        description="VAD 語音偵測閾值"
    )
    ASR_BEAM_SIZE: int = Field(
        default=5,
        description="Beam Search 大小"
    )
```

**驗收標準**：
- [ ] 新設定可透過環境變數覆蓋
- [ ] 預設值符合 Breeze-ASR-25 推薦
- [ ] 向後相容舊版設定

**預估時間**：2 小時

---

### Task 9: 整合測試 - ASR 模組

**目標**：驗證 ASR 升級後的效能

**測試案例**：

| 編號 | 測試案例 | 輸入 | 預期結果 |
|------|----------|------|----------|
| ASR-01 | 短音檔轉錄 | 5 分鐘會議 | 無幻覺，CER < 10% |
| ASR-02 | 長音檔轉錄 | 60 分鐘會議 | 無幻覺，CER < 15% |
| ASR-03 | 中英混用 | 含英文專有名詞 | 英文正確辨識 |
| ASR-04 | 靜音處理 | 含 30 秒靜音 | 不產生填充文字 |
| ASR-05 | GPU 加速 | 任意音檔 | 使用 CUDA，速度 > 10x |

**驗收標準**：
- [ ] 所有測試案例通過
- [ ] 效能基準符合預期

**預估時間**：1 天

---

### Task 10: 整合測試 - LLM 模組

**目標**：驗證 LLM 參數優化後的效能

**測試案例**：

| 編號 | 測試案例 | 輸入 | 預期結果 |
|------|----------|------|----------|
| LLM-01 | 格式遵從 | 標準逐字稿 | 100% 遵循指定格式 |
| LLM-02 | 長逐字稿 | 20000 字 | 正確摘要，無截斷 |
| LLM-03 | 繁中驗證 | 任意逐字稿 | 無簡體/英文混雜 |
| LLM-04 | VRAM 使用 | 完整流程 | 峰值 < 22GB |
| LLM-05 | 回應時間 | 任意逐字稿 | 首 token < 10 秒 |

**驗收標準**：
- [ ] 格式遵從率 >= 90%
- [ ] 無 VRAM OOM 錯誤

**預估時間**：1 天

---

### Task 11: 端對端測試

**目標**：完整流程驗證

**測試流程**：
```
音檔上傳 → ASR 轉錄 → LLM 摘要 → 輸出會議記錄
```

**測試案例**：

| 編號 | 輸入 | 預期輸出 |
|------|------|----------|
| E2E-01 | 10 分鐘會議錄音 | 完整會議記錄（5 章節） |
| E2E-02 | 30 分鐘會議錄音 | 完整會議記錄（5 章節） |
| E2E-03 | 60 分鐘會議錄音 | 完整會議記錄（5 章節） |

**驗收標準**：
- [ ] 全流程無錯誤
- [ ] 輸出品質符合預期
- [ ] 處理時間合理

**預估時間**：1 天

---

### Task 12: 更新升級計畫狀態

**目標**：更新文件狀態

**變更內容**：
- 更新 `doc/升級計畫.md` 狀態為「✅ 已完成」
- 更新 `doc/Implement_Plan.md` 狀態為「✅ 已完成」
- 建立 `doc/Test_Report.md`

**預估時間**：30 分鐘

---

### Task 13: 版本發布準備

**目標**：準備 v4.0.0 發布

**步驟**：
```bash
# 合併至 develop
git checkout develop
git merge feature/asr-breeze-upgrade

# 建立 release 分支
git checkout -b release/v4.0.0

# 更新版本號
# - CHANGELOG.md
# - README.md（如需要）

# 合併至 main
git checkout main
git merge release/v4.0.0
git tag -a v4.0.0 -m "feat: ASR 升級至 Breeze-ASR-25 + LLM 參數優化"
git push origin main --tags
```

**驗收標準**：
- [ ] 所有測試通過
- [ ] CHANGELOG.md 已更新
- [ ] v4.0.0 tag 已建立

**預估時間**：1 小時

---

## 📊 任務依賴關係

```
Task 1 (分支準備)
    │
    ├── Task 2 (requirements.txt)
    │       │
    │       └── Task 6 (Dockerfile)
    │
    ├── Task 8 (config.py ASR 設定)
    │       │
    │       └── Task 3 (transcription.py)
    │               │
    │               └── Task 9 (ASR 測試)
    │
    └── Task 4 (config.yaml LLM)
            │
            └── Task 5 (summarization.py)
                    │
                    └── Task 10 (LLM 測試)
                            │
                            └── Task 11 (E2E 測試)
                                    │
                                    ├── Task 7 (預載腳本)
                                    ├── Task 12 (文件更新)
                                    └── Task 13 (版本發布)
```

---

## ⚠️ 風險清單與緩解措施

| 風險 | 可能性 | 影響 | 緩解措施 |
|------|--------|------|----------|
| Breeze-ASR 首次下載慢 | 高 | 低 | 提供預載腳本 |
| VRAM 不足 | 低 | 高 | 維持 QAT，順序執行 |
| 格式遵從率未達標 | 中 | 中 | 迭代調整 system prompt |
| Docker build 失敗 | 低 | 中 | 保留現有 Dockerfile |

---

## ✅ CEO 批准清單

請審閱以下項目並確認：

- [ ] **1. 技術方案修正**：維持 QAT 而非 8-bit，是否接受？
- [ ] **2. 13 項任務分解**：是否完整涵蓋所有需求？
- [ ] **3. 風險緩解措施**：是否充分？
- [ ] **4. 時程估計**：約 2-3 週是否合理？

---

## 📌 下一步行動

**待 CEO 批准本文件後，將開始執行：**

→ **Task 1：建立開發分支與環境準備**

---

## 📝 文件版本記錄

| 日期 | 版本 | 變更內容 |
|------|------|----------|
| 2025-12-19 | v1.0 | 初版建立 - 包含深度檢查與任務分解 |

---

> 📌 **重要提醒**：在您明確批准之前，不會進行任何程式碼修改。
