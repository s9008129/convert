# -*- coding: utf-8 -*-
"""P7-B（T20260923-1810-01）：萃取階段結構性分塊（CORE-1b）與筆記落檔（CORE-1a）契約測試。

對應計畫 `.agent/tasks/T20260923-1810-01-local-record-fidelity-density/plan.md`（rev3）：

- **CORE-1b｜結構性分塊萃取**：`LOCAL_LLM_EXTRACTION_CHUNK_CEILING_TOKENS`（預設 6000）
  把「依 context 推導」的分塊上限夾住 ⇒ 長逐字稿恢復「每個區段都有自己的萃取呼叫」。
  契約：實際上限＝`min(依 context 推導值, 本上限)`；**0＝停用＝逐字等於本波前**。
  根因實測：LM Studio instance context 71,936 tokens 對 11,711 est tokens 的逐字稿
  只跑 1 次萃取（`chunk_count=1`），gemma 4 31B 連續兩場缺同一組尾段核心事實。
- **CORE-1a｜萃取筆記落檔**：`LOCAL_LLM_DUMP_EXTRACTION_NOTES`（預設 `False`）
  開啟時把原始各塊筆記與零損串接後筆記寫入 `<DATA_DIR>/debug/extraction-notes/`。
  契約：**不改任何產品輸出**；關閉時不得建立任何檔案／目錄；寫入失敗不得影響流程。
"""

import os
import tempfile

# 本測試檔必須可獨立 collect：logger 於 import 時建立 DATA_DIR/logs，
# 預設 /app/data 在 macOS 讀取失敗，故在 import backend 前備妥隔離目錄。
os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="meetingscribe-p7b-"))

from pathlib import Path  # noqa: E402

import pytest  # noqa: E402

from backend.core.config import settings  # noqa: E402
from backend.core.templates import get_template  # noqa: E402
from backend.services.summarization import SummarizationService  # noqa: E402

# 長逐字稿：480 行 ≈ 23,410 字元 ≈ 11,928 est tokens（0903 場實測 11,711 est tokens 同量級）。
# 注意：必須真的超過 6000 est tokens，否則 `needs_chunking` 不會翻真，本測試會失去鑑別力。
LONG_TRANSCRIPT = "".join(
    f"[{index // 60:02d}:{index % 60:02d}:00-{index // 60:02d}:{index % 60:02d}:30] "
    f"發言者{index % 5 + 1}：第 {index} 段逐字稿內容，討論搬遷與淹水處理。\n"
    for index in range(480)
)

BIG_CONTEXT = 71936  # LM Studio instance 實測值


def _service() -> SummarizationService:
    return SummarizationService()


def _plan(service: SummarizationService, monkeypatch, *, ceiling, context=BIG_CONTEXT):
    monkeypatch.setattr(settings, "LOCAL_LLM_EXTRACTION_CHUNK_CEILING_TOKENS", ceiling)
    template = get_template("section_meeting")
    return service._build_local_context_plan(
        LONG_TRANSCRIPT,
        settings.DEFAULT_SYSTEM_PROMPT,
        template=template,
        context_window_tokens=context,
    )


def test_ceiling_clamps_context_derived_chunk_budget(monkeypatch):
    """CORE-1b：上限 6000 時，分塊上限被夾住且長逐字稿真的被分塊。"""
    service = _service()
    baseline = _plan(service, monkeypatch, ceiling=0)
    clamped = _plan(service, monkeypatch, ceiling=6000)

    assert baseline.chunk_input_budget_tokens > 6000, "前置條件：大 context 下推導值應遠大於 6000"
    assert baseline.needs_chunking is False, "前置條件：本波前對同量級逐字稿只跑 1 次呼叫（R1 根因）"
    assert clamped.chunk_input_budget_tokens == 6000
    assert clamped.needs_chunking is True, "夾住上限後必須真的分成多塊（每塊各自一次呼叫）"
    assert clamped.estimated_chunk_count >= 2


def test_ceiling_zero_is_back_to_before(monkeypatch):
    """CORE-1b：0＝停用；分塊上限完全依 context 推導（本波前行為）。"""
    service = _service()
    disabled = _plan(service, monkeypatch, ceiling=0)
    assert disabled.chunk_input_budget_tokens > 6000
    assert disabled.needs_chunking is False


def test_ceiling_never_raises_budget_for_small_context(monkeypatch):
    """CORE-1b：小 context（Ollama 8k 級）不得因本上限而放大預算——只做 min()。"""
    service = _service()
    small = _plan(service, monkeypatch, ceiling=6000, context=8192)
    assert small.chunk_input_budget_tokens <= 6000
    assert small.chunk_input_budget_tokens >= 1200


def _dump(service: SummarizationService, monkeypatch, tmp_path, *, enabled: bool, **kwargs):
    monkeypatch.setattr(settings, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(settings, "LOCAL_LLM_DUMP_EXTRACTION_NOTES", enabled)
    service._dump_extraction_notes(
        kwargs.get("raw_notes", ["### 筆記一\n- 尾段事實：禮堂淹水"]),
        kwargs.get("merged_notes", "### 合併\n- 尾段事實：禮堂淹水"),
        chunk_count=kwargs.get("chunk_count", 2),
        transcript=kwargs.get("transcript", "逐字稿內容"),
    )
    return Path(settings.debug_dir) / "extraction-notes"


def test_dump_writes_all_chunks_and_merged(monkeypatch, tmp_path):
    """CORE-1a：開啟時寫出一份檔，含每一塊原始筆記與零損串接後內容。"""
    service = _service()
    target = _dump(
        service, monkeypatch, tmp_path, enabled=True, raw_notes=["### 塊一", "### 塊二"]
    )
    files = list(target.glob("notes-*.md"))
    assert len(files) == 1
    body = files[0].read_text(encoding="utf-8")
    assert "chunk_count=2" in body
    assert "## 原始萃取筆記 1（chunk 1/2）" in body
    assert "## 原始萃取筆記 2（chunk 2/2）" in body
    assert "## 零損串接後（實際進下游生成）" in body
    assert "### 合併" in body


def test_dump_disabled_creates_nothing(monkeypatch, tmp_path):
    """CORE-1a：預設關閉 ⇒ 不得建立任何檔案或目錄（逐字等於本波前）。"""
    service = _service()
    target = _dump(service, monkeypatch, tmp_path, enabled=False)
    assert list(target.glob("notes-*.md")) == []
    assert not target.exists()


def test_dump_failure_does_not_raise(monkeypatch, tmp_path):
    """CORE-1a：落檔失敗（不可寫入路徑）不得影響流程。"""
    service = _service()
    blocker = tmp_path / "blocked"
    blocker.write_text("not a directory", encoding="utf-8")
    monkeypatch.setattr(settings, "DATA_DIR", str(blocker))
    monkeypatch.setattr(settings, "LOCAL_LLM_DUMP_EXTRACTION_NOTES", True)
    service._dump_extraction_notes(["note"], "merged", chunk_count=1, transcript="T")
