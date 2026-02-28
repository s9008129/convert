#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
會議轉錄工具核心模組

這個套件是「核心零件集合」，方便其他程式直接匯入：
- OllamaClient：負責和本地 LLM 溝通。
- WhisperTranscriber：負責把音訊轉成文字。
- MeetingSummarizer：負責把逐字稿整理成重點摘要。

流程說明：
- 其他程式由此統一匯入核心類別，串成「轉錄 → 摘要」的主要流程。

錯誤情境說明：
- 若底層服務連線失敗或模型不可用，會由各模組拋出對應錯誤，供上層顯示友善訊息。
"""

from .ollama_client import (
    OllamaClient,
    OllamaError,
    OllamaConnectionError,
    OllamaTimeoutError,
    OllamaModelError,
    create_client,
    quick_generate
)

from .whisper_transcriber import (
    WhisperTranscriber,
    TranscriptionResult,
    TranscriptionError,
    AudioFileNotFoundError,
    UnsupportedFormatError,
    transcribe_audio
)

from .summarizer import (
    MeetingSummarizer,
    SummaryResult,
    MarkdownFormatter,
    summarize_transcript,
    DEFAULT_SYSTEM_PROMPT,
    CONCISE_SYSTEM_PROMPT
)

__version__ = "1.0.0"
__all__ = [
    # 本地 LLM 連線與文字生成能力
    "OllamaClient",
    "OllamaError",
    "OllamaConnectionError", 
    "OllamaTimeoutError",
    "OllamaModelError",
    "create_client",
    "quick_generate",
    
    # 音訊轉文字（Whisper）相關能力
    "WhisperTranscriber",
    "TranscriptionResult",
    "TranscriptionError",
    "AudioFileNotFoundError",
    "UnsupportedFormatError",
    "transcribe_audio",
    
    # 逐字稿摘要整理能力
    "MeetingSummarizer",
    "SummaryResult",
    "MarkdownFormatter",
    "summarize_transcript",
    "DEFAULT_SYSTEM_PROMPT",
    "CONCISE_SYSTEM_PROMPT",
]
