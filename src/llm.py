import os
from langchain_ollama import OllamaEmbeddings, OllamaLLM, ChatOllama

embedder = OllamaEmbeddings(
    model=os.environ.get("EMBEDDING_MODEL_NAME", "nomic-embed-text")
)
completion = OllamaLLM(
    model=os.environ.get("MODEL_NAME", "qwen3.5:2b"), temperature=0.1
)
chat = ChatOllama(model=os.environ.get("MODEL_NAME", "qwen3.5:2b"), temperature=0.1)


if __name__ == "__main__":
    query = "What is the meaning of life?"
    result = chat.invoke([query])
    print(result.content)
