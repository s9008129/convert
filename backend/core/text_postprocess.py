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
