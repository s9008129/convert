#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TaskProcessor 與記錄級後處理（text_postprocess）測試。

v4.2 起記錄級清理移至 backend.core.text_postprocess（P1-9，於驗證前執行），
本檔同步改測新模組；TaskProcessor 僅測「包裝輸出」行為（含 P0-5 失敗顯性化）。
"""

import importlib

from backend.core.text_postprocess import (
    ensure_record_structure,
    finalize_record,
    has_excessive_english,
    remove_english_segments,
    sanitize_text_language,
)
from backend.models.schemas import ProcessingMode, TaskInfo
from backend.services.task_processor import TaskProcessor

task_processor_module = importlib.import_module("backend.services.task_processor")


def test_ensure_structure_inserts_missing_sections_and_converts_action_bullets():
    summary = """會議名稱：113年度第1次專案進度追蹤會議
會議時間：中華民國113年3月1日 09時00分至10時30分
會議地點：本部第2會議室
主  席：王主任○○
出席人員：王主任、陳科長
列席人員：資訊室林專員
記  錄：AI 會議助理

一、 報告事項：
1. 專案整體進度維持如期。"""

    repaired = ensure_record_structure(summary)

    assert "二、 討論事項：" in repaired
    assert "三、 主席裁示事項（後續管考與追蹤）：" in repaired
    assert "案由：逐字稿未提及" in repaired
    assert "決議：" in repaired
    assert "主辦單位：逐字稿未提及" in repaired


def test_ensure_structure_preserves_existing_new_format_rows():
    summary = """會議名稱：113年度第1次專案進度追蹤會議
會議時間：中華民國113年3月1日 09時00分至10時30分
會議地點：本部第2會議室
主  席：王主任○○
出席人員：王主任、陳科長
列席人員：資訊室林專員
記  錄：AI 會議助理

一、 報告事項：
1. 專案整體進度維持如期。

二、 討論事項：
案由：關於專案里程碑與上線前準備事宜，提請 審議。
說明：
1. 專案已完成整合測試。
2. 上線公告草案待確認。
各單位意見（多方立場）：
- 王主任：建議依原定期程推進。
- 陳科長：應先完成公告草案。
決議：
1. 維持月底上線時程。（主辦單位：資訊室，協辦單位：行政室）
2. 完成整合測試及上線公告草案。（主辦單位：資訊室，協辦單位：行政室）

三、 主席裁示事項（後續管考與追蹤）：
1. 請於下週三前完成整合測試。（主辦單位：王主任，辦理期程：下週三前）
2. 請於本週五前提交上線公告草案。（主辦單位：陳科長，辦理期程：本週五前）"""

    repaired = ensure_record_structure(summary)

    assert repaired.count("主辦單位：資訊室") == 2
    assert repaired.count("辦理期程：") == 2
    assert "逐字稿未提及" not in repaired


def test_ensure_structure_tolerates_single_space_field_variants():
    """P1-8：欄位存在性採容錯比對，「主 席：」單空格不應被判為缺漏而重複補欄。"""
    summary = """會議名稱：測試會議
會議時間：中華民國113年3月1日
會議地點：本部第2會議室
主 席：王主任
出席人員：資訊室
列席人員：無
記 錄：AI 會議助理

一、 報告事項：
無

二、 討論事項：
案由：測試案由，提請 審議。
說明：測試說明。
各單位意見（多方立場）：
- 資訊室：無意見。
決議：
1. 照案通過。（主辦單位：資訊室，協辦單位：無）

三、 主席裁示事項（後續管考與追蹤）：
1. 依決議辦理。（主辦單位：資訊室，辦理期程：（待確認））"""

    repaired = ensure_record_structure(summary)

    # 不應因空格差異而補出第二份欄位
    assert repaired.count("會議名稱") == 1
    assert "逐字稿未提及" not in repaired


def test_language_cleanup_keeps_important_technical_terms():
    summary = """案由：關於 OAuth2、JWT 與 GitHub Actions 上線事宜，提請 審議。
決議：
1. 相關技術納入上線範圍，Okay。"""

    sanitized = sanitize_text_language(summary)

    assert "OAuth2" in sanitized
    assert "JWT" in sanitized
    assert "GitHub Actions" in sanitized
    assert "Okay" not in sanitized
    assert "好" in sanitized


def test_excessive_english_detection_is_not_triggered_by_mixed_technical_summary():
    summary = """案由：關於 API 串接、OAuth2 驗證、GitHub Actions 部署與 AWS 資源調整，提請 審議。
說明：
1. 相關規劃已進入測試階段。
決議：
1. 整體仍以中文敘述為主，並確認月底前完成上線。"""

    assert has_excessive_english(summary) is False


def test_remove_english_segments_drops_preamble_but_keeps_record_and_terms():
    text = "\n".join([
        "Analysis of the Transcript: the content revolves around a project review meeting.",
        "Evaluation Criteria: Legal Compliance, Responsibility Clarity.",
        "會議名稱：113年度第1次專案進度追蹤會議",
        "會議地點：（待確認）",
        "案由：關於 OAuth2 與 GitHub Actions 上線事宜，提請 審議。",
    ])

    cleaned = remove_english_segments(text)

    assert "Analysis of the Transcript" not in cleaned
    assert "Evaluation Criteria" not in cleaned
    assert "會議名稱：113年度第1次專案進度追蹤會議" in cleaned
    assert "會議地點：（待確認）" in cleaned
    assert "OAuth2" in cleaned and "GitHub Actions" in cleaned


def test_remove_english_segments_protects_pending_marker_even_when_line_is_english():
    """含（待確認）的合法缺漏標記不可被英文比例規則誤刪。"""
    text = "TBD location info （待確認）"

    cleaned = remove_english_segments(text)

    assert "（待確認）" in cleaned


def test_remove_english_segments_protects_glossary_terms():
    """P1-10：詞彙表命中的英文專名行受白名單保護。"""
    text = "Ollama GPU server deployment status check"

    assert "Ollama" not in remove_english_segments(text)
    assert "Ollama" in remove_english_segments(text, protected_terms={"Ollama"})


def test_finalize_record_normalizes_common_local_output_artifacts():
    """記錄級後處理（驗證前）應清除常見輸出瑕疵（原 _format_result 職責）。"""
    summary = """會議名稱：測試會議
會議時間：中華民國113年3月1日 09時00分至10時30分
會議地點：本部第2會議室
主  席：王主任○○
出席人員：資訊室、業務組
列席人員：無
記  錄：AI 會議助理

二、 討論事項：
案由：關於流程順序與現場支援事宜，提請 審議。
說明：
1. 流程順序定為：縣長致詞 $\\rightarrow$ 簡報。
決議：
1. 現場教官需 Stand by。"""

    result = finalize_record(summary)

    assert "$\\rightarrow$" not in result
    assert "Stand by" not in result
    assert "→" in result
    assert "待命" in result


def _make_task() -> TaskInfo:
    return TaskInfo(
        task_id="task1234",
        filename="meeting.mp3",
        original_filename="測試會議.mp3",
        file_size=1024,
        processing_mode=ProcessingMode.LOCAL,
    )


def _patch_device(monkeypatch):
    monkeypatch.setattr(task_processor_module.device_detector, "current_device", "cpu")
    monkeypatch.setattr(
        task_processor_module.device_detector,
        "get_device_info",
        lambda: {"current_device": "cpu", "gpu_available": False, "mps_available": False},
    )


def test_format_result_does_not_rewrite_validated_summary(monkeypatch):
    """P1-9：驗證後的紀錄本文不得再被 _format_result 改寫。"""
    processor = TaskProcessor()
    _patch_device(monkeypatch)
    summary = "會議名稱：測試會議\n決議：\n1. 照案通過。"

    result = processor._format_result(_make_task(), "逐字稿內容", summary)

    assert summary in result
    # v4.2.3：交付文件只留紀錄本文——逐字稿改由獨立下載、處理資訊只進 log
    assert result.startswith("# 會議紀錄")
    assert "原始逐字稿" not in result
    assert "逐字稿內容" not in result
    assert "處理模式" not in result
    assert "運算裝置" not in result


def test_format_result_marks_summary_failure_explicitly(monkeypatch):
    """P0-5：摘要失敗時輸出必須顯著標示，不得偽裝成會議紀錄。"""
    processor = TaskProcessor()
    _patch_device(monkeypatch)

    result = processor._format_result(
        _make_task(), "逐字稿內容", None, summary_error="Ollama 服務不可用"
    )

    assert "會議紀錄生成失敗" in result
    assert "僅包含逐字稿" in result
    assert "Ollama 服務不可用" in result
    assert result.startswith("# 逐字稿（會議紀錄生成失敗）")
