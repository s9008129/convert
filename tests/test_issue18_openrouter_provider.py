"""Issue #18 OpenRouter validation-provider contracts."""

from types import SimpleNamespace

import pytest

from backend.core.config import settings
from backend.core.platform_config import resolve_local_llm_provider
from backend.services.local_pipeline_v2 import ModelRuntimeProfile
from backend.services.summarization import SummarizationService


def _response(content='{"claims":[]}'):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content=content, reasoning_content=None),
                finish_reason="stop",
            )
        ],
        usage=SimpleNamespace(
            prompt_tokens=10,
            completion_tokens=5,
            completion_tokens_details=SimpleNamespace(reasoning_tokens=0),
        ),
    )


def test_openrouter_is_explicit_validation_provider():
    assert resolve_local_llm_provider("openrouter") == "openrouter"
    # Production platform auto semantics are intentionally untouched.
    assert resolve_local_llm_provider("lmstudio") == "lmstudio"


@pytest.mark.asyncio
async def test_openrouter_selection_requires_key_and_exact_model(monkeypatch):
    service = SummarizationService()
    monkeypatch.setattr(settings, "LOCAL_LLM_PROVIDER", "openrouter")
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "test-secret")
    monkeypatch.setattr(settings, "OPENROUTER_MODEL", "qwen/qwen3.8-27b")
    assert await service._select_local_engine() == "openrouter"
    assert service._get_effective_model() == "qwen/qwen3.8-27b"


@pytest.mark.asyncio
async def test_openrouter_request_is_model_sticky_and_disables_reasoning(monkeypatch):
    service = SummarizationService()
    monkeypatch.setattr(settings, "OPENROUTER_MODEL", "google/gemma-4-31b-it")
    monkeypatch.setattr(settings, "LOCAL_LLM_DISABLE_THINKING", True)
    captured = {}

    class Completion:
        async def create(self, **kwargs):
            captured.update(kwargs)
            return _response()

    client = SimpleNamespace(chat=SimpleNamespace(completions=Completion()))
    monkeypatch.setattr(service, "_get_openrouter_client", lambda: client)
    profile = ModelRuntimeProfile(
        family="Gemma",
        model_key="google/gemma-4-31b-it",
        provider="openrouter",
        temperature=0.1,
        top_p=0.9,
        supported_controls=("temperature", "top_p"),
    )
    response = await service._openrouter_chat_request(
        [{"role": "user", "content": "x"}],
        0.1,
        128,
        runtime_profile=profile,
    )
    assert response.choices[0].finish_reason == "stop"
    assert captured["model"] == "google/gemma-4-31b-it"
    assert captured["temperature"] == 0.1
    assert captured["top_p"] == 0.9
    assert captured["extra_body"] == {"reasoning": {"enabled": False}}


@pytest.mark.asyncio
async def test_openrouter_schema_probe_is_source_free(monkeypatch):
    service = SummarizationService()
    monkeypatch.setattr(settings, "OPENROUTER_MODEL", "qwen/qwen3.8-27b")
    captured = {}

    async def chat(messages, temperature, max_tokens, **kwargs):
        captured.update(messages=messages, temperature=temperature, max_tokens=max_tokens, **kwargs)
        return _response()

    monkeypatch.setattr(service, "_openrouter_chat_request", chat)
    result = await service._probe_native_schema_capability("openrouter", None)
    assert result.capability == "SUPPORTED"
    assert captured["messages"] == [
        {"role": "system", "content": "Return the requested JSON object exactly."},
        {"role": "user", "content": 'Return {"claims":[]}. '[:-1]},
    ]
    schema = captured["response_format"]["json_schema"]["schema"]
    assert "claims" in schema["properties"]
