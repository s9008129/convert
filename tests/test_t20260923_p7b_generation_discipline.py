# -*- coding: utf-8 -*-
"""P7-B（T20260923-1810-01）CORE-2a：地端生成紀律三開關契約測試。

對應計畫 `.agent/tasks/T20260923-1810-01-local-record-fidelity-density/plan.md`（rev4 §4、§8、§9.1）：

- **雲端 byte 不變（凍結介面；審查 I10）**：共用常數 `LOCAL_EXTRACTION_PROMPT`
  一字不改（`CLOUD_EXTRACTION_PROMPT` 直接串接它），三條紀律只以「地端專屬區塊」
  追加，且只在 `mode="local"` 注入 ⇒ 雲端三支提示詞（萃取／生成／補強）
  在三開關任何組合下 **byte 完全相同**。
- **地端逐條可關**：`LOCAL_LLM_ONEPERITEM_RULE`／`LOCAL_LLM_SPEAKER_DISCIPLINE_RULE`／
  `LOCAL_LLM_ANTI_DUPLICATE_RULE` 各自生效；三條全關 ⇒ 地端訊息與開啟時的差異
  **只有**紀律區塊（byte 級可回退）。
- **補強輪覆蓋**：補強 builder `_build_record_refinement_message(mode="local")` 同樣注入，
  避免補強把紀律重置（rev3 之前的缺口）。
- **跨引擎同碼路徑（§8 ②）**：`engine="lmstudio"` 與 `engine="ollama"` 走同一條
  `_summarize_with_local_pipeline`，捕獲到的生成／補強訊息都帶上三條紀律。
- **跨 OS（§8）**：本波新增的程式碼不得出現平台／模型名判斷。
"""

import os
import tempfile

# 本測試檔必須可獨立 collect：logger 於 import 時建立 DATA_DIR/logs。
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="meetingscribe-p7b-c2a-"))

import inspect  # noqa: E402
from types import SimpleNamespace  # noqa: E402

import pytest  # noqa: E402

from backend.core.config import settings  # noqa: E402
from backend.core.templates import get_template  # noqa: E402
from backend.services.summarization import SummarizationService  # noqa: E402

SWITCHES = (
    "LOCAL_LLM_ONEPERITEM_RULE",
    "LOCAL_LLM_SPEAKER_DISCIPLINE_RULE",
    "LOCAL_LLM_ANTI_DUPLICATE_RULE",
)

NOTES = (
    "# 萃取筆記\n\n## 1. 會議資訊\n- **日期**：2026-09-03\n\n"
    "## 3. 待辦清單\n| 待辦事項 | 負責人 | 期限 | 依據 |\n"
    "| :--- | :--- | :--- | :--- |\n| 場勘 | 事務股 | 9/10 | 逐字稿 |\n"
)
TRANSCRIPT = "[00:00:00-00:00:30] 發言者1：請事務股於 9 月 10 日前完成場勘。"


def _service() -> SummarizationService:
    return SummarizationService()


def _set_switches(monkeypatch, value: bool) -> None:
    for name in SWITCHES:
        monkeypatch.setattr(settings, name, value)


def _rule_texts(service: SummarizationService) -> tuple:
    return (
        service.LOCAL_RECORD_ONEPERITEM_RULE,
        service.LOCAL_RECORD_SPEAKER_DISCIPLINE_RULE,
        service.LOCAL_RECORD_ANTI_DUPLICATE_RULE,
    )


def _messages(service: SummarizationService, mode: str) -> SimpleNamespace:
    template = get_template("section_meeting")
    return SimpleNamespace(
        generation=service._build_record_generation_message(
            NOTES, TRANSCRIPT, template=template, mode=mode
        ),
        refinement=service._build_record_refinement_message(
            "目前版本", NOTES, ["議題遺漏 1 項"], TRANSCRIPT, template=template, mode=mode
        ),
        extraction=(
            service._local_extraction_prompt(template)
            if mode == "local"
            else service._cloud_extraction_prompt(template)
        ),
    )


def test_cloud_prompts_byte_stable_across_all_switch_combinations(monkeypatch):
    """I10 契約：雲端萃取／生成／補強三支提示詞在三開關任何組合下 byte 不變。"""
    service = _service()
    _set_switches(monkeypatch, True)
    enabled = _messages(service, "cloud")
    _set_switches(monkeypatch, False)
    disabled = _messages(service, "cloud")

    for field in ("generation", "refinement", "extraction"):
        assert getattr(enabled, field) == getattr(disabled, field), (
            f"雲端 {field} 提示詞被地端開關改動（凍結介面違反）"
        )
    for rule in _rule_texts(service) + (service.LOCAL_EXTRACTION_ONEPERITEM_RULE,):
        assert rule not in enabled.generation
        assert rule not in enabled.refinement
        assert rule not in enabled.extraction


def test_shared_extraction_constant_is_untouched():
    """I10 契約：共用常數不得被就地改寫（雲端 `CLOUD_EXTRACTION_PROMPT` 串接它）。"""
    service = _service()
    assert service.CLOUD_EXTRACTION_PROMPT.startswith(service.LOCAL_EXTRACTION_PROMPT)
    for rule in _rule_texts(service) + (service.LOCAL_EXTRACTION_ONEPERITEM_RULE,):
        assert rule not in service.LOCAL_EXTRACTION_PROMPT
        assert rule not in service.CLOUD_EXTRACTION_PROMPT


def test_local_generation_and_refinement_get_all_three_rules(monkeypatch):
    """地端（mode="local"）生成與補強都必須帶三條紀律（補強不得重置紀律）。"""
    service = _service()
    _set_switches(monkeypatch, True)
    local = _messages(service, "local")
    for field in ("generation", "refinement"):
        for rule in _rule_texts(service):
            assert rule in getattr(local, field), f"{field} 缺少紀律：{rule[:16]}…"


def test_local_extraction_prompt_gets_oneperitem_scope_rule(monkeypatch):
    """地端萃取側只加「拆細只適用於待辦表格」；關閉時 byte 回共用常數＋模板增補。"""
    service = _service()
    template = get_template("section_meeting")
    extra = template.extraction_prompt_extra if template else ""

    _set_switches(monkeypatch, True)
    enabled = service._local_extraction_prompt(template)
    assert service.LOCAL_EXTRACTION_ONEPERITEM_RULE in enabled

    _set_switches(monkeypatch, False)
    disabled = service._local_extraction_prompt(template)
    assert disabled == service.LOCAL_EXTRACTION_PROMPT + extra, (
        "全關時地端萃取提示詞必須 byte 級回共用常數＋模板增補"
    )


@pytest.mark.parametrize("switch", SWITCHES)
def test_each_switch_is_independently_toggleable(monkeypatch, switch):
    """三條各自可關：只關一條時，其餘兩條仍在、該條消失。"""
    service = _service()
    rule_of = {
        "LOCAL_LLM_ONEPERITEM_RULE": service.LOCAL_RECORD_ONEPERITEM_RULE,
        "LOCAL_LLM_SPEAKER_DISCIPLINE_RULE": service.LOCAL_RECORD_SPEAKER_DISCIPLINE_RULE,
        "LOCAL_LLM_ANTI_DUPLICATE_RULE": service.LOCAL_RECORD_ANTI_DUPLICATE_RULE,
    }
    _set_switches(monkeypatch, True)
    monkeypatch.setattr(settings, switch, False)
    message = _messages(service, "local").generation

    assert rule_of[switch] not in message, f"{switch} 關閉後仍注入"
    for other, rule in rule_of.items():
        if other != switch:
            assert rule in message, f"{switch} 關閉時誤刪 {other}"


def test_discipline_is_the_only_local_delta(monkeypatch):
    """三條全關時，地端訊息與開啟時的差異**只有**紀律區塊（byte 級可回退）。"""
    service = _service()
    template = get_template("section_meeting")
    _set_switches(monkeypatch, True)
    on_generation = service._build_record_generation_message(
        NOTES, TRANSCRIPT, template=template, mode="local"
    )
    on_refinement = service._build_record_refinement_message(
        "目前版本", NOTES, ["議題遺漏 1 項"], TRANSCRIPT, template=template, mode="local"
    )
    block = service._local_record_discipline_rule("local")
    assert block, "前置條件：三開關全開時紀律區塊不得為空"

    _set_switches(monkeypatch, False)
    off_generation = service._build_record_generation_message(
        NOTES, TRANSCRIPT, template=template, mode="local"
    )
    off_refinement = service._build_record_refinement_message(
        "目前版本", NOTES, ["議題遺漏 1 項"], TRANSCRIPT, template=template, mode="local"
    )

    assert on_generation.replace(block, "") == off_generation
    assert on_refinement.replace(block, "") == off_refinement


def test_no_platform_or_model_branching_in_new_code():
    """§8：本波新增程式碼不得以平台或模型名分流（LM Studio／Ollama／macOS／Windows 同碼路徑）。"""
    for func in (
        SummarizationService._local_record_discipline_rule,
        SummarizationService._local_extraction_discipline_rule,
        SummarizationService._local_extraction_prompt,
    ):
        source = inspect.getsource(func).lower()
        for forbidden in ("platform.system", "sys.platform", "os.name", "darwin", "win32"):
            assert forbidden not in source, f"{func.__name__} 出現平台分流：{forbidden}"
        for model_name in ("gemma", "qwen", "llama", "mistral"):
            assert model_name not in source, f"{func.__name__} 出現模型名分流：{model_name}"


@pytest.mark.asyncio
@pytest.mark.parametrize("engine", ["lmstudio", "ollama"])
async def test_local_pipeline_discipline_is_engine_independent(monkeypatch, engine):
    """§8 ②：engine="lmstudio" 與 engine="ollama" 走同一條管線，生成／補強都帶三條紀律。"""
    service = _service()
    _set_switches(monkeypatch, True)
    template = get_template("section_meeting")

    async def _select() -> str:
        return engine

    monkeypatch.setattr(service, "_select_local_engine", _select)

    captured: list = []

    async def generator(engine_id, system_prompt, user_message, **kwargs):
        captured.append((engine_id, user_message))
        if "請直接輸出以下 Markdown" in user_message:
            return NOTES
        if "整併" in user_message:
            return NOTES
        return (
            "一、主席報告\n（一）場勘作業（發言者1，00:00:05）\n"
            "1、請事務股於 9 月 10 日前完成場勘（發言者1，00:00:05）。\n"
        )

    monkeypatch.setattr(service, "_generate_with_local_engine", generator)

    await service._summarize_with_local_pipeline(
        TRANSCRIPT, settings.DEFAULT_SYSTEM_PROMPT, template=template
    )

    assert captured, "前置條件：管線必須至少呼叫一次模型邊界"
    assert all(engine_id == engine for engine_id, _ in captured)

    generation_messages = [
        message
        for _, message in captured
        if "輸出最終版本的會議記錄" in message or "請根據問題清單重新輸出完整版本" in message
    ]
    assert generation_messages, "前置條件：必須捕獲到生成或補強訊息"
    for message in generation_messages:
        for rule in _rule_texts(service):
            assert rule in message

