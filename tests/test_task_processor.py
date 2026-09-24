#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TaskProcessor 與記錄級後處理（text_postprocess）測試。

v4.2 起記錄級清理移至 backend.core.text_postprocess（P1-9，於驗證前執行），
本檔同步改測新模組；TaskProcessor 僅測「包裝輸出」行為（含 P0-5 失敗顯性化）。
"""

import importlib
from unittest.mock import AsyncMock

import pytest

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


def test_format_result_shows_reason_even_without_error_message(monkeypatch):
    """v4.6.2：空訊息例外（如 httpx.ReadTimeout）不得讓「失敗原因」行整個消失。"""
    processor = TaskProcessor()
    _patch_device(monkeypatch)

    result = processor._format_result(_make_task(), "逐字稿內容", None, summary_error=None)

    assert "失敗原因：未知錯誤（無例外訊息）" in result


def test_format_result_shows_exception_class_reason(monkeypatch):
    """v4.6.2：describe_exception 產生的「類別: 訊息」需完整進入文件。"""
    processor = TaskProcessor()
    _patch_device(monkeypatch)

    result = processor._format_result(
        _make_task(), "逐字稿內容", None, summary_error="ReadTimeout: ReadTimeout('')"
    )

    assert "失敗原因：ReadTimeout" in result


@pytest.mark.asyncio
async def test_process_task_warms_up_before_correction_and_reports_timeout(monkeypatch):
    """v4.6.2：warmup 須在逐字稿之後、校正之前；摘要逾時（空訊息）仍要完成任務
    並在輸出中標示例外類別、設定 summary_failed。"""
    import httpx

    processor = TaskProcessor()
    _patch_device(monkeypatch)
    task = _make_task()
    calls: list[str] = []
    saved: dict[str, str] = {}

    monkeypatch.setattr(task_processor_module.os.path, "exists", lambda _p: True)
    monkeypatch.setattr(processor, "_update_progress", AsyncMock())

    async def fake_obtain(_task, _path):
        calls.append("transcript")
        return "不可變ASR原文"

    async def fake_warmup():
        calls.append("warmup")

    async def fake_correction(_task, transcript):
        calls.append("correction")
        assert transcript == "不可變ASR原文"
        return "校正後理解文字", None

    observed_summary: dict = {}
    async def fake_summarize(*args, **kwargs):
        calls.append("summarize")
        observed_summary["transcript"] = args[0]
        observed_summary.update(kwargs)
        raise httpx.ReadTimeout("")

    async def fake_save_result(_task_id, _filename, content):
        saved["content"] = content

    monkeypatch.setattr(processor, "_obtain_transcript", fake_obtain)
    monkeypatch.setattr(processor, "_apply_semantic_correction", fake_correction)
    monkeypatch.setattr(
        task_processor_module.summarization_service, "warmup_local_model", fake_warmup
    )
    monkeypatch.setattr(
        task_processor_module.summarization_service, "summarize", fake_summarize
    )
    monkeypatch.setattr(
        task_processor_module.file_manager, "save_transcript_result", AsyncMock()
    )
    monkeypatch.setattr(task_processor_module.file_manager, "save_result", fake_save_result)
    monkeypatch.setattr(task_processor_module.task_queue, "complete_task", AsyncMock())

    await processor._process_task(task)

    assert calls == ["transcript", "warmup", "correction", "summarize"]
    assert observed_summary["transcript"] == "校正後理解文字"
    assert observed_summary["raw_source_transcript"] == "不可變ASR原文"
    assert task.summary_failed is True
    assert "失敗原因：ReadTimeout" in saved["content"]
    assert "會議紀錄生成失敗" in saved["content"]


def test_device_info_reports_gpu_present_even_when_busy(monkeypatch):
    """v4.3.2：VRAM 被占滿（current_device 暫為 CPU）時，GPU 仍應回報存在。

    T20260912-2242-01：Mac auto 預設改走 apple（顯示 apple-neural 且 gpu_busy
    固定 False）；本測試描述的是 CUDA 情境，改以顯式非 apple 後端固定，
    避免斷言取決於執行主機平台。
    """
    from backend.services.device_detector import DeviceDetector, DeviceType
    from backend.core.config import settings

    # 明確把主機釘在非 Apple 平台：顯式 legacy backend 在 macOS 已被硬性拒絕
    # （T20260912-2242-01），本測試描述的是 CUDA 情境。
    monkeypatch.setattr("backend.core.asr_model_resolver.is_darwin_arm64", lambda: False)
    monkeypatch.setattr("backend.core.platform_config.is_darwin_arm64", lambda: False)
    monkeypatch.setattr(settings, "ASR_BACKEND", "transformers")

    detector = DeviceDetector()
    detector.gpu_present = True
    detector.gpu_name = "NVIDIA GeForce RTX 4090"
    detector.current_device = DeviceType.CPU  # 忙碌時被排到 CPU

    info = detector.get_device_info()

    assert info["gpu_available"] is True   # 存在（顯示用）
    assert info["gpu_busy"] is True        # 但目前忙碌
    assert info["gpu_name"] == "NVIDIA GeForce RTX 4090"


def test_websocket_status_labels_are_chinese():
    """v4.3.2：推送給使用者的狀態不得是英文 enum 值。"""
    from backend.api.websocket import status_label
    from backend.models.schemas import TaskStatus

    for status in TaskStatus:
        label = status_label(status)
        assert label
        assert not label.isascii(), f"{status} 的標籤仍是英文: {label}"
