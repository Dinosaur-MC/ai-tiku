"""
数据库会话管理
基于 SQLModel 实现，避免直接使用 SQL
"""

import os
from pathlib import Path
from typing import List, Optional
from sqlalchemy import Engine
from sqlmodel import SQLModel, create_engine, Session, select
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import FAISS
import faiss
import json

# 导入模型
from models import *

# 获取项目根目录
ROOT_DIR = Path(__file__).parent.parent

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

    def _get_session(self) -> Session:
        """获取数据库会话"""

        return Session(self.engine)

    def read_all[T: SQLModel](self, model: type[T]) -> List[T]:
        """读取所有数据"""

        with self._get_session() as session:
            return session.exec(select(model)).all()

    def read_one[T: SQLModel](self, model: type[T], id: int) -> Optional[T]:
        """读取一行数据"""

        with self._get_session() as session:
            return session.get(model, id)


class VectorStore:
    """FAISS 向量存储管理类"""

    def __init__(self, category_id: int = 0, category_name: Optional[str] = None):
        self.category_id = category_id
        self.category_name = category_name
        self.index_path = EMBEDDINGS_DIR / f"faiss_{category_id}.index"
        self.embedder = OllamaEmbeddings(
            model=os.environ.get("EMBEDDING_MODEL_NAME", "qwen3-embedding:0.6b")
        )
        self.index = None
        self.docstore = {}  # 存储 ID 到文档的映射

        if self.index_path.exists():
            self.load_index()

    def load_index(self):
        """加载 FAISS 索引"""
        self.index = faiss.read_index(str(self.index_path))
        # 同时加载 docstore
        docstore_path = self.index_path.with_suffix(".json")
        if docstore_path.exists():
            with open(docstore_path, "r", encoding="utf-8") as f:
                self.docstore = json.load(f)

    def save_index(self):
        """保存 FAISS 索引"""
        if self.index is not None:
            faiss.write_index(self.index, str(self.index_path))
            # 保存 docstore
            docstore_path = self.index_path.with_suffix(".json")
            with open(docstore_path, "w", encoding="utf-8") as f:
                json.dump(self.docstore, f, ensure_ascii=False, indent=2)

    # def add_documents(self, ...):
    #     """添加文档到向量库"""

    # def similarity_search(self, ...) -> List[Dict]:
    #     """相似度搜索"""

    def clear_index(self):
        """清空索引"""
        self.index = None
        self.docstore = {}
        if self.index_path.exists():
            self.index_path.unlink()
        docstore_path = self.index_path.with_suffix(".json")
        if docstore_path.exists():
            docstore_path.unlink()


# 单例模式
db = Database()
