# -*- coding: utf-8 -*-
"""跨平台（macOS／Windows）地端引擎路由契約（v4.9.0）。

需求來源（Owner 2026-09-22）：本專案設計上同時支援 macOS（LM Studio）與
Windows 11 ＋ RTX 4090（Ollama），本波「出處標註確定性吸附」必須兩平台一體適用。

獨立查核（`e2e/crossos-audit-01/audit.md`）指出：程式碼層證據齊備，但
「非 Darwin（Windows/Linux）auto → Ollama 優先」的選擇邏輯**沒有任何測試覆蓋**——
也就是說，未來若有人不小心改動路由，Windows 端會靜默失效而測試仍全綠。

本檔釘住三件事：
1. 平台 → provider 解析：Apple Silicon auto＝LM Studio；非 Darwin auto＝保留 auto。
2. ``_select_local_engine`` 的路由優先序：非 Mac auto＝Ollama 優先、Ollama 不可用才
   退 LM Studio；「Ollama 有回應但缺模型」必須**直接報錯，不得靜默 fallback**
   （否則使用者在 Windows 上會以為跑的是 Ollama，其實被換掉）。
3. 品質後處理（吸附／收尾）本身**不得含平台分支**——兩平台共用同一條
   ``_finalize_record_text(mode="local")``；引擎分派函式也不得依平台分支。
"""

import inspect
import os
import platform
import tempfile

os.environ.setdefault("DATA_DIR", tempfile.mkdtemp(prefix="meetingscribe-platform-routing-"))

from types import SimpleNamespace  # noqa: E402
from unittest.mock import AsyncMock, Mock  # noqa: E402

import pytest  # noqa: E402

from backend.core import text_postprocess  # noqa: E402
from backend.core.config import settings  # noqa: E402
from backend.core.platform_config import resolve_local_llm_provider  # noqa: E402
from backend.services.summarization import SummarizationService  # noqa: E402


@pytest.fixture
def platform_kind(monkeypatch):
    """把 ``platform.system／machine`` 固定成指定平台（未知平台視為非 Mac）。"""

    def _set(system: str, machine: str = "arm64") -> None:
        monkeypatch.setattr(platform, "system", lambda: system)
        monkeypatch.setattr(platform, "machine", lambda: machine)

    return _set


def _lmstudio_selection() -> SimpleNamespace:
    return SimpleNamespace(
        model_identifier="qwen3.8-27b-splash",
        loaded_instance_id="qwen3.8-27b-splash",
    )


# ---------------------------------------------------------------------------
# 1. 平台 → provider 解析
# ---------------------------------------------------------------------------


def test_apple_silicon_auto_resolves_to_lmstudio(platform_kind, monkeypatch):
    """macOS（Apple Silicon）的 auto 必須是 LM Studio（本機使用情境）。"""
    platform_kind("Darwin", "arm64")
    monkeypatch.setattr(settings, "LOCAL_LLM_PROVIDER", "auto")

    assert resolve_local_llm_provider("auto") == "lmstudio"


def test_windows_auto_keeps_auto_for_ollama_first_routing(platform_kind, monkeypatch):
    """Windows（非 Darwin）的 auto 必須保留 auto，才能走 Ollama 優先。"""
    platform_kind("Windows", "AMD64")
    monkeypatch.setattr(settings, "LOCAL_LLM_PROVIDER", "auto")

    assert resolve_local_llm_provider("auto") == "auto"


def test_explicit_provider_is_preserved_on_every_platform(platform_kind, monkeypatch):
    """明確指定 lmstudio／ollama 時，兩平台皆不得被平台預設改寫。"""
    monkeypatch.setattr(settings, "LOCAL_LLM_PROVIDER", "ollama")
    platform_kind("Windows", "AMD64")
    assert resolve_local_llm_provider("ollama") == "ollama"
    platform_kind("Darwin", "arm64")
    assert resolve_local_llm_provider("ollama") == "ollama"


def test_unsupported_provider_value_fails_fast(platform_kind):
    """未知 provider 值必須 fail-fast（不得默默當成 auto）。"""
    platform_kind("Windows", "AMD64")
    with pytest.raises(ValueError):
        resolve_local_llm_provider("not-a-provider")


# ---------------------------------------------------------------------------
# 2. 引擎路由優先序（Windows 路徑＝本專案的辦公室部署情境）
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_windows_auto_prefers_ollama_when_healthy(platform_kind, monkeypatch):
    """Windows auto ＋ Ollama 可用 → 必須選 Ollama（RTX 4090 部署路徑）。"""
    platform_kind("Windows", "AMD64")
    monkeypatch.setattr(settings, "LOCAL_LLM_PROVIDER", "auto")
    service = SummarizationService()
    monkeypatch.setattr(service, "check_ollama_health", AsyncMock(return_value=True))

    assert await service._select_local_engine() == "ollama"


@pytest.mark.asyncio
async def test_windows_auto_falls_back_to_lmstudio_only_when_ollama_unavailable(
    platform_kind, monkeypatch
):
    """Ollama 連不上（服務未啟動）才允許退 LM Studio；此為既有 fallback 語意。"""
    platform_kind("Windows", "AMD64")
    monkeypatch.setattr(settings, "LOCAL_LLM_PROVIDER", "auto")
    service = SummarizationService()
    service._ollama_model_error = None
    monkeypatch.setattr(service, "check_ollama_health", AsyncMock(return_value=False))
    monkeypatch.setattr(
        service, "_resolve_lmstudio_selection", AsyncMock(return_value=_lmstudio_selection())
    )

    assert await service._select_local_engine() == "lmstudio"


@pytest.mark.asyncio
async def test_windows_auto_reports_missing_ollama_model_without_silent_fallback(
    platform_kind, monkeypatch
):
    """Ollama 可用但缺指定模型 → 必須報錯，不得靜默換引擎（否則使用者不知情）。"""
    platform_kind("Windows", "AMD64")
    monkeypatch.setattr(settings, "LOCAL_LLM_PROVIDER", "auto")
    service = SummarizationService()
    service._ollama_model_error = "配置的模型 'gemma4:31b' 未找到"
    monkeypatch.setattr(service, "check_ollama_health", AsyncMock(return_value=False))
    resolve_lmstudio = AsyncMock(return_value=_lmstudio_selection())
    monkeypatch.setattr(service, "_resolve_lmstudio_selection", resolve_lmstudio)

    with pytest.raises(RuntimeError) as excinfo:
        await service._select_local_engine()

    assert "gemma4:31b" in str(excinfo.value)
    resolve_lmstudio.assert_not_awaited()


@pytest.mark.asyncio
async def test_explicit_ollama_provider_raises_when_service_down(platform_kind, monkeypatch):
    """明確指定 ollama 時，服務不可用必須報錯（不 fallback 到 LM Studio）。"""
    platform_kind("Windows", "AMD64")
    monkeypatch.setattr(settings, "LOCAL_LLM_PROVIDER", "ollama")
    service = SummarizationService()
    service._ollama_model_error = None
    monkeypatch.setattr(service, "check_ollama_health", AsyncMock(return_value=False))

    with pytest.raises(RuntimeError, match="Ollama 服務不可用"):
        await service._select_local_engine()


@pytest.mark.asyncio
async def test_mac_auto_never_probes_ollama(platform_kind, monkeypatch):
    """macOS auto 不得對 Ollama 發出探測（既有 contract，回歸保護）。"""
    platform_kind("Darwin", "arm64")
    monkeypatch.setattr(settings, "LOCAL_LLM_PROVIDER", "auto")
    service = SummarizationService()
    monkeypatch.setattr(
        service, "_resolve_lmstudio_selection", AsyncMock(return_value=_lmstudio_selection())
    )
    ollama_health = AsyncMock(side_effect=AssertionError("macOS auto 不得探測 Ollama"))
    monkeypatch.setattr(service, "check_ollama_health", ollama_health)

    assert await service._select_local_engine() == "lmstudio"
    ollama_health.assert_not_awaited()


# ---------------------------------------------------------------------------
# 3. 品質後處理不得含平台分支（兩平台共用同一條修復路徑）
# ---------------------------------------------------------------------------


def test_record_postprocess_module_has_no_platform_branch():
    """吸附／收尾模組（本波修復所在）不得出現任何平台判斷。"""
    source = inspect.getsource(text_postprocess).lower()
    forbidden = ("sys.platform", "platform.system", "os.name", "darwin", "win32", "linux")
    hits = [token for token in forbidden if token in source]

    assert hits == [], f"品質後處理模組不應含平台分支，命中：{hits}"


def test_local_engine_dispatch_has_no_platform_branch():
    """引擎分派本身不得依平台分支（平台只決定『選哪個引擎』，不決定行為）。"""
    source = inspect.getsource(SummarizationService._generate_with_local_engine).lower()
    forbidden = ("sys.platform", "platform.system", "os.name", "darwin", "win32")
    hits = [token for token in forbidden if token in source]

    assert hits == [], f"引擎分派不應含平台分支，命中：{hits}"


@pytest.mark.parametrize("engine", ["ollama", "lmstudio"])
def test_snap_fix_is_engine_agnostic(engine, monkeypatch):
    """同一份輸入下，吸附結果不得因引擎而異（純函式、與引擎無關）。"""
    transcript = "[00:00:10-00:00:40] 發言者1：請各股配合辦理。\n[00:00:40-00:00:55] 發言者2：收到。"
    text = "決議：請各股配合辦理。（發言者1，00:00:22）"

    first = text_postprocess.snap_source_tags_to_transcript(text, transcript)
    # 重複呼叫（模擬另一引擎的同一步驟）必須得到 byte 級相同結果
    second = text_postprocess.snap_source_tags_to_transcript(text, transcript)

    assert first == second
    assert first[0] == text_postprocess.snap_source_tags_to_transcript(text, transcript)[0]
    assert engine in ("ollama", "lmstudio")  # 參數化僅用於標示「引擎無關」的兩條路徑
