import os
from langchain_ollama import OllamaLLM, OllamaEmbeddings

llm = OllamaLLM(model=os.environ.get("MODEL_NAME", "qwen3"), temperature=0.1)


def generate_completion(prompt, stream=False):
    if stream:
        return llm.stream(input=prompt)
    return llm.invoke(input=prompt)


async def async_generate_completion(prompt, stream=False):
    if stream:
        return await llm.astream(input=prompt)
    return await llm.ainvoke(input=prompt)


embedder = OllamaEmbeddings(model=os.environ.get("MODEL_NAME", "nomic-embed-text"))


def embed_documents(content):
    return embedder.embed_documents(content)


def embed_query(content):
    return embedder.embed_query(content)
