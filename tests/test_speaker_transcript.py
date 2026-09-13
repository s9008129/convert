#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""發言者標註逐字稿建構器測試（T20260913-1900-01）。

純函式測試：以假資料驗證時間軸對位、chunk→speaker 對應、標籤格式
（「發言者N」）與 fail-soft 行為（空輸入／無時間戳一律不拋例外）。
不載入任何模型、不下載檔案、不使用 GPU，全部 deterministic。
"""

from __future__ import annotations

import re

import pytest

from backend.services.diarization import DiarizationTurn
from backend.services.speaker_transcript import (
    SPEAKER_NOTE,
    AsrPiece,
    _allocate_text,
    align_transcript,
    build_speaker_labeled_transcript,
    format_timestamp,
    join_text,
    split_segment_by_turns,
)

_UTTERANCE_LINE_RE = re.compile(r"^\[\d{2}:\d{2}:\d{2}-\d{2}:\d{2}:\d{2}\] 發言者\d+：")
_SPEAKER_LABEL_RE = re.compile(r"^發言者\d+$")


def _two_speaker_scenario():
    """7 號分群發言 12 秒、3 號分群發言 5 秒（分群編號刻意不從 0 開始）。"""

    segments = [
        AsrPiece(0.0, 12.0, "主席開場報告事項"),
        AsrPiece(20.0, 25.0, "同仁提問內容"),
    ]
    turns = [DiarizationTurn(0.0, 12.0, 7), DiarizationTurn(20.0, 25.0, 3)]
    return segments, turns


# ---------------------------------------------------------------------------
# 基礎格式化
# ---------------------------------------------------------------------------


def test_format_timestamp_floors_and_clamps_negative():
    assert format_timestamp(0) == "00:00:00"
    assert format_timestamp(59.9) == "00:00:59"
    assert format_timestamp(3661.9) == "01:01:01"
    assert format_timestamp(-5) == "00:00:00"


def test_join_text_keeps_cjk_unspaced_and_separates_ascii():
    assert join_text("你好", "世界") == "你好世界"
    assert join_text("你好，", "世界") == "你好，世界"
    assert join_text("hello", "world") == "hello world"
    assert join_text("你好", "hello") == "你好 hello"
    assert join_text("hello", "你好") == "hello 你好"
    assert join_text("", "只有右邊") == "只有右邊"
    assert join_text("只有左邊", "") == "只有左邊"


# ---------------------------------------------------------------------------
# 文字分配（不丟字）
# ---------------------------------------------------------------------------


def test_allocate_text_is_lossless_and_weighted():
    pieces = _allocate_text("abcdefghij", [3, 1])

    assert "".join(pieces) == "abcdefghij"
    assert pieces == ["abcdefgh", "ij"]


def test_allocate_text_edge_inputs():
    assert _allocate_text("", [1, 2]) == ["", ""]
    assert _allocate_text("abc", [0, 0]) == ["", ""]
    assert _allocate_text("abc", [1, 1, 1]) == ["a", "b", "c"]


# ---------------------------------------------------------------------------
# chunk → speaker 對應
# ---------------------------------------------------------------------------


def test_split_segment_assigns_whole_chunk_to_dominant_speaker():
    segment = AsrPiece(0.0, 10.0, "甲乙丙丁戊己庚辛壬癸")
    turns = [DiarizationTurn(0.0, 8.0, 1), DiarizationTurn(8.0, 10.0, 2)]

    pieces = split_segment_by_turns(segment, turns)

    assert len(pieces) == 1
    assert pieces[0].speaker == 1
    assert pieces[0].text == segment.text
    assert (pieces[0].start, pieces[0].end) == (0.0, 10.0)


def test_split_segment_splits_text_when_no_single_speaker_dominates():
    segment = AsrPiece(0.0, 10.0, "abcdefghij")
    turns = [DiarizationTurn(0.0, 5.0, 1), DiarizationTurn(5.0, 10.0, 2)]

    pieces = split_segment_by_turns(segment, turns)

    assert [(p.speaker, p.text) for p in pieces] == [(1, "abcde"), (2, "fghij")]
    assert pieces[0].start == 0.0
    assert pieces[1].end == 10.0
    assert "".join(p.text for p in pieces) == segment.text


def test_split_segment_ignores_negligible_overlap_speaker():
    segment = AsrPiece(0.0, 10.0, "abcdefghij")
    turns = [
        DiarizationTurn(0.0, 4.0, 1),
        DiarizationTurn(4.0, 4.2, 2),  # 重疊 0.2 秒 < min_overlap_seconds，不成段
        DiarizationTurn(4.2, 10.0, 3),
    ]

    pieces = split_segment_by_turns(segment, turns)

    assert [p.speaker for p in pieces] == [1, 3]
    assert "".join(p.text for p in pieces) == segment.text


def test_split_segment_keeps_short_text_or_brief_chunk_whole():
    turns = [DiarizationTurn(0.0, 5.0, 1), DiarizationTurn(5.0, 10.0, 2)]

    short_text = split_segment_by_turns(AsrPiece(0.0, 10.0, "好"), turns)
    assert [(p.speaker, p.text) for p in short_text] == [(1, "好")]

    short_span = split_segment_by_turns(AsrPiece(0.0, 0.5, "abcdefgh"), turns)
    assert [(p.speaker, p.text) for p in short_span] == [(1, "abcdefgh")]


def test_split_segment_without_overlap_uses_nearest_speaker():
    segment = AsrPiece(100.0, 102.0, "沒有重疊的段落")
    turns = [DiarizationTurn(0.0, 10.0, 3), DiarizationTurn(95.0, 99.0, 5)]

    pieces = split_segment_by_turns(segment, turns)

    assert [(p.speaker, p.text) for p in pieces] == [(5, "沒有重疊的段落")]


def test_zero_duration_segment_does_not_crash_and_still_gets_speaker():
    segment = AsrPiece(5.0, 5.0, "無長度")
    turns = [DiarizationTurn(0.0, 4.0, 1), DiarizationTurn(6.0, 10.0, 2)]

    pieces = split_segment_by_turns(segment, turns)

    assert len(pieces) == 1
    assert pieces[0].speaker in {1, 2}
    assert pieces[0].text == "無長度"


def test_split_segment_fail_soft_on_empty_inputs():
    assert split_segment_by_turns(AsrPiece(0.0, 1.0, "文字"), []) == []
    assert split_segment_by_turns(AsrPiece(0.0, 1.0, ""), [DiarizationTurn(0.0, 1.0, 1)]) == []


# ---------------------------------------------------------------------------
# 時間軸對位與合併
# ---------------------------------------------------------------------------


def test_align_transcript_merges_same_speaker_within_gap():
    segments = [
        AsrPiece(0.0, 2.0, "你好"),
        AsrPiece(3.5, 4.0, "早安"),  # 停頓 1.5 秒 = 門檻，仍合併
        AsrPiece(10.0, 12.0, "再見"),
    ]
    turns = [DiarizationTurn(0.0, 12.0, 1)]

    utterances = align_transcript(segments, turns, merge_gap=1.5)

    assert len(utterances) == 2
    assert utterances[0].text == "你好早安"
    assert (utterances[0].start, utterances[0].end) == (0.0, 4.0)
    assert utterances[1].text == "再見"


def test_align_transcript_keeps_speaker_changes_separate_without_gap():
    segments = [AsrPiece(0.0, 2.0, "甲"), AsrPiece(2.0, 4.0, "乙")]
    turns = [DiarizationTurn(0.0, 2.0, 1), DiarizationTurn(2.0, 4.0, 2)]

    utterances = align_transcript(segments, turns)

    assert [(u.speaker, u.text) for u in utterances] == [(1, "甲"), (2, "乙")]


def test_align_transcript_sorts_segments_and_drops_blank_text():
    segments = [
        AsrPiece(10.0, 12.0, "後段"),
        AsrPiece(0.0, 2.0, "前段"),
        AsrPiece(5.0, 6.0, "   "),
    ]
    turns = [DiarizationTurn(0.0, 12.0, 1)]

    utterances = align_transcript(segments, turns)

    assert [u.text for u in utterances] == ["前段", "後段"]


def test_align_transcript_maps_each_chunk_to_its_dominant_speaker():
    segments = [
        AsrPiece(0.0, 4.0, "第一段"),
        AsrPiece(4.0, 8.0, "第二段"),
        AsrPiece(8.0, 12.0, "第三段"),  # 6/4 秒重疊但太短（3 字）不拆分
    ]
    turns = [
        DiarizationTurn(0.0, 4.0, 10),
        DiarizationTurn(4.0, 8.0, 20),
        DiarizationTurn(8.0, 10.0, 10),
        DiarizationTurn(10.0, 12.0, 20),
    ]

    utterances = align_transcript(segments, turns)

    assert [(u.speaker, u.text) for u in utterances] == [
        (10, "第一段"),
        (20, "第二段"),
        (10, "第三段"),
    ]


def test_align_transcript_fail_soft_on_empty_inputs():
    turns = [DiarizationTurn(0.0, 1.0, 1)]

    assert align_transcript([], turns) == []
    assert align_transcript([AsrPiece(0.0, 1.0, "文字")], []) == []
    assert align_transcript([AsrPiece(0.0, 1.0, "   ")], turns) == []


# ---------------------------------------------------------------------------
# 帶標籤逐字稿組裝
# ---------------------------------------------------------------------------


def test_build_transcript_fail_soft_on_empty_or_timestampless_inputs():
    turns = [DiarizationTurn(0.0, 1.0, 1)]

    assert build_speaker_labeled_transcript([], turns) is None  # 無 ASR 片段
    # 有 ASR 時間戳但沒有分群結果
    assert build_speaker_labeled_transcript([AsrPiece(0.0, 1.0, "字")], []) is None
    assert build_speaker_labeled_transcript([AsrPiece(0.0, 1.0, "  ")], turns) is None  # 全空白


def test_labels_are_ranked_by_speaking_time_and_named_speaker_n():
    segments, turns = _two_speaker_scenario()

    result = build_speaker_labeled_transcript(segments, turns)

    assert result is not None
    assert result.speaker_labels == {7: "發言者1", 3: "發言者2"}
    assert result.speaker_count == 2
    assert [stat.label for stat in result.stats] == ["發言者1", "發言者2"]
    assert result.stats[0].seconds == pytest.approx(12.0)
    assert result.stats[0].share == pytest.approx(12.0 / 17.0)
    assert result.stats[0].utterance_count == 1
    assert result.stats[0].first_seen == 0.0
    assert all(_SPEAKER_LABEL_RE.match(label) for label in result.speaker_labels.values())


def test_label_tie_break_prefers_smaller_speaker_id():
    segments = [AsrPiece(0.0, 5.0, "先發言"), AsrPiece(10.0, 15.0, "後發言")]
    turns = [DiarizationTurn(0.0, 5.0, 4), DiarizationTurn(10.0, 15.0, 2)]

    result = build_speaker_labeled_transcript(segments, turns)

    assert result.speaker_labels == {2: "發言者1", 4: "發言者2"}


def test_labeled_text_contains_note_stats_and_timestamped_lines():
    segments, turns = _two_speaker_scenario()

    result = build_speaker_labeled_transcript(segments, turns)
    utterance_lines = [
        line for line in result.text.splitlines() if _UTTERANCE_LINE_RE.match(line)
    ]

    assert result.text.startswith(SPEAKER_NOTE)
    assert "【發言者統計】" in result.text
    assert utterance_lines == [
        "[00:00:00-00:00:12] 發言者1：主席開場報告事項",
        "[00:00:20-00:00:25] 發言者2：同仁提問內容",
    ]


def test_mid_segment_speaker_change_is_split_into_two_speakers():
    segment = AsrPiece(0.0, 10.0, "abcdefghij")
    turns = [DiarizationTurn(0.0, 5.0, 1), DiarizationTurn(5.0, 10.0, 2)]

    result = build_speaker_labeled_transcript([segment], turns)

    assert [utterance.speaker for utterance in result.utterances] == [1, 2]
    assert "".join(utterance.text for utterance in result.utterances) == "abcdefghij"
    assert "[00:00:00-00:00:05] 發言者1：abcde" in result.text
    assert "[00:00:05-00:00:10] 發言者2：fghij" in result.text


def test_metadata_records_alignment_parameters_and_utterance_count():
    segments, turns = _two_speaker_scenario()

    result = build_speaker_labeled_transcript(
        segments, turns, merge_gap=2.0, min_segment_coverage=0.5
    )

    assert result.metadata == {
        "merge_gap": 2.0,
        "min_segment_coverage": 0.5,
        "utterance_count": 2,
    }
