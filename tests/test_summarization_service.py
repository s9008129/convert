#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Focused tests for Ollama model resolution in SummarizationService.
"""
from unittest.mock import AsyncMock, Mock

import pytest

from backend.core.config import settings
from backend.services.summarization import SummarizationService


def _build_tags_response(models: list[str]) -> Mock:
    response = Mock()
    response.status_code = 200
    response.json.return_value = {
        "models": [{"name": model_name} for model_name in models]
    }
    return response


def test_resolve_compatible_model_legacy_alias_to_standard_model():
    service = SummarizationService()

    resolved = service._resolve_compatible_model(
        "gemma3:27b-it-qat",
        ["gemma3:27b", "mistral-small3.2:latest"]
    )

    assert resolved == "gemma3:27b"


def test_resolve_compatible_model_prefers_same_family_latest():
    service = SummarizationService()

    resolved = service._resolve_compatible_model(
        "gemma3:27b-it-qat",
        ["gemma3:latest", "mistral-small3.2:latest"]
    )

    assert resolved == "gemma3:latest"


@pytest.mark.asyncio
async def test_check_ollama_health_uses_resolved_model(monkeypatch):
    service = SummarizationService()
    fake_client = Mock()
    fake_client.get = AsyncMock(
        return_value=_build_tags_response(["gemma3:27b", "mistral-small3.2:latest"])
    )

    monkeypatch.setattr(settings, "LOCAL_LLM_MODEL", "gemma3:27b-it-qat")
    monkeypatch.setattr(service, "_get_ollama_client", AsyncMock(return_value=fake_client))

    healthy = await service.check_ollama_health()

    assert healthy is True
    assert service._get_effective_model() == "gemma3:27b"
    assert service._ollama_model_error is None


@pytest.mark.asyncio
async def test_check_ollama_health_reports_clear_model_error(monkeypatch):
    service = SummarizationService()
    fake_client = Mock()
    fake_client.get = AsyncMock(
        return_value=_build_tags_response(["mistral-small3.2:latest"])
    )

    monkeypatch.setattr(settings, "LOCAL_LLM_MODEL", "gemma3:27b-it-qat")
    monkeypatch.setattr(service, "_get_ollama_client", AsyncMock(return_value=fake_client))

    healthy = await service.check_ollama_health()

    assert healthy is False
    assert service._resolved_model is None
    assert service._ollama_model_error is not None
    assert "gemma3:27b-it-qat" in service._ollama_model_error
    assert "mistral-small3.2:latest" in service._ollama_model_error
    assert "ollama pull gemma3:27b" in service._ollama_model_error


@pytest.mark.asyncio
async def test_summarize_with_local_llm_surfaces_model_resolution_error(monkeypatch):
    service = SummarizationService()
    service._ollama_model_error = "設定的 Ollama 模型不存在。"

    monkeypatch.setattr(service, "check_ollama_health", AsyncMock(return_value=False))
    monkeypatch.setattr(service, "check_lmstudio_health", AsyncMock(return_value=False))

    with pytest.raises(RuntimeError, match="設定的 Ollama 模型不存在"):
        await service._summarize_with_local_llm("system", "user")
