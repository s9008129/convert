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
async def test_generate_local_surfaces_model_resolution_error(monkeypatch):
    service = SummarizationService()
    service._ollama_model_error = "設定的 Ollama 模型不存在。"

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
    """雲端第一段須分段萃取；第二段生成須同時看到筆記與原始逐字稿。"""
    service = SummarizationService()
    transcript = "主席：討論專案里程碑。科長：建議維持月底上線。"

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
async def test_cloud_pipeline_refines_when_summary_below_dynamic_floor(monkeypatch):
    """長會議的過薄輸出必須觸發補強輪，且補強訊息附上原始逐字稿。"""
    service = SummarizationService()
    # 約 2 萬 tokens 的長逐字稿 → 動態下限約 1,360 字（20400 // 15，未達 2000 上限）
    transcript = "與會人員針對訪談流程、效益口徑與展示方式進行詳細討論。" * 800

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
async def test_stream_ollama_chat_once_raises_on_truncated_done_reason():
    """done_reason=length（輸出被截斷）→ 可重試例外。"""
    from backend.services.summarization import OllamaStreamRetryable

    service = SummarizationService()
    client = _stream_client([_content_chunk("截斷"), _done_chunk(done_reason="length")])

    with pytest.raises(OllamaStreamRetryable):
        await service._stream_ollama_chat_once(client, {"model": "m"})


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
    assert degraded_plan.notes_merge_budget_tokens < default_plan.notes_merge_budget_tokens


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
