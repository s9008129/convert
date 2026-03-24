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
    return """# 會議記錄摘要

## 1. 會議概況
- **日期**：113年3月1日
- **參與者**：王主任、陳科長
- **會議主題**：專案進度追蹤

## 2. 執行摘要 (Executive Summary)
本次會議確認專案整體進度仍維持月底上線，重點聚焦於整合測試與公告準備，並明確交辦兩項後續工作。

## 3. 詳細議題與決議 (Discussion & Decisions)
- **議題 1**：專案里程碑
  - *討論重點*：確認測試與上線時程，檢視是否有延後風險。
  - *最終決議*：維持月底上線，並依既定時程完成測試與公告準備。

## 4. 待辦事項 (Action Items) - 必填
| 待辦事項 | 負責人 | 期限 |
| :--- | :--- | :--- |
| 完成整合測試 | 王主任 | 下週三 |
| 提交上線公告草案 | 陳科長 | 本週五 |

## 5. 其他備註
- 無"""


def test_resolve_compatible_model_legacy_alias_to_standard_model():
    service = SummarizationService()

    resolved = service._resolve_compatible_model(
        "gemma3:27b-it-qat",
        ["gemma3:27b", "mistral-small3.2:latest"]
    )

    assert resolved == "gemma3:27b"


def test_resolve_compatible_model_prefers_same_family_latest():
    service = SummarizationService()

    resolved = service._resolve_compatible_model(
        "gemma3:27b-it-qat",
        ["gemma3:latest", "mistral-small3.2:latest"]
    )

    assert resolved == "gemma3:latest"


@pytest.mark.asyncio
async def test_check_ollama_health_uses_resolved_model(monkeypatch):
    service = SummarizationService()
    fake_client = Mock()
    fake_client.get = AsyncMock(
        return_value=_build_tags_response(["gemma3:27b", "mistral-small3.2:latest"])
    )

    monkeypatch.setattr(settings, "LOCAL_LLM_MODEL", "gemma3:27b-it-qat")
    monkeypatch.setattr(service, "_get_ollama_client", AsyncMock(return_value=fake_client))

    healthy = await service.check_ollama_health()

    assert healthy is True
    assert service._get_effective_model() == "gemma3:27b"
    assert service._ollama_model_error is None


@pytest.mark.asyncio
async def test_check_ollama_health_reports_clear_model_error(monkeypatch):
    service = SummarizationService()
    fake_client = Mock()
    fake_client.get = AsyncMock(
        return_value=_build_tags_response(["mistral-small3.2:latest"])
    )

    monkeypatch.setattr(settings, "LOCAL_LLM_MODEL", "gemma3:27b-it-qat")
    monkeypatch.setattr(service, "_get_ollama_client", AsyncMock(return_value=fake_client))

    healthy = await service.check_ollama_health()

    assert healthy is False
    assert service._resolved_model is None
    assert service._ollama_model_error is not None
    assert "gemma3:27b-it-qat" in service._ollama_model_error
    assert "mistral-small3.2:latest" in service._ollama_model_error
    assert "ollama pull gemma3:27b" in service._ollama_model_error


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
    monkeypatch.setattr(settings, "LOCAL_LLM_RESERVED_OUTPUT_TOKENS", 2200)

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
    incomplete_summary = """# 會議記錄摘要

## 1. 會議概況
- **日期**：113年3月1日

## 2. 執行摘要 (Executive Summary)
會議確認月底上線。"""

    issues = service._validate_summary_quality(incomplete_summary, _notes_with_two_actions())

    assert any("缺少區塊" in issue for issue in issues)
    assert any("缺少待辦事項表格" in issue for issue in issues)
    assert any("待辦事項遺漏" in issue for issue in issues)


def test_validate_summary_quality_accepts_complete_summary():
    service = SummarizationService()

    issues = service._validate_summary_quality(_complete_summary(), _notes_with_two_actions())

    assert issues == []


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

    assert summary.startswith("# 會議記錄摘要")
    assert "## 4. 待辦事項 (Action Items) - 必填" in summary
    assert generator.await_count == 5
    assert "問題清單" in generator.await_args_list[-1].args[2]
