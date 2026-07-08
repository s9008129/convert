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
    stats: dict = {"opencc": False, "hallucinations_removed": 0, "dedup_removed": 0, "term_fixes": []}
    if not text:
        return text, stats

    converted = to_taiwan_traditional(text)
    stats["opencc"] = converted != text

    cleaned, hallucinated = remove_hallucination_lines(converted)
    stats["hallucinations_removed"] = hallucinated

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


def ensure_record_structure(summary: str) -> str:
    """確保會議紀錄具有完整的公務欄位結構（容錯比對，缺漏者補「（待確認）」骨架）。"""
    missing_text = MISSING_TEXT
    default_fallback_line = f"- {missing_text}（主辦單位：{missing_text}，辦理期程：{missing_text}）"
    cleaned = (summary or "").strip()

    cleaned = re.sub(r"^```(?:markdown)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\n?```$", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    header_lines: list[str] = []
    section_lines: list[str] = []
    # 欄位存在性採容錯 regex（允許空格數量差異與全半形冒號），輸出統一為標準格式
    required_fields = [
        ("會議名稱", missing_text, re.compile(r"^會議名稱\s*[:：]", re.MULTILINE)),
        ("會議時間", missing_text, re.compile(r"^會議時間\s*[:：]", re.MULTILINE)),
        ("會議地點", missing_text, re.compile(r"^會議地點\s*[:：]", re.MULTILINE)),
        ("主  席", missing_text, re.compile(r"^主\s*席\s*[:：]", re.MULTILINE)),
        ("出席人員", missing_text, re.compile(r"^出席人員\s*[:：]", re.MULTILINE)),
        ("列席人員", "無", re.compile(r"^列席人員\s*[:：]", re.MULTILINE)),
        ("記  錄", "AI 會議助理", re.compile(r"^記\s*錄\s*[:：]", re.MULTILINE)),
    ]
    for field, default, pattern in required_fields:
        if not pattern.search(cleaned):
            header_lines.append(f"{field}：{default}")

    if not re.search(r"一、\s*報告事項", cleaned):
        section_lines.extend(["一、 報告事項：", "無"])

    if not re.search(r"二、\s*討論事項", cleaned):
        section_lines.extend([
            "二、 討論事項：",
            f"案由：{missing_text}",
            f"說明：{missing_text}",
            "各單位意見（多方立場）：",
            f"- {missing_text}：{missing_text}",
            "決議：",
            f"1. {missing_text}（主辦單位：{missing_text}，協辦單位：{missing_text}）",
        ])
    else:
        if not re.search(r"案由\s*[:：]", cleaned):
            section_lines.append(f"案由：{missing_text}")
        if not re.search(r"說明\s*[:：]", cleaned):
            section_lines.append(f"說明：{missing_text}")
        if not re.search(r"各單位意見", cleaned):
            section_lines.extend([
                "各單位意見（多方立場）：",
                f"- {missing_text}：{missing_text}",
            ])
        if not re.search(r"決議\s*[:：]", cleaned):
            section_lines.extend([
                "決議：",
                f"1. {missing_text}（主辦單位：{missing_text}，協辦單位：{missing_text}）",
            ])

    if not re.search(r"三、\s*主席裁示事項", cleaned):
        section_lines.extend(["三、 主席裁示事項（後續管考與追蹤）：", default_fallback_line])
    elif not re.search(r"辦理期程\s*[:：]", cleaned):
        section_lines.append(default_fallback_line)

    if header_lines:
        prefix = "\n".join(header_lines)
        cleaned = f"{prefix}\n\n{cleaned}" if cleaned else prefix

    if section_lines:
        suffix = "\n".join(section_lines)
        cleaned = f"{cleaned}\n\n{suffix}" if cleaned else suffix

    return cleaned.strip()


def finalize_record(summary: str, protected_terms: Optional[set[str]] = None) -> str:
    """會議紀錄的完整記錄級後處理（驗證前呼叫，此後不得再改寫本文）。"""
    cleaned = remove_english_segments(summary or "", protected_terms=protected_terms)
    cleaned = sanitize_text_language(cleaned)
    cleaned = to_taiwan_traditional(cleaned)
    if has_excessive_english(cleaned):
        log.warning("[品質] 會議紀錄仍含較多英文詞彙，請人工抽查輸出內容")
    return ensure_record_structure(cleaned)
