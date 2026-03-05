import os
import sqlite3
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime
import json

from langchain_community.vectorstores import FAISS
from langchain_ollama import OllamaEmbeddings
import faiss
import numpy as np

# 获取项目根目录
ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
DB_PATH = DATA_DIR / "db.sqlite3"
EMBEDDINGS_DIR = DATA_DIR / "embeddings"

# 确保目录存在
DATA_DIR.mkdir(exist_ok=True)
EMBEDDINGS_DIR.mkdir(exist_ok=True)


class Database:
    """SQLite 数据库管理类"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or DB_PATH
        self.init_database()
    
    def get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """初始化数据库表结构"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 创建用户凭证表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS api_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT NOT NULL UNIQUE,
                total_queries INTEGER NOT NULL DEFAULT 0,
                success_queries INTEGER NOT NULL DEFAULT 0,
                remaining_queries INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建题库主表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_text TEXT NOT NULL,
                answer_text TEXT NOT NULL,
                is_ai_generated INTEGER NOT NULL DEFAULT 0,
                source TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建查询日志表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS query_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token_id INTEGER NOT NULL,
                query_text TEXT NOT NULL,
                found INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (token_id) REFERENCES api_tokens(id) ON DELETE CASCADE
            )
        ''')
        
        # 创建分类表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT
            )
        ''')
        
        # 创建题目 - 分类关联表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS question_category (
                question_id INTEGER NOT NULL,
                category_id INTEGER NOT NULL,
                PRIMARY KEY (question_id, category_id),
                FOREIGN KEY (question_id) REFERENCES questions(id) ON DELETE CASCADE,
                FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE CASCADE
            )
        ''')
        
        conn.commit()
        conn.close()
    
    # Token 相关操作
    def get_token_by_value(self, token: str) -> Optional[Dict]:
        """根据 token 值获取用户信息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM api_tokens WHERE token = ?", (token,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    def create_token(self, token: str, remaining_queries: int = 1000) -> Dict:
        """创建新的 token"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO api_tokens (token, total_queries, success_queries, remaining_queries)
            VALUES (?, 0, 0, ?)
        ''', (token, remaining_queries))
        conn.commit()
        
        cursor.execute("SELECT * FROM api_tokens WHERE token = ?", (token,))
        row = cursor.fetchone()
        conn.close()
        return dict(row)
    
    def update_token_usage(self, token_id: int, success: bool = False):
        """更新 token 使用统计"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # 增加总查询次数
        cursor.execute('''
            UPDATE api_tokens 
            SET total_queries = total_queries + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (token_id,))
        
        if success:
            # 增加成功查询次数
            cursor.execute('''
                UPDATE api_tokens 
                SET success_queries = success_queries + 1,
                    remaining_queries = MAX(0, remaining_queries - 1),
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (token_id,))
        
        conn.commit()
        conn.close()
    
    def get_token_info(self, token_id: int) -> Optional[Dict]:
        """获取 token 的统计信息"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM api_tokens WHERE id = ?", (token_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    # Question 相关操作
    def add_question(self, question_text: str, answer_text: str, 
                     is_ai_generated: bool = False, source: str = None) -> int:
        """添加题目"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO questions (question_text, answer_text, is_ai_generated, source)
            VALUES (?, ?, ?, ?)
        ''', (question_text, answer_text, 1 if is_ai_generated else 0, source))
        conn.commit()
        question_id = cursor.lastrowid
        conn.close()
        return question_id
    
    def search_questions(self, query_text: str, limit: int = 5) -> List[Dict]:
        """搜索题目（基于全文搜索）"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM questions 
            WHERE question_text LIKE ? OR answer_text LIKE ?
            LIMIT ?
        ''', (f'%{query_text}%', f'%{query_text}%', limit))
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def get_question_by_id(self, question_id: int) -> Optional[Dict]:
        """根据 ID 获取题目"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM questions WHERE id = ?", (question_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    # Query Log 相关操作
    def log_query(self, token_id: int, query_text: str, found: bool):
        """记录查询日志"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO query_logs (token_id, query_text, found)
            VALUES (?, ?, ?)
        ''', (token_id, query_text, 1 if found else 0))
        conn.commit()
        conn.close()
    
    # Category 相关操作
    def create_category(self, name: str, description: str = None) -> int:
        """创建分类"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO categories (name, description)
            VALUES (?, ?)
        ''', (name, description))
        conn.commit()
        category_id = cursor.lastrowid
        conn.close()
        return category_id
    
    def get_all_categories(self) -> List[Dict]:
        """获取所有分类"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categories")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    def assign_category(self, question_id: int, category_id: int):
        """为题目分配分类"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR IGNORE INTO question_category (question_id, category_id)
            VALUES (?, ?)
        ''', (question_id, category_id))
        conn.commit()
        conn.close()


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
