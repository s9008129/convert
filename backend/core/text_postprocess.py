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
    """套用公務用字白名單＋詞彙表已知誤辨，回傳（修正後文字, 修正對照清單）。

    兩層來源：
    1. `_OFFICIAL_TERM_FIXES`：內建公務用字（regex，可含 lookahead）。
    2. 詞彙表 `data/glossary/*.txt` 的 `錯誤寫法=>正確寫法`：資料驅動、確定性、
       與模型無關——被測模型能力再弱，資料檔登錄的固定誤辨仍一定被修好。
    """
    if not text:
        return text, []
    changes: list[tuple[str, str]] = []
    fixed = text
    for pattern, replacement in _OFFICIAL_TERM_FIXES:
        if pattern.search(fixed):
            changes.append((pattern.pattern, replacement))
            fixed = pattern.sub(replacement, fixed)

    from backend.core.glossary import apply_known_corrections

    fixed, applied = apply_known_corrections(fixed)
    for wrong, right, _count in applied:
        changes.append((wrong, right))
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

    P5：同一層再套用詞彙表的確定性誤辨（`data/glossary/*.txt` 的 `錯=>對`），
    讓紀錄層與逐字稿層吃同一份模型無關的詞表（紀錄若又把 `內稽` 寫成 `內機`、
    `差勤` 寫成 `拆勤`，這裡仍修得回來）。此層只在地端路徑執行，雲端輸出不受
    影響（`summarization.py` 於 `mode != "local"` 直接返回）。
    """
    if not text:
        return text, []
    changes: list[tuple[str, str]] = []
    fixed = text
    for pattern, replacement in fixes or ():
        compiled = re.compile(pattern)
        if compiled.search(fixed):
            changes.append((pattern, replacement))
            fixed = compiled.sub(replacement, fixed)

    from backend.core.glossary import apply_known_corrections

    fixed, applied = apply_known_corrections(fixed)
    for wrong, right, _count in applied:
        changes.append((wrong, right))
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
# 規則 6（P4-D，T20260922-2037-02）：同標籤同時戳去重複化的上限——每個
# （發言者標籤, 時間）最多允許幾筆標註共用同一時間戳，其餘改指到同標籤
# ±``TAG_SNAP_MAX_SHIFT_SECONDS`` s 內未被使用的真實段落起點。
# cap=2 為設計期離線模擬 [INFERRED] 的建議值（B2 0.288→0.654、D1 0.667→0.708）；
# cap=3 邊際過薄（B2 僅 0.538），不設限會放寬位移密度。
TAG_DIVERSIFY_MAX_PER_TIME = 2
# 規則 6 bigram 排序用的字元串（漢字／英數混合，數字＋單位如「10月」也算一段）。
_TAG_BIGRAM_RUN_PATTERN = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff0-9A-Za-z]+")
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


def _source_tag_diversify_enabled() -> bool:
    """規則 6 回退開關（``LOCAL_SOURCE_TAG_DIVERSIFY_ENABLED``；預設開啟）。

    ``backend/core/config.py`` 的欄位由同波 W1 新增，本函式以 ``getattr`` 容錯：
    欄位尚未落地（或設定模組不可用）時預設 ``True``，落地後自動生效；
    ``False``＝一行回 P3 行為（吸附輸出 byte 級不變）。欄位名稱兩種寫法都認
    （config 欄位慣例為大寫；規劃文件凍結名為小寫），避免平行實作的命名落差
    讓回退開關失效。
    """
    try:
        from backend.core.config import settings
    except Exception:
        return True
    value = getattr(settings, "LOCAL_SOURCE_TAG_DIVERSIFY_ENABLED", None)
    if value is None:
        value = getattr(settings, "local_source_tag_diversify_enabled", None)
    if value is None:
        return True
    return bool(value)


def _tag_bigrams(text: str) -> set:
    """取文字中的「漢字／英數」字元 bigram 集合（規則 6 的相似度排序依據）。"""
    bigrams: set = set()
    for run in _TAG_BIGRAM_RUN_PATTERN.findall(text or ""):
        run = run.lower()
        for index in range(len(run) - 1):
            bigrams.add(run[index:index + 2])
    return bigrams


def _diversify_source_tag_times(text: str, transcript: str, segments: list, stats: dict) -> str:
    """規則 6：同標籤同時戳去重複化（fail-soft；不新增／不刪除標註）。

    任何內部錯誤（含標註格式異常、逐字稿解析失敗）一律回傳原文字、絕不拋錯——
    規則 6 是品質槓桿，不得讓紀錄生成失敗。
    """
    try:
        return _diversify_source_tag_times_impl(text, transcript, segments, stats)
    except Exception as exc:  # pragma: no cover - 防禦性 fail-soft
        log.warning("[品質] 標註去重複化略過（fail-soft）：{}", exc)
        return text


def _diversify_source_tag_times_impl(text: str, transcript: str, segments: list, stats: dict) -> str:
    """規則 6 實作。語意（決定性、可稽核）：

    1. 合格群組＝同一正規化標籤、同一秒數、出現次數 ≥2、標籤非空、且該秒數
       已是**真實段落起點**（＝規則 0 保留下來的「誠實但攏統」標註）。空標籤
       （正文裡的「（10:30）」）一律不碰。
    2. 每群保留前 ``TAG_DIVERSIFY_MAX_PER_TIME`` 筆（文字順序），其餘依序
       改指到：真實段首、``|Δ| ≤ TAG_SNAP_MAX_SHIFT_SECONDS``、**未被該標籤
       使用過**的秒數；原標註無秒（``HH:MM``）時只接受整分鐘落點（沿用規則 4
       的 render/parse 可逆性論證）。排序：bigram 重疊數高者 → |Δ| 小者 →
       秒數小者。命中即取代時間戳並加入該標籤的已使用集合；無候選則原樣保留。
    3. 不新增／不刪除標註、不改發言者文字；所有落點都是真實段首。

    冪等：一次套用後，每個（標籤, 時間）群組只剩 ≤ cap 筆（搬移落點是該標籤
    獨占的新秒數）；失敗群組的候選集合在第二輪只會更小（已使用集合單調增），
    故 ``f(f(x)) == f(x)``。
    """
    starts: list = []
    start_set: set = set()
    for segment in segments:
        if segment[0] not in start_set:
            start_set.add(segment[0])
            starts.append(segment[0])

    segment_text_by_start: dict = {}
    for raw_line in (transcript or "").splitlines():
        line = raw_line.strip()
        match = TRANSCRIPT_SEGMENT_PATTERN.match(line)
        if not match:
            continue
        start = _hms_to_seconds(*match.group(1, 2, 3))
        segment_text_by_start.setdefault(start, line[match.end():].strip())

    entries: list = []
    for match in SOURCE_TAG_PATTERN.finditer(text):
        inner = match.group()[1:-1]
        time_match = SOURCE_TAG_TIME_PATTERN.search(inner)
        if not time_match:
            # 標註格式異常（無時間戳）→ 原樣保留、不計入規則 6。
            continue
        line_start = text.rfind("\n", 0, match.start()) + 1
        line_end = text.find("\n", match.end())
        if line_end == -1:
            line_end = len(text)
        entries.append(
            {
                "match": match,
                "time_match": time_match,
                "inner": inner,
                "label": _normalize_speaker_label(
                    inner[: time_match.start()].strip(_SPEAKER_LABEL_STRIP_CHARS)
                ),
                "seconds": _hms_to_seconds(
                    time_match.group(1), time_match.group(2), time_match.group(3) or "0"
                ),
                "with_seconds": time_match.group(3) is not None,
                "line_bigrams": _tag_bigrams(text[line_start:line_end]),
            }
        )
    if not entries:
        return text

    used: dict = {}
    groups: dict = {}
    for entry in entries:
        if not entry["label"]:
            continue
        used.setdefault(entry["label"], set()).add(entry["seconds"])
        groups.setdefault((entry["label"], entry["seconds"]), []).append(entry)

    segment_bigrams: dict = {}

    def _candidate_overlap(entry: dict, candidate: int) -> int:
        if candidate not in segment_bigrams:
            segment_bigrams[candidate] = _tag_bigrams(segment_text_by_start.get(candidate, ""))
        return len(entry["line_bigrams"] & segment_bigrams[candidate])

    replacements: list = []
    for (label, seconds), members in groups.items():
        if len(members) < 2 or seconds not in start_set:
            continue
        for entry in members[TAG_DIVERSIFY_MAX_PER_TIME:]:
            candidates = [
                candidate
                for candidate in starts
                if abs(candidate - seconds) <= TAG_SNAP_MAX_SHIFT_SECONDS
                and candidate not in used[label]
                and (entry["with_seconds"] or candidate % 60 == 0)
            ]
            if not candidates:
                stats["diversify_skipped_no_candidate"] += 1
                continue
            target = min(
                candidates,
                key=lambda candidate: (
                    -_candidate_overlap(entry, candidate),
                    abs(candidate - seconds),
                    candidate,
                ),
            )
            used[label].add(target)
            replacement = _seconds_to_hms(target, with_seconds=entry["with_seconds"])
            new_inner = (
                entry["inner"][: entry["time_match"].start()]
                + replacement
                + entry["inner"][entry["time_match"].end():]
            )
            replacements.append(
                (entry["match"].start(), entry["match"].end(), f"（{new_inner}）")
            )
            stats["diversified"] += 1
            stats["diversify_max_shift_seconds"] = max(
                stats["diversify_max_shift_seconds"], abs(target - seconds)
            )

    if not replacements:
        return text
    replacements.sort(key=lambda item: item[0])
    parts: list = []
    cursor = 0
    for start, end, replacement_text in replacements:
        parts.append(text[cursor:start])
        parts.append(replacement_text)
        cursor = end
    parts.append(text[cursor:])
    return "".join(parts)


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
    6. **同標籤同時戳去重複化**（T20260922-2037-02 P4-D）：同一（發言者，時間）
       標註出現多次、且該時間已是真實段首時，保留前 ``TAG_DIVERSIFY_MAX_PER_TIME``
       筆，其餘改指到「同標籤、± ``TAG_SNAP_MAX_SHIFT_SECONDS`` s 內、該標籤
       未使用過」的真實段落起點（bigram 重疊優先；原標註無秒時只接受整分鐘
       落點）。不新增／不刪除標註、不改發言者文字；找不到候選或逐字稿不可用
       一律原樣保留（fail-soft）。回退開關
       ``LOCAL_SOURCE_TAG_DIVERSIFY_ENABLED=false`` 時整步 no-op（輸出與本波
       之前 byte 級相同）。規則 6 冪等：一次套用後每個（標籤, 時間）群組只剩
       ≤ cap 筆、搬移落點是該標籤獨占的新秒數，且失敗群組的候選集合第二輪只會
       更小，故 ``f(f(x)) == f(x)``。

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
        # 規則 6（P4-D）：同標籤同時戳去重複化（獨立於既有指標定義）。
        "diversified": 0,
        "diversify_skipped_no_candidate": 0,
        "diversify_max_shift_seconds": 0,
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

    result = SOURCE_TAG_PATTERN.sub(replace_tag, text)
    if not _source_tag_diversify_enabled():
        return result, stats
    return _diversify_source_tag_times(result, transcript, segments, stats), stats


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


# ---------------------------------------------------------------------------
# P7-B SUPPORTING-1：地端佔位符正規化（2026-09-23；作用域釘死、純函式）
# ---------------------------------------------------------------------------
# 背景：地端模型輸出會出現相鄰重複的「（待確認）（待確認）」（紀錄開頭欄位與標題
# 行）與表格內的多層括號「（（待確認））」。以確定性規則收斂，不用模型、不新增
# 事實；作用域見下方常數與函式 docstring，不得擴大。
#
# 呼叫端契約：僅地端收尾（mode="local"）且 `LOCAL_LLM_PLACEHOLDER_NORMALIZE_EXT`
# 為 True 時由呼叫端呼叫；本函式不讀設定（保持純函式、可單測），雲端路徑不呼叫。

# 開頭欄位／標題行的掃描上限（行數）：本專案最長模板（section_meeting）的開頭
# 骨架（標題→時間／地點／主持人→列管案件→彙整表標題）含空行不超過十餘行，
# 15 行是安全上界；明文禁止全文掃描，正文段落一律不動。
_PLACEHOLDER_HEAD_LINE_LIMIT = 15

# 目標表格標題（行內比對；與 section_meeting._SUMMARY_TABLE_TITLE_PATTERN 同字串，
# 不依賴模板物件）。找不到該表時原樣回傳、不報錯。
_PLACEHOLDER_TARGET_TABLE_TITLE = "決議事項辦理情形彙整表"
# 表格標題與表格之間允許出現的標籤行（模板骨架「決議事項：」；對應
# section_meeting._RESOLUTION_LABEL_PATTERN，不逐字掃其他內容行）。
_PLACEHOLDER_TABLE_LABEL_PATTERN = re.compile(r"^決議事項\s*[:：]\s*$")

# 佔位符核心字串（與 _MISSING_TEXT 同源，不得各自漂移）。
_PLACEHOLDER_INNER_TEXT = _MISSING_TEXT[1:-1]
# 單一佔位符樣式：半形與全形括號視為同一符號。
_PLACEHOLDER_TOKEN_PATTERN = r"[（(]" + re.escape(_PLACEHOLDER_INNER_TEXT) + r"[）)]"
# 相鄰重複的佔位符（≥2 個緊鄰）：收斂成一個，保留第一個出現的原樣（半全形混用亦同）。
_ADJACENT_PLACEHOLDERS_PATTERN = re.compile(
    r"(" + _PLACEHOLDER_TOKEN_PATTERN + r")(?:" + _PLACEHOLDER_TOKEN_PATTERN + r")+"
)
# 多層括號的佔位符（「（（待確認））」／「((待確認))」）：收斂成一層，保留最外層樣式。
_NESTED_PLACEHOLDER_PATTERN = re.compile(
    r"([（(])[（(]+" + re.escape(_PLACEHOLDER_INNER_TEXT) + r"[）)]+"
)

# 標題行：Markdown 標題（#～######），或以「紀錄／彙整表」收尾的全文標題行
# （後者沿用 _UNFILLED_PLACEHOLDER_TITLE_LINE_PATTERN 的判定，不另立標準）。
_PLACEHOLDER_HEAD_TITLE_PATTERN = re.compile(
    r"^\s*#{1,6}\s|" + _UNFILLED_PLACEHOLDER_TITLE_LINE_PATTERN.pattern
)
# 欄位行：可選項目符號＋可選粗體，短標籤（≤20 字、不含冒號與表格直線）後接全／半形
# 冒號。20 字＝本專案最長欄位標籤（「歷次科務會議決議事項繼續列管案件」16 字）的
# 安全上界；這是「欄位行」與「清單條目正文」的分界，沒有此形狀的條目正文一律不動。
_PLACEHOLDER_HEAD_FIELD_PATTERN = re.compile(
    r"^\s*(?:[-*+]\s+)?(?:\*\*|__)?[^：:\n|]{1,20}(?:\*\*|__)?\s*[:：]"
)

# 表格列切分：group(1)＝「| 第 1 欄 |」、group(2)＝第 2 欄內容、group(3)＝其餘欄位與
# 收尾直線（皆原樣保留）；跳脫直線（\|）不支援，與本檔既有表格處理一致。
_PLACEHOLDER_TABLE_ROW_PATTERN = re.compile(
    r"^([ \t]*\|[^|\n]*\|)([^|\n]*)((?:\|[^|\n]*)*)$"
)
# 分隔列單一儲存格樣式（---／:---:）；用於排除表頭下的分隔列（不是資料列）。
_TABLE_SEPARATOR_CELL_PATTERN = re.compile(r":?-+:?")


def _collapse_nested_placeholder(match: re.Match) -> str:
    """多層括號佔位符收斂成一層（沿用最外層括號的全／半形樣式）。"""
    opener = match.group(1)
    closer = "）" if opener == "（" else ")"
    return f"{opener}{_PLACEHOLDER_INNER_TEXT}{closer}"


def _is_placeholder_head_line(stripped: str) -> bool:
    """是否屬「開頭欄位／標題行」（表格列與清單條目正文一律排除）。"""
    if not stripped or TABLE_ROW_PATTERN.match(stripped):
        return False
    if _PLACEHOLDER_HEAD_TITLE_PATTERN.search(stripped):
        return True
    return bool(_PLACEHOLDER_HEAD_FIELD_PATTERN.match(stripped))


def _is_table_separator_row(row: str) -> bool:
    """Markdown 表格分隔列（全儲存格皆為 ---／:---: 樣式）。"""
    stripped = row.strip()
    inner = stripped[1:] if stripped.startswith("|") else stripped
    inner = inner[:-1] if inner.endswith("|") else inner
    cells = [cell.strip() for cell in inner.split("|")]
    return bool(cells) and all(
        _TABLE_SEPARATOR_CELL_PATTERN.fullmatch(cell) for cell in cells
    )


def _placeholder_summary_table_rows(lines: list[str]) -> list[int]:
    """回傳「決議事項辦理情形彙整表」資料列的行號（不含表頭與分隔列）。

    標題後僅允許空行與「決議事項：」標籤行，首個內容行必須是表格列，否則換下
    一個標題候選；完全找不到時回傳空清單（呼叫端原樣回傳、不報錯）。只處理
    第一個可解析的該表。
    """
    for title_index, line in enumerate(lines):
        if _PLACEHOLDER_TARGET_TABLE_TITLE not in line or TABLE_ROW_PATTERN.match(line):
            continue
        index = title_index + 1
        while index < len(lines) and (
            not lines[index].strip()
            or _PLACEHOLDER_TABLE_LABEL_PATTERN.match(lines[index].strip())
        ):
            index += 1
        if index >= len(lines) or not TABLE_ROW_PATTERN.match(lines[index]):
            continue
        rows: list[int] = []
        is_header = True
        while index < len(lines) and TABLE_ROW_PATTERN.match(lines[index]):
            if is_header:
                is_header = False  # 首列＝表頭（非資料列）
            elif not _is_table_separator_row(lines[index]):
                rows.append(index)
            index += 1
        return rows
    return []


def _normalize_placeholder_table_row(row: str) -> str:
    """只改表格列第 2 欄儲存格：多層括號收斂、半形冒號改全形；其餘 byte 不動。"""
    match = _PLACEHOLDER_TABLE_ROW_PATTERN.match(row)
    if not match:
        return row
    cell = match.group(2)
    fixed = _NESTED_PLACEHOLDER_PATTERN.sub(_collapse_nested_placeholder, cell)
    fixed = fixed.replace(":", "：")
    if fixed == cell:
        return row
    return f"{match.group(1)}{fixed}{match.group(3)}"


def normalize_unfilled_placeholders_ext(text: str) -> str:
    """P7-B SUPPORTING-1：地端佔位符正規化（作用域釘死；純函式）。

    確定性規則（不用模型、不新增事實、不改語意；作用域不得擴大）：

    ① 文件開頭的欄位／標題行：只掃描前 `_PLACEHOLDER_HEAD_LINE_LIMIT`（15）行，
       把同一行內**相鄰重複**的「（待確認）」收斂成一個；半形 `(待確認)` 與全形
       「（待確認）」視為同一符號（保留第一個出現的樣式）。表格列與清單條目
       正文一律排除；單一個不動、不相鄰的重複不動。
    ② 僅「決議事項辦理情形彙整表」**資料列的第 2 欄**儲存格：
       a) 「（（待確認））」／「((待確認))」等多層括號收斂成一層（保留最外層樣式）；
       b) 半形冒號 `:` 改全形 `：`。
       其他欄位、其他表格與正文一律不動；找不到該表時原樣回傳（不報錯）。

    呼叫端契約（本函式不讀設定、不自行判斷路徑）：僅在地端收尾（`mode="local"`）
    且 `settings.LOCAL_LLM_PLACEHOLDER_NORMALIZE_EXT` 為 True 時由呼叫端呼叫；
    雲端路徑不呼叫（輸出 byte 不變）。

    純字串函式：無 I/O、無網路、無模型、無時間依賴；輸入 `""` 回 `""`；非字串
    輸入原樣回傳（不丟例外）；冪等：`f(f(x)) == f(x)`。
    """
    if not isinstance(text, str) or not text:
        return text

    lines = text.split("\n")

    # ① 文件開頭欄位／標題行（僅前 _PLACEHOLDER_HEAD_LINE_LIMIT 行）：相鄰重複的
    # 佔位符收斂成一個（regex 只匹配緊鄰者，不相鄰的重複不動）。
    for index in range(min(len(lines), _PLACEHOLDER_HEAD_LINE_LIMIT)):
        line = lines[index]
        if not _is_placeholder_head_line(line.strip()):
            continue
        fixed = _ADJACENT_PLACEHOLDERS_PATTERN.sub(r"\1", line)
        if fixed != line:
            lines[index] = fixed

    # ② 該表資料列第 2 欄（只作用於「決議事項辦理情形彙整表」；其他表格不受影響）。
    for row_index in _placeholder_summary_table_rows(lines):
        fixed = _normalize_placeholder_table_row(lines[row_index])
        if fixed != lines[row_index]:
            lines[row_index] = fixed

    return "\n".join(lines)
