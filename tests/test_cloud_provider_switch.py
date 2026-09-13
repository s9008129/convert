#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""雲端 LLM provider 切換測試（T20260913-1900-01，v4.7.1）。

為什麼需要這組測試：
- 雲端模式原本硬綁 Gemini；切換 provider 後，模型名稱、端點、金鑰環境變數
  全部必須由 `settings.cloud_llm_*` 單一來源決定，不能再有任一處直接讀
  `GEMINI_*`（否則切回 Gemini 或改模型時會出現「一半 Ollama 一半 Gemini」）。
- 推理模型（Ollama Cloud deepseek-v4.1-flash 等）在 streaming 時可能把思考
  內容放在 content 以外的欄位；若只讀 content，會誤判為「空回應」而讓整份
  會議紀錄失敗。這裡用假串流鎖住「只有 reasoning 時必須回報可理解的錯誤」。
"""

from types import SimpleNamespace

import pytest

from backend.core.config import Settings, settings
from backend.services.summarization import SummarizationService


# ---------------------------------------------------------------------------
# 假串流（不連網、不呼叫真實 API）
# ---------------------------------------------------------------------------
class _Delta:
    def __init__(self, content=None, reasoning=None):
        self.content = content
        self.reasoning = reasoning


class _Chunk:
    def __init__(self, delta=None, choices=None):
        if choices is not None:
            self.choices = choices
        else:
            self.choices = [SimpleNamespace(delta=delta)] if delta is not None else []


class _FakeStream:
    def __init__(self, chunks):
        self._chunks = list(chunks)
        self._index = 0

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    def __aiter__(self):
        self._index = 0
        return self

    async def __anext__(self):
        if self._index >= len(self._chunks):
            raise StopAsyncIteration
        chunk = self._chunks[self._index]
        self._index += 1
        return chunk


class _FakeCompletions:
    def __init__(self, stream, captured=None):
        self._stream = stream
        self._captured = captured

    async def create(self, **kwargs):
        if self._captured is not None:
            self._captured.update(kwargs)
        return self._stream


def _fake_client(stream, captured=None):
    return SimpleNamespace(
        chat=SimpleNamespace(completions=_FakeCompletions(stream, captured))
    )


# ---------------------------------------------------------------------------
# 設定解析
# ---------------------------------------------------------------------------
def test_default_cloud_provider_is_ollama_cloud():
    cfg = Settings(_env_file=None)
    assert cfg.cloud_llm_provider_id == "ollama_cloud"
    assert cfg.cloud_llm_model == "deepseek-v4.1-flash"
    assert cfg.cloud_llm_base_url == "https://ollama.com/v1"
    assert cfg.cloud_llm_api_key_env_name == "OLLAMA_API_KEY"
    assert cfg.cloud_llm_provider_label == "Ollama Cloud"


def test_gemini_provider_still_selectable():
    cfg = Settings(_env_file=None, CLOUD_LLM_PROVIDER="gemini")
    assert cfg.cloud_llm_provider_id == "gemini"
    assert cfg.cloud_llm_model == "gemini-3.5-flash-lite"
    assert "generativelanguage.googleapis.com" in cfg.cloud_llm_base_url
    assert cfg.cloud_llm_api_key_env_name == "GEMINI_API_KEY"


def test_provider_aliases_normalized():
    cfg = Settings(_env_file=None, CLOUD_LLM_PROVIDER="Ollama-Cloud")
    assert cfg.cloud_llm_provider_id == "ollama_cloud"


def test_unknown_cloud_provider_rejected():
    with pytest.raises(Exception):
        Settings(_env_file=None, CLOUD_LLM_PROVIDER="bogus")


def test_cloud_base_url_normalized_without_trailing_slash():
    cfg = Settings(_env_file=None, OLLAMA_CLOUD_BASE_URL="https://example.invalid/v1/")
    assert cfg.cloud_llm_base_url == "https://example.invalid/v1"


# ---------------------------------------------------------------------------
# 金鑰解析（provider-aware）
# ---------------------------------------------------------------------------
def test_api_key_resolves_from_provider_env(monkeypatch):
    service = SummarizationService()
    monkeypatch.setattr(settings, "CLOUD_LLM_PROVIDER", "ollama_cloud")
    monkeypatch.setattr(settings, "OLLAMA_API_KEY", "dummy-ollama-key")
    assert service._get_gemini_api_key() == "dummy-ollama-key"
    assert service.check_gemini_available() is True


def test_missing_key_reports_provider_env_name(monkeypatch):
    service = SummarizationService()
    monkeypatch.setattr(settings, "CLOUD_LLM_PROVIDER", "ollama_cloud")
    monkeypatch.setattr(settings, "OLLAMA_API_KEY", None)

    assert service.check_gemini_available() is False
    with pytest.raises(ValueError) as excinfo:
        service._get_gemini_api_key()
    assert "OLLAMA_API_KEY" in str(excinfo.value)


def test_gemini_provider_key_falls_back_to_gemini_env(monkeypatch):
    service = SummarizationService()
    monkeypatch.setattr(settings, "CLOUD_LLM_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "GEMINI_API_KEY", "dummy-gemini-key")
    monkeypatch.setattr(settings, "OLLAMA_API_KEY", "dummy-ollama-key")
    assert service._get_gemini_api_key() == "dummy-gemini-key"


def test_async_client_uses_provider_base_url(monkeypatch):
    service = SummarizationService()
    monkeypatch.setattr(settings, "CLOUD_LLM_PROVIDER", "ollama_cloud")
    monkeypatch.setattr(settings, "OLLAMA_API_KEY", "dummy-ollama-key")
    service._gemini_async_client = None

    client = service._get_gemini_async_client()
    assert str(client.base_url).rstrip("/") == settings.cloud_llm_base_url
    assert client.api_key == "dummy-ollama-key"


# ---------------------------------------------------------------------------
# 串流解析
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_streaming_content_is_concatenated_and_model_from_settings(monkeypatch):
    service = SummarizationService()
    captured = {}
    stream = _FakeStream(
        [
            _Chunk(delta=_Delta(reasoning="先想一下")),  # reasoning 不應混進正文
            _Chunk(choices=[]),                          # 空 choices 不得炸掉
            _Chunk(delta=_Delta(content="會議")),
            _Chunk(delta=_Delta(content="紀錄")),
        ]
    )
    monkeypatch.setattr(service, "_get_gemini_async_client", lambda: _fake_client(stream, captured))
    monkeypatch.setattr(settings, "CLOUD_LLM_PROVIDER", "ollama_cloud")

    result = await service._gemini_chat_once("系統提示", "使用者訊息", 0.1, None)

    assert "會議紀錄" in result
    assert "先想一下" not in result
    assert captured["model"] == settings.cloud_llm_model
    assert captured["messages"][0]["role"] == "system"


@pytest.mark.asyncio
async def test_reasoning_only_response_raises_actionable_error(monkeypatch):
    service = SummarizationService()
    stream = _FakeStream([_Chunk(delta=_Delta(reasoning="思考" * 50))])
    monkeypatch.setattr(service, "_get_gemini_async_client", lambda: _fake_client(stream))
    monkeypatch.setattr(settings, "CLOUD_LLM_PROVIDER", "ollama_cloud")

    with pytest.raises(RuntimeError) as excinfo:
        await service._gemini_chat_once("系統提示", "使用者訊息", 0.1, None)

    message = str(excinfo.value)
    assert "reasoning" in message
    assert settings.cloud_llm_model in message


@pytest.mark.asyncio
async def test_truly_empty_stream_keeps_generic_error(monkeypatch):
    service = SummarizationService()
    stream = _FakeStream([_Chunk(delta=_Delta(content=""))])
    monkeypatch.setattr(service, "_get_gemini_async_client", lambda: _fake_client(stream))

    with pytest.raises(RuntimeError) as excinfo:
        await service._gemini_chat_once("系統提示", "使用者訊息", 0.1, None)
    assert "結果為空" in str(excinfo.value)
