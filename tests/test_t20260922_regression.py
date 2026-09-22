# -*- coding: utf-8 -*-
"""T20260922-1349-01 fail-first regression tests：merge 可承接預算與 LM Studio 思考關閉。

對應實機 E2E 失敗（task 3ae2d9ec，`0903-科務會議.m4a`，輸出
`逐字稿（會議紀錄生成失敗）`）的三個根因：

1. **RC-1b（固定 900 常數）**：merge 的可見目標是與 context 無關的硬性
   900-token gate。整併一旦收斂到單一 note 且模型未壓到 900 以下，即無分組可
   再依賴 → 必然拋 `LOCAL_LLM_MERGE_NOT_CONVERGED`，整份會議紀錄被 veto 成
   逐字稿 fallback（實測 1 份筆記、1754 tokens）。正確契約：可見目標由「最終
   生成階段可承接的輸入預算」推導（900 為下限、4096 為品質上限），單一 note
   只要在下游預算內即視為已收斂；真的超出下游預算時仍 fail loudly。
2. **RC-2（LM Studio 未關閉思考）**：`LOCAL_LLM_DISABLE_THINKING` 僅實作於
   Ollama 路徑，LM Studio 每次呼叫都先產生 reasoning tokens（實測單場 11 次
   呼叫、其中 1 次 finish_reason=length 且 content 為空）。正確契約：LM Studio
   以 OpenAI 相容的 `reasoning_effort="none"` 關閉思考；端點不支援（HTTP 400）
   時降級為不帶該欄位重送一次。
3. **RC-3（規劃視窗被 settings 預設夾住）**：`min(settings, instance ctx)` 讓
   8192 在已載入 32K/128K instance 時反向成為瓶頸。正確契約：規劃視窗以
   selected loaded instance 的 context_length 為權威。

這些測試描述修復後的正確行為；修復前應「以正確原因失敗」。
"""

import json
import os
import re
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest

# 本測試檔必須可獨立 collect：logger 於 import 時建立 DATA_DIR/logs，
# 預設 /app/data 在 macOS 讀取失敗，故在 import backend 前備妥隔離目錄。
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="meetingscribe-t20260922-"))

from backend.core.config import settings
from backend.core.errors import LOCAL_LLM_MERGE_NOT_CONVERGED, StableServiceError
from backend.services.summarization import SummarizationService


FIXTURES = Path(__file__).parent / "fixtures"

SENTINEL_LINE = "決議：T20260922-SENTINEL-RESOLUTION 待辦：T20260922-SENTINEL-ACTION"


def _one_loaded_selection(service: SummarizationService):
    instance = service._parse_lmstudio_loaded_instances(
        json.loads((FIXTURES / "lmstudio_one_loaded.json").read_text(encoding="utf-8"))
    )[0]
    return service._make_lmstudio_selection(instance)


def _note_with_tokens(service, marker: str, target_tokens: int, tail: str = "") -> str:
    """建構精確等於 target_tokens（依 `_estimate_tokens`）的萃取筆記 fixture。"""
    header = f"# 萃取筆記（{marker}）\n\n## 議題與決議\n"
    body = "- 討論預算編列與執行進度，並確認後續分工安排。\n"
    note = header + body + tail
    deficit = target_tokens - service._estimate_tokens(note)
    if deficit > 0:
        candidate = header + "尾" * deficit + "\n" + body + tail
        drift = target_tokens - service._estimate_tokens(candidate)
        if drift:
            candidate = header + "尾" * (deficit + drift) + "\n" + body + tail
        note = candidate
    assert service._estimate_tokens(note) == target_tokens, (
        f"測試 fixture 建構失敗：{marker} 應為 {target_tokens} tokens，"
        f"實際 {service._estimate_tokens(note)}"
    )
    return note


def _install_merge_generator(monkeypatch, service, responder):
    """在 `_generate_with_local_engine` 邊界 mock 模型，回傳呼叫紀錄清單。"""
    calls = []

    async def generator(engine, system_prompt, user_message, **kwargs):
        calls.append(SimpleNamespace(user_message=user_message, kwargs=kwargs))
        return responder(user_message)

    monkeypatch.setattr(service, "_generate_with_local_engine", generator)
    return calls


# ---------------------------------------------------------------------------
# RC-1b：可見目標由 context 推導（900 為下限、4096 為品質上限）
# ---------------------------------------------------------------------------

def test_merge_visible_target_floor_at_8192_and_ceiling_at_large_context():
    """ctx=8192 時可見目標＝歷史下限 900；大 context 時＝品質上限 4096。"""
    service = SummarizationService()

    degraded = service._build_local_context_plan(
        "測試逐字稿",
        settings.DEFAULT_SYSTEM_PROMPT,
        context_window_tokens=8192,
    )
    assert degraded.merge_visible_target_tokens == service.LOCAL_LLM_MERGE_VISIBLE_TARGET_TOKENS
    assert degraded.merge_feasible_input_tokens is not None
    assert degraded.merge_feasible_input_tokens >= degraded.merge_visible_target_tokens, (
        "下游可承接上限不得低於可見目標（否則比舊行為更嚴格）"
    )

    large = service._build_local_context_plan(
        "測試逐字稿",
        settings.DEFAULT_SYSTEM_PROMPT,
        context_window_tokens=128000,
    )
    assert large.merge_visible_target_tokens == (
        service.LOCAL_LLM_MERGE_VISIBLE_TARGET_CEILING_TOKENS
    ), "大 context 時可見目標應停在上限，不隨 context 無界放大（維持最終生成聚焦）"
    assert large.merge_feasible_input_tokens > large.merge_visible_target_tokens, (
        "下游可承接上限必須大於軟性可見目標，單一 note 才有「已收斂」的成功出口"
    )


@pytest.mark.asyncio
async def test_merge_production_shape_single_note_above_legacy_900_target_succeeds(
    monkeypatch,
):
    """實機失敗形狀：5 份 notes 整併後為單一 1754-token note，不得 veto 整份紀錄。

    修復前行為（實測 task 3ae2d9ec）：可見目標是固定 900，第 4 輪檢查
    `round_index > LOCAL_LLM_MAX_MERGE_ROUNDS` 先觸發 → 拋
    `LOCAL_LLM_MERGE_NOT_CONVERGED` → 整份會議紀錄回退為逐字稿 fallback。
    修復後可見目標由 context 推導（32768 → 4096），同一份 note 即在下游可承接
    範圍內，且 5 份 notes 於單組完成整併（不再呼叫放大）。
    """
    service = SummarizationService()
    plan = service._build_local_context_plan(
        "測試逐字稿", settings.DEFAULT_SYSTEM_PROMPT, context_window_tokens=32768
    )
    visible = plan.merge_visible_target_tokens
    feasible = plan.merge_feasible_input_tokens
    assert 900 < 1754 <= visible, "測試前提：1754-token note 必須落在可見目標之內"

    notes = [_note_with_tokens(service, f"N{i}", 900) for i in range(1, 6)]
    responder = lambda user_message: _note_with_tokens(  # noqa: E731
        service, "R1", 1754, tail=SENTINEL_LINE + "\n"
    )
    calls = _install_merge_generator(monkeypatch, service, responder)

    result = await service._merge_notes_until_fit(
        "lmstudio",
        notes,
        visible,
        context_window_tokens=plan.context_window_tokens,
        merge_input_budget_tokens=plan.merge_input_budget_tokens,
        merge_provider_output_tokens=plan.merge_provider_output_tokens,
        merge_feasible_input_tokens=feasible,
    )

    assert len(calls) == 1, (
        f"5 份 notes 在充足的 merge_input_budget 下應於單組一次呼叫完成整併"
        f"（實際 {len(calls)} 次）"
    )
    assert service._estimate_tokens(result) > 900, (
        "測試前提：結果必須高於舊的固定 900 目標（否則測不到 RC-1b）"
    )
    assert SENTINEL_LINE in result, "停止整併不得丟失尾端決議／待辦內容"


@pytest.mark.asyncio
async def test_single_note_between_visible_target_and_feasible_budget_is_accepted(
    monkeypatch,
):
    """單一 note 超過軟性可見目標但仍在硬性下游預算內 → 直接收斂、不再呼叫模型。

    「可見目標」是壓縮壓力（模型不保證縮小），「下游可承接上限」才是安全判斷。
    兩者之間的單一 note 必須視為已收斂，否則整份紀錄會被無謂 veto。
    """
    service = SummarizationService()
    plan = service._build_local_context_plan(
        "測試逐字稿", settings.DEFAULT_SYSTEM_PROMPT, context_window_tokens=32768
    )
    visible = plan.merge_visible_target_tokens
    feasible = plan.merge_feasible_input_tokens
    oversized = _note_with_tokens(
        service, "BAND", visible + 1000, tail=SENTINEL_LINE + "\n"
    )
    assert service._estimate_tokens(oversized) <= feasible, "測試前提：仍在硬性上限內"

    calls = _install_merge_generator(
        monkeypatch, service, lambda user_message: oversized
    )

    result = await service._merge_notes_until_fit(
        "lmstudio",
        [oversized],
        visible,
        context_window_tokens=plan.context_window_tokens,
        merge_feasible_input_tokens=feasible,
    )

    assert len(calls) == 0, (
        f"單一 note 已在下游可承接範圍內，不應再耗用 provider 呼叫（實際 "
        f"{len(calls)} 次）"
    )
    assert result.strip() == oversized.strip(), (
        "停止整併必須原樣保留來源內容（不得硬截斷）"
    )


# ---------------------------------------------------------------------------
# RC-2：LM Studio 以 reasoning_effort="none" 關閉思考（含 HTTP 400 相容降級）
# ---------------------------------------------------------------------------

def _fake_client(create: AsyncMock):
    return SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )


def _http_error(status_code: int) -> Exception:
    error = Exception(f"HTTP {status_code}")
    error.response = SimpleNamespace(status_code=status_code)
    return error


@pytest.mark.asyncio
async def test_lmstudio_request_disables_thinking_with_reasoning_effort(monkeypatch):
    """LOCAL_LLM_DISABLE_THINKING=True 時，LM Studio 請求必須帶 reasoning_effort=none。"""
    service = SummarizationService()
    selection = _one_loaded_selection(service)
    monkeypatch.setattr(settings, "LOCAL_LLM_DISABLE_THINKING", True)
    create = AsyncMock(return_value=SimpleNamespace())
    client = _fake_client(create)

    await service._lmstudio_chat_request(
        client, selection, [{"role": "user", "content": "x"}], 0.2, 512
    )

    assert create.await_count == 1
    kwargs = create.await_args.kwargs
    extra_body = kwargs.get("extra_body") or {}
    assert extra_body.get("reasoning_effort") == "none", (
        "LM Studio 路徑必須套用 LOCAL_LLM_DISABLE_THINKING（舊行為僅 Ollama 有此開關），"
        "否則推理型模型的 thinking 會吃光 completion 預算並拖長生成階段"
    )
    # v4.8.0：非思考模式另需送官方建議的 top_p／top_k（見
    # test_lmstudio_request_sends_official_sampling_params）
    assert extra_body.get("top_p") == settings.LOCAL_LLM_SAMPLING_TOP_P
    assert extra_body.get("top_k") == settings.LOCAL_LLM_SAMPLING_TOP_K


@pytest.mark.asyncio
async def test_lmstudio_request_sends_official_sampling_params(monkeypatch):
    """v4.8.0：非思考模式必須送官方建議的 top_p=0.8／top_k=20（舊行為完全不送）。"""
    service = SummarizationService()
    selection = _one_loaded_selection(service)
    monkeypatch.setattr(settings, "LOCAL_LLM_SAMPLING_TOP_P", 0.8)
    monkeypatch.setattr(settings, "LOCAL_LLM_SAMPLING_TOP_K", 20)
    create = AsyncMock(return_value=SimpleNamespace())

    await service._lmstudio_chat_request(
        _fake_client(create), selection, [{"role": "user", "content": "x"}], 0.7, 512
    )

    extra_body = create.await_args.kwargs.get("extra_body") or {}
    assert extra_body.get("top_p") == 0.8
    assert extra_body.get("top_k") == 20


@pytest.mark.asyncio
async def test_lmstudio_request_omits_reasoning_effort_when_thinking_enabled(monkeypatch):
    """LOCAL_LLM_DISABLE_THINKING=False 時不得送出 reasoning_effort（維持模型預設）。"""
    service = SummarizationService()
    selection = _one_loaded_selection(service)
    monkeypatch.setattr(settings, "LOCAL_LLM_DISABLE_THINKING", False)
    create = AsyncMock(return_value=SimpleNamespace())

    await service._lmstudio_chat_request(
        _fake_client(create), selection, [{"role": "user", "content": "x"}], 0.2, 512
    )

    extra_body = create.await_args.kwargs.get("extra_body") or {}
    assert "reasoning_effort" not in extra_body


@pytest.mark.asyncio
async def test_lmstudio_request_degrades_when_endpoint_rejects_reasoning_effort(monkeypatch):
    """端點回 HTTP 400（不認識 reasoning_effort）時必須降級重送一次，不得讓整份紀錄失敗。"""
    service = SummarizationService()
    selection = _one_loaded_selection(service)
    monkeypatch.setattr(settings, "LOCAL_LLM_DISABLE_THINKING", True)
    expected = SimpleNamespace()
    create = AsyncMock(side_effect=[_http_error(400), expected])

    response = await service._lmstudio_chat_request(
        _fake_client(create), selection, [{"role": "user", "content": "x"}], 0.2, 512
    )

    assert response is expected
    assert create.await_count == 2, "HTTP 400 應降級重送一次（同 Ollama 的 think 相容降級）"
    first_extra = create.await_args_list[0].kwargs.get("extra_body") or {}
    assert first_extra.get("reasoning_effort") == "none"
    # v4.8.0 降級順序：先丟取樣欄位（top_p／top_k），仍失敗才丟 reasoning_effort
    second_extra = create.await_args_list[1].kwargs.get("extra_body") or {}
    assert "top_p" not in second_extra and "top_k" not in second_extra, (
        "第一次降級只丟取樣欄位，仍須保留關閉思考的 reasoning_effort"
    )
    assert second_extra.get("reasoning_effort") == "none"


@pytest.mark.asyncio
async def test_lmstudio_request_degrades_fully_when_endpoint_rejects_sampling_too(monkeypatch):
    """端點對取樣欄位也回 400 時，必須再降一級為完全不帶 extra_body。"""
    service = SummarizationService()
    selection = _one_loaded_selection(service)
    monkeypatch.setattr(settings, "LOCAL_LLM_DISABLE_THINKING", True)
    expected = SimpleNamespace()
    create = AsyncMock(side_effect=[_http_error(400), _http_error(400), expected])

    response = await service._lmstudio_chat_request(
        _fake_client(create), selection, [{"role": "user", "content": "x"}], 0.2, 512
    )

    assert response is expected
    assert create.await_count == 3, "兩級降級各重送一次即成功，不得讓整份紀錄失敗"
    assert "extra_body" not in create.await_args_list[2].kwargs


# ---------------------------------------------------------------------------
# RC-3：規劃視窗以已載入 instance 的 context_length 為權威
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pipeline_plans_with_loaded_instance_context_not_settings_default(monkeypatch):
    """規劃視窗必須等於 selected instance 的 context_length，不受 settings 預設夾住。"""
    service = SummarizationService()
    selection = service._make_lmstudio_selection(
        SimpleNamespace(
            model_key="model-alpha",
            instance_id="model-alpha-instance-1",
            context_length=32768,
        )
    )
    monkeypatch.setattr(settings, "LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS", 8192)
    service._active_lmstudio_selection = selection

    async def fake_engine():
        return "lmstudio"

    monkeypatch.setattr(service, "_select_local_engine", fake_engine)

    captured = {}

    def fake_plan(transcript, system_prompt, **kwargs):
        captured.update(kwargs)
        return SummarizationService._build_local_context_plan(
            service,
            transcript,
            system_prompt,
            context_window_tokens=8192,
        )

    monkeypatch.setattr(service, "_build_local_context_plan", fake_plan)

    async def fake_generate(*args, **kwargs):
        return "一、測試紀錄\n（一）項目\n1. 內容（發言者1，00:00:00）。"

    monkeypatch.setattr(service, "_generate_with_local_engine", fake_generate)

    await service._summarize_with_local_pipeline("逐字稿內容", settings.DEFAULT_SYSTEM_PROMPT)

    assert captured.get("context_window_tokens") == 32768, (
        "規劃視窗必須以 selected loaded instance 的 context_length 為權威；"
        "min(settings, instance) 會讓 settings 預設反向成為瓶頸"
    )
