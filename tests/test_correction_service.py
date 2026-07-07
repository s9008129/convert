#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
語意校正機制測試（P1-2 確定性清理、P1-3 選擇性 LLM 校正、P1-4 同音驗證閘門）。
"""

import pytest

from backend.core.text_postprocess import (
    clean_transcript,
    contains_simplified_chinese,
    dedup_consecutive_sentences,
    remove_hallucination_lines,
    to_taiwan_traditional,
)
from backend.services.correction import (
    CorrectionReport,
    gate_correction,
    is_homophone_swap,
    transcript_correction_service,
)


# ---------------------------------------------------------------------------
# P1-4 同音驗證閘門
# ---------------------------------------------------------------------------

def test_homophone_swap_accepts_same_pinyin():
    assert is_homophone_swap("再", "在") is True
    assert is_homophone_swap("進成核", "陳核") is False  # 長度不同 → 拒絕
    assert is_homophone_swap("權責", "全責") is True


def test_homophone_swap_accepts_taiwan_accent_near_pairs():
    # 捲舌/平舌（zh/z）與 in/ing 常見混淆
    assert is_homophone_swap("紙", "子") is True
    assert is_homophone_swap("心", "星") is True


def test_homophone_swap_rejects_different_sounds():
    assert is_homophone_swap("會議", "餐廳") is False
    assert is_homophone_swap("核定", "廢止") is False


def test_gate_accepts_homophone_and_rejects_rewrite():
    original = "本案已經簽辦完成，後續在下週處理。"
    # LLM 修了「在→再」（同音，應接受）也擅自改寫了「完成→辦妥」（非同音，應退回）
    corrected = "本案已經簽辦辦妥，後續再下週處理。"

    gated, changes = gate_correction(original, corrected, max_change_ratio=0.5)

    assert "再下週" in gated          # 同音替換被接受
    assert "簽辦完成" in gated        # 非同音改寫被退回
    accepted = [c for c in changes if c.accepted]
    rejected = [c for c in changes if not c.accepted]
    assert len(accepted) == 1 and accepted[0].corrected == "再"
    assert any("退回" in c.reason for c in rejected)


def test_gate_discards_segment_when_change_ratio_exceeded():
    original = "今天開會討論年度預算編列事宜。"
    corrected = "本次會議針對明年度的預算規劃進行全面檢討與調整。"

    gated, changes = gate_correction(original, corrected, max_change_ratio=0.10)

    assert gated == original
    assert changes and changes[0].reason.startswith("改動比例")


def test_gate_rejects_insertions_and_deletions():
    original = "請資訊室辦理。"
    corrected = "請資訊室盡速確實辦理。"

    gated, _changes = gate_correction(original, corrected, max_change_ratio=0.9)

    assert gated == original


def test_gate_no_change_returns_original():
    original = "今天天氣很好。"
    gated, changes = gate_correction(original, original, max_change_ratio=0.1)
    assert gated == original
    assert changes == []


# ---------------------------------------------------------------------------
# P1-3 選擇性校正流程（LLM 以假引擎注入）
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_correct_transcript_applies_gated_fix(monkeypatch):
    from backend.core.config import settings

    monkeypatch.setattr(settings, "CORRECTION_SCOPE", "all")
    monkeypatch.setattr(settings, "CORRECTION_MAX_CHANGE_RATIO", 0.3)

    async def fake_generate(system_prompt, user_message):
        # 模擬 LLM 修正同音錯字：權益→權益（不變）、在→再
        segment = user_message.split("【待校正段落，只輸出此段校正結果】\n")[-1]
        return segment.replace("在說一次", "再說一次")

    transcript = "主席表示這個議題在說一次。請各單位確認。"
    corrected, report = await transcript_correction_service.correct_transcript(transcript, fake_generate)

    assert "再說一次" in corrected
    assert report.segments_total >= 1
    assert any(change.accepted for change in report.changes)
    assert "再說一次" in report.to_markdown() or "再" in report.to_markdown()


@pytest.mark.asyncio
async def test_correct_transcript_survives_llm_failure(monkeypatch):
    from backend.core.config import settings

    monkeypatch.setattr(settings, "CORRECTION_SCOPE", "all")

    async def broken_generate(system_prompt, user_message):
        raise RuntimeError("Ollama 不可用")

    transcript = "主席裁示照案通過。"
    corrected, report = await transcript_correction_service.correct_transcript(transcript, broken_generate)

    assert corrected == transcript
    assert report.error is not None


# ---------------------------------------------------------------------------
# P1-2 確定性清理層
# ---------------------------------------------------------------------------

def test_remove_hallucination_lines():
    text = "會議開始。請訂閱我們的頻道 謝謝觀看\n下週繼續討論。字幕由 Amara.org 社群提供"
    cleaned, removed = remove_hallucination_lines(text)
    assert removed >= 2
    assert "請訂閱" not in cleaned
    assert "Amara" not in cleaned
    assert "會議開始。" in cleaned
    assert "下週繼續討論。" in cleaned


def test_dedup_consecutive_sentences():
    text = "本案照案通過。本案照案通過。本案照案通過。散會。"
    cleaned, removed = dedup_consecutive_sentences(text)
    assert removed == 2
    assert cleaned.count("本案照案通過。") == 1
    assert "散會。" in cleaned


def test_simplified_detection_and_conversion():
    assert contains_simplified_chinese("这个会议记录") is True
    assert contains_simplified_chinese("這個會議紀錄") is False
    converted = to_taiwan_traditional("这个会议很重要")
    assert "這個會議" in converted


def test_clean_transcript_pipeline():
    text = "这个案子已经核定。請訂閱我們的頻道"
    cleaned, stats = clean_transcript(text)
    assert "這個案子" in cleaned
    assert "請訂閱" not in cleaned
    assert stats["opencc"] is True
    assert stats["hallucinations_removed"] >= 1


def test_correction_report_markdown_empty():
    report = CorrectionReport()
    assert "未修改" in report.to_markdown()


@pytest.mark.asyncio
async def test_split_segments_handles_punctuationless_asr_transcript(monkeypatch):
    """faster-whisper 逐字稿常無標點；分段器必須仍能切出 max_chars 內的段落。"""
    from backend.core.config import settings

    monkeypatch.setattr(settings, "CORRECTION_MAX_SEGMENT_CHARS", 100)
    transcript = " ".join(["這是一句沒有標點的話"] * 50)  # 550+ 字元、無句號

    segments = transcript_correction_service._split_segments(transcript)

    assert len(segments) > 1
    assert all(len(seg) <= 100 for seg in segments)
    assert "".join(segments) == transcript  # 重組必須與原文完全一致


@pytest.mark.asyncio
async def test_split_segments_hard_splits_no_whitespace(monkeypatch):
    from backend.core.config import settings

    monkeypatch.setattr(settings, "CORRECTION_MAX_SEGMENT_CHARS", 50)
    transcript = "無標點也無空白" * 30  # 210 字元連續字串

    segments = transcript_correction_service._split_segments(transcript)

    assert all(len(seg) <= 50 for seg in segments)
    assert "".join(segments) == transcript
