"""
数据库会话管理
基于 SQLModel 实现，避免直接使用 SQL
"""

import os
from pathlib import Path
from typing import List, Optional, Dict, Literal
import pydantic
from sqlalchemy import Engine
from sqlmodel import SQLModel, create_engine, Session, select
from langchain_ollama import OllamaEmbeddings
import numpy as np
import faiss
import json

# 导入模型
from models import *

# 获取项目根目录
ROOT_DIR = Path(__file__).parent.parent.parent

DATA_DIR = ROOT_DIR / "data"

DB_PATH = DATA_DIR / "db.sqlite3"
EMBEDDINGS_DIR = DATA_DIR / "embeddings"

# 确保目录存在
DATA_DIR.mkdir(parents=True, exist_ok=True)
EMBEDDINGS_DIR.mkdir(parents=True, exist_ok=True)


def get_engine() -> Engine:
    """获取数据库引擎"""

    return create_engine(
        f"sqlite:///{DB_PATH}", echo=False, connect_args={"check_same_thread": False}
    )


def create_db_and_tables() -> None:
    """创建数据库和表"""

    engine = get_engine()
    SQLModel.metadata.create_all(engine)


def get_session():
    """获取数据库会话"""

    engine = get_engine()
    with Session(engine) as session:
        yield session


class Database:
    """数据库管理类"""

    def __init__(self):
        self.engine = get_engine()
        # 创建数据库和表
        SQLModel.metadata.create_all(self.engine)

    def get_session(self) -> Session:
        """获取数据库会话"""

        return Session(self.engine)

    def create[T: SQLModel](self, instance: T) -> T:
        """创建数据"""

        with self.get_session() as session:
            session.add(instance)
            session.commit()
            session.refresh(instance)
            return instance

    def create_many[T: SQLModel](self, instances: List[T]) -> List[T]:
        """创建多行数据"""

        with self.get_session() as session:
            session.add_all(instances)
            session.commit()
            session.refresh(instances)
            return instances

    def delete[T: SQLModel](self, instance: T) -> None:
        """删除数据"""

        with self.get_session() as session:
            session.delete(instance)
            session.commit()

    def delete_many[T: SQLModel](self, instances: List[T]) -> None:
        """批量删除数据"""

        with self.get_session() as session:
            for instance in instances:
                session.delete(instance)
            session.commit()

    def update[T: SQLModel](self, instance: T) -> T:
        """更新数据"""

        return self.create(instance)

    def update_many[T: SQLModel](self, instances: List[T]) -> List[T]:
        """批量更新数据"""

        return self.create_many(instances)

    def read_all[T: SQLModel](
        self, model: type[T], limit: int = None, offset: int = None
    ) -> List[T]:
        """读取所有数据"""

        with self.get_session() as session:
            return session.exec(select(model).offset(offset).limit(limit)).all()

    def read_one[T: SQLModel](self, model: type[T], id: int) -> Optional[T]:
        """读取一行数据"""

        with self.get_session() as session:
            return session.get(model, id)

    def read_by_condition[T: SQLModel](self, model: type[T], *whereclauses) -> List[T]:
        """根据条件读取数据"""

        with self.get_session() as session:
            return session.exec(select(model).where(*whereclauses)).all()

    def read_one_by_condition[T: SQLModel](
        self, model: type[T], *whereclauses
    ) -> Optional[T]:
        """根据条件读取一行数据"""

        with self.get_session() as session:
            return session.exec(select(model).where(*whereclauses)).first()


class VectorStore:
    """FAISS 向量存储管理类"""

    class EmbdQuestion(pydantic.BaseModel):
        """Question 数据模型"""

        id: int
        question_title: str
        question_options: Optional[str]
        answer_text: str
        question_type: Literal[
            "single", "multiple", "judgement", "completion", "essay", "unknown"
        ]
        source: Optional[str]
        text: str

    def __init__(self, category_id: int = 0, category_name: Optional[str] = None):
        self.category_id = category_id
        self.category_name = category_name
        self.index_path = EMBEDDINGS_DIR / f"faiss_{category_id}.index"
        self.embedder = OllamaEmbeddings(
            model=os.environ.get("EMBEDDING_MODEL_NAME", "qwen3-embedding:0.6b")
        )
        self.index: Optional[faiss.IndexHNSWFlat] = None
        self.docstore: Dict[str, VectorStore.EmbdQuestion] = {}  # 存储 ID 到文档的映射
        self.id_mapping: Dict[int, int] = {}  # 内部 ID -> 外部 Question ID 的映射
        self.next_internal_id: int = 0

        if self.index_path.exists():
            self.load_index()

    def load_index(self):
        """加载 FAISS 索引"""

        self.index = faiss.read_index(str(self.index_path))
        # 同时加载 docstore 和 id_mapping
        docstore_path = self.index_path.with_suffix(".json")
        if docstore_path.exists():
            with open(docstore_path, "r", encoding="utf-8") as f:
                data: Dict[str, Dict] = json.load(f)
                self.docstore = data.get("docstore", {})
                self.id_mapping = {
                    int(k): v for k, v in data.get("id_mapping", {}).items()
                }
                self.next_internal_id = data.get("next_internal_id", 0)

    def save_index(self):
        """保存 FAISS 索引"""

        if self.index is not None:
            faiss.write_index(self.index, str(self.index_path))
            # 保存 docstore 和 id_mapping
            docstore_path = self.index_path.with_suffix(".json")
            data = {
                "docstore": {k: v.model_dump() for k, v in self.docstore.items()},
                "id_mapping": self.id_mapping,
                "next_internal_id": self.next_internal_id,
            }
            with open(docstore_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    def _build_question_text(self, question: Question) -> str:
        """构建完整的题目标文本（题干 + 选项）"""

        text = question.question_title
        options = question.question_options
        if options:
            text += "\n" + options
        return text

    def add_documents(self, questions: List[Question]) -> List[int]:
        """
        添加题目文档到向量库

        Args:
            questions: 题目字典列表，每个字典包含 id, question_title, question_options, answer 等字段

        Returns:
            成功添加的内部 ID 列表
        """

        if not questions:
            return []

        # 提取文本并生成向量
        texts = []
        for q in questions:
            text = self._build_question_text(q)
            texts.append(text)

        # 生成嵌入向量
        embeddings = self.embedder.embed_documents(texts)
        embeddings_array = np.array(embeddings, dtype=np.float32)

        # 初始化或扩展索引
        dim = embeddings_array.shape[1]
        if self.index is None:
            # 创建新的 HNSW 索引
            self.index = faiss.IndexHNSWFlat(dim, 32)
            self.next_internal_id = 0

        # 添加到索引
        start_id = self.next_internal_id
        self.index.add(embeddings_array)

        # 更新 docstore 和 id_mapping
        internal_ids: List[int] = []
        for i, q in enumerate(questions):
            internal_id = start_id + i
            external_id = q.id

            # 存储完整文档信息
            self.docstore[str(internal_id)] = VectorStore.EmbdQuestion(
                id=external_id,
                question_title=q.question_title,
                question_options=q.question_options,
                answer_text=q.answer_text,
                question_type=q.question_type,
                source=q.source,
                text=texts[i],  # 用于精确匹配
            )

            # 记录内部 ID 到外部 ID 的映射
            self.id_mapping[internal_id] = external_id
            internal_ids.append(internal_id)

        self.next_internal_id = start_id + len(questions)

        # 保存索引
        self.save_index()

        return internal_ids

    def similarity_search(
        self,
        query: str,
        k: int = 10,
        subject_filter: Optional[str] = None,
        question_type_filter: Optional[str] = None,
        score_threshold: float = 0.7,
    ) -> List[Dict]:
        """
        相似度搜索

        Args:
            query: 查询文本
            k: 返回结果数量
            subject_filter: 学科领域过滤（暂未实现，预留）
            question_type_filter: 题目类型过滤
            score_threshold: 相似度阈值，低于此值的结果将被过滤

        Returns:
            匹配的题目列表，包含完整信息和相似度分数
        """

        if self.index is None or self.index.ntotal == 0:
            return []

        # 生成查询向量
        query_embedding = self.embedder.embed_query(query)
        query_array = np.array([query_embedding], dtype=np.float32)

        # 执行搜索（多取一些以备过滤）
        search_k = k * 2
        distances, indices = self.index.search(query_array, search_k)

        results: List[Dict] = []
        for i, (distance, internal_id) in enumerate(zip(distances[0], indices[0])):
            if internal_id == -1:  # FAISS 返回 -1 表示无效 ID
                continue

            # 计算相似度分数（余弦相似度转百分比）
            similarity_score = 1.0 - distance

            # 应用阈值过滤
            if similarity_score < score_threshold:
                continue

            # 获取文档
            doc = self.docstore.get(str(internal_id))
            if not doc:
                continue

            # 应用题目类型过滤
            if question_type_filter and doc.question_type != question_type_filter:
                continue

            # 应用学科领域过滤（如果实现了分类功能）
            if subject_filter:
                # TODO: 需要从数据库查询题目的学科领域
                pass

            # 添加结果
            results.append({**doc, "score": float(similarity_score), "rank": i + 1})

        # 按相似度排序并返回前 k 个
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:k]

    def exact_search(
        self,
        query: str,
        subject_filter: Optional[str] = None,
        question_type_filter: Optional[str] = None,
        limit: int = 10,
    ) -> List[dict]:
        """
        精确查找（基于关键词匹配）

        Args:
            query: 查询关键词
            subject_filter: 学科领域过滤
            question_type_filter: 题目类型过滤
            limit: 返回结果数量

        Returns:
            匹配的题目列表
        """

        results = []
        query_lower = query.lower()

        for doc_id, doc in self.docstore.items():
            text = doc.text

            # 简单的关键词匹配
            if query_lower not in text.lower():
                continue

            # 应用题目类型过滤
            if question_type_filter and doc.question_type != question_type_filter:
                continue

            # 应用学科领域过滤
            if subject_filter:
                # TODO: 需要实现学科领域过滤
                pass

            results.append(
                {**doc, "score": 1.0, "match_type": "exact"}  # 精确匹配给满分
            )

            if len(results) >= limit:
                break

        return results

    def search(
        self, query: str, k: int = 10, use_semantic: bool = True, **filters
    ) -> List[Dict]:
        """
        统一搜索接口（支持语义检索和精确查找）

        Args:
            query: 查询文本
            k: 返回结果数量
            use_semantic: 是否使用语义检索（默认 True）
            **filters: 过滤条件（subject_filter, question_type_filter, score_threshold）

        Returns:
            匹配的题目列表
        """

        if use_semantic:
            return self.similarity_search(query, k=k, **filters)
        else:
            return self.exact_search(
                query,
                subject_filter=filters.get("subject_filter"),
                question_type_filter=filters.get("question_type_filter"),
                limit=k,
            )

    def get_stats(self) -> Dict:
        """获取索引统计信息"""

        return {
            "category_id": self.category_id,
            "category_name": self.category_name,
            "total_documents": len(self.docstore),
            "index_exists": self.index is not None,
            "index_size": self.index.ntotal if self.index else 0,
            "file_path": str(self.index_path) if self.index_path.exists() else None,
        }


# 单例模式
db = Database()
