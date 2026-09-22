#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
事實涵蓋率量尺（deterministic coverage metric；無 LLM、無網路、無 LM Studio）。

用途：
    對「受測會議紀錄 Markdown」＋「事實清單 JSON」輸出**確定性**涵蓋率報告，
    量化「會議真正講過的事實有多少被寫進紀錄」——補上
    ``scripts/e2e/measure_record_quality.py``（只量出處標註可查核性）量不到的
    維度；雲端（Gemini）與地端（Qwen／Gemma）模型使用完全相同的一把尺。

    * ``--record``（必要）：受測會議紀錄 Markdown 為權威來源（不收 DOCX）。
    * ``--checklist``（必要）：事實清單 JSON（schema 與 probes 語意見 README）。
    * ``--label``（選用）：報告顯示名稱；預設取紀錄檔名 stem。
    * ``--transcript``（選用）：逐字稿 txt；提供時多一段**觀察值**
      ``transcript``（同一組 probes 對逐字稿的涵蓋率），用來分辨「模型漏寫」
      與「清單事實根本沒出現在逐字稿（ASR 變體／清單瑕疵）」。永不作為閘門。
    * ``--json-out``／``--md-out``（選用）：另寫 JSON／Markdown 檔；
      stdout 一律輸出同一份 JSON。
    * ``--fuzzy-homophone``（選用，預設關）：字面未命中才改用逐字拼音近音
      （台灣口音聲母/韻母混淆組，同 ``backend.services.correction`` 的判定精神；
      沿用專案既有依賴 pypinyin，不新增任何依賴）。開啟時報告
      ``normalization.fuzzy=true``，關閉時 ``fuzzy=false``。
    * ``--timestamp``／``--no-timestamp``：是否寫入 ``generated_at``；預設**不寫**
      （同一組輸入 → byte 相同輸出）。

probes 語意（與事實清單產生端的共用契約）：
    ``probes`` 是 group 的列表；**任一 group 內全部 token 都出現在受測紀錄
    → 該事實算被涵蓋**（group 內 AND、group 間 OR）；命中第一個 group 即停，
    ``matched_group_index`` 記該 group index。

正規化（雙向對稱；受測紀錄與 checklist token 過同一條管線）：
    NFKC → casefold → OpenCC ``s2twp`` 折到台灣正體（不可用時兩邊套同一
    identity fallback，報告標記 ``opencc_available=false``）→ 去除空白與換行
    （含 Windows CRLF）→ 只保留中日韓漢字與英數字（中英文標點、括號、破折號、
    表格管線、Markdown 符號、全形空白…全部去除）。

誠實邊界：
    * 這是**字面**量尺、不是語意量尺：換句話說但意思有寫到的事實可能被計為
      漏寫（false negative）；關鍵詞堆砌也可能造成 false positive。
    * ``--fuzzy-homophone`` 只處理同音近音錯字，不處理改寫、語序與否定
      （「同意」vs「不同意」在 token 層面同分）。
    * 本儀器不改任何產品行為，也不放寬任何判準；輸出不含當下時間戳（除非
      ``--timestamp``）。

用法：
    uv run python scripts/e2e/measure_coverage.py \
        --record data/cache/e2e/p2-gemma31b-fix-01/backend_data/outputs/0903-科務會議_ac1edcec.md \
        --checklist data/cache/staging/quality/fact_checklist.json \
        --transcript data/cache/e2e/p2-gemma31b-fix-01/backend_data/outputs/0903-科務會議_ac1edcec_逐字稿.txt \
        --label gemma31b \
        --md-out data/cache/staging/coverage/coverage_gemma31b.md

退出碼：
    0 - 成功
    2 - 參數或環境錯誤（檔案不存在、JSON 無法解析、checklist 不是物件等）
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional, Sequence

METRIC_VERSION = "coverage-1.0.0"
SUPPORTED_CHECKLIST_VERSIONS = ("1.0.0",)
VALID_TIERS = ("core", "supporting")
DEFAULT_CATEGORY = "unknown"
# probe token 少於此字數 → 告警（易誤匹配）；fuzzy 也只用 >= 此長度的 token。
MIN_PROBE_TOKEN_CHARS = 2
MAX_MATCHED_POSITIONS = 3


def _find_project_root(start: Path) -> Path:
    """往上尋找含 pyproject.toml 與 backend/ 的專案根。

    staging 目錄（data/cache/staging/coverage/）與正式位置（scripts/e2e/）皆適用；
    找不到時退回與 ``scripts/e2e/measure_record_quality.py`` 相同的 parents[2] 慣例。
    """
    for candidate in (start, *start.parents):
        if (candidate / "pyproject.toml").is_file() and (candidate / "backend").is_dir():
            return candidate
    return start.parents[2] if len(start.parents) > 2 else start


PROJECT_ROOT = _find_project_root(Path(__file__).resolve())
# DATA_DIR 必須在 import backend 模組（OpenCC fallback 路徑）之前備妥
# （同 scripts/e2e/measure_record_quality.py 慣例）。
os.environ.setdefault("DATA_DIR", str(PROJECT_ROOT / "data"))
os.environ.setdefault("LOG_LEVEL", "CRITICAL")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


class CoverageInputError(ValueError):
    """輸入層級錯誤（CLI 參數、檔案、checklist schema）：對應退出碼 2。"""


# ---------------------------------------------------------------------------
# 正規化：雙向對稱（受測紀錄與 checklist token 共用同一條管線）
# ---------------------------------------------------------------------------

_WHITESPACE_PATTERN = re.compile(r"\s+")  # 一般空白、\r、\n、全形空白（NFKC 後轉為空白）
# 只保留：ASCII 英數字 ＋ 中日韓漢字（基本區／擴充 A＋B 以上／相容表意文字）。
_KEEP_PATTERN = re.compile(
    "[^0-9A-Za-z"
    "\u3400-\u4dbf"            # CJK 擴充 A
    "\u4e00-\u9fff"            # CJK 基本區
    "\uf900-\ufaff"            # CJK 相容表意文字
    "\U00020000-\U0003ffff"    # CJK 擴充 B 以上（含相容補充）
    "]"
)


def _is_cjk(char: str) -> bool:
    """是否為本量尺保留的中日韓漢字（與 ``_KEEP_PATTERN`` 同一組範圍）。"""
    return (
        "\u3400" <= char <= "\u4dbf"
        or "\u4e00" <= char <= "\u9fff"
        or "\uf900" <= char <= "\ufaff"
        or "\U00020000" <= char <= "\U0003ffff"
    )


def create_opencc_fold() -> tuple:
    """建立簡繁折疊函式（折到台灣正體）：(fold, source)。

    順序：
    1. ``opencc.OpenCC("s2twp")``（專案既有依賴 ``opencc-python-reimplemented``；
       與 ``backend/core/text_postprocess.py`` 同一轉換器家族）。
    2. ``backend.core.text_postprocess.to_taiwan_traditional``（偵測式、最後手段）。
    3. 皆不可用 → ``(None, "none")``：呼叫端標記 ``opencc_available=false``，
       且**兩邊套同一 identity fallback**（比較仍對稱，只是簡繁寫法無法互通）。

    兩側一律套同一函式是刻意的：s2twp 對已是正體的文本為冪等（實測
    「會議紀錄臺灣組織幹預裡面軟體」二次轉換不變），因此「先轉再比」不會
    讓任一側吃虧；反過來若只轉「偵測到簡體」的那一側，簡繁混寫的 token
    會出現單側未折疊的假漏寫。
    """
    try:
        from opencc import OpenCC

        converter = OpenCC("s2twp")
        return (lambda text: converter.convert(text)), "opencc-s2twp"
    except Exception:  # noqa: BLE001 - 依賴缺失／轉換器建置失敗皆降級
        pass
    try:
        from backend.core.text_postprocess import to_taiwan_traditional

        return to_taiwan_traditional, "backend.core.text_postprocess.to_taiwan_traditional"
    except Exception:  # noqa: BLE001
        return None, "none"


_PINYIN_AVAILABLE: Optional[bool] = None
_CHAR_PINYIN_CACHE: dict = {}
_PINYIN_SYLLABLE_PATTERN = re.compile(r"^[a-zü]+$")


def _pinyin_available() -> bool:
    """pypinyin（專案既有依賴）是否可用；不可用時 fuzzy 誠實停用。"""
    global _PINYIN_AVAILABLE
    if _PINYIN_AVAILABLE is None:
        try:
            from pypinyin import lazy_pinyin  # noqa: F401

            _PINYIN_AVAILABLE = True
        except Exception:  # noqa: BLE001
            _PINYIN_AVAILABLE = False
    return _PINYIN_AVAILABLE


def _char_pinyin(char: str) -> str:
    """單一漢字的拼音音節（快取；失敗時回原字元，讓近音判定自然退化為字面相等）。"""
    cached = _CHAR_PINYIN_CACHE.get(char)
    if cached is not None:
        return cached
    from pypinyin import Style, lazy_pinyin

    try:
        syllables = lazy_pinyin(char, style=Style.NORMAL)
        value = syllables[0] if syllables else char
    except Exception:  # noqa: BLE001
        value = char
    _CHAR_PINYIN_CACHE[char] = value
    return value


# 台灣口音常見的聲母/韻母混淆組（與 backend/services/correction.py 的同名分組一致）。
_INITIAL_EQUIV = [
    {"zh", "z"}, {"ch", "c"}, {"sh", "s"}, {"l", "n"}, {"f", "h"}, {"r", "l"},
]
_FINAL_EQUIV = [
    {"in", "ing"}, {"en", "eng"}, {"an", "ang"}, {"uan", "uang"}, {"ian", "iang"},
    {"o", "e"}, {"uo", "o"},
]
_SYLLABLE_INITIALS = (
    "zh", "ch", "sh", "b", "p", "m", "f", "d", "t", "n", "l", "g", "k", "h",
    "j", "q", "x", "r", "z", "c", "s", "y", "w",
)


def _split_syllable(syllable: str) -> tuple:
    """粗略拆出（聲母, 韻母）。"""
    for initial in _SYLLABLE_INITIALS:
        if syllable.startswith(initial):
            return initial, syllable[len(initial):]
    return "", syllable


def _syllables_near(a: str, b: str) -> bool:
    """兩拼音音節是否同音或近音（台灣口音容錯）。"""
    if a == b:
        return True
    if not (_PINYIN_SYLLABLE_PATTERN.match(a) and _PINYIN_SYLLABLE_PATTERN.match(b)):
        return False
    initial_a, final_a = _split_syllable(a)
    initial_b, final_b = _split_syllable(b)
    initials_ok = initial_a == initial_b or any(
        {initial_a, initial_b} <= group for group in _INITIAL_EQUIV
    )
    finals_ok = final_a == final_b or any(
        {final_a, final_b} <= group for group in _FINAL_EQUIV
    )
    return initials_ok and finals_ok


def _units_near(unit_a: tuple, unit_b: tuple) -> bool:
    """fuzzy 單元比較：英數字只認完全相等；漢字才走拼音近音。"""
    kind_a, value_a = unit_a
    kind_b, value_b = unit_b
    if value_a == value_b:
        return True
    if kind_a != kind_b or kind_a != "cjk":
        return False
    return _syllables_near(value_a, value_b)


class CoverageNormalizer:
    """雙向對稱的字面正規化器（受測紀錄與 checklist token 必須共用同一實例）。"""

    def __init__(
        self,
        *,
        fuzzy: bool = False,
        fold: Optional[Callable[[str], str]] = None,
        fold_source: Optional[str] = None,
    ) -> None:
        if fold is None and fold_source is None:
            fold, fold_source = create_opencc_fold()
        self._fold = fold
        self._opencc_source = fold_source if fold_source is not None else (
            "none" if fold is None else "unknown"
        )
        self.fuzzy_requested = bool(fuzzy)
        self.fuzzy = bool(fuzzy) and _pinyin_available()
        self.warnings: list = []
        if self._fold is None:
            self.warnings.append(
                "OpenCC 不可用：簡繁折疊停用（受測紀錄與 checklist token 套用同一 identity "
                "fallback，比較仍對稱；但簡繁不同寫法將無法互相匹配）。"
            )
        if self.fuzzy_requested and not self.fuzzy:
            self.warnings.append(
                "--fuzzy-homophone 已要求，但 pypinyin 不可用：fuzzy 判定停用（維持純字面比對）。"
            )

    def normalize(self, text: str) -> str:
        """正規化管線：NFKC → casefold → OpenCC → 去空白 → 去標點符號。"""
        if not text:
            return ""
        folded = unicodedata.normalize("NFKC", text)
        folded = folded.casefold()
        if self._fold is not None:
            folded = self._fold(folded)
        folded = _WHITESPACE_PATTERN.sub("", folded)
        return _KEEP_PATTERN.sub("", folded)

    def build_units(self, normalized_text: str) -> Optional[list]:
        """逐字單元（fuzzy 用）：('cjk', 拼音音節) 或 ('lit', 原字元)；fuzzy 關閉時 None。

        逐字建單元（含快取）保證與正規化字串 1:1 對齊，matched_positions 可直接當
        正規化字串索引使用。
        """
        if not self.fuzzy:
            return None
        return [
            ("cjk", _char_pinyin(char)) if _is_cjk(char) else ("lit", char)
            for char in normalized_text
        ]

    def describe(self) -> dict:
        """報告用：實際套用的步驟與可用性標記。"""
        return {
            "steps": [
                "unicode_nfkc",
                "casefold",
                "opencc_fold_s2twp" if self._fold is not None else "opencc_fold_unavailable",
                "strip_whitespace_and_newlines",
                "strip_punctuation_and_symbols",
            ],
            "opencc_available": self._fold is not None,
            "opencc_source": self._opencc_source,
            "folded_to": "台灣正體（OpenCC s2twp）" if self._fold is not None else "未折疊（identity fallback）",
            "kept_chars": "ASCII 英數字 ＋ 中日韓漢字（基本區／擴充 A＋B 以上／相容表意文字）",
            "removed_chars": (
                "空白與換行（含 Windows CRLF）、中英文標點與符號、括號、破折號、'、'、'：'、"
                "'，'、'.'、'-'、'_'、'|'、Markdown 表格管線與 '#'、'*'、'>'、全形空白"
            ),
            "fuzzy": self.fuzzy,
            "fuzzy_requested": self.fuzzy_requested,
            "fuzzy_mode": "pinyin_per_char_near_syllable" if self.fuzzy else "disabled",
        }


# ---------------------------------------------------------------------------
# checklist 載入與驗證
# ---------------------------------------------------------------------------


def validate_checklist(checklist: dict) -> tuple:
    """驗證事實清單並補齊缺欄位：回傳（facts, warnings）。

    刻意寬容（缺 id／tier／category 只補值＋告警，不倒整體）：量尺是觀測工具，
    清單瑕疵應反映在 warnings 與漏寫清單，而不是讓三份紀錄無法量測。
    """
    warnings: list = []

    def warn(message: str) -> None:
        if message not in warnings:
            warnings.append(message)

    version = checklist.get("checklist_version")
    if version not in SUPPORTED_CHECKLIST_VERSIONS:
        warn(
            f"checklist_version 非預期（{version!r}；本量尺支援 {SUPPORTED_CHECKLIST_VERSIONS}）："
            "仍照 schema 1.x 欄位讀取。"
        )

    raw_facts = checklist.get("facts")
    if not isinstance(raw_facts, list) or not raw_facts:
        warn("事實清單沒有 facts（空清單）：所有涵蓋率以 0 計，請先確認清單產生流程。")
        return [], warnings

    facts: list = []
    seen_ids: set = set()
    for index, raw in enumerate(raw_facts, start=1):
        if not isinstance(raw, dict):
            warn(f"第 {index} 筆 fact 不是物件：略過。")
            continue

        fact_id = raw.get("id")
        if not isinstance(fact_id, str) or not fact_id.strip():
            fact_id = f"UNKNOWN-{index:03d}"
            warn(f"第 {index} 筆 fact 缺 id：以 {fact_id} 代替。")
        fact_id = fact_id.strip()
        if fact_id in seen_ids:
            warn(f"fact id 重複（{fact_id}）：重複項仍各自計分。")
        seen_ids.add(fact_id)

        tier = raw.get("tier")
        if tier not in VALID_TIERS:
            warn(f"fact {fact_id} 的 tier 未知（{tier!r}）：歸入 supporting 統計。")
            tier = "supporting"

        category = raw.get("category")
        if not isinstance(category, str) or not category.strip():
            warn(f"fact {fact_id} 缺 category：歸為 {DEFAULT_CATEGORY}。")
            category = DEFAULT_CATEGORY
        else:
            category = category.strip()

        probes = raw.get("probes")
        if not isinstance(probes, list) or not probes:
            warn(f"fact {fact_id} 沒有 probes：永不可能被判定涵蓋。")
            probes = []
        else:
            for group_index, group in enumerate(probes):
                if not isinstance(group, list) or not group:
                    warn(f"fact {fact_id} group {group_index} 不是非空清單：該 group 永不匹配。")
                    continue
                for token in group:
                    if not isinstance(token, str) or not token:
                        warn(f"fact {fact_id} group {group_index} 有非字串或空 token：該 group 永不匹配。")
                        continue
                    if len(token.strip()) < MIN_PROBE_TOKEN_CHARS:
                        warn(
                            f"fact {fact_id} group {group_index} token 少於 "
                            f"{MIN_PROBE_TOKEN_CHARS} 字（{token!r}）：易誤匹配，建議加長。"
                        )

        facts.append(
            {
                "id": fact_id,
                "tier": tier,
                "category": category,
                "statement": str(raw.get("statement") or ""),
                "probes": probes,
            }
        )
    return facts, warnings


def _probe_normalization_warnings(normalizer: CoverageNormalizer, facts: list) -> list:
    """正規化後為空的 token（純標點／空白）→ 該 group 永不匹配，列入 warnings。"""
    warnings: list = []
    for fact in facts:
        probes = fact["probes"]
        if not isinstance(probes, list):
            continue
        for group_index, group in enumerate(probes):
            if not isinstance(group, list) or not group:
                continue
            normalized = [
                normalizer.normalize(token) for token in group if isinstance(token, str)
            ]
            if any(not token for token in normalized):
                message = (
                    f"fact {fact['id']} group {group_index} 含正規化後為空的 token"
                    "（純標點／空白等）：該 group 永不匹配，請改用實詞關鍵詞。"
                )
                if message not in warnings:
                    warnings.append(message)
    return warnings


# ---------------------------------------------------------------------------
# 匹配：group 內 AND、group 間 OR
# ---------------------------------------------------------------------------


def _find_fuzzy(record_units: list, token_units: list) -> int:
    """逐字拼音近音掃描：回傳首個命中視窗的起始索引（正規化字串索引），無命中回 -1。"""
    if not record_units or not token_units:
        return -1
    span = len(token_units)
    if span > len(record_units):
        return -1
    for start in range(len(record_units) - span + 1):
        if all(
            _units_near(record_units[start + offset], token_units[offset])
            for offset in range(span)
        ):
            return start
    return -1


def match_fact(
    normalizer: CoverageNormalizer,
    record_norm: str,
    record_units: Optional[list],
    probes,
) -> dict:
    """單一事實匹配：回傳 covered／matched_group_index／matched_positions／reason。"""
    if not isinstance(probes, list) or not probes:
        return {
            "covered": False,
            "matched_group_index": None,
            "matched_positions": [],
            "reason": "no_probe_group_matched",
        }
    for group_index, group in enumerate(probes):
        if not isinstance(group, list) or not group:
            continue
        tokens = [normalizer.normalize(token) for token in group if isinstance(token, str)]
        if not tokens or len(tokens) != len(group) or any(not token for token in tokens):
            # 空 token（含非字串）使 group 永不匹配；warnings 已於驗證階段記錄。
            continue
        positions: list = []
        matched = True
        for token in tokens:
            position = record_norm.find(token)
            if position < 0 and normalizer.fuzzy and record_units is not None:
                if len(token) >= MIN_PROBE_TOKEN_CHARS:
                    token_units = normalizer.build_units(token)
                    position = _find_fuzzy(record_units, token_units) if token_units else -1
            if position < 0:
                matched = False
                break
            positions.append(position)
        if matched:
            return {
                "covered": True,
                "matched_group_index": group_index,
                "matched_positions": positions[:MAX_MATCHED_POSITIONS],
                "reason": None,
            }
    return {
        "covered": False,
        "matched_group_index": None,
        "matched_positions": [],
        "reason": "no_probe_group_matched",
    }


def _ratio(covered: int, total: int) -> float:
    """涵蓋率（總數為 0 時回 0.0；請以計數欄判讀無母數情況）。"""
    return round(covered / total, 4) if total else 0.0


def _aggregate(facts: list, matches: list) -> dict:
    """彙總：總數／core／supporting／分類涵蓋率與漏寫清單。"""
    fact_total = len(facts)
    core_total = sum(1 for fact in facts if fact["tier"] == "core")
    supporting_total = fact_total - core_total
    covered_total = sum(1 for match in matches if match["covered"])
    covered_core = sum(
        1 for fact, match in zip(facts, matches) if fact["tier"] == "core" and match["covered"]
    )
    covered_supporting = covered_total - covered_core
    missing_core = [
        (fact, match)
        for fact, match in zip(facts, matches)
        if fact["tier"] == "core" and not match["covered"]
    ]
    missing_supporting = [
        fact
        for fact, match in zip(facts, matches)
        if fact["tier"] != "core" and not match["covered"]
    ]

    by_category: dict = {}
    for fact, match in zip(facts, matches):
        bucket = by_category.setdefault(
            fact["category"], {"total": 0, "covered": 0, "coverage": 0.0}
        )
        bucket["total"] += 1
        if match["covered"]:
            bucket["covered"] += 1
    for bucket in by_category.values():
        bucket["coverage"] = _ratio(bucket["covered"], bucket["total"])

    return {
        "fact_total": fact_total,
        "fact_core_total": core_total,
        "fact_supporting_total": supporting_total,
        "covered_total": covered_total,
        "covered_core": covered_core,
        "covered_supporting": covered_supporting,
        "coverage_all": _ratio(covered_total, fact_total),
        "coverage_core": _ratio(covered_core, core_total),
        "coverage_supporting": _ratio(covered_supporting, supporting_total),
        "missing_core_ids": [fact["id"] for fact, _ in missing_core],
        "missing_core_statements": [fact["statement"] for fact, _ in missing_core],
        "missing_supporting_ids": [fact["id"] for fact in missing_supporting],
        "by_category": by_category,
    }


def _build_notes(normalizer: CoverageNormalizer) -> dict:
    """報告內嵌的指標定義／語意／已知限制（與 README 同文）。"""
    return {
        "definitions": {
            "metric_version": f"量尺版本（{METRIC_VERSION}）；欄位語意變更時遞增，不得就地改義。",
            "coverage_all": "已涵蓋事實數／事實總數（0~1）。",
            "coverage_core": "core 事實涵蓋率；分母＝fact_core_total（0 筆時為 0.0）。",
            "coverage_supporting": "supporting 事實涵蓋率；分母＝fact_supporting_total（0 筆時為 0.0，請以計數欄判讀）。",
            "covered_total": "至少命中一個 probe group 的事實數（group 內 AND、group 間 OR）。",
            "missing_core_ids": "未涵蓋的 core fact id（清單順序）。",
            "missing_core_statements": "對應 missing_core_ids 的 statement（同序）。",
            "by_category": "每類 category 的 total／covered／coverage（類別順序＝清單首次出現順序）。",
            "record_char_count": "受測紀錄 Markdown 全文 len(text)（含換行）；與 measure_record_quality.py 的 char_count 同定義。",
            "record_normalized_char_count": "正規化後字元數；matched_positions 的索引以此字串為準。",
            "matched_group_index": "第一個命中的 probe group index（0 起算）；命中即停。",
            "matched_positions": "該 group 內各 token 在正規化後紀錄的首次出現起始索引（依 token 宣告順序，最多前 3 個）。",
            "reason": "未涵蓋時固定為 no_probe_group_matched（所有 probe group 皆未全數命中）。",
            "normalization": "實際套用的正規化步驟與 OpenCC 可用性；受測紀錄與 checklist token 一律套同一條管線（雙向對稱）。",
            "warnings": "輸入或 probes 品質告警（空清單、token <2 字、正規化後為空、tier 未知、重複 id、OpenCC／pypinyin 不可用…）。",
            "transcript": "觀察值：同一組 probes 對逐字稿的涵蓋率；未提供 --transcript 時為 null。",
        },
        "semantics": {
            "probes": "任一 group 內全部 token 都出現在受測紀錄 → 該事實算被涵蓋（group 內 AND、group 間 OR）。",
            "scope": "只量『事實有沒有以可辨識的詞面被寫進紀錄』；不是語意蘊含判定，也不評價敘述正確性與出處標註（那是 measure_record_quality.py 的 tag_traceability）。",
            "determinism": "同輸入（紀錄＋清單＋參數）→ byte 相同輸出；不呼叫網路、LLM、LM Studio；預設不寫時間戳（--timestamp 才寫 generated_at）。",
            "fuzzy": "fuzzy=false 時純字面；--fuzzy-homophone 開啟時，字面未命中才改用逐字拼音近音（台灣口音聲母/韻母混淆組，同 backend.services.correction），僅供除錯與觀察。",
        },
        "limitations": [
            "字面量尺：換句話說、語序重排、同義改寫的事實可能被計為漏寫（false negative），漏寫清單必須人工抽查再定案。",
            "反向風險：紀錄中零散出現關鍵詞即算涵蓋，關鍵詞堆砌或表格殘留可能造成 false positive。",
            "不判否定與數字正確性：『同意』與『不同意』在 token 層面同分；probe 只要求數字 token 出現，不檢查數值是否正確。",
            "fuzzy 只處理同音近音錯字，不處理 ASR 漏字／斷詞錯誤；此類差異會落在漏寫清單。",
            "清單品質（fact 是否真的來自逐字稿）不由本量尺保證；--transcript 觀察值是第一層交叉檢查。",
            "單次抽樣限制（temperature 0.7），跨模型差異解讀仍需搭配重跑次數。",
        ],
    }


# ---------------------------------------------------------------------------
# 量測入口
# ---------------------------------------------------------------------------


def measure_coverage(
    record_text: str,
    checklist: dict,
    *,
    label: Optional[str] = None,
    record_path: Optional[str] = None,
    record_sha256: Optional[str] = None,
    checklist_path: Optional[str] = None,
    checklist_sha256: Optional[str] = None,
    transcript_text: Optional[str] = None,
    transcript_path: Optional[str] = None,
    transcript_sha256: Optional[str] = None,
    fuzzy: bool = False,
    generated_at: Optional[str] = None,
) -> dict:
    """量測入口：回傳固定 schema 報告（全部為確定性字面統計，無 LLM）。"""
    if not isinstance(checklist, dict):
        raise CoverageInputError("checklist 必須是 JSON 物件（{...}）。")

    normalizer = CoverageNormalizer(fuzzy=fuzzy)
    facts, warnings = validate_checklist(checklist)
    for message in normalizer.warnings + _probe_normalization_warnings(normalizer, facts):
        if message not in warnings:
            warnings.append(message)

    record_norm = normalizer.normalize(record_text)
    record_units = normalizer.build_units(record_norm) if normalizer.fuzzy else None
    matches = [
        match_fact(normalizer, record_norm, record_units, fact["probes"]) for fact in facts
    ]
    summary = _aggregate(facts, matches)

    fact_details = [
        {
            "id": fact["id"],
            "category": fact["category"],
            "tier": fact["tier"],
            "statement": fact["statement"],
            "probe_group_count": len(fact["probes"]) if isinstance(fact["probes"], list) else 0,
            "covered": match["covered"],
            "matched_group_index": match["matched_group_index"],
            "matched_positions": match["matched_positions"],
            "reason": match["reason"],
        }
        for fact, match in zip(facts, matches)
    ]

    transcript_block = None
    if transcript_text is not None:
        transcript_norm = normalizer.normalize(transcript_text)
        transcript_units = normalizer.build_units(transcript_norm) if normalizer.fuzzy else None
        transcript_matches = [
            match_fact(normalizer, transcript_norm, transcript_units, fact["probes"])
            for fact in facts
        ]
        transcript_summary = _aggregate(facts, transcript_matches)
        transcript_block = {
            "transcript_path": transcript_path,
            "transcript_sha256": transcript_sha256,
            "transcript_char_count": len(transcript_text),
            "fact_total": transcript_summary["fact_total"],
            "covered_total": transcript_summary["covered_total"],
            "covered_core": transcript_summary["covered_core"],
            "coverage_all": transcript_summary["coverage_all"],
            "coverage_core": transcript_summary["coverage_core"],
            "missing_core_ids": transcript_summary["missing_core_ids"],
            "missing_supporting_ids": transcript_summary["missing_supporting_ids"],
            "note": (
                "觀察值：同一組 probes 對逐字稿（含時間戳與發言者標籤）的涵蓋率，用來分辨"
                "『模型漏寫』與『清單事實根本沒出現在逐字稿（ASR 變體／清單瑕疵）』；"
                "永不作為閘門。"
            ),
        }

    report = {
        "metric_version": METRIC_VERSION,
        "label": label if label is not None else (Path(record_path).stem if record_path else ""),
        "record_path": record_path,
        "record_sha256": record_sha256,
        "record_char_count": len(record_text),
        "record_normalized_char_count": len(record_norm),
        "checklist_path": checklist_path,
        "checklist_sha256": checklist_sha256,
        "checklist_version": checklist.get("checklist_version"),
        "meeting": checklist.get("meeting"),
        **summary,
        "normalization": normalizer.describe(),
        "warnings": warnings,
        "transcript": transcript_block,
        "facts": fact_details,
        "notes": _build_notes(normalizer),
    }
    if generated_at is not None:
        report["generated_at"] = generated_at
    return report


# ---------------------------------------------------------------------------
# Markdown 人類可讀報告
# ---------------------------------------------------------------------------


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _ratio_text(value: float, covered: int, total: int) -> str:
    return f"{value:.4f}（{_pct(value)}；{covered}/{total}）"


def render_markdown(report: dict) -> str:
    """把報告渲染成 Markdown（確定性：同報告 → 同文字）。"""
    norm = report["normalization"]
    lines: list = []
    lines.append(f"# 事實涵蓋率報告：{report.get('label') or '(未命名)'}")
    lines.append("")
    lines.append(f"- 量尺版本：`{report.get('metric_version')}`")
    lines.append(
        f"- 受測紀錄：`{report.get('record_path')}`（sha256 `{report.get('record_sha256')}`；"
        f"字元數 {report['record_char_count']}，正規化後 {report['record_normalized_char_count']}）"
    )
    lines.append(
        f"- 事實清單：`{report.get('checklist_path')}`（sha256 `{report.get('checklist_sha256')}`；"
        f"checklist_version `{report.get('checklist_version')}`；meeting "
        f"`{report.get('meeting')}`；共 {report['fact_total']} 條＝core {report['fact_core_total']}"
        f"＋supporting {report['fact_supporting_total']}）"
    )
    lines.append(
        f"- 正規化：{'、'.join(norm['steps'])}；OpenCC "
        + (f"可用（`{norm['opencc_source']}`）" if norm["opencc_available"] else "**不可用**（identity fallback，兩側同一套）")
        + f"；fuzzy {'啟用（' + norm['fuzzy_mode'] + '）' if norm['fuzzy'] else '停用'}"
    )
    transcript = report.get("transcript")
    if transcript:
        lines.append(
            f"- 逐字稿（觀察值）：`{transcript['transcript_path']}`；"
            f"coverage_all {_ratio_text(transcript['coverage_all'], transcript['covered_total'], transcript['fact_total'])}、"
            f"coverage_core {_ratio_text(transcript['coverage_core'], transcript['covered_core'], report['fact_core_total'])}"
        )
    if report.get("generated_at"):
        lines.append(f"- 產生時間：{report['generated_at']}")
    lines.append("")

    lines.append("## 總覽")
    lines.append("")
    lines.append("| 指標 | 數值 |")
    lines.append("| --- | --- |")
    lines.append(
        f"| coverage_all | {_ratio_text(report['coverage_all'], report['covered_total'], report['fact_total'])} |"
    )
    lines.append(
        f"| coverage_core | {_ratio_text(report['coverage_core'], report['covered_core'], report['fact_core_total'])} |"
    )
    lines.append(
        f"| coverage_supporting | {_ratio_text(report['coverage_supporting'], report['covered_supporting'], report['fact_supporting_total'])} |"
    )
    lines.append("")

    lines.append("## 分類涵蓋率")
    lines.append("")
    lines.append("| category | total | covered | coverage |")
    lines.append("| --- | --- | --- | --- |")
    if report["by_category"]:
        for category, bucket in report["by_category"].items():
            lines.append(
                f"| {category} | {bucket['total']} | {bucket['covered']} | {_ratio_text(bucket['coverage'], bucket['covered'], bucket['total'])} |"
            )
    else:
        lines.append("| （無 facts） | 0 | 0 | 0.0000 |")
    lines.append("")

    lines.append(f"## 漏寫事實（core；{len(report['missing_core_ids'])} 條）")
    lines.append("")
    if report["missing_core_ids"]:
        for index, (fact_id, statement) in enumerate(
            zip(report["missing_core_ids"], report["missing_core_statements"]), start=1
        ):
            lines.append(f"{index}. `{fact_id}` {statement}")
    else:
        lines.append("（無）")
    lines.append("")

    lines.append(f"## 漏寫事實（supporting；{len(report['missing_supporting_ids'])} 條）")
    lines.append("")
    if report["missing_supporting_ids"]:
        lines.append("、".join(f"`{fact_id}`" for fact_id in report["missing_supporting_ids"]))
    else:
        lines.append("（無）")
    lines.append("")

    lines.append(f"## 警告（{len(report['warnings'])} 條）")
    lines.append("")
    if report["warnings"]:
        for warning in report["warnings"]:
            lines.append(f"- {warning}")
    else:
        lines.append("（無）")
    lines.append("")

    lines.append("## 事實明細")
    lines.append("")
    lines.append("| id | tier | category | 涵蓋 | matched group | matched positions | 備註 |")
    lines.append("| --- | --- | --- | --- | --- | --- | --- |")
    for fact in report["facts"]:
        covered_mark = "✅" if fact["covered"] else "❌"
        group = fact["matched_group_index"] if fact["matched_group_index"] is not None else "-"
        positions = ", ".join(str(position) for position in fact["matched_positions"]) or "-"
        note = fact["reason"] or ""
        lines.append(
            f"| `{fact['id']}` | {fact['tier']} | {fact['category']} | {covered_mark} | "
            f"{group} | {positions} | {note} |"
        )
    lines.append("")

    lines.append("## 指標定義")
    lines.append("")
    for key, text in report["notes"]["definitions"].items():
        lines.append(f"- **{key}**：{text}")
    lines.append("")

    lines.append("## 已知限制")
    lines.append("")
    for item in report["notes"]["limitations"]:
        lines.append(f"- {item}")
    lines.append("")
    return "\n".join(lines).rstrip("\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="measure_coverage.py",
        description=(
            "確定性事實涵蓋率量尺：受測會議紀錄 Markdown＋事實清單 JSON → 涵蓋率報告"
            "（stdout JSON；可另寫 JSON／Markdown）。不呼叫 LLM／網路／LM Studio。"
        ),
    )
    parser.add_argument(
        "--record", type=Path, required=True, help="受測會議紀錄 Markdown 路徑（.docx 不受理）"
    )
    parser.add_argument(
        "--checklist", type=Path, required=True, help="事實清單 JSON 路徑（schema 見 README）"
    )
    parser.add_argument("--json-out", type=Path, default=None, help="另寫一份 JSON 檔（stdout 仍輸出同一份）")
    parser.add_argument("--md-out", type=Path, default=None, help="寫一份 Markdown 人類可讀報告")
    parser.add_argument("--label", default=None, help="報告顯示名稱；預設＝紀錄檔名 stem")
    parser.add_argument(
        "--transcript", type=Path, default=None, help="逐字稿 txt（選用；提供時多一段 transcript 觀察值）"
    )
    parser.add_argument(
        "--fuzzy-homophone",
        action="store_true",
        help="字面未命中時改用逐字拼音近音（pypinyin；預設關）",
    )
    timestamp_group = parser.add_mutually_exclusive_group()
    timestamp_group.add_argument(
        "--timestamp", dest="timestamp", action="store_true", help="在報告寫入 generated_at（UTC ISO8601）"
    )
    timestamp_group.add_argument(
        "--no-timestamp", dest="timestamp", action="store_false", help="不寫 generated_at（預設；顯式化用）"
    )
    parser.set_defaults(timestamp=False)
    return parser.parse_args(argv)


def _read_text(path: Path) -> tuple:
    """讀檔並回傳（文字, sha256）；sha256 以原始 bytes 計（與換行正規化無關）。"""
    data = path.read_bytes()
    return data.decode("utf-8"), hashlib.sha256(data).hexdigest()


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)

    if args.record.suffix.lower() in {".docx", ".doc"}:
        print(f"ERROR: 本量尺只收 Markdown 紀錄（docx 段落合併使行結構失真）：{args.record}", file=sys.stderr)
        return 2
    if not args.record.exists():
        print(f"ERROR: 找不到紀錄檔案：{args.record}", file=sys.stderr)
        return 2
    if not args.checklist.exists():
        print(f"ERROR: 找不到事實清單：{args.checklist}", file=sys.stderr)
        return 2
    if args.transcript is not None and not args.transcript.exists():
        print(f"ERROR: 找不到逐字稿檔案：{args.transcript}", file=sys.stderr)
        return 2

    try:
        record_text, record_sha = _read_text(args.record)
        checklist_text, checklist_sha = _read_text(args.checklist)
        transcript_text = None
        transcript_sha = None
        if args.transcript is not None:
            transcript_text, transcript_sha = _read_text(args.transcript)
    except UnicodeDecodeError as exc:
        print(f"ERROR: 檔案不是 UTF-8 文字：{exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"ERROR: 讀取檔案失敗：{exc}", file=sys.stderr)
        return 2

    try:
        checklist = json.loads(checklist_text)
    except json.JSONDecodeError as exc:
        print(f"ERROR: 事實清單 JSON 無法解析：{exc}", file=sys.stderr)
        return 2

    generated_at = None
    if args.timestamp:
        generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    try:
        report = measure_coverage(
            record_text,
            checklist,
            label=args.label,
            record_path=str(args.record),
            record_sha256=record_sha,
            checklist_path=str(args.checklist),
            checklist_sha256=checklist_sha,
            transcript_text=transcript_text,
            transcript_path=str(args.transcript) if args.transcript is not None else None,
            transcript_sha256=transcript_sha,
            fuzzy=args.fuzzy_homophone,
            generated_at=generated_at,
        )
    except CoverageInputError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    payload = json.dumps(report, ensure_ascii=False, indent=2)
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(payload + "\n", encoding="utf-8")
    if args.md_out is not None:
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        args.md_out.write_text(render_markdown(report) + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
