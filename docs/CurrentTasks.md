## 基于 Faiss 的单机题库检索系统设计（可平滑迁移到 Elasticsearch）

### 一、数据建模与存储设计

#### 1. 题目数据字段
每道题目应包含以下核心字段：
- **`id`**：唯一标识（整型或字符串）
- **`question_text`**：题目文本（包括题干和可能的选项拼接，例如 “牛顿第一定律的内容是什么？A. … B. … C. … D. …”）
- **`answer`**：答案文本（或结构化答案）
- **`question_type`**：问题类型（如“单选题”、“填空题”、“解答题”等）
- **`subject_area`**：学科领域（如“物理”、“数学”、“英语”）
- **`embedding`**：向量表示（用于语义检索，后期由 ES 管理或单独存储）

#### 2. 存储方案（单机版）
- **向量索引**：使用 Faiss 存储 `id` → 向量的映射，仅用于 ANN 检索。
- **元数据存储**：使用 SQLite 或内存字典（如 Python `dict`）存储题目的元数据（`id`, `question_text`, `answer`, `question_type`, `subject_area`），支持按 `id` 快速获取完整信息，并支持简单的 SQL 过滤（如 `WHERE subject_area = '物理'`）。

### 二、题目向量化编码策略

#### 1. 嵌入模型选择
- 使用预训练的 Sentence-BERT 模型，例如 `paraphrase-multilingual-MiniLM-L12-v2`（支持中文），或 `BAAI/bge-large-zh`。
- 若后续需要与 ES 兼容，建议选择 OpenAI `text-embedding-ada-002` 或 ES 内置的 `sentence-transformers` 模型，便于迁移。

#### 2. 编码内容
- **语义检索向量**：仅对 `question_text` 进行编码（包含题干和选项）。这样检索时能匹配语义相似的问题。
- **可选**：若希望检索也能考虑答案，可将答案文本与问题拼接后编码，但需注意答案可能很长，会稀释问题本身的信号。通常建议单独对问题编码，答案在返回时附带即可。

#### 3. 向量维度
- 常见模型输出维度：384、768、1024。根据模型确定 Faiss 索引维度。

### 三、基于 Faiss 的单机检索实现

#### 1. 索引构建
假设使用 HNSW 索引（Faiss 中 `IndexHNSWFlat`），平衡速度与召回率。
```python
import faiss
import numpy as np
import sqlite3
from sentence_transformers import SentenceTransformer

# 1. 初始化模型和数据库
model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
conn = sqlite3.connect('questions.db')
cursor = conn.cursor()
# 创建表：id, question_text, answer, question_type, subject_area
cursor.execute('''
    CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY,
        question_text TEXT,
        answer TEXT,
        question_type TEXT,
        subject_area TEXT
    )
''')

# 2. 准备数据（假设已有题目列表）
questions = [...]   # 题目文本列表
answers = [...]     # 对应答案列表
types = [...]       # 对应类型列表
subjects = [...]    # 对应学科列表

# 3. 生成向量
embeddings = model.encode(questions, normalize_embeddings=True)  # shape: (N, dim)

# 4. 构建 Faiss 索引 (HNSW)
dim = embeddings.shape[1]
index = faiss.IndexHNSWFlat(dim, 32)  # 32 为 HNSW 的邻居数
index.add(embeddings)                  # 索引向量

# 5. 将元数据存入 SQLite
for i, (q, a, t, s) in enumerate(zip(questions, answers, types, subjects)):
    cursor.execute('INSERT INTO questions VALUES (?, ?, ?, ?, ?)', (i, q, a, t, s))
conn.commit()
```

#### 2. 检索流程
支持两种模式：**精确查找**（关键词匹配）和**同义查找**（向量语义检索），并可结合分类过滤。

**函数示例**：
```python
def search(query, subject_filter=None, question_type_filter=None, top_k=10, use_semantic=True):
    if use_semantic:
        # 语义检索
        query_emb = model.encode([query], normalize_embeddings=True)
        distances, indices = index.search(query_emb, top_k * 2)  # 多取一些以备过滤
        candidate_ids = indices[0].tolist()
        
        # 从 SQLite 获取元数据并过滤
        placeholders = ','.join(['?'] * len(candidate_ids))
        cursor.execute(f'''
            SELECT id, question_text, answer, question_type, subject_area
            FROM questions
            WHERE id IN ({placeholders})
        ''', candidate_ids)
        results = cursor.fetchall()
        
        # 按学科和类型过滤
        filtered = []
        for row in results:
            if subject_filter and row[4] != subject_filter:
                continue
            if question_type_filter and row[3] != question_type_filter:
                continue
            filtered.append(row)
        
        # 按原始距离排序（注意 Faiss 返回的顺序与 candidate_ids 一致，但 SQLite 查询后顺序可能打乱，需重新排序）
        # 简化：在内存中按距离排序（需保留原始距离）
        # 这里略去重排序细节，可按 candidate_ids 顺序保留距离
        return filtered[:top_k]
    else:
        # 精确查找：使用 SQLite 的 LIKE（或 FTS 全文检索）
        query_like = f'%{query}%'
        sql = 'SELECT id, question_text, answer, question_type, subject_area FROM questions WHERE question_text LIKE ?'
        params = [query_like]
        if subject_filter:
            sql += ' AND subject_area = ?'
            params.append(subject_filter)
        if question_type_filter:
            sql += ' AND question_type = ?'
            params.append(question_type_filter)
        cursor.execute(sql, params)
        return cursor.fetchall()[:top_k]
```

**说明**：
- 语义检索时，Faiss 返回的 `indices` 对应题目 `id`，通过 SQLite 获取完整信息并应用过滤。
- 由于 SQLite 查询后顺序可能丢失，如需保留 Faiss 的相似度排序，可在获取元数据后根据原始距离重新排序。
- 精确查找依赖 SQLite 的 `LIKE`，性能较差（全表扫描），但适合小规模单机原型。后期可改用 SQLite FTS5 或直接迁移到 ES。

#### 3. 分类过滤优化
- **预过滤**：如果题库按学科领域物理分表，可以为每个学科创建独立的 Faiss 索引。查询时根据 `subject_filter` 选择对应索引，减少搜索空间。
- **后过滤**：如上述代码，先检索再过滤。若过滤条件筛选性强（如只保留 10% 数据），效率尚可。若需更高性能，可用 Faiss 的 `IDSelector` 结合 IVF 索引实现过滤（需自定义）。

### 四、后期平滑迁移到 Elasticsearch

#### 1. 设计目标
- 保持数据模型一致，ES 索引字段名与当前 SQLite 字段对应。
- 向量存储方式兼容：ES 8.0+ 支持 `dense_vector` 类型，可直接存储向量并执行 HNSW 近似检索。
- 将精确查找和语义查找统一在 ES 的 `bool` 查询中。

#### 2. ES 索引映射示例
```json
{
  "mappings": {
    "properties": {
      "id": {"type": "integer"},
      "question_text": {"type": "text", "analyzer": "ik_max_word"},
      "answer": {"type": "text", "analyzer": "ik_max_word"},
      "question_type": {"type": "keyword"},
      "subject_area": {"type": "keyword"},
      "embedding": {"type": "dense_vector", "dims": 384, "similarity": "cosine"}
    }
  }
}
```

#### 3. 数据迁移
- 将 SQLite 中的元数据导出为 JSON，批量导入 ES。
- 向量可提前计算好，随文档一同导入。

#### 4. 查询示例（混合检索）
```json
{
  "query": {
    "bool": {
      "should": [
        { "match": { "question_text": "牛顿第二定律" } },   // 精确/关键词匹配
        { "script_score": {                                 // 向量相似度
            "query": { "match_all": {} },
            "script": {
              "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
              "params": {"query_vector": [...]}
            }
          }
        }
      ],
      "filter": [
        { "term": { "subject_area": "物理" } },
        { "term": { "question_type": "单选题" } }
      ]
    }
  }
}
```
ES 会自动结合两种匹配方式，并通过 filter 进行精确过滤。

#### 5. 迁移优势
- 无需修改上层业务代码太多，只需将 SQLite 查询替换为 ES 客户端调用。
- 向量检索与元数据过滤一体化，性能更优（ES 内部会先过滤再计算向量相似度）。
- 支持分布式、高可用、全文检索（IK 分词）。

### 五、总结与建议

| 阶段 | 检索方式 | 元数据过滤 | 向量存储 | 备注 |
|------|----------|------------|----------|------|
| 单机原型（Faiss） | Faiss HNSW + SQLite LIKE | SQLite WHERE | Faiss 索引 | 快速搭建，验证语义检索效果 |
| 生产增强（ES） | ES 混合查询（BM25 + 向量） | ES filter 上下文 | ES dense_vector | 统一入口，支持复杂查询 |

**建议实施步骤**：
1. 使用 Sentence-BERT 生成所有题目的向量。
2. 使用 Faiss 构建 HNSW 索引，配合 SQLite 存储元数据，实现基础检索。
3. 开发过程中注意保留字段映射关系，便于后期直接导入 ES。
4. 当数据量增长或需要更复杂的全文检索时，平滑迁移到 Elasticsearch。

通过这种分阶段设计，既能快速实现单机语义检索，又能保证未来扩展性，满足题库系统对精确查找、同义查找和分类过滤的需求。