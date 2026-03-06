"""
数据库会话管理和操作类
基于 SQLModel 实现，避免直接使用 SQL
"""
import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from sqlmodel import SQLModel, create_engine, Session, select
from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
import faiss
import numpy as np
import json

from models.token import ApiToken
from models.question import Question
from models.query_log import QueryLog
from models.category import Category
from models.question_category import QuestionCategory

# 获取项目根目录
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "db.sqlite3"
EMBEDDINGS_DIR = DATA_DIR / "embeddings"

# 确保目录存在
DATA_DIR.mkdir(exist_ok=True)
EMBEDDINGS_DIR.mkdir(exist_ok=True)


def get_engine():
    """获取数据库引擎"""
    return create_engine(
        f"sqlite:///{DB_PATH}",
        echo=False,
        connect_args={"check_same_thread": False}
    )


def create_db_and_tables():
    """创建数据库和表"""
    engine = get_engine()
    SQLModel.metadata.create_all(engine)


def get_session():
    """获取数据库会话"""
    engine = get_engine()
    with Session(engine) as session:
        yield session


class Database:
    """数据库操作类（基于 SQLModel）"""
    
    def __init__(self):
        self.engine = get_engine()
        # 初始化时自动创建表
        SQLModel.metadata.create_all(self.engine)
    
    def _get_session(self):
        """获取会话"""
        return Session(self.engine)
    
    # ========== Token 相关操作 ==========
    
    def get_token_by_value(self, token: str) -> Optional[ApiToken]:
        """根据 token 值获取用户信息"""
        with self._get_session() as session:
            statement = select(ApiToken).where(ApiToken.token == token)
            result = session.exec(statement)
            return result.first()
    
    def create_token(self, token: str, remaining_queries: int = 1000) -> ApiToken:
        """创建新的 token"""
        with self._get_session() as session:
            db_token = ApiToken(
                token=token,
                total_queries=0,
                success_queries=0,
                remaining_queries=remaining_queries
            )
            session.add(db_token)
            session.commit()
            session.refresh(db_token)
            return db_token
    
    def update_token_usage(self, token_id: int, success: bool = False):
        """更新 token 使用统计"""
        with self._get_session() as session:
            db_token = session.get(ApiToken, token_id)
            if db_token:
                db_token.total_queries += 1
                from datetime import datetime
                db_token.updated_at = datetime.utcnow()
                
                if success:
                    db_token.success_queries += 1
                    db_token.remaining_queries = max(0, db_token.remaining_queries - 1)
                
                session.add(db_token)
                session.commit()
    
    def get_token_info(self, token_id: int) -> Optional[ApiToken]:
        """获取 token 的统计信息"""
        with self._get_session() as session:
            return session.get(ApiToken, token_id)
    
    # ========== Question 相关操作 ==========
    
    def add_question(self, question_text: str, answer_text: str, 
                     is_ai_generated: bool = False, source: str = None) -> int:
        """添加题目"""
        with self._get_session() as session:
            question = Question(
                question_text=question_text,
                answer_text=answer_text,
                is_ai_generated=is_ai_generated,
                source=source
            )
            session.add(question)
            session.commit()
            session.refresh(question)
            return question.id
    
    def search_questions(self, query_text: str, limit: int = 5) -> List[Question]:
        """搜索题目（基于 LIKE 查询）"""
        with self._get_session() as session:
            # 使用 ORM 的 like 方法
            statement = select(Question).where(
                (Question.question_text.contains(query_text)) |
                (Question.answer_text.contains(query_text))
            ).limit(limit)
            results = session.exec(statement)
            return results.all()
    
    def get_question_by_id(self, question_id: int) -> Optional[Question]:
        """根据 ID 获取题目"""
        with self._get_session() as session:
            return session.get(Question, question_id)
    
    # ========== Query Log 相关操作 ==========
    
    def log_query(self, token_id: int, query_text: str, found: bool):
        """记录查询日志"""
        with self._get_session() as session:
            query_log = QueryLog(
                token_id=token_id,
                query_text=query_text,
                found=found
            )
            session.add(query_log)
            session.commit()
    
    # ========== Category 相关操作 ==========
    
    def create_category(self, name: str, description: str = None) -> int:
        """创建分类"""
        with self._get_session() as session:
            category = Category(name=name, description=description)
            session.add(category)
            session.commit()
            session.refresh(category)
            return category.id
    
    def get_all_categories(self) -> List[Category]:
        """获取所有分类"""
        with self._get_session() as session:
            statement = select(Category)
            results = session.exec(statement)
            return results.all()
    
    def assign_category(self, question_id: int, category_id: int):
        """为题目分配分类"""
        with self._get_session() as session:
            # 检查是否已存在
            existing = session.get(QuestionCategory, (question_id, category_id))
            if not existing:
                qc = QuestionCategory(question_id=question_id, category_id=category_id)
                session.add(qc)
                session.commit()


class VectorStore:
    """FAISS 向量存储管理类"""
    
    def __init__(self, category_id: int = 0):
        self.category_id = category_id
        self.index_path = EMBEDDINGS_DIR / f"faiss_{category_id}.index"
        self.embedder = OllamaEmbeddings(
            model=os.environ.get("EMBEDDING_MODEL_NAME", "nomic-embed-text")
        )
        self.index = None
        self.docstore = {}  # 存储 ID 到文档的映射
        
        if self.index_path.exists():
            self.load_index()
    
    def load_index(self):
        """加载 FAISS 索引"""
        self.index = faiss.read_index(str(self.index_path))
        # 同时加载 docstore
        docstore_path = self.index_path.with_suffix('.json')
        if docstore_path.exists():
            with open(docstore_path, 'r', encoding='utf-8') as f:
                self.docstore = json.load(f)
    
    def save_index(self):
        """保存 FAISS 索引"""
        if self.index is not None:
            faiss.write_index(self.index, str(self.index_path))
            # 保存 docstore
            docstore_path = self.index_path.with_suffix('.json')
            with open(docstore_path, 'w', encoding='utf-8') as f:
                json.dump(self.docstore, f, ensure_ascii=False, indent=2)
    
    def add_documents(self, documents: List[str], metadatas: List[Dict] = None):
        """添加文档到向量库"""
        if not documents:
            return
        
        # 生成 embeddings
        embeddings = self.embedder.embed_documents(documents)
        
        # 转换为 numpy 数组
        import numpy as np
        embeddings_array = np.array(embeddings, dtype=np.float32)
        
        # 创建或更新索引
        if self.index is None:
            dimension = embeddings_array.shape[1]
            self.index = faiss.IndexFlatL2(dimension)
        
        # 记录起始 ID
        start_id = len(self.docstore)
        
        # 添加到索引
        self.index.add(embeddings_array)
        
        # 更新 docstore
        for i, doc in enumerate(documents):
            doc_id = str(start_id + i)
            self.docstore[doc_id] = {
                'content': doc,
                'metadata': metadatas[i] if metadatas else {}
            }
        
        # 保存索引
        self.save_index()
    
    def similarity_search(self, query: str, k: int = 5) -> List[Dict]:
        """相似度搜索"""
        if self.index is None or len(self.docstore) == 0:
            return []
        
        # 生成查询 embedding
        query_embedding = self.embedder.embed_query(query)
        query_array = np.array([query_embedding], dtype=np.float32)
        
        # 搜索最相似的 k 个结果
        k = min(k, len(self.docstore))
        distances, indices = self.index.search(query_array, k)
        
        # 返回结果
        results = []
        for i, idx in enumerate(indices[0]):
            if idx >= 0 and str(idx) in self.docstore:
                doc = self.docstore[str(idx)]
                results.append({
                    'content': doc['content'],
                    'metadata': doc['metadata'],
                    'distance': float(distances[0][i])
                })
        
        return results
    
    def clear_index(self):
        """清空索引"""
        self.index = None
        self.docstore = {}
        if self.index_path.exists():
            self.index_path.unlink()
        docstore_path = self.index_path.with_suffix('.json')
        if docstore_path.exists():
            docstore_path.unlink()


# 单例模式
db = Database()
