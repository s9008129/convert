import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

from backend.core.config import settings
from backend.core.errors import (
    LMSTUDIO_MODEL_NOT_LOADED,
    LMSTUDIO_MULTIPLE_LOADED_LLMS,
    LMSTUDIO_NO_LOADED_LLM,
    LMSTUDIO_UNREACHABLE,
    StableServiceError,
)
from backend.services.summarization import SummarizationService


FIXTURES = Path(__file__).parent / "fixtures"


def _payload(name: str) -> dict:
    return json.loads((FIXTURES / f"lmstudio_{name}.json").read_text(encoding="utf-8"))


class _Response:
    status_code = 200

    def __init__(self, payload: dict):
        self._payload = payload

    def json(self) -> dict:
        return self._payload


def _service_with_payload(monkeypatch, payload: dict) -> tuple[SummarizationService, AsyncMock]:
    service = SummarizationService()
    client = Mock()
    client.get = AsyncMock(return_value=_Response(payload))
    get_client = AsyncMock(return_value=client)
    monkeypatch.setattr(service, "_get_lmstudio_http_client", get_client)
    monkeypatch.setattr(settings, "LOCAL_LLM_PROVIDER", "lmstudio")
    monkeypatch.setattr(settings, "LMSTUDIO_MODEL", None)
    monkeypatch.setattr(settings, "LOCAL_LLM_TRANSIENT_RETRIES", 0)
    return service, client.get


def test_lmstudio_parser_excludes_embeddings_and_reads_instance_context():
    instances = SummarizationService._parse_lmstudio_loaded_instances(_payload("one_loaded"))

    assert len(instances) == 1
    assert instances[0].model_key == "model-alpha"
    assert instances[0].instance_id == "model-alpha-instance-1"
    assert instances[0].context_length == 16384


def test_lmstudio_zero_loaded_and_embedding_only_are_distinct():
    service = SummarizationService()

    assert service._parse_lmstudio_loaded_instances(_payload("zero_loaded")) == []
    assert service._parse_lmstudio_loaded_instances(_payload("embedding_loaded")) == []


def test_lmstudio_parser_rejects_ambiguous_inventory_shape():
    service = SummarizationService()

    with pytest.raises(StableServiceError) as missing_instances:
        service._parse_lmstudio_loaded_instances({"models": [{"type": "llm", "key": "x"}]})
    assert missing_instances.value.code == LMSTUDIO_UNREACHABLE

    with pytest.raises(StableServiceError) as unknown_type:
        service._parse_lmstudio_loaded_instances(
            {"models": [{"type": "unknown", "key": "x", "loaded_instances": []}]}
        )
    assert unknown_type.value.code == LMSTUDIO_UNREACHABLE


@pytest.mark.asyncio
async def test_lmstudio_selection_requires_one_loaded_llm(monkeypatch):
    service, get_calls = _service_with_payload(monkeypatch, _payload("zero_loaded"))

    with pytest.raises(StableServiceError) as exc_info:
        await service._resolve_lmstudio_selection()

    assert exc_info.value.code == LMSTUDIO_NO_LOADED_LLM
    get_calls.assert_awaited_once_with("/api/v1/models")


@pytest.mark.asyncio
async def test_lmstudio_multiple_loaded_requires_exact_override(monkeypatch):
    service, _ = _service_with_payload(monkeypatch, _payload("multiple_loaded"))

    with pytest.raises(StableServiceError) as exc_info:
        await service._resolve_lmstudio_selection()
    assert exc_info.value.code == LMSTUDIO_MULTIPLE_LOADED_LLMS

    monkeypatch.setattr(settings, "LMSTUDIO_MODEL", "model-beta-instance-1")
    selection = await service._resolve_lmstudio_selection()
    assert selection.model_identifier == "model-beta"
    assert selection.loaded_instance_id == "model-beta-instance-1"


@pytest.mark.asyncio
async def test_lmstudio_wrong_override_is_not_loaded(monkeypatch):
    service, _ = _service_with_payload(monkeypatch, _payload("one_loaded"))
    monkeypatch.setattr(settings, "LMSTUDIO_MODEL", "model-missing")

    with pytest.raises(StableServiceError) as exc_info:
        await service._resolve_lmstudio_selection()

    assert exc_info.value.code == LMSTUDIO_MODEL_NOT_LOADED


@pytest.mark.asyncio
async def test_lmstudio_health_separates_reachable_from_selection_ready(monkeypatch):
    service, _ = _service_with_payload(monkeypatch, _payload("zero_loaded"))

    assert await service.check_lmstudio_health() is True
    assert service.get_local_llm_health() == {
        "provider": "lmstudio",
        "server_reachable": True,
        "selection_status": LMSTUDIO_NO_LOADED_LLM,
        "loaded_llm_count": 0,
        "selected_model": None,
        "context_length": None,
    }


@pytest.mark.asyncio
async def test_mac_auto_does_not_probe_ollama(monkeypatch):
    service, _ = _service_with_payload(monkeypatch, _payload("one_loaded"))
    monkeypatch.setattr(settings, "LOCAL_LLM_PROVIDER", "auto")
    monkeypatch.setattr(
        "backend.services.summarization.resolve_local_llm_provider",
        Mock(return_value="lmstudio"),
    )
    ollama_health = AsyncMock(side_effect=AssertionError("Ollama must not be probed"))
    monkeypatch.setattr(service, "check_ollama_health", ollama_health)

    assert await service._select_local_engine() == "lmstudio"
    ollama_health.assert_not_awaited()


def test_lmstudio_health_snapshot_reports_effective_provider(monkeypatch):
    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_LLM_PROVIDER", "auto")
    monkeypatch.setattr(
        "backend.services.summarization.resolve_local_llm_provider",
        Mock(return_value="lmstudio"),
    )

    assert service.get_local_llm_health()["provider"] == "lmstudio"


@pytest.mark.asyncio
async def test_lmstudio_generation_is_async_and_uses_fixed_model_selection(monkeypatch):
    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_LLM_PROVIDER", "lmstudio")
    selection = service._make_lmstudio_selection(
        service._parse_lmstudio_loaded_instances(_payload("one_loaded"))[0]
    )
    service._active_lmstudio_selection = selection

    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="會議紀錄本文"))]
    )
    create = AsyncMock(return_value=response)
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    monkeypatch.setattr(service, "_get_lmstudio_client", Mock(return_value=client))

    result = await service._summarize_with_lmstudio(
        "system",
        "user",
        max_tokens=200,
        selection=selection,
    )

    assert result == "會議紀錄本文"
    assert create.await_count == 1
    assert create.await_args.kwargs["model"] == "model-alpha"


@pytest.mark.asyncio
async def test_lmstudio_generation_retries_transient_timeout(monkeypatch):
    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_LLM_PROVIDER", "lmstudio")
    monkeypatch.setattr(settings, "LOCAL_LLM_TRANSIENT_RETRIES", 1)
    monkeypatch.setattr(settings, "LOCAL_LLM_RETRY_BACKOFF_SECONDS", 0.0)
    selection = service._make_lmstudio_selection(
        service._parse_lmstudio_loaded_instances(_payload("one_loaded"))[0]
    )
    response = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content="重試後的摘要"))]
    )
    create = AsyncMock(side_effect=[httpx.ReadTimeout(""), response])
    client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=create))
    )
    monkeypatch.setattr(service, "_get_lmstudio_client", Mock(return_value=client))

    assert await service._summarize_with_lmstudio("system", "user", selection=selection) == "重試後的摘要"
    assert create.await_count == 2


@pytest.mark.asyncio
async def test_lmstudio_unreachable_has_stable_error(monkeypatch):
    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_LLM_PROVIDER", "lmstudio")
    monkeypatch.setattr(settings, "LOCAL_LLM_TRANSIENT_RETRIES", 0)
    client = Mock()
    client.get = AsyncMock(side_effect=httpx.ConnectError("offline"))
    monkeypatch.setattr(service, "_get_lmstudio_http_client", AsyncMock(return_value=client))

    with pytest.raises(StableServiceError) as exc_info:
        await service._resolve_lmstudio_selection()

    assert exc_info.value.code == LMSTUDIO_UNREACHABLE
    assert service.get_local_llm_health()["selection_status"] == LMSTUDIO_UNREACHABLE


@pytest.mark.asyncio
async def test_lmstudio_server_error_has_stable_unreachable_error(monkeypatch):
    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_LLM_PROVIDER", "lmstudio")
    monkeypatch.setattr(settings, "LOCAL_LLM_TRANSIENT_RETRIES", 0)
    selection = service._make_lmstudio_selection(
        service._parse_lmstudio_loaded_instances(_payload("one_loaded"))[0]
    )
    server_error = RuntimeError("server error")
    server_error.response = SimpleNamespace(status_code=503)
    client = SimpleNamespace(
        chat=SimpleNamespace(
            completions=SimpleNamespace(create=AsyncMock(side_effect=server_error))
        )
    )
    monkeypatch.setattr(service, "_get_lmstudio_client", Mock(return_value=client))

    with pytest.raises(StableServiceError) as exc_info:
        await service._summarize_with_lmstudio("system", "user", selection=selection)

    assert exc_info.value.code == LMSTUDIO_UNREACHABLE
