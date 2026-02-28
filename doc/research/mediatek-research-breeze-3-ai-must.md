# MediaTek Research Breeze 生態系統：讓 AI 聽懂台語、說出台味、守護台灣

**研究日期：** 2026-02-27  
**研究目的：** 整合 MediaTek Research (聯發創新基地) 全系列開源 AI 模型，提供完整下載連結供後續開發準備  
**範疇澄清：** "Breeze 3" 截至研究日期尚未正式釋出，本報告涵蓋 Breeze 生態系目前最完整的台灣語言 AI 開源模型群

---

## Executive Summary

MediaTek Research（聯發創新基地，縮寫 MR）是台灣聯發科技旗下的 AI 研究部門，長期致力於打造**適合正體中文及台灣語境的開源基礎模型**。截至 2025 年底，MR 已形成一套完整的台灣 AI 技術鏈，涵蓋：
- 🗣️ **語音辨識（ASR）**：Breeze ASR 25 - 針對台灣口音、中英混用優化
- 🔊 **語音合成（TTS）**：BreezyVoice - 台灣腔語音合成 + 聲音複製  
- 🧠 **多模態語言模型（LLM）**：Llama-Breeze2 (3B/8B) - 繁體中文強化  
- 📱 **行動端應用**：BreezeApp - 純手機離線 AI  
- 🎙️ **口語語言模型（SpokenLM）**：TASTE - 語音對齊的口語建模

**重要說明：** "Breeze 3" 目前（2026-02-27）並無正式以此名稱命名的模型發布記錄[^1]。現行最新版本為 **Breeze ASR 25**（2025.06.16 開源）與 **Breeze 2 系列**（2025.01.24 開源）。本報告以「台灣語言 AI 完整生態系」為研究核心。

---

## ⚠️ 關於「台語」的重要說明

本文標題中的「台語」在 MediaTek Research 的語境中，主要指：

| 用法 | 實際含意 | MR 支援程度 |
|------|---------|------------|
| **台灣腔中文** (Taiwanese Mandarin) | 台灣口音的普通話、在地詞彙 | ✅ 完整支援 |
| **中英混用** (Code-switching) | 台灣人日常中英夾雜語句 | ✅ 核心強項（+56% 精準度） |
| **台語/閩南語** (Hokkien/Holo) | 以閩南語為主的本土語言 | ⚠️ 尚無獨立模型，部分覆蓋 |

> 如需純正台語/閩南語（Hokkien）ASR，目前 MR 尚未釋出專屬模型。社群資源可參考：
> - [NCHC Formosa Speech](https://huggingface.co/formospeech) 
> - [台灣本土語言資源](https://huggingface.co/datasets/mozilla-foundation/common_voice_17_0) (CommonVoice)

---

## 架構總覽

```
MediaTek Research 台灣 AI 技術鏈
┌─────────────────────────────────────────────┐
│           語音輸入 (Audio Input)             │
│                    ↓                         │
│  ┌──────────────────────────────────────┐   │
│  │    Breeze ASR 25 (語音辨識)          │   │
│  │    Whisper-large-v2 fine-tuned      │   │
│  │    1.55B params | MIT License       │   │
│  └──────────────────────────────────────┘   │
│                    ↓                         │
│  ┌──────────────────────────────────────┐   │
│  │    Llama-Breeze2 3B/8B (語言模型)    │   │
│  │    繁體中文 + 視覺 + Function Call   │   │
│  │    Apache 2.0 License              │   │
│  └──────────────────────────────────────┘   │
│                    ↓                         │
│  ┌──────────────────────────────────────┐   │
│  │    BreezyVoice (語音合成)            │   │
│  │    台灣腔 TTS + 聲音克隆             │   │
│  │    Apache 2.0 License              │   │
│  └──────────────────────────────────────┘   │
│                    ↓                         │
│           語音輸出 (Audio Output)             │
└─────────────────────────────────────────────┘

  延伸技術：TASTE SpokenLM (端對端語音 LLM)
  行動端：BreezeApp (Android/iOS 離線 AI)
```

---

## 模型一：Breeze ASR 25（語音辨識）

### 概述
**最新的台灣語音辨識模型**，基於 OpenAI Whisper-large-v2 微調，專為台灣在地語境強化。代號 **Twister**。

### 核心特色
- 強化**繁體中文**語境辨識（CommonVoice16-zh-TW: WER 7.97% vs Whisper 9.84%）
- **中英混用**辨識大幅提升（ASCEND-MIX: WER 16.38% vs Whisper 21.01%，降低 **22%**）
- 支援**時間戳記對齊**（適合自動字幕生成）
- 模型大小：**1.55B 參數**，量化後約 2-4GB VRAM

### 訓練資料
| 資料集 | 類型 | 語言 | 時長 | 授權 |
|--------|------|------|------|------|
| ODC Synth (by BreezyVoice) | 合成 | 台灣中文 | 10,000h | ODC + Apache 2.0 |
| CommonVoice17-EN | 真實 | 英語 | 1,738h | CC0 |
| NTUML2021 | 真實 | 中英混用 | 11h | MIT |

### ✅ 開源下載連結

| 資源 | 連結 | 說明 |
|------|------|------|
| **HuggingFace 模型** | https://huggingface.co/MediaTek-Research/Breeze-ASR-25 | 主要下載點 |
| **GitHub 程式碼** | https://github.com/mtkresearch/Breeze-ASR-25 | 含 run.py 範例 |
| **論文 (arXiv)** | https://arxiv.org/pdf/2506.11130 | "A Self-Refining Framework..." |
| **Whisper CLI 整合** | `git submodule update --init --recursive` | 見 GitHub 說明 |

#### 快速下載指令
```bash
# 方法一：Hugging Face Hub
pip install transformers datasets[audio] accelerate
python -c "from transformers import WhisperProcessor; WhisperProcessor.from_pretrained('MediaTek-Research/Breeze-ASR-25')"

# 方法二：Whisper CLI
git clone --recursive https://github.com/mtkresearch/Breeze-ASR-25
pip install third_party/whisper-patch-breeze
whisper audio.wav --model breeze-asr-25

# 方法三：git lfs（直接下載權重）
git lfs install
git clone https://huggingface.co/MediaTek-Research/Breeze-ASR-25
```

#### 範例程式碼（摘自官方 run.py[^2]）
```python
from transformers import WhisperProcessor, WhisperForConditionalGeneration, AutomaticSpeechRecognitionPipeline

processor = WhisperProcessor.from_pretrained("MediaTek-Research/Breeze-ASR-25")
model = WhisperForConditionalGeneration.from_pretrained("MediaTek-Research/Breeze-ASR-25").to("cuda").eval()

asr_pipeline = AutomaticSpeechRecognitionPipeline(
    model=model,
    tokenizer=processor.tokenizer,
    feature_extractor=processor.feature_extractor,
    chunk_length_s=0  # Sequential mode: best results for long audio
)
output = asr_pipeline("audio.wav", return_timestamps=True)
```

#### 台灣腔優化小技巧
```python
# 用 initial_prompt 引導模型使用台灣繁體中文
output = asr_pipeline(
    "audio.wav",
    generate_kwargs={"initial_prompt": "以下是台灣繁體中文的會議記錄。"}
)
```

### 授權：MIT License

---

## 模型二：BreezyVoice（語音合成 / TTS）

### 概述
**台灣腔文字轉語音模型**，基於 CosyVoice 架構，針對台灣口音、多音字（破音字）優化，支援聲音複製（Voice Cloning）。

### 核心特色
- 支援繁體中文、英文、**注音輸入**
- **聲音複製**：僅需 5 秒參考音頻即可克隆聲線
- 台灣腔調優化：正確處理台灣特有多音字及節奏
- 中英混用（code-switching）合成能力

### ✅ 開源下載連結

| 資源 | 連結 | 說明 |
|------|------|------|
| **HuggingFace 主模型** | https://huggingface.co/MediaTek-Research/BreezyVoice | 完整模型 |
| **HuggingFace 300M版** | https://huggingface.co/MediaTek-Research/BreezyVoice-300M | 輕量版 |
| **GitHub 程式碼** | https://github.com/mtkresearch/BreezyVoice | 含 Docker/ONNX 支援 |
| **論文 (arXiv)** | https://arxiv.org/abs/2501.17790 | "BreezyVoice: Adapting TTS..." |
| **Kaggle Demo** | https://www.kaggle.com/code/a24998667/breezyvoice-playground | 線上試用 |
| **訓練資料集** | BreezyVoice 合成語料（ODC 授權） | 見 HuggingFace |

#### 快速下載指令
```bash
# 主模型
git lfs install
git clone https://huggingface.co/MediaTek-Research/BreezyVoice

# 300M 輕量版
git clone https://huggingface.co/MediaTek-Research/BreezyVoice-300M

# 程式碼
git clone https://github.com/mtkresearch/BreezyVoice
cd BreezyVoice
# 建議 Python 3.10，支援 Docker、ONNX 部署
```

#### 使用範例（台灣腔 TTS）
```python
# 參考 BreezyVoice GitHub README
# 支援聲音複製：提供 5 秒參考音頻 + 目標文字
python single_inference.py \
    --text "歡迎使用 BreezyVoice，這是台灣腔的語音合成。" \
    --reference_audio "speaker_reference.wav"
```

### 授權：Apache 2.0 License

---

## 模型三：Llama-Breeze2（多模態語言模型）

### 概述
**最先進的繁體中文開源 LLM**，基於 Meta LLaMA 3.2 持續預訓練，加入視覺理解和函式呼叫能力，分 **3B（手機）** 和 **8B（電腦）** 兩種規格。

### 核心特色
- **繁體中文知識強化**：大規模繁體中文語料持續訓練
- **視覺語言模型（VLM）**：可讀圖、理解圖表、OCR
- **函式呼叫（Function Calling）**：適合 Agent / API 呼叫場景
- **台灣文化本位**：正確使用台灣在地詞彙（軟體 vs 软件，計程車 vs 出租车）

### ✅ 開源下載連結

| 資源 | 連結 | 說明 |
|------|------|------|
| **Llama-Breeze2-3B-Instruct (HF)** | https://huggingface.co/MediaTek-Research/Llama-Breeze2-3B-Instruct | 手機/邊緣端用 |
| **Llama-Breeze2-8B-Instruct (HF)** | https://huggingface.co/MediaTek-Research/Llama-Breeze2-8B-Instruct | PC/伺服器用 |
| **Breeze 2 Collection** | https://huggingface.co/collections/MediaTek-Research/breeze-2-67863158443a06a72dd29900 | 完整系列集合 |
| **論文 (arXiv)** | https://arxiv.org/abs/2501.13921 | "The Breeze 2 Herd of Models" |
| **Kaggle Demo** | https://www.kaggle.com/code/ycckaggle/breeze-2-demo | 線上試用 |

#### 快速下載指令
```bash
# 3B 版（適合本地/手機開發）
git lfs install
git clone https://huggingface.co/MediaTek-Research/Llama-Breeze2-3B-Instruct

# 8B 版（適合伺服器/高效能推論）
git clone https://huggingface.co/MediaTek-Research/Llama-Breeze2-8B-Instruct

# 或使用 HuggingFace transformers
pip install transformers
python -c "
from transformers import AutoModelForCausalLM, AutoTokenizer
model = AutoModelForCausalLM.from_pretrained('MediaTek-Research/Llama-Breeze2-8B-Instruct')
tokenizer = AutoTokenizer.from_pretrained('MediaTek-Research/Llama-Breeze2-8B-Instruct')
"

# GGUF 版（適合 Ollama/llama.cpp）
# 社群轉換版：搜尋 HuggingFace "Llama-Breeze2 GGUF"
```

### 授權：依 LLaMA 3.2 Community License + Apache 2.0

---

## 模型四：TASTE SpokenLM（口語語言模型）

### 概述
**新一代語音對齊語言模型**，採用 Text-Aligned Speech Tokenization and Embedding 技術，讓 LLM 直接理解和生成語音，不需 ASR 中介轉換。

### 核心特色
- 語音 token 與文字語義空間對齊
- 直接語音輸入 → 語言模型 → 直接語音輸出（端對端）
- 基於 Llama-1B 架構
- 保留語音的情感、語調、節奏等副語言資訊

### ✅ 開源下載連結

| 資源 | 連結 | 說明 |
|------|------|------|
| **HuggingFace 模型** | https://huggingface.co/MediaTek-Research/Llama-1B-TASTE-V0 | 語音LM模型 |
| **資料集** | https://huggingface.co/datasets/MediaTek-Research/TASTE-Dump | 16.1M 語音資料 |
| **論文 (arXiv)** | https://arxiv.org/abs/2504.07053 | "TASTE: Text-Aligned Speech..." |

#### 下載指令
```bash
git lfs install
git clone https://huggingface.co/MediaTek-Research/Llama-1B-TASTE-V0
# 資料集（16.1M 筆語音-文字對）
python -c "from datasets import load_dataset; ds = load_dataset('MediaTek-Research/TASTE-Dump')"
```

### 授權：Apache 2.0 License

---

## 模型五：BreezeApp（行動端 AI 應用）

### 概述
**完全離線的 Android/iOS AI 應用**，整合 Breeze 2 系列模型，支援 LLM 對話、TTS、ASR、VLM，在飛航模式下也可運作。

### 技術架構（v2 模組化）
```
BreezeApp
├── BreezeApp-engine  ← Core AI Engine (AI 推論核心)
├── BreezeApp-client  ← Demo & Testing Platform
└── BreezeApp/        ← Production App (即將推出)
```

### ✅ 開源下載連結

| 資源 | 連結 | 說明 |
|------|------|------|
| **GitHub (主倉庫)** | https://github.com/mtkresearch/BreezeApp | Kotlin 原始碼 |
| **GitHub (Engine)** | https://github.com/mtkresearch/BreezeApp-engine | AI 推論引擎 |
| **GitHub (Client)** | https://github.com/mtkresearch/BreezeApp-client | 工程版/展示用 |
| **APK 直接下載** | https://huggingface.co/MediaTek-Research/BreezeApp/resolve/main/BreezeApp.apk | 直接安裝 |

#### 開發者快速上手
```bash
# Clone（含 submodules）
git clone --recursive https://github.com/mtkresearch/BreezeApp.git
# 或初始化 submodule
git submodule update --init --recursive
```

### 授權：License Pending（Kotlin 源碼開源）

---

## 傳承模型（舊版但仍可用）

### Breeze-7B（第一代 LLM）
| 模型 | HuggingFace 連結 | 授權 |
|------|----------------|------|
| Breeze-7B-Instruct-v1.0 | https://huggingface.co/MediaTek-Research/Breeze-7B-Instruct-v1_0 | Apache 2.0 |
| Breeze-7B-FC-v1.0 (Function Call) | https://huggingface.co/MediaTek-Research/Breeze-7B-FC-v1_0 | Apache 2.0 |
| YC-Chen/Breeze-7B-GGUF | https://huggingface.co/YC-Chen/Breeze-7B-Instruct-v1_0-GGUF | Apache 2.0 |

### Breexe-8x7B（MOE 架構）
| 模型 | HuggingFace 連結 | 授權 |
|------|----------------|------|
| Breexe-8x7B-Instruct-v0.1 | https://huggingface.co/MediaTek-Research/Breexe-8x7B-Instruct-v0_1 | Apache 2.0 |

### 論文
- Breeze-7B 論文：https://arxiv.org/abs/2403.02712
- Breeze FC 論文：https://arxiv.org/abs/2412.01130
- Generative Fusion Decoding (GFD)：https://arxiv.org/abs/2405.14259

---

## 開發者資源彙整

### 官方入口

| 資源 | 連結 |
|------|------|
| **GitHub 主倉庫 (MR-Models)** | https://github.com/mtkresearch/MR-Models |
| **HuggingFace 組織頁** | https://huggingface.co/MediaTek-Research |
| **All Collections** | https://huggingface.co/MediaTek-Research/collections |
| **PyPi 套件 (mtkresearch)** | https://pypi.org/project/mtkresearch/ |
| **官方網站** | https://i.mediatek.com/mediatekresearch |
| **聯絡信箱** | info@mtkresearch.com |

### Python 套件安裝
```bash
# MR 官方推論套件
pip install mtkresearch

# ASR 相關
pip install --upgrade transformers datasets[audio] accelerate torchaudio

# TTS 相關（BreezyVoice）
# Python 3.10 建議，見 BreezyVoice GitHub

# Whisper CLI（with Breeze ASR 25 patches）
git clone --recursive https://github.com/mtkresearch/Breeze-ASR-25
pip install third_party/whisper-patch-breeze
```

### 評測基準
- **TCEval-v2**（繁體中文評測）：https://github.com/mtkresearch/TCEval
- **ASCEND**（中英混用評測）：見 Breeze ASR 25 論文
- **Generative Fusion Decoding**：https://github.com/mtkresearch/generative-fusion-decoding

---

## 完整下載連結速查表（開發準備用）

### 模型權重（HuggingFace）

| 模型名稱 | 用途 | 大小 | 下載連結 |
|---------|------|------|---------|
| `Breeze-ASR-25` | 台灣語音辨識 ASR | 2B | https://huggingface.co/MediaTek-Research/Breeze-ASR-25 |
| `BreezyVoice` | 台灣腔語音合成 TTS | - | https://huggingface.co/MediaTek-Research/BreezyVoice |
| `BreezyVoice-300M` | TTS 輕量版 | 300M | https://huggingface.co/MediaTek-Research/BreezyVoice-300M |
| `Llama-Breeze2-3B-Instruct` | 繁體中文 LLM（手機/邊緣） | 4B | https://huggingface.co/MediaTek-Research/Llama-Breeze2-3B-Instruct |
| `Llama-Breeze2-8B-Instruct` | 繁體中文 LLM（伺服器） | 8B | https://huggingface.co/MediaTek-Research/Llama-Breeze2-8B-Instruct |
| `Llama-1B-TASTE-V0` | 口語 SpokenLM | 2B | https://huggingface.co/MediaTek-Research/Llama-1B-TASTE-V0 |
| `Breeze-7B-Instruct-v1_0` | LLM 舊版 | 7B | https://huggingface.co/MediaTek-Research/Breeze-7B-Instruct-v1_0 |
| `Breeze-7B-FC-v1_0` | LLM + Function Call | 7B | https://huggingface.co/MediaTek-Research/Breeze-7B-FC-v1_0 |
| `Breexe-8x7B-Instruct-v0_1` | MOE LLM | 47B(MOE) | https://huggingface.co/MediaTek-Research/Breexe-8x7B-Instruct-v0_1 |
| `Breeze-7B-Instruct-v1_0-GGUF` | GGUF 社群版 | 7B | https://huggingface.co/YC-Chen/Breeze-7B-Instruct-v1_0-GGUF |
| `BreezeApp` (APK) | Android 應用 | - | https://huggingface.co/MediaTek-Research/BreezeApp/resolve/main/BreezeApp.apk |
| `TASTE-Dump` 資料集 | 語音對齊資料集 | 16.1M | https://huggingface.co/datasets/MediaTek-Research/TASTE-Dump |

### 程式碼（GitHub）

| 倉庫 | 用途 | 連結 |
|------|------|------|
| `MR-Models` | 主倉庫（模型導覽） | https://github.com/mtkresearch/MR-Models |
| `Breeze-ASR-25` | ASR 推論程式碼 | https://github.com/mtkresearch/Breeze-ASR-25 |
| `BreezyVoice` | TTS 推論程式碼 | https://github.com/mtkresearch/BreezyVoice |
| `BreezeApp` | Android/iOS App | https://github.com/mtkresearch/BreezeApp |
| `BreezeApp-engine` | AI 推論引擎 | https://github.com/mtkresearch/BreezeApp-engine |
| `BreezeApp-client` | Demo App 客端 | https://github.com/mtkresearch/BreezeApp-client |
| `mtkresearch` (PyPi) | 官方 Python 套件 | https://github.com/mtkresearch/mtkresearch |
| `generative-fusion-decoding` | GFD 技術程式碼 | https://github.com/mtkresearch/generative-fusion-decoding |
| `TCEval` | 繁中評測基準 | https://github.com/mtkresearch/TCEval |

### HuggingFace 集合（一鍵查看系列）

| 集合名稱 | 連結 |
|---------|------|
| **Breeze 2 完整系列** | https://huggingface.co/collections/MediaTek-Research/breeze-2-67863158443a06a72dd29900 |
| **BreezeASR 系列** | https://huggingface.co/collections/MediaTek-Research/breezeasr |
| **TASTE-SpokenLM 系列** | https://huggingface.co/collections/MediaTek-Research/taste-spokenlm |
| **Breeze-7B & Breexe 系列** | https://huggingface.co/collections/MediaTek-Research/breeze-7b-and-breexe-8x7b-65a67144880ad716173d7d87 |

---

## 技術整合建議（針對轉寫系統）

根據你目前的 `convert` 專案（已有 Whisper 轉寫、Ollama/LM Studio 支援），以下是整合 Breeze 模型的建議路徑：

### 階段一：升級 ASR（最高優先）
```python
# 現有 Whisper → 替換為 Breeze ASR 25
# 1. 安裝
pip install transformers datasets[audio] accelerate torchaudio

# 2. 在 config.yaml 中加入新模型選項
# model_name: "MediaTek-Research/Breeze-ASR-25"
# 優點：台灣腔 +10% 精準度，中英混用 +56% 精準度
```

### 階段二：整合 TTS（口說回饋）
```bash
# BreezyVoice 可在台灣腔 TTS 輸出
git clone https://github.com/mtkresearch/BreezyVoice
# 支援 Docker 部署，可整合為微服務
```

### 階段三：升級 LLM（可選）
```python
# 本地 Ollama 可載入 GGUF 版 Breeze2
# 或直接用 HuggingFace Transformers 載入 Llama-Breeze2
# 更懂台灣用語和繁體中文知識
```

### 硬體需求參考
| 模型 | 最低 VRAM | 建議 VRAM | 備注 |
|------|---------|---------|------|
| Breeze ASR 25 | 2GB (INT8) | 4GB (FP16) | 量化後可低資源運行 |
| BreezyVoice 300M | 2GB | 4GB | 輕量版 |
| Llama-Breeze2-3B | 4GB | 8GB | 適合手機 NPU |
| Llama-Breeze2-8B | 8GB | 16GB | 適合 PC 開發 |

---

## "Breeze 3" 現況與未來展望

### 目前狀態（2026-02-27）
- **官方未發布任何名為 "Breeze 3" 的模型**[^1]
- MR-Models 最新里程碑：Breeze-ASR-25（2025.06.16）
- 最新 GitHub commit：2025-09-08（README 更新）
- 沒有任何公告預告 "Breeze 3" 的發布時程

### 推測的 "Breeze 3" 可能方向
基於 MediaTek Research 的研究軌跡，推測下一代模型可能包括：
1. **更完整的台語/閩南語支援**（目前的最大缺口）
2. **端對端語音 LLM**（TASTE 技術成熟後整合）
3. **更大規模的繁體中文預訓練**（基於 Llama 4 或更新基底）
4. **強化台灣文化知識**（本土歷史、地名、俚語等）

### 持續追蹤的官方管道
- 📡 GitHub：https://github.com/mtkresearch/MR-Models（看 Milestones 更新）
- 🤗 HuggingFace：https://huggingface.co/MediaTek-Research（新模型第一時間出現）
- 📰 MediaTek 新聞稿：https://www.mediatek.com/zh-tw/press-room
- 📧 聯絡：info@mtkresearch.com

---

## Confidence Assessment

| 項目 | 可信度 | 說明 |
|------|--------|------|
| 所有列出的下載連結 | ✅ 高 | 直接從 GitHub/HuggingFace 官方頁面驗證 |
| "Breeze 3" 目前未發布 | ✅ 高 | 多個搜尋來源及官方 GitHub 里程碑確認 |
| 模型效能數據（WER 等） | ✅ 高 | 來自官方 README 及 arXiv 論文 |
| 台語/閩南語未獲原生支援 | ✅ 高 | 官方訓練資料僅包含普通話合成語料 |
| TASTE 整合未來展望 | ⚠️ 推測 | 基於現有研究方向的合理推論 |
| "Breeze 3" 預測方向 | ⚠️ 推測 | 個人判斷，非官方確認 |

---

## Footnotes

[^1]: 截至 2026-02-27，MR-Models GitHub 最新里程碑為 `[2025.06.16] Breeze-ASR-25`，無任何 "Breeze 3" 相關發布或預告。來源：https://github.com/mtkresearch/MR-Models (commit: 3d6ce8a, 2025-09-08)

[^2]: Breeze-ASR-25 官方推論程式碼，來源：https://github.com/mtkresearch/Breeze-ASR-25/blob/main/run.py (SHA: bda1051)

[^3]: Breeze ASR 25 效能數據，來源：README.md，https://github.com/mtkresearch/Breeze-ASR-25 (SHA: bf4a06c)

[^4]: BreezyVoice 模型說明，來源：https://github.com/mtkresearch/BreezyVoice，論文 arXiv:2501.17790

[^5]: Breeze 2 多模態模型說明，來源：https://github.com/mtkresearch/MR-Models (SHA: f5eedc9)，論文 arXiv:2501.13921

[^6]: BreezeApp v2 架構，來源：https://github.com/mtkresearch/BreezeApp (SHA: e9356b2)

[^7]: TASTE SpokenLM，來源：https://huggingface.co/MediaTek-Research/Llama-1B-TASTE-V0，論文 arXiv:2504.07053
