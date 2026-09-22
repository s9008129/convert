# -*- coding: utf-8 -*-
"""T20260922-1930-01 —— 地端深度會議紀錄品質對齊雲端（v4.8.0）fail-first 測試。

背景（實測，同一支 `0903-科務會議.m4a`、同一模板、同一份 ASR 逐字稿）：

* 雲端 Gemini 基準：事實覆蓋率 61.7%、忠實度 12 點 0 捏造、發言來源標註 25 處、
  ASR 同音錯字修正率 84.6%。
* 地端 dense 27B（task b20c90a7）：覆蓋 53.9%、出處標註 0 處、錯字修正 53.8%。
* 地端 MoE 35B-A3B（task 836fcae7）：覆蓋 75.6%（**高於雲端**）、但出處標註 0 處、
  錯字修正 15.4%，並有 1 條捏造與 1 條自相矛盾。

=> 地端輸的不是「模型能力」，而是管線與規則。本檔釘住五條修復契約：

1. ``chunk_input_budget`` 不再固定夾在 3200（128K instance 只用到 2.6%）。
2. 各階段輸出上限由 context 推導（不再固定 3072）。
3. 萃取筆記在下游可承接時零損串接、不進有損整併（實測整併關卡截斷損失 47~62%）。
4. 最終生成與補強改「筆記＋逐字稿」雙輸入（雲端同構），context 不足才退回只餵筆記。
5. 地端一體適用雲端的紀錄契約：時間戳出處標註、年份依據、動態長度閘門、補強訊息
   指名具體遺漏待辦。
"""

import os
import tempfile

# 本測試檔必須可獨立 collect：logger 於 import 時建立 DATA_DIR/logs，
# 預設 /app/data 在 macOS 讀取失敗，故在 import backend 前備妥隔離目錄。
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="meetingscribe-t20260922-rq-"))

from unittest.mock import AsyncMock, Mock  # noqa: E402

import pytest  # noqa: E402

from backend.core.config import settings  # noqa: E402
from backend.core.templates import get_template  # noqa: E402
from backend.services.summarization import SummarizationService  # noqa: E402


TRANSCRIPT_LINE = "[00:00:10-00:00:40] 發言者1：請各股配合辦理組織規程調整，並於本週五前回報。"


def _notes_with_two_actions() -> str:
    return """# 萃取筆記

## 1. 會議資訊
- **日期**：（待確認）
- **會議主題**：組織規程調整

## 2. 議題與決議
- **議題**：組織規程調整
  - *討論重點*：各股配合辦理
  - *決議*：本週五前回報

## 3. 待辦清單
| 待辦事項 | 負責人 | 期限 | 依據 |
| :--- | :--- | :--- | :--- |
| 各股回報組織規程調整情形 | 各股 | 本週五 | 科長指示 |
| 人事室公告預備缺 | 人事室 | 近日 | 科長指示 |

## 4. 待確認資訊
- 生效日期
"""


# ---------------------------------------------------------------------------
# 契約 1：分塊輸入上限改由 context 推導（不再固定 3200）
# ---------------------------------------------------------------------------

def test_large_context_transcript_is_no_longer_forced_into_3200_token_chunks():
    """128K instance 下 11,712 est 的逐字稿必須單次萃取，而不是被切成 4 塊。

    修復前：``chunk_input_budget = min(max(1200, ctx-3072-overhead), 3200)``，
    實測把 11,712 est 的逐字稿切成 3,185/3,127/3,068/2,599 四塊——單次呼叫只看得到
    全會約 18% 的上下文，「前段提議、後段定案」在萃取階段就不可能被一起推理。
    """
    service = SummarizationService()
    transcript = "字" * 11712

    plan = service._build_local_context_plan(
        transcript, settings.DEFAULT_SYSTEM_PROMPT, context_window_tokens=128000
    )

    assert plan.chunk_input_budget_tokens > 3200, (
        "128K window 下分塊預算不得仍被固定 3200 夾住（那只用掉可承載量的 2.6%）"
    )
    assert plan.needs_chunking is False
    assert plan.estimated_chunk_count == 1


def test_chunk_input_ceiling_still_configurable_and_small_context_unchanged(monkeypatch):
    """明確設定上限時仍可夾住；小 context 的推導結果不得比舊行為更嚴格。"""
    service = SummarizationService()
    transcript = "字" * 11712

    monkeypatch.setattr(settings, "LOCAL_LLM_CHUNK_INPUT_TOKENS_CEILING", 3200)
    capped = service._build_local_context_plan(
        transcript, settings.DEFAULT_SYSTEM_PROMPT, context_window_tokens=128000
    )
    assert capped.chunk_input_budget_tokens == 3200
    assert capped.needs_chunking is True

    monkeypatch.setattr(settings, "LOCAL_LLM_CHUNK_INPUT_TOKENS_CEILING", 0)
    small = service._build_local_context_plan(
        transcript, settings.DEFAULT_SYSTEM_PROMPT, context_window_tokens=8192
    )
    # 舊行為（ctx=8192）為 3200；推導值只可能略高，且不低於下限 1200
    assert 1200 <= small.chunk_input_budget_tokens <= 3400


# ---------------------------------------------------------------------------
# 契約 2：輸出上限由 context 推導（不再固定 3072）
# ---------------------------------------------------------------------------

def test_stage_output_budget_is_derived_from_context_with_ceiling(monkeypatch):
    """大 context 的輸出上限必須遠高於 3072，但受 ceiling 保護；小 context 不更嚴格。"""
    service = SummarizationService()

    monkeypatch.setattr(settings, "LOCAL_LLM_OUTPUT_TOKENS_CEILING", 8192)
    large = service._resolve_local_output_tokens(context_window=128000, prompt_tokens=5000)
    assert large == 8192, "輸出上限應吃滿 context 餘裕並停在 ceiling（舊行為固定 3072）"

    monkeypatch.setattr(settings, "LOCAL_LLM_OUTPUT_TOKENS_CEILING", 0)
    uncapped = service._resolve_local_output_tokens(context_window=128000, prompt_tokens=5000)
    assert uncapped > 8192, "ceiling=0 代表完全依 context 推導（不設上限）"

    # 小 context：不得低於歷史保留量（否則比舊行為更嚴格）
    small = service._resolve_local_output_tokens(context_window=4096, prompt_tokens=4000)
    assert small == settings.LOCAL_LLM_RESERVED_OUTPUT_TOKENS


# ---------------------------------------------------------------------------
# 契約 3：筆記零損串接（能不整併就不整併）
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_notes_within_downstream_budget_skip_lossy_merge(monkeypatch):
    """筆記總量在下游可承接範圍內時，必須零損串接、完全不呼叫整併。"""
    service = SummarizationService()
    plan = service._build_local_context_plan(
        "字" * 11712, settings.DEFAULT_SYSTEM_PROMPT, context_window_tokens=128000
    )
    merge = AsyncMock(return_value="MERGED")
    monkeypatch.setattr(service, "_merge_notes_until_fit", merge)
    monkeypatch.setattr(settings, "LOCAL_LLM_ZERO_LOSS_NOTES_PASSTHROUGH", True)

    notes = [_notes_with_two_actions(), _notes_with_two_actions()]
    result = await service._consolidate_notes("lmstudio", notes, plan, None, 128000, None)

    assert merge.await_count == 0, (
        "實測整併關卡把 8,176 tokens 截斷成 3,072（finish_reason=length，損失 47~62%）；"
        "下游接得住就不得再進有損整併"
    )
    assert result.count("# 萃取筆記") == 2, "零損串接必須保留每一份筆記的內容"
    assert "---" in result


@pytest.mark.asyncio
async def test_notes_are_still_merged_when_downstream_budget_is_small(monkeypatch):
    """小 context 導致筆記超出下游預算時，仍必須走既有整併路徑（行為不變）。"""
    service = SummarizationService()
    plan = service._build_local_context_plan(
        "字" * 11712, settings.DEFAULT_SYSTEM_PROMPT, context_window_tokens=8192
    )
    # 8192 視窗本身仍接得住這份小筆記；這裡直接把「下游可承接上限」壓到低於
    # 筆記量，逼出「必須整併」的分支（該分支的觸發條件才是本測試的主體）。
    plan.merge_feasible_input_tokens = 32
    assert plan.merge_feasible_input_tokens < service._estimate_tokens(_notes_with_two_actions())
    merge = AsyncMock(return_value="MERGED")
    monkeypatch.setattr(service, "_merge_notes_until_fit", merge)

    result = await service._consolidate_notes(
        "lmstudio", [_notes_with_two_actions()], plan, None, 8192, None
    )

    assert merge.await_count == 1
    assert result == "MERGED"


# ---------------------------------------------------------------------------
# 契約 4：最終生成／補強雙輸入（筆記＋逐字稿）
# ---------------------------------------------------------------------------

def test_final_generation_message_is_dual_input_at_large_context(monkeypatch):
    """128K context 下生成訊息必須同時帶筆記與逐字稿，並含紀錄契約規則。"""
    service = SummarizationService()
    template = get_template("section_meeting")
    monkeypatch.setattr(settings, "LOCAL_LLM_TRANSCRIPT_IN_FINAL_GENERATION", True)

    message = service._resolve_final_generation_message(
        _notes_with_two_actions(), TRANSCRIPT_LINE, settings.DEFAULT_SYSTEM_PROMPT,
        128000, template=template,
    )

    assert "原始逐字稿：" in message
    assert TRANSCRIPT_LINE in message
    assert SummarizationService.RECORD_DATE_GROUNDING_RULE in message
    assert SummarizationService.RECORD_SPEAKER_TRACEABILITY_RULE in message
    assert "各股回報組織規程調整情形" in message


def test_final_generation_message_falls_back_to_notes_only_when_context_is_small(monkeypatch):
    """context 餘裕不足（例如 num_ctx=8192 的 Ollama）時必須退回只餵筆記。"""
    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_LLM_TRANSCRIPT_IN_FINAL_GENERATION", True)

    # 8192 視窗下，一份 5,580 est 的逐字稿加筆記與系統提示已吃掉保留輸出空間，
    # 必須走降級路徑（真實 8192 情境就是這種量級的逐字稿）。
    long_transcript = TRANSCRIPT_LINE * 200
    message = service._resolve_final_generation_message(
        _notes_with_two_actions(), long_transcript, settings.DEFAULT_SYSTEM_PROMPT, 8192
    )

    assert "原始逐字稿：" not in message
    assert long_transcript not in message
    assert "各股回報組織規程調整情形" in message
    # 年份依據屬紀錄契約，降級路徑仍須保留
    assert SummarizationService.RECORD_DATE_GROUNDING_RULE in message


def test_final_generation_message_respects_transcript_toggle(monkeypatch):
    """設定關閉雙輸入時，即使 context 充足也不得附上逐字稿（可回復旋鈕）。"""
    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_LLM_TRANSCRIPT_IN_FINAL_GENERATION", False)

    message = service._resolve_final_generation_message(
        _notes_with_two_actions(), TRANSCRIPT_LINE, settings.DEFAULT_SYSTEM_PROMPT, 128000
    )

    assert "原始逐字稿：" not in message


@pytest.mark.asyncio
async def test_local_pipeline_skips_merge_and_feeds_transcript_at_large_context(monkeypatch):
    """pipeline 級：單一分塊＋筆記可承接時，呼叫數＝萃取1＋生成1（無整併）。"""
    service = SummarizationService()
    notes = _notes_with_two_actions()
    summary = (
        "會議名稱：科務會議\n"
        "時間：（待確認）\n"
        "地點：（待確認）\n"
        "主持人：科長　紀錄：AI 會議助理\n"
        "出席人員：如後附簽到表\n"
        "一、科長轉知局務會議工作報告及相關注意事項：\n"
        "1. 各股回報組織規程調整情形（科長，00:00:10）。\n"
        "二、主席裁示事項（後續管考與追蹤）：\n"
        "1. 人事室公告預備缺（科長，00:00:10）。\n"
        "散會：（待確認）\n"
    )
    # 逐次呼叫角色：1＝萃取（回筆記）、2＝最終生成（回紀錄）。用呼叫序判定，
    # 不依賴 prompt 內容比對，避免未來提示詞調整讓測試誤判。
    generated_messages: list[str] = []

    async def _fake_generate(engine, prompt, message, **kwargs):  # noqa: ANN001, ARG001
        generated_messages.append(message)
        return notes if len(generated_messages) == 1 else summary

    merge = AsyncMock(return_value="MERGED")
    monkeypatch.setattr(service, "_select_local_engine", AsyncMock(return_value="lmstudio"))
    monkeypatch.setattr(service, "_effective_context_tokens", Mock(return_value=128000))
    monkeypatch.setattr(service, "_generate_with_local_engine", _fake_generate)
    monkeypatch.setattr(service, "_merge_notes_until_fit", merge)
    # 本測試主體是「整併被略過＋最終生成看得到逐字稿」；紀錄品質驗證器
    # （動態長度閘門／出處／年份）由各自的契約測試把關，這裡隔離以免補強輪
    # 讓呼叫次數不再是 2。
    monkeypatch.setattr(service, "_validate_summary_quality", lambda *a, **k: [])
    monkeypatch.setattr(service, "_validate_cloud_speaker_traceability", lambda *a, **k: [])
    monkeypatch.setattr(service, "_validate_cloud_date_grounding", lambda *a, **k: [])

    result = await service._summarize_with_local_pipeline(
        TRANSCRIPT_LINE * 200, settings.DEFAULT_SYSTEM_PROMPT
    )

    assert merge.await_count == 0, "筆記在下游可承接時不得進有損整併"
    assert len(generated_messages) == 2, "萃取 1 次＋最終生成 1 次；無整併、無補強"
    final_message = generated_messages[1]
    assert "原始逐字稿：" in final_message, "最終生成必須看得到逐字稿（雙輸入）"
    assert "各股回報組織規程調整情形" in result


@pytest.mark.asyncio
async def test_local_pipeline_applies_dynamic_length_gate_and_cites_transcript(monkeypatch):
    """動態長度閘門：過薄紀錄必須觸發補強，且補強訊息同樣帶逐字稿。"""
    service = SummarizationService()
    notes = _notes_with_two_actions()
    thin_summary = "會議名稱：科務會議\n時間：（待確認）\n散會：（待確認）\n"
    refined_summary = (
        "會議名稱：科務會議\n"
        "時間：（待確認）\n"
        "地點：（待確認）\n"
        "主持人：科長　紀錄：AI 會議助理\n"
        "出席人員：如後附簽到表\n"
        "一、科長轉知局務會議工作報告及相關注意事項：\n"
        "1. 各股回報組織規程調整情形（科長，00:00:10）。\n"
        "二、主席裁示事項（後續管考與追蹤）：\n"
        "1. 人事室公告預備缺（科長，00:00:10）。\n"
        "散會：（待確認）\n"
    )
    generated_messages: list[str] = []

    async def _fake_generate(engine, prompt, message, **kwargs):  # noqa: ANN001, ARG001
        generated_messages.append(message)
        if len(generated_messages) == 1:
            return notes
        return thin_summary if len(generated_messages) == 2 else refined_summary

    transcript = TRANSCRIPT_LINE * 200
    # 先用真實驗證器證明「這份薄紀錄確實會被動態閘門攔下」，再以側錄方式
    # 固定後續輪次的驗證結果（第 2 次起視為已達標），避免補強輪次數不確定。
    min_chars = service._estimate_cloud_min_summary_chars(transcript)
    gate_issues = service._validate_summary_quality(
        thin_summary, notes, min_chars=min_chars
    )
    assert gate_issues, "過薄紀錄必須被動態長度閘門攔下（固定 min_chars=250 不會）"
    quality = Mock(side_effect=[gate_issues, [], []])
    monkeypatch.setattr(service, "_select_local_engine", AsyncMock(return_value="lmstudio"))
    monkeypatch.setattr(service, "_effective_context_tokens", Mock(return_value=128000))
    monkeypatch.setattr(service, "_generate_with_local_engine", _fake_generate)
    monkeypatch.setattr(service, "_merge_notes_until_fit", AsyncMock(return_value="MERGED"))
    monkeypatch.setattr(service, "_validate_summary_quality", quality)
    monkeypatch.setattr(service, "_validate_cloud_speaker_traceability", lambda *a, **k: [])
    monkeypatch.setattr(service, "_validate_cloud_date_grounding", lambda *a, **k: [])

    result = await service._summarize_with_local_pipeline(
        transcript, settings.DEFAULT_SYSTEM_PROMPT
    )

    assert len(generated_messages) == 3, "過薄紀錄必須觸發補強輪（舊行為固定 min_chars=250 不會）"
    assert "各股回報組織規程調整情形" in result
    refinement_message = generated_messages[2]
    assert "問題清單" in refinement_message
    assert "原始逐字稿" in refinement_message, "補強必須能回原文補細節（雲端 v4.3.3 同構）"


# ---------------------------------------------------------------------------
# 契約 5：補強訊息指名具體遺漏待辦（不再只給數量）
# ---------------------------------------------------------------------------

def test_missing_action_issue_names_the_specific_items():
    """遺漏待辦的問題字串必須帶具體項目名稱，否則補強輪無從下手。"""
    service = SummarizationService()
    summary = "會議名稱：科務會議\n時間：（待確認）\n散會：（待確認）\n"

    issues = service._validate_summary_quality(summary, _notes_with_two_actions())
    missing = [issue for issue in issues if "待辦事項遺漏" in issue]

    assert missing, "待辦遺漏必須被驗證捕捉"
    assert "各股回報組織規程調整情形" in missing[0]
    assert "人事室公告預備缺" in missing[0]


def test_local_pipeline_speaker_traceability_tripwire_uses_shared_contract():
    """地端亦套用發言來源絆索：正文完全沒有時間戳標註即回報問題。"""
    service = SummarizationService()
    template = get_template("section_meeting")

    without_tag = "一、科長轉知局務會議工作報告及相關注意事項：\n1. 各股配合辦理。\n"
    with_tag = "一、科長轉知局務會議工作報告及相關注意事項：\n1. 各股配合辦理（科長，00:00:10）。\n"

    assert service._validate_cloud_speaker_traceability(without_tag, template)
    assert service._validate_cloud_speaker_traceability(with_tag, template) == []
