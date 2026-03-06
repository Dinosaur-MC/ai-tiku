import os
from typing import AsyncGenerator, Generator, List, Dict, Any
from langchain_ollama import OllamaEmbeddings, OllamaLLM, ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage

# 初始化 Embeddings
embedder = OllamaEmbeddings(
    model=os.environ.get("EMBEDDING_MODEL_NAME", "nomic-embed-text")
)

# 初始化 Completion 模型
completion = OllamaLLM(
    model=os.environ.get("MODEL_NAME", "qwen3.5:2b"),
    temperature=float(os.environ.get("MODEL_TEMPERATURE", "0.1")),
)

# 初始化 Chat 模型
chat = ChatOllama(
    model=os.environ.get("MODEL_NAME", "qwen3.5:2b"),
    temperature=float(os.environ.get("MODEL_TEMPERATURE", "0.1")),
)


class LLMWrapper:
    """LLM 包装类 - 提供流式和异步支持"""

    def __init__(self, completion_model=None, chat_model=None):
        self.completion = completion_model or completion
        self.chat = chat_model or chat

    def invoke(self, prompt: str, **kwargs) -> str:
        """同步调用 LLM"""
        response = self.completion.invoke(prompt, **kwargs)
        return response.content if hasattr(response, "content") else response

    async def ainvoke(self, prompt: str, **kwargs) -> str:
        """异步调用 LLM"""
        response = await self.completion.ainvoke(prompt, **kwargs)
        return response.content if hasattr(response, "content") else response

    def stream(self, prompt: str, **kwargs) -> Generator[str, None, None]:
        """流式生成（同步）"""
        for chunk in self.completion.stream(prompt, **kwargs):
            yield chunk.content if hasattr(chunk, "content") else chunk

    async def astream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """流式生成（异步）"""
        async for chunk in self.completion.astream(prompt, **kwargs):
            yield chunk.content if hasattr(chunk, "content") else chunk

    def chat_invoke(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """聊天模式调用"""
        # 转换消息格式
        langchain_messages = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if role == "system":
                langchain_messages.append(SystemMessage(content=content))
            elif role == "user":
                langchain_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                langchain_messages.append(AIMessage(content=content))

        response = self.chat.invoke(langchain_messages, **kwargs)
        return response.content if hasattr(response, "content") else response

    async def chat_ainvoke(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """聊天模式异步调用"""
        langchain_messages = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if role == "system":
                langchain_messages.append(SystemMessage(content=content))
            elif role == "user":
                langchain_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                langchain_messages.append(AIMessage(content=content))

        response = await self.chat.ainvoke(langchain_messages, **kwargs)
        return response.content if hasattr(response, "content") else response

    def chat_stream(
        self, messages: List[Dict[str, str]], **kwargs
    ) -> Generator[str, None, None]:
        """聊天模式流式生成"""
        langchain_messages = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if role == "system":
                langchain_messages.append(SystemMessage(content=content))
            elif role == "user":
                langchain_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                langchain_messages.append(AIMessage(content=content))

        for chunk in self.chat.stream(langchain_messages, **kwargs):
            yield chunk.content if hasattr(chunk, "content") else chunk

    async def chat_astream(
        self, messages: List[Dict[str, str]], **kwargs
    ) -> AsyncGenerator[str, None]:
        """聊天模式异步流式生成"""
        langchain_messages = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if role == "system":
                langchain_messages.append(SystemMessage(content=content))
            elif role == "user":
                langchain_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                langchain_messages.append(AIMessage(content=content))

        async for chunk in self.chat.astream(langchain_messages, **kwargs):
            yield chunk.content if hasattr(chunk, "content") else chunk


# 创建全局 LLM 包装实例
llm = LLMWrapper()


if __name__ == "__main__":
    import asyncio

    async def test_llm():
        print("Testing LLM...")

        # 测试普通调用
        query = "中国梦是什么？"
        result = llm.invoke(query)
        print(f"\n普通调用结果:")
        print(f"{result}")

        # 测试流式调用
        print("\n\n流式调用:")
        for chunk in llm.stream(query):
            print(chunk, end="", flush=True)

        # 测试聊天模式
        print("\n\n\n聊天模式:")
        messages = [
            {"role": "system", "content": "你是一个专业的助手。"},
            {"role": "user", "content": "你好，请介绍一下自己。"},
        ]
        result = llm.chat_invoke(messages)
        print(result)

        # 测试异步调用
        print("\n\n异步调用:")
        result = await llm.ainvoke(query)
        print(result)

    asyncio.run(test_llm())
