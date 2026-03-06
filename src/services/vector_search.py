from typing import Optional, List, Dict, Any
from db import db, VectorStore
import numpy as np


class VectorSearch:
    """向量搜索服务 - 负责常规的题目检索功能"""

    def __init__(self, category_id: int = 0):
        """
        初始化向量搜索服务

        Args:
            category_id: 题库分类 ID，默认为 0（全局题库）
        """
        self.vector_store = VectorStore(category_id=category_id)

    def search_similar(self, query_text: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        搜索相似题目

        Args:
            query_text: 查询的题目文本
            k: 返回的结果数量

        Returns:
            相似题目列表
        """
        return self.vector_store.similarity_search(query_text, k=k)

    def get_best_match(self, query_text: str) -> Optional[Dict[str, Any]]:
        """
        获取最匹配的题目

        Args:
            query_text: 查询的题目文本

        Returns:
            最匹配的题目字典，如果没有匹配则返回 None
        """
        results = self.search_similar(query_text, k=1)
        return results[0] if results else None

    def add_document(self, content: str, answer: str, metadata: Dict = None):
        """
        添加文档到向量库

        Args:
            content: 文档内容（题目）
            answer: 答案
            metadata: 额外元数据
        """
        doc_metadata = {"answer": answer}
        if metadata:
            doc_metadata.update(metadata)

        self.vector_store.add_documents(documents=[content], metadatas=[doc_metadata])

    def add_documents(
        self, contents: List[str], answers: List[str], metadatas: List[Dict] = None
    ):
        """
        批量添加文档到向量库

        Args:
            contents: 文档内容列表（题目列表）
            answers: 答案列表
            metadatas: 元数据列表
        """
        if metadatas is None:
            metadatas = [{} for _ in range(len(contents))]

        doc_metadatas = []
        for i, answer in enumerate(answers):
            meta = {"answer": answer}
            if i < len(metadatas) and metadatas[i]:
                meta.update(metadatas[i])
            doc_metadatas.append(meta)

        self.vector_store.add_documents(documents=contents, metadatas=doc_metadatas)


# 单例模式 - 全局向量搜索服务
vector_search = VectorSearch(category_id=0)
