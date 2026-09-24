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
from backend.core.templates import get_template
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
    monkeypatch.setattr(settings, "LOCAL_LLM_PROVIDER", "ollama")
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
    monkeypatch.setattr(settings, "LOCAL_LLM_PROVIDER", "ollama")
    monkeypatch.setattr(service, "_get_ollama_client", AsyncMock(return_value=fake_client))

    healthy = await service.check_ollama_health()

    assert healthy is False
    assert service._resolved_model is None
    assert service._ollama_model_error is not None
    assert "gemma4:31b" in service._ollama_model_error
    assert "mistral-small3.2:latest" in service._ollama_model_error
    assert "ollama pull gemma4:31b" in service._ollama_model_error


@pytest.mark.asyncio
async def test_generate_local_surfaces_model_resolution_error(monkeypatch):
    service = SummarizationService()
    service._ollama_model_error = "設定的 Ollama 模型不存在。"

    monkeypatch.setattr(settings, "LOCAL_LLM_PROVIDER", "ollama")
    monkeypatch.setattr(service, "check_ollama_health", AsyncMock(return_value=False))
    monkeypatch.setattr(service, "check_lmstudio_health", AsyncMock(return_value=False))

    with pytest.raises(RuntimeError, match="設定的 Ollama 模型不存在"):
        await service.generate_local("system", "user")


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
            "[00:00:02] 乙：方案甲使管線乙外露。",
            "丙：請陳科長準備上線公告。",
            "丁：下週三前要完成整合測試。",
            "戊：本週五前送出公告草案。",
            "己：月底前正式上線。",
        ]
    )

    chunks = service._split_transcript_into_chunks(transcript, max_input_tokens=25)

    assert len(chunks) >= 2
    anchored_relation = "[00:00:02] 乙：方案甲使管線乙外露。"
    assert anchored_relation in chunks[0]
    assert anchored_relation in chunks[1], "重疊塊應保留原因→結果方向與來源錨點"
    assert all(service._estimate_tokens(chunk) <= 35 for chunk in chunks)

    source_evidence_chunks = service._deduplicate_chunk_source_overlaps(chunks, overlap_line_limit=2)
    source_evidence = "\n".join(source_evidence_chunks)
    assert source_evidence.count(anchored_relation) == 1
    assert "方案甲使管線乙外露" in source_evidence
    assert "管線乙使方案甲外露" not in source_evidence


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
        merge_input_budget_tokens=1500,
        merge_visible_target_tokens=900,
        merge_provider_output_tokens=3072,
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


# ---------------------------------------------------------------------------
# v4.3.3 雲端管線：分段萃取＋雙輸入生成＋動態豐富度閘門
# ---------------------------------------------------------------------------


def test_validate_summary_quality_dynamic_min_chars():
    service = SummarizationService()

    # 預設下限 250：完整摘要應通過
    assert service._validate_summary_quality(_complete_summary(), _notes_with_two_actions()) == []

    # 動態下限拉高後，同一份摘要應被標記為過短
    issues = service._validate_summary_quality(
        _complete_summary(), _notes_with_two_actions(), min_chars=5000
    )
    assert any("摘要內容過短" in issue for issue in issues)


def test_estimate_cloud_min_summary_chars_scales_with_transcript():
    service = SummarizationService()

    # 短逐字稿維持防空底線 250
    assert service._estimate_cloud_min_summary_chars("測試逐字稿") == 250

    # 103 分鐘量級（約 1.8 萬 tokens）下限應落在可攔截 8 百字過薄輸出的區間
    medium = "字" * 18000
    assert 1000 <= service._estimate_cloud_min_summary_chars(medium) <= 1300

    # 超長逐字稿封頂 2000，避免不合理的灌水要求
    assert service._estimate_cloud_min_summary_chars("字" * 60000) == 2000


@pytest.mark.asyncio
async def test_cloud_pipeline_chunked_extraction_and_transcript_in_generation(monkeypatch):
    """回退路徑：CLOUD_LLM_SEGMENTED_EXTRACTION=true 時分段萃取；生成仍須雙輸入。"""
    service = SummarizationService()
    # 逐字稿需含年份：測試資料的紀錄寫「113年」，日期依據絆索要求逐字稿有同樣的年份
    transcript = "主席：今天是113年3月1日，討論專案里程碑。科長：建議維持月底上線。"
    monkeypatch.setattr(settings, "CLOUD_LLM_SEGMENTED_EXTRACTION", True)

    chunk_notes_1 = _notes_with_two_actions()
    chunk_notes_2 = _notes_with_two_actions()
    responses = iter([chunk_notes_1, chunk_notes_2, _complete_summary()])

    monkeypatch.setattr(
        service, "_split_transcript_into_chunks", Mock(return_value=["chunk-1", "chunk-2"])
    )
    # 讓分段依序處理，side_effect 順序才可預期
    monkeypatch.setattr(settings, "CLOUD_LLM_MAX_CONCURRENT_REQUESTS", 1)
    gemini = AsyncMock(side_effect=lambda *args, **kwargs: next(responses))
    monkeypatch.setattr(service, "_gemini_chat", gemini)

    summary = await service._summarize_with_gemini(settings.DEFAULT_SYSTEM_PROMPT, transcript)

    assert summary.startswith("會議名稱：")
    assert gemini.await_count == 3

    # 萃取階段：每段各一次呼叫，且使用雲端豐富度提示詞
    extraction_prompts = [call.args[0] for call in gemini.await_args_list[:2]]
    assert all("豐富度" in prompt for prompt in extraction_prompts)

    # 生成階段：筆記＋逐字稿雙輸入
    generation_message = gemini.await_args_list[-1].args[1]
    assert "萃取筆記：" in generation_message
    assert "原始逐字稿：" in generation_message
    assert transcript in generation_message


@pytest.mark.asyncio
async def test_cloud_pipeline_single_pass_extraction_by_default(monkeypatch):
    """v4.7.3：雲端預設不分段——整份逐字稿一次萃取，切塊函式不得被呼叫。"""
    service = SummarizationService()
    transcript = "主席：今天是113年3月1日，討論專案里程碑。科長：建議維持月底上線。"
    monkeypatch.setattr(settings, "CLOUD_LLM_SEGMENTED_EXTRACTION", False)

    chunk_splitter = Mock(side_effect=AssertionError("雲端預設不得呼叫切塊"))
    monkeypatch.setattr(service, "_split_transcript_into_chunks", chunk_splitter)

    responses = iter([_notes_with_two_actions(), _complete_summary()])
    gemini = AsyncMock(side_effect=lambda *args, **kwargs: next(responses))
    monkeypatch.setattr(service, "_gemini_chat", gemini)

    summary = await service._summarize_with_gemini(settings.DEFAULT_SYSTEM_PROMPT, transcript)

    assert summary.startswith("會議名稱：")
    # 萃取 1 次＋最終生成 1 次（品質無問題，不進補強輪）
    assert gemini.await_count == 2
    assert chunk_splitter.call_count == 0

    # 單次萃取必須看到整份逐字稿，且仍使用雲端豐富度提示詞
    extraction_prompt, extraction_message = gemini.await_args_list[0].args[:2]
    assert "豐富度" in extraction_prompt
    assert transcript in extraction_message

    # 生成階段：筆記＋逐字稿雙輸入不變
    generation_message = gemini.await_args_list[-1].args[1]
    assert "萃取筆記：" in generation_message
    assert "原始逐字稿：" in generation_message


@pytest.mark.asyncio
async def test_cloud_pipeline_refines_when_summary_below_dynamic_floor(monkeypatch):
    """長會議的過薄輸出必須觸發補強輪，且補強訊息附上原始逐字稿。"""
    service = SummarizationService()
    # 約 2 萬 tokens 的長逐字稿 → 動態下限約 1,360 字（20400 // 15，未達 2000 上限）
    transcript = "與會人員針對113年訪談流程、效益口徑與展示方式進行詳細討論。" * 800

    thin_summary = _complete_summary()  # 結構完整但僅約 7 百字 → 低於動態下限
    rich_summary = _complete_summary().replace(
        "說明：",
        "說明：\n" + ("本案歷次會議已就訪談流程、效益口徑與展示方式充分交換意見。\n" * 60),
    )

    responses = iter([_notes_with_two_actions(), thin_summary, rich_summary])

    monkeypatch.setattr(
        service, "_split_transcript_into_chunks", Mock(return_value=["single-chunk"])
    )
    gemini = AsyncMock(side_effect=lambda *args, **kwargs: next(responses))
    monkeypatch.setattr(service, "_gemini_chat", gemini)

    summary = await service._summarize_with_gemini(settings.DEFAULT_SYSTEM_PROMPT, transcript)

    assert gemini.await_count == 3
    refinement_message = gemini.await_args_list[-1].args[1]
    assert "問題清單" in refinement_message
    assert "摘要內容過短" in refinement_message
    assert "原始逐字稿（補充細節時以此為準）" in refinement_message
    assert len(summary) > len(thin_summary)


# ========================================
# v4.6.2/v4.7.0：串流生成、瞬時錯誤重試、模型預熱自我修復、雲端串流重試
# ========================================


class _FakeStreamResponse:
    """模擬 httpx client.stream 的回應（NDJSON lines）。"""

    def __init__(self, lines: list[str], status_code: int = 200):
        self.status_code = status_code
        self._lines = lines

    async def aiter_lines(self):
        for line in self._lines:
            if isinstance(line, Exception):
                raise line
            yield line

    async def aread(self):
        return b""

    def raise_for_status(self):
        if self.status_code >= 400:
            import httpx

            response = Mock()
            response.status_code = self.status_code
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}", request=Mock(), response=response
            )


class _FakeStreamContext:
    def __init__(self, response: _FakeStreamResponse):
        self._response = response

    async def __aenter__(self):
        return self._response

    async def __aexit__(self, *args):
        return False


def _stream_client(lines: list, status_code: int = 200) -> Mock:
    client = Mock()
    client.stream = Mock(return_value=_FakeStreamContext(_FakeStreamResponse(lines, status_code)))
    return client


def _done_chunk(**overrides) -> str:
    import json as _json

    chunk = {
        "done": True,
        "done_reason": "stop",
        "load_duration": int(2e9),
        "eval_count": 100,
        "eval_duration": int(5e9),
    }
    chunk.update(overrides)
    return _json.dumps(chunk)


def _content_chunk(text: str) -> str:
    import json as _json

    return _json.dumps({"message": {"content": text}, "done": False})


@pytest.mark.asyncio
async def test_stream_ollama_chat_once_accumulates_content():
    """happy path：串流內容累積＋done chunk 指標回傳。"""
    service = SummarizationService()
    client = _stream_client([_content_chunk("會議"), _content_chunk("紀錄"), _done_chunk()])

    content, final = await service._stream_ollama_chat_once(client, {"model": "m"})

    assert content == "會議紀錄"
    assert final["done_reason"] == "stop"
    assert final["eval_count"] == 100


@pytest.mark.asyncio
async def test_stream_ollama_chat_once_raises_on_error_chunk():
    """串流中途 error chunk（模型卸載／runner 崩潰）→ 可重試例外。"""
    from backend.services.summarization import OllamaStreamRetryable

    service = SummarizationService()
    client = _stream_client([_content_chunk("部分"), '{"error": "model unloaded"}'])

    with pytest.raises(OllamaStreamRetryable):
        await service._stream_ollama_chat_once(client, {"model": "m"})


@pytest.mark.asyncio
async def test_stream_ollama_chat_once_raises_when_no_done_chunk():
    """串流結束但沒有 done chunk（連線中斷）→ 可重試例外。"""
    from backend.services.summarization import OllamaStreamRetryable

    service = SummarizationService()
    client = _stream_client([_content_chunk("斷在一半")])

    with pytest.raises(OllamaStreamRetryable):
        await service._stream_ollama_chat_once(client, {"model": "m"})


@pytest.mark.asyncio
async def test_stream_ollama_chat_once_accepts_truncated_done_reason():
    """v4.7.1：done_reason=length（撞 num_predict 上限）是確定性結果，
    不得重試——單次呼叫即應回傳已累積的完整內容。"""
    service = SummarizationService()
    client = _stream_client([_content_chunk("截"), _content_chunk("斷"), _done_chunk(done_reason="length")])

    content, final = await service._stream_ollama_chat_once(client, {"model": "m"})

    assert content == "截斷"
    assert final["done_reason"] == "length"
    # 只建立/呼叫一次串流（沒有因為 length 而重試）
    client.stream.assert_called_once()


@pytest.mark.asyncio
async def test_stream_ollama_chat_once_raises_on_other_done_reason():
    """done_reason 為 length/stop/None 以外的其他值（如連線異常結束）仍應可重試。"""
    from backend.services.summarization import OllamaStreamRetryable

    service = SummarizationService()
    client = _stream_client([_content_chunk("異常"), _done_chunk(done_reason="unload")])

    with pytest.raises(OllamaStreamRetryable):
        await service._stream_ollama_chat_once(client, {"model": "m"})


@pytest.mark.asyncio
async def test_post_ollama_chat_accepts_truncated_content_without_retry(monkeypatch):
    """v4.7.1：done_reason=length 不重試，直接接受截斷內容並記錄警告。"""
    from loguru import logger

    monkeypatch.setattr(settings, "LOCAL_LLM_TRANSIENT_RETRIES", 2)

    service = SummarizationService()
    once = AsyncMock(
        return_value=("截斷但完整累積的內容", {"done_reason": "length", "eval_count": 2048})
    )
    monkeypatch.setattr(service, "_stream_ollama_chat_once", once)

    records: list[str] = []
    sink_id = logger.add(lambda message: records.append(str(message)), level="WARNING")
    try:
        content, final_chunk, send_think = await service._post_ollama_chat(
            Mock(), {"model": "m", "options": {"num_predict": 2048}}, False
        )
    finally:
        logger.remove(sink_id)

    assert content == "截斷但完整累積的內容"
    assert final_chunk["done_reason"] == "length"
    assert once.await_count == 1  # 不重試
    assert any("num_predict 上限" in record for record in records)


@pytest.mark.asyncio
async def test_post_ollama_chat_retries_transient_and_stream_failures(monkeypatch):
    """閒置逾時（ReadTimeout）與串流層失敗都應重試，而非毀掉整份紀錄。"""
    import httpx

    from backend.services.summarization import OllamaStreamRetryable

    monkeypatch.setattr(settings, "LOCAL_LLM_TRANSIENT_RETRIES", 2)
    monkeypatch.setattr(settings, "LOCAL_LLM_RETRY_BACKOFF_SECONDS", 0.0)

    service = SummarizationService()
    once = AsyncMock(
        side_effect=[httpx.ReadTimeout(""), OllamaStreamRetryable("斷線"), ("OK", {})]
    )
    monkeypatch.setattr(service, "_stream_ollama_chat_once", once)

    content, _metrics, send_think = await service._post_ollama_chat(Mock(), {"model": "m"}, False)

    assert content == "OK"
    assert send_think is False
    assert once.await_count == 3


@pytest.mark.asyncio
async def test_post_ollama_chat_gives_up_after_configured_retries(monkeypatch):
    import httpx

    monkeypatch.setattr(settings, "LOCAL_LLM_TRANSIENT_RETRIES", 2)
    monkeypatch.setattr(settings, "LOCAL_LLM_RETRY_BACKOFF_SECONDS", 0.0)

    service = SummarizationService()
    once = AsyncMock(side_effect=httpx.ReadTimeout(""))
    monkeypatch.setattr(service, "_stream_ollama_chat_once", once)

    with pytest.raises(httpx.ReadTimeout):
        await service._post_ollama_chat(Mock(), {"model": "m"}, False)

    assert once.await_count == 3


@pytest.mark.asyncio
async def test_post_ollama_chat_does_not_retry_non_transient_errors(monkeypatch):
    """非瞬時錯誤（如程式邏輯例外）不得重試，避免掩蓋真正 bug。"""
    monkeypatch.setattr(settings, "LOCAL_LLM_TRANSIENT_RETRIES", 2)

    service = SummarizationService()
    once = AsyncMock(side_effect=ValueError("boom"))
    monkeypatch.setattr(service, "_stream_ollama_chat_once", once)

    with pytest.raises(ValueError):
        await service._post_ollama_chat(Mock(), {"model": "m"}, False)

    assert once.await_count == 1


@pytest.mark.asyncio
async def test_post_ollama_chat_adds_think_field_and_downgrades_on_400(monkeypatch):
    """think 相容降級語意須保留：400 時改以不帶 think 欄位重送。"""
    import httpx

    monkeypatch.setattr(settings, "LOCAL_LLM_TRANSIENT_RETRIES", 0)

    service = SummarizationService()
    bodies: list[dict] = []

    async def fake_once(_client, body):
        bodies.append(body)
        if body.get("think") is False:
            response = Mock()
            response.status_code = 400
            raise httpx.HTTPStatusError("400", request=Mock(), response=response)
        return "OK", {}

    monkeypatch.setattr(service, "_stream_ollama_chat_once", fake_once)

    content, _metrics, send_think = await service._post_ollama_chat(Mock(), {"model": "m"}, True)

    assert content == "OK"
    assert send_think is False
    assert bodies[0].get("think") is False
    assert "think" not in bodies[1]


@pytest.mark.asyncio
async def test_summarize_with_ollama_honors_context_override(monkeypatch):
    """v4.7.0：num_ctx 覆蓋值須貫穿到 payload（warmup 降級的落點）。"""
    service = SummarizationService()
    payloads: list[dict] = []

    async def fake_post(_client, payload, send_think_field):
        payloads.append(payload)
        return "會議紀錄本文", {}, send_think_field

    monkeypatch.setattr(service, "_get_ollama_client", AsyncMock(return_value=Mock()))
    monkeypatch.setattr(service, "_get_effective_model", Mock(return_value="gemma4:31b"))
    monkeypatch.setattr(service, "_post_ollama_chat", fake_post)

    await service._summarize_with_ollama("sys", "user", context_window_tokens=4096)
    assert payloads[-1]["options"]["num_ctx"] == 4096
    assert payloads[-1]["stream"] is True

    service._active_context_tokens = 8192
    await service._summarize_with_ollama("sys", "user")
    assert payloads[-1]["options"]["num_ctx"] == 8192


@pytest.mark.asyncio
async def test_summarize_with_ollama_expands_num_predict_to_context_headroom(monkeypatch):
    """v4.7.1：context 有餘裕時，num_predict 應自動擴大到超過預設保留值，
    從源頭降低撞 num_predict 上限（done_reason=length）的機率。"""
    monkeypatch.setattr(settings, "LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS", 16384)

    service = SummarizationService()
    payloads: list[dict] = []

    async def fake_post(_client, payload, send_think_field):
        payloads.append(payload)
        return "會議紀錄本文", {}, send_think_field

    monkeypatch.setattr(service, "_get_ollama_client", AsyncMock(return_value=Mock()))
    monkeypatch.setattr(service, "_get_effective_model", Mock(return_value="gemma4:31b"))
    monkeypatch.setattr(service, "_post_ollama_chat", fake_post)

    system_prompt = "sys"
    user_message = "user"
    await service._summarize_with_ollama(system_prompt, user_message)

    est_prompt = service._estimate_tokens(system_prompt) + service._estimate_tokens(user_message) + 64
    expected_num_predict = 16384 - est_prompt - 256

    assert payloads[-1]["options"]["num_predict"] == expected_num_predict
    assert expected_num_predict > settings.LOCAL_LLM_RESERVED_OUTPUT_TOKENS


@pytest.mark.asyncio
async def test_summarize_with_ollama_expand_output_budget_false_keeps_caller_value(monkeypatch):
    """v4.7.1：expand_output_budget=False（整併呼叫）時，num_predict 必須
    維持呼叫端指定值，不得自動擴大——否則會破壞整併「必縮小」的收斂保證。"""
    monkeypatch.setattr(settings, "LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS", 16384)

    service = SummarizationService()
    payloads: list[dict] = []

    async def fake_post(_client, payload, send_think_field):
        payloads.append(payload)
        return "整併後筆記", {}, send_think_field

    monkeypatch.setattr(service, "_get_ollama_client", AsyncMock(return_value=Mock()))
    monkeypatch.setattr(service, "_get_effective_model", Mock(return_value="gemma4:31b"))
    monkeypatch.setattr(service, "_post_ollama_chat", fake_post)

    caller_num_predict = 512
    await service._summarize_with_ollama(
        "sys", "user", num_predict=caller_num_predict, expand_output_budget=False
    )

    assert payloads[-1]["options"]["num_predict"] == caller_num_predict


def test_build_local_context_plan_context_override_shrinks_budgets():
    """降級 ctx 必須同步縮小 merge 預算，否則輸入會超出 num_ctx 被靜默截斷。"""
    service = SummarizationService()
    transcript = "測試逐字稿" * 2000

    default_plan = service._build_local_context_plan(
        transcript, settings.DEFAULT_SYSTEM_PROMPT, context_window_tokens=16384
    )
    degraded_plan = service._build_local_context_plan(
        transcript, settings.DEFAULT_SYSTEM_PROMPT, context_window_tokens=8192
    )

    assert degraded_plan.context_window_tokens == 8192
    # RC-1：merge 預算語意分離後，「降級 ctx 必須同步縮小 merge 預算」的契約
    # 落在 merge_input_budget_tokens（來源分組上限）；visible target 固定 900、
    # provider cap 來自 reserved output，兩者不隨 context 縮放。
    assert (
        degraded_plan.merge_input_budget_tokens
        < default_plan.merge_input_budget_tokens
    )


def _ps_response(size: int, size_vram: int) -> Mock:
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "models": [{"name": "gemma4:31b", "size": size, "size_vram": size_vram}]
    }
    return response


def _tags_response(disk_size: int) -> Mock:
    response = Mock()
    response.status_code = 200
    response.json.return_value = {"models": [{"name": "gemma4:31b", "size": disk_size}]}
    return response


def _warmup_service(monkeypatch, client: Mock) -> SummarizationService:
    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_LLM_PROVIDER", "ollama")
    monkeypatch.setattr(service, "check_ollama_health", AsyncMock(return_value=True))
    monkeypatch.setattr(service, "_get_ollama_client", AsyncMock(return_value=client))
    monkeypatch.setattr(service, "_get_effective_model", Mock(return_value="gemma4:31b"))
    monkeypatch.setattr(service, "release_local_model", AsyncMock())
    return service


@pytest.mark.asyncio
async def test_warmup_local_model_sends_load_only_request_with_num_ctx(monkeypatch):
    """預熱請求帶 model＋keep_alive＋options.num_ctx（不帶 prompt＝load-only）。

    num_ctx 必須與後續 chat 相同——runner 依 ctx 載入，不一致會觸發整顆重載。
    """
    generate_response = Mock()
    generate_response.status_code = 200
    generate_response.raise_for_status = Mock()

    client = Mock()
    client.post = AsyncMock(return_value=generate_response)
    client.get = AsyncMock(side_effect=[_ps_response(100, 100), _tags_response(90)])

    service = _warmup_service(monkeypatch, client)
    await service.warmup_local_model()

    assert client.post.await_args.args[0] == "/api/generate"
    payload = client.post.await_args.kwargs["json"]
    assert set(payload) == {"model", "keep_alive", "options"}
    assert payload["options"]["num_ctx"] == settings.LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS
    assert "prompt" not in payload
    assert service._active_context_tokens is None


@pytest.mark.asyncio
async def test_warmup_self_heal_recovers_without_degrade(monkeypatch):
    """offload → 卸載重載成功 → 不降級，且會清掉前一任務殘留的降級值。"""
    monkeypatch.setattr("asyncio.sleep", AsyncMock())

    generate_response = Mock()
    generate_response.status_code = 200
    generate_response.raise_for_status = Mock()

    client = Mock()
    client.post = AsyncMock(return_value=generate_response)
    client.get = AsyncMock(
        side_effect=[_ps_response(100, 60), _ps_response(100, 100), _tags_response(90)]
    )

    service = _warmup_service(monkeypatch, client)
    service._active_context_tokens = 8192  # 模擬前一任務殘留

    await service.warmup_local_model()

    service.release_local_model.assert_awaited_once()
    assert service._active_context_tokens is None


@pytest.mark.asyncio
async def test_warmup_self_heal_failure_degrades_context(monkeypatch):
    """自我修復後仍 offload → 本任務降級 num_ctx，並以降級 ctx 再載一次。"""
    from loguru import logger

    monkeypatch.setattr("asyncio.sleep", AsyncMock())
    monkeypatch.setattr(settings, "LOCAL_LLM_DEGRADED_CONTEXT_TOKENS", 8192)

    generate_response = Mock()
    generate_response.status_code = 200
    generate_response.raise_for_status = Mock()

    client = Mock()
    client.post = AsyncMock(return_value=generate_response)
    client.get = AsyncMock(
        side_effect=[
            _ps_response(100, 60),   # 第 1 次載入：offload
            _ps_response(100, 60),   # 自我修復重載：仍 offload
            _ps_response(80, 80),    # 降級 ctx 重載：全載
            _tags_response(70),
        ]
    )

    service = _warmup_service(monkeypatch, client)

    records: list[str] = []
    sink_id = logger.add(lambda message: records.append(str(message)), level="WARNING")
    try:
        await service.warmup_local_model()
    finally:
        logger.remove(sink_id)

    assert service._active_context_tokens == 8192
    assert any("降級 num_ctx" in record for record in records)
    # 第 3 次 /api/generate 應帶降級 ctx
    degraded_payload = client.post.await_args_list[-1].kwargs["json"]
    assert degraded_payload["options"]["num_ctx"] == 8192


def test_kv_quantization_heuristic_warns_on_f16_signature(monkeypatch):
    """overhead ≈ f16 特徵 → 警告主機 KV 量化可能未生效。"""
    from loguru import logger

    monkeypatch.setattr(settings, "LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS", 16384)
    service = SummarizationService()
    service._active_context_tokens = None

    records: list[str] = []
    sink_id = logger.add(lambda message: records.append(str(message)), level="WARNING")
    try:
        # 19.9GB 磁碟、23.5GB 載入 → overhead 3.6GB ＝ f16@16384 特徵（門檻 3.5GB）
        service._check_kv_quantization_heuristic(int(23.5e9), int(19.9e9))
    finally:
        logger.remove(sink_id)

    assert any("可能未生效" in record for record in records)


def test_kv_quantization_heuristic_accepts_q8_signature(monkeypatch):
    """overhead 約 f16 一半以下 → 判定量化已生效，不得誤報。"""
    from loguru import logger

    monkeypatch.setattr(settings, "LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS", 16384)
    service = SummarizationService()
    service._active_context_tokens = None

    records: list[str] = []
    sink_id = logger.add(lambda message: records.append(str(message)), level="WARNING")
    try:
        # 正式機實測值：22.6GB 載入、19.9GB 磁碟 → overhead 2.7GB ＝ q8 生效特徵
        service._check_kv_quantization_heuristic(int(22.6e9), int(19.9e9))
    finally:
        logger.remove(sink_id)

    assert not any("可能未生效" in record for record in records)


@pytest.mark.asyncio
async def test_warmup_local_model_never_raises(monkeypatch):
    """預熱只是把載入成本前移；任何失敗都不得中斷任務。"""
    service = SummarizationService()
    monkeypatch.setattr(
        service, "check_ollama_health", AsyncMock(side_effect=RuntimeError("down"))
    )

    await service.warmup_local_model()  # 不應拋出


@pytest.mark.asyncio
async def test_gemini_chat_retries_transient_stream_failure(monkeypatch):
    """雲端串流中途逾時應重試——最終生成與補強輪因此自動受保護。"""
    import httpx

    monkeypatch.setattr(settings, "CLOUD_LLM_MAX_RETRIES", 2)
    monkeypatch.setattr(settings, "LOCAL_LLM_RETRY_BACKOFF_SECONDS", 0.0)

    service = SummarizationService()
    once = AsyncMock(side_effect=[httpx.ReadTimeout(""), "會議紀錄本文"])
    monkeypatch.setattr(service, "_gemini_chat_once", once)

    summary = await service._gemini_chat("system", "user")

    assert summary == "會議紀錄本文"
    assert once.await_count == 2


@pytest.mark.asyncio
async def test_gemini_chat_does_not_retry_non_transient_errors(monkeypatch):
    monkeypatch.setattr(settings, "CLOUD_LLM_MAX_RETRIES", 2)

    service = SummarizationService()
    once = AsyncMock(side_effect=RuntimeError("摘要生成失敗：結果為空"))
    monkeypatch.setattr(service, "_gemini_chat_once", once)

    with pytest.raises(RuntimeError):
        await service._gemini_chat("system", "user")

    assert once.await_count == 1


def test_cloud_generation_message_requires_speaker_traceability():
    """開啟旗標的模板（科務會議）雲端生成／補強訊息必須帶發言來源標註規則。"""
    service = SummarizationService()
    template = get_template("section_meeting")
    notes = "## 1. 會議資訊\n- **主題**：組織規程調整\n"
    transcript = "[00:00:00-00:01:00] 發言者1：請各股配合辦理"

    cloud = service._build_cloud_summary_message(notes, transcript, template=template)
    cloud_refine = service._build_cloud_refinement_message(
        "草稿", notes, ["缺少區塊：X"], transcript, template=template
    )

    rule = SummarizationService.CLOUD_SPEAKER_TRACEABILITY_RULE
    assert rule in cloud
    assert rule in cloud_refine


def test_speaker_traceability_rule_is_template_gated():
    """旗標未開啟的模板（含 general）與地端生成訊息都不得被雲端規則影響。"""
    service = SummarizationService()
    notes = "## 1. 會議資訊\n- **主題**：組織規程調整\n"
    transcript = "[00:00:00-00:01:00] 發言者1：請各股配合辦理"
    rule = SummarizationService.CLOUD_SPEAKER_TRACEABILITY_RULE

    for template_id in ("general", "procurement_evaluation"):
        template = get_template(template_id)
        assert template.speaker_traceability is False
        assert rule not in service._build_cloud_summary_message(notes, transcript, template=template)
        assert service._validate_cloud_speaker_traceability("會議紀錄正文", template) == []

    local = service._build_summary_from_notes_message(notes, template=get_template("section_meeting"))
    assert rule not in local, "地端生成流程不得被雲端規則影響"


def test_validate_cloud_speaker_traceability_accepts_body_source_tag():
    service = SummarizationService()
    template = get_template("section_meeting")
    record = """科務會議紀錄
時間：中華民國115年9月3日
主持人：科長　紀錄：AI 會議助理
| 案由及承辦單位 | 辦理情形 | 解除列管 | 繼續列管 |
| --- | --- | --- | --- |
| 配合組織規程調整 | 資管股： | | |

二、科長指示及提醒事項：
（一）組織規程調整
1. 請各相關股別提早預約準備（發言者1，00:00:00）。
2. 印花稅業務移撥（科長，00:01:30）。
"""
    assert service._validate_cloud_speaker_traceability(record, template) == []


def test_validate_cloud_speaker_traceability_flags_omitted_attribution():
    """標籤只出現在開頭欄位／彙整表不算數（實測 Gemini 對照組的失效樣態）。"""
    service = SummarizationService()
    template = get_template("section_meeting")
    record = """科務會議紀錄
時間：中華民國115年9月3日
主持人：發言者1（科長）　紀錄：AI 會議助理
出席人員：發言者1、發言者2、發言者3
| 案由及承辦單位 | 辦理情形 | 解除列管 | 繼續列管 |
| --- | --- | --- | --- |
| 配合組織規程調整（發言者1，00:00:00） | 資管股： | | |

二、科長指示及提醒事項：
1. 請各相關股別提早預約準備。
"""
    issues = service._validate_cloud_speaker_traceability(record, template)
    assert any("缺少發言來源標註" in issue for issue in issues)


def _section_meeting_record(with_sources: bool) -> str:
    tag = "（發言者1，00:00:00）。" if with_sources else "。"
    filler = "本次會議就組織規程與編制表生效後之系統權限、設備調整與人員配置逐項確認，並請各相關股別依分工於期限內完成配合事項，如有疑義應即時向科長反映。" * 2
    return f"""（待確認）科（待確認）年（待確認）月份第（待確認）次科務會議紀錄
時間：中華民國（待確認）年（待確認）月（日）日（星期）（待確認）
地點：（待確認）
主持人：科長　紀錄：AI 會議助理
出席人員：如後附簽到表
歷次科務會議決議事項繼續列管案件：（待確認）
（待確認）年（待確認）月份第（待確認）次科務會議決議事項辦理情形彙整表
決議事項：
| 案由及承辦單位 | 辦理情形 | 解除列管 | 繼續列管 |
| --- | --- | --- | --- |
| 組織規程調整配合事項｜各相關股別： | | |
一、科長轉知局務會議工作報告及相關注意事項：無
二、科長指示及提醒事項：
（一）組織規程與編制表生效配合事項
1. 請各相關股別就系統權限與設備提早預約準備{tag}
{filler}
散會：（待確認）
"""


@pytest.mark.asyncio
async def test_cloud_pipeline_refines_when_speaker_attribution_missing(monkeypatch):
    """科務會議缺發言來源標註時，應觸發補強輪並在補強後通過（確定性絆索）。"""
    service = SummarizationService()
    template = get_template("section_meeting")
    transcript = "[00:00:00-00:01:00] 發言者1：請各股配合組織規程調整"
    notes = "## 1. 會議資訊\n- **主題**：組織規程調整\n"

    responses = iter([
        notes,
        _section_meeting_record(with_sources=False),
        _section_meeting_record(with_sources=True),
    ])
    gemini = AsyncMock(side_effect=lambda *args, **kwargs: next(responses))
    monkeypatch.setattr(service, "_gemini_chat", gemini)

    summary = await service._summarize_with_gemini(
        template.resolve_system_prompt(), transcript, template=template
    )

    # 萃取 1 次＋生成 1 次＋補強 1 次
    assert gemini.await_count == 3
    refinement_message = gemini.await_args_list[-1].args[1]
    assert "缺少發言來源標註" in refinement_message
    assert "（發言者1，00:00:00）" in summary


def test_section_meeting_forbids_source_tags_inside_tracking_table():
    """來源標註只能出現在正文：寫進彙整表會原樣流入列管附件，必須被攔下。"""
    service = SummarizationService()
    template = get_template("section_meeting")
    base = _section_meeting_record(with_sources=True)
    clean_issues = service._validate_summary_quality(base, "## 1. 會議資訊\n", template=template)
    assert not any("機敏" in issue or "彙整表內出現" in issue for issue in clean_issues)

    polluted = base.replace(
        "| 組織規程調整配合事項｜各相關股別： | | |",
        "| 組織規程調整配合事項｜各相關股別：（科長，00:00:00） | | |",
    )
    issues = service._validate_summary_quality(polluted, "## 1. 會議資訊\n", template=template)
    assert any("彙整表內出現發言來源標註" in issue for issue in issues)


# ========================================
# 2026-09-14：會議日期杜撰防線（提示詞規則＋確定性絆索）
# ========================================


def test_extract_year_tokens_normalizes_arabic_chinese_and_excludes_decades():
    """年份抽取：阿拉伯與國字等價比對；「年代」不算年份，避免誤判合法寫法。"""
    extract = SummarizationService._extract_year_tokens

    assert extract("時間：民國113年10月；生效日期為2026年度") == {"113", "2026"}
    assert extract("一一三年、一百一十三年度、二〇二六年度") == {"113", "2026"}
    assert extract("現場有2戶90年代長者，這是九〇年代的事") == set()
    assert extract("生效日期是今年的 11 月 1 號") == set()
    assert extract("") == set()


def test_cloud_generation_requires_date_grounding_rule():
    """日期依據規則必須進雲端生成與補強訊息；地端生成訊息不得被影響（地端不動）。"""
    service = SummarizationService()
    notes = "## 1. 會議資訊\n- **主題**：組織規程調整\n"
    transcript = "[00:00:00-00:01:00] 發言者1：生效日期是今年的 11 月 1 號"
    rule = SummarizationService.CLOUD_DATE_GROUNDING_RULE

    assert rule in service._build_cloud_summary_message(notes, transcript)
    assert rule in service._build_cloud_refinement_message(
        "草稿", notes, ["缺少區塊：X"], transcript
    )
    assert rule not in service._build_summary_from_notes_message(notes)
    assert rule not in service._build_refinement_message("草稿", notes, ["缺少區塊：X"])


def test_validate_cloud_date_grounding_flags_year_missing_from_transcript():
    """實測失效模式：逐字稿只有「今年」，紀錄卻寫死年份 → 必須回報問題。"""
    service = SummarizationService()
    record = "時間：中華民國113年10月（待確認）日\n1. 生效日期為113年11月1日。"
    transcript = "[00:00:00] 發言者1：生效日期是今年的 11 月 1 號"

    issues = service._validate_cloud_date_grounding(record, transcript)
    assert any("紀錄出現逐字稿沒有依據的年份：113年" in issue for issue in issues)

    # 逐字稿有同樣的年份（阿拉伯或國字寫法）→ 不觸發
    assert service._validate_cloud_date_grounding(record, "民國113年11月1日生效") == []
    assert service._validate_cloud_date_grounding(record, "一百一十三年的11月1日生效") == []
    # 紀錄本來就標「（待確認）」→ 不觸發
    assert service._validate_cloud_date_grounding("時間：（待確認）年", transcript) == []


def _summary_without_year() -> str:
    """`_complete_summary()` 去識別年份版本，供日期絆索補強後的情境使用。"""
    return (
        _complete_summary()
        .replace("113年度第1次", "（待確認）年度第1次")
        .replace("中華民國113年3月1日", "中華民國（待確認）年（待確認）月（待確認）日")
    )


@pytest.mark.asyncio
async def test_cloud_pipeline_refines_when_year_not_in_transcript(monkeypatch):
    """紀錄寫入逐字稿沒有的年份時，絆索應觸發補強輪，補強後年份消失。"""
    service = SummarizationService()
    transcript = "主席：生效日期是今年的 11 月 1 號。科長：建議維持月底上線。"

    responses = iter([_notes_with_two_actions(), _complete_summary(), _summary_without_year()])
    gemini = AsyncMock(side_effect=lambda *args, **kwargs: next(responses))
    monkeypatch.setattr(service, "_gemini_chat", gemini)

    summary = await service._summarize_with_gemini(settings.DEFAULT_SYSTEM_PROMPT, transcript)

    # 萃取 1 次＋生成 1 次＋補強 1 次
    assert gemini.await_count == 3
    refinement_message = gemini.await_args_list[-1].args[1]
    assert "紀錄出現逐字稿沒有依據的年份：113年" in refinement_message
    assert "113年" not in summary


# ========================================
# 2026-09-14：範本骨架佔位符外洩修復（雲端專用，確定性）
# ========================================


def test_cloud_finalize_repairs_leaked_template_placeholders():
    """實測失效模式：模型把範本骨架原樣吐出（（年）（月）（日））→ 修回「（待確認）」。

    Gemini 在逐字稿沒提日期時，頭欄位會整段抄提示詞骨架，例如
    「時間：中華民國（年）年（月）月（日）日（星期）（時分）」——看似填了、
    實際上整欄沒有可用資訊，比官方規定的「（待確認）」更糟。
    """
    service = SummarizationService()
    template = get_template("section_meeting")
    leaked = (
        "# 科務會議紀錄\n\n"
        "（待確認）（待確認）年（月）月份第（次）次科務會議紀錄\n"
        "時間：中華民國（年）年（月）月（日）日（星期）（時分）\n"
        "地點：（待確認）\n"
        "主持人：科長　紀錄：AI 會議助理\n"
        "出席人員：如後附簽到表\n"
        "歷次科務會議決議事項繼續列管案件：（待確認）\n"
        "（待確認）（待確認）年（月）月份第（次）次科務會議決議事項辦理情形彙整表\n"
        "決議事項：\n"
        "| 案由及承辦單位 | 辦理情形 | 解除列管 | 繼續列管 |\n"
        "| --- | --- | --- | --- |\n"
        "| 辦理文康活動（資管股） | 資管股： | | |\n"
        "一、科長轉知局務會議工作報告及相關注意事項：無\n"
        "散會：（待確認）\n"
    )

    fixed = service._finalize_cloud_record_text(leaked, template=template)

    assert "（年）年" not in fixed
    assert "（月）月" not in fixed
    assert "（日）日" not in fixed
    assert "第（次）次" not in fixed
    assert "時間：中華民國（待確認）年（待確認）月（待確認）日（待確認）" in fixed
    assert "（待確認）年（待確認）月份第（待確認）次科務會議紀錄" in fixed

    # 地端路徑（`_finalize_record_text`）不套用此修復：地端行為不變
    assert "（年）年" in service._finalize_record_text(leaked, template=template)


def test_placeholder_repair_leaves_body_lines_untouched():
    """正文若剛好出現同名字樣（例如引述表格欄位）不得被改寫。"""
    service = SummarizationService()
    template = get_template("section_meeting")
    record = (
        "（待確認）年（待確認）月份第（待確認）次科務會議紀錄\n"
        "時間：中華民國（年）年（月）月（日）日（星期）（時分）\n"
        "地點：（待確認）\n"
        "一、科長轉知局務會議工作報告及相關注意事項：\n"
        "1. 表格欄位「（月）」的定義請人事室確認（科長，00:05:00）。\n"
        "散會：（待確認）\n"
    )

    fixed = service._finalize_cloud_record_text(record, template=template)

    assert "表格欄位「（月）」的定義請人事室確認（科長，00:05:00）。" in fixed
    assert "（年）年" not in fixed
