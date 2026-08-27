# -*- coding: utf-8 -*-
"""T20260827-1127-01 WAVE-01 fail-first regression tests。

針對 macOS LM Studio 空摘要、錯誤切塊與逐字稿重複的五類新契約。
這些測試描述 WAVE-02/03/04 之後的正確行為；在現行程式上應
「以正確原因失敗」（現行程式缺該契約，而非測試本身錯誤）。
"""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from backend.core.config import settings
from backend.core.errors import LMSTUDIO_UNREACHABLE, StableServiceError
from backend.services.summarization import SummarizationService
from backend.services.correction import transcript_correction_service
from backend.core.text_postprocess import clean_transcript


FIXTURES = Path(__file__).parent / "fixtures"

BUDGET_TOKENS = 3112  # 16384（LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS）減 output/prompt 開銷


def _one_loaded_selection(service: SummarizationService):
    instance = service._parse_lmstudio_loaded_instances(
        json.loads((FIXTURES / "lmstudio_one_loaded.json").read_text(encoding="utf-8"))
    )[0]
    return service._make_lmstudio_selection(instance)


def _mock_create(monkeypatch, service: SummarizationService, create: AsyncMock):
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    monkeypatch.setattr(service, "_get_lmstudio_client", Mock(return_value=client))
    return create


# ---------------------------------------------------------------------------
# 1. 單行 sparse-punctuation 33k-token chunk 測試
# ---------------------------------------------------------------------------

def _sparse_punctuation_transcript() -> str:
    """模擬真實 ASR：單行、稀疏標點（每約 5,000 字一個句號）、約 33k+ tokens。

    內容隨位置唯一（真實 ASR 不會整份逐字稿完全週期重複）：若 fixture 為
    週期性重複（同一 block 乘 8），任何合法切塊都會因來源週期性產生內容
    相同的 chunks，使「不得近整份重複」的斷言在數學上不可能成立。
    """
    base = "與會單位就年度預算編列與執行進度交換意見並確認後續分工"
    return "".join(
        " ".join(f"{base}第{s}場第{k:03d}項" for k in range(160)) + "。"
        for s in range(8)
    )


def test_single_line_sparse_transcript_chunks_respect_token_budget():
    service = SummarizationService()
    transcript = _sparse_punctuation_transcript()
    assert service._estimate_tokens(transcript) >= 30_000

    chunks = service._split_transcript_into_chunks(transcript, max_input_tokens=BUDGET_TOKENS)

    assert chunks, "切塊結果不可為空"
    for index, chunk in enumerate(chunks):
        assert service._estimate_tokens(chunk) <= BUDGET_TOKENS, (
            f"chunk {index} 超過 input budget "
            f"（{service._estimate_tokens(chunk)} > {BUDGET_TOKENS} tokens）"
        )


def test_single_line_sparse_transcript_chunks_have_no_near_duplicate_pairs():
    service = SummarizationService()
    transcript = _sparse_punctuation_transcript()

    chunks = service._split_transcript_into_chunks(transcript, max_input_tokens=BUDGET_TOKENS)

    def shingles(text: str, width: int = 20) -> set[str]:
        return {text[i:i + width] for i in range(max(len(text) - width + 1, 0))}

    for i in range(len(chunks)):
        for j in range(i + 1, len(chunks)):
            a, b = chunks[i], chunks[j]
            assert a not in b and b not in a, f"chunk {i} 與 chunk {j} 互相包含（近整份重複）"
            sa, sb = shingles(a), shingles(b)
            if not sa or not sb:
                continue
            overlap = len(sa & sb) / min(len(sa), len(sb))
            assert overlap <= 0.6, (
                f"chunk {i} 與 chunk {j} 重疊率 {overlap:.0%} > 60%（重複切塊）"
            )


# ---------------------------------------------------------------------------
# 2. reasoning-only response 測試
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reasoning_only_response_triggers_exactly_one_semantic_retry(monkeypatch):
    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_LLM_PROVIDER", "lmstudio")
    monkeypatch.setattr(settings, "LOCAL_LLM_TRANSIENT_RETRIES", 0)
    selection = _one_loaded_selection(service)

    reasoning_text = "讓我依序思考會議紀錄的結構與重點。" * 60
    first = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content="", reasoning_content=reasoning_text),
                finish_reason="length",
            )
        ]
    )
    second = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content="會議紀錄：討論事項與決議如下。"),
                finish_reason="stop",
            )
        ]
    )
    create = _mock_create(monkeypatch, service, AsyncMock(side_effect=[first, second]))

    try:
        result = await service._summarize_with_lmstudio(
            "system",
            "user",
            max_tokens=1024,
            selection=selection,
        )
    except RuntimeError as exc:
        pytest.fail(f"現行實作未對 reasoning-only 回應執行 semantic retry，直接失敗：{exc}")

    assert result == "會議紀錄：討論事項與決議如下。"
    assert create.await_count == 2, f"應恰好一次 semantic retry，實際呼叫 {create.await_count} 次"

    first_kwargs = create.await_args_list[0].kwargs
    second_kwargs = create.await_args_list[1].kwargs
    assert first_kwargs["model"] == second_kwargs["model"] == "model-alpha"
    assert first_kwargs["temperature"] == second_kwargs["temperature"]
    assert second_kwargs["max_tokens"] > first_kwargs["max_tokens"], "retry 應提高 max_tokens"


# ---------------------------------------------------------------------------
# 3. YAML precedence 測試
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_yaml_must_not_override_caller_temperature_and_max_tokens(monkeypatch):
    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_LLM_PROVIDER", "lmstudio")
    monkeypatch.setattr(settings, "LOCAL_LLM_TRANSIENT_RETRIES", 0)
    yaml_config_reader = Mock(
        return_value={
            "llm": {"lmstudio": {"temperature": 0.2, "max_tokens": 3072}}
        }
    )
    # 後端已移除 summarization 對 legacy YAML 的讀取；raising=False 讓此
    # monkeypatch 改作「斷言 YAML reader 完全不被呼叫」的哨兵。
    monkeypatch.setattr(
        "backend.services.summarization.get_global_config",
        yaml_config_reader,
        raising=False,
    )
    selection = _one_loaded_selection(service)
    create = _mock_create(
        monkeypatch,
        service,
        AsyncMock(
            return_value=SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="caller 參數為權威"))]
            )
        ),
    )

    result = await service._summarize_with_lmstudio(
        "system",
        "user",
        temperature=0.1,
        max_tokens=1500,
        selection=selection,
    )

    assert result == "caller 參數為權威"
    yaml_config_reader.assert_not_called(), "summarization backend 不得讀取 legacy YAML config"
    kwargs = create.await_args.kwargs
    assert kwargs["temperature"] == 0.1, (
        f"YAML temperature 覆蓋了 caller 值（送出 {kwargs['temperature']}）"
    )
    assert kwargs["max_tokens"] == 1500, (
        f"YAML max_tokens 覆蓋了 caller 值（送出 {kwargs['max_tokens']}）"
    )


# ---------------------------------------------------------------------------
# 4. correction amplification 測試
# ---------------------------------------------------------------------------

def _multi_segment_transcript(count: int = 20) -> str:
    return "。".join(f"第{n}位同仁表示這個議題在說一次" for n in range(1, count + 1)) + "。"


@pytest.mark.asyncio
async def test_correction_provider_failure_circuit_breaks_remaining_calls(monkeypatch):
    from backend.core.config import settings as s

    monkeypatch.setattr(s, "CORRECTION_SCOPE", "all")
    monkeypatch.setattr(s, "CORRECTION_MAX_SEGMENT_CHARS", 40)
    transcript = _multi_segment_transcript()
    segments = transcript_correction_service._split_segments(transcript)
    assert len(segments) > 3

    calls: list[str] = []

    async def provider_failing_generate(system_prompt, user_message):
        calls.append(user_message)
        raise StableServiceError(LMSTUDIO_UNREACHABLE, "LM Studio chat 請求失敗")

    corrected, report = await transcript_correction_service.correct_transcript(
        transcript, provider_failing_generate
    )

    assert len(calls) <= 1, (
        f"provider-level 穩定失敗應熔斷後續呼叫，實際呼叫了 {len(calls)} 次"
    )
    assert corrected == transcript, "所有段落原文必須完整保留"
    assert report.error is not None, "provider-level 失敗應記錄在 report.error"


@pytest.mark.asyncio
async def test_correction_local_segment_failure_does_not_circuit_break(monkeypatch):
    from backend.core.config import settings as s

    monkeypatch.setattr(s, "CORRECTION_SCOPE", "all")
    monkeypatch.setattr(s, "CORRECTION_MAX_SEGMENT_CHARS", 40)
    transcript = _multi_segment_transcript(count=10)

    calls: list[str] = []

    async def locally_flaky_generate(system_prompt, user_message):
        calls.append(user_message)
        if len(calls) == 1:
            return ""  # 段落級空回應：局部保留原文，不得熔斷
        return user_message.split("【待校正段落，只輸出此段校正結果】\n")[-1].replace(
            "在說一次", "再說一次"
        )

    corrected, report = await transcript_correction_service.correct_transcript(
        transcript, locally_flaky_generate
    )

    assert len(calls) == report.segments_total, (
        "段落級局部問題不應熔斷，每段仍應嘗試校正"
    )
    assert "再說一次" in corrected
    # 第 1 段回空字串 → 該段（前 2 句）保留原文，其餘段落仍被校正
    assert corrected.count("在說一次") == 2


# ---------------------------------------------------------------------------
# 5. repetition-loop cleanup 測試
# ---------------------------------------------------------------------------

def test_clean_transcript_collapses_single_char_repetition_loop():
    text = "開會前先確認出席名單。" + "對" * 10 + "接著進入報告事項。"
    cleaned, _stats = clean_transcript(text)
    assert cleaned.count("對") <= 2, (
        f"1 字單元連續 >= 8 次應壓到保留 2 次，實際剩 {cleaned.count('對')} 個「對」"
    )
    assert "接著進入報告事項" in cleaned


def test_clean_transcript_collapses_multi_char_repetition_loop_with_spaces():
    text = "報告事項如下。" + " ".join(["請看影片"] * 5) + "。會議結束。"
    cleaned, _stats = clean_transcript(text)
    assert cleaned.count("請看影片") == 2, (
        f"2 字以上單元連續 >= 4 次應壓到保留 2 次，實際剩 {cleaned.count('請看影片')} 次"
    )
    assert "會議結束" in cleaned


@pytest.mark.parametrize(
    "text",
    [
        "主席表示對對對就這樣辦。",          # 1 字單元 3 連 < 8
        "好 好 好 我們繼續。",               # 1 字單元 3 連（空白相連）< 8
        "好的好的好的各位請就座。",          # 2 字單元 3 連 < 4
    ],
)
def test_clean_transcript_preserves_natural_repeats_below_threshold(text):
    cleaned, _stats = clean_transcript(text)
    assert cleaned == text, f"低於 threshold 的自然重複不得被改動：{text!r} → {cleaned!r}"