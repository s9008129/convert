# -*- coding: utf-8 -*-
"""P4-B 忠實度絆索接線（T20260922-2037-02 §4.3）—— 契約測試（W1）。

凍結介面（handoff §4.1）：
    backend.core.fidelity_checks.analyze_fidelity(
        record_text, transcript_text, template_id) -> dict
`problems` 為可直接併入既有補強問題清單的人類可讀字串（只回報、不改寫、不刪句、
不新增提示詞）。W2 平行開發中：I-1／I-2 以 fake 模組注入（sys.modules）驗證接線；
若實體模組已落地，另加跑一條真實整合測試（`problems` 逐字過帳不變形）。

I-1（正向）：
  - problems 原樣併入補強問題清單（補強訊息必須看得到它們）且紀錄本文不變。
  - 傳入引數＝（紀錄, 逐字稿, template_id）。
  - fail-soft：檢查器丟錯／模組不存在 → 回 []、log 證據、主流程照走。
I-2（關閉＝byte 級不變）：
  - `LOCAL_FIDELITY_TRIPWIRES=False` 時**完全不呼叫**檢查器。
  - 函式級 golden：關閉時同一輸入的（紀錄＋log）與「本波前」（方法不存在）逐字相同。
雲端不變：雲端路徑原始碼不得出現本波兩個新檢查（呼叫點僅地端兩處）。
"""

import inspect
import os
import re
import sys
import tempfile
import types

# 本測試檔必須可獨立 collect：logger 於 import 時建立 DATA_DIR/logs。
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="meetingscribe-t20260923-p4b-"))

from unittest.mock import AsyncMock, Mock  # noqa: E402

import pytest  # noqa: E402
from loguru import logger as loguru_logger  # noqa: E402

import backend.core as backend_core_pkg  # noqa: E402
from backend.core.config import settings  # noqa: E402
from backend.core.templates import get_template  # noqa: E402
from backend.services.summarization import SummarizationService  # noqa: E402


TRANSCRIPT_LINE = "[00:00:10-00:00:40] 發言者1：請各股配合辦理組織規程調整，並於本週五前回報。"
TEMPLATE_ID = "section_meeting"

PROBLEM_1 = "自創專名：紀錄出現逐字稿未提及的『環境維護暨永續發展推動委員會』"
PROBLEM_2 = "數字單位：『約一萬多元』未依逐字稿寫出 800 元 × 17 人 = 13,600 元"


def _service() -> SummarizationService:
    return SummarizationService()


def _capture_logs(level: str = "DEBUG") -> tuple:
    messages: list = []
    sink_id = loguru_logger.add(lambda message: messages.append(str(message)), level=level)
    return messages, sink_id


def _without_wall_clock(text: str) -> str:
    return re.sub(r"\d+\.\d+", "<T>", text)


def _warm_glossary_cache() -> None:
    from backend.core.glossary import load_glossary

    load_glossary()


def _inject_fake_fidelity(monkeypatch, *, problems=(), raises=False, calls: list = None):
    """把 fake `backend.core.fidelity_checks` 注入 import 系統（優先於實體檔）。"""
    fake = types.ModuleType("backend.core.fidelity_checks")
    call_log = calls if calls is not None else []

    def analyze_fidelity(record_text, transcript_text, template_id=None):  # noqa: ANN001
        call_log.append({"record_text": record_text, "transcript_text": transcript_text, "template_id": template_id})
        if raises:
            raise RuntimeError("fidelity 檢查器內部錯誤（模擬）")
        return {
            "metric_version": "fidelity-test-1.0.0",
            "problems": list(problems),
            "fabricated_entities": [],
            "attribution_violations": [],
            "missing_numbers": [],
            "registry_aware_unsupported_entities": [],
            "raw_unsupported_entities": [],
        }

    fake.analyze_fidelity = analyze_fidelity
    fake.FIDELITY_METRIC_VERSION = "fidelity-test-1.0.0"
    monkeypatch.setitem(sys.modules, "backend.core.fidelity_checks", fake)
    monkeypatch.setattr(backend_core_pkg, "fidelity_checks", fake, raising=False)
    return fake, call_log


def _remove_fidelity_module(monkeypatch) -> None:
    """模擬「模組不存在」（W2 尚未落地；即使檔案已存在，sys.modules=None 亦強制 ImportError）。"""
    monkeypatch.setitem(sys.modules, "backend.core.fidelity_checks", None)
    monkeypatch.delattr(backend_core_pkg, "fidelity_checks", raising=False)


# ---------------------------------------------------------------------------
# I-1：problems 併入既有補強問題清單（原樣、不改寫、不刪句）
# ---------------------------------------------------------------------------


def test_I1_problems原樣併入且帶完整引數(monkeypatch):
    """`_validate_record_fidelity` 回傳 problems 原樣，並以（紀錄, 逐字稿, template_id）呼叫。"""
    service = _service()
    template = get_template(TEMPLATE_ID)
    _fake, calls = _inject_fake_fidelity(
        monkeypatch, problems=[PROBLEM_1, PROBLEM_2, "", None, 123, "   "]
    )

    problems = service._validate_record_fidelity("紀錄本文", "逐字稿本文", template)

    assert problems == [PROBLEM_1, PROBLEM_2], "非字串／空白一律濾除，其餘原樣（不得改寫）"
    assert len(calls) == 1
    assert calls[0]["record_text"] == "紀錄本文"
    assert calls[0]["transcript_text"] == "逐字稿本文"
    assert calls[0]["template_id"] == TEMPLATE_ID


@pytest.mark.asyncio
async def test_I1_problems進入補強訊息_紀錄本文不變(monkeypatch):
    """problems 必須看得到在補強訊息（問題清單）中；紀錄本文不得被改寫、不得刪句。

    紀錄不變以「同一輸入、開／關忠實度」兩跑的紀錄 byte 相同證明（避免把
    `_finalize_record_text` 的正常模板整形誤認為改寫）。
    """
    _warm_glossary_cache()
    notes = "## 1. 議題與決議\n- **議題**：辦公廳舍搬遷時程與經費分攤方式需再確認。\n"
    summary = "會議名稱：科務會議\n時間：（待確認）\n散會：（待確認）\n"

    with monkeypatch.context() as ctx:
        baseline_summary, _baseline_logs, _generated = await _run_local_pipeline_golden(
            ctx, prewave_stub=False, transcript=TRANSCRIPT_LINE * 200, notes=notes, summary=summary
        )
    with monkeypatch.context() as ctx:
        _inject_fake_fidelity(ctx, problems=[PROBLEM_1, PROBLEM_2])
        result, _logs, generated = await _run_local_pipeline_with_fidelity(
            ctx, transcript=TRANSCRIPT_LINE * 200, notes=notes, summary=summary
        )

    assert result == baseline_summary, "忠實度問題只回報，不得改寫或刪句（紀錄與關閉時 byte 相同）"
    assert len(generated) >= 3, "problems 必須觸發補強輪（併入既有補強問題清單）"
    refinement_message = generated[2]
    assert PROBLEM_1 in refinement_message and PROBLEM_2 in refinement_message, (
        "problems 必須原樣出現在補強訊息的問題清單中"
    )


def test_I1_檢查器丟錯時fail_soft(monkeypatch):
    """檢查器內部錯誤 → 回 []、留 log，絕不影響主流程。"""
    service = _service()
    _inject_fake_fidelity(monkeypatch, raises=True)

    messages, sink_id = _capture_logs(level="ERROR")
    try:
        problems = service._validate_record_fidelity("紀錄本文", "逐字稿本文", get_template(TEMPLATE_ID))
    finally:
        loguru_logger.remove(sink_id)

    assert problems == []
    assert any("忠實度檢查器異常" in message for message in messages), "fail-soft 必須留可追的 log"


def test_I1_模組不存在時fail_soft(monkeypatch):
    """檢查模組尚未落地（W2 平行開發中）→ 回 []，不得讓主流程失敗。"""
    service = _service()
    _remove_fidelity_module(monkeypatch)

    messages, sink_id = _capture_logs(level="WARNING")
    try:
        problems = service._validate_record_fidelity("紀錄本文", "逐字稿本文", get_template(TEMPLATE_ID))
    finally:
        loguru_logger.remove(sink_id)

    assert problems == []
    assert any("忠實度絆索已啟用但檢查模組不可用" in message for message in messages)


def test_I1_真實模組整合_problems逐字過帳不變形(monkeypatch):
    """W2 實體模組已落地時，同一 lazy import 路徑必須原樣帶回真實 `problems`。

    fake 注入驗的是接線邏輯；本測試補「真實模組」整合面（介面不漂移）：
    `_validate_record_fidelity` 的輸出必須等於 `analyze_fidelity(...)["problems"]`
    逐字原樣（不改寫、不刪句、不重排），且校準案例確實觸發至少一條問題
    （保證鑑別力）。模組未落地時 skip（W2 平行開發；不依賴 LM Studio／網路）。
    """
    fidelity_checks = pytest.importorskip("backend.core.fidelity_checks")
    monkeypatch.setattr(settings, "LOCAL_FIDELITY_TRIPWIRES", True)
    service = _service()
    record = "## 紀錄\n\n（主持人，00:00:10）今天討論禮券發放。\n"
    transcript = "[00:00:10-00:00:40] 發言者1：一個人 800 塊嘛，有 17 個人所以 13600。"

    expected = fidelity_checks.analyze_fidelity(
        record, transcript, template_id=TEMPLATE_ID
    )["problems"]
    assert expected, "校準案例應至少觸發一條問題，否則本測試沒有鑑別力"

    problems = service._validate_record_fidelity(record, transcript, get_template(TEMPLATE_ID))

    assert problems == expected, "真實模組的 problems 必須原樣（不改寫、不刪句、不重排）"


# ---------------------------------------------------------------------------
# I-2：關閉＝完全不呼叫＋函式級 golden byte 不變
# ---------------------------------------------------------------------------


def test_I2_關閉開關完全不呼叫檢查器(monkeypatch):
    """`LOCAL_FIDELITY_TRIPWIRES=False` → 檢查器一次都不得被呼叫。"""
    service = _service()
    _fake, calls = _inject_fake_fidelity(monkeypatch, problems=[PROBLEM_1])
    monkeypatch.setattr(settings, "LOCAL_FIDELITY_TRIPWIRES", False)

    problems = service._validate_record_fidelity("紀錄本文", "逐字稿本文", get_template(TEMPLATE_ID))

    assert problems == []
    assert calls == [], "關閉時完全不得呼叫 analyze_fidelity（不得有任何副作用）"


@pytest.mark.asyncio
async def test_I2_關閉時地端pipeline函式級golden(monkeypatch):
    """關閉開關 vs「本波前」：同一輸入 → 紀錄與 log 逐字相同（函式級 golden）。"""
    _warm_glossary_cache()
    transcript = TRANSCRIPT_LINE * 200
    notes = "## 1. 議題與決議\n- **議題**：辦公廳舍搬遷時程與經費分攤方式需再確認。\n"
    summary = "會議名稱：科務會議\n時間：（待確認）\n地點：（待確認）\n散會：（待確認）\n"

    with monkeypatch.context() as ctx:
        baseline_summary, baseline_logs, _calls = await _run_local_pipeline_golden(
            ctx, prewave_stub=True, transcript=transcript, notes=notes, summary=summary
        )
    with monkeypatch.context() as ctx:
        fake, calls = _inject_fake_fidelity(ctx, problems=[PROBLEM_1])
        off_summary, off_logs, _calls2 = await _run_local_pipeline_golden(
            ctx, prewave_stub=False, transcript=transcript, notes=notes, summary=summary
        )

    assert off_summary == baseline_summary, "關閉開關的紀錄必須與本波前 byte 相同"
    assert _without_wall_clock("\n".join(off_logs)) == _without_wall_clock("\n".join(baseline_logs))
    assert calls == [], "關閉開關時分析器一次都不得被呼叫"


# ---------------------------------------------------------------------------
# 雲端不變：雲端路徑不得出現本波檢查（呼叫點僅地端兩處）
# ---------------------------------------------------------------------------


def test_雲端路徑不得呼叫覆蓋率與忠實度檢查():
    """雲端生成路徑（`_summarize_with_gemini`）原始碼不得含本波兩個新檢查的呼叫。"""
    source = inspect.getsource(SummarizationService._summarize_with_gemini)

    assert "_validate_record_source_coverage" not in source, "P4-A 呼叫點僅地端兩處"
    assert "_validate_record_fidelity" not in source, "P4-B 呼叫點僅地端兩處"
    assert "_validate_cloud_date_grounding" in source, "既有雲端檢查不得被移除"


# ---------------------------------------------------------------------------
# 共用：地端 pipeline 全鏈（fake 引擎）
# ---------------------------------------------------------------------------


async def _run_local_pipeline_golden(monkeypatch, *, prewave_stub: bool, transcript: str, notes: str, summary: str):
    """跑一次地端 pipeline 並回傳（紀錄, log 行, 生成訊息）。

    `prewave_stub=True` ＝ 本波前的等效實作（忠實度方法不存在、metrics 欄位不存在）；
    `LOCAL_FIDELITY_TRIPWIRES=False` 時，本波實作必須與它逐字相同。
    """
    service = _service()
    generated: list = []
    outputs = [notes, summary]

    async def _fake_generate(engine, prompt, message, **kwargs):  # noqa: ANN001, ARG001
        generated.append(message)
        return outputs[min(len(generated) - 1, len(outputs) - 1)]

    monkeypatch.setattr(settings, "LOCAL_LLM_RECORD_COVERAGE_MODE", "off")
    monkeypatch.setattr(settings, "LOCAL_FIDELITY_TRIPWIRES", False)
    monkeypatch.setattr(service, "_select_local_engine", AsyncMock(return_value="lmstudio"))
    monkeypatch.setattr(service, "_effective_context_tokens", Mock(return_value=128000))
    monkeypatch.setattr(service, "_generate_with_local_engine", _fake_generate)
    monkeypatch.setattr(service, "_merge_notes_until_fit", AsyncMock(return_value="MERGED"))
    monkeypatch.setattr(service, "_validate_summary_quality", lambda *args, **kwargs: [])  # noqa: ARG005
    monkeypatch.setattr(service, "_validate_cloud_speaker_traceability", lambda *args, **kwargs: [])  # noqa: ARG005
    monkeypatch.setattr(service, "_validate_cloud_date_grounding", lambda *args, **kwargs: [])  # noqa: ARG005
    if prewave_stub:
        monkeypatch.setattr(service, "_validate_record_fidelity", lambda *args, **kwargs: [])  # noqa: ARG005
        monkeypatch.setattr(service, "_record_coverage_metrics_fields", lambda: "")

    messages, sink_id = _capture_logs(level="DEBUG")
    try:
        result = await service._summarize_with_local_pipeline(
            transcript, settings.DEFAULT_SYSTEM_PROMPT, template=get_template(TEMPLATE_ID)
        )
    finally:
        loguru_logger.remove(sink_id)
    return result, messages, generated


async def _run_local_pipeline_with_fidelity(monkeypatch, *, transcript: str, notes: str, summary: str):
    """同上，但忠實度**開啟**（覆蓋率關閉）＝驗證 problems 併入補強清單的行為。"""
    service = _service()
    generated: list = []
    outputs = [notes, summary, summary]

    async def _fake_generate(engine, prompt, message, **kwargs):  # noqa: ANN001, ARG001
        generated.append(message)
        return outputs[min(len(generated) - 1, len(outputs) - 1)]

    monkeypatch.setattr(settings, "LOCAL_LLM_RECORD_COVERAGE_MODE", "off")
    monkeypatch.setattr(settings, "LOCAL_FIDELITY_TRIPWIRES", True)
    monkeypatch.setattr(service, "_select_local_engine", AsyncMock(return_value="lmstudio"))
    monkeypatch.setattr(service, "_effective_context_tokens", Mock(return_value=128000))
    monkeypatch.setattr(service, "_generate_with_local_engine", _fake_generate)
    monkeypatch.setattr(service, "_merge_notes_until_fit", AsyncMock(return_value="MERGED"))
    monkeypatch.setattr(service, "_validate_summary_quality", lambda *args, **kwargs: [])  # noqa: ARG005
    monkeypatch.setattr(service, "_validate_cloud_speaker_traceability", lambda *args, **kwargs: [])  # noqa: ARG005
    monkeypatch.setattr(service, "_validate_cloud_date_grounding", lambda *args, **kwargs: [])  # noqa: ARG005

    messages, sink_id = _capture_logs(level="DEBUG")
    try:
        result = await service._summarize_with_local_pipeline(
            transcript, settings.DEFAULT_SYSTEM_PROMPT, template=get_template(TEMPLATE_ID)
        )
    finally:
        loguru_logger.remove(sink_id)
    return result, messages, generated
