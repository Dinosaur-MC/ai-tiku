import importlib
import sys
from types import SimpleNamespace

import langchain_ollama
import langchain_openai
import pytest


class FakeOllamaEmbeddings:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakeChatOllama:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def invoke(self, messages, **kwargs):
        return SimpleNamespace(content="fake-ollama-chat")

    async def ainvoke(self, messages, **kwargs):
        return SimpleNamespace(content="fake-ollama-chat-async")

    def stream(self, messages, **kwargs):
        yield SimpleNamespace(content="fake-")
        yield SimpleNamespace(content="ollama-")
        yield SimpleNamespace(content="stream")

    async def astream(self, messages, **kwargs):
        for value in ["fake-", "ollama-", "astream"]:
            yield SimpleNamespace(content=value)


class FakeOllamaLLM:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def invoke(self, prompt, **kwargs):
        return "fake-ollama-completion"

    async def ainvoke(self, prompt, **kwargs):
        return "fake-ollama-completion-async"


class FakeChatOpenAI:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def invoke(self, messages, **kwargs):
        return SimpleNamespace(content="fake-openai-chat")

    async def ainvoke(self, messages, **kwargs):
        return SimpleNamespace(content="fake-openai-chat-async")

    def stream(self, messages, **kwargs):
        yield SimpleNamespace(content="fake-")
        yield SimpleNamespace(content="openai-")
        yield SimpleNamespace(content="stream")

    async def astream(self, messages, **kwargs):
        for value in ["fake-", "openai-", "astream"]:
            yield SimpleNamespace(content=value)


class FakeOpenAIEmbeddings:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


def reload_llm(monkeypatch, env):
    keys = [
        "MODEL_TEMPERATURE",
        "CHAT_PROVIDER",
        "CHAT_MODEL",
        "CHAT_BASE_URL",
        "CHAT_API_KEY",
        "CHAT_TEMPERATURE",
        "COMPLETION_PROVIDER",
        "COMPLETION_MODEL",
        "COMPLETION_BASE_URL",
        "COMPLETION_API_KEY",
        "COMPLETION_TEMPERATURE",
        "EMBEDDING_PROVIDER",
        "EMBEDDING_MODEL",
        "EMBEDDING_BASE_URL",
        "EMBEDDING_API_KEY",
    ]
    for key in keys:
        monkeypatch.delenv(key, raising=False)
    for key, value in env.items():
        monkeypatch.setenv(key, value)

    monkeypatch.setattr(langchain_ollama, "OllamaEmbeddings", FakeOllamaEmbeddings)
    monkeypatch.setattr(langchain_ollama, "ChatOllama", FakeChatOllama)
    monkeypatch.setattr(langchain_ollama, "OllamaLLM", FakeOllamaLLM)
    monkeypatch.setattr(langchain_openai, "ChatOpenAI", FakeChatOpenAI)
    monkeypatch.setattr(langchain_openai, "OpenAIEmbeddings", FakeOpenAIEmbeddings)

    sys.modules.pop("utils.llm", None)
    import utils.llm as llm

    return importlib.reload(llm)


def test_loads_provider_specific_settings(monkeypatch):
    llm = reload_llm(
        monkeypatch,
        {
            "MODEL_TEMPERATURE": "0.2",
            "CHAT_PROVIDER": "ollama",
            "CHAT_MODEL": "qwen3.5:2b",
            "CHAT_BASE_URL": "http://localhost:11434",
            "COMPLETION_PROVIDER": "openai_compatible",
            "COMPLETION_MODEL": "gpt-4o-mini",
            "COMPLETION_BASE_URL": "https://completion.example.test/v1",
            "COMPLETION_API_KEY": "sk-completion",
            "EMBEDDING_PROVIDER": "openai_compatible",
            "EMBEDDING_MODEL": "text-embedding-3-large",
            "EMBEDDING_BASE_URL": "https://embedding.example.test/v1",
            "EMBEDDING_API_KEY": "sk-embedding",
        },
    )

    assert llm.settings.chat.provider == "ollama"
    assert llm.settings.chat.model == "qwen3.5:2b"
    assert llm.settings.chat.temperature == 0.2
    assert llm.settings.completion.provider == "openai_compatible"
    assert llm.settings.completion.base_url == "https://completion.example.test/v1"
    assert llm.settings.embedding.provider == "openai_compatible"
    assert llm.settings.embedding.api_key == "sk-embedding"


def test_chat_temperature_falls_back_to_model_temperature(monkeypatch):
    llm = reload_llm(
        monkeypatch,
        {
            "MODEL_TEMPERATURE": "0.35",
            "CHAT_PROVIDER": "ollama",
            "CHAT_MODEL": "qwen3.5:2b",
            "COMPLETION_PROVIDER": "ollama",
            "COMPLETION_MODEL": "qwen3.5:2b",
            "EMBEDDING_PROVIDER": "ollama",
            "EMBEDDING_MODEL": "qwen3-embedding:0.6b",
        },
    )

    assert llm.settings.chat.temperature == 0.35
    assert llm.settings.completion.temperature == 0.35


def test_openai_compatible_requires_base_url_and_api_key(monkeypatch):
    with pytest.raises(ValueError, match="COMPLETION_BASE_URL"):
        reload_llm(
            monkeypatch,
            {
                "CHAT_PROVIDER": "ollama",
                "CHAT_MODEL": "qwen3.5:2b",
                "COMPLETION_PROVIDER": "openai_compatible",
                "COMPLETION_MODEL": "gpt-4o-mini",
                "EMBEDDING_PROVIDER": "ollama",
                "EMBEDDING_MODEL": "qwen3-embedding:0.6b",
            },
        )


@pytest.mark.parametrize(
    ("provider_key", "model_key"),
    [
        ("CHAT_PROVIDER", "CHAT_MODEL"),
        ("COMPLETION_PROVIDER", "COMPLETION_MODEL"),
        ("EMBEDDING_PROVIDER", "EMBEDDING_MODEL"),
    ],
)
def test_unsupported_provider_raises_during_load(monkeypatch, provider_key, model_key):
    env = {
        "CHAT_PROVIDER": "ollama",
        "CHAT_MODEL": "qwen3.5:2b",
        "COMPLETION_PROVIDER": "ollama",
        "COMPLETION_MODEL": "qwen3.5:2b",
        "EMBEDDING_PROVIDER": "ollama",
        "EMBEDDING_MODEL": "qwen3-embedding:0.6b",
        provider_key: "invalid_provider",
        model_key: "irrelevant-model",
    }

    with pytest.raises(ValueError, match="invalid_provider|unsupported|openai_compatible"):
        reload_llm(monkeypatch, env)


@pytest.mark.parametrize(
    ("provider_key", "model_key", "extra_env"),
    [
        (
            "CHAT_PROVIDER",
            "CHAT_MODEL",
            {
                "CHAT_BASE_URL": "https://chat.example.test/v1",
                "CHAT_API_KEY": "sk-chat",
            },
        ),
        (
            "COMPLETION_PROVIDER",
            "COMPLETION_MODEL",
            {
                "COMPLETION_BASE_URL": "https://completion.example.test/v1",
                "COMPLETION_API_KEY": "sk-completion",
            },
        ),
        (
            "EMBEDDING_PROVIDER",
            "EMBEDDING_MODEL",
            {
                "EMBEDDING_BASE_URL": "https://embedding.example.test/v1",
                "EMBEDDING_API_KEY": "sk-embedding",
            },
        ),
    ],
)
def test_openai_compatible_requires_explicit_model(
    monkeypatch, provider_key, model_key, extra_env
):
    env = {
        "CHAT_PROVIDER": "ollama",
        "CHAT_MODEL": "qwen3.5:2b",
        "COMPLETION_PROVIDER": "ollama",
        "COMPLETION_MODEL": "qwen3.5:2b",
        "EMBEDDING_PROVIDER": "ollama",
        "EMBEDDING_MODEL": "qwen3-embedding:0.6b",
        provider_key: "openai_compatible",
    }
    env.pop(model_key)
    env.update(extra_env)

    with pytest.raises(ValueError, match=model_key):
        reload_llm(monkeypatch, env)


def test_builds_ollama_clients(monkeypatch):
    llm = reload_llm(
        monkeypatch,
        {
            "CHAT_PROVIDER": "ollama",
            "CHAT_MODEL": "qwen3.5:7b",
            "CHAT_BASE_URL": "http://localhost:11434",
            "COMPLETION_PROVIDER": "ollama",
            "COMPLETION_MODEL": "qwen3.5:7b",
            "COMPLETION_BASE_URL": "http://localhost:11434",
            "EMBEDDING_PROVIDER": "ollama",
            "EMBEDDING_MODEL": "qwen3-embedding:0.6b",
            "EMBEDDING_BASE_URL": "http://localhost:11434",
        },
    )

    assert isinstance(llm.chat, FakeChatOllama)
    assert llm.chat.kwargs["model"] == "qwen3.5:7b"
    assert isinstance(llm.completion, FakeOllamaLLM)
    assert llm.completion.kwargs["model"] == "qwen3.5:7b"
    assert isinstance(llm.embedder, FakeOllamaEmbeddings)
    assert llm.embedder.kwargs["model"] == "qwen3-embedding:0.6b"


def test_builds_openai_compatible_chat_and_embeddings(monkeypatch):
    llm = reload_llm(
        monkeypatch,
        {
            "CHAT_PROVIDER": "openai_compatible",
            "CHAT_MODEL": "gpt-4.1-mini",
            "CHAT_BASE_URL": "https://chat.example.test/v1",
            "CHAT_API_KEY": "sk-chat",
            "COMPLETION_PROVIDER": "ollama",
            "COMPLETION_MODEL": "qwen3.5:2b",
            "EMBEDDING_PROVIDER": "openai_compatible",
            "EMBEDDING_MODEL": "text-embedding-3-large",
            "EMBEDDING_BASE_URL": "https://embedding.example.test/v1",
            "EMBEDDING_API_KEY": "sk-embedding",
        },
    )

    assert isinstance(llm.chat, FakeChatOpenAI)
    assert llm.chat.kwargs["model"] == "gpt-4.1-mini"
    assert llm.chat.kwargs["base_url"] == "https://chat.example.test/v1"
    assert llm.chat.kwargs["api_key"] == "sk-chat"
    assert isinstance(llm.embedder, FakeOpenAIEmbeddings)
    assert llm.embedder.kwargs["model"] == "text-embedding-3-large"
    assert llm.embedder.kwargs["base_url"] == "https://embedding.example.test/v1"


def test_openai_compatible_completion_adapter_stringifies_non_string_content(monkeypatch):
    llm = reload_llm(
        monkeypatch,
        {
            "CHAT_PROVIDER": "ollama",
            "CHAT_MODEL": "qwen3.5:2b",
            "COMPLETION_PROVIDER": "openai_compatible",
            "COMPLETION_MODEL": "gpt-4o-mini",
            "COMPLETION_BASE_URL": "https://completion.example.test/v1",
            "COMPLETION_API_KEY": "sk-completion",
            "EMBEDDING_PROVIDER": "ollama",
            "EMBEDDING_MODEL": "qwen3-embedding:0.6b",
        },
    )

    monkeypatch.setattr(
        llm.completion.client,
        "invoke",
        lambda messages, **kwargs: SimpleNamespace(content={"answer": 42}),
    )

    assert llm.completion.invoke("只返回一个词") == "{'answer': 42}"


def test_openai_compatible_completion_adapter_returns_text(monkeypatch):
    llm = reload_llm(
        monkeypatch,
        {
            "CHAT_PROVIDER": "ollama",
            "CHAT_MODEL": "qwen3.5:2b",
            "COMPLETION_PROVIDER": "openai_compatible",
            "COMPLETION_MODEL": "gpt-4o-mini",
            "COMPLETION_BASE_URL": "https://completion.example.test/v1",
            "COMPLETION_API_KEY": "sk-completion",
            "EMBEDDING_PROVIDER": "ollama",
            "EMBEDDING_MODEL": "qwen3-embedding:0.6b",
        },
    )

    assert llm.completion.invoke("只返回一个词") == "fake-openai-chat"


@pytest.mark.asyncio
async def test_openai_compatible_completion_adapter_ainvoke_returns_text(monkeypatch):
    llm = reload_llm(
        monkeypatch,
        {
            "CHAT_PROVIDER": "ollama",
            "CHAT_MODEL": "qwen3.5:2b",
            "COMPLETION_PROVIDER": "openai_compatible",
            "COMPLETION_MODEL": "gpt-4o-mini",
            "COMPLETION_BASE_URL": "https://completion.example.test/v1",
            "COMPLETION_API_KEY": "sk-completion",
            "EMBEDDING_PROVIDER": "ollama",
            "EMBEDDING_MODEL": "qwen3-embedding:0.6b",
        },
    )

    assert await llm.completion.ainvoke("只返回一个词") == "fake-openai-chat-async"


def test_invoke_llm_returns_chat_content(monkeypatch):
    llm = reload_llm(
        monkeypatch,
        {
            "CHAT_PROVIDER": "openai_compatible",
            "CHAT_MODEL": "gpt-4.1-mini",
            "CHAT_BASE_URL": "https://chat.example.test/v1",
            "CHAT_API_KEY": "sk-chat",
            "COMPLETION_PROVIDER": "ollama",
            "COMPLETION_MODEL": "qwen3.5:2b",
            "EMBEDDING_PROVIDER": "ollama",
            "EMBEDDING_MODEL": "qwen3-embedding:0.6b",
        },
    )

    assert llm.invoke_llm("你好") == "fake-openai-chat"


def test_stream_llm_yields_chat_chunks(monkeypatch):
    llm = reload_llm(
        monkeypatch,
        {
            "CHAT_PROVIDER": "ollama",
            "CHAT_MODEL": "qwen3.5:2b",
            "COMPLETION_PROVIDER": "openai_compatible",
            "COMPLETION_MODEL": "gpt-4o-mini",
            "COMPLETION_BASE_URL": "https://completion.example.test/v1",
            "COMPLETION_API_KEY": "sk-completion",
            "EMBEDDING_PROVIDER": "ollama",
            "EMBEDDING_MODEL": "qwen3-embedding:0.6b",
        },
    )

    assert "".join(llm.stream_llm("你好")) == "fake-ollama-stream"


@pytest.mark.asyncio
async def test_astream_llm_yields_chat_chunks(monkeypatch):
    llm = reload_llm(
        monkeypatch,
        {
            "CHAT_PROVIDER": "openai_compatible",
            "CHAT_MODEL": "gpt-4.1-mini",
            "CHAT_BASE_URL": "https://chat.example.test/v1",
            "CHAT_API_KEY": "sk-chat",
            "COMPLETION_PROVIDER": "ollama",
            "COMPLETION_MODEL": "qwen3.5:2b",
            "EMBEDDING_PROVIDER": "ollama",
            "EMBEDDING_MODEL": "qwen3-embedding:0.6b",
        },
    )

    parts = []
    async for chunk in llm.astream_llm("你好"):
        parts.append(chunk)

    assert "".join(parts) == "fake-openai-astream"
