"""發言者標註逐字稿建構器（T20260913-1900-01）。

把兩份獨立來源合成一份「可讀、可稽核、可餵 LLM」的逐字稿：
1. ASR 片段（``start``/``end``/``text``；Apple SpeechAnalyzer 逐詞時間軸或
   Whisper 的 chunk 時間戳）
2. 說話者分離結果（``DiarizationTurn``；語音分群編號）

對位規則（凍結語意 SI-D3）：
- 每個 ASR 片段以「與單一發言者重疊時間最大」者為該段發言者。
- 若該片段與單一發言者的重疊比例低於 ``min_segment_coverage``（預設 0.6），
  且片段長度足以切分（≥4 字、≥1.0 秒），依各發言者重疊時間**比例**拆分文字
  （處理「一句話中間換人說」）；否則整段歸給重疊最大的發言者。
- 連續同發言者且停頓 ≤ ``merge_gap``（預設 1.5 秒）的片段合併為一段發言。
- 標籤為系統自動分群之「發言者N」，**非姓名**；編號依發言時間由多到少排序
  （發言者1＝本場發言量最大者），純屬統計排序，不得視為職稱或身分。

純函式、零 I/O、零 LLM：所有邏輯可單元測試。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence, Tuple

_CJK_RE = re.compile(r"[\u3400-\u9fff]")
_ASCII_ALNUM_RE = re.compile(r"[A-Za-z0-9]")

#: 逐字稿開頭標註說明（提供給 LLM 與人工閱讀者）。
SPEAKER_NOTE = (
    "【發言者標註說明】本逐字稿由系統依語音特徵自動分群標註，"
    "「發言者N」為分群編號、不是姓名；同一編號代表同一人，"
    "編號依發言時間由多到少排序（發言者1 為本場發言量最大者，通常為主持人但不必然）。"
)


@dataclass
class AsrPiece:
    """ASR 片段（時間區間＋文字）。"""

    start: float
    end: float
    text: str


@dataclass
class AlignedUtterance:
    """對位後的發言段落（同一發言者的連續發言）。"""

    start: float
    end: float
    speaker: int
    text: str


@dataclass
class SpeakerStat:
    """單一發言者的統計（供角色判讀與人工核對）。"""

    speaker: int
    label: str
    seconds: float
    share: float
    utterance_count: int
    first_seen: float
    first_text: str


@dataclass
class SpeakerLabeledTranscript:
    """帶發言者標註的逐字稿與其統計。"""

    text: str
    utterances: List[AlignedUtterance]
    stats: List[SpeakerStat]
    speaker_labels: dict
    speaker_count: int = 0
    metadata: dict = field(default_factory=dict)


def _overlap(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def format_timestamp(seconds: float) -> str:
    """秒數 → HH:MM:SS（向下取整；負值視為 0）。"""

    total = max(0, int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


def join_text(left: str, right: str) -> str:
    """依中英排版規則連接兩個片段（保留 ASR 原文，不新增多餘空白）。"""

    if not left:
        return right
    if not right:
        return left
    left_tail = left[-1]
    right_head = right[0]
    if _ASCII_ALNUM_RE.match(left_tail) and _ASCII_ALNUM_RE.match(right_head):
        return f"{left} {right}"
    if _CJK_RE.match(left_tail) and _ASCII_ALNUM_RE.match(right_head):
        return f"{left} {right}"
    if _ASCII_ALNUM_RE.match(left_tail) and _CJK_RE.match(right_head):
        return f"{left} {right}"
    return left + right


def _allocate_text(text: str, weights: Sequence[float]) -> List[str]:
    """依權重把 text 切成 len(weights) 份（字元級、確定性、不丟字）。"""

    total_weight = sum(weights)
    if total_weight <= 0 or not text:
        return ["" for _ in weights]
    lengths = len(text)
    raw = [lengths * weight / total_weight for weight in weights]
    counts = [max(1, int(value)) for value in raw]
    # 修正四捨五入造成的總長偏差：從最大權重者開始增減
    order = sorted(range(len(weights)), key=lambda index: (-weights[index], index))
    while sum(counts) > lengths and order:
        for index in order:
            if sum(counts) <= lengths:
                break
            if counts[index] > 1:
                counts[index] -= 1
        if all(count == 1 for count in counts):
            break
    deficit = lengths - sum(counts)
    position = 0
    while deficit > 0 and order:
        counts[order[position % len(order)]] += 1
        deficit -= 1
        position += 1
    pieces: List[str] = []
    cursor = 0
    for count in counts:
        pieces.append(text[cursor : cursor + count])
        cursor += count
    if cursor < lengths:  # 保險：任何未配置到的尾字併入最後一段
        pieces[-1] = pieces[-1] + text[cursor:]
    return pieces


def _nearest_turn_speaker(segment: AsrPiece, turns) -> Optional[int]:
    """無重疊時以時間距離最近的發言者作為歸屬。"""

    best_speaker: Optional[int] = None
    best_distance = None
    midpoint = (segment.start + segment.end) / 2.0
    for turn in turns:
        distance = min(abs(midpoint - turn.start), abs(midpoint - turn.end))
        if best_distance is None or distance < best_distance:
            best_distance = distance
            best_speaker = turn.speaker
    return best_speaker


def split_segment_by_turns(
    segment: AsrPiece,
    turns,
    *,
    min_segment_coverage: float = 0.6,
    min_split_chars: int = 4,
    min_split_seconds: float = 1.0,
    min_overlap_seconds: float = 0.3,
) -> List[AlignedUtterance]:
    """把單一 ASR 片段依說話者時間重疊分配成 1..n 段發言。"""

    text = segment.text
    if not text or not turns:
        return []

    by_speaker: dict = {}
    for turn in turns:
        overlap = _overlap(segment.start, segment.end, turn.start, turn.end)
        if overlap <= 0:
            continue
        by_speaker[turn.speaker] = by_speaker.get(turn.speaker, 0.0) + overlap

    if not by_speaker:
        speaker = _nearest_turn_speaker(segment, turns)
        if speaker is None:
            return []
        return [AlignedUtterance(start=segment.start, end=segment.end, speaker=speaker, text=text)]

    total_overlap = sum(by_speaker.values())
    dominant_speaker = max(by_speaker.items(), key=lambda item: (item[1], -item[0]))[0]
    dominant_share = by_speaker[dominant_speaker] / total_overlap if total_overlap else 1.0
    duration = max(0.0, segment.end - segment.start)

    splittable = [
        (speaker, overlap)
        for speaker, overlap in by_speaker.items()
        if overlap >= min_overlap_seconds
    ]
    if (
        dominant_share >= min_segment_coverage
        or len(text) < min_split_chars
        or duration < min_split_seconds
        or len(splittable) < 2
    ):
        return [
            AlignedUtterance(
                start=segment.start, end=segment.end, speaker=dominant_speaker, text=text
            )
        ]

    ordered = sorted(splittable, key=lambda item: item[0])
    weights = [overlap for _, overlap in ordered]
    pieces = _allocate_text(text, weights)
    results: List[AlignedUtterance] = []
    cursor = segment.start
    for (speaker, overlap), piece in zip(ordered, pieces):
        span = duration * overlap / total_overlap if total_overlap else duration
        end = min(segment.end, cursor + span)
        results.append(AlignedUtterance(start=cursor, end=max(cursor, end), speaker=speaker, text=piece))
        cursor = end
    if results:
        results[-1].end = segment.end
        # 空片段（純空白）不出現在輸出
        results = [item for item in results if item.text.strip()]
    return results


def align_transcript(
    segments: Iterable[AsrPiece],
    turns,
    *,
    min_segment_coverage: float = 0.6,
    merge_gap: float = 1.5,
) -> List[AlignedUtterance]:
    """對位並合併成發言段落清單（依時間排序）。"""

    ordered_segments = sorted(
        (segment for segment in segments if (segment.text or "").strip()),
        key=lambda segment: (segment.start, segment.end),
    )
    pieces: List[AlignedUtterance] = []
    for segment in ordered_segments:
        pieces.extend(
            split_segment_by_turns(
                segment, turns, min_segment_coverage=min_segment_coverage
            )
        )

    merged: List[AlignedUtterance] = []
    for piece in pieces:
        if merged:
            last = merged[-1]
            gap = piece.start - last.end
            if piece.speaker == last.speaker and gap <= merge_gap:
                last.text = join_text(last.text, piece.text)
                last.end = max(last.end, piece.end)
                continue
        merged.append(
            AlignedUtterance(
                start=piece.start, end=piece.end, speaker=piece.speaker, text=piece.text
            )
        )
    return merged


def _speaker_order(utterances: Sequence[AlignedUtterance]) -> List[Tuple[int, float]]:
    durations: dict = {}
    for utterance in utterances:
        durations[utterance.speaker] = durations.get(utterance.speaker, 0.0) + max(
            0.0, utterance.end - utterance.start
        )
    return sorted(durations.items(), key=lambda item: (-item[1], item[0]))


def build_speaker_labeled_transcript(
    segments: Iterable[AsrPiece],
    turns,
    *,
    merge_gap: float = 1.5,
    min_segment_coverage: float = 0.6,
) -> Optional[SpeakerLabeledTranscript]:
    """組出帶發言者標註的逐字稿；無法對位（無 turns 或無 segments）時回 None。"""

    turn_list = list(turns or [])
    if not turn_list:
        return None
    utterances = align_transcript(
        segments,
        turn_list,
        min_segment_coverage=min_segment_coverage,
        merge_gap=merge_gap,
    )
    if not utterances:
        return None

    order = _speaker_order(utterances)
    labels = {speaker: f"發言者{index + 1}" for index, (speaker, _) in enumerate(order)}
    total_seconds = sum(duration for _, duration in order) or 1.0

    stats: List[SpeakerStat] = []
    for speaker, duration in order:
        speaker_utterances = [item for item in utterances if item.speaker == speaker]
        first = speaker_utterances[0]
        stats.append(
            SpeakerStat(
                speaker=speaker,
                label=labels[speaker],
                seconds=duration,
                share=duration / total_seconds,
                utterance_count=len(speaker_utterances),
                first_seen=first.start,
                first_text=first.text[:40],
            )
        )

    lines: List[str] = [SPEAKER_NOTE, "【發言者統計】"]
    for stat in stats:
        lines.append(
            f"- {stat.label}：{format_timestamp(stat.seconds)}"
            f"（{stat.share:.0%}，{stat.utterance_count} 段，首次發言 {format_timestamp(stat.first_seen)}）"
            f" 首句節錄：{stat.first_text}"
        )
    lines.append("")
    for utterance in utterances:
        label = labels.get(utterance.speaker, f"發言者?{utterance.speaker}")
        lines.append(
            f"[{format_timestamp(utterance.start)}-{format_timestamp(utterance.end)}] "
            f"{label}：{utterance.text}"
        )

    return SpeakerLabeledTranscript(
        text="\n".join(lines),
        utterances=utterances,
        stats=stats,
        speaker_labels=labels,
        speaker_count=len(labels),
        metadata={
            "merge_gap": merge_gap,
            "min_segment_coverage": min_segment_coverage,
            "utterance_count": len(utterances),
        },
    )
