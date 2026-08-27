# -*- coding: utf-8 -*-
"""T20260827-1127-01 WAVE-01b fail-first regression tests。

有界 reasoning-only recovery state machine（plan CONFIRMED_ROOT_CAUSE RC-2、
CHANGE_MAP 2、REGRESSION_AND_ACCEPTANCE 第 2/3/4 組）。

重現 task 8fd56c54 的 observed 序列：
    initial   finish_reason=length + reasoning evidence + empty content（cap 3072）
    → growth retry 以增加後的 cap（fixture：max_tokens=6522）回應
      finish_reason=stop + reasoning_chars=828 + content_chars=0
    → 需要一次「同 model/instance/prompt/temperature、同 token cap」的 final
      stop replay 才取回非空 content。

目標契約（每個 CORE logical generation 最多三次 completed provider calls）：
    1. initial：caller 指定的初始 provider completion cap。
    2. growth retry：僅 initial 為 `length + reasoning evidence + empty content`
       時，以 Revision-1 headroom/configured-cap 公式增加一次 budget。
    3. stop replay：僅 growth retry 為 `stop + reasoning evidence + empty content`
       時，以相同 model/instance/prompt/temperature 與目前 token cap replay 一次。
    initial 直接 `stop + reasoning evidence + empty content` → 只做一次同 cap
    replay（總計兩次），不接續 growth retry。
    growth retry 再度 `length + empty content`、stop replay 仍空、無 reasoning
    evidence、無可增加 headroom → 立即拋 `LMSTUDIO_NO_FINAL_CONTENT`，且不再
    呼叫 provider。
    correction（BEST_EFFORT）不得使用 semantic recovery：相同回應 shape 最多
    一次 provider call，熔斷後保留該段與剩餘原文，摘要核心繼續。

現行程式（`reasoning_retry_allowed = allow_reasoning_retry and
expand_output_budget`，只允許 `length + reasoning + empty` 一次 budget 增長）
的預期結果：
    - test 1/2/3a 以 RC-2 缺陷的正確原因失敗（缺 final stop replay）。
    - test 3b/3c/3d/4 為契約鎖定（現行程式已符合；WAVE-02 改動 state machine
      時不得回歸）。

本檔 mock LM Studio chat 回應，不做真實 HTTP。執行：
    cd /Users/hsiaojohnny/dev/convert && \\
    DATA_DIR=/Users/hsiaojohnny/dev/convert/data \\
    uv run pytest tests/test_wave01_recovery_sequence.py -p no:cacheprovider -v
"""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

from backend.core.config import settings
from backend.core.errors import LMSTUDIO_NO_FINAL_CONTENT, StableServiceError
from backend.services.correction import transcript_correction_service
from backend.services.summarization import SummarizationService


FIXTURES = Path(__file__).parent / "fixtures"

# task 8fd56c54 observed fixture：initial cap 為 reserved output 3072，
# growth retry 以增加後的 cap 6522 呼叫（stop + reasoning_chars=828 + empty）。
INITIAL_CAP = 3072
GROWTH_CAP = 6522
# initial 回應的 observed reasoning tokens：令 Revision-1 retry cap 公式
# min(provider_headroom, configured_cap, max(initial*2, observed+initial+256))
# = min(16254, 6522, 6728) = 6522，精確重現 fixture 的 growth-retry cap。
OBSERVED_REASONING_TOKENS = 3400

FINAL_CONTENT = "會議紀錄：討論事項與決議如下。"


def _reasoning_text(target_chars: int) -> str:
    """產生指定字元數的 reasoning 證據文字（重現 fixture reasoning_chars）。"""
    sentence = "讓我依序思考會議紀錄的結構與重點。"
    repeated = sentence * (target_chars // len(sentence) + 1)
    return repeated[:target_chars]


def _one_loaded_selection(service: SummarizationService):
    """以既有 fixture 建立唯一 loaded LLM selection（context_length=16384）。"""
    instance = service._parse_lmstudio_loaded_instances(
        json.loads((FIXTURES / "lmstudio_one_loaded.json").read_text(encoding="utf-8"))
    )[0]
    return service._make_lmstudio_selection(instance)


def _lmstudio_response(
    *,
    content: str = "",
    reasoning: str | None = None,
    finish_reason: str | None = None,
    reasoning_tokens: int | None = None,
    prompt_tokens: int = 120,
    completion_tokens: int = 400,
):
    """建構 LM Studio chat.completions 回應 shape（content/reasoning/finish_reason/usage）。"""
    message = SimpleNamespace(content=content)
    if reasoning is not None:
        message.reasoning_content = reasoning
    details = (
        SimpleNamespace(reasoning_tokens=reasoning_tokens)
        if reasoning_tokens is not None
        else None
    )
    return SimpleNamespace(
        choices=[SimpleNamespace(message=message, finish_reason=finish_reason)],
        usage=SimpleNamespace(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            completion_tokens_details=details,
        ),
    )


def _mock_create(monkeypatch, service: SummarizationService, create: AsyncMock) -> AsyncMock:
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    monkeypatch.setattr(service, "_get_lmstudio_client", Mock(return_value=client))
    return create


def _recovery_settings(monkeypatch, growth_cap: int = GROWTH_CAP) -> None:
    """隔離設定：LM Studio provider、零 transient retry、configured retry cap。

    configured_cap 釘在 fixture 值 6522：Revision-1 公式另兩項
    （headroom≈16254、max(initial*2, observed+initial+256)=6728）皆大於 6522，
    因此 growth-retry cap 由 configured cap 決定，精確重現 observed fixture。
    """
    monkeypatch.setattr(settings, "LOCAL_LLM_PROVIDER", "lmstudio")
    monkeypatch.setattr(settings, "LOCAL_LLM_TRANSIENT_RETRIES", 0)
    monkeypatch.setattr(settings, "LMSTUDIO_REASONING_RETRY_MAX_TOKENS", growth_cap)


# ---------------------------------------------------------------------------
# 1. Observed three-call sequence（REGRESSION_AND_ACCEPTANCE 第 2 組）
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_observed_three_call_sequence_replays_after_growth_stop_empty(monkeypatch):
    """8fd56c54 observed 序列：length/empty → growth stop/empty(6522) → replay content。

    契約：精確三次 provider calls；三次的 model/prompt/temperature 完全相同；
    只有 growth retry 增加 token cap，stop replay 沿用相同 cap。

    現行程式（RC-2 缺陷）在 growth retry 回應 stop+reasoning+empty 後直接拋
    LMSTUDIO_NO_FINAL_CONTENT，缺少同 cap stop replay → 本測試以該原因失敗。
    """
    service = SummarizationService()
    _recovery_settings(monkeypatch)
    selection = _one_loaded_selection(service)

    create = _mock_create(
        monkeypatch,
        service,
        AsyncMock(
            side_effect=[
                # initial：length + reasoning evidence + empty content（cap 3072）
                _lmstudio_response(
                    finish_reason="length",
                    content="",
                    reasoning=_reasoning_text(3194),
                    reasoning_tokens=OBSERVED_REASONING_TOKENS,
                ),
                # growth retry：fixture 重現——stop + reasoning_chars=828 + content_chars=0
                _lmstudio_response(
                    finish_reason="stop",
                    content="",
                    reasoning=_reasoning_text(828),
                    reasoning_tokens=828,
                ),
                # final stop replay：同 model/instance/prompt/temperature、同 cap，非空 content
                _lmstudio_response(finish_reason="stop", content=FINAL_CONTENT),
            ]
        ),
    )

    try:
        result = await service._summarize_with_lmstudio(
            "system", "user", max_tokens=INITIAL_CAP, selection=selection,
        )
    except StableServiceError as exc:
        pytest.fail(
            "現行程式缺陷（RC-2）：growth retry（max_tokens=6522）回應 "
            "stop + reasoning + empty content 後直接拋 "
            f"{exc.code}，未執行同 model/instance/prompt/temperature、同 cap 的 "
            f"final stop replay（provider 呼叫數 {create.await_count}）：{exc}"
        )

    assert result == FINAL_CONTENT
    assert create.await_count == 3, (
        f"observed 序列應精確三次 provider calls（initial + growth retry + stop replay），"
        f"實際 {create.await_count} 次"
    )

    calls = create.await_args_list
    caps = [call.kwargs["max_tokens"] for call in calls]
    assert caps[0] == INITIAL_CAP, f"initial 應使用 caller cap {INITIAL_CAP}，實際 {caps[0]}"
    assert caps[1] == GROWTH_CAP, (
        f"growth retry 應以增加後的 cap（fixture 6522）呼叫，實際 {caps[1]}"
    )
    assert caps[1] > caps[0], "只有 growth retry 應增加 token cap"
    assert caps[2] == caps[1], (
        f"stop replay 不得再增加 token cap（應維持 {caps[1]}），實際 {caps[2]}"
    )

    models = {call.kwargs["model"] for call in calls}
    assert models == {"model-alpha"}, f"三次呼叫必須使用同一 model key，實際 {models}"
    temperatures = {call.kwargs["temperature"] for call in calls}
    assert len(temperatures) == 1, f"三次呼叫 temperature 必須相同，實際 {temperatures}"
    messages = [call.kwargs["messages"] for call in calls]
    assert messages[0] == messages[1] == messages[2], (
        "三次呼叫的 system/user prompt 必須完全相同"
    )


# ---------------------------------------------------------------------------
# 2. initial 直接 stop + reasoning + empty → 一次同 cap replay（總計兩次）
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_initial_stop_reasoning_empty_replays_once_at_same_cap(monkeypatch):
    """initial 即 `stop + reasoning evidence + empty content` → 只做一次同 cap replay。

    契約：總計兩次 provider calls、replay 不增加 token cap、不接續 growth retry。

    現行程式（RC-2 缺陷）只認得 `length` 觸發的 retry，stop + empty 直接拋
    LMSTUDIO_NO_FINAL_CONTENT（僅 1 次呼叫）→ 本測試以該原因失敗。
    """
    service = SummarizationService()
    _recovery_settings(monkeypatch)
    selection = _one_loaded_selection(service)

    create = _mock_create(
        monkeypatch,
        service,
        AsyncMock(
            side_effect=[
                _lmstudio_response(
                    finish_reason="stop",
                    content="",
                    reasoning=_reasoning_text(828),
                    reasoning_tokens=828,
                ),
                _lmstudio_response(finish_reason="stop", content="會議紀錄：結論與待辦如下。"),
            ]
        ),
    )

    try:
        result = await service._summarize_with_lmstudio(
            "system", "user", max_tokens=INITIAL_CAP, selection=selection,
        )
    except StableServiceError as exc:
        pytest.fail(
            "現行程式缺陷（RC-2）：initial 直接回應 stop + reasoning + empty content 時拋 "
            f"{exc.code}，未執行一次同 cap replay（provider 呼叫數 {create.await_count}）：{exc}"
        )

    assert result == "會議紀錄：結論與待辦如下。"
    assert create.await_count == 2, (
        f"initial stop+empty 只允許一次同 cap replay（總計兩次），實際 {create.await_count} 次"
    )
    calls = create.await_args_list
    caps = [call.kwargs["max_tokens"] for call in calls]
    assert caps == [INITIAL_CAP, INITIAL_CAP], (
        f"同 cap replay 不得增加 token cap，實際 caps={caps}"
    )
    assert len({call.kwargs["model"] for call in calls}) == 1
    assert len({call.kwargs["temperature"] for call in calls}) == 1
    assert calls[0].kwargs["messages"] == calls[1].kwargs["messages"]


# ---------------------------------------------------------------------------
# 3. Retry exhaustion（REGRESSION_AND_ACCEPTANCE 第 3 組）
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_stop_replay_still_empty_raises_after_exactly_three_calls(monkeypatch):
    """3a：第三次（stop replay）仍空 content → 拋 LMSTUDIO_NO_FINAL_CONTENT。

    契約：精確三次 calls 後立即拋穩定錯誤，不再有後續 provider 呼叫。

    現行程式（RC-2 缺陷）在第二次（growth retry stop+empty）就拋錯，只呼叫
    2 次 → call-count 斷言以「缺 stop replay」為原因失敗。
    """
    service = SummarizationService()
    _recovery_settings(monkeypatch)
    selection = _one_loaded_selection(service)

    create = _mock_create(
        monkeypatch,
        service,
        AsyncMock(
            side_effect=[
                _lmstudio_response(
                    finish_reason="length",
                    content="",
                    reasoning=_reasoning_text(3194),
                    reasoning_tokens=OBSERVED_REASONING_TOKENS,
                ),
                _lmstudio_response(
                    finish_reason="stop",
                    content="",
                    reasoning=_reasoning_text(828),
                    reasoning_tokens=828,
                ),
                # 第三次 stop replay 仍空 content（含 reasoning 也不得再重試）
                _lmstudio_response(
                    finish_reason="stop",
                    content="",
                    reasoning=_reasoning_text(828),
                    reasoning_tokens=828,
                ),
            ]
        ),
    )

    with pytest.raises(StableServiceError) as exc_info:
        await service._summarize_with_lmstudio(
            "system", "user", max_tokens=INITIAL_CAP, selection=selection,
        )

    assert exc_info.value.code == LMSTUDIO_NO_FINAL_CONTENT
    assert create.await_count == 3, (
        "stop replay 仍空應在精確三次 provider calls 後拋 LMSTUDIO_NO_FINAL_CONTENT"
        f"且不再呼叫，實際 {create.await_count} 次（現行程式缺第三次 stop replay）"
    )


@pytest.mark.asyncio
async def test_growth_retry_again_length_empty_raises_without_third_call(monkeypatch):
    """3b：growth retry 再度 `length + empty content` → 立即拋，不接續第三次呼叫。

    契約鎖定（現行程式已符合）：growth retry 後仍 length+empty 表示 budget
    增長無效，必須立即拋 LMSTUDIO_NO_FINAL_CONTENT 且不得再 replay。
    """
    service = SummarizationService()
    _recovery_settings(monkeypatch)
    selection = _one_loaded_selection(service)

    create = _mock_create(
        monkeypatch,
        service,
        AsyncMock(
            side_effect=[
                _lmstudio_response(
                    finish_reason="length",
                    content="",
                    reasoning=_reasoning_text(3194),
                    reasoning_tokens=OBSERVED_REASONING_TOKENS,
                ),
                # growth retry（cap 6522）後仍 length + empty content
                _lmstudio_response(
                    finish_reason="length",
                    content="",
                    reasoning=_reasoning_text(828),
                    reasoning_tokens=828,
                ),
            ]
        ),
    )

    with pytest.raises(StableServiceError) as exc_info:
        await service._summarize_with_lmstudio(
            "system", "user", max_tokens=INITIAL_CAP, selection=selection,
        )

    assert exc_info.value.code == LMSTUDIO_NO_FINAL_CONTENT
    assert create.await_count == 2, (
        f"growth retry 再度 length+empty 應立即拋錯（共 2 次呼叫），實際 {create.await_count} 次"
    )


@pytest.mark.asyncio
async def test_empty_response_without_reasoning_evidence_raises_without_retry(monkeypatch):
    """3c：回應無 reasoning evidence → 不得觸發任何 retry，立即拋。

    契約鎖定（現行程式已符合）：growth retry 與 stop replay 都需要 reasoning
    evidence；無證據的空回應是模型異常，直接拋 LMSTUDIO_NO_FINAL_CONTENT。
    """
    service = SummarizationService()
    _recovery_settings(monkeypatch)
    selection = _one_loaded_selection(service)

    create = _mock_create(
        monkeypatch,
        service,
        AsyncMock(
            side_effect=[
                # length + empty content，但無任何 reasoning 證據
                _lmstudio_response(finish_reason="length", content=""),
            ]
        ),
    )

    with pytest.raises(StableServiceError) as exc_info:
        await service._summarize_with_lmstudio(
            "system", "user", max_tokens=INITIAL_CAP, selection=selection,
        )

    assert exc_info.value.code == LMSTUDIO_NO_FINAL_CONTENT
    assert create.await_count == 1, (
        f"無 reasoning evidence 時不得 retry，實際呼叫 {create.await_count} 次"
    )


@pytest.mark.asyncio
async def test_no_available_headroom_raises_after_single_call(monkeypatch):
    """3d：無可增加 headroom（configured cap 低於 initial cap）→ 立即拋。

    契約鎖定（現行程式已符合）：retry cap 無法高於 initial cap 時不得發出
    第二次呼叫，直接拋 LMSTUDIO_NO_FINAL_CONTENT。
    """
    service = SummarizationService()
    # configured retry cap 1024 < initial 3072 → 無可增加 headroom
    _recovery_settings(monkeypatch, growth_cap=1024)
    selection = _one_loaded_selection(service)

    create = _mock_create(
        monkeypatch,
        service,
        AsyncMock(
            side_effect=[
                _lmstudio_response(
                    finish_reason="length",
                    content="",
                    reasoning=_reasoning_text(3194),
                    reasoning_tokens=OBSERVED_REASONING_TOKENS,
                ),
            ]
        ),
    )

    with pytest.raises(StableServiceError) as exc_info:
        await service._summarize_with_lmstudio(
            "system", "user", max_tokens=INITIAL_CAP, selection=selection,
        )

    assert exc_info.value.code == LMSTUDIO_NO_FINAL_CONTENT
    assert create.await_count == 1, (
        f"無 headroom 時不得發出第二次呼叫，實際 {create.await_count} 次"
    )


# ---------------------------------------------------------------------------
# 4. Correction 熔斷（REGRESSION_AND_ACCEPTANCE 第 4 組）
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_correction_reasoning_only_empty_response_circuit_breaks_after_one_call(monkeypatch):
    """相同回應 shape（reasoning-only/empty）用於 correction：最多一次 provider call。

    契約：correction 是 BEST_EFFORT，不得使用 semantic recovery；首次
    provider 穩定失敗即熔斷，保留該段與剩餘原文，摘要核心繼續。

    以 production wiring 驗證：task_processor 注入的 generate_fn 呼叫
    `generate_local(..., allow_reasoning_retry=False)`，LM Studio 回
    reasoning-only/empty 時不得出現 semantic recovery 呼叫放大。
    契約鎖定（現行程式已符合；WAVE-02 重構 state machine 時不得回歸）。
    """
    monkeypatch.setattr(settings, "LOCAL_LLM_PROVIDER", "lmstudio")
    monkeypatch.setattr(settings, "LOCAL_LLM_TRANSIENT_RETRIES", 0)
    monkeypatch.setattr(settings, "CORRECTION_SCOPE", "all")
    monkeypatch.setattr(settings, "CORRECTION_MAX_SEGMENT_CHARS", 40)

    service = SummarizationService()
    selection = _one_loaded_selection(service)
    # generate_local → _select_local_engine → _resolve_lmstudio_selection：
    # 以 selection mock 取代 inventory 探測，其餘走 production 路徑。
    monkeypatch.setattr(
        service, "_resolve_lmstudio_selection", AsyncMock(return_value=selection)
    )
    create = _mock_create(
        monkeypatch,
        service,
        AsyncMock(
            return_value=_lmstudio_response(
                finish_reason="length",
                content="",
                reasoning=_reasoning_text(828),
                reasoning_tokens=828,
            )
        ),
    )

    transcript = "。".join(
        f"第{n}位同仁表示這個議題在說一次" for n in range(1, 7)
    ) + "。"

    corrected, report = await transcript_correction_service.correct_transcript(
        transcript,
        lambda system_prompt, user_message: service.generate_local(
            system_prompt, user_message, temperature=0.0, allow_reasoning_retry=False
        ),
    )

    assert create.await_count == 1, (
        "correction 遇 reasoning-only/empty 回應不得使用 semantic recovery，"
        f"最多一次 provider call，實際 {create.await_count} 次"
    )
    assert corrected == transcript, (
        "熔斷後必須保留該段與所有剩餘段落原文（correction 為 BEST_EFFORT，"
        "不得遺失任何逐字稿內容）"
    )
    assert report.error is not None, "熔斷應記錄在 report.error，摘要核心繼續"
    assert report.segments_total >= 2, (
        "fixture 應產生多段逐字稿，才能驗證熔斷保留『該段及剩餘原文』"
    )