# -*- coding: utf-8 -*-
"""T20260827-1127-01 WAVE-01a — merge budget 語意分離 fail-first 測試。

RC-1（plan CONFIRMED_ROOT_CAUSE / CHANGE_MAP 1 / REGRESSION_AND_ACCEPTANCE 第 1 組）：
現行 ``LocalContextPlan.notes_merge_budget_tokens``（merge 後可見 notes 目標，
約 900 tokens）同時被當作 provider completion ``max_tokens``：

    merge_predict_cap = min(LOCAL_LLM_RESERVED_OUTPUT_TOKENS, max(notes_merge_budget_tokens, 512))
                      = min(3072, 900) = 900

且 ``_merge_notes_until_fit`` 以 ``expand_output_budget=False`` 呼叫 generation，
使 ``reasoning_retry_allowed = allow_reasoning_retry and expand_output_budget``
恆為 False —— merge 明確禁用 reasoning recovery。

四個測試在現行程式上必須以「行為原因」失敗（不得因 import/fixture/語法錯誤失敗）：

1. ``test_merge_provider_initial_cap_is_reserved_output_not_visible_target``
   merge 第一個 provider 呼叫的 ``max_tokens`` 必須是
   ``LOCAL_LLM_RESERVED_OUTPUT_TOKENS``（3072）；現行送出 900 → 失敗。
2. ``test_merge_call_must_not_disable_semantic_recovery``
   reasoning-only（length + reasoning + 空 content）回應必須觸發 semantic
   recovery；現行以 ``expand_output_budget=False`` 禁用並直接拋
   ``LMSTUDIO_NO_FINAL_CONTENT`` → 失敗。同時記錄 merge 的 generation 呼叫
   kwargs，斷言不得設定 ``allow_reasoning_retry=False``。
3. ``test_reasoning_only_growth_retry_then_orchestration_convergence``
   重現 task 90fdb193 fixture（max_tokens 收到 900、finish_reason=length、
   completion_tokens=899、reasoning_chars=2778、content_chars=0）：growth
   retry 以更高 cap 帶回超過 visible target 的 content，orchestration 續壓縮
   至 <=900 且尾端哨兵不消失；現行在第一次回應就拋
   ``LMSTUDIO_NO_FINAL_CONTENT`` → 失敗。
4. ``test_visible_target_must_not_compress_provider_cap_into_reasoning_exhaustion``
   cap-dependent mock 重現因果：cap<=900 時 reasoning 吃光預算（length+空）、
   cap>900 時留有正文空間。visible target 900 不得把第一次 merge 呼叫的 cap
   壓到 900 造成 fail-fast；現行 cap=900 → 失敗。

測試為 production-shaped：驅動真實 merge orchestration
（``_merge_notes_until_fit`` → ``_generate_with_local_engine`` →
``_summarize_with_lmstudio`` → ``chat.completions.create``），只 mock LM Studio
OpenAI 相容 transport，不做真實 HTTP。
"""

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Optional
from unittest.mock import AsyncMock, Mock

import pytest

from backend.core.config import settings
from backend.core.errors import LMSTUDIO_NO_FINAL_CONTENT, StableServiceError
from backend.services.summarization import SummarizationService


FIXTURES = Path(__file__).parent / "fixtures"

# plan CHANGE_MAP 1 的 merge_visible_target_tokens（未來命名）；目前欄位名為
# notes_merge_budget_tokens（_build_local_context_plan 以 max(900, ...) 計算）。
# fail-first 測試直接以 900 作為 visible target 驅動 merge orchestration。
VISIBLE_TARGET_TOKENS = 900

# task 90fdb193 merge fixture 觀測值：max_tokens=900、finish_reason=length、
# completion_tokens=899、reasoning_chars=2778、content_chars=0
OBSERVED_REASONING_CHARS = 2778
OBSERVED_COMPLETION_TOKENS = 899

# 尾端決議哨兵：hard truncation（保留前段、丟棄後段）會使其消失。
TAIL_SENTINEL = "【尾端決議哨兵】本月底前完成驗收並歸檔結案。"


def _one_loaded_selection(service: SummarizationService):
    instance = service._parse_lmstudio_loaded_instances(
        json.loads((FIXTURES / "lmstudio_one_loaded.json").read_text(encoding="utf-8"))
    )[0]
    return service._make_lmstudio_selection(instance)


def _mock_create(monkeypatch, service: SummarizationService, create: AsyncMock) -> AsyncMock:
    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(service, "_get_lmstudio_client", Mock(return_value=client))
    return create


def _response(
    content: str,
    finish_reason: str = "stop",
    reasoning_text: Optional[str] = None,
    completion_tokens: Optional[int] = None,
    reasoning_tokens: Optional[int] = None,
) -> SimpleNamespace:
    """建立與 LM Studio OpenAI 相容回應同形的 SimpleNamespace。"""
    message = SimpleNamespace(content=content)
    if reasoning_text is not None:
        message.reasoning_content = reasoning_text
    return SimpleNamespace(
        choices=[SimpleNamespace(message=message, finish_reason=finish_reason)],
        usage=SimpleNamespace(
            prompt_tokens=1234,
            completion_tokens=completion_tokens,
            completion_tokens_details=SimpleNamespace(reasoning_tokens=reasoning_tokens),
        ),
    )


def _reasoning_only_text() -> str:
    """reasoning 2778 字元（task 90fdb193 fixture）。"""
    base = "讓我依序思考會議紀錄的結構與重點，逐項盤點決議與待辦是否完整，再決定輸出格式。"
    text = (base * 100)[:OBSERVED_REASONING_CHARS]
    assert len(text) == OBSERVED_REASONING_CHARS
    return text


def _note_with_token_size(
    service: SummarizationService, marker: str, target_tokens: int
) -> str:
    """產生以 ``_estimate_tokens`` 計接近 target_tokens 的萃取筆記 Markdown。"""
    header = "# 萃取筆記\n\n## 2. 議題與決議\n"
    sentence = f"與會單位就{marker}項議題確認設備採購、場地佈置與新聞稿發布的分工，並決議下週五前完成簽核。"
    lines: list[str] = []
    while service._estimate_tokens(header + "\n".join(lines)) < target_tokens:
        lines.append(sentence)
    return header + "\n".join(lines)


async def _merge_notes(service: SummarizationService, selection, notes: list[str]) -> str:
    """以 visible target 900 驅動 production merge orchestration。"""
    return await service._merge_notes_until_fit(
        "lmstudio",
        notes,
        VISIBLE_TARGET_TOKENS,
        None,
        lmstudio_selection=selection,
    )


# ---------------------------------------------------------------------------
# 1. merge provider cap 分離（RC-1 / CHANGE_MAP 1）
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_merge_provider_initial_cap_is_reserved_output_not_visible_target(monkeypatch):
    """merge 第一個 provider 呼叫的 max_tokens 必須是 reserved output（3072）。

    現行 merge_predict_cap = min(3072, max(900, 512)) = 900 →
    以「收到 900 而非 3072」的行為原因失敗。
    """
    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_LLM_PROVIDER", "lmstudio")
    monkeypatch.setattr(settings, "LOCAL_LLM_TRANSIENT_RETRIES", 0)
    selection = _one_loaded_selection(service)

    note_a = _note_with_token_size(service, "甲", 350)
    note_b = _note_with_token_size(service, "乙", 350)
    # 兩份 notes 總量 <= visible target，必須落入同一 merge group（一次呼叫）。
    assert (
        service._estimate_tokens(note_a) + service._estimate_tokens(note_b)
        <= VISIBLE_TARGET_TOKENS
    )

    merged_note = _note_with_token_size(service, "整合", 400)
    create = _mock_create(
        monkeypatch,
        service,
        AsyncMock(return_value=_response(merged_note, finish_reason="stop", completion_tokens=500)),
    )

    await _merge_notes(service, selection, [note_a, note_b])

    assert create.await_count >= 1, "merge 必須實際呼叫 provider"
    first_cap = create.await_args_list[0].kwargs["max_tokens"]
    reserved_output = settings.LOCAL_LLM_RESERVED_OUTPUT_TOKENS
    assert first_cap == reserved_output, (
        f"merge 階段 provider 初始 completion cap 必須是 LOCAL_LLM_RESERVED_OUTPUT_TOKENS"
        f"（{reserved_output}），實際收到 {first_cap}：visible target {VISIBLE_TARGET_TOKENS} "
        "被誤當 provider max_tokens，hidden reasoning 會吃光整個 completion 預算"
    )


# ---------------------------------------------------------------------------
# 2. merge 不得禁用 reasoning recovery（RC-1 / CHANGE_MAP 2）
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_merge_call_must_not_disable_semantic_recovery(monkeypatch):
    """merge 的 generation 呼叫必須允許 semantic recovery。

    現行：``reasoning_retry_allowed = allow_reasoning_retry and expand_output_budget``
    而 merge 以 ``expand_output_budget=False`` 呼叫 → reasoning-only 回應直接
    拋 LMSTUDIO_NO_FINAL_CONTENT（本測試的預期失敗原因）。
    """
    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_LLM_PROVIDER", "lmstudio")
    monkeypatch.setattr(settings, "LOCAL_LLM_TRANSIENT_RETRIES", 0)
    selection = _one_loaded_selection(service)

    note_a = _note_with_token_size(service, "甲", 350)
    note_b = _note_with_token_size(service, "乙", 350)
    assert (
        service._estimate_tokens(note_a) + service._estimate_tokens(note_b)
        <= VISIBLE_TARGET_TOKENS
    )
    merged_note = _note_with_token_size(service, "整合", 400)
    assert service._estimate_tokens(merged_note) <= VISIBLE_TARGET_TOKENS

    create = _mock_create(
        monkeypatch,
        service,
        AsyncMock(
            side_effect=[
                # 第一次回應：finish_reason=length + reasoning + 空 content
                _response(
                    "",
                    finish_reason="length",
                    reasoning_text=_reasoning_only_text(),
                    completion_tokens=OBSERVED_COMPLETION_TOKENS,
                    reasoning_tokens=OBSERVED_COMPLETION_TOKENS,
                ),
                # semantic retry 成功：帶回 final content
                _response(merged_note, finish_reason="stop", completion_tokens=500),
            ]
        ),
    )

    # 記錄 merge 對 generation 入口傳遞的 kwargs（不得設定 allow_reasoning_retry=False）
    recorded_generation_calls: list[dict] = []
    real_generate = service._generate_with_local_engine

    async def recording_generate(engine, system_prompt, user_message, **kwargs):
        recorded_generation_calls.append(
            {"system_prompt": system_prompt, "kwargs": dict(kwargs)}
        )
        return await real_generate(engine, system_prompt, user_message, **kwargs)

    monkeypatch.setattr(service, "_generate_with_local_engine", recording_generate)

    try:
        result = await _merge_notes(service, selection, [note_a, note_b])
    except StableServiceError as exc:
        if exc.code == LMSTUDIO_NO_FINAL_CONTENT:
            pytest.fail(
                "現行 merge 呼叫以 expand_output_budget=False 使 "
                "reasoning_retry_allowed=False，reasoning-only 回應直接拋 "
                "LMSTUDIO_NO_FINAL_CONTENT；merge generation 必須允許 "
                "semantic recovery（allow_reasoning_retry 單獨決定）"
            )
        raise

    assert result.strip(), "merge 必須取得非空 final content"
    assert create.await_count == 2, (
        f"reasoning-only 回應應觸發恰好一次 semantic retry，實際 provider 呼叫 {create.await_count} 次"
    )

    merge_calls = [
        call
        for call in recorded_generation_calls
        if call["system_prompt"] == service.LOCAL_NOTES_MERGE_PROMPT
    ]
    assert merge_calls, "必須觀察到 merge 階段的 generation 呼叫"
    for call in merge_calls:
        kwargs = call["kwargs"]
        assert kwargs.get("allow_reasoning_retry", True) is not False, (
            "merge generation 呼叫不得設定 allow_reasoning_retry=False；"
            f"實際收到 kwargs={kwargs}"
        )


# ---------------------------------------------------------------------------
# 3. reasoning-only growth retry 後成功收斂（task 90fdb193 fixture）
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reasoning_only_growth_retry_then_orchestration_convergence(monkeypatch):
    """重現 task 90fdb193 merge fixture：growth retry 後 orchestration 收斂。

    call1：finish_reason=length、completion_tokens=899、reasoning_chars=2778、
           content_chars=0（重現現行 fail-fast 點）
    call2：growth retry 以更高 cap 帶回 content，但超過 visible target 900
    call3：orchestration 續壓縮 → 最終 <=900，尾端決議哨兵不得消失
    """
    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_LLM_PROVIDER", "lmstudio")
    monkeypatch.setattr(settings, "LOCAL_LLM_TRANSIENT_RETRIES", 0)
    selection = _one_loaded_selection(service)

    note_a = _note_with_token_size(service, "甲", 350)
    note_b = _note_with_token_size(service, "乙", 350)
    assert (
        service._estimate_tokens(note_a) + service._estimate_tokens(note_b)
        <= VISIBLE_TARGET_TOKENS
    )

    oversized_note = _note_with_token_size(service, "超標", 1200) + "\n" + TAIL_SENTINEL
    assert service._estimate_tokens(oversized_note) > VISIBLE_TARGET_TOKENS
    final_note = _note_with_token_size(service, "收斂", 400) + "\n" + TAIL_SENTINEL
    assert service._estimate_tokens(final_note) <= VISIBLE_TARGET_TOKENS

    create = _mock_create(
        monkeypatch,
        service,
        AsyncMock(
            side_effect=[
                # call1：重現 task 90fdb193 的 length/reasoning/empty 回應形狀
                _response(
                    "",
                    finish_reason="length",
                    reasoning_text=_reasoning_only_text(),
                    completion_tokens=OBSERVED_COMPLETION_TOKENS,
                    reasoning_tokens=OBSERVED_COMPLETION_TOKENS,
                ),
                # call2：growth retry 成功，但 content 超過 visible target
                _response(
                    oversized_note, finish_reason="stop", completion_tokens=1300
                ),
                # call3：orchestration 對超標 note 續壓縮並收斂
                _response(final_note, finish_reason="stop", completion_tokens=500),
            ]
        ),
    )

    try:
        result = await _merge_notes(service, selection, [note_a, note_b])
    except StableServiceError as exc:
        if exc.code == LMSTUDIO_NO_FINAL_CONTENT:
            pytest.fail(
                "現行程式在第一次 length/reasoning/empty 回應即拋 "
                "LMSTUDIO_NO_FINAL_CONTENT（merge 以 expand_output_budget=False "
                "禁用 growth retry）；正確行為：growth retry 以更高 cap 取得 "
                "content 後由 orchestration 續壓縮收斂到 <=900"
            )
        raise

    assert create.await_count == 3, (
        f"預期 initial + growth retry + 續壓縮共 3 次 provider 呼叫，實際 {create.await_count} 次"
    )
    first_cap = create.await_args_list[0].kwargs["max_tokens"]
    growth_cap = create.await_args_list[1].kwargs["max_tokens"]
    assert growth_cap > first_cap, "growth retry 必須提高 token cap"

    assert result.strip(), "merge 最終必須產出非空 notes"
    assert service._estimate_tokens(result) <= VISIBLE_TARGET_TOKENS, (
        f"最終 notes 必須收斂到 <= {VISIBLE_TARGET_TOKENS} tokens，"
        f"實際 {service._estimate_tokens(result)}"
    )
    assert "尾端決議哨兵" in result, (
        "尾端決議不得在收斂過程中消失（禁止以 hard truncation 偽造成功）"
    )


# ---------------------------------------------------------------------------
# 4. fail-fast 不得發生：visible target 不得壓縮第一次呼叫的 cap
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_visible_target_must_not_compress_provider_cap_into_reasoning_exhaustion(monkeypatch):
    """visible target 900 不得使 merge 第一次呼叫的 cap 壓到 900。

    cap-dependent mock 忠實重現觀察到的模型行為：hidden reasoning 約消耗
    900+ tokens，因此 cap<=900 時 reasoning 吃光預算（length + 空 content）、
    cap>900 時留有正文空間。merge 若把第一次呼叫 cap 壓到 900，必然
    fail-fast（現行行為，即本測試的預期失敗原因）；cap 使用 reserved output
    時 merge 應直接成功收斂。
    """
    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_LLM_PROVIDER", "lmstudio")
    monkeypatch.setattr(settings, "LOCAL_LLM_TRANSIENT_RETRIES", 0)
    selection = _one_loaded_selection(service)

    note_a = _note_with_token_size(service, "甲", 350)
    note_b = _note_with_token_size(service, "乙", 350)
    merged_note = _note_with_token_size(service, "整合", 400)
    assert service._estimate_tokens(merged_note) <= VISIBLE_TARGET_TOKENS

    def cap_dependent_response(max_tokens: int) -> SimpleNamespace:
        if max_tokens <= VISIBLE_TARGET_TOKENS:
            # reasoning 約 900+ tokens 吃光 cap=900 的預算 → 無正文空間
            return _response(
                "",
                finish_reason="length",
                reasoning_text=_reasoning_only_text(),
                completion_tokens=OBSERVED_COMPLETION_TOKENS,
                reasoning_tokens=OBSERVED_COMPLETION_TOKENS,
            )
        return _response(merged_note, finish_reason="stop", completion_tokens=500)

    # 因果探針（fixture 自檢，非 production 行為斷言）：cap=900 必然
    # reasoning-only、cap=3072 必然有正文，證明 mock 的因果成立。
    probe_900 = cap_dependent_response(VISIBLE_TARGET_TOKENS)
    probe_reserved = cap_dependent_response(settings.LOCAL_LLM_RESERVED_OUTPUT_TOKENS)
    assert probe_900.choices[0].finish_reason == "length"
    assert not probe_900.choices[0].message.content
    assert probe_900.choices[0].message.reasoning_content
    assert probe_reserved.choices[0].finish_reason == "stop"
    assert probe_reserved.choices[0].message.content.strip()

    create = _mock_create(
        monkeypatch,
        service,
        AsyncMock(
            side_effect=lambda **kwargs: cap_dependent_response(int(kwargs["max_tokens"]))
        ),
    )

    try:
        result = await _merge_notes(service, selection, [note_a, note_b])
    except StableServiceError as exc:
        if exc.code == LMSTUDIO_NO_FINAL_CONTENT:
            pytest.fail(
                f"visible target {VISIBLE_TARGET_TOKENS} 使 merge 第一次呼叫的 "
                "provider cap 被壓到 900，hidden reasoning 吃光預算後直接 "
                "fail-fast（LMSTUDIO_NO_FINAL_CONTENT）；provider 初始 completion "
                "cap 必須使用 LOCAL_LLM_RESERVED_OUTPUT_TOKENS（3072）"
            )
        raise

    assert create.await_args_list[0].kwargs["max_tokens"] > VISIBLE_TARGET_TOKENS, (
        "merge 第一次呼叫的 provider cap 不得等於 visible target"
    )
    assert result.strip(), "merge 必須取得非空 final content"
    assert service._estimate_tokens(result) <= VISIBLE_TARGET_TOKENS, (
        f"最終 notes 必須收斂到 <= {VISIBLE_TARGET_TOKENS} tokens"
    )