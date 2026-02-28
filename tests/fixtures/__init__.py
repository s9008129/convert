#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
測試固定資料（fixtures）匯出入口。
統一提供常見會議逐字稿樣本，讓測試情境一致且可重現。

流程說明：
- 測試案例可直接從這裡拿到標準化逐字稿，不必各自重建資料。

錯誤情境說明：
- 若 fixture 欄位缺漏，相關測試會快速失敗，提醒補齊測試資料。
"""
from tests.fixtures.mock_transcripts import (
    MockTranscript,
    STANDARD_GOVERNMENT_MEETING,
    TECHNICAL_PROJECT_MEETING,
    COMPLEX_MEETING_WITH_MULTIPLE_ACTIONS,
    MEETING_WITH_AMBIGUOUS_INFO,
    VERY_SHORT_TRANSCRIPT,
    VERY_LONG_TRANSCRIPT,
    ALL_MOCK_TRANSCRIPTS,
)

__all__ = [
    'MockTranscript',
    'STANDARD_GOVERNMENT_MEETING',
    'TECHNICAL_PROJECT_MEETING',
    'COMPLEX_MEETING_WITH_MULTIPLE_ACTIONS',
    'MEETING_WITH_AMBIGUOUS_INFO',
    'VERY_SHORT_TRANSCRIPT',
    'VERY_LONG_TRANSCRIPT',
    'ALL_MOCK_TRANSCRIPTS',
]
