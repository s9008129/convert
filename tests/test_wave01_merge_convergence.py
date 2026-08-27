# -*- coding: utf-8 -*-
"""T20260827-1127-01 WAVE-01c fail-first regression tests：merge 收斂契約與 tail sentinel。

涵蓋 plan.md `REGRESSION_AND_ACCEPTANCE` 第 5 組（Merge progress/data integrity）：
1. 分組預算正確性：context 可行時，merge 分組每組必須容納至少兩份目標大小
   notes（正確行為以 merge_input_budget 分組；現行程式以 900-token visible
   target（plan.notes_merge_budget_tokens）分組來源 notes → 每組只放得下一份、
   呼叫放大）。
2. Single oversized note 可壓縮：單一 note 超過 visible target 時必須允許單獨
   compaction，不得直接硬截斷。
3. 非收斂拋 stable error：模型持續回應超標內容且無實質進度時，必須在既有
   max rounds（LOCAL_LLM_MAX_MERGE_ROUNDS=3）內拋出
   `LOCAL_LLM_MERGE_NOT_CONVERGED`（WAVE-02 才會新增的 stable error code，
   尚未存在，因此以 StableServiceError + message 行為斷言，不得 top-level
   import 導致 collection error）。
4. CORE merge 無 hard truncation：merge path（含成功收斂路徑）永不呼叫
   `_truncate_to_token_budget` 省略尾端來源內容。
5. tail sentinel 不消失：無法收斂時必須拋 stable error 而非回傳「截斷後的
   成功結果」，因此 tail sentinel 不可能被無聲丟失；成功收斂路徑輸出仍含
   sentinel。

這些測試描述 WAVE-02 之後的正確行為；在現行程式上應「以正確原因失敗」
（現行程式於 summarization.py `_merge_notes_until_fit` 輪數上限/縮減停滯時
break，並在 line ~1059 無條件呼叫 `_truncate_to_token_budget` 以 hard
truncation 偽造成功，而非測試本身錯誤）。

Mock 慣例比照 tests/test_summarization_service.py 與
tests/test_t20260827_regression.py：在 `_generate_with_local_engine` 邊界
mock 模型回應（不做事實 HTTP）；呼叫 `_merge_notes_until_fit` 的參數比照
production call site（`_summarize_with_local_pipeline`）。
"""

import json
import os
import re
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

# 本測試檔必須可獨立 collect：logger 於 import 時建立 DATA_DIR/logs，
# 預設 /app/data 在 macOS 讀取失敗，故在 import backend 前備妥隔離目錄
#（比照 tests/test_api_routes.py 慣例；已在其他測試設定時不覆蓋）。
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="meetingscribe-wave01c-"))

from backend.core.config import settings
from backend.core.errors import StableServiceError
from backend.services.summarization import SummarizationService


FIXTURES = Path(__file__).parent / "fixtures"

# tail sentinel：唯一決議／待辦字串（plan CHANGE_MAP 3 的 deterministic fixture）
SENTINEL_RESOLUTION = "T20260827-SENTINEL-RESOLUTION"
SENTINEL_ACTION = "T20260827-SENTINEL-ACTION"
SENTINEL_LINE = f"決議：{SENTINEL_RESOLUTION} 待辦：{SENTINEL_ACTION}"


def _feasible_plan(service):
    """以預設有效 context（8192）建立 production LocalContextPlan。

    該 plan 的 notes_merge_budget_tokens 在 8192 context 下即為 900-token
    visible target（max(900, context - reserve - final/merge overhead)），
    與真實 LM Studio E2E 失敗時的 merge budget 語意一致。
    """
    return service._build_local_context_plan(
        "測試逐字稿",
        settings.DEFAULT_SYSTEM_PROMPT,
        context_window_tokens=settings.LOCAL_LLM_EFFECTIVE_CONTEXT_TOKENS,
    )


def _one_loaded_selection(service):
    instance = service._parse_lmstudio_loaded_instances(
        json.loads((FIXTURES / "lmstudio_one_loaded.json").read_text(encoding="utf-8"))
    )[0]
    return service._make_lmstudio_selection(instance)


def _note_with_tokens(service, marker: str, target_tokens: int, tail: str = "") -> str:
    """建構精確等於 target_tokens（依 `_estimate_tokens`）的萃取筆記 fixture。

    `tail` 置於筆記最尾端（模擬最後一份 note 的尾端決議／待辦 sentinel）。
    padding 以 CJK 字元補足，每字恰 +1 token，可精準控制大小。
    """
    header = f"# 萃取筆記（{marker}）\n\n## 議題與決議\n"
    body = "- 討論預算編列與執行進度，並確認後續分工安排。\n"
    note = header + body + tail
    deficit = target_tokens - service._estimate_tokens(note)
    if deficit > 0:
        # 補入 padding 與其換行後，other_chars//4 項可能 ±1，做一次精準校正。
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
        calls.append(
            SimpleNamespace(
                engine=engine,
                system_prompt=system_prompt,
                user_message=user_message,
                kwargs=kwargs,
            )
        )
        return responder(user_message)

    monkeypatch.setattr(service, "_generate_with_local_engine", generator)
    return calls


def _converging_responder(service):
    """收斂模型：把送入內容整併成約 450 tokens 的單份筆記，保留 sentinel。"""

    def respond(user_message: str) -> str:
        header = "# 萃取筆記\n\n## 議題與決議\n"
        body = "- 整合結論：預算編列與後續分工已確認。\n"
        tail = (SENTINEL_LINE + "\n") if SENTINEL_LINE in user_message else ""
        base = header + body + tail
        deficit = 450 - service._estimate_tokens(base)
        if deficit > 0:
            candidate = header + "整" * deficit + "\n" + body + tail
            drift = 450 - service._estimate_tokens(candidate)
            if drift:
                candidate = header + "整" * (deficit + drift) + "\n" + body + tail
            base = candidate
        return base

    return respond


def _non_converging_responder():
    """不收斂模型：每輪都回傳約 1800 tokens 的超標內容且無實質進度。

    輸入含 sentinel 時仍於輸出尾端保留 sentinel（模擬模型確實保留了決議／
    待辦，但內容持續超標），以證明現行 hard truncation 會把模型已保留的
    tail sentinel 無聲丟失。
    """

    def respond(user_message: str) -> str:
        body = "超" * 1790 + "\n"
        if SENTINEL_LINE in user_message:
            body += SENTINEL_LINE + "\n"
        return body

    return respond


def _merge_round_numbers(calls) -> list[int]:
    """從 merge user message（`_build_notes_merge_message`）解析輪數。"""
    rounds = []
    for call in calls:
        match = re.search(r"第\s*(\d+)\s*輪整併", call.user_message)
        if match:
            rounds.append(int(match.group(1)))
    return rounds


# ---------------------------------------------------------------------------
# 1. 分組預算正確性
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_merge_grouping_budget_fits_two_target_size_notes_per_group(monkeypatch):
    """Context 可行時，merge 分組每組必須容納至少兩份目標大小 notes。

    現行程式以 900-token visible target（plan.notes_merge_budget_tokens）分組
    來源 notes，每組只放得下一份 → provider 呼叫放大；正確行為是以
    merge_input_budget（context 頭空間扣除 merge prompt overhead 與 provider
    completion reserve）分組。斷言分組預算與分組結果。
    """
    service = SummarizationService()
    plan = _feasible_plan(service)
    visible_target = plan.notes_merge_budget_tokens

    # 可行性前提（plan CHANGE_MAP 1 preflight）：context 頭空間必須同時容納
    # merge prompt、至少兩份目標大小 notes 與 provider completion reserve。
    available_input = (
        plan.context_window_tokens
        - settings.LOCAL_LLM_RESERVED_OUTPUT_TOKENS
        - (service._estimate_tokens(service.LOCAL_NOTES_MERGE_PROMPT) + 250)
    )
    assert available_input >= 2 * visible_target, (
        f"測試前提不成立：context {plan.context_window_tokens} 扣除 provider "
        f"completion reserve {settings.LOCAL_LLM_RESERVED_OUTPUT_TOKENS} 與 merge "
        f"prompt overhead 後僅剩 {available_input} tokens，容不下兩份 "
        f"{visible_target}-token 目標筆記（此情境應走 preflight stable failure，"
        "非本測試範疇）"
    )

    notes = [
        _note_with_tokens(service, "A", visible_target),
        _note_with_tokens(service, "B", visible_target),
    ]
    calls = _install_merge_generator(monkeypatch, service, _converging_responder(service))

    captured = []
    original_group = service._group_texts_by_budget

    def spy_group(*args, **kwargs):
        texts = kwargs.get("texts", args[0] if args else None)
        budget = kwargs.get("budget_tokens", args[1] if len(args) > 1 else None)
        groups = original_group(*args, **kwargs)
        captured.append(
            {
                "texts": list(texts or []),
                "budget": budget,
                "groups": [list(group) for group in groups],
            }
        )
        return groups

    monkeypatch.setattr(service, "_group_texts_by_budget", spy_group)

    result = await service._merge_notes_until_fit(
        "lmstudio",
        notes,
        plan.notes_merge_budget_tokens,
        context_window_tokens=plan.context_window_tokens,
        lmstudio_selection=_one_loaded_selection(service),
    )

    assert captured, "merge 必須實際分組來源 notes 並呼叫模型整併"
    first_round = captured[0]
    assert first_round["budget"] is not None and first_round["budget"] >= 2 * visible_target, (
        f"分組預算 {first_round['budget']} 無法在單組容納兩份 {visible_target}-token "
        f"目標筆記：不應以 900-token visible target 分組來源 notes（每組只放得下"
        f"一份、呼叫放大）；context 可行（headroom {available_input} ≥ "
        f"{2 * visible_target}）時應以 merge_input_budget 分組"
    )
    group_sizes = [len(group) for group in first_round["groups"]]
    assert group_sizes and min(group_sizes) >= 2, (
        f"第一輪分組結果 {group_sizes} 有只容納一份目標大小 notes 的組別："
        "context 可行時每組必須至少容納兩份目標大小 notes"
    )
    assert len(calls) == 1, (
        f"兩份目標大小 notes 應於單組一次呼叫完成整併（不得因分組預算過小放大"
        f"呼叫），實際呼叫 {len(calls)} 次"
    )
    assert result, "merge 必須回傳整併結果"


# ---------------------------------------------------------------------------
# 2. single oversized note 可壓縮
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_single_oversized_note_compacts_alone_without_error(monkeypatch):
    """單一 note 超過 visible target 時必須允許單獨 compaction，不得直接硬截斷。

    現行程式：單份 note 形成單一 group 時 `len(note_groups) == 1 and
    len(current_notes) == 1` 直接 break，該 note 從未送模型壓縮，接著
    `_truncate_to_token_budget` 立即硬截斷（尾端內容無聲消失）。
    """
    service = SummarizationService()
    plan = _feasible_plan(service)
    visible_target = plan.notes_merge_budget_tokens
    oversized = _note_with_tokens(service, "X", visible_target + 600, tail=SENTINEL_LINE + "\n")
    assert service._estimate_tokens(oversized) > visible_target

    calls = _install_merge_generator(monkeypatch, service, _converging_responder(service))

    result = await service._merge_notes_until_fit(
        "lmstudio",
        [oversized],
        visible_target,
        context_window_tokens=plan.context_window_tokens,
    )

    assert len(calls) >= 1, (
        f"單一 oversized note（{service._estimate_tokens(oversized)} tokens > 目標 "
        f"{visible_target}）應允許單獨 compaction（至少一次模型壓縮呼叫），實際呼叫 "
        f"{len(calls)} 次——現行程式跳過壓縮直接硬截斷"
    )
    assert service._estimate_tokens(result) <= visible_target, (
        f"compaction 結果應收斂到 visible target（{visible_target} tokens）內，"
        f"實際 {service._estimate_tokens(result)} tokens"
    )
    assert SENTINEL_LINE in result, "單份 compaction 結果必須保留來源尾端 sentinel"


# ---------------------------------------------------------------------------
# 3. 非收斂拋 stable error
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_merge_non_convergence_raises_stable_error_within_max_rounds(monkeypatch):
    """模型持續超標且無實質進度時，必須在既有 max rounds 內拋 stable error。

    現行程式於縮減停滯/輪數上限時 break，改呼叫 `_truncate_to_token_budget`
    以「截斷後的成功結果」返回、不拋錯 → `pytest.raises` 以 DID NOT RAISE
    失敗，此即預期 fail 原因。`LOCAL_LLM_MERGE_NOT_CONVERGED` 為 WAVE-02
    新增 stable error（尚未存在），故以 StableServiceError + message 行為
    斷言，不得 top-level import。
    """
    service = SummarizationService()
    plan = _feasible_plan(service)
    notes = [
        _note_with_tokens(service, "A", plan.notes_merge_budget_tokens),
        _note_with_tokens(service, "B", plan.notes_merge_budget_tokens),
    ]
    calls = _install_merge_generator(monkeypatch, service, _non_converging_responder())

    with pytest.raises(StableServiceError) as excinfo:
        await service._merge_notes_until_fit(
            "lmstudio",
            notes,
            plan.notes_merge_budget_tokens,
            context_window_tokens=plan.context_window_tokens,
        )

    assert "LOCAL_LLM_MERGE_NOT_CONVERGED" in str(excinfo.value), (
        f"非收斂必須拋 LOCAL_LLM_MERGE_NOT_CONVERGED stable error，實際拋出："
        f"{str(excinfo.value)!r}"
    )
    rounds = _merge_round_numbers(calls)
    assert rounds, "merge 收斂迴圈必須實際呼叫模型"
    assert max(rounds) <= settings.LOCAL_LLM_MAX_MERGE_ROUNDS, (
        f"非收斂應在既有 max rounds（{settings.LOCAL_LLM_MAX_MERGE_ROUNDS}）內拋出 "
        f"stable error，實際跑到第 {max(rounds)} 輪"
    )


# ---------------------------------------------------------------------------
# 4. CORE merge 無 hard truncation
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_core_merge_path_never_hard_truncates(monkeypatch):
    """CORE merge path 永不呼叫 `_truncate_to_token_budget` 省略尾端來源內容。

    以 raise-spy 證明：即使是成功收斂路徑，merge 也必須完全不觸及硬截斷
    helper。現行程式 `_merge_notes_until_fit` 結尾（line ~1059）無條件呼叫
    `_truncate_to_token_budget` → spy raise AssertionError，此即預期 fail 原因
    （CORE merge path 仍觸及 hard truncation）。
    """
    service = SummarizationService()
    plan = _feasible_plan(service)
    notes = [
        _note_with_tokens(service, "A", plan.notes_merge_budget_tokens),
        _note_with_tokens(service, "B", plan.notes_merge_budget_tokens),
    ]
    _install_merge_generator(monkeypatch, service, _converging_responder(service))

    def _forbidden_truncate(*args, **kwargs):
        raise AssertionError(
            "CORE merge path 不得呼叫 _truncate_to_token_budget：merge 必須全量收斂"
            "或拋 LOCAL_LLM_MERGE_NOT_CONVERGED，不得以硬截斷省略尾端來源內容"
        )

    monkeypatch.setattr(service, "_truncate_to_token_budget", _forbidden_truncate)

    result = None
    non_convergence_error = None
    try:
        result = await service._merge_notes_until_fit(
            "lmstudio",
            notes,
            plan.notes_merge_budget_tokens,
            context_window_tokens=plan.context_window_tokens,
        )
    except StableServiceError as exc:
        # 允許的正確結束路徑：非收斂時拋 stable error（而非截斷後返回成功）。
        non_convergence_error = exc

    if non_convergence_error is not None:
        assert "LOCAL_LLM_MERGE_NOT_CONVERGED" in str(non_convergence_error), (
            f"非收斂必須拋 LOCAL_LLM_MERGE_NOT_CONVERGED，實際："
            f"{str(non_convergence_error)!r}"
        )
    else:
        assert result, "merge 收斂成功時必須回傳整併結果"


# ---------------------------------------------------------------------------
# 5. tail sentinel 不消失
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tail_sentinel_never_lost_to_truncation(monkeypatch):
    """tail sentinel 不得因 merge hard truncation 無聲消失。

    情境 A（無法收斂）：模型每輪回傳超標內容（且於輸出尾端保留 sentinel），
    merge 必須以 `LOCAL_LLM_MERGE_NOT_CONVERGED` stable error 結束——此時
    sentinel 不可能被無聲丟失；若仍返回結果，該結果必須含 sentinel。
    現行程式以「截斷後的成功結果」返回且 sentinel 消失 → 斷言失敗（預期原因）。
    情境 B（成功收斂）：輸出必須仍含 sentinel。
    """
    service = SummarizationService()
    plan = _feasible_plan(service)
    note_a = _note_with_tokens(service, "A", plan.notes_merge_budget_tokens)
    note_b = _note_with_tokens(
        service, "B", plan.notes_merge_budget_tokens, tail=SENTINEL_LINE + "\n"
    )
    assert SENTINEL_LINE in note_b, "fixture 最後一份 note 必須含 tail sentinel"

    # 情境 A：持續不收斂
    _install_merge_generator(monkeypatch, service, _non_converging_responder())
    result = None
    error = None
    try:
        result = await service._merge_notes_until_fit(
            "lmstudio",
            [note_a, note_b],
            plan.notes_merge_budget_tokens,
            context_window_tokens=plan.context_window_tokens,
        )
    except StableServiceError as exc:
        error = exc

    if error is not None:
        # 正確行為：非收斂必須以 stable error 顯式失敗（sentinel 不可能被無聲丟失）。
        assert "LOCAL_LLM_MERGE_NOT_CONVERGED" in str(error), (
            f"無法收斂時必須拋 LOCAL_LLM_MERGE_NOT_CONVERGED，實際：{str(error)!r}"
        )
    else:
        # 現行程式：硬截斷後返回成功 → sentinel 必須仍在（會失敗：sentinel 消失）。
        assert result is not None
        assert SENTINEL_LINE in result, (
            f"tail sentinel 因 merge hard truncation 無聲消失（回傳 "
            f"{service._estimate_tokens(result)} tokens 的「截斷成功」結果）；無法收斂"
            "時必須拋 LOCAL_LLM_MERGE_NOT_CONVERGED stable error，而非以截斷偽造成功"
        )

    # 情境 B：成功收斂路徑的輸出仍必須含 sentinel。
    _install_merge_generator(monkeypatch, service, _converging_responder(service))
    converged = await service._merge_notes_until_fit(
        "lmstudio",
        [note_a, note_b],
        plan.notes_merge_budget_tokens,
        context_window_tokens=plan.context_window_tokens,
    )
    assert SENTINEL_LINE in converged, "成功收斂路徑的輸出必須保留 tail sentinel"