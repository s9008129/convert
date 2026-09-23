# -*- coding: utf-8 -*-
"""P7-A（T20260923-1700-03）：地端補強輪「不回退」守衛 —— 契約測試。

對應計畫 `.agent/tasks/T20260923-1700-03-local-refine-no-regress/plan.md` §4-A：

- **CORE-1**：`LOCAL_LLM_REFINEMENT_NO_REGRESSION`（預設 `True`）＝交付本次執行中
  **核心覆蓋率最佳**的那一版；某輪把核心未涵蓋數弄多 ⇒ 丟棄該輪輸出（同分取最後一版）。
  根因證據：gemma 場同一場三次對帳 = 數字未涵蓋 `3 → 0 → 又 1`（第 1 輪補回 600 元、
  第 2 輪又把它寫掉；`data/cache/e2e/p6a-gemma31b-e6/backend.log:328／421／511`）。
- **CORE-2**：比較基準只有核心覆蓋率；`off` 模式（逐條對帳未執行）⇒ 守衛完全不作用。
- **CORE-3**：觸發必須留下可查核的 `log.warning`。
- **一致性**：回退後問題清單與 `cov_*` 必須跟著重算（log 不得與實際交付版本不符）。
- **回退開關**：`False` ＝ 一行回本波前（交付最後一版，且不產生任何守衛 log）。
"""

import os
import re
import tempfile

# 本測試檔必須可獨立 collect：logger 於 import 時建立 DATA_DIR/logs，
# 預設 /app/data 在 macOS 讀取失敗，故在 import backend 前備妥隔離目錄。
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="meetingscribe-p7a-"))

from unittest.mock import AsyncMock, Mock  # noqa: E402

import pytest  # noqa: E402
from loguru import logger as loguru_logger  # noqa: E402

from backend.core.config import settings  # noqa: E402
from backend.core.templates import get_template  # noqa: E402
from backend.services.summarization import SummarizationService  # noqa: E402

NOTES = "## 1. 議題與決議\n- **議題**：測試用議題（本檔不驗解析，只驗守衛）。\n"
TRANSCRIPT = "[00:00:00-00:00:20] 發言者1：測試發言。\n" * 5

# 三個「版本」＝三次整份生成的字串（守衛只比內容，不比模型名／引擎）。
V1 = "# 會議紀錄\n\n內容版本一\n"
V2 = "# 會議紀錄\n\n內容版本二\n"
V3 = "# 會議紀錄\n\n內容版本三\n"

REVERT_WARNING = "丟棄本輪輸出，交付最佳版本"


def _service() -> SummarizationService:
    return SummarizationService()


def _capture_logs(level: str = "DEBUG") -> tuple:
    messages: list = []
    sink_id = loguru_logger.add(lambda message: messages.append(str(message)), level=level)
    return messages, sink_id


def _version_of(text: str) -> str:
    """由紀錄內容認版本（不依賴呼叫次序，回退後重算才會得到同一個答案）。"""
    for marker in ("版本一", "版本二", "版本三"):
        if marker in text:
            return marker
    return "unknown"


async def _run(
    monkeypatch,
    *,
    outputs: list,
    coverage_by_version: dict,
    quality_by_version: dict,
    no_regression=None,
    coverage_mode: str = "observe",
    coverage_stateful=None,
    prewave_stub: bool = False,
) -> tuple:
    """跑一次地端 pipeline；覆蓋率／品質驗證以「內容 → 腳本值」對應，其餘驗證器隔離。"""
    service = _service()
    generated: list = []

    async def _fake_generate(engine, prompt, message, **kwargs):  # noqa: ANN001, ARG001
        generated.append(message)
        return outputs[min(len(generated) - 1, len(outputs) - 1)]

    monkeypatch.setattr(settings, "LOCAL_LLM_RECORD_COVERAGE_MODE", coverage_mode)
    monkeypatch.setattr(settings, "LOCAL_FIDELITY_TRIPWIRES", False)
    if no_regression is not None:
        monkeypatch.setattr(settings, "LOCAL_LLM_REFINEMENT_NO_REGRESSION", no_regression)
    monkeypatch.setattr(service, "_select_local_engine", AsyncMock(return_value="lmstudio"))
    monkeypatch.setattr(service, "_effective_context_tokens", Mock(return_value=128000))
    monkeypatch.setattr(service, "_generate_with_local_engine", _fake_generate)
    monkeypatch.setattr(service, "_merge_notes_until_fit", AsyncMock(return_value="MERGED"))
    if prewave_stub:
        # 「本波前」的程式碼路徑：沒有守衛、也取不到快照（等價於守衛不作用）。
        monkeypatch.setattr(service, "_core_coverage_snapshot", lambda: None)
    monkeypatch.setattr(service, "_finalize_record_text", lambda text, **kwargs: text)  # noqa: ARG005
    monkeypatch.setattr(
        service,
        "_validate_summary_quality",
        lambda *args, **kwargs: list(quality_by_version.get(_version_of(args[0]), [])),  # noqa: ARG005
    )
    monkeypatch.setattr(service, "_validate_cloud_speaker_traceability", lambda *a, **k: [])  # noqa: ARG005
    monkeypatch.setattr(service, "_validate_cloud_date_grounding", lambda *a, **k: [])  # noqa: ARG005

    coverage_calls: list = []

    def _fake_coverage(summary, notes, transcript, template=None):  # noqa: ANN001, ARG001
        coverage_calls.append(_version_of(summary))
        if coverage_stateful is not None:
            stats = coverage_stateful(summary, len(coverage_calls))
        else:
            scripted = coverage_by_version.get(_version_of(summary), {})
            stats = {
                "expected": scripted.get("expected", 0),
                "missing": scripted.get("missing", 0),
                "items": scripted.get("items", []),
            }
        service._record_coverage_stats = {
            "expected_topic": stats.get("expected", 0),
            "missing_topic": stats.get("missing", 0),
            "missing_items_topic": list(stats.get("items", [])),
            "expected_decision": 0,
            "missing_decision": 0,
            "expected_number": 0,
            "missing_number": 0,
            "expected_date": 0,
            "missing_date": 0,
            "issues_added": 1 if stats.get("missing") else 0,
        }
        if not stats.get("expected"):
            service._record_coverage_stats = {}
        return []

    monkeypatch.setattr(service, "_validate_record_source_coverage", _fake_coverage)

    messages, sink_id = _capture_logs(level="DEBUG")
    try:
        result = await service._summarize_with_local_pipeline(
            TRANSCRIPT, settings.DEFAULT_SYSTEM_PROMPT, template=get_template("section_meeting")
        )
    finally:
        loguru_logger.remove(sink_id)
    return service, result, generated, messages


def _without_wall_clock(text: str) -> str:
    """遮罩 wall-clock 欄位（`:.1f` 秒數）——對照唯一允許的非確定性欄位。"""
    return re.sub(r"\d+\.\d+", "<T>", text)


# ---------------------------------------------------------------------------
# T-01 ~ T-03：守衛的判定（回退／不回退／同分）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_T01_某輪把核心未涵蓋數弄多_改交付最佳版本(monkeypatch):
    """實測情境（gemma 場 `3 → 0 → 又 1` 的同構）：第 2 輪變差 ⇒ 交付第 1 輪的版本。"""
    service, result, generated, messages = await _run(
        monkeypatch,
        outputs=[NOTES, V1, V2, V3],
        coverage_by_version={
            "版本一": {"expected": 10, "missing": 2, "items": ["項目A", "項目B"]},
            "版本二": {"expected": 10, "missing": 1, "items": ["項目A"]},
            "版本三": {"expected": 10, "missing": 3, "items": ["項目A", "項目B", "項目C"]},
        },
        quality_by_version={"版本一": ["問題A"], "版本二": ["問題B"], "版本三": ["問題C"]},
    )

    assert "版本二" in result, "必須交付核心未涵蓋數最少的版本（不是最後一版）"
    assert "版本三" not in result
    assert [line for line in messages if REVERT_WARNING in line], "觸發必須留下 WARNING（可查核）"
    assert generated, "生成訊息不得因守衛而消失"


@pytest.mark.asyncio
async def test_T02_覆蓋率逐輪改善_不得誤回退(monkeypatch):
    """`2 → 1 → 0`：每一輪都更好 ⇒ 交付最後一版（守衛不得把正常補強擋掉）。"""
    service, result, generated, messages = await _run(
        monkeypatch,
        outputs=[NOTES, V1, V2, V3],
        coverage_by_version={
            "版本一": {"expected": 10, "missing": 2, "items": ["項目A", "項目B"]},
            "版本二": {"expected": 10, "missing": 1, "items": ["項目A"]},
            "版本三": {"expected": 10, "missing": 0, "items": []},
        },
        quality_by_version={"版本一": ["問題A"], "版本二": ["問題B"], "版本三": ["問題C"]},
    )

    assert "版本三" in result
    assert not [line for line in messages if REVERT_WARNING in line], "沒有變差就不得回退"
    assert len(generated) == 4, "萃取 1＋初稿 1＋補強 2 輪"


@pytest.mark.asyncio
async def test_T03_同分取最後一版(monkeypatch):
    """同分（未涵蓋數相同）⇒ 取本輪（後一版通常修掉其他問題），不得為同分回退。"""
    _, result, _, messages = await _run(
        monkeypatch,
        outputs=[NOTES, V1, V2, V3],
        coverage_by_version={
            "版本一": {"expected": 10, "missing": 2, "items": ["項目A", "項目B"]},
            "版本二": {"expected": 10, "missing": 2, "items": ["項目A", "項目B"]},
            "版本三": {"expected": 10, "missing": 2, "items": ["項目A", "項目B"]},
        },
        quality_by_version={"版本一": ["問題A"], "版本二": ["問題B"], "版本三": ["問題C"]},
    )

    assert "版本三" in result
    assert not [line for line in messages if REVERT_WARNING in line]
    assert [line for line in messages if "（持平，取本輪）" in line], "持平必須留下觀測紀錄"


# ---------------------------------------------------------------------------
# T-04 ~ T-06：開關回退、不可比與一致性
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_T04_開關關閉_交付最後一版且無守衛log(monkeypatch):
    """`LOCAL_LLM_REFINEMENT_NO_REGRESSION=False`：一行回本波前（交付最後一版）。"""
    _, result, _, messages = await _run(
        monkeypatch,
        outputs=[NOTES, V1, V2, V3],
        coverage_by_version={
            "版本一": {"expected": 10, "missing": 2, "items": ["項目A", "項目B"]},
            "版本二": {"expected": 10, "missing": 1, "items": ["項目A"]},
            "版本三": {"expected": 10, "missing": 3, "items": ["項目A", "項目B", "項目C"]},
        },
        quality_by_version={"版本一": ["問題A"], "版本二": ["問題B"], "版本三": ["問題C"]},
        no_regression=False,
    )

    assert "版本三" in result, "關閉開關＝交付最後一版（與本波前相同）"
    assert not [line for line in messages if REVERT_WARNING in line]
    assert not [line for line in messages if "不回退守衛" in line], "關閉時不得產生任何守衛 log"


@pytest.mark.asyncio
async def test_T05_逐條對帳未執行_守衛不作用(monkeypatch):
    """`LOCAL_LLM_RECORD_COVERAGE_MODE=off`（取不到快照）⇒ 守衛不作用、交付最後一版。"""
    service, result, _, messages = await _run(
        monkeypatch,
        outputs=[NOTES, V1, V2, V3],
        coverage_by_version={},
        quality_by_version={"版本一": ["問題A"], "版本二": ["問題B"], "版本三": ["問題C"]},
        coverage_mode="off",
    )

    assert service._core_coverage_snapshot() is None
    assert "版本三" in result
    # P7-B §8（T20260923-1810-01）：這裡過去是本專案唯一「靜默停用」的守衛路徑——
    # 開關開著、卻因取不到快照而完全不作用，實機（Windows／Ollama）無法分辨
    # 「評估後放行」與「根本沒跑」。本波改為留下 skip-reason 觀測（observation-only，
    # 不改交付結果、不改 metrics），因此斷言由「不得有 log」改為「必須有 skip-reason」。
    assert [line for line in messages if "skipped_reason=coverage_mode_off" in line], (
        "P7-B §8：守衛未評估必須留下 skip-reason 觀測"
    )
    assert not [line for line in messages if REVERT_WARNING in line]
    assert service._record_coverage_metrics_fields() == "", "off 模式的 metrics 必須維持空字串"


@pytest.mark.asyncio
async def test_T06_期望集合改變_不可比即停用比較(monkeypatch):
    """期望集合（對帳基準）改變 ⇒ 未涵蓋數不可比，不得據此回退（寧可不作用也不誤傷）。"""
    _, result, _, messages = await _run(
        monkeypatch,
        outputs=[NOTES, V1, V2, V3],
        coverage_by_version={
            "版本一": {"expected": 10, "missing": 2, "items": ["項目A", "項目B"]},
            "版本二": {"expected": 9, "missing": 1, "items": ["項目A"]},
            "版本三": {"expected": 9, "missing": 1, "items": ["項目A"]},
        },
        quality_by_version={"版本一": ["問題A"], "版本二": ["問題B"], "版本三": ["問題C"]},
    )

    assert [line for line in messages if "基準不同不可比" in line], "必須留下停用比較的觀測紀錄"
    assert not [line for line in messages if REVERT_WARNING in line]
    assert "版本三" in result


@pytest.mark.asyncio
async def test_T07_回退後問題清單與cov欄位對齊交付版本(monkeypatch):
    """回退後必須用同一組檢查重算 ⇒ `cov_*` 與殘餘問題講的是「真正交付的那一版」。"""
    service, result, _, messages = await _run(
        monkeypatch,
        outputs=[NOTES, V1, V2, V3],
        coverage_by_version={
            "版本一": {"expected": 10, "missing": 2, "items": ["項目A", "項目B"]},
            "版本二": {"expected": 10, "missing": 1, "items": ["項目A"]},
            "版本三": {"expected": 10, "missing": 3, "items": ["項目A", "項目B", "項目C"]},
        },
        quality_by_version={"版本一": ["問題A"], "版本二": ["問題B"], "版本三": ["問題C"]},
    )

    assert "版本二" in result
    assert "cov_missing_topic=1" in service._record_coverage_metrics_fields()
    residual = [line for line in messages if "本地摘要仍有待補強問題" in line]
    assert residual, "交付版本仍有殘餘問題時必須照實記錄"
    assert "問題B" in residual[-1] and "問題C" not in residual[-1], (
        "殘餘問題必須屬於交付版本，不得留下『log 說缺、實際不缺』的假象"
    )


@pytest.mark.asyncio
async def test_T08_執行中快照消失_停用比較並如實記錄(monkeypatch):
    """防禦路徑：第 2 次之後取不到快照（逐條對帳忽然不執行）⇒ 停用比較、交付最後一版。"""
    _, result, _, messages = await _run(
        monkeypatch,
        outputs=[NOTES, V1, V2, V3],
        coverage_by_version={},
        quality_by_version={"版本一": ["問題A"], "版本二": ["問題B"], "版本三": ["問題C"]},
        coverage_stateful=lambda summary, call_index: (
            {"expected": 10, "missing": 2} if call_index == 1 else {"expected": 0, "missing": 0}
        ),
    )

    assert [line for line in messages if "取不到核心覆蓋快照" in line]
    assert not [line for line in messages if REVERT_WARNING in line]
    assert "版本三" in result


# ---------------------------------------------------------------------------
# T-11 ~ T-12：等量互換與「本波前」等價
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_T11_未涵蓋數相同但換項_視為回退(monkeypatch):
    """等量互換（補回一項、掉另一項）＝實測痛點同型（gemma 決議類）⇒ 必須視為回退。

    只比計數會漏掉這個情況（未涵蓋數 1 → 1），故守衛另比「未涵蓋項目身分集合」。
    """
    _, result, _, messages = await _run(
        monkeypatch,
        outputs=[NOTES, V1, V2, V3],
        coverage_by_version={
            "版本一": {"expected": 10, "missing": 1, "items": ["項目A"]},
            "版本二": {"expected": 10, "missing": 1, "items": ["項目B"]},
            "版本三": {"expected": 10, "missing": 1, "items": ["項目B"]},
        },
        quality_by_version={"版本一": ["問題A"], "版本二": ["問題B"], "版本三": ["問題C"]},
    )

    assert "版本一" in result, "第 1 輪把原本已寫到的事實換掉 ⇒ 必須交付換掉之前的版本"
    swapped = [line for line in messages if "等量互換" in line]
    assert swapped and REVERT_WARNING in swapped[-1]


@pytest.mark.asyncio
async def test_T12_關閉開關等同本波前程式碼路徑(monkeypatch):
    """`no_regression=False` ≡ 沒有守衛的程式碼路徑（pre-wave stub）：產物與 log 逐字相同。"""
    script = {
        "outputs": [NOTES, V1, V2, V3],
        "coverage_by_version": {
            "版本一": {"expected": 10, "missing": 2, "items": ["項目A", "項目B"]},
            "版本二": {"expected": 10, "missing": 1, "items": ["項目A"]},
            "版本三": {"expected": 10, "missing": 3, "items": ["項目A", "項目B", "項目C"]},
        },
        "quality_by_version": {"版本一": ["問題A"], "版本二": ["問題B"], "版本三": ["問題C"]},
    }

    _, off_result, off_generated, off_messages = await _run(
        monkeypatch, **script, no_regression=False
    )
    with monkeypatch.context() as ctx:
        _, pre_result, pre_generated, pre_messages = await _run(ctx, **script, prewave_stub=True)

    assert off_result == pre_result, "關閉開關的交付內容必須與沒有守衛時相同"
    assert off_generated == pre_generated, "生成訊息序列不得因守衛而改變"
    assert _without_wall_clock("\n".join(off_messages)) == _without_wall_clock(
        "\n".join(pre_messages)
    ), "關閉開關的 log 必須與沒有守衛時逐字相同（wall-clock 除外）"


# ---------------------------------------------------------------------------
# T-09 ~ T-10：真實 `_validate_record_source_coverage` 的快照語意
# ---------------------------------------------------------------------------

COVERAGE_NOTES = (
    "## 1. 議題與決議\n"
    "- **議題**：辦公廳舍搬遷時程與經費分攤方式需再確認。\n"
    "  - *決議*：請總務股於下週三前提出搬遷經費分攤表。\n"
)
COVERAGE_TRANSCRIPT = (
    "[00:00:00-00:00:20] 發言者1：今年文康禮券 600 元，共 17 人。\n"
    "[00:00:20-00:00:40] 發言者2：相關作業請於 11月1日 前完成。\n"
)
COVERAGE_RECORD = "會議名稱：科務會議\n時間：中華民國114年9月3日\n"


def test_T09_observe模式仍供快照_守衛才能在觀察場運作(monkeypatch):
    """`observe` 不把問題交給補強清單，但統計照算 ⇒ 快照非 None（守衛可運作）。"""
    monkeypatch.setattr(settings, "LOCAL_LLM_RECORD_COVERAGE_MODE", "observe")
    service = _service()

    issues = service._validate_record_source_coverage(
        COVERAGE_RECORD, COVERAGE_NOTES, COVERAGE_TRANSCRIPT
    )

    assert issues == [], "observe 模式的品質必須零變化（不產生補強問題）"
    snapshot = service._core_coverage_snapshot()
    assert snapshot is not None, "observe 也必須供給快照，否則守衛在觀察場形同不存在"
    assert snapshot[1] > 0 and snapshot[0] > 0, "此 fixture 應有期望項且尚未涵蓋"


def test_T10_off模式不供快照_守衛完全不作用(monkeypatch):
    """`off`：完全不跑（無 log／無 metrics／無快照）＝一行回本波前。"""
    monkeypatch.setattr(settings, "LOCAL_LLM_RECORD_COVERAGE_MODE", "off")
    service = _service()

    issues = service._validate_record_source_coverage(
        COVERAGE_RECORD, COVERAGE_NOTES, COVERAGE_TRANSCRIPT
    )

    assert issues == []
    assert service._core_coverage_snapshot() is None
    assert service._record_coverage_metrics_fields() == ""
