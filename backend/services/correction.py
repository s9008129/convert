"""
逐字稿選擇性 LLM 校正服務（語意校正機制第三層＋第四層同音驗證閘門）。

設計依據（詳見《系統改善及優化計畫.md》P1-3 / P1-4 與研究出處）：
- 中文 ASR 錯誤以同音替換為壓倒性主體 → 校正只允許「同音/近音」替換
- naive 全文改寫有品質劣化實證 → 每個替換經注音比對閘門，非同音近音一律退回
- 單段改動比例超過上限（預設 10%）→ 整段放棄校正
- 所有修改記錄成對照表，隨會議紀錄輸出供人工複核（政府合規要求）

與三階段摘要管線完全解耦，可用 ENABLE_TRANSCRIPT_CORRECTION 獨立開關。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Optional

from backend.core.config import settings
from backend.core.errors import StableServiceError, describe_exception
from backend.core.glossary import apply_known_corrections, glossary_prompt_block
from backend.core.logger import log
from backend.core.prompts import TRANSCRIPT_CORRECTION_SYSTEM_PROMPT, build_correction_user_message

_CJK_RE = re.compile(r"[㐀-鿿]")

# 台灣口音常見的聲母/韻母混淆組（近音判定用）
_INITIAL_EQUIV = [
    {"zh", "z"}, {"ch", "c"}, {"sh", "s"}, {"l", "n"}, {"f", "h"}, {"r", "l"},
]
_FINAL_EQUIV = [
    {"in", "ing"}, {"en", "eng"}, {"an", "ang"}, {"uan", "uang"}, {"ian", "iang"},
    {"o", "e"}, {"uo", "o"},
]


@dataclass
class CorrectionChange:
    original: str
    corrected: str
    accepted: bool
    reason: str = ""


@dataclass
class CorrectionReport:
    enabled: bool = True
    segments_total: int = 0
    segments_corrected: int = 0
    segments_discarded: int = 0
    changes: list[CorrectionChange] = field(default_factory=list)
    # 確定性誤辨修正（詞彙表 `錯=>對`）：不吃 LLM、與模型無關，獨立於
    # `changes`（LLM 閘門結果）之外統計，避免污染既有「採納 N 處」語意。
    deterministic_changes: list[CorrectionChange] = field(default_factory=list)
    known_fixes_applied: int = 0
    error: Optional[str] = None

    @property
    def accepted_changes(self) -> list[CorrectionChange]:
        return [change for change in self.changes if change.accepted]

    def to_markdown(self) -> str:
        """輸出修改對照表（附於會議紀錄之後，供人工複核）。"""
        accepted = self.deterministic_changes + self.accepted_changes
        if not accepted:
            return "（本次語意校正未修改任何內容）"
        lines = ["| 原文 | 校正後 |", "| :--- | :--- |"]
        seen: set[tuple[str, str]] = set()
        for change in accepted:
            key = (change.original, change.corrected)
            if key in seen:
                continue
            seen.add(key)
            lines.append(f"| {change.original} | {change.corrected} |")
        return "\n".join(lines)


def _lazy_pinyin(text: str) -> list[str]:
    from pypinyin import Style, lazy_pinyin

    return lazy_pinyin(text, style=Style.NORMAL, errors=lambda chars: list(chars))


def _split_syllable(syllable: str) -> tuple[str, str]:
    """粗略拆出聲母/韻母。"""
    for initial in ("zh", "ch", "sh", "b", "p", "m", "f", "d", "t", "n", "l", "g", "k", "h", "j", "q", "x", "r", "z", "c", "s", "y", "w"):
        if syllable.startswith(initial):
            return initial, syllable[len(initial):]
    return "", syllable


def _syllables_near(a: str, b: str) -> bool:
    """兩音節是否同音或近音（台灣口音容錯）。"""
    if a == b:
        return True
    initial_a, final_a = _split_syllable(a)
    initial_b, final_b = _split_syllable(b)

    initials_ok = initial_a == initial_b or any(
        {initial_a, initial_b} <= group for group in _INITIAL_EQUIV
    )
    finals_ok = final_a == final_b or any(
        {final_a, final_b} <= group for group in _FINAL_EQUIV
    )
    return initials_ok and finals_ok


def is_homophone_swap(original: str, corrected: str) -> bool:
    """同音驗證閘門核心：判斷替換是否屬於同音/近音替換。"""
    if not original or not corrected:
        return False
    # 只允許「純中日韓字元」的替換（英數替換一律退回，交由詞彙表白名單處理）
    cjk_original = _CJK_RE.findall(original)
    cjk_corrected = _CJK_RE.findall(corrected)
    if not cjk_original or len(cjk_original) != len(original) or len(cjk_corrected) != len(corrected):
        return False

    pinyin_a = _lazy_pinyin(original)
    pinyin_b = _lazy_pinyin(corrected)
    if len(pinyin_a) != len(pinyin_b):
        return False
    return all(_syllables_near(a, b) for a, b in zip(pinyin_a, pinyin_b))


def _is_glossary_correction(original: str, corrected: str) -> bool:
    """已知誤辨修正清單（詞彙表 `錯=>對`）直接放行。"""
    from backend.core.glossary import load_glossary

    _, corrections = load_glossary()
    return (original, corrected) in {(wrong, right) for wrong, right in corrections}


_PROTECTED_WINDOW_CHARS = 24


def _would_destroy_protected_term(original: str, i1: int, i2: int, new_piece: str) -> bool:
    """保護詞表護欄：替換若使局部視窗內的保護詞消失，即退回該替換。

    語意：保護詞（詞彙表登錄的正確詞面，如「內稽」「戶數」「差勤」）不得被
    LLM 的自由替換消滅；已知誤辨白名單不受此限（它只會把錯形換成正形）。
    視窗取替換點前後各 24 字，避免跨句誤判。
    """
    from backend.core.glossary import protected_terms

    terms = protected_terms()
    if not terms:
        return False
    start = max(0, i1 - _PROTECTED_WINDOW_CHARS)
    end = min(len(original), i2 + _PROTECTED_WINDOW_CHARS)
    before = original[start:end]
    after = original[start:i1] + new_piece + original[i2:end]
    return any(before.count(term) > after.count(term) for term in terms)


def gate_correction(original: str, corrected: str, max_change_ratio: float) -> tuple[str, list[CorrectionChange]]:
    """第四層閘門：對 LLM 輸出逐一比對替換，非同音近音一律退回原文。

    回傳（閘門後文字, 修改清單）。整段改動超過 max_change_ratio 時放棄整段校正。
    """
    if corrected.strip() == original.strip():
        return original, []

    matcher = SequenceMatcher(None, original, corrected, autojunk=False)
    opcodes = matcher.get_opcodes()

    changed_chars = sum(
        max(i2 - i1, j2 - j1) for tag, i1, i2, j1, j2 in opcodes if tag != "equal"
    )
    if original and changed_chars / len(original) > max_change_ratio:
        return original, [
            CorrectionChange(
                original="（整段）",
                corrected="（放棄）",
                accepted=False,
                reason=f"改動比例 {changed_chars / len(original):.0%} 超過上限 {max_change_ratio:.0%}",
            )
        ]

    result_parts: list[str] = []
    changes: list[CorrectionChange] = []
    for tag, i1, i2, j1, j2 in opcodes:
        old_piece = original[i1:i2]
        new_piece = corrected[j1:j2]
        if tag == "equal":
            result_parts.append(old_piece)
            continue
        if tag == "replace":
            glossary_pair = _is_glossary_correction(old_piece, new_piece)
            allowed = glossary_pair or is_homophone_swap(old_piece, new_piece)
            if allowed and not glossary_pair and _would_destroy_protected_term(original, i1, i2, new_piece):
                result_parts.append(old_piece)
                changes.append(
                    CorrectionChange(
                        original=old_piece,
                        corrected=new_piece,
                        accepted=False,
                        reason="替換會消滅保護詞（詞彙表護欄），退回",
                    )
                )
                continue
            if allowed:
                result_parts.append(new_piece)
                changes.append(CorrectionChange(original=old_piece, corrected=new_piece, accepted=True))
            else:
                result_parts.append(old_piece)
                changes.append(
                    CorrectionChange(original=old_piece, corrected=new_piece, accepted=False, reason="非同音近音替換，退回")
                )
            continue
        # insert / delete：一律退回（保持逐字忠實），僅允許純空白差異
        if tag == "delete":
            if old_piece.strip():
                result_parts.append(old_piece)
                changes.append(CorrectionChange(original=old_piece, corrected="（刪除）", accepted=False, reason="不允許刪字，退回"))
            # 純空白刪除放行（不記錄）
            else:
                result_parts.append(old_piece)
        elif tag == "insert":
            if not new_piece.strip():
                result_parts.append(new_piece)
            else:
                changes.append(CorrectionChange(original="（無）", corrected=new_piece, accepted=False, reason="不允許加字，退回"))

    return "".join(result_parts), changes


class TranscriptCorrectionService:
    """逐字稿校正服務：分段 → LLM 校正 → 同音閘門 → 回填。"""

    def _split_segments(self, transcript: str) -> list[str]:
        """依句界切成 300-500 字段落。

        ASR 逐字稿（尤其 faster-whisper）常常整份無標點、以空白相連；
        句界切不開時退而以空白為斷點，仍超長再硬切，確保每段都在
        max_chars 之內（否則 LLM 會整段重寫、被閘門全數退回而白做工）。
        """
        max_chars = settings.CORRECTION_MAX_SEGMENT_CHARS
        sentences = [s for s in re.split(r"(?<=[。！？!?\n])", transcript) if s]

        pieces: list[str] = []
        for sentence in sentences:
            if len(sentence) <= max_chars:
                pieces.append(sentence)
                continue
            # 次要斷點：空白（保留空白於前一片段結尾，維持原文重組不變）
            buffer = ""
            for token in re.split(r"(\s+)", sentence):
                if buffer and len(buffer) + len(token) > max_chars and token.strip():
                    pieces.append(buffer)
                    buffer = token
                else:
                    buffer += token
            if buffer:
                pieces.append(buffer)

        # 仍超長（完全無空白）→ 硬切
        hard_pieces: list[str] = []
        for piece in pieces:
            if len(piece) <= max_chars:
                hard_pieces.append(piece)
            else:
                hard_pieces.extend(piece[i:i + max_chars] for i in range(0, len(piece), max_chars))

        segments: list[str] = []
        buffer = ""
        for piece in hard_pieces:
            if buffer and len(buffer) + len(piece) > max_chars:
                segments.append(buffer)
                buffer = piece
            else:
                buffer += piece
        if buffer:
            segments.append(buffer)
        return segments

    def _segment_needs_correction(self, segment: str) -> bool:
        """選擇性校正判斷。scope=all 一律校正；scope=auto 需命中詞彙表近音或已知誤辨。"""
        scope = (settings.CORRECTION_SCOPE or "all").lower()
        if scope == "all":
            return True

        from backend.core.glossary import load_glossary

        terms, corrections = load_glossary()
        for wrong, _ in corrections:
            if wrong in segment:
                return True

        # 注音 n-gram 模糊命中：段落中任一與詞彙表詞長相同、拼音相近的視窗
        segment_cjk = "".join(_CJK_RE.findall(segment))
        for term in terms:
            term_cjk = "".join(_CJK_RE.findall(term))
            if not (2 <= len(term_cjk) <= 6):
                continue
            if term_cjk in segment_cjk:
                continue  # 已正確出現，不觸發
            term_pinyin = _lazy_pinyin(term_cjk)
            window = len(term_cjk)
            for start in range(0, max(len(segment_cjk) - window + 1, 0)):
                piece = segment_cjk[start:start + window]
                if all(_syllables_near(a, b) for a, b in zip(_lazy_pinyin(piece), term_pinyin)):
                    return True
        return False

    async def correct_transcript(
        self,
        transcript: str,
        generate_fn,
        extra_glossary_block: str = "",
    ) -> tuple[str, CorrectionReport]:
        """對逐字稿執行選擇性校正。

        Args:
            transcript: 已經過確定性清理的逐字稿
            generate_fn: async (system_prompt, user_message) -> str 的生成函式
                         （由呼叫端注入，與摘要引擎解耦）
            extra_glossary_block: 會議模板專屬術語表區塊（v4.4.0；僅注入
                         LLM 校正層，刻意不進 ASR hotwords 以免污染逐字稿快取）
        """
        report = CorrectionReport()
        if not transcript or not transcript.strip():
            return transcript, report

        glossary_block = "\n\n".join(
            block for block in (glossary_prompt_block(), extra_glossary_block) if block
        )
        segments = self._split_segments(transcript)
        report.segments_total = len(segments)

        corrected_segments: list[str] = []
        context_chars = settings.CORRECTION_CONTEXT_CHARS

        for index, segment in enumerate(segments):
            original_segment = segment
            # 確定性誤辨修正（詞彙表 `錯=>對`）：模型無關、零 LLM 成本。
            # 先修掉資料檔登錄的固定誤辨，再交給 LLM 校正層——被測模型的校正
            # 能力不足（實測 27B 漏修 `內機→內稽`）時，這一層仍保證修好。
            segment, known_fixes = apply_known_corrections(segment)
            if known_fixes:
                report.known_fixes_applied += sum(count for _wrong, _right, count in known_fixes)
                report.deterministic_changes.extend(
                    CorrectionChange(
                        original=wrong,
                        corrected=right,
                        accepted=True,
                        reason=f"known_misrecognition×{count}",
                    )
                    for wrong, right, count in known_fixes
                )

            # 觸發判定沿用「修正前」文字：確定性修正不得讓原本該校正的段落被跳過。
            if not self._segment_needs_correction(original_segment):
                corrected_segments.append(segment)
                continue

            context_before = "".join(corrected_segments)[-context_chars:] if corrected_segments else ""
            try:
                raw = await generate_fn(
                    TRANSCRIPT_CORRECTION_SYSTEM_PROMPT,
                    build_correction_user_message(segment.strip(), context_before.strip(), glossary_block),
                )
            except StableServiceError as exc:
                # provider-level 穩定失敗（如 LMSTUDIO_UNREACHABLE）：BEST_EFFORT
                # 校正不得放大呼叫。熔斷後續所有段落的 LLM 呼叫，
                # 保留當段與所有剩餘段落原文。
                log.warning(
                    "校正遇 provider 穩定失敗（{}），熔斷後續 LLM 校正，剩餘段落保留原文: {}",
                    exc.code,
                    describe_exception(exc),
                )
                corrected_segments.append(segment)
                corrected_segments.extend(segments[index + 1:])
                report.error = describe_exception(exc)
                break
            except Exception as exc:  # noqa: BLE001
                log.warning("校正第 {}/{} 段失敗，保留原文: {}", index + 1, len(segments), exc)
                corrected_segments.append(segment)
                report.error = str(exc)
                continue

            candidate = (raw or "").strip()
            if not candidate:
                corrected_segments.append(segment)
                continue

            gated, changes = gate_correction(segment.strip(), candidate, settings.CORRECTION_MAX_CHANGE_RATIO)
            report.changes.extend(changes)
            if changes and all(not change.accepted for change in changes) and any(
                change.original == "（整段）" for change in changes
            ):
                report.segments_discarded += 1
            elif any(change.accepted for change in changes):
                report.segments_corrected += 1

            # 保留原始段落的前後空白樣式
            leading = segment[: len(segment) - len(segment.lstrip())]
            trailing = segment[len(segment.rstrip()):]
            corrected_segments.append(f"{leading}{gated}{trailing}")

        accepted_count = len(report.accepted_changes)
        log.info(
            "語意校正完成：{} 段中 {} 段有修正、{} 段放棄、採納 {} 處替換、"
            "確定性誤辨修正 {} 處（詞彙表）",
            report.segments_total,
            report.segments_corrected,
            report.segments_discarded,
            accepted_count,
            report.known_fixes_applied,
        )
        return "".join(corrected_segments), report


transcript_correction_service = TranscriptCorrectionService()
