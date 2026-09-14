"""
確定性文字後處理層（語意校正機制第二層）。

不依賴 LLM 的固定規則清理，依序提供：
- OpenCC 簡體→台灣繁體正規化（s2twp）
- Whisper 幻覺黑名單移除（「請訂閱」「字幕由…提供」等訓練資料汙染句）
- 連續重複句去重（中文重複字幻覺的保險網）
- 公務用字白名單修正（高頻固定錯誤）

以及供會議紀錄「驗證前」統一使用的記錄級清理（自 task_processor 移入，
確保驗證是最後一關，驗證通過後不再被改寫）。
"""

from __future__ import annotations

import re
from typing import Optional

from backend.core.logger import log

# ---------------------------------------------------------------------------
# OpenCC 簡繁轉換（lazy singleton；未安裝 opencc 時降級為原字元表偵測）
# ---------------------------------------------------------------------------

_OPENCC_S2TWP = None
_OPENCC_AVAILABLE: Optional[bool] = None

# 簡體偵測字元表：只收「無歧義、僅存在於簡體」的常用字。
# 注意不可收簡繁共用字（如 里、干、后、面、台），否則正體文本會誤報。
_SIMPLIFIED_ONLY_CHARS = (
    "为会体们动办务发号启实对开当录总应数术样气没点产监类统网规让议话这进项"
    "华质关证长门问间东车贝见页风飞马鸟龙齐语说读写学习经济级红结组织给继续"
    "记报确认单资讯电脑络软设备预处调审决书简称属"
)


def _get_s2twp():
    """取得 OpenCC s2twp 轉換器（簡體→台灣正體＋台灣用語）。"""
    global _OPENCC_S2TWP, _OPENCC_AVAILABLE
    if _OPENCC_AVAILABLE is None:
        try:
            from opencc import OpenCC

            _OPENCC_S2TWP = OpenCC("s2twp")
            _OPENCC_AVAILABLE = True
        except Exception as exc:  # noqa: BLE001
            _OPENCC_AVAILABLE = False
            log.warning("OpenCC 不可用，簡繁轉換降級為字元表偵測: {}", exc)
    return _OPENCC_S2TWP


def to_taiwan_traditional(text: str) -> str:
    """將文字統一為台灣正體（含台灣用語轉換）。OpenCC 不可用時原樣回傳。

    只轉換「偵測到簡體字的行」：對已是正體的文字跑 s2twp 會誤傷
    簡繁共用字（實測案例：干預→幹預），先偵測再轉換可完全避免。
    """
    if not text:
        return text
    converter = _get_s2twp()
    if converter is None:
        return text

    lines = text.split("\n")
    converted_lines: list[str] = []
    for line in lines:
        if line and contains_simplified_chinese(line):
            try:
                converted_lines.append(converter.convert(line))
                continue
            except Exception as exc:  # noqa: BLE001
                log.warning("OpenCC 轉換失敗，保留原文: {}", exc)
        converted_lines.append(line)
    return "\n".join(converted_lines)


def contains_simplified_chinese(text: str) -> bool:
    """偵測文字是否含簡體字。

    以「無歧義簡體字」擴充字元表比對（零誤報）；簡繁共用字（里、干、后、
    面、台等）刻意不列入，避免正體文本誤報。共用字造成的漏網由
    `to_taiwan_traditional` 的整段轉換兜底。
    """
    if not text:
        return False
    return any(char in text for char in _SIMPLIFIED_ONLY_CHARS)


# ---------------------------------------------------------------------------
# Whisper 幻覺黑名單與重複句去重
# ---------------------------------------------------------------------------

# 訓練資料（字幕組）汙染造成的典型幻覺句式
_HALLUCINATION_PATTERNS = [
    r"請[訂订]閱[^\n。]*",
    r"[謝谢]{1,2}[謝谢]?觀看[^\n。]*",
    r"感謝(?:您的)?[收觀]看[^\n。]*",
    r"字幕[由提供製作志愿者]{0,4}[^\n。]{0,20}(?:提供|製作|字幕組|社[群区]|Amara\.org)[^\n。]*",
    r"(?:by\s+)?Amara\.org[^\n]*",
    r"明天(?:見|再見)[!！]?\s*$",
    r"訂閱[、,，]?按讚[、,，]?開啟小鈴鐺[^\n。]*",
]
_HALLUCINATION_RES = [re.compile(p, re.IGNORECASE) for p in _HALLUCINATION_PATTERNS]


def remove_hallucination_lines(text: str) -> tuple[str, int]:
    """移除幻覺黑名單句式，回傳（清理後文字, 移除次數）。"""
    if not text:
        return text, 0
    removed = 0
    cleaned = text
    for pattern in _HALLUCINATION_RES:
        cleaned, count = pattern.subn("", cleaned)
        removed += count
    if removed:
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip(), removed


def dedup_consecutive_sentences(text: str, min_len: int = 4, max_repeats: int = 1) -> tuple[str, int]:
    """將「連續完全重複」的句子壓縮為一次（重複字/句幻覺保險網）。

    只處理相鄰重複，不做跨段去重，避免誤刪合法的重複強調。
    """
    if not text:
        return text, 0

    parts = re.split(r"(?<=[。！？!?\n])", text)
    result: list[str] = []
    removed = 0
    for part in parts:
        normalized = part.strip()
        if (
            normalized
            and len(normalized) >= min_len
            and result
        ):
            recent = [p.strip() for p in result[-max_repeats:]]
            if all(p == normalized for p in recent) and len(recent) == max_repeats:
                removed += 1
                continue
        result.append(part)
    return "".join(result), removed


# ---------------------------------------------------------------------------
# 連續重複迴圈壓縮（generic，無特定詞黑名單）
# ---------------------------------------------------------------------------

# 迴圈單元之間僅允許空白或輕標點
_REP_LOOP_SEP = r"[、，,。\s]*"
# 1 字 primitive unit：連續 >= 8 次才視為迴圈（保留自然強調）
_REP_LOOP_SINGLE_RE = re.compile(r"([^\s、，,。])(?:" + _REP_LOOP_SEP + r"\1){7,}")
# 2–20 字 primitive unit：連續 >= 4 次才視為迴圈
_REP_LOOP_MULTI_RE = re.compile(r"(\S{2,20}?)(?:" + _REP_LOOP_SEP + r"\1){3,}")


def collapse_repetition_loops(text: str) -> tuple[str, int]:
    """壓縮無句界的連續重複迴圈，回傳（清理後文字, 壓縮的迴圈數）。

    針對 ASR decoder 進入重複迴圈時產生的「請看影片 請看影片 請看影片…」
    或「對對對對…」等病理模式：以 primitive unit 的連續重複次數判定
    （1 字單元 >= 8 次；2–20 字單元 >= 4 次），單元之間僅允許空白或輕標點，
    觸發後保留兩次以避免刪除自然強調。刻意不使用特定詞黑名單，保持
    provider 無關；低於 threshold 的自然重複完全不會被改動。
    """
    if not text:
        return text, 0

    collapsed = 0

    def _keep_two(match: re.Match) -> str:
        nonlocal collapsed
        unit = match.group(1)
        pairs = re.findall(_REP_LOOP_SEP + re.escape(unit), match.group(0)[len(unit):])
        collapsed += 1
        return unit + "".join(pairs[:1])

    # 先處理 1 字單元（threshold 8），再處理 2–20 字單元（threshold 4），
    # 避免長單字迴圈被誤當成 2 字單元迴圈而保留過多
    result = _REP_LOOP_SINGLE_RE.sub(_keep_two, text)
    result = _REP_LOOP_MULTI_RE.sub(_keep_two, result)
    return result, collapsed


# ---------------------------------------------------------------------------
# 公務用字白名單（高頻固定錯誤的確定性替換）
# ---------------------------------------------------------------------------

# 只放「幾乎不可能誤傷」的固定修正；動態同音字交給 LLM 校正層
_OFFICIAL_TERM_FIXES = [
    (re.compile(r"會議紀錄表"), "會議紀錄"),
    (re.compile(r"薦任官"), "薦任"),
    (re.compile(r"筒任"), "簡任"),
    (re.compile(r"函辦(?=[^㐀-鿿]|$)"), "函頒"),
    (re.compile(r"呈核(?=無誤)"), "陳核"),
]


def apply_official_term_fixes(text: str) -> tuple[str, list[tuple[str, str]]]:
    """套用公務用字白名單，回傳（修正後文字, 修正對照清單）。"""
    if not text:
        return text, []
    changes: list[tuple[str, str]] = []
    fixed = text
    for pattern, replacement in _OFFICIAL_TERM_FIXES:
        if pattern.search(fixed):
            changes.append((pattern.pattern, replacement))
            fixed = pattern.sub(replacement, fixed)
    return fixed, changes


# ---------------------------------------------------------------------------
# 逐字稿清理管線（P1-2：語意校正第二層入口）
# ---------------------------------------------------------------------------


def clean_transcript(text: str) -> tuple[str, dict]:
    """對 ASR 逐字稿執行完整的確定性清理，回傳（清理後文字, 統計）。"""
    stats: dict = {
        "opencc": False,
        "hallucinations_removed": 0,
        "repetition_loops_collapsed": 0,
        "dedup_removed": 0,
        "term_fixes": [],
    }
    if not text:
        return text, stats

    converted = to_taiwan_traditional(text)
    stats["opencc"] = converted != text

    cleaned, hallucinated = remove_hallucination_lines(converted)
    stats["hallucinations_removed"] = hallucinated

    cleaned, loops_collapsed = collapse_repetition_loops(cleaned)
    stats["repetition_loops_collapsed"] = loops_collapsed
    if loops_collapsed:
        log.warning("[清理] 壓縮連續重複迴圈 {} 處（保留兩次）", loops_collapsed)

    cleaned, deduped = dedup_consecutive_sentences(cleaned)
    stats["dedup_removed"] = deduped

    cleaned, fixes = apply_official_term_fixes(cleaned)
    stats["term_fixes"] = fixes

    return cleaned, stats


# ---------------------------------------------------------------------------
# 會議紀錄（record）級清理 —— 供 summarization 於「驗證前」統一套用
# （自 task_processor 移入；P1-9 後處理與驗證順序重構）
# ---------------------------------------------------------------------------

MISSING_TEXT = "逐字稿未提及"

_ENGLISH_PREAMBLE_RE = re.compile(
    r"^(?:Analysis of the Transcript|Evaluation Criteria|Let'?s\b|Here'?s\b|"
    r"Below is\b|Okay[,，]?\s*(?:let|here)|Sure[,，]?\b)",
    re.IGNORECASE,
)

_ENGLISH_TERM_REPLACEMENTS = {
    r"\bOkay\b": "好",
    r"\bokay\b": "好",
    r"\bSure\b": "好",
    r"\bsure\b": "好",
    r"\bRecap\b": "總結",
    r"\brecap\b": "總結",
    r"\bExecutive Summary\b": "執行摘要",
    r"\bDiscussion & Decisions\b": "詳細議題與決議",
    r"\bAction Items\b": "待辦事項",
    r"\bStand\s*by\b": "待命",
    r"\bstand\s*by\b": "待命",
    r"\$\s*\\rightarrow\s*\$": "→",
    r"\\rightarrow": "→",
}


def remove_english_segments(text: str, protected_terms: Optional[set[str]] = None) -> str:
    """移除英文比例過高的行（P1-10：詞彙表命中行受白名單保護，刪除行為記入 log）。"""
    protected_terms = protected_terms or set()
    lines = text.split("\n")
    cleaned_lines: list[str] = []

    for line in lines:
        stripped = line.lstrip()

        if "（待確認）" in stripped:
            cleaned_lines.append(line)
            continue

        if not stripped or stripped.startswith(("#", "*", "|", "-", ">")):
            cleaned_lines.append(line)
            continue

        if _ENGLISH_PREAMBLE_RE.match(stripped):
            log.warning("[清理] 移除英文前言行: {}...", stripped[:50])
            continue

        if stripped[0].isascii() and stripped[0].isalpha():
            # 詞彙表白名單保護：行內含機關詞彙表的英文專名則不刪
            if protected_terms and any(term and term in line for term in protected_terms):
                cleaned_lines.append(line)
                continue

            english_words = len(re.findall(r"\b[a-zA-Z]+\b", line))
            total_words = len(line.split())
            cjk_chars = len(re.findall(r"[㐀-鿿]", line))

            if total_words > 0 and english_words / total_words > 0.5 and cjk_chars < 4:
                log.warning("[清理] 移除高英文比例行: {}...", line[:50])
                continue

        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def sanitize_text_language(text: str) -> str:
    """將常見英文詞彙替換為中文對應詞。"""
    result = text
    for pattern, replacement in _ENGLISH_TERM_REPLACEMENTS.items():
        result = re.sub(pattern, replacement, result)
    return result


def has_excessive_english(text: str) -> bool:
    """檢查文本中是否有過多英文。"""
    normalized = re.sub(r"[#|>*`\-]+", " ", text)
    cjk_chars = len(re.findall(r"[㐀-鿿]", normalized))
    english_words = len(re.findall(r"\b[a-zA-Z][A-Za-z0-9_/-]*\b", normalized))
    token_count = cjk_chars + english_words

    if token_count == 0:
        return False

    english_ratio = english_words / token_count
    if english_ratio > 0.25:
        log.warning("[品質] 檢測到高英文比例: {:.1f}% ({}/{} 詞)", english_ratio * 100, english_words, token_count)
        return True
    return False


# ---------------------------------------------------------------------------
# 範本骨架佔位符外洩修復（v4.7.3；2026-09-14 實測）
# ---------------------------------------------------------------------------
# 提示詞內含「紀錄骨架」示範，模型有時會把骨架原樣抄進成品：實測 Gemini 在逐字稿
# 沒提到日期時，直接吐出「時間：中華民國（年）年（月）月（日）日（星期）（時分）」
# 與「（待確認）年（月）月份第（次）次科務會議紀錄」。這種輸出看起來有填、實際上
# 整欄沒有任何可用資訊，比官方規定的「（待確認）」更糟（讀者無法分辨「尚未填寫」
# 與「系統吐了佔位符」）。此處以確定性規則把佔位符換回「（待確認）」——只拿掉沒有
# 資訊的佔位符，不新增任何事實，故不違反忠實性原則（絕不杜撰）。
_UNFILLED_PLACEHOLDER_PATTERN = re.compile(
    r"[（(](?:機關及科別|機關科別|民國年|年|月|日|星期|時分|次)[）)]"
)
# 只修「紀錄開頭欄位」與「標題行」：正文若剛好出現同名字樣（例如引述表格欄位）
# 一律不動，避免誤傷內容。
_UNFILLED_PLACEHOLDER_FIELD_LINE_PATTERN = re.compile(
    r"^(?:時間|地點|主持人|出席人員|紀\s*錄|散會)\s*[:：]"
)
_UNFILLED_PLACEHOLDER_TITLE_LINE_PATTERN = re.compile(r"(?:紀錄|彙整表)\s*$")
_MISSING_TEXT = "（待確認）"


def _is_unfilled_placeholder_line(stripped: str, template) -> bool:
    """判斷某行是否屬於「該修」的紀錄欄位／標題行。"""
    if _UNFILLED_PLACEHOLDER_FIELD_LINE_PATTERN.match(stripped):
        return True
    if _UNFILLED_PLACEHOLDER_TITLE_LINE_PATTERN.search(stripped):
        return True
    for spec in getattr(template, "record_header_fields", ()) or ():
        if spec.pattern.search(stripped):
            return True
    return False


def normalize_unfilled_placeholders(text: str, template=None) -> str:
    """把模型照抄範本骨架留下的日期佔位符換成「（待確認）」（v4.7.3）。

    只處理紀錄開頭欄位與標題行（含所選模板宣告的欄位樣式），正文完全不動；
    沒有出現佔位符的行一個字都不改（不做多餘加工）。地端／雲端共用本函式，
    但呼叫端目前僅雲端生成流程套用。
    """
    if not text or not _UNFILLED_PLACEHOLDER_PATTERN.search(text):
        return text

    normalized_lines: list[str] = []
    fixed_lines = 0
    for line in text.splitlines():
        stripped = line.strip()
        if (
            _UNFILLED_PLACEHOLDER_PATTERN.search(stripped)
            and _is_unfilled_placeholder_line(stripped, template)
        ):
            fixed = _UNFILLED_PLACEHOLDER_PATTERN.sub(_MISSING_TEXT, line)
            # 骨架中相鄰的佔位符（如（星期）（時分））修完會連成一串，
            # 合併成一個「（待確認）」以免同一欄重複出現。
            fixed = re.sub(
                f"(?:{re.escape(_MISSING_TEXT)}){{2,}}", _MISSING_TEXT, fixed
            )
            if fixed != line:
                fixed_lines += 1
            normalized_lines.append(fixed)
            continue
        normalized_lines.append(line)

    if fixed_lines:
        log.info(
            f"[品質] 修復範本骨架佔位符 {fixed_lines} 行"
            f"（日期欄位改回「{_MISSING_TEXT}」）"
        )
    return "\n".join(normalized_lines)


def ensure_record_structure(summary: str, template=None) -> str:
    """確保會議紀錄具有完整欄位結構（容錯比對，缺漏者依模板補骨架）。

    v4.4.0：欄位與章節骨架改由會議模板（MeetingTemplate）驅動；
    template=None 時使用 general 模板，輸出與 v4.3.3 完全一致。
    """
    # 延遲 import 避免循環（templates 不得反向 import 本模組）
    from backend.core.templates import get_template

    if template is None:
        template = get_template(None)

    cleaned = (summary or "").strip()

    cleaned = re.sub(r"^```(?:markdown)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\n?```$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    header_lines: list[str] = []
    section_lines: list[str] = []

    # 欄位存在性採容錯 regex（允許空格數量差異與全半形冒號），輸出統一為標準格式
    for field_spec in template.record_header_fields:
        if not field_spec.pattern.search(cleaned):
            header_lines.append(field_spec.line)

    for section in template.record_sections:
        if not section.presence_pattern.search(cleaned):
            section_lines.extend(section.skeleton_lines)
            continue
        for subfield_pattern, subfield_lines in section.subfields:
            if not subfield_pattern.search(cleaned):
                section_lines.extend(subfield_lines)

    if header_lines:
        prefix = "\n".join(header_lines)
        cleaned = f"{prefix}\n\n{cleaned}" if cleaned else prefix

    if section_lines:
        suffix = "\n".join(section_lines)
        cleaned = f"{cleaned}\n\n{suffix}" if cleaned else suffix

    return cleaned.strip()


def finalize_record(summary: str, protected_terms: Optional[set[str]] = None, template=None) -> str:
    """會議紀錄的完整記錄級後處理（驗證前呼叫，此後不得再改寫本文）。"""
    cleaned = remove_english_segments(summary or "", protected_terms=protected_terms)
    cleaned = sanitize_text_language(cleaned)
    cleaned = to_taiwan_traditional(cleaned)
    if has_excessive_english(cleaned):
        log.warning("[品質] 會議紀錄仍含較多英文詞彙，請人工抽查輸出內容")
    return ensure_record_structure(cleaned, template=template)
