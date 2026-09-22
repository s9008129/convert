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
from typing import Optional, Set

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
    v4.8.0 起兩條生成路徑都套用（地端紀錄的未填佔位符實測是雲端的 3 倍以上）。
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


# ---------------------------------------------------------------------------
# 會議紀錄契約後處理（T20260922-1930-01 軌 A；僅地端路徑套用，雲端輸出不動）
# 詞彙修正（W3）→ 彙整表出處標註清除（W2b）→ 跨節重複抑制（W5，最後一步）
# ---------------------------------------------------------------------------

# 發言來源標註樣式；與 SummarizationService._SOURCE_TAG_PATTERN 同式
# （雲端發言來源絆索與本處表格清理共用同一契約，兩者不得各自漂移）。
SOURCE_TAG_PATTERN = re.compile(r"（[^）]{0,24}?\d{1,2}:\d{2}(?::\d{2})?[^）]{0,12}?）")

# 只認 Markdown 表格列（行首可縮排的直線符號）；正文行一律不進清理範圍。
# TABLE_ROW_PATTERN 是「表格列」定義的公開單一來源（2026-09-22）：本檔 W2b 清除器
# 與 E2E 量測儀器（軌 C）共用同一份定義，且與 section_meeting 的 forbidden_patterns
# 「彙整表內出現發言來源標註」（`^\|`）語意一致，三處不得各自漂移。
# `_TABLE_ROW_PATTERN` 保留為相容別名（同一個 compiled pattern 物件）。
TABLE_ROW_PATTERN = re.compile(r"^\s*\|")
_TABLE_ROW_PATTERN = TABLE_ROW_PATTERN
# 移除標註時一併吃掉緊接在前的分隔空白與頓號／逗號／分號，避免留下懸空標點。
_TABLE_SOURCE_TAG_STRIP_PATTERN = re.compile(
    r"[ \t\u3000]*[、，,；;]?[ \t\u3000]*(?:" + SOURCE_TAG_PATTERN.pattern + r")"
)
# 模板契約禁止彙整表標註的判定片段（section_meeting 的 forbidden label 含此字串）。
_TABLE_SOURCE_TAG_FORBIDDEN_LABEL = "發言來源標註"


def template_forbids_table_source_tags(template) -> bool:
    """模板契約是否禁止彙整表列出發言來源標註（2026-09-22；W2b）。

    以 `forbidden_patterns` 的標籤判定（不寫死模板 id）：section_meeting 的
    「彙整表內出現發言來源標註」含此片段；general 等模板沒有這條契約，
    因此表格內容完全不動。template=None 或缺屬性時一律回 False。
    """
    for label, _pattern in getattr(template, "forbidden_patterns", ()) or ():
        if _TABLE_SOURCE_TAG_FORBIDDEN_LABEL in label:
            return True
    return False


def strip_source_tags_from_table_rows(text: str, template=None) -> tuple[str, int]:
    """移除彙整表列的發言來源標註，回傳（清理後文字, 移除的標註數）。

    W2b：模型把出處標註寫進四欄彙整表，違反 section_meeting 的 forbidden 契約，
    且會原樣流入「列管資料」附件（附件是確定性抽取、不清洗）。提示詞兩輪無效，
    故以確定性後處理移除。

    僅在模板契約禁止表格標註時啟用（`template_forbids_table_source_tags`），
    且只動 `^\\s*\\|` 的表格列；正文（含正文句末標註）與其他模板一個字都不改。
    """
    if not text or not template_forbids_table_source_tags(template):
        return text, 0

    lines = text.split("\n")
    removed = 0
    for index, line in enumerate(lines):
        if not TABLE_ROW_PATTERN.match(line):
            continue
        cleaned, count = _TABLE_SOURCE_TAG_STRIP_PATTERN.subn("", line)
        if count:
            lines[index] = cleaned
            removed += count
    if not removed:
        return text, 0
    return "\n".join(lines), removed


def apply_record_term_fixes(
    text: str, fixes: tuple[tuple[str, str], ...]
) -> tuple[str, list[tuple[str, str]]]:
    """套用紀錄級詞彙修正清單，回傳（修正後文字, 實際命中的規則）。

    W3：形狀同 `apply_official_term_fixes`；`fixes` 由模板宣告
    （`MeetingTemplate.record_term_fixes`），只回報「實際命中」的規則，
    未命中的規則不影響文字、也不出現在回傳清單。
    """
    if not text or not fixes:
        return text, []
    changes: list[tuple[str, str]] = []
    fixed = text
    for pattern, replacement in fixes:
        compiled = re.compile(pattern)
        if compiled.search(fixed):
            changes.append((pattern, replacement))
            fixed = compiled.sub(replacement, fixed)
    return fixed, changes


# ---------------------------------------------------------------------------
# 跨章節重複抑制（W5；general 紀錄的「決議」節 vs「主席裁示事項」節）
# ---------------------------------------------------------------------------

# 重複條目在決議節的替代文字；整節皆重複時改寫單行「無」。
_DEDUPE_REPLACEMENT_LINE = "（與主席裁示事項重複，詳見該節）"
_DEDUPE_EMPTY_SECTION_LINE = "無"
_DONOR_SECTION_KEYWORD = "主席裁示事項"

# 決議節標題（可帶編號與冒號）；僅認整行都是標題者，避免誤抓內文提及。
_DECISIONS_HEADING_PATTERN = re.compile(
    r"^\s*(?:[一二三四五六七八九十0-9]+[、.]?\s*)?決議\s*[:：]?\s*$"
)
# 章節層級標題（界定章節邊界用）。
_CHAPTER_HEADING_PATTERN = re.compile(
    r"^\s*[（(]?[一二三四五六七八九十壹貳參肆伍陸柒捌玖拾百0-9０-９]+[）).、．]?\s*"
    r"(?:主席裁示事項|報告事項|討論事項|臨時動議|散會|其他事項)"
)
# 行首編號／項目符號（最多剝三層，如「（一） 1、」）。
_LEADING_NUMBERING_PATTERN = re.compile(
    r"^\s*(?:"
    r"[（(][0-9０-９一二三四五六七八九十百]{1,4}[）)]"
    r"|[0-9０-９一二三四五六七八九十百]{1,4}[、．.,)）]"
    r"|[-*・·‧]+"
    r")\s*"
)
# 標點統一（全形→半形；只用於比對，不寫回文件）。
_DEDUPE_PUNCTUATION_UNIFY_TABLE = str.maketrans(
    {
        "（": "(", "）": ")", "：": ":", "，": ",", "、": ",", "；": ";",
        "。": ".", "！": "!", "？": "?", "「": '"', "」": '"', "［": "[",
        "］": "]", "【": "[", "】": "]",
    }
)
# 比對前移除所有標點與空白（含全形空白）。
_DEDUPE_PUNCTUATION_STRIP_PATTERN = re.compile(
    r"[\s\u3000、，,。．；;：:！!？?「」『』（）()［］【】\[\]｛｝{}·…—–\-~～\"'“”‘’]+"
)
# 行尾「（主辦單位…協辦單位…辦理期程…）」metadata 區塊的起點。
_METADATA_BLOCK_START_PATTERN = re.compile(r"[（(]主辦單位")
# 佔位欄位行（主辦單位／協辦單位／辦理期程）永不參與判重。
_METADATA_FIELD_LINE_PATTERN = re.compile(r"^\s*(?:主辦單位|協辦單位|辦理期程)\s*[:：]")
# 判重門檻：正規化後扣掉固定欄位名與佔位值，仍須留有 >=2 個漢字的實詞。
_DEDUPE_STOPWORD_PATTERN = re.compile(
    r"(?:主辦單位|協辦單位|辦理期程|待確認|未定|同上|略|無)+"
)
_DEDUPE_SUBSTANTIVE_PATTERN = re.compile(r"[一-鿿]{2,}")


def _strip_leading_numbering(line: str) -> str:
    """去除行首編號／項目符號（最多三層，如「（一） 1、 內容」）。"""
    text = line.strip()
    for _ in range(3):
        stripped = _LEADING_NUMBERING_PATTERN.sub("", text)
        if stripped == text:
            break
        text = stripped
    return text


def _cut_trailing_metadata_block(text: str) -> str:
    """切除行尾的「（主辦單位…）」metadata 區塊（括號內可再嵌套括號）。"""
    last_match = None
    for match in _METADATA_BLOCK_START_PATTERN.finditer(text):
        last_match = match
    if last_match is None:
        return text
    tail = text[last_match.start():].rstrip()
    if not tail.endswith(("）", ")")):
        return text
    return text[: last_match.start()].rstrip()


def _normalize_dedupe_key(line: str) -> str:
    """判重用的正規化字串（編號→標點統一→去空白→切 metadata→去標點）。"""
    text = _strip_leading_numbering(line)
    text = text.translate(_DEDUPE_PUNCTUATION_UNIFY_TABLE)
    text = re.sub(r"\s+", "", text)
    text = _cut_trailing_metadata_block(text)
    return _DEDUPE_PUNCTUATION_STRIP_PATTERN.sub("", text)


def _is_dedupe_candidate(line: str) -> bool:
    """是否為可判重的條目行（標題／佔位欄位／表格列一律排除）。"""
    stripped = line.strip()
    if not stripped or stripped.startswith("|"):
        return False
    content = _strip_leading_numbering(stripped)
    if not content:
        return False
    # 標題：去編號後以冒號收尾（如「決議：」「一、 組織規程與編制異動：」）。
    if content.endswith(("：", ":")):
        return False
    if _METADATA_FIELD_LINE_PATTERN.match(content):
        return False
    normalized = _normalize_dedupe_key(line)
    residue = _DEDUPE_STOPWORD_PATTERN.sub("", normalized)
    return bool(_DEDUPE_SUBSTANTIVE_PATTERN.search(residue))


def dedupe_cross_section_items(text: str, template=None) -> tuple[str, int]:
    """抑制「決議」節與「主席裁示事項」節之間的逐條重複（W5）。

    只在 general 紀錄（使用者 13:49 失敗場）發生：同一批條目同時寫進決議與
    主席裁示事項。判準極窄——正規化（去編號→標點統一→去空白→切除行尾
    「（主辦單位…）」metadata→去標點）後**完全相等**、留有實詞、且非標題／
    非佔位欄位，才算重複；保留 metadata 較完整的主席裁示（donor），決議節的
    重複條目改寫為「（與主席裁示事項重複，詳見該節）」，整節皆重複則寫「無」。

    防禦性邊界：沒有「主席裁示事項」節、沒有「決議」節即原樣回傳；
    作用域依 plan §3 W5 限縮為 general-only（2026-09-22 稽核修正）——只有
    template=None（fixture 直接呼叫）或 template.id == "general" 才處理，
    其餘模板（section_meeting／isms_monthly／procurement_evaluation 等）一律
    原樣回傳，不把未核准的模板語意納入改寫面。必須是
    `_finalize_record_text` 的最後一步。
    """
    if not text:
        return text, 0
    if template is not None and getattr(template, "id", None) != "general":
        return text, 0

    lines = text.split("\n")
    donor_index = None
    for index, line in enumerate(lines):
        if _DONOR_SECTION_KEYWORD in line and _CHAPTER_HEADING_PATTERN.match(line):
            donor_index = index
            break
    if donor_index is None:
        return text, 0

    target_index = None
    for index in range(donor_index):
        if _DECISIONS_HEADING_PATTERN.match(lines[index]):
            target_index = index
            break
    if target_index is None:
        return text, 0

    donor_end = len(lines)
    for index in range(donor_index + 1, len(lines)):
        if _CHAPTER_HEADING_PATTERN.match(lines[index]) and _DONOR_SECTION_KEYWORD not in lines[index]:
            donor_end = index
            break

    donor_keys = {
        _normalize_dedupe_key(line)
        for line in lines[donor_index + 1: donor_end]
        if _is_dedupe_candidate(line)
    }
    donor_keys.discard("")
    if not donor_keys:
        return text, 0

    item_indexes = [
        index
        for index in range(target_index + 1, donor_index)
        if _is_dedupe_candidate(lines[index])
    ]
    removed_indexes = [
        index
        for index in item_indexes
        if _normalize_dedupe_key(lines[index]) in donor_keys
    ]
    if not removed_indexes:
        return text, 0

    new_lines = list(lines)
    for index in removed_indexes:
        new_lines[index] = _DEDUPE_REPLACEMENT_LINE
    if len(removed_indexes) == len(item_indexes):
        start, end = min(removed_indexes), max(removed_indexes)
        removed_set = set(removed_indexes)
        if all(index in removed_set for index in range(start, end + 1)):
            # 整節皆為重複：以單行「無」取代，不留一排指向同一節的提示。
            new_lines[start: end + 1] = [_DEDUPE_EMPTY_SECTION_LINE]

    log.info("[品質] 跨節重複抑制：移除決議節重複條目 {} 條", len(removed_indexes))
    return "\n".join(new_lines), len(removed_indexes)

# ---------------------------------------------------------------------------
# 出處標註真實性（T20260922-2037-02 軌 A；P1-14 的確定性部分）
#
# 實測（0903 場、v4.8.1、MoE 35B）：27 個正文標註中有 23 個的時間戳「不存在於
# 逐字稿的任何段落起點」——模型寫得出標註，但時間戳多半是憑印象生成的。同一份
# 紀錄的 25/27 個時間戳其實**落在**該發言者的真實段落內；也就是說，錯的不是
# 「指到誰、指到哪一段」，而是「指到段落裡的一個不存在的秒數」。
#
# 因此這裡不去問模型、也不重寫內容，只做一件事：把時間戳吸附到它所屬的真實
# 段落邊界（``[start-end] 發言者N：`` 的 start）。這是確定性、可稽核、可回復的
# 後處理，且只作用於有 ``speaker_traceability`` 契約的模板。
# ---------------------------------------------------------------------------

# ASR 逐字稿的段落列：``[00:07:11-00:07:16] 發言者1：…``
# （小時允許 1–3 位：103 分鐘以上的會議會出現 ``01:43:00``；時間戳與破折號間
# 允許空白，因為不同 ASR 來源的格式略有差異）。
TRANSCRIPT_SEGMENT_PATTERN = re.compile(
    r"^\[(\d{1,3}):(\d{2}):(\d{2})\s*-\s*(\d{1,3}):(\d{2}):(\d{2})\]\s*([^：:]{1,24})[：:]"
)
# 標註內容裡的時間戳（``（發言者1，00:03:45）``）。
SOURCE_TAG_TIME_PATTERN = re.compile(r"(\d{1,3}):(\d{2})(?::(\d{2}))?")
# 「同一發言者最近段落」的吸附容忍距離（秒）。超過此距離視為不可回溯、原樣保留。
TAG_SNAP_TOLERANCE_SECONDS = 180
# 吸附的位移上限（秒）：精確度保護。實測 183 段的段落長度中位數 3 秒、p90 28 秒，
# 但也有 336 秒的開場長段；若原時間戳落在長段中間，硬吸附到段首會把「大概第 4 分半」
# 變成「00:00:00」，反而更難查。因此位移超過此值時保留原時間戳（仍在真實段落內）。
TAG_SNAP_MAX_SHIFT_SECONDS = 120
# 標註內「發言者標籤」與時間戳之間的分隔符。
_SPEAKER_LABEL_STRIP_CHARS = "，,、;；:： 	　"


def _hms_to_seconds(hours: str, minutes: str, seconds: str) -> int:
    """``HH:MM:SS`` 三欄字串轉秒數（純函式，供段落與標註共用）。"""
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds)


def _segment_contains(segment, seconds: int) -> bool:
    """段落是否含此秒數：語意為**閉區間** ``[start, end]``（v1.x 歷史語意）。

    零長度段落（``end <= start``，實測逐字稿可能出現）退化為單點 ``start``，
    否則它永遠不可能命中，該段的標註會全部變成不可回溯。

    為什麼是閉區間而非半開：逐字稿段落之間可能有**空隙**（前段 ``end`` 與
    後段 ``start`` 之間沒有人講話）。若用半開區間，一個「恰為某段 ``end``
    且不為任何段 ``start``」的時間戳會變成「不在任何段落內」＝不可回溯，
    而它其實落在真實段落內、而且是最靠近該段內容的位置（實測 C1：唯一真正
    被修正的 ``00:10:04 → 00:08:15`` 就屬此類）。R24 的真正根因不是閉區間
    本身，而是「取第一個命中的段落」這個**順序**（見 `_pick_containing_segment`）。
    """
    start, end = segment[0], segment[1]
    if end <= start:
        return seconds == start
    return start <= seconds <= end


def _pick_containing_segment(segments, seconds: int):
    """回傳含此秒數的段落（閉區間），沒有則回 ``None``。

    優先序：``start == seconds``（段首命中）優先於其他命中的段落。
    由於吸附落點一律是某段 ``start``，而 `snap_source_tags_to_transcript`
    另有「全域段首保護」與「精度保護」兩道條件，落點才會是不動點
    （``f(f(x)) == f(x)``）——但冪等性的**保證來源是那兩道條件**，
    本函式只是輔助（見其 docstring）。

    T20260922-2037-02（R24）的真正根因就在這裡的**順序**：v1.0 是
    「閉區間 ＋ 取第一個命中的段落」，當時間戳恰好等於相鄰兩段的交界
    （``前段.end == 後段.start``）時，清單中**先出現的前一段**勝出，
    於是標註被吸回前一段起點＝**倒退一格**（C1 驗收：7 個被改寫的值中 6 個
    是倒退，例 ``00:18:09 → 00:18:06``）。段首優先修好了「同一份清單內」的交界，
    但**跨發言者交界**（後一段屬別的發言者，故不在同一份清單裡）仍會後退；
    完整修正因此分成兩層：本函式的段首優先 ＋ 呼叫端的全域段首保護。
    """
    fallback = None
    for segment in segments:
        if segment[0] == seconds:
            return segment
        if fallback is None and _segment_contains(segment, seconds):
            fallback = segment
    return fallback


def _seconds_to_hms(total_seconds: int, *, with_seconds: bool) -> str:
    """秒數轉回 ``HH:MM(:SS)``；``with_seconds`` 依原標註的精度決定。"""
    hours, remainder = divmod(max(0, int(total_seconds)), 3600)
    minutes, seconds = divmod(remainder, 60)
    if with_seconds:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{hours:02d}:{minutes:02d}"


def _normalize_speaker_label(label: str) -> str:
    """發言者標籤正規化（去空白）；逐字稿與標註的空白慣例可能不同。"""
    return re.sub(r"\s+", "", label or "")


def iter_transcript_segments(transcript: str) -> list:
    """解析逐字稿段落時間表，回傳 ``[(start_seconds, end_seconds, speaker)]``。

    只認行首 ``[start-end] 發言者：`` 的段落列（逐字稿產生器的固定格式）；
    「發言者統計」那種 ``- 發言者1：00:37:28（…）`` 的累計時長列刻意不認，
    因為它們不是段落。
    """
    segments = []
    for raw_line in (transcript or "").splitlines():
        match = TRANSCRIPT_SEGMENT_PATTERN.match(raw_line.strip())
        if not match:
            continue
        start = _hms_to_seconds(*match.group(1, 2, 3))
        end = _hms_to_seconds(*match.group(4, 5, 6))
        if end < start:
            start, end = end, start
        segments.append((start, end, match.group(7).strip()))
    return segments


def template_supports_source_tags(template) -> bool:
    """模板是否有「發言來源標註」契約（``speaker_traceability``）。"""
    return bool(getattr(template, "speaker_traceability", False))


def snap_source_tags_to_transcript(text: str, transcript: str, template=None) -> tuple:
    """把發言來源標註的時間戳吸附到逐字稿的真實段落邊界，回傳（文字, 統計）。

    規則（依序，全部確定性）：

    0. **全域段首保護**：時間戳若已是**任一**真實段落的起點 → 原樣保留
       （``kept_on_start``）。段落區間語意是**閉區間** ``[start, end]``：
       時間戳恰為某段 ``end`` 但非任何段 ``start`` 時仍算「落在該段內」
       （段落之間可能有空隙），因此不會變成不可回溯。
    1. 標註的發言者標籤在逐字稿中存在，且時間戳落在該發言者的某段落內
       → 吸附到該段落的 ``start``（``snapped_exact``）。
    2. 否則，同發言者最近的段落 ``start`` 距離 ≤ ``TAG_SNAP_TOLERANCE_SECONDS``
       → 吸附（``snapped_nearest``）；模型只寫「大概幾秒」時仍可回溯。
    3. 否則，時間戳落在**任何**真實段落內（發言者標籤與逐字稿不同名時）
       → 吸附到該段落 ``start``（``snapped_speaker_mismatch``，時間為真、
       發言者標籤維持模型原文——不代模型改歸屬）。
    4. **精度保護**：原標註是 ``HH:MM``（無秒）而目標段首**不是整分鐘**
       （``target % 60 != 0``）→ 原樣保留（``kept_precision``）。理由：渲染
       無秒標註必須捨秒，採用該目標會讓「換出來的值」不等於目標，二次套用
       會再往更早的段落吸（實測鏈式後退 ``00:03 → 00:02 → 00:00``，
       見下方 rev 10 說明）。與 ``kept_far`` 同精神：精度不足時不硬改。
    5. 其餘（找不到任何依據）→ 原樣保留並計入 ``untraceable``。

    fail-soft：任何一步不成立都保留原標註（不刪、不改寫、不動內文），因此
    最壞情況與現行行為完全相同；只有「時間戳確實對得上逐字稿」時才會替換。

    T20260922-2037-02（P3 波，R24／R26）：v1.0 取「第一個命中的段落」，於是
    「時間戳恰好等於前一段 ``end``（＝後一段 ``start``）」會被吸回前一段起點＝
    **倒退一格**（C1 獨立驗收：7 個實際被改寫的值中 6 個是倒退，例
    ``00:18:09 → 00:18:06``）；且因為落點仍是真實段首，主指標
    ``on_start_tag_ratio`` 完全無感（指標盲區）。

    v1.1／rev 10 的保證由三件事**共同**構成（獨立審查 attempt-07 的 R1／R3、
    attempt-08 的 R1 反例修正）：
    ①**全域段首保護**（規則 0）：時間戳若已是**任一**真實段落起點 → 原樣保留；
    ②**所有吸附落點都只能是某段 ``start``**（規則 1／2／3 的 target 定義）；
    ③**精度保護**（規則 4）：``HH:MM`` 標註的目標必須是整分鐘才採用。
    三者合起來才足以保證「已是段首的值不被搬動」，且**所有被接受的值都是不動點**
    （``f(f(x)) == f(x)``）——含秒標註渲染可逆（``HH:MM:SS`` 還原相等）、
    無秒標註則一律落在整分鐘上，故第二輪必為規則 0 或規則 4 接住。
    **後退幅度（如實，rev 12／審查 attempt-09 R4）**：規則 1（段落內）與規則 3
    （跨發言者命中）的落點必在時間戳所屬段落內或該段落起點；但**規則 2（nearest 容忍，
    ``TAG_SNAP_TOLERANCE_SECONDS``＝180 s）例外**——時間戳落在**別的**發言者段落內時，
    會吸到「該發言者最近的真實段首」，該段首可能**早於**原時間戳所在段落，即**跨段後退**
    （最小反例：``[00:00:02-00:00:32] 發言者2``／``[00:00:32-00:01:02] 發言者1``
    ＋``（發言者2，00:00:34）``→ ``00:00:02``，Δ32 s；仍冪等）。此行為**非本波引入**
    （v1.0 同輸出），列為已知限制（plan §8.7 風險⑤），本波只如實限縮宣稱、不改行為。
    只做「同發言者清單內段首優先」不夠：反例是「跨發言者的交界」
    （前一段 ``end`` ＝ 後一段 ``start``，而後一段屬於別的發言者），此時同發言者
    清單裡沒有 ``start == 時間戳`` 的段落，仍會吸回前一段起點並可再往後退
    （實測 A1 素材 12 筆被改寫、其中 9 筆原值已是全域真實段首，
    例 ``00:13:37 → 00:13:12``）。同理只做①②也不夠：``（科長，00:03）`` 這種
    無秒標註會先被吸到 ``00:02:42``，渲染成 ``00:02`` 後再被吸到 ``00:00``
    ＝鏈式後退（審查 attempt-08 R1；實測真實素材 228 個標註中 0 個無秒，
    但產品樣式允許 ``HH:MM``，屬可達輸入類）。
    區間語意維持閉區間：改用半開區間雖然也能不退化，但會把「恰為某段 ``end``
    且非任何段 ``start``」的良性吸附打成不可回溯（實測 C1 唯一真修正
    ``00:10:04 → 00:08:15``），且該段時間戳其實仍在真實段落內。
    """
    stats = {
        "segments": 0,
        "tags": 0,
        "snapped": 0,
        "changed": 0,
        "snapped_exact": 0,
        "snapped_nearest": 0,
        "snapped_speaker_mismatch": 0,
        "kept_on_start": 0,
        "kept_precision": 0,
        "backward_moves": 0,
        "forward_moves": 0,
        "max_backward_seconds": 0,
        "kept_far": 0,
        "untraceable": 0,
    }
    if not text or not transcript or not template_supports_source_tags(template):
        return text, stats
    segments = iter_transcript_segments(transcript)
    stats["segments"] = len(segments)
    if not segments:
        return text, stats

    by_speaker: dict = {}
    for segment in segments:
        by_speaker.setdefault(_normalize_speaker_label(segment[2]), []).append(segment)

    def replace_tag(match: "re.Match") -> str:
        stats["tags"] += 1
        tag = match.group()
        inner = tag[1:-1]
        time_match = SOURCE_TAG_TIME_PATTERN.search(inner)
        if not time_match:
            stats["untraceable"] += 1
            return tag
        seconds = _hms_to_seconds(
            time_match.group(1), time_match.group(2), time_match.group(3) or "0"
        )
        # 規則 0（v1.1，R26）：全域段首保護。時間戳若已是**任一**真實段落的起點，
        # 一律原樣保留——這是「已是段首的值不被搬動」與「冪等」的必要條件
        # （註：規則 2 的 nearest 容忍仍可能跨段後退，見本函式 docstring 的如實界定）：
        # 只靠「同發言者清單內段首優先」擋不住跨發言者交界（前段 end ＝ 後段 start，
        # 而後段屬別的發言者時，同發言者清單內沒有任何 start 等於此時間戳）。
        if any(seg[0] == seconds for seg in segments):
            stats["kept_on_start"] += 1
            return tag
        speaker_label = _normalize_speaker_label(
            inner[: time_match.start()].strip(_SPEAKER_LABEL_STRIP_CHARS)
        )
        target = None
        status = ""
        same_speaker = by_speaker.get(speaker_label, ())
        if same_speaker:
            containing = _pick_containing_segment(same_speaker, seconds)
            if containing is not None:
                target, status = containing[0], "exact"
            else:
                nearest = min(same_speaker, key=lambda seg: abs(seg[0] - seconds))
                if abs(nearest[0] - seconds) <= TAG_SNAP_TOLERANCE_SECONDS:
                    target, status = nearest[0], "nearest"
        if target is None:
            containing_any = _pick_containing_segment(segments, seconds)
            if containing_any is not None:
                target, status = containing_any[0], "speaker_mismatch"
        if target is None:
            stats["untraceable"] += 1
            return tag

        if abs(target - seconds) > TAG_SNAP_MAX_SHIFT_SECONDS:
            # 位移過大（長段落）→ 保留模型原時間戳：它仍在真實段落內，不會造假，
            # 但硬拉到段首會損失精確度。
            stats["kept_far"] += 1
            return tag

        with_seconds = time_match.group(3) is not None
        # 規則 4（rev 10，審查 attempt-08 R1）：精度保護。`HH:MM` 標註渲染時
        # 必然捨秒，若目標段首不是整分鐘，採用 replacement 會產生一個「不等於
        # 目標」的值（例 target=162s 渲染成 `00:02`＝120s）→ 第二輪再從 120s
        # 往更早的段落吸（`00:03 → 00:02 → 00:00` 鏈式後退），破壞冪等。
        # 只在 render/parse 可逆（含秒，或目標為整分鐘）時才採用。
        if not with_seconds and target % 60 != 0:
            stats["kept_precision"] += 1
            return tag
        replacement = _seconds_to_hms(target, with_seconds=with_seconds)
        stats["snapped"] += 1
        stats[f"snapped_{status}"] += 1
        if target < seconds:
            # 觀察值（非閘門）：往前收的幅度。段落內吸附本來就會往段首退，
            # 因此它不是 0 是正常的；規則 2 的 nearest 容忍另可跨段後退（v1.0 同）；
            # 它的用途是「精度損失幅度」的量測，
            # 以及與 v1.0 的「跨段後退」對照（後者會同時讓冪等性失效）。
            stats["backward_moves"] += 1
            stats["max_backward_seconds"] = max(
                stats["max_backward_seconds"], seconds - target
            )
        elif target > seconds:
            stats["forward_moves"] += 1
        if replacement == time_match.group():
            return tag
        stats["changed"] += 1
        new_inner = inner[: time_match.start()] + replacement + inner[time_match.end():]
        return f"（{new_inner}）"

    return SOURCE_TAG_PATTERN.sub(replace_tag, text), stats


def measure_tag_traceability(text: str, transcript: str) -> dict:
    """標註可回溯性量測（量測儀器與產品共用同一份定義），回傳純量統計。

    * ``tags_total``：正文標註數（含表格列；表格標註另由 E2E 契約清除）。
    * ``tags_inside_any_segment``／``traceable_tag_ratio``：時間戳落在逐字稿任一
      真實段落內（＝「這個時間點會議真的在進行」）。段落區間語意與吸附一致
      （閉區間 ``[start, end]``，含段落間空隙的邊界時間戳），避免量尺與產品
      對同一份逐字稿給出不同答案。
    * ``tags_on_real_segment_start``／``on_start_tag_ratio``：時間戳恰好等於**任一**真實
      段落起點（吸附後的主指標；不看發言者標籤，因為模型可能用「科長」等角色名）。
    * ``tags_exact_segment_start``／``exact_tag_ratio``：時間戳恰為某段起點**且**發言者
      標籤與該段發言者一致（嚴格版，角色名標註不計入）。
    * ``tags_inside_same_speaker_segment``：時間戳落在**該標註指名發言者**的段落內
      （＝「這個時間點確實在講這句話」）。
    * ``zero_time_tag_count``／``zero_time_tag_ratio``：時間戳為 ``00:00:00`` 的標註數
      （會議起點；結構上必然「落在段落起點」，會膨脹 ``on_start_tag_ratio``，故單獨列出）。
    * ``distinct_tag_time_count``／``distinct_tag_time_ratio``：不同時間戳個數／比例
      （＝標註的辨別力；模型大量重複同一時間戳時會偏低）。
    * ``on_start_tag_ratio_excluding_zero``：排除 ``00:00:00`` 後的段落起點命中率
      （分母＝非 ``00:00:00`` 的標註數；比 ``on_start_tag_ratio`` 嚴格且模型無關）。
    """
    segments = iter_transcript_segments(transcript)
    total = inside_any = exact = inside_same = on_start = 0
    zero_time = on_start_nonzero = 0
    tag_times: Set[int] = set()
    for match in SOURCE_TAG_PATTERN.finditer(text or ""):
        inner = match.group()[1:-1]
        time_match = SOURCE_TAG_TIME_PATTERN.search(inner)
        if not time_match:
            continue
        total += 1
        seconds = _hms_to_seconds(
            time_match.group(1), time_match.group(2), time_match.group(3) or "0"
        )
        speaker_label = _normalize_speaker_label(
            inner[: time_match.start()].strip(_SPEAKER_LABEL_STRIP_CHARS)
        )
        tag_times.add(seconds)
        if seconds == 0:
            zero_time += 1
        if any(_segment_contains(seg, seconds) for seg in segments):
            inside_any += 1
        if any(seg[0] == seconds for seg in segments):
            on_start += 1
            if seconds != 0:
                on_start_nonzero += 1
        if any(
            _normalize_speaker_label(seg[2]) == speaker_label and seg[0] == seconds
            for seg in segments
        ):
            exact += 1
        if any(
            _normalize_speaker_label(seg[2]) == speaker_label
            and _segment_contains(seg, seconds)
            for seg in segments
        ):
            inside_same += 1
    return {
        # 量尺版本：欄位語意變更時必須遞增，避免同名指標跨版本被直接比較
        # （獨立審查 F2：on_start_tag_ratio_excluding_zero 的分母曾在驗收期間由「總數」改為「非零數」）。
        "metric_version": "tag_traceability-1.1.0",
        "segments": len(segments),
        "tags_total": total,
        "tags_inside_any_segment": inside_any,
        "traceable_tag_ratio": (inside_any / total) if total else None,
        "tags_exact_segment_start": exact,
        "exact_tag_ratio": (exact / total) if total else None,
        "tags_on_real_segment_start": on_start,
        "on_start_tag_ratio": (on_start / total) if total else None,
        "tags_on_real_segment_start_excluding_zero": on_start_nonzero,
        "on_start_tag_ratio_excluding_zero": (
            on_start_nonzero / (total - zero_time) if total - zero_time > 0 else None
        ),
        "tags_inside_same_speaker_segment": inside_same,
        "zero_time_tag_count": zero_time,
        "zero_time_tag_ratio": (zero_time / total) if total else None,
        "distinct_tag_time_count": len(tag_times),
        "distinct_tag_time_ratio": (len(tag_times) / total) if total else None,
    }
