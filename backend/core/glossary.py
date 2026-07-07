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

_GLOSSARY_CACHE: dict = {"mtime": None, "terms": [], "corrections": []}


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
    seen: set[str] = set()

    if os.path.isdir(directory):
        for name in sorted(os.listdir(directory)):
            if not name.endswith(".txt"):
                continue
            try:
                with open(os.path.join(directory, name), "r", encoding="utf-8") as handle:
                    for raw_line in handle:
                        line = raw_line.strip()
                        if not line or line.startswith("#"):
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
            except OSError as exc:
                log.warning("讀取詞彙表 {} 失敗: {}", name, exc)

    _GLOSSARY_CACHE.update({"mtime": mtime, "terms": terms, "corrections": corrections})
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
