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
        self.bound_invocations = []

    def invoke(self, prompt, **kwargs):
        return "fake-ollama-completion"

    async def ainvoke(self, prompt, **kwargs):
        return "fake-ollama-completion-async"

    def bind(self, **kwargs):
        parent = self
        images = kwargs.get("images", [])

        class BoundModel:
            def invoke(self, prompt, **invoke_kwargs):
                parent.bound_invocations.append((prompt, images, invoke_kwargs))
                return "fake-ollama-completion"

        return BoundModel()


class FakeChatOpenAI:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.invocations = []

    def invoke(self, messages, **kwargs):
        self.invocations.append(("invoke", messages, kwargs))
        return SimpleNamespace(content="fake-openai-chat")

    async def ainvoke(self, messages, **kwargs):
        self.invocations.append(("ainvoke", messages, kwargs))
        return SimpleNamespace(content="fake-openai-chat-async")

    def stream(self, messages, **kwargs):
        self.invocations.append(("stream", messages, kwargs))
        yield SimpleNamespace(content="fake-")
        yield SimpleNamespace(content="openai-")
        yield SimpleNamespace(content="stream")

    async def astream(self, messages, **kwargs):
        self.invocations.append(("astream", messages, kwargs))
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
        "VISION_PROVIDER",
        "VISION_MODEL",
        "VISION_BASE_URL",
        "VISION_API_KEY",
        "VISION_TEMPERATURE",
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
        llm.completion.client.client,
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


def test_vision_settings_load_when_fully_configured(monkeypatch):
    llm = reload_llm(
        monkeypatch,
        {
            "CHAT_PROVIDER": "ollama",
            "CHAT_MODEL": "qwen3.5:2b",
            "COMPLETION_PROVIDER": "ollama",
            "COMPLETION_MODEL": "qwen3.5:2b",
            "EMBEDDING_PROVIDER": "ollama",
            "EMBEDDING_MODEL": "qwen3-embedding:0.6b",
            "VISION_PROVIDER": "openai_compatible",
            "VISION_MODEL": "gpt-4.1-mini",
            "VISION_BASE_URL": "https://vision.example.test/v1",
            "VISION_API_KEY": "sk-vision",
            "VISION_TEMPERATURE": "0.4",
        },
    )

    assert llm.settings.vision is not None
    assert llm.settings.vision.provider == "openai_compatible"
    assert llm.settings.vision.model == "gpt-4.1-mini"
    assert llm.settings.vision.base_url == "https://vision.example.test/v1"
    assert llm.settings.vision.api_key == "sk-vision"
    assert llm.settings.vision.temperature == 0.4
    assert llm.vision_enabled() is True
    assert llm.vision is not None


def test_vision_disabled_when_provider_not_set(monkeypatch):
    llm = reload_llm(
        monkeypatch,
        {
            "CHAT_PROVIDER": "ollama",
            "CHAT_MODEL": "qwen3.5:2b",
            "COMPLETION_PROVIDER": "ollama",
            "COMPLETION_MODEL": "qwen3.5:2b",
            "EMBEDDING_PROVIDER": "ollama",
            "EMBEDDING_MODEL": "qwen3-embedding:0.6b",
        },
    )

    assert llm.settings.vision is None
    assert llm.vision is None
    assert llm.vision_enabled() is False


@pytest.mark.parametrize(
    "missing_key",
    ["VISION_MODEL", "VISION_BASE_URL", "VISION_API_KEY"],
)
def test_incomplete_openai_compatible_vision_config_raises_value_error(
    monkeypatch, missing_key
):
    env = {
        "CHAT_PROVIDER": "ollama",
        "CHAT_MODEL": "qwen3.5:2b",
        "COMPLETION_PROVIDER": "ollama",
        "COMPLETION_MODEL": "qwen3.5:2b",
        "EMBEDDING_PROVIDER": "ollama",
        "EMBEDDING_MODEL": "qwen3-embedding:0.6b",
        "VISION_PROVIDER": "openai_compatible",
        "VISION_MODEL": "gpt-4.1-mini",
        "VISION_BASE_URL": "https://vision.example.test/v1",
        "VISION_API_KEY": "sk-vision",
    }
    env.pop(missing_key)

    with pytest.raises(ValueError, match=missing_key):
        reload_llm(monkeypatch, env)


def test_openai_compatible_vision_adapter_sends_image_content_blocks(monkeypatch):
    llm = reload_llm(
        monkeypatch,
        {
            "CHAT_PROVIDER": "ollama",
            "CHAT_MODEL": "qwen3.5:2b",
            "COMPLETION_PROVIDER": "ollama",
            "COMPLETION_MODEL": "qwen3.5:2b",
            "EMBEDDING_PROVIDER": "ollama",
            "EMBEDDING_MODEL": "qwen3-embedding:0.6b",
            "VISION_PROVIDER": "openai_compatible",
            "VISION_MODEL": "gpt-4.1-mini",
            "VISION_BASE_URL": "https://vision.example.test/v1",
            "VISION_API_KEY": "sk-vision",
        },
    )

    assert llm.analyze_images(
        "请描述图片内容",
        ["https://cdn.example.test/1.png", "https://cdn.example.test/2.png"],
    ) == "fake-openai-chat"

    method, messages, kwargs = llm.vision.client.invocations[0]
    assert method == "invoke"
    assert kwargs == {}
    assert messages[0].content == [
        {"type": "text", "text": "请描述图片内容"},
        {
            "type": "image_url",
            "image_url": {"url": "https://cdn.example.test/1.png"},
        },
        {
            "type": "image_url",
            "image_url": {"url": "https://cdn.example.test/2.png"},
        },
    ]


def test_vision_settings_load_for_ollama_without_api_key(monkeypatch):
    llm = reload_llm(
        monkeypatch,
        {
            "CHAT_PROVIDER": "ollama",
            "CHAT_MODEL": "qwen3.5:2b",
            "COMPLETION_PROVIDER": "ollama",
            "COMPLETION_MODEL": "qwen3.5:2b",
            "EMBEDDING_PROVIDER": "ollama",
            "EMBEDDING_MODEL": "qwen3-embedding:0.6b",
            "VISION_PROVIDER": "ollama",
            "VISION_MODEL": "llava:7b",
            "VISION_BASE_URL": "http://localhost:11434",
        },
    )

    assert llm.settings.vision is not None
    assert llm.settings.vision.provider == "ollama"
    assert llm.settings.vision.model == "llava:7b"
    assert llm.settings.vision.base_url == "http://localhost:11434"
    assert llm.settings.vision.api_key is None
    assert llm.vision_enabled() is True


def test_vision_provider_ollama_requires_model(monkeypatch):
    with pytest.raises(ValueError, match="VISION_MODEL"):
        reload_llm(
            monkeypatch,
            {
                "CHAT_PROVIDER": "ollama",
                "CHAT_MODEL": "qwen3.5:2b",
                "COMPLETION_PROVIDER": "ollama",
                "COMPLETION_MODEL": "qwen3.5:2b",
                "EMBEDDING_PROVIDER": "ollama",
                "EMBEDDING_MODEL": "qwen3-embedding:0.6b",
                "VISION_PROVIDER": "ollama",
            },
        )


def test_vision_provider_rejects_unknown_value(monkeypatch):
    with pytest.raises(ValueError, match="unsupported VISION_PROVIDER"):
        reload_llm(
            monkeypatch,
            {
                "CHAT_PROVIDER": "ollama",
                "CHAT_MODEL": "qwen3.5:2b",
                "COMPLETION_PROVIDER": "ollama",
                "COMPLETION_MODEL": "qwen3.5:2b",
                "EMBEDDING_PROVIDER": "ollama",
                "EMBEDDING_MODEL": "qwen3-embedding:0.6b",
                "VISION_PROVIDER": "unknown_provider",
                "VISION_MODEL": "x",
            },
        )


def test_builds_ollama_vision_adapter(monkeypatch):
    llm = reload_llm(
        monkeypatch,
        {
            "CHAT_PROVIDER": "ollama",
            "CHAT_MODEL": "qwen3.5:2b",
            "COMPLETION_PROVIDER": "ollama",
            "COMPLETION_MODEL": "qwen3.5:2b",
            "EMBEDDING_PROVIDER": "ollama",
            "EMBEDDING_MODEL": "qwen3-embedding:0.6b",
            "VISION_PROVIDER": "ollama",
            "VISION_MODEL": "llava:7b",
        },
    )

    assert llm.vision is not None
    assert llm.vision.__class__.__name__ == "OllamaVisionAdapter"


def test_ollama_vision_adapter_prefers_remote_urls(monkeypatch):
    llm = reload_llm(
        monkeypatch,
        {
            "CHAT_PROVIDER": "ollama",
            "CHAT_MODEL": "qwen3.5:2b",
            "COMPLETION_PROVIDER": "ollama",
            "COMPLETION_MODEL": "qwen3.5:2b",
            "EMBEDDING_PROVIDER": "ollama",
            "EMBEDDING_MODEL": "qwen3-embedding:0.6b",
            "VISION_PROVIDER": "ollama",
            "VISION_MODEL": "llava:7b",
        },
    )

    monkeypatch.setattr(
        llm,
        "prepare_ollama_image_inputs",
        lambda image_urls, raw_images=None, allow_remote_urls=True: [
            SimpleNamespace(kind="url", value=image_urls[0])
        ],
    )

    assert llm.analyze_images("describe", ["https://img.test/a.png"]) == "fake-ollama-completion"
    assert llm.vision.client.kwargs["model"] == "llava:7b"
    prompt, images, kwargs = llm.vision.client.bound_invocations[0]
    assert prompt == "describe"
    assert images == ["https://img.test/a.png"]
    assert kwargs == {}


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


class RetryableProviderError(Exception):
    def __init__(self, status_code=None):
        super().__init__(f"retryable:{status_code}")
        self.status_code = status_code


class NonRetryableProviderError(Exception):
    def __init__(self, status_code=None):
        super().__init__(f"non_retryable:{status_code}")
        self.status_code = status_code


def test_retry_delay_schedule():
    import utils.llm as llm

    assert llm._get_retry_delay(1) == 1.0
    assert llm._get_retry_delay(2) == 1.0
    assert llm._get_retry_delay(3) == 1.0
    assert llm._get_retry_delay(4) == 2.0
    assert llm._get_retry_delay(5) == 4.0


@pytest.mark.parametrize("status_code", [429, 529, 401, 502])
def test_retryable_http_statuses(status_code):
    import utils.llm as llm

    assert llm._is_retryable_exception(RetryableProviderError(status_code)) is True


@pytest.mark.parametrize("status_code", [403, 404, 500])
def test_non_retryable_http_statuses(status_code):
    import utils.llm as llm

    assert llm._is_retryable_exception(NonRetryableProviderError(status_code)) is False


def test_sync_retry_stops_on_non_retryable(monkeypatch):
    import utils.llm as llm

    calls = {"count": 0}

    def fail_once():
        calls["count"] += 1
        raise NonRetryableProviderError(404)

    with pytest.raises(NonRetryableProviderError):
        llm._with_retry(fail_once)

    assert calls["count"] == 1


def test_sync_retry_retries_then_succeeds(monkeypatch):
    import utils.llm as llm

    calls = {"count": 0}
    delays = []

    def fake_sleep(seconds):
        delays.append(seconds)

    monkeypatch.setattr(llm.time, "sleep", fake_sleep)

    def flaky():
        calls["count"] += 1
        if calls["count"] < 4:
            raise RetryableProviderError(429)
        return "ok"

    assert llm._with_retry(flaky) == "ok"
    assert calls["count"] == 4
    assert delays == [1.0, 1.0, 1.0]


def test_sync_retry_exhausts_after_ten_attempts(monkeypatch):
    import utils.llm as llm

    calls = {"count": 0}
    monkeypatch.setattr(llm.time, "sleep", lambda seconds: None)

    def always_fail():
        calls["count"] += 1
        raise RetryableProviderError(502)

    with pytest.raises(RetryableProviderError):
        llm._with_retry(always_fail)

    assert calls["count"] == 10


@pytest.mark.asyncio
async def test_async_retry_retries_then_succeeds(monkeypatch):
    import utils.llm as llm

    calls = {"count": 0}
    delays = []

    async def fake_sleep(seconds):
        delays.append(seconds)

    monkeypatch.setattr(llm.asyncio, "sleep", fake_sleep)

    async def flaky():
        calls["count"] += 1
        if calls["count"] < 3:
            raise RetryableProviderError(429)
        return "ok"

    assert await llm._with_retry_async(flaky) == "ok"
    assert calls["count"] == 3
    assert delays == [1.0, 1.0]


def test_completion_adapter_stringifies_non_string_content(monkeypatch):
    import utils.llm as llm

    client = FakeChatOpenAI(model="gpt-4o-mini")
    client.invoke = lambda messages, **kwargs: SimpleNamespace(content={"answer": "ok"})
    adapter = llm.OpenAICompatibleCompletionAdapter(client)

    assert adapter.invoke("hello") == "{'answer': 'ok'}"


def test_openai_compatible_completion_adapter_does_not_retry_internally(monkeypatch):
    import utils.llm as llm

    calls = {"count": 0}
    monkeypatch.setattr(llm.time, "sleep", lambda seconds: None)

    client = FakeChatOpenAI(model="gpt-4o-mini")

    def always_fail(messages, **kwargs):
        calls["count"] += 1
        raise RetryableProviderError(429)

    client.invoke = always_fail
    adapter = llm.OpenAICompatibleCompletionAdapter(client)

    with pytest.raises(RetryableProviderError):
        adapter.invoke("hello")

    assert calls["count"] == 1


@pytest.mark.asyncio
async def test_openai_compatible_completion_adapter_does_not_retry_internally_async(
    monkeypatch,
):
    import utils.llm as llm

    calls = {"count": 0}

    async def fake_sleep(seconds):
        return None

    monkeypatch.setattr(llm.asyncio, "sleep", fake_sleep)

    client = FakeChatOpenAI(model="gpt-4o-mini")

    async def always_fail(messages, **kwargs):
        calls["count"] += 1
        raise RetryableProviderError(429)

    client.ainvoke = always_fail
    adapter = llm.OpenAICompatibleCompletionAdapter(client)

    with pytest.raises(RetryableProviderError):
        await adapter.ainvoke("hello")

    assert calls["count"] == 1


def test_builds_retrying_openai_compatible_completion_model(monkeypatch):
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

    assert isinstance(llm.completion, llm.RetryingCompletionModel)
    assert isinstance(llm.completion.client, llm.OpenAICompatibleCompletionAdapter)


def test_retrying_completion_model_retries_ollama_completion(monkeypatch):
    import utils.llm as llm

    calls = {"count": 0}
    delays = []

    def fake_sleep(seconds):
        delays.append(seconds)

    monkeypatch.setattr(llm.time, "sleep", fake_sleep)

    client = FakeOllamaLLM(model="qwen3.5:2b")

    def flaky(prompt, **kwargs):
        calls["count"] += 1
        if calls["count"] < 4:
            raise RetryableProviderError(429)
        return "ok"

    client.invoke = flaky
    completion = llm.RetryingCompletionModel(client)

    assert completion.invoke("hello") == "ok"
    assert calls["count"] == 4
    assert delays == [1.0, 1.0, 1.0]

