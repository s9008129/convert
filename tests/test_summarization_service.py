#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
SummarizationService 測試。

涵蓋：
1. Ollama 模型解析
2. 本地 8192 context 規劃 / chunking
3. 萃取筆記與最終摘要的驗證回圈
"""

from unittest.mock import AsyncMock, Mock

import pytest

from backend.core.config import settings
from backend.services.summarization import LocalContextPlan, SummarizationService


def _build_tags_response(models: list[str]) -> Mock:
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "models": [{"name": model_name} for model_name in models]
    }
    return response


def _notes_with_two_actions() -> str:
    return """# 萃取筆記

## 1. 會議資訊
- **日期**：113年3月1日
- **參與者**：王主任、陳科長
- **會議主題**：專案進度追蹤

## 2. 議題與決議
- **議題**：專案里程碑
  - *討論重點*：確認測試與上線時程
  - *決議*：維持月底上線

## 3. 待辦清單
| 待辦事項 | 負責人 | 期限 | 依據 |
| :--- | :--- | :--- | :--- |
| 完成整合測試 | 王主任 | 下週三 | 主席要求 |
| 提交上線公告草案 | 陳科長 | 本週五 | 會中交辦 |

## 4. 待確認資訊
- 無"""


def _complete_summary() -> str:
    return """會議名稱：113年度第1次專案進度追蹤會議
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


def test_resolve_compatible_model_prefers_gemma4_q4_variant_for_same_base_model():
    service = SummarizationService()

    resolved = service._resolve_compatible_model(
        "gemma4:31b",
        ["gemma4:31b-it-q4_K_M", "mistral-small3.2:latest"]
    )

    assert resolved == "gemma4:31b-it-q4_K_M"


def test_resolve_compatible_model_prefers_same_family_latest():
    service = SummarizationService()

    resolved = service._resolve_compatible_model(
        "gemma4:31b",
        ["gemma4:latest", "mistral-small3.2:latest"]
    )

    assert resolved == "gemma4:latest"


@pytest.mark.asyncio
async def test_check_ollama_health_uses_resolved_model(monkeypatch):
    service = SummarizationService()
    fake_client = Mock()
    fake_client.get = AsyncMock(
        return_value=_build_tags_response(["gemma4:31b-it-q4_K_M", "mistral-small3.2:latest"])
    )

    monkeypatch.setattr(settings, "LOCAL_LLM_MODEL", "gemma4:31b")
    monkeypatch.setattr(service, "_get_ollama_client", AsyncMock(return_value=fake_client))

    healthy = await service.check_ollama_health()

    assert healthy is True
    assert service._get_effective_model() == "gemma4:31b-it-q4_K_M"
    assert service._ollama_model_error is None


@pytest.mark.asyncio
async def test_check_ollama_health_reports_clear_model_error(monkeypatch):
    service = SummarizationService()
    fake_client = Mock()
    fake_client.get = AsyncMock(
        return_value=_build_tags_response(["mistral-small3.2:latest"])
    )

    monkeypatch.setattr(settings, "LOCAL_LLM_MODEL", "gemma4:31b")
    monkeypatch.setattr(service, "_get_ollama_client", AsyncMock(return_value=fake_client))

    healthy = await service.check_ollama_health()

    assert healthy is False
    assert service._resolved_model is None
    assert service._ollama_model_error is not None
    assert "gemma4:31b" in service._ollama_model_error
    assert "mistral-small3.2:latest" in service._ollama_model_error
    assert "ollama pull gemma4:31b" in service._ollama_model_error


@pytest.mark.asyncio
async def test_summarize_with_local_llm_surfaces_model_resolution_error(monkeypatch):
    service = SummarizationService()
    service._ollama_model_error = "設定的 Ollama 模型不存在。"

    monkeypatch.setattr(service, "check_ollama_health", AsyncMock(return_value=False))
    monkeypatch.setattr(service, "check_lmstudio_health", AsyncMock(return_value=False))

    with pytest.raises(RuntimeError, match="設定的 Ollama 模型不存在"):
        await service._summarize_with_local_llm("system", "user")


def test_build_local_context_plan_assumes_effective_8192_window(monkeypatch):
    service = SummarizationService()
    transcript = "王主任：請在下週前完成測試。\n" * 600

    monkeypatch.setattr(settings, "LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS", 8192)
    monkeypatch.setattr(settings, "LOCAL_LLM_RESERVED_OUTPUT_TOKENS", 3072)

    plan = service._build_local_context_plan(transcript, settings.DEFAULT_SYSTEM_PROMPT)

    assert isinstance(plan, LocalContextPlan)
    assert plan.context_window_tokens == 8192
    assert plan.chunk_input_budget_tokens < plan.context_window_tokens
    assert plan.needs_chunking is True
    assert plan.estimated_chunk_count >= 2


def test_split_transcript_into_chunks_keeps_overlap(monkeypatch):
    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_LLM_CHUNK_OVERLAP_LINES", 2)

    transcript = "\n".join(
        [
            "甲：今天先確認專案時程。",
            "乙：請王主任整理測試清單。",
            "丙：請陳科長準備上線公告。",
            "丁：下週三前要完成整合測試。",
            "戊：本週五前送出公告草案。",
            "己：月底前正式上線。",
        ]
    )

    chunks = service._split_transcript_into_chunks(transcript, max_input_tokens=25)

    assert len(chunks) >= 2
    assert "乙：請王主任整理測試清單。" in chunks[0]
    assert "乙：請王主任整理測試清單。" in chunks[1], "第二塊應保留前一塊的重疊行"
    assert all(service._estimate_tokens(chunk) <= 35 for chunk in chunks)


def test_validate_summary_quality_flags_missing_sections_and_actions():
    service = SummarizationService()
    incomplete_summary = """會議名稱：113年度第1次專案進度追蹤會議
會議時間：中華民國113年3月1日 09時00分至10時30分
會議地點：本部第2會議室
主  席：王主任○○
出席人員：王主任、陳科長
列席人員：資訊室林專員
記  錄：AI 會議助理

一、 報告事項：
1. 專案整體進度維持如期。"""

    issues = service._validate_summary_quality(incomplete_summary, _notes_with_two_actions())

    assert any("缺少區塊" in issue for issue in issues)
    assert any("缺少主辦單位資訊" in issue for issue in issues)
    assert any("待辦事項遺漏" in issue for issue in issues)


def test_validate_summary_quality_accepts_complete_summary():
    service = SummarizationService()

    issues = service._validate_summary_quality(_complete_summary(), _notes_with_two_actions())

    assert issues == []


def test_clean_ollama_output_removes_gemma4_thought_block():
    service = SummarizationService()
    raw_output = """<think>
先想一下格式
</think>

會議名稱：113年度第1次專案進度追蹤會議
會議時間：中華民國113年3月1日 09時00分至10時30分
"""

    cleaned = service._clean_ollama_output(raw_output)

    assert "<think>" not in cleaned
    assert cleaned.startswith("會議名稱：")


def test_clean_ollama_output_strips_english_preamble_before_record():
    """正式格式以「會議名稱：」開頭（非 #），英文分析前言必須被裁掉。"""
    service = SummarizationService()
    raw_output = """Analysis of the Transcript: Meeting Name: Not explicitly stated, but the content revolves around a project review. Let's infer a name.

Evaluation Criteria: Legal Compliance, Responsibility Clarity.

會議名稱：113年度第1次專案進度追蹤會議
會議時間：中華民國113年3月1日 09時00分至10時30分"""

    cleaned = service._clean_ollama_output(raw_output)

    assert cleaned.startswith("會議名稱：")
    assert "Analysis of the Transcript" not in cleaned
    assert "Evaluation Criteria" not in cleaned
    assert "Let's infer" not in cleaned


def test_validate_summary_quality_flags_english_and_rubric_leakage():
    service = SummarizationService()
    leaked = _complete_summary() + (
        "\n\nEvaluation Criteria: Legal Compliance: Full-width punctuation, government tone."
    )

    issues = service._validate_summary_quality(leaked, _notes_with_two_actions())

    assert any("英文前言" in issue or "評估標準" in issue for issue in issues)


def test_validate_summary_quality_does_not_flag_clean_summary_with_tech_terms():
    """合法的英文技術名詞（OAuth2、GitHub Actions）不應被誤判為英文洩漏。"""
    service = SummarizationService()
    summary = _complete_summary().replace(
        "1. 專案已完成整合測試。",
        "1. 專案已完成 OAuth2 與 GitHub Actions 整合測試。",
    )

    issues = service._validate_summary_quality(summary, _notes_with_two_actions())

    assert all("英文" not in issue and "評估標準" not in issue for issue in issues)


def test_validate_summary_quality_flags_simplified_and_non_markdown_leakage():
    service = SummarizationService()
    leaked_summary = """<think>推理中</think>

會議名稱：113年度第1次專案進度追蹤會議
會議時間：中華民國113年3月1日 09時00分至10時30分
會議地點：本部第2會議室
備註：会议记录这项进度已录入（含簡體漂移）
"""

    issues = service._validate_summary_quality(leaked_summary, _notes_with_two_actions())

    assert "出現簡體中文漂移" in issues
    assert "包含思考標籤或非 Markdown 洩漏內容" in issues


@pytest.mark.asyncio
async def test_local_pipeline_chunks_merges_and_refines(monkeypatch):
    service = SummarizationService()
    transcript = "逐字稿很長，需要分段處理"

    plan = LocalContextPlan(
        context_window_tokens=8192,
        estimated_transcript_tokens=6000,
        chunk_input_budget_tokens=1200,
        notes_merge_budget_tokens=1500,
        needs_chunking=True,
        estimated_chunk_count=2,
    )

    chunk_notes_1 = """# 萃取筆記
## 1. 會議資訊
- **日期**：113年3月1日
## 2. 議題與決議
- **議題**：測試安排
  - *討論重點*：安排整合測試
  - *決議*：下週三前完成
## 3. 待辦清單
| 待辦事項 | 負責人 | 期限 | 依據 |
| :--- | :--- | :--- | :--- |
| 完成整合測試 | 王主任 | 下週三 | 主席要求 |
## 4. 待確認資訊
- 無"""
    chunk_notes_2 = """# 萃取筆記
## 1. 會議資訊
- **日期**：113年3月1日
## 2. 議題與決議
- **議題**：公告準備
  - *討論重點*：準備上線公告
  - *決議*：本週五前提交草案
## 3. 待辦清單
| 待辦事項 | 負責人 | 期限 | 依據 |
| :--- | :--- | :--- | :--- |
| 提交上線公告草案 | 陳科長 | 本週五 | 會中交辦 |
## 4. 待確認資訊
- 無"""
    merged_notes = _notes_with_two_actions()
    incomplete_summary = """# 會議記錄摘要

## 1. 會議概況
- **日期**：113年3月1日

## 2. 執行摘要 (Executive Summary)
已確認上線時程。"""
    refined_summary = _complete_summary()

    responses = iter([chunk_notes_1, chunk_notes_2, merged_notes, incomplete_summary, refined_summary])

    monkeypatch.setattr(service, "_select_local_engine", AsyncMock(return_value="ollama"))
    monkeypatch.setattr(service, "_build_local_context_plan", Mock(return_value=plan))
    monkeypatch.setattr(service, "_split_transcript_into_chunks", Mock(return_value=["chunk-1", "chunk-2"]))
    generator = AsyncMock(side_effect=lambda *args, **kwargs: next(responses))
    monkeypatch.setattr(service, "_generate_with_local_engine", generator)

    summary = await service._summarize_with_local_pipeline(transcript, settings.DEFAULT_SYSTEM_PROMPT)

    assert summary.startswith("會議名稱：")
    assert "三、 主席裁示事項（後續管考與追蹤）：" in summary
    assert generator.await_count == 5
    assert "問題清單" in generator.await_args_list[-1].args[2]
