"""
機關詞彙表（glossary / hotwords）管理。

語意校正機制第一層：把機關專有名詞注入 ASR 解碼（faster-whisper 的
hotwords 每個視窗都生效；transformers 路徑併入 initial prompt），
並提供 LLM 校正層與英文白名單保護使用。

詞庫檔案：data/glossary/*.txt，一行一詞，# 開頭為註解。
支援「錯誤寫法=>正確寫法」格式登錄已知固定誤辨（供校正層 few-shot 與白名單）。
"""

from __future__ import annotations

import os
import re
from typing import Optional

from backend.core.logger import log

_GLOSSARY_CACHE: dict = {"mtime": None, "terms": [], "corrections": [], "exclusions": []}


def _glossary_dir() -> str:
    from backend.core.config import settings

    configured = getattr(settings, "GLOSSARY_DIR", "") or ""
    if configured:
        return configured
    return os.path.join(os.path.dirname(__file__), "..", "..", "data", "glossary")


def _scan_mtime(directory: str) -> Optional[float]:
    try:
        files = [
            os.path.join(directory, name)
            for name in os.listdir(directory)
            if name.endswith(".txt")
        ]
        if not files:
            return None
        return max(os.path.getmtime(path) for path in files)
    except OSError:
        return None


def load_glossary(force: bool = False) -> tuple[list[str], list[tuple[str, str]]]:
    """載入詞彙表，回傳（詞彙清單, 已知誤辨修正清單）。附 mtime 快取。"""
    directory = os.path.abspath(_glossary_dir())
    mtime = _scan_mtime(directory)

    if not force and mtime is not None and _GLOSSARY_CACHE["mtime"] == mtime:
        return _GLOSSARY_CACHE["terms"], _GLOSSARY_CACHE["corrections"]

    terms: list[str] = []
    corrections: list[tuple[str, str]] = []
    exclusions: list[str] = []
    seen: set[str] = set()

    if os.path.isdir(directory):
        for name in sorted(os.listdir(directory)):
            if not name.endswith(".txt"):
                continue
            try:
                # `utf-8-sig`：對「無 BOM 的 UTF-8」byte 級等價，但能正確吃掉 Windows
                # 記事本等編輯器存檔時加上的 BOM；用 `utf-8` 讀會讓**第一行配對靜默失效**
                # （`\ufeff內機=>內稽` 的錯誤形永遠比對不到），是 Windows 端最難察覺的品質破口。
                with open(os.path.join(directory, name), "r", encoding="utf-8-sig") as handle:
                    for raw_line in handle:
                        line = raw_line.strip()
                        # 行尾註解（` # …`）不算內容：避免 `錯誤形=>正確形  # 說明`
                        # 把說明文字一起寫進正確形（會污染逐字稿）。
                        line = re.sub(r"\s+#.*$", "", line).strip()
                        if not line or line.startswith("#"):
                            continue
                        # `!複合詞`：排除複合詞——含登錄錯形但屬正常用語的詞，
                        # 確定性替換不得在它內部套用（例：!評審員 之於 審員=>審計員）
                        if line.startswith("!"):
                            compound = line[1:].strip()
                            if len(compound) >= 2 and compound not in exclusions:
                                exclusions.append(compound)
                            continue
                        if "=>" in line:
                            wrong, _, right = line.partition("=>")
                            wrong, right = wrong.strip(), right.strip()
                            if wrong and right:
                                corrections.append((wrong, right))
                                if right not in seen:
                                    seen.add(right)
                                    terms.append(right)
                            continue
                        if line not in seen:
                            seen.add(line)
                            terms.append(line)
            except (OSError, UnicodeDecodeError) as exc:
                # 詞表壞檔不得讓整條管線失敗（fail-soft）：Windows 使用者若用 ANSI／Big5
                # 誤存詞表，`UnicodeDecodeError` 原本會直接往上拋；這裡改成跳過該檔並告警。
                log.warning("讀取詞彙表 {} 失敗: {}", name, exc)

    _GLOSSARY_CACHE.update(
        {"mtime": mtime, "terms": terms, "corrections": corrections, "exclusions": exclusions}
    )
    if terms:
        log.info("詞彙表載入完成：{} 詞、{} 條已知誤辨修正", len(terms), len(corrections))
    return terms, corrections


def build_hotwords_string(max_chars: int = 300) -> str:
    """組出給 faster-whisper `hotwords` 的字串（≲223 tokens，保守以字元數控管）。"""
    terms, _ = load_glossary()
    if not terms:
        return ""
    selected: list[str] = []
    total = 0
    for term in terms:
        cost = len(term) + 1
        if total + cost > max_chars:
            break
        selected.append(term)
        total += cost
    return "、".join(selected)


def english_protected_terms() -> set[str]:
    """回傳詞彙表中的英文/含英文專名，供英文行清理白名單保護。"""
    terms, _ = load_glossary()
    return {term for term in terms if re.search(r"[A-Za-z]", term)}


_CJK_ONLY_RE = re.compile(r"^[㐀-鿿]+$")
_MIN_MISRECOGNITION_LEN = 2


def protected_terms(min_len: int = 2) -> tuple[str, ...]:
    """回傳「不得被模型改動」的保護詞（純中日韓、長度 ≥ min_len）。

    語意：保護詞表是確定性護欄——LLM 校正層若提出會消滅保護詞的替換，一律退回
    （除非該替換本身登錄在已知誤辨白名單）。資料來源同詞彙表，因此換模型、
    換作業系統都吃同一份詞表。
    """
    terms, _ = load_glossary()
    return tuple(
        term
        for term in terms
        if len(term) >= min_len and _CJK_ONLY_RE.match(term)
    )


def _pair_is_admissible(wrong: str, exclusions: tuple[str, ...]) -> bool:
    """配對是否可套用：錯誤形 ≥2 字；單字配對須已登錄排除複合詞才放行。"""
    if len(wrong) >= _MIN_MISRECOGNITION_LEN:
        return True
    return any(wrong in compound for compound in exclusions)


def apply_known_corrections(text: str) -> tuple[str, list[tuple[str, str, int]]]:
    """確定性套用詞彙表「錯誤寫法=>正確寫法」清單（模型無關、零 LLM 成本）。

    這一層刻意不吃 LLM 的自由生成：資料檔登錄的固定誤辨一定被修好，不受被測
    模型能力影響（實測 27B 校正層漏修 `內機→內稽`，直接吃掉一條 core 事實）。
    錯誤形長度 ≥2 才收；單字配對（如 `麵→面`）另須在資料檔登錄至少一個
    `!排除複合詞` 才放行——沒登錄排除詞就代表還沒想清楚誤傷面，一律不套用。
    `!複合詞` 排除清單內的錯形不替換（例：`保護數…` 不是 `戶數` 的誤辨）。
    """
    if not text:
        return text, []
    _, corrections = load_glossary()
    if not corrections:
        return text, []

    exclusions: tuple[str, ...] = tuple(_GLOSSARY_CACHE.get("exclusions") or ())
    applied: list[tuple[str, str, int]] = []
    fixed = text
    # 長形優先：避免短形先命中而讓長形配對失效（例如「內機房」與「內機」）
    for wrong, right in sorted(corrections, key=lambda pair: -len(pair[0])):
        if not _pair_is_admissible(wrong, exclusions):
            continue
        fixed, count = _replace_pair(fixed, wrong, right, exclusions)
        if not count:
            continue
        applied.append((wrong, right, count))
    return fixed, applied


def _replace_pair(
    text: str, wrong: str, right: str, exclusions: tuple[str, ...]
) -> tuple[str, int]:
    """替換 `wrong` → `right`，但落在排除複合詞內部的 occurrence 不動。"""
    blockers = [word for word in exclusions if wrong in word]
    if not blockers:
        return text.replace(wrong, right), text.count(wrong)

    blocked_spans: list[tuple[int, int]] = []
    for word in blockers:
        start = text.find(word)
        while start != -1:
            blocked_spans.append((start, start + len(word)))
            start = text.find(word, start + 1)

    parts: list[str] = []
    hits = 0
    cursor = 0
    position = text.find(wrong)
    while position != -1:
        end = position + len(wrong)
        if any(start <= position and end <= stop for start, stop in blocked_spans):
            parts.append(text[cursor:end])
        else:
            parts.append(text[cursor:position])
            parts.append(right)
            hits += 1
        cursor = end
        position = text.find(wrong, end)
    parts.append(text[cursor:])
    return "".join(parts), hits


def glossary_prompt_block(max_terms: int = 200) -> str:
    """組出給 LLM 校正層的詞彙表區塊。"""
    terms, corrections = load_glossary()
    lines: list[str] = []
    if terms:
        lines.append("、".join(terms[:max_terms]))
    if corrections:
        lines.append("已知固定誤辨（一律照此修正）：")
        lines.extend(f"- {wrong} → {right}" for wrong, right in corrections[:50])
    return "\n".join(lines)
