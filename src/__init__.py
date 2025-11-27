#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
會議轉錄工具核心模組

提供：
- OllamaClient: 本地 LLM 客戶端
- WhisperTranscriber: 語音轉錄器
- MeetingSummarizer: 會議摘要生成器
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
    # Ollama
    "OllamaClient",
    "OllamaError",
    "OllamaConnectionError", 
    "OllamaTimeoutError",
    "OllamaModelError",
    "create_client",
    "quick_generate",
    
    # Whisper
    "WhisperTranscriber",
    "TranscriptionResult",
    "TranscriptionError",
    "AudioFileNotFoundError",
    "UnsupportedFormatError",
    "transcribe_audio",
    
    # Summarizer
    "MeetingSummarizer",
    "SummaryResult",
    "MarkdownFormatter",
    "summarize_transcript",
    "DEFAULT_SYSTEM_PROMPT",
    "CONCISE_SYSTEM_PROMPT",
]
