"""
LLM 工具模块 - 基于 LangChain/LangGraph 最佳实践

提供:
1. 全局 LLM 实例 (chat, completion, embedder)
2. Agent Factory 函数 (create_agent, create_graph_agent)
3. 统一的配置管理
"""

import asyncio
import os
import time
from logging import getLogger
from typing import Callable, Dict, List, Literal, Optional

from langchain.agents import create_agent
from langchain.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_ollama import ChatOllama, OllamaEmbeddings, OllamaLLM
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langgraph.graph import END, START, MessagesState, StateGraph
from pydantic import BaseModel
from utils.vision_inputs import prepare_ollama_image_inputs

logger = getLogger(__name__)


# ==================== 配置管理 ====================

ProviderName = Literal["ollama", "openai_compatible"]


class ChatConfig(BaseModel):
    """Chat 模型配置"""

    provider: ProviderName
    model: str
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    temperature: float


class CompletionConfig(BaseModel):
    """Completion 模型配置"""

    provider: ProviderName
    model: str
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    temperature: float


class EmbeddingConfig(BaseModel):
    """Embedding 模型配置"""

    provider: ProviderName
    model: str
    base_url: Optional[str] = None
    api_key: Optional[str] = None


class VisionConfig(BaseModel):
    """Vision 模型配置"""

    provider: ProviderName
    model: str
    base_url: Optional[str] = None
    api_key: Optional[str] = None
    temperature: float


class LLMSettings(BaseModel):
    """按能力划分的 LLM 配置"""

    chat: ChatConfig
    completion: CompletionConfig
    embedding: EmbeddingConfig
    vision: Optional[VisionConfig] = None


def _read_temperature(name: str, default: float) -> float:
    raw = os.environ.get(name)
    return float(raw) if raw is not None else default


def _require(value: Optional[str], env_name: str, provider: str) -> str:
    if value:
        return value
    raise ValueError(f"{env_name} is required when provider={provider}")


def _read_provider_model(prefix: str, default_model: str) -> tuple[str, str]:
    provider = os.environ.get(f"{prefix}_PROVIDER", "ollama")
    if provider not in {"ollama", "openai_compatible"}:
        raise ValueError(f"unsupported {prefix}_PROVIDER '{provider}'")

    model = os.environ.get(f"{prefix}_MODEL")
    if provider == "openai_compatible":
        return provider, _require(model, f"{prefix}_MODEL", provider)

    return provider, model or default_model


def _read_optional_vision_config(default_temperature: float) -> Optional[VisionConfig]:
    provider = os.environ.get("VISION_PROVIDER")
    if not provider:
        return None
    if provider not in {"ollama", "openai_compatible"}:
        raise ValueError(f"unsupported VISION_PROVIDER '{provider}'")

    return VisionConfig(
        provider=provider,
        model=_require(os.environ.get("VISION_MODEL"), "VISION_MODEL", provider),
        base_url=os.environ.get("VISION_BASE_URL"),
        api_key=os.environ.get("VISION_API_KEY"),
        temperature=_read_temperature("VISION_TEMPERATURE", default_temperature),
    )


def _validate_provider_config(prefix: str, config: BaseModel) -> None:
    provider = getattr(config, "provider")
    if provider == "openai_compatible":
        _require(getattr(config, "base_url", None), f"{prefix}_BASE_URL", provider)
        _require(getattr(config, "api_key", None), f"{prefix}_API_KEY", provider)


RETRYABLE_STATUS_CODES = {429, 529, 401, 502}
NON_RETRYABLE_STATUS_CODES = {403, 404, 500}
MAX_RETRY_ATTEMPTS = 10


def _extract_status_code(exc: Exception) -> Optional[int]:
    value = getattr(exc, "status_code", None)
    if isinstance(value, int):
        return value
    response = getattr(exc, "response", None)
    response_status = getattr(response, "status_code", None)
    return response_status if isinstance(response_status, int) else None


def _is_retryable_exception(exc: Exception) -> bool:
    status_code = _extract_status_code(exc)
    if status_code in RETRYABLE_STATUS_CODES:
        return True
    if status_code in NON_RETRYABLE_STATUS_CODES:
        return False

    name = exc.__class__.__name__.lower()
    message = str(exc).lower()
    transient_markers = [
        "timeout",
        "timed out",
        "connection",
        "connect",
        "temporarily unavailable",
    ]
    return any(marker in name or marker in message for marker in transient_markers)


def _get_retry_delay(attempt: int) -> float:
    if attempt <= 3:
        return 1.0
    return float(2 ** (attempt - 3))


def _with_retry(func):
    for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
        try:
            return func()
        except Exception as exc:
            if attempt >= MAX_RETRY_ATTEMPTS or not _is_retryable_exception(exc):
                raise
            time.sleep(_get_retry_delay(attempt))


async def _with_retry_async(func):
    for attempt in range(1, MAX_RETRY_ATTEMPTS + 1):
        try:
            return await func()
        except Exception as exc:
            if attempt >= MAX_RETRY_ATTEMPTS or not _is_retryable_exception(exc):
                raise
            await asyncio.sleep(_get_retry_delay(attempt))


def get_llm_settings() -> LLMSettings:
    """从环境变量获取按能力划分的 LLM 配置"""

    default_temperature = float(os.environ.get("MODEL_TEMPERATURE", "0.1"))
    chat_provider, chat_model = _read_provider_model("CHAT", "qwen3.5:2b")
    completion_provider, completion_model = _read_provider_model(
        "COMPLETION", "qwen3.5:2b"
    )
    embedding_provider, embedding_model = _read_provider_model(
        "EMBEDDING", "nomic-embed-text"
    )
    vision_config = _read_optional_vision_config(default_temperature)
    settings = LLMSettings(
        chat=ChatConfig(
            provider=chat_provider,
            model=chat_model,
            base_url=os.environ.get("CHAT_BASE_URL"),
            api_key=os.environ.get("CHAT_API_KEY"),
            temperature=_read_temperature("CHAT_TEMPERATURE", default_temperature),
        ),
        completion=CompletionConfig(
            provider=completion_provider,
            model=completion_model,
            base_url=os.environ.get("COMPLETION_BASE_URL"),
            api_key=os.environ.get("COMPLETION_API_KEY"),
            temperature=_read_temperature(
                "COMPLETION_TEMPERATURE", default_temperature
            ),
        ),
        embedding=EmbeddingConfig(
            provider=embedding_provider,
            model=embedding_model,
            base_url=os.environ.get("EMBEDDING_BASE_URL"),
            api_key=os.environ.get("EMBEDDING_API_KEY"),
        ),
        vision=vision_config,
    )
    _validate_provider_config("CHAT", settings.chat)
    _validate_provider_config("COMPLETION", settings.completion)
    _validate_provider_config("EMBEDDING", settings.embedding)
    if settings.vision is not None:
        _validate_provider_config("VISION", settings.vision)
    return settings


# ==================== 全局 LLM 实例 ====================

settings = get_llm_settings()


class OpenAICompatibleCompletionAdapter:
    def __init__(self, client: ChatOpenAI):
        self.client = client

    @staticmethod
    def _as_text(response) -> str:
        content = getattr(response, "content", response)
        return content if isinstance(content, str) else str(content)

    def invoke(self, prompt: str, **kwargs) -> str:
        response = self.client.invoke([HumanMessage(content=prompt)], **kwargs)
        return self._as_text(response)

    async def ainvoke(self, prompt: str, **kwargs) -> str:
        response = await self.client.ainvoke([HumanMessage(content=prompt)], **kwargs)
        return self._as_text(response)


class RetryingChatModel:
    def __init__(self, client):
        self.client = client

    @property
    def __class__(self):
        return self.client.__class__

    def invoke(self, messages, **kwargs):
        return _with_retry(lambda: self.client.invoke(messages, **kwargs))

    async def ainvoke(self, messages, **kwargs):
        return await _with_retry_async(lambda: self.client.ainvoke(messages, **kwargs))

    def stream(self, messages, **kwargs):
        return self.client.stream(messages, **kwargs)

    async def astream(self, messages, **kwargs):
        async for chunk in self.client.astream(messages, **kwargs):
            yield chunk

    def __getattr__(self, name):
        return getattr(self.client, name)


class RetryingEmbeddings:
    def __init__(self, client):
        self.client = client

    @property
    def __class__(self):
        return self.client.__class__

    def embed_query(self, text: str):
        return _with_retry(lambda: self.client.embed_query(text))

    def embed_documents(self, texts):
        return _with_retry(lambda: self.client.embed_documents(texts))

    def __getattr__(self, name):
        return getattr(self.client, name)


class RetryingCompletionModel:
    def __init__(self, client):
        self.client = client

    @property
    def __class__(self):
        return self.client.__class__

    def invoke(self, prompt: str, **kwargs):
        return _with_retry(lambda: self.client.invoke(prompt, **kwargs))

    async def ainvoke(self, prompt: str, **kwargs):
        return await _with_retry_async(lambda: self.client.ainvoke(prompt, **kwargs))

    def __getattr__(self, name):
        return getattr(self.client, name)


class OllamaVisionAdapter:
    def __init__(self, client: OllamaLLM):
        self.client = client

    def invoke(self, prompt: str, image_urls: List[str], **kwargs) -> str:
        prepared = prepare_ollama_image_inputs(
            image_urls,
            allow_remote_urls=True,
        )
        images = [item.value for item in prepared]
        bound = self.client.bind(images=images)
        return str(bound.invoke(prompt, **kwargs))


class OpenAICompatibleVisionAdapter:
    def __init__(self, client: ChatOpenAI):
        self.client = client

    @staticmethod
    def _as_text(response) -> str:
        content = getattr(response, "content", response)
        return content if isinstance(content, str) else str(content)

    def invoke(self, prompt: str, image_urls: List[str], **kwargs) -> str:
        content = [{"type": "text", "text": prompt}]
        content.extend(
            {"type": "image_url", "image_url": {"url": image_url}}
            for image_url in image_urls
        )
        response = self.client.invoke([HumanMessage(content=content)], **kwargs)
        return self._as_text(response)

    async def ainvoke(self, prompt: str, image_urls: List[str], **kwargs) -> str:
        content = [{"type": "text", "text": prompt}]
        content.extend(
            {"type": "image_url", "image_url": {"url": image_url}}
            for image_url in image_urls
        )
        response = await self.client.ainvoke([HumanMessage(content=content)], **kwargs)
        return self._as_text(response)


def build_chat_model(config: ChatConfig):
    if config.provider == "ollama":
        client = ChatOllama(
            model=config.model,
            temperature=config.temperature,
            base_url=config.base_url,
            reasoning=False,
        )
    else:
        client = ChatOpenAI(
            model=config.model,
            temperature=config.temperature,
            base_url=config.base_url,
            api_key=config.api_key,
        )
    return RetryingChatModel(client)


def build_completion_model(config: CompletionConfig):
    if config.provider == "ollama":
        return RetryingCompletionModel(
            OllamaLLM(
                model=config.model,
                temperature=config.temperature,
                base_url=config.base_url,
                reasoning=False,
            )
        )
    return RetryingCompletionModel(
        OpenAICompatibleCompletionAdapter(
            ChatOpenAI(
                model=config.model,
                temperature=config.temperature,
                base_url=config.base_url,
                api_key=config.api_key,
            )
        )
    )


def build_embedding_model(config: EmbeddingConfig):
    if config.provider == "ollama":
        client = OllamaEmbeddings(
            model=config.model,
            base_url=config.base_url,
        )
    else:
        client = OpenAIEmbeddings(
            model=config.model,
            base_url=config.base_url,
            api_key=config.api_key,
        )
    return RetryingEmbeddings(client)


def build_vision_model(config: VisionConfig):
    if config.provider == "ollama":
        return OllamaVisionAdapter(
            OllamaLLM(
                model=config.model,
                temperature=config.temperature,
                base_url=config.base_url,
                reasoning=False,
            )
        )

    return OpenAICompatibleVisionAdapter(
        ChatOpenAI(
            model=config.model,
            temperature=config.temperature,
            base_url=config.base_url,
            api_key=config.api_key,
        )
    )


chat = build_chat_model(settings.chat)
completion = build_completion_model(settings.completion)
embedder = build_embedding_model(settings.embedding)
vision = build_vision_model(settings.vision) if settings.vision is not None else None


def vision_enabled() -> bool:
    return vision is not None


def analyze_images(prompt: str, image_urls: List[str], **kwargs) -> str:
    if vision is None:
        raise ValueError("vision model is not configured")
    return vision.invoke(prompt, image_urls, **kwargs)


# ==================== Agent Factory ====================


def create_graph_agent(
    nodes: Dict[str, Callable],
    edges: List[tuple],
    conditional_edges: Optional[List[tuple]] = None,
    entry_point: str = "start",
):
    """
    创建自定义 Graph Agent

    Args:
        nodes: 节点字典 {node_name: node_function}
        edges: 边列表 [(from, to), ...]
        conditional_edges: 条件边列表 [(from, condition_func, mapping), ...]
        entry_point: 入口节点名称

    Returns:
        编译后的 Graph

    示例:
        ```python
        def node1(state):
            return {"messages": [...]}

        def node2(state):
            return {"messages": [...]}

        def condition(state):
            return "node2" if some_condition else END

        agent = create_graph_agent(
            nodes={"node1": node1, "node2": node2},
            edges=[("start", "node1")],
            conditional_edges=[("node1", condition, {"node2": "node2", END: END})]
        )
        ```
    """
    workflow = StateGraph(MessagesState)

    for name, func in nodes.items():
        workflow.add_node(name, func)

    workflow.add_edge(START, entry_point)

    for from_node, to_node in edges:
        if to_node == END:
            workflow.add_edge(from_node, END)
        else:
            workflow.add_edge(from_node, to_node)

    if conditional_edges:
        for from_node, condition_func, mapping in conditional_edges:
            workflow.add_conditional_edges(from_node, condition_func, mapping)

    return workflow.compile()


# ==================== 便捷函数 ====================


def invoke_llm(
    prompt: str,
    system_prompt: Optional[str] = None,
    **kwargs,
) -> str:
    """
    便捷调用 LLM

    Args:
        prompt: 用户提示词
        system_prompt: 系统提示词（可选）
        **kwargs: 其他参数

    Returns:
        LLM 响应文本
    """

    messages = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    messages.append(HumanMessage(content=prompt))

    response = chat.invoke(messages, **kwargs)
    return response.content


def stream_llm(
    prompt: str,
    system_prompt: Optional[str] = None,
    **kwargs,
):
    """
    流式调用 LLM

    Args:
        prompt: 用户提示词
        system_prompt: 系统提示词（可选）
        **kwargs: 其他参数

    Yields:
        文本片段
    """

    messages = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    messages.append(HumanMessage(content=prompt))

    for chunk in chat.stream(messages, **kwargs):
        if hasattr(chunk, "content"):
            yield chunk.content


async def ainvoke_llm(
    prompt: str,
    system_prompt: Optional[str] = None,
    timeout: Optional[float] = 30.0,
    **kwargs,
) -> str:
    """
    异步调用 LLM

    Args:
        prompt: 用户提示词
        system_prompt: 系统提示词（可选）
        timeout: 超时时间（秒），默认 30 秒，None 表示不限制
        **kwargs: 其他参数

    Returns:
        LLM 响应文本

    Raises:
        TimeoutError: 超过指定时间未返回结果
    """
    messages = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    messages.append(HumanMessage(content=prompt))

    try:
        if timeout is not None:
            response = await asyncio.wait_for(
                chat.ainvoke(messages, **kwargs), timeout=timeout
            )
        else:
            response = await chat.ainvoke(messages, **kwargs)
        return response.content
    except asyncio.TimeoutError:
        logger.warning(f"LLM 异步调用超时（{timeout}秒）")
        raise
    except Exception as e:
        logger.error(f"LLM 异步调用失败：{str(e)}")
        raise


async def astream_llm(
    prompt: str,
    system_prompt: Optional[str] = None,
    **kwargs,
):
    """
    异步流式调用 LLM

    Args:
        prompt: 用户提示词
        system_prompt: 系统提示词（可选）
        **kwargs: 其他参数

    Yields:
        文本片段
    """

    messages = []
    if system_prompt:
        messages.append(SystemMessage(content=system_prompt))
    messages.append(HumanMessage(content=prompt))

    async for chunk in chat.astream(messages, **kwargs):
        if hasattr(chunk, "content"):
            yield chunk.content


# ==================== 测试代码 ====================

if __name__ == "__main__":
    import sys

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    async def test_llm():
        print("=" * 60)
        print("测试 LLM 模块")
        print("=" * 60)

        print("\n【测试 1】简单调用:")
        result = invoke_llm("中国梦是什么？")
        print(f"结果：{result}")

        print("\n【测试 2】流式调用:")
        print("回答：", end="", flush=True)
        for chunk in stream_llm("简要介绍马克思主义"):
            print(chunk, end="", flush=True)
        print()

        print("\n【测试 3】带系统提示词:")
        result = invoke_llm(
            "谁是矛盾论的作者？",
            system_prompt="你是一个专业的题库助手，只输出答案，不做解释。",
        )
        print(f"结果：{result}")

        print("\n【测试 4】创建简单 Agent:")
        agent = create_agent(model=chat)
        result = agent.invoke({"messages": [HumanMessage(content="你好")]})
        print(f"Agent 响应：{result['messages'][-1].content}")

        print("\n【测试 5】创建带工具的 Agent:")

        @tool
        def search(query: str) -> str:
            """搜索工具"""
            print(f"搜索'{query}'...")
            return (
                f"搜索'{query}'的结果:"
                + """### 人工智能（AI）是指计算机系统执行通常与人类智慧相关的任务的能力

人工智能（AI）是指计算机系统执行通常与人类智慧相关的任务的能力，例如学习、推理、解决问题、感知和决策。人工智能是计算机科学的一个研究领域，致力于开发和研究使机器能够感知其环境并利用学习和智能采取行动以最大限度地提高其实现既定目标的可能性的方法和软件。

人工智能的发展历程可以追溯到20世纪50年代，当时科学家们开始探索如何让计算机模拟人类的思维过程。经过几十年的努力，AI经历了从符号主义到连接主义的转变，从专家系统到机器学习的飞跃。

人工智能的核心特性包括学习能力、推理能力、感知能力、自主决策能力等。这些特性使得AI系统能够从大量数据中提取有用信息，不断优化自身的性能，并在复杂多变的环境中自主决策、优化性能并创造价值。

人工智能的应用领域广泛，包括医疗、金融、教育、交通、制造业等。AI在医疗领域中，能够通过数据分析以及演算方式等对患者的病情、诊断和治疗方案等做出准确判断，让医生做出更好的医疗决策，提高患者的生存率。

人工智能的普及和应用将进一步推动经济的发展。在日益激烈的现代经济环境中，企业需要提高效率并降低成本，AI可提高企业的竞争力和经济效益，推动全球经济更好、更快速的发展。

总的来说，人工智能是一种富有活力的技术，越来越多地渗透到人类社会各个领域，提高人类生活质量，推动科技发展和经济进步，都具有十分重要的作用。"""
            )

        agent_with_tools = create_agent(model=chat, tools=[search])
        result = agent_with_tools.invoke(
            {"messages": [HumanMessage(content="请搜索'人工智能'")]}
        )
        print(f"Agent with tools 响应：{result['messages'][-1].content}")

        print("\n【测试 6】异步调用:")
        result = await ainvoke_llm("用一句话总结量子力学")
        print(f"结果：{result}")

        print("\n" + "=" * 60)
        print("✅ 所有测试完成！")
        print("=" * 60)

    asyncio.run(test_llm())
