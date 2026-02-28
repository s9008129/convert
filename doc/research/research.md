## **3\. 台灣繁體中文語境的深度解析與解決方案**

台灣的語言環境具有高度的特殊性，單純使用針對「標準普通話」（Standard Mandarin）訓練的模型，往往無法滿足在地化的精確度要求。

### **3.1 語言學挑戰：語碼轉換與在地化詞彙**

台灣日常口語中最顯著的特徵是 語碼轉換（Code-Switching），即在中文句子中自然地嵌入英文單詞或片語（例如：「幫我 update 一下那個 file，然後 send 給 client」）。  
通用模型如Whisper Large V3在處理此類語句時，常出現以下幾種失效模式：

1. **強行音譯：** 將 "update" 轉寫為 "阿普得特" 或無意義的中文同音字。  
2. **語言識別錯誤：** 模型在偵測到英文單詞後，錯誤地將整句標記為英文，導致中文部分被翻譯或忽略。  
3. **語意斷裂：** 因切換語言導致上下文預測機率驟降，產生幻覺或重複 10。

此外，台灣特有的詞彙（如「軟體」vs 中國用語「軟件」、「計程車」vs「出租車」、「印表機」vs「打印機」）也是檢驗模型在地化能力的關鍵指標。

### **3.2 最佳實踐：MediaTek Breeze-ASR-25 (Twister)**

針對上述痛點，MediaTek Research（聯發科研究團隊）在2025年中發布了 **Breeze-ASR-25**（代號 Twister），這是目前針對台灣繁體中文與中英混用場景的最佳實踐模型 11。

#### **3.2.1 自修正框架 (Self-Refining Framework) 的技術突破**

Breeze-ASR-25 的核心優勢並非僅來自模型架構（基於Whisper Large V2微調），而在於其創新的數據生成策略。由於高質量的台灣中英混用標註數據極其稀缺，研究團隊開發了一套 **自修正框架**：

1. **合成數據生成：** 利用高保真度的TTS系統 **BreezyVoice**，將大量包含中英夾雜文本的語料庫轉換為語音。BreezyVoice 本身經過台灣口音與多音字處理的優化，能夠生成極其逼真的本地口音 13。  
2. **模擬真實語境：** 在合成過程中，刻意模擬了句內（Intra-sentential）與句間（Inter-sentential）的語言切換，創造了約10,000小時的合成訓練數據 14。  
3. **閉環優化：** 利用初步訓練的模型對真實無標註語音進行偽標籤（Pseudo-labeling），經過過濾後再回饋到訓練中，形成正向循環。

#### **3.2.2 性能指標與對比**

根據 ASCEND 基準測試（台灣中英混用數據集），Breeze-ASR-25 展現了壓倒性的優勢：

* **混合語言錯誤率：** 相比 Whisper Large V2 基線，錯誤率降低了 **22.01%**。  
* **純中文錯誤率：** 降低了 **8.29%**。  
* 純英文錯誤率： 降低了 2.63%。  
  這項數據證實了利用合成數據進行在地化適配的有效性，使其成為目前處理台灣口語最穩健的選擇 10。

## **4\. 關鍵模型技術規格與基準測試對比**

為了協助工程師進行選型，以下表格詳細對比了截至2025年末四大主流模型的關鍵技術規格與性能指標。

### **4.1 模型規格對比表**

| 模型名稱 | 架構類型 | 參數量 | 主要優勢 | 台灣繁中適配性 | 推薦推論引擎 | VRAM 需求 (FP16/INT8) |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **Breeze-ASR-25** | Transformer (Whisper V2) | 1.55B | 中英混用 SOTA | **極高 (專項優化)** | Faster-Whisper | \~4GB / \~2GB |
| **Whisper V3 Turbo** | Transformer (4-layer Decoder) | 809M | 速度與通用性平衡 | 中 | Faster-Whisper / Whisper.cpp | \~2GB / \~1GB |
| **FireRedASR-LLM** | Encoder-Adapter-LLM | 8.3B | 純中文準確度王者 | 高 (泛化能力強) | PyTorch / vLLM | \~16GB / \~9GB |
| **SenseVoice-Small** | Non-Autoregressive | \~300M | 極致低延遲 (70ms) | 中 | Sherpa-ONNX | \<1GB / \<512MB |

### **4.2 性能基準測試 (CER/WER)**

數據來源整合自各大模型發布之技術報告與 Hugging Face Leaderboard 5。

| 測試集 (Dataset) | Breeze-ASR-25 (CER%) | Whisper Large V3 (CER%) | FireRedASR-LLM (CER%) |
| :---- | :---- | :---- | :---- |
| **ASCEND (台灣中英混用)** | **16.38** | 25.13 | N/A (未針對此優化) |
| **AISHELL-1 (標準中文)** | 2.5% (估計) | 5.14 | **0.76** |
| **CommonVoice zh-TW** | **低** | 中 | 低 |
| **KeSpeech (方言)** | N/A | 6.70 | **3.56** |

**深度解讀：**

* 若應用場景為**台灣會議記錄、日常對話、Podcast轉寫**，**Breeze-ASR-25** 是唯一能有效處理中英夾雜的選擇。  
* 若應用場景為**醫療聽寫、法律文件**（多為純中文且要求極高準確度），**FireRedASR-LLM** 憑藉其LLM的語意修正能力，能提供更低的錯誤率。  
* 若應用場景為**手機App語音輸入**，**SenseVoice-Small** 或量化後的 **Whisper Turbo** 是唯二可行的方案。

## **5\. 本地端推論引擎與量化策略深度指南**

在選定模型後，如何「高效地運行」是軟體工程師面臨的下一個挑戰。2025年的推論生態系已高度成熟，Python與C++路徑均有最佳實踐。

### **5.1 Python 生態系：Faster-Whisper 與 CTranslate2**

對於伺服器端部署（Server-side Deployment），**Faster-Whisper** 庫是目前的黃金標準。它底層依賴 **CTranslate2** 推論引擎，該引擎針對 Transformer 模型進行了深度優化，包括權重矩陣預重排、層融合（Layer Fusion）以及動態批處理（Dynamic Batching）18。

* Breeze-ASR-25 的轉換與載入：  
  由於 Breeze 基於 Whisper 架構，它完全兼容 CTranslate2。開發者需先將 Hugging Face 的 PyTorch 模型權重轉換為 CTranslate2 格式：  
  Bash  
  ct2-transformers-converter \--model MediaTek-Research/Breeze-ASR-25 \--output\_dir breeze-ct2-int8 \--quantization int8\_float16

  此步驟中的 \--quantization int8\_float16 參數至關重要，它會在模型權重加載時將其量化為 INT8，但在計算時使用 FP16（在 GPU 上）或 INT16（在 CPU 上），從而在幾乎不損失精度的情況下減少 50% 以上的 VRAM 佔用並提升 4 倍推論速度 19。

## **6\. 生產環境硬化 (Production Hardening)**

在實驗室環境中跑通模型只是第一步，在真實世界的髒數據（Noisy Data）中保持穩定才是關鍵。以下是針對台灣繁體中文環境的生產級優化策略。

### **6.1 幻覺抑制 (Hallucination Mitigation)**

Whisper 系列模型最著名的缺陷是「幻覺」。當輸入音訊為靜音、純背景音樂或噪音時，模型傾向於強行生成文字，常見的幻覺包括重複上一句內容，或輸出訓練數據中的字幕版權宣告（如 "Subtitles by Amara.org", "Thank you for watching"）28。  
解決方案：基於 VAD 的預處理管道  
單純依賴模型的 no\_speech\_threshold 參數往往不夠可靠。業界的最佳實踐是引入獨立的 語音活動檢測（Voice Activity Detection, VAD） 模組。

1. **Silero VAD v5：** 相比 v4 版本，v5 在抗噪聲能力上有顯著提升，且對細微語音的捕捉更為敏銳。  
2. **管道設計：**  
   * **Step 1:** 音訊輸入 \-\> Silero VAD v5 掃描。  
   * **Step 2:** 切割出僅包含人聲的時間片段。  
   * **Step 3:** 僅將人聲片段送入 Breeze-ASR-25 進行轉寫。  
   * Step 4: 將轉寫結果按時間戳拼回。  
     此方案能從根本上杜絕靜音段的幻覺生成，並顯著提升整體處理速度（因為跳過了無效音訊）30。

### **6.2 時間戳記精準化 (Timestamp Alignment)**

Breeze-ASR-25 雖然優化了時間戳記，但在生成字幕（SRT/VTT）時，仍可能出現單詞級別的漂移。

* **強制對齊 (Forced Alignment)：** 建議在 ASR 轉寫後，串接 **WhisperX** 工具。WhisperX 利用 Wav2Vec2 模型將轉寫出的文本與音訊進行音素級（Phoneme-level）的強制對齊，能將時間戳精度從秒級提升至毫秒級，這對於製作精確的卡拉OK字幕或會議逐字稿至關重要 32。

### **6.3 提示工程 (Prompt Engineering)**

對於繁體中文，適當的 **Prompting** 可以引導模型進入正確的語言模式。

* **Prefix Prompt:** 在推論時輸入 initial\_prompt="以下是台灣繁體中文的會議記錄。"。這能有效提示模型使用台灣習慣用語（如「資訊」而非「信息」），並減少簡體字輸出的機率 34。  
* **熱詞增強:** 雖然Whisper架構不直接支援傳統的熱詞（Hotwords）加權，但在 Prompt 中加入關鍵詞列表（如公司名、專有名詞）往往能起到類似的效果。

## **8\. 結論與策略建議**

綜合 2025 年 12 月的技術現狀，對於要求「理解台灣繁體中文語意並完整轉出文字」的開發任務，我們提出以下策略建議：

1. **核心模型選擇：** **MediaTek Breeze-ASR-25** 是無可爭議的首選。它透過合成數據自修正技術，解決了Whisper在台灣特有中英混用場景下的痛點，是目前市面上唯一真正「懂」台灣口語的開源模型。  
2. **部署架構：** 優先採用 **Faster-Whisper (CTranslate2)** 配合 **INT8 量化**。這在保證精度的前提下，最大化了硬體利用率。  
3. **品質保證：** 必須構建包含 **Silero VAD v5** 的預處理管道以消除幻覺，並視需求引入 **WhisperX** 進行時間戳對齊。  
4. **備用方案：** 對於對準確率有極端要求且無中英混用的場景（如純中文古籍錄入），可考慮 **FireRedASR-LLM**；對於極致低延遲的語音控制，則轉向 **SenseVoice-Small**。

隨著 Breeze-ASR 等在地化模型的出現，2025 年標誌著 ASR 技術從「通用大一統」走向「精緻在地化」的轉折點。掌握這些工具與架構，將使開發者能夠構建出真正符合台灣使用者期待的頂級語音應用。

#### **Works cited**

1. Multilingual Whisper Large-v3 Turbo \- Nvidia NGC, accessed December 18, 2025, [https://catalog.ngc.nvidia.com/orgs/nvidia/teams/riva/models/whisper\_large\_turbo](https://catalog.ngc.nvidia.com/orgs/nvidia/teams/riva/models/whisper_large_turbo)  
2. openai/whisper-large-v3 \- Hugging Face, accessed December 18, 2025, [https://huggingface.co/openai/whisper-large-v3](https://huggingface.co/openai/whisper-large-v3)  
3. Open AI's new Whisper Turbo model runs 5.4 times faster LOCALLY than Whisper V3 Large on M1 Pro : r/LocalLLaMA \- Reddit, accessed December 18, 2025, [https://www.reddit.com/r/LocalLLaMA/comments/1fvb83n/open\_ais\_new\_whisper\_turbo\_model\_runs\_54\_times/](https://www.reddit.com/r/LocalLLaMA/comments/1fvb83n/open_ais_new_whisper_turbo_model_runs_54_times/)  
4. Benchmark faster whisper turbo v3 · Issue \#1030 \- GitHub, accessed December 18, 2025, [https://github.com/SYSTRAN/faster-whisper/issues/1030](https://github.com/SYSTRAN/faster-whisper/issues/1030)  
5. FireRedTeam/FireRedASR: Open-source industrial-grade ASR models supporting Mandarin, Chinese dialects and English, achieving a new SOTA on public Mandarin ASR benchmarks, while also offering outstanding singing lyrics recognition capability. \- GitHub, accessed December 18, 2025, [https://github.com/FireRedTeam/FireRedASR](https://github.com/FireRedTeam/FireRedASR)  
6. \[2501.14350\] FireRedASR: Open-Source Industrial-Grade Mandarin Speech Recognition Models from Encoder-Decoder to LLM Integration \- arXiv, accessed December 18, 2025, [https://arxiv.org/abs/2501.14350](https://arxiv.org/abs/2501.14350)  
7. \[Literature Review\] FireRedASR: Open-Source Industrial-Grade Mandarin Speech Recognition Models from Encoder-Decoder to LLM Integration \- Moonlight, accessed December 18, 2025, [https://www.themoonlight.io/en/review/fireredasr-open-source-industrial-grade-mandarin-speech-recognition-models-from-encoder-decoder-to-llm-integration](https://www.themoonlight.io/en/review/fireredasr-open-source-industrial-grade-mandarin-speech-recognition-models-from-encoder-decoder-to-llm-integration)  
8. FunAudioLLM/SenseVoice: Multilingual Voice Understanding Model \- GitHub, accessed December 18, 2025, [https://github.com/FunAudioLLM/SenseVoice](https://github.com/FunAudioLLM/SenseVoice)  
9. FunAudioLLM/SenseVoiceSmall \- Hugging Face, accessed December 18, 2025, [https://huggingface.co/FunAudioLLM/SenseVoiceSmall](https://huggingface.co/FunAudioLLM/SenseVoiceSmall)  
10. MediaTek-Research/Breeze-ASR-25 · Hugging Face, accessed December 18, 2025, [https://huggingface.co/MediaTek-Research/Breeze-ASR-25](https://huggingface.co/MediaTek-Research/Breeze-ASR-25)  
11. improve · MediaTek-Research/Breeze-ASR-25 at 3e47c29 \- Hugging Face, accessed December 18, 2025, [https://huggingface.co/MediaTek-Research/Breeze-ASR-25/commit/3e47c29c8150ce2b47f9474610582693c7246fba](https://huggingface.co/MediaTek-Research/Breeze-ASR-25/commit/3e47c29c8150ce2b47f9474610582693c7246fba)  
12. README.md · MediaTek-Research/Breeze-ASR-25 at main \- Hugging Face, accessed December 18, 2025, [https://huggingface.co/MediaTek-Research/Breeze-ASR-25/blame/main/README.md](https://huggingface.co/MediaTek-Research/Breeze-ASR-25/blame/main/README.md)  
13. \[2501.17790\] BreezyVoice: Adapting TTS for Taiwanese Mandarin with Enhanced Polyphone Disambiguation \-- Challenges and Insights \- arXiv, accessed December 18, 2025, [https://arxiv.org/abs/2501.17790](https://arxiv.org/abs/2501.17790)  
14. A Self-Refining Framework for Enhancing ASR Using TTS-Synthesized Data \- arXiv, accessed December 18, 2025, [https://arxiv.org/html/2506.11130v1](https://arxiv.org/html/2506.11130v1)  
15. JacobLinCool/whisper-large-v3-turbo-zh-TW-clean-1 · Hugging Face, accessed December 18, 2025, [https://huggingface.co/JacobLinCool/whisper-large-v3-turbo-zh-TW-clean-1](https://huggingface.co/JacobLinCool/whisper-large-v3-turbo-zh-TW-clean-1)  
16. JacobLinCool/whisper-large-v3-turbo-common\_voice\_19\_0-zh-TW \- Hugging Face, accessed December 18, 2025, [https://huggingface.co/JacobLinCool/whisper-large-v3-turbo-common\_voice\_19\_0-zh-TW](https://huggingface.co/JacobLinCool/whisper-large-v3-turbo-common_voice_19_0-zh-TW)  
17. MediaTek releases ASR model tuned for Taiwanese Mandarin \- digitimes, accessed December 18, 2025, [https://www.digitimes.com/news/a20250701PD240/mediatek-ai-language-model-openai-taiwan.html](https://www.digitimes.com/news/a20250701PD240/mediatek-ai-language-model-openai-taiwan.html)  
18. OpenNMT/CTranslate2: Fast inference engine for Transformer models \- GitHub, accessed December 18, 2025, [https://github.com/OpenNMT/CTranslate2](https://github.com/OpenNMT/CTranslate2)  
19. Faster Whisper transcription with CTranslate2 \- GitHub, accessed December 18, 2025, [https://github.com/SYSTRAN/faster-whisper](https://github.com/SYSTRAN/faster-whisper)  
20. SoybeanMilk/faster-whisper-Breeze-ASR-25 \- Hugging Face, accessed December 18, 2025, [https://huggingface.co/SoybeanMilk/faster-whisper-Breeze-ASR-25](https://huggingface.co/SoybeanMilk/faster-whisper-Breeze-ASR-25)  
21. ggml-org/whisper.cpp: Port of OpenAI's Whisper model in C/C++ \- GitHub, accessed December 18, 2025, [https://github.com/ggml-org/whisper.cpp](https://github.com/ggml-org/whisper.cpp)  
22. Overview of GGUF quantization methods : r/LocalLLaMA \- Reddit, accessed December 18, 2025, [https://www.reddit.com/r/LocalLLaMA/comments/1ba55rj/overview\_of\_gguf\_quantization\_methods/](https://www.reddit.com/r/LocalLLaMA/comments/1ba55rj/overview_of_gguf_quantization_methods/)  
23. How to Run Large Language Models Locally: Hardware, VRAM, and Setup Explained, accessed December 18, 2025, [https://medium.com/data-science-in-your-pocket/how-to-run-large-language-models-locally-hardware-vram-and-setup-explained-7caec36ef181](https://medium.com/data-science-in-your-pocket/how-to-run-large-language-models-locally-hardware-vram-and-setup-explained-7caec36ef181)  
24. Add support for SenseVoice model, which is supposedly much better than whisper · mozilla-ai llamafile · Discussion \#545 \- GitHub, accessed December 18, 2025, [https://github.com/Mozilla-Ocho/llamafile/discussions/545](https://github.com/Mozilla-Ocho/llamafile/discussions/545)  
25. Export SenseVoice to sherpa-onnx \- GitHub Pages, accessed December 18, 2025, [https://k2-fsa.github.io/sherpa/onnx/sense-voice/export.html](https://k2-fsa.github.io/sherpa/onnx/sense-voice/export.html)  
26. SenseVoice — sherpa 1.3 documentation, accessed December 18, 2025, [https://k2-fsa.github.io/sherpa/onnx/sense-voice/index.html](https://k2-fsa.github.io/sherpa/onnx/sense-voice/index.html)  
27. sherpa-onnx \- Browse /asr-models-qnn-binary at SourceForge.net, accessed December 18, 2025, [https://sourceforge.net/projects/sherpa-onnx.mirror/files/asr-models-qnn-binary/](https://sourceforge.net/projects/sherpa-onnx.mirror/files/asr-models-qnn-binary/)  
28. Solutions to Repeated Output Issues with Whisper \- Memo AI, accessed December 18, 2025, [https://memo.ac/blog/whisper-hallucinations](https://memo.ac/blog/whisper-hallucinations)  
29. Careless Whisper: Speech-to-Text Hallucination Harms \- arXiv, accessed December 18, 2025, [https://arxiv.org/html/2402.08021v2](https://arxiv.org/html/2402.08021v2)  
30. Audio Pre-Processings For Better Results in the Transcription Pipeline \- Medium, accessed December 18, 2025, [https://medium.com/@developerjo0517/audio-pre-processings-for-better-results-in-the-transcription-pipeline-bab1e8f63334](https://medium.com/@developerjo0517/audio-pre-processings-for-better-results-in-the-transcription-pipeline-bab1e8f63334)  
31. 1.0.3 VAD v5 is much worse than 1.0.2 VAD v4 · Issue \#934 · SYSTRAN/faster-whisper \- GitHub, accessed December 18, 2025, [https://github.com/SYSTRAN/faster-whisper/issues/934](https://github.com/SYSTRAN/faster-whisper/issues/934)  
32. WhisperX \- Word-level Timestamps with Whisper \- Subtitles Transcription \- YouTube, accessed December 18, 2025, [https://www.youtube.com/watch?v=KtAFU\_xeHr4](https://www.youtube.com/watch?v=KtAFU_xeHr4)  
33. WhisperX: Automatic Speech Recognition with Word-level Timestamps (& Diarization) \- GitHub, accessed December 18, 2025, [https://github.com/m-bain/whisperX](https://github.com/m-bain/whisperX)  
34. How to avoid Hallucinations in Whisper transcriptions? \- OpenAI Developer Community, accessed December 18, 2025, [https://community.openai.com/t/how-to-avoid-hallucinations-in-whisper-transcriptions/125300?page=2](https://community.openai.com/t/how-to-avoid-hallucinations-in-whisper-transcriptions/125300?page=2)  
35. Dual 4090 VS Dual 3090 VS single 4090 \- distributed \- PyTorch Forums, accessed December 18, 2025, [https://discuss.pytorch.org/t/dual-4090-vs-dual-3090-vs-single-4090/192681](https://discuss.pytorch.org/t/dual-4090-vs-dual-3090-vs-single-4090/192681)  
36. FireRedASR-LLM-L CUDA out of memory \#32 \- GitHub, accessed December 18, 2025, [https://github.com/FireRedTeam/FireRedASR/issues/32](https://github.com/FireRedTeam/FireRedASR/issues/32)  
37. LM Studio VRAM Requirements for Local LLMs | LocalLLM.in, accessed December 18, 2025, [https://localllm.in/blog/lm-studio-vram-requirements-for-local-llms](https://localllm.in/blog/lm-studio-vram-requirements-for-local-llms)

