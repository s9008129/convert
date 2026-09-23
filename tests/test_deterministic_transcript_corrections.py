#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""確定性誤辨修正與保護詞表護欄測試（P5：校正層「保護詞表＋同音替換白名單」）。

設計依據：`quality-parity-01/report.md` §4.3／§七-1——同一份 ASR 快取在 gemma
校正下修好 `內機→內稽`、在 27B 校正下沒修，直接吃掉一條 core 事實。修法是把
「必須改的錯形」與「不得被改的保護詞」寫成資料檔，交由確定性規則執行。
"""

import pytest

from backend.core.config import settings
from backend.core.text_postprocess import clean_transcript
from backend.services.correction import gate_correction, transcript_correction_service


@pytest.fixture()
def glossary_dir(tmp_path, monkeypatch):
    """以臨時詞彙表目錄隔離測試（不改 repo 的 data/glossary）。"""
    from backend.core import glossary as glossary_module

    directory = tmp_path / "glossary"
    directory.mkdir()
    (directory / "測試詞表.txt").write_text(
        "內稽\n戶數\n差勤\n審計員\n內機=>內稽\n護數=>戶數\n拆勤=>差勤\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(settings, "GLOSSARY_DIR", str(directory), raising=False)
    glossary_module.load_glossary(force=True)
    yield directory
    monkeypatch.undo()
    glossary_module.load_glossary(force=True)


@pytest.fixture()
def empty_glossary_dir(tmp_path, monkeypatch):
    from backend.core import glossary as glossary_module

    directory = tmp_path / "empty_glossary"
    directory.mkdir()
    monkeypatch.setattr(settings, "GLOSSARY_DIR", str(directory), raising=False)
    glossary_module.load_glossary(force=True)
    yield directory
    monkeypatch.undo()
    glossary_module.load_glossary(force=True)


# ---------------------------------------------------------------------------
# 確定性誤辨修正（資料檔驅動，不吃 LLM）
# ---------------------------------------------------------------------------

def test_known_correction_is_deterministic_without_llm(glossary_dir):
    from backend.core.glossary import apply_known_corrections

    fixed, applied = apply_known_corrections("下個禮拜一我們要做內機檢查，順便看一下護數。")

    assert "內稽" in fixed and "內機" not in fixed
    assert "戶數" in fixed and "護數" not in fixed
    assert ("內機", "內稽", 1) in applied and ("護數", "戶數", 1) in applied


def test_known_correction_is_idempotent(glossary_dir):
    from backend.core.glossary import apply_known_corrections

    once, _ = apply_known_corrections("要做內機檢查")
    twice, applied = apply_known_corrections(once)

    assert twice == once == "要做內稽檢查"
    assert applied == []


def test_single_character_pair_is_ignored(tmp_path, monkeypatch):
    from backend.core import glossary as glossary_module
    from backend.core.glossary import apply_known_corrections

    directory = tmp_path / "short_pair"
    directory.mkdir()
    (directory / "詞表.txt").write_text("機=>稽\n", encoding="utf-8")
    monkeypatch.setattr(settings, "GLOSSARY_DIR", str(directory), raising=False)
    glossary_module.load_glossary(force=True)
    try:
        fixed, applied = apply_known_corrections("要做內機檢查")
        assert fixed == "要做內機檢查" and applied == []
    finally:
        monkeypatch.undo()
        glossary_module.load_glossary(force=True)


def test_no_pairs_keeps_text_unchanged(empty_glossary_dir):
    from backend.core.glossary import apply_known_corrections

    assert apply_known_corrections("要做內機檢查") == ("要做內機檢查", [])


def test_clean_transcript_reports_glossary_fixes(glossary_dir):
    cleaned, stats = clean_transcript("下週一要做內機檢查。")

    assert "內稽" in cleaned
    assert ("內機", "內稽") in stats["term_fixes"]


def test_exclusion_compound_is_not_rewritten(tmp_path, monkeypatch):
    from backend.core import glossary as glossary_module
    from backend.core.glossary import apply_known_corrections

    directory = tmp_path / "exclusion"
    directory.mkdir()
    (directory / "詞表.txt").write_text(
        "審員=>審計員\n!評審員\n!複審員\n", encoding="utf-8"
    )
    monkeypatch.setattr(settings, "GLOSSARY_DIR", str(directory), raising=False)
    glossary_module.load_glossary(force=True)
    try:
        fixed, applied = apply_known_corrections("三位評審員與一位審員到場。")
        assert "評審員" in fixed          # 排除複合詞不動
        assert "審計員到場" in fixed      # 真正的誤辨要修
        assert applied == [("審員", "審計員", 1)]
    finally:
        monkeypatch.undo()
        glossary_module.load_glossary(force=True)


# ---------------------------------------------------------------------------
# 保護詞表護欄（LLM 不得消滅保護詞）
# ---------------------------------------------------------------------------

def test_gate_rejects_change_destroying_protected_term(glossary_dir):
    original = "下週一要內稽，請準備資料。"
    corrected = "下週一要內機，請準備資料。"  # 同音（機/稽）但會消滅保護詞

    gated, changes = gate_correction(original, corrected, max_change_ratio=0.5)

    assert gated == original
    assert changes and all(not change.accepted for change in changes)
    assert any("保護詞" in change.reason for change in changes)


def test_gate_still_accepts_homophone_elsewhere(glossary_dir):
    original = "內稽前請在確認一次資料。"
    corrected = "內稽前請再確認一次資料。"  # 在/再 同音，且未動到保護詞

    gated, changes = gate_correction(original, corrected, max_change_ratio=0.5)

    assert "再確認" in gated and "內稽" in gated
    assert any(change.accepted for change in changes)


# ---------------------------------------------------------------------------
# 服務層整合：LLM 不提修正也要修好
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_correct_transcript_applies_known_fixes_without_llm_proposal(glossary_dir):
    async def generate_fn(_system_prompt: str, _user_message: str) -> str:
        return ""  # 模擬校正模型「什麼都沒提」

    corrected, report = await transcript_correction_service.correct_transcript(
        "下個禮拜一我們要做內機檢查。", generate_fn
    )

    assert "內稽" in corrected and "內機" not in corrected
    assert report.known_fixes_applied == 1
    assert [change.corrected for change in report.deterministic_changes] == ["內稽"]
    assert "內機" in report.to_markdown()
