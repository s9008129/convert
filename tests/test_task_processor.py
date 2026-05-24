#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TaskProcessor 結構修補測試。
"""

import importlib

from backend.models.schemas import ProcessingMode, TaskInfo
from backend.services.task_processor import TaskProcessor

task_processor_module = importlib.import_module("backend.services.task_processor")


def test_ensure_structure_inserts_missing_sections_and_converts_action_bullets():
    processor = TaskProcessor()
    summary = """會議名稱：113年度第1次專案進度追蹤會議
會議時間：中華民國113年3月1日 09時00分至10時30分
會議地點：本部第2會議室
主  席：王主任○○
出席人員：王主任、陳科長
列席人員：資訊室林專員
記  錄：AI 會議助理

一、 報告事項：
1. 專案整體進度維持如期。"""

    repaired = processor._ensure_structure(summary)

    assert "二、 討論事項：" in repaired
    assert "三、 主席裁示事項（後續管考與追蹤）：" in repaired
    assert "案由：逐字稿未提及" in repaired
    assert "決議：" in repaired
    assert "主辦單位：逐字稿未提及" in repaired


def test_ensure_structure_preserves_existing_new_format_rows():
    processor = TaskProcessor()
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

    repaired = processor._ensure_structure(summary)

    assert repaired.count("主辦單位：資訊室") == 2
    assert repaired.count("辦理期程：") == 2
    assert "逐字稿未提及" not in repaired


def test_language_cleanup_keeps_important_technical_terms():
    processor = TaskProcessor()
    summary = """會議名稱：技術整合會議
會議時間：中華民國113年3月1日 09時00分至10時30分
會議地點：本部第2會議室
主  席：王主任○○
出席人員：資訊室、業務組
列席人員：無
記  錄：AI 會議助理

二、 討論事項：
案由：關於 OAuth2、JWT 與 GitHub Actions 上線事宜，提請 審議。
說明：
1. 相關技術已完成初步驗證。
決議：
1. 相關技術納入上線範圍，Okay。"""

    sanitized = processor._sanitize_text_language(summary)

    assert "OAuth2" in sanitized
    assert "JWT" in sanitized
    assert "GitHub Actions" in sanitized
    assert "Okay" not in sanitized
    assert "好" in sanitized


def test_excessive_english_detection_is_not_triggered_by_mixed_technical_summary():
    processor = TaskProcessor()
    summary = """會議名稱：技術整合會議
會議時間：中華民國113年3月1日 09時00分至10時30分
會議地點：本部第2會議室
主  席：王主任○○
出席人員：資訊室、業務組
列席人員：無
記  錄：AI 會議助理

二、 討論事項：
案由：關於 API 串接、OAuth2 驗證、GitHub Actions 部署與 AWS 資源調整，提請 審議。
說明：
1. 相關規劃已進入測試階段。
決議：
1. 整體仍以中文敘述為主，並確認月底前完成上線。"""

    assert processor._has_excessive_english(summary) is False


def test_format_result_normalizes_common_local_output_artifacts(monkeypatch):
    processor = TaskProcessor()
    task = TaskInfo(
        task_id="task1234",
        filename="meeting.mp3",
        original_filename="測試會議.mp3",
        file_size=1024,
        processing_mode=ProcessingMode.LOCAL,
    )
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

    monkeypatch.setattr(task_processor_module.device_detector, "current_device", "cpu")
    monkeypatch.setattr(
        task_processor_module.device_detector,
        "get_device_info",
        lambda: {"current_device": "cpu", "gpu_available": False, "mps_available": False},
    )

    result = processor._format_result(task, "逐字稿內容", summary)

    assert "$\\rightarrow$" not in result
    assert "Stand by" not in result
    assert "→" in result
    assert "待命" in result
