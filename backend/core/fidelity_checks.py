"""P4-B 忠實度絆索：A 自創專名／B 無依據歸屬／C 數字單位（確定性、模型無關、fail-soft）。

設計權威＝plan §9.4（T20260922-2037-02，P4-B）＋handoff §4.1 凍結介面：

    FIDELITY_METRIC_VERSION
    analyze_fidelity(record_text, transcript_text, template_id=None) -> dict
    load_entity_registry() -> set[str]

硬性契約（handoff §4.1／§5；設計 §2.1／§6）：
* 純函式、fail-soft：任何內部錯誤回傳空結果、**絕不拋出**（呼叫端另有
  一層 try/except 為第二保險）。只產生可直接併入既有補強問題清單的
  ``problems`` 字串（繁體中文、指名具體字串）；不改寫、不刪句、不生成替代名稱。
* 確定性：同輸入 → byte 級相同輸出（無時間戳、無隨機、無集合序外洩）。
* import 期零副作用：實體白名單與詞彙表皆在函式內 lazy 讀取。
* 逐字稿缺席（None／空）＝不作用（與 ``_validate_cloud_date_grounding`` 同模式）。
* 量尺（``scripts/e2e/measure_record_quality.py``）與產品
  （``summarization._validate_record_fidelity``）共用本模組，不得另立第二套規則。

唯一 I/O：``data/entities/entity_registry.json``（本包資料檔）與
``backend.core.glossary.load_glossary()``（既有 mtime 快取）。不 import
``backend.services``（維持 core 純度、避免反向依賴）。
"""

from __future__ import annotations

import json
import os
import re
import unicodedata
from statistics import median
from typing import Any, Iterable, Optional

from backend.core.logger import log

FIDELITY_METRIC_VERSION = "fidelity-1.0.0"

# 問題清單上限（設計 §2.5／§4.3）：避免問題清單爆量、淹沒補強提示詞。
ENTITY_MAX = 3
ATTRIBUTION_MAX = 3
NUMBER_MAX = 6
NUMBER_MIN_COUNT = 10
NEAR_MISS_RATIO = 0.5
VARIANT_DICE_MIN = 0.75

# 變體折疊（只用於比對、不改文字；設計 §2.3）。理→里：逐字稿「瑞裏／瑞理」並存。
FOLD_VARIANTS = {
    "裏": "里",
    "裡": "里",
    "理": "里",
    "徵": "征",
    "菸": "煙",
    "臺": "台",
    "檯": "台",
}

# 組織後綴（長者優先；`endswith` 判定與 regex 交替皆用同一份）。
ORG_SUFFIXES = (
    "及稅務管理科",
    "稅務管理科",
    "稅科",
    "稅股",
    "管理科",
    "稽徵股",
    "分局",
    "分署",
    "中心",
    "科",
    "股",
    "室",
    "處",
    "局",
    "村",
    "里",
)
# 「後綴＋下一個字」構成一般複合詞者直接跳過（科務／科長／局長／處長／村里…）。
SUFFIX_NEXT_CHAR_SKIP = frozenset(
    "內長員別務室裡系學名制度規標表卡間面方法式樣區"
)
# 核心（＝候選去後綴）內不得再出現這些字（殺「煙酒及稅管科一股」「財管科搬入處」）。
SUFFIX_CHARS = frozenset("科股室處局村里中心")
# 左側限定詞剝除（「原房稅科」「該稽查股」→ 核心）。
DETERMINER_PREFIXES = (
    "原", "本", "該", "新", "舊", "前", "後", "全", "各", "同", "含", "涵", "蓋",
    "待", "求", "配", "合", "評", "估", "關", "注", "詢", "問", "搬", "入", "併",
    "移", "更", "設", "等", "共", "計", "約", "逾", "超", "額", "另", "再", "以",
    "由", "至", "對", "就", "並", "與", "及", "或", "之", "其",
)
# 命名動詞（A 的 P2 高訊號位置）。
NAME_VERB_PATTERN = r"(?:改名為|更名為|併入|下設|分設|改為|改稱|統稱|稱作)"
# 角色詞（B3；封閉集合）。科長／主席刻意排除＝section_meeting／general 的章節
# 固定用語，非「歸屬斷言」（見 _role_word_issues 的標題行排除）。
ROLE_WORDS = (
    "局長",
    "副局長",
    "主任",
    "會計師",
    "股長",
    "秘書長",
    "人事主任",
    "專員",
)

# 與量尺 `find_unsupported_entities` 同一份 raw 抽取（歷史欄位語意凍結）。
QUOTED_NAME_PATTERN = re.compile(r"「([^」]{2,20})」")
ENTITY_SUFFIX_PATTERN = re.compile(r"(?:股|科|室|處|局|中心|公司)$")

# A 的高訊號位置（設計 §2.2；P3 辦理情形欄由 B4 承辦單位檢查覆蓋，避免重複回報）。
_QUOTED_CANDIDATE_PATTERN = re.compile(r"「([^」]{2,14})」")
_NAME_VERB_CANDIDATE_PATTERN = re.compile(
    r"([\u4e00-\u9fff]{2,8}(?:%s))(?=%s)" % ("|".join(ORG_SUFFIXES), NAME_VERB_PATTERN)
)
_DETERMINER_PATTERN = re.compile(r"^(?:%s)+" % "|".join(DETERMINER_PREFIXES))
_SUFFIX_RUN_PATTERN = re.compile(r"[\u4e00-\u9fff]{1,8}(?:%s)" % "|".join(ORG_SUFFIXES))

# B：紀錄固定欄位與表格列（與 text_postprocess.TABLE_ROW_PATTERN 同定義）。
_HEADER_FIELD_PATTERN = re.compile(r"^([^\n:：]{1,20})\s*[:：](.*)$", re.M)
_HEADER_FIELD_NAMES = ("時間", "地點", "主持人", "出席人員", "紀錄")

# 比對用寬鬆化：引號內清單可能有分隔符差異（紀錄「一股、二股」vs 逐字稿「一股二股」）。
# 逐字稿段落列（含段落文字；B5 觀察值用；與 text_postprocess 的解析同格式）。
_TRANSCRIPT_TEXT_LINE_PATTERN = re.compile(
    r"^\[(\d{1,3}):(\d{2}):(\d{2})\s*-\s*(\d{1,3}):(\d{2}):(\d{2})\]\s*[^：:]{1,24}[：:](.*)$"
)

_SEPARATOR_PATTERN = re.compile(
    r"[\s、，,。．.；;：:·・～~！!？?（）()［］\[\]【】「」『』《》〈〉／/\\\-—‐…﹑‧]"
)

# C：單位類別表（等價群組；DATE 兩方向皆排除——沿用既有年份絆索的決策）。
UNIT_CLASS = {
    "元": "MONEY",
    "塊": "MONEY",
    "圓": "MONEY",
    "萬元": "MONEY",
    "人": "PERSON",
    "名": "PERSON",
    "位": "PERSON",
    "個": "PERSON",
    "員": "PERSON",
    "戶": "HOUSEHOLD",
    "份": "COUNT",
    "張": "COUNT",
    "台": "COUNT",
    "臺": "COUNT",
    "部": "COUNT",
    "件": "COUNT",
    "％": "RATIO",
    "%": "RATIO",
    "成": "RATIO",
    "倍": "MULT",
    "月": "DATE",
    "日": "DATE",
    "年": "DATE",
}
_UNIT_ALTERNATION = "|".join(
    sorted((re.escape(unit) for unit in UNIT_CLASS), key=len, reverse=True)
)
_NUM_PATTERN = re.compile(
    r"(\d{1,2}(?:,\d{3})+|\d+)\s*(?:多|餘|幾)?\s*(%s)" % _UNIT_ALTERNATION
)
_CN_PATTERN = re.compile(
    r"([零〇一二三四五六七八九十百千兩萬万]{1,6})\s*(?:多|餘|幾)?\s*(%s)" % _UNIT_ALTERNATION
)
_CN_DIGITS = {
    "零": 0, "〇": 0, "一": 1, "二": 2, "兩": 2, "三": 3, "四": 4, "五": 5,
    "六": 6, "七": 7, "八": 8, "九": 9, "十": 10, "百": 100, "千": 1000,
    "萬": 10000, "万": 10000,
}
_CN_STUTTER_PATTERN = re.compile(r"([零〇一二三四五六七八九十百千兩萬万])\1")
_BARE_PATTERN = re.compile(r"(?<![\d.])(\d{4,6})(?![\d.])")
# 類別優先序（設計 §4.3：MONEY → BARE → RATIO → PERSON → COUNT）。
_NUMBER_PRIORITY = {"MONEY": 0, "BARE": 1, "RATIO": 2, "PERSON": 3, "HOUSEHOLD": 4, "COUNT": 5}

_ATTRIBUTION_KIND_ORDER = (
    "header_speaker_id",
    "table_speaker_id",
    "tag_owner",
    "header_selfinvent",
    "role_word",
    "cell_unit",
)

_REGISTRY_CACHE: dict = {"key": None, "names": frozenset()}
_GLOSSARY_FALLBACK = frozenset()


# ---------------------------------------------------------------------------
# 正規化（僅比對用；永不改寫輸入文字）
# ---------------------------------------------------------------------------


def _fold(text: str) -> str:
    """NFKC＋變體折疊（比對用）。"""
    normalized = unicodedata.normalize("NFKC", text or "")
    return "".join(FOLD_VARIANTS.get(char, char) for char in normalized)


def _loose(text: str) -> str:
    """再去除標點與分隔符（比對用；處理引號清單「一股、二股」vs「一股二股」）。"""
    return _SEPARATOR_PATTERN.sub("", _fold(text))


def _contains(haystack: str, needle: str) -> bool:
    """needle 是否在 haystack（已 fold）中；允許分隔符差異。"""
    if not needle:
        return True
    if needle in haystack:
        return True
    return _loose(needle) in _loose(haystack)


def _lcs_length(a: str, b: str) -> int:
    """最長共同子序列長度（短字串限定使用；確定性）。"""
    if not a or not b:
        return 0
    if len(a) > len(b):
        a, b = b, a
    previous = [0] * (len(a) + 1)
    for char_b in b:
        current = [0]
        for index, char_a in enumerate(a, start=1):
            if char_a == char_b:
                current.append(previous[index - 1] + 1)
            else:
                current.append(max(previous[index], current[index - 1]))
        previous = current
    return previous[-1]


def _dice(a: str, b: str) -> float:
    """Dice 係數＝2×LCS 長度 /(len(a)+len(b))（設計 §2.3 規則 4）。"""
    if not a or not b:
        return 0.0
    return 2.0 * _lcs_length(a, b) / (len(a) + len(b))


def _template_terms(template: Any) -> set:
    """模板內建詞彙（duck-typing；缺欄位＝空集合，不拋錯）。"""
    terms: set = set()
    for name in getattr(template, "glossary_terms", ()) or ():
        if isinstance(name, str) and name.strip():
            terms.add(_fold(name.strip()))
    for pair in getattr(template, "glossary_corrections", ()) or ():
        right = pair[1] if isinstance(pair, (tuple, list)) and len(pair) >= 2 else None
        if isinstance(right, str) and right.strip():
            terms.add(_fold(right.strip()))
    for pair in getattr(template, "record_term_fixes", ()) or ():
        right = pair[1] if isinstance(pair, (tuple, list)) and len(pair) >= 2 else None
        if isinstance(right, str) and right.strip():
            terms.add(_fold(right.strip()))
    for name in getattr(template, "entity_whitelist", ()) or ():
        if isinstance(name, str) and name.strip():
            terms.add(_fold(name.strip()))
    return terms


def _glossary_terms() -> set:
    """既有 glossary（``data/glossary/*.txt``；mtime 快取）→ fold 後集合（fail-soft）。"""
    try:
        from backend.core.glossary import load_glossary

        terms, corrections = load_glossary()
    except Exception:
        log.warning("忠實度絆索：詞彙表不可用（fail-soft，僅縮小白名單）")
        return set()
    names: set = set()
    for term in terms or ():
        if isinstance(term, str) and term.strip():
            names.add(_fold(term.strip()))
    for wrong, right in corrections or ():
        for side in (wrong, right):
            if isinstance(side, str) and side.strip():
                names.add(_fold(side.strip()))
    return names


def _registry_path() -> str:
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..",
        "..",
        "data",
        "entities",
        "entity_registry.json",
    )


def _registry_file_terms() -> frozenset:
    """讀 ``data/entities/entity_registry.json`` 白名單（mtime 快取；fail-soft）。"""
    path = os.path.abspath(_registry_path())
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        mtime = None
    if mtime is not None and _REGISTRY_CACHE["key"] == (path, mtime):
        return _REGISTRY_CACHE["names"]
    names: set = set()
    if mtime is not None:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
            for entry in payload.get("entity_whitelist", []) or []:
                name = entry.get("name") if isinstance(entry, dict) else entry
                if isinstance(name, str) and name.strip():
                    names.add(_fold(name.strip()))
        except Exception:
            log.warning("忠實度絆索：讀取 entity_registry.json 失敗（fail-soft）")
    frozen = frozenset(names)
    _REGISTRY_CACHE.update({"key": (path, mtime), "names": frozen})
    return frozen


def load_entity_registry() -> set:
    """已知實體白名單（fold 後）：資料檔 ∪ 既有 glossary（模板無關）。

    fail-soft：任何例外回傳空集合（只用於放行判定 → 空集合＝更多回報，
    但 `analyze_fidelity` 內另有逐檢查的 try/except 保護，不會拋出）。
    """
    try:
        return set(_registry_file_terms()) | _glossary_terms()
    except Exception:
        log.warning("忠實度絆索：白名單載入異常（fail-soft，回空集合）")
        return set()


def _resolve_template(template_id: Optional[str]) -> Any:
    """``template_id`` → MeetingTemplate（lazy import；未知 id／失敗＝None）。"""
    try:
        from backend.core.templates import get_template

        return get_template(template_id)
    except Exception:
        return None


def _registry_for(template_id: Optional[str]) -> set:
    """本次檢查用的白名單＝load_entity_registry() ∪ 該模板詞彙。"""
    registry = load_entity_registry()
    if isinstance(template_id, str) and template_id.strip():
        registry |= _template_terms(_resolve_template(template_id.strip()))
    return registry


# ---------------------------------------------------------------------------
# A：自創專名（entity tripwire）
# ---------------------------------------------------------------------------


def _strip_determiners(token: str) -> str:
    return _DETERMINER_PATTERN.sub("", token)


def _suffix_of(token: str) -> str:
    return next((suffix for suffix in ORG_SUFFIXES if token.endswith(suffix)), "")


def _candidate_names(record_text: str) -> dict:
    """高訊號位置的專名候選（P1 引號／P2 命名動詞前）→ {token: 首次出現序}。"""
    candidates: dict = {}

    def add(raw_token: str) -> None:
        token = _strip_determiners((raw_token or "").strip())
        if len(token) < 3 or token in candidates:
            return
        suffix = _suffix_of(token)
        if not suffix:
            return
        stem = token[: len(token) - len(suffix)]
        if len(stem) < 2 or any(char in SUFFIX_CHARS for char in stem):
            return
        candidates[token] = len(candidates)

    for match in _QUOTED_CANDIDATE_PATTERN.finditer(record_text):
        add(match.group(1))
    for match in _NAME_VERB_CANDIDATE_PATTERN.finditer(record_text):
        add(match.group(1))
    return candidates


def _transcript_suffix_candidates(folded_transcript: str) -> dict:
    """逐字稿側的同後綴候選（stem）→ {suffix: (stem, ...)}（規則 4 用）。"""
    grouped: dict = {}
    for match in _SUFFIX_RUN_PATTERN.finditer(folded_transcript):
        run = match.group(0)
        suffix = _suffix_of(run)
        if not suffix:
            continue
        stem = run[: len(run) - len(suffix)]
        if len(stem) < 2:
            continue
        grouped.setdefault(suffix, set()).add(stem)
    return {suffix: tuple(sorted(stems)) for suffix, stems in grouped.items()}


def is_supported_entity(
    token: str,
    folded_transcript: str,
    registry: Iterable[str],
    *,
    transcript_candidates: Optional[dict] = None,
) -> tuple:
    """候選專名是否有依據 → ``(是否支持, 最佳 Dice)``（產品與量尺共用）。

    支持規則（設計 §2.3）：
    ① ``fold(token) ∈ 逐字稿``；② ``fold(stem) ∈ 逐字稿``（正確改寫／變體）；
    ③ ``fold(token)`` 或 ``fold(stem) ∈ registry``；
    ④ 逐字稿同後綴候選 Dice ≥ ``VARIANT_DICE_MIN``（僅在提供
    ``transcript_candidates`` 時套用；量尺 registry-aware 判定不使用此備援規則）。
    """
    token = (token or "").strip()
    if not token:
        return True, 1.0
    registry = registry or ()
    suffix = _suffix_of(token)
    stem = token[: len(token) - len(suffix)] if suffix else ""
    folded_token = _fold(token)
    folded_stem = _fold(stem) if stem else ""

    if _contains(folded_transcript, folded_token) or folded_token in registry:
        return True, 1.0
    if len(stem) >= 2 and (_contains(folded_transcript, folded_stem) or folded_stem in registry):
        return True, 1.0

    best = 0.0
    if transcript_candidates and suffix:
        probe = folded_stem or folded_token
        for candidate in transcript_candidates.get(suffix, ()):
            score = _dice(probe, candidate)
            if score > best:
                best = score
    if best >= VARIANT_DICE_MIN:
        return True, best
    return False, best


def _entity_flags(
    record_text: str,
    folded_transcript: str,
    registry: set,
    transcript_candidates: dict,
    max_flags: int = ENTITY_MAX,
) -> list:
    """A 的旗標 → ``[(token, similarity), ...]``（「最不像」優先；同 token 去重）。"""
    flags = []
    for token in _candidate_names(record_text):
        supported, similarity = is_supported_entity(
            token, folded_transcript, registry, transcript_candidates=transcript_candidates
        )
        if not supported:
            flags.append((token, similarity))
    flags.sort(key=lambda item: (item[1], item[0]))
    return flags[:max_flags]


def _entity_flag_messages(flags: list) -> list:
    """設計 §2.5 的兩段式訊息（不提議替代名稱）。"""
    messages = []
    for token, similarity in flags:
        if similarity >= NEAR_MISS_RATIO:
            messages.append(
                "專名依據待確認（疑似逐字稿變體／同音重寫）：%s。請以逐字稿實際出現的寫法為準；"
                "逐字稿若本身是聽錯的變體而無法確認正確名稱，保留逐字稿寫法或標「（待確認）」，"
                "不得自行重組或發明名稱。" % token
            )
        else:
            messages.append(
                "具名單位無逐字稿依據（疑似自創）：%s。逐字稿未出現此名稱時，"
                "一律標「（待確認）」或改用逐字稿出現的名稱。" % token
            )
    return messages


# ---------------------------------------------------------------------------
# B：無依據歸屬（attribution tripwire）
# ---------------------------------------------------------------------------


def _header_field_values(record_text: str) -> list:
    """紀錄開頭固定欄位 ``[(欄位, 值), ...]``（只認開頭連續區塊）。"""
    values = []
    for line in record_text.splitlines():
        stripped = line.strip()
        if not stripped:
            if values:
                break
            continue
        match = _HEADER_FIELD_PATTERN.match(stripped)
        if not match:
            if values:
                break
            continue
        name = match.group(1).strip()
        if name in _HEADER_FIELD_NAMES:
            values.append((name, match.group(2).strip()))
    return values


def _table_rows(record_text: str) -> list:
    return [line for line in record_text.splitlines() if line.strip().startswith("|")]


def _tag_owner_issues(record_text: str, transcript_text: str) -> list:
    """B1：``（發言者N，HH:MM:SS）`` 的時間戳落在**他人**段落內 → 回報。"""
    from backend.core.text_postprocess import iter_transcript_segments

    segments = iter_transcript_segments(transcript_text)
    if not segments:
        return []
    issues = []
    for match in re.finditer(r"（[^）]{0,24}?\d{1,3}:\d{2}(?::\d{2})?[^）]{0,12}?）", record_text):
        body = match.group(0)[1:-1]
        time_match = re.search(r"(\d{1,3}):(\d{2})(?::(\d{2}))?", body)
        if not time_match:
            continue
        label = body[: time_match.start()].strip(" ，,、;；:：")
        if not re.fullmatch(r"發言者\d+", label):
            continue
        seconds = (
            int(time_match.group(1)) * 3600
            + int(time_match.group(2)) * 60
            + int(time_match.group(3) or 0)
        )
        owner = None
        for start, end, speaker in segments:
            if start == seconds or (start <= seconds <= end):
                owner = speaker
                break
        if owner and re.fullmatch(r"發言者\d+", owner) and owner != label:
            issues.append("tag_owner|（%s）落在 %s 的逐字稿段落內" % (body.strip(), owner))
    return issues


def _header_issues(record_text: str, folded_transcript: str) -> list:
    """B2：固定欄位不得指名「發言者N」／不得出現逐字稿沒有的名稱。"""
    issues = []
    for field, value in _header_field_values(record_text):
        if field in ("時間", "地點") or not value:
            continue
        if "發言者" in value:
            issues.append("header_speaker_id|%s：%s" % (field, value[:40]))
            continue
        if value in ("（待確認）",) or "如後附簽到表" in value or "AI 會議助理" in value:
            continue
        cleaned = re.sub(r"[（(][^）)]*[）)]", "", value)
        invented = [
            run
            for run in re.findall(r"[\u4e00-\u9fff]{2,4}", cleaned)
            if not _contains(folded_transcript, _fold(run))
        ]
        if invented:
            issues.append(
                "header_selfinvent|%s：%s（「%s」逐字稿未見）"
                % (field, value[:40], "」「".join(invented[:3]))
            )
    return issues


def _table_speaker_issues(record_text: str) -> list:
    """B5：表格列出現「發言者N」→ 回報（契約禁止；現行 forbidden_patterns 漏網）。"""
    issues = []
    for row in _table_rows(record_text):
        for match in re.finditer(r"發言者\d+", row):
            cell = row.strip()
            if len(cell) > 60:
                cell = cell[:57] + "…"
            issues.append("table_speaker_id|表格列「%s」出現「%s」" % (cell, match.group(0)))
    return issues


def _role_word_issues(record_text: str, transcript_text: str) -> list:
    """B3：角色詞紀錄有、逐字稿完全沒有 → 回報（章節標題行不計）。"""
    issues = []
    body_lines = [
        line
        for line in record_text.splitlines()
        if not re.match(r"^\s*(?:[一二三四五六七八九十]+、|#|\*|-)", line)
    ]
    body_text = "\n".join(body_lines)
    for role in ROLE_WORDS:
        if role in body_text and role not in transcript_text:
            issues.append("role_word|%s" % role)
    return issues


def _cell_unit_issues(record_text: str, folded_transcript: str, registry: set) -> list:
    """B4：彙整表「辦理情形」欄的組織型 token 套用同一份支持測試。"""
    rows = _table_rows(record_text)
    if not rows:
        return []
    issues = []
    in_summary_table = False
    for index, row in enumerate(rows):
        cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
        if index < 2 and any("辦理情形" in cell for cell in cells):
            in_summary_table = True
        if not in_summary_table or len(cells) < 2:
            continue
        unit_cell = cells[1]
        if not unit_cell or unit_cell == "（待確認）":
            continue
        for match in re.finditer(r"[\u4e00-\u9fff]{2,6}(?:%s)" % "|".join(ORG_SUFFIXES), unit_cell):
            token = _strip_determiners(match.group(0))
            suffix = _suffix_of(token)
            if not suffix:
                continue
            stem = token[: len(token) - len(suffix)]
            if len(stem) < 2 or any(char in SUFFIX_CHARS for char in stem):
                continue
            supported, _similarity = is_supported_entity(token, folded_transcript, registry)
            if not supported:
                issues.append("cell_unit|%s" % token)
    return issues


def _attribution_issues(
    record_text: str, transcript_text: str, folded_transcript: str, registry: set
) -> list:
    issues = []
    issues.extend(_tag_owner_issues(record_text, transcript_text))
    issues.extend(_header_issues(record_text, folded_transcript))
    issues.extend(_table_speaker_issues(record_text))
    issues.extend(_role_word_issues(record_text, transcript_text))
    issues.extend(_cell_unit_issues(record_text, folded_transcript, registry))
    issues.sort(key=lambda issue: (_ATTRIBUTION_KIND_ORDER.index(issue.split("|", 1)[0]), issue))
    return issues


_ATTRIBUTION_MESSAGES = {
    "header_speaker_id": (
        "紀錄固定欄位歸屬待確認：%s；「發言者N」是分群編號、不是姓名，"
        "不得寫入紀錄欄位，請改以逐字稿實際出現的稱謂或標「（待確認）」。"
    ),
    "table_speaker_id": (
        "彙整表欄位歸屬待確認：%s；表格欄位不得出現發言者編號，"
        "請改以逐字稿實際出現的承辦單位或同仁稱謂，查不到者標「（待確認）」。"
    ),
    "tag_owner": "來源標註歸屬待確認：%s；請改標該段落實際的發言者，或標「（待確認）」。",
    "header_selfinvent": (
        "紀錄欄位依據待確認：%s；未提及時一律填「（待確認）」，不得自行填寫。"
    ),
    "role_word": (
        "角色依據待確認：紀錄出現「%s」，但逐字稿未出現此角色；"
        "請以逐字稿實際出現的職稱記載，查不到者標「（待確認）」。"
    ),
    "cell_unit": (
        "承辦單位依據待確認：彙整表「辦理情形」欄出現逐字稿未見的「%s」；"
        "請以逐字稿實際出現的承辦單位記載，查不到者標「（待確認）」。"
    ),
}


def _attribution_messages(issues: list, max_messages: int = ATTRIBUTION_MAX) -> list:
    messages = []
    for issue in issues[:max_messages]:
        kind, _, detail = issue.partition("|")
        template = _ATTRIBUTION_MESSAGES.get(kind)
        if template:
            messages.append(template % detail)
    return messages


def _transcript_segments_with_text(transcript_text: str) -> list:
    """逐字稿段落 ``[(start, end, 段落文字), ...]``（只給觀察值使用；fail-soft）。"""
    segments = []
    for raw_line in (transcript_text or "").splitlines():
        match = _TRANSCRIPT_TEXT_LINE_PATTERN.match(raw_line.strip())
        if not match:
            continue
        start = (
            int(match.group(1)) * 3600 + int(match.group(2)) * 60 + int(match.group(3))
        )
        end = int(match.group(4)) * 3600 + int(match.group(5)) * 60 + int(match.group(6))
        if end < start:
            start, end = end, start
        segments.append((start, end, match.group(7)))
    return segments


def _attribution_overlap_median(record_text: str, transcript_text: str) -> Optional[float]:
    """B5 觀察值：帶標註條目與其段落（含 ±1 段）的 LCS 覆蓋率中位數（未校準，僅觀察）。"""
    segments = _transcript_segments_with_text(transcript_text)
    if not segments:
        return None
    ratios = []
    for line in record_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("|"):
            continue
        time_match = re.search(r"（[^）]{0,24}?(\d{1,3}):(\d{2})(?::(\d{2}))?[^）]{0,12}?）", stripped)
        if not time_match:
            continue
        seconds = (
            int(time_match.group(1)) * 3600
            + int(time_match.group(2)) * 60
            + int(time_match.group(3) or 0)
        )
        index = None
        for position, (start, end, _text) in enumerate(segments):
            if start <= seconds <= end:
                index = position
                break
        if index is None:
            continue
        context = "".join(
            segment[2] for segment in segments[max(0, index - 1) : index + 2]
        )[:400]
        item_text = re.sub(r"（[^）]*）", "", stripped)
        item_text = re.sub(r"^[0-9０-９]+[.、)）]\s*", "", item_text)[:160]
        if not item_text:
            continue
        ratios.append(min(1.0, _lcs_length(item_text, context) / len(item_text)))
    if not ratios:
        return None
    ratios.sort()
    return round(float(median(ratios)), 4)


# ---------------------------------------------------------------------------
# C：數字／單位回查（number tripwire）
# ---------------------------------------------------------------------------


def _strip_transcript_noise(text: str) -> str:
    """剝【發言者標註說明】【發言者統計】前言與 ``[HH:MM:SS-HH:MM:SS]`` 時間戳。"""
    cleaned = re.sub(r"【發言者標註說明】.*?(?=\n\[)", "", text or "", flags=re.S)
    cleaned = re.sub(r"【發言者統計】.*?(?=\n\[)", "", cleaned, flags=re.S)
    return re.sub(
        r"\[\d{1,3}:\d{2}:\d{2}\s*-\s*\d{1,3}:\d{2}:\d{2}\]", "", cleaned
    )


def _cn_to_int(numeral: str) -> Optional[int]:
    if any(char in "十百千萬万" for char in numeral):
        total = 0
        section = 0
        for char in numeral:
            value = _CN_DIGITS[char]
            if value >= 10:
                total += (section or 1) * value
                section = 0
            else:
                section = value
        return total + section
    return int("".join(str(_CN_DIGITS[char]) for char in numeral))


def _collect_numbers(text: str, *, material_view: bool) -> dict:
    """抽取 ``{數字值: (類別, 原文 token, 值)}``。

    ``material_view=True``＝實質視圖（漏寫方向；MONEY／RATIO ≥2、
    PERSON／HOUSEHOLD／COUNT ≥``NUMBER_MIN_COUNT``、BARE ≥4 位且 ±2 字無其他數字）；
    ``False``＝全量視圖（捏造方向；只排除 DATE 與 0 值／前導零／口吃）。
    """
    cleaned = unicodedata.normalize("NFKC", _strip_transcript_noise(text))
    full: dict = {}
    material: dict = {}

    for match in _NUM_PATTERN.finditer(cleaned):
        raw_value = match.group(1).replace(",", "")
        kind = UNIT_CLASS.get(match.group(2), "COUNT")
        if kind == "DATE" or kind not in _NUMBER_PRIORITY:
            continue
        if not raw_value.isdigit():
            continue
        if len(raw_value) > 1 and raw_value.startswith("0"):
            continue
        value = int(raw_value)
        if value == 0:
            continue
        token = match.group(0).replace(" ", "")
        full.setdefault(str(value), (kind, token))
        if material_view and (
            (kind in ("MONEY", "RATIO") and value >= 2)
            or (kind in ("PERSON", "HOUSEHOLD", "COUNT") and value >= NUMBER_MIN_COUNT)
        ):
            material.setdefault(str(value), (kind, token))
    for match in _CN_PATTERN.finditer(cleaned):
        numeral = match.group(1)
        if _CN_STUTTER_PATTERN.search(numeral):
            continue
        if any(char not in _CN_DIGITS for char in numeral):
            continue
        value = _cn_to_int(numeral)
        if value is None or value == 0:
            continue
        kind = UNIT_CLASS.get(match.group(2), "COUNT")
        if kind == "DATE" or kind not in _NUMBER_PRIORITY:
            continue
        token = match.group(0).replace(" ", "")
        full.setdefault(str(value), (kind, token))
        if material_view and (
            (kind in ("MONEY", "RATIO") and value >= 2)
            or (kind in ("PERSON", "HOUSEHOLD", "COUNT") and value >= NUMBER_MIN_COUNT)
        ):
            material.setdefault(str(value), (kind, token))
    for match in _BARE_PATTERN.finditer(cleaned):
        raw_value = match.group(1)
        if raw_value.startswith("0"):
            continue
        left = cleaned[max(0, match.start() - 2) : match.start()]
        right = cleaned[match.end() : match.end() + 2]
        if re.search(r"\d", left + right):
            continue
        full.setdefault(raw_value, ("BARE", raw_value))
        material.setdefault(raw_value, ("BARE", raw_value))

    return material if material_view else full


def _number_issue_tokens(entries: Iterable[tuple]) -> list:
    """排序（類別優先＋值大者先）＋上限（設計 §4.3）。"""
    ordered = sorted(
        entries,
        key=lambda entry: (
            _NUMBER_PRIORITY.get(entry[1][0], 9),
            -int(entry[0]) if str(entry[0]).isdigit() else 0,
            str(entry[0]),
        ),
    )
    tokens = [entry[1][1] for entry in ordered[:NUMBER_MAX]]
    return tokens


def _number_messages(missing_tokens: list, fabricated_tokens: list) -> list:
    messages = []
    if missing_tokens:
        quoted = "".join("「%s」" % token for token in missing_tokens)
        messages.append(
            "金額／數量依據待確認：逐字稿出現但紀錄未見%s。請回逐字稿核對後補進對應段落"
            "（金額與人數須與用途同段）；查不到用途者標「（待確認）」，不得改寫為概括數字。"
            % quoted
        )
    if fabricated_tokens:
        quoted = "".join("「%s」" % token for token in fabricated_tokens)
        messages.append(
            "數字依據待確認（疑似捏造）：紀錄出現逐字稿沒有的%s。"
            "請刪除或改為逐字稿實際數字／標「（待確認）」。" % quoted
        )
    return messages


# ---------------------------------------------------------------------------
# 對外凍結介面
# ---------------------------------------------------------------------------


def _empty_report() -> dict:
    return {
        "metric_version": FIDELITY_METRIC_VERSION,
        "problems": [],
        "fabricated_entities": [],
        "attribution_violations": [],
        "missing_numbers": [],
        "fabricated_numbers": [],
        "registry_aware_unsupported_entities": [],
        "raw_unsupported_entities": [],
        "attribution_overlap_median": None,
        "entity_registry_size": 0,
        "failed_checks": [],
    }


def analyze_fidelity(
    record_text: str,
    transcript_text: Optional[str],
    template_id: Optional[str] = None,
) -> dict:
    """忠實度絆索總入口（凍結介面；純函式、fail-soft）。

    回傳 dict 至少含：``metric_version``／``problems``／``fabricated_entities``／
    ``attribution_violations``／``missing_numbers``／``registry_aware_unsupported_entities``／
    ``raw_unsupported_entities``（另附 kinds／counts 觀察鍵）。
    逐字稿缺席或任何內部錯誤 → 空結果（空清單，不拋出）。
    """
    report = _empty_report()
    try:
        record = record_text if isinstance(record_text, str) else ""
        transcript = transcript_text if isinstance(transcript_text, str) else ""
        if not record.strip() or not transcript.strip():
            return report

        registry = _registry_for(template_id)
        folded_transcript = _fold(transcript)
        report["entity_registry_size"] = len(registry)

        failed: list = []
        entity_flags: list = []
        attribution_issues: list = []
        missing_tokens: list = []
        fabricated_tokens: list = []

        try:
            entity_flags = _entity_flags(
                record,
                folded_transcript,
                registry,
                _transcript_suffix_candidates(folded_transcript),
            )
        except Exception:
            failed.append("entity")
            log.warning("忠實度絆索 A（自創專名）異常（fail-soft）", exc_info=True)
        try:
            attribution_issues = _attribution_issues(
                record, transcript, folded_transcript, registry
            )
        except Exception:
            failed.append("attribution")
            log.warning("忠實度絆索 B（無依據歸屬）異常（fail-soft）", exc_info=True)
        try:
            record_full = _collect_numbers(record, material_view=False)
            transcript_all = _collect_numbers(transcript, material_view=False)
            transcript_material = _collect_numbers(transcript, material_view=True)
            missing_tokens = _number_issue_tokens(
                [(key, value) for key, value in transcript_material.items() if key not in record_full]
            )
            fabricated_tokens = _number_issue_tokens(
                [(key, value) for key, value in record_full.items() if key not in transcript_all]
            )
        except Exception:
            failed.append("numbers")
            log.warning("忠實度絆索 C（數字單位）異常（fail-soft）", exc_info=True)
        try:
            overlap = _attribution_overlap_median(record, transcript)
        except Exception:
            overlap = None
            failed.append("overlap")
        try:
            raw_unsupported = sorted(
                token
                for token in QUOTED_NAME_PATTERN.findall(record)
                if ENTITY_SUFFIX_PATTERN.search(token) and token not in transcript
            )
            registry_aware = [
                token
                for token in raw_unsupported
                if not is_supported_entity(token, folded_transcript, registry)[0]
            ]
        except Exception:
            raw_unsupported = []
            registry_aware = []
            failed.append("unsupported_entities")
            log.warning("忠實度絆索：未落地專名抽取異常（fail-soft）", exc_info=True)

        report["failed_checks"] = failed
        report["fabricated_entities"] = [token for token, _score in entity_flags]
        report["fabricated_entity_similarities"] = [
            round(score, 4) for _token, score in entity_flags
        ]
        report["fabricated_entity_kinds"] = [
            "variant" if score >= NEAR_MISS_RATIO else "unsupported"
            for _token, score in entity_flags
        ]
        report["attribution_violations"] = attribution_issues
        report["attribution_kinds"] = sorted({issue.split("|", 1)[0] for issue in attribution_issues})
        report["missing_numbers"] = missing_tokens
        report["fabricated_numbers"] = fabricated_tokens
        report["attribution_overlap_median"] = overlap
        report["raw_unsupported_entities"] = raw_unsupported
        report["registry_aware_unsupported_entities"] = registry_aware
        report["problems"] = (
            _entity_flag_messages(entity_flags)
            + _attribution_messages(attribution_issues)
            + _number_messages(missing_tokens, fabricated_tokens)
        )
        return report
    except Exception:
        log.warning("忠實度絆索異常（fail-soft，回空結果）", exc_info=True)
        return _empty_report()


__all__ = [
    "FIDELITY_METRIC_VERSION",
    "analyze_fidelity",
    "load_entity_registry",
]
