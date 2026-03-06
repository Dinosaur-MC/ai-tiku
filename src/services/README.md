# Services 模块说明

## 概述

`src/services/` 目录包含了 AI-Tiku 项目的核心业务服务，将原有的 `answer_retriever.py` 拆分为更专注、更可维护的独立服务。

## 模块结构

```
src/services/
├── __init__.py          # 模块初始化和服务导出
├── vector_search.py     # 向量搜索服务（常规检索功能）
└── ai_responder.py      # AI响应服务（AI答题功能）
```

## 服务详情

### 1. VectorSearch - 向量搜索服务

**文件**: `vector_search.py`

**职责**: 负责常规的题目检索功能，包括：
- 向量相似度搜索
- 最佳匹配获取
- 文档添加（单个/批量）

**主要类和方法**:
- `VectorSearch`: 向量搜索服务类
  - `__init__(category_id: int = 0)`: 初始化，可指定题库分类 ID
  - `search_similar(query_text: str, k: int = 5)`: 搜索相似题目
  - `get_best_match(query_text: str)`: 获取最匹配的题目
  - `add_document(content: str, answer: str, metadata: Dict)`: 添加单个文档
  - `add_documents(contents: List[str], answers: List[str], metadatas: List[Dict])`: 批量添加文档

**单例实例**: `vector_search`

**使用示例**:
```python
from services.vector_search import vector_search

# 搜索相似题目
results = vector_search.search_similar("什么是人工智能？", k=5)

# 获取最佳匹配
best = vector_search.get_best_match("什么是人工智能？")

# 添加文档
vector_search.add_document("题目内容", "答案内容")
```

---

### 2. AIResponder - AI响应服务

**文件**: `ai_responder.py`

**职责**: 负责使用 LLM 生成答案，包括：
- 构建查询提示词
- 调用 LLM 生成答案

**主要类和方法**:
- `AIResponder`: AI响应服务类
  - `generate_answer(question: str, options: List[str], question_type: str)`: 生成答案
  - `_build_query_prompt(question: str, options: List[str], question_type: str)`: 构建提示词

**单例实例**: `ai_responder`

**使用示例**:
```python
from services.ai_responder import ai_responder

# 生成答案
answer = ai_responder.generate_answer(
    question="什么是人工智能？",
    options=["A. 机器学习", "B. 深度学习"],
    question_type="single"
)
```

---

### 3. AnswerRetriever - 答案检索器（整合服务）

**文件**: `answer_retriever.py` (重构后)

**职责**: 整合向量搜索和 AI响应，提供完整的查题功能：
- 优先使用向量搜索查找相似题目
- 未找到时使用 AI 生成答案
- 保持向后兼容的接口

**主要类和方法**:
- `AnswerRetriever`: 答案检索器类
  - `search(query_text, options, question_type, more, force_ai)`: 搜索答案
  - `add_to_vectorstore(question, answer, metadata)`: 添加到向量库

**单例实例**: `retriever`

**使用示例**:
```python
from answer_retriever import retriever

# 搜索答案（自动选择向量搜索或 AI）
result = retriever.search(
    query_text="什么是人工智能？",
    options="A. 机器学习\nB. 深度学习",
    question_type="single"
)
```

---

## 重构优势

### 1. 职责分离
- **VectorSearch**: 专注于向量检索
- **AIResponder**: 专注于 AI 答案生成
- **AnswerRetriever**: 专注于业务流程编排

### 2. 可维护性提升
- 每个服务职责单一，易于理解和维护
- 代码量减少，逻辑更清晰
- 便于独立测试和调试

### 3. 可扩展性增强
- 可以轻松为不同服务添加新功能
- 支持独立替换某个服务（如更换 LLM）
- 便于添加新的服务（如缓存服务、日志服务等）

### 4. 向后兼容
- `AnswerRetriever` 保持原有接口不变
- 现有代码无需修改即可正常工作
- 平滑过渡，降低迁移成本

---

## API 集成

在 `api.py` 中，现在直接使用服务模块：

```python
from services.vector_search import vector_search
from services.ai_responder import ai_responder

# 查询逻辑
if not force_ai:
    similar_results = vector_search.search_similar(query_text, k=5)
    if similar_results:
        # 返回相似题目结果
        ...

# 未找到时使用 AI
ai_answer = ai_responder.generate_answer(query_text, options, question_type)
```

---

## 测试

运行测试脚本验证服务模块：

```bash
python src/test/test_services.py
```

测试覆盖：
- ✓ VectorSearch 服务的创建和使用
- ✓ AIResponder 服务的创建和提示词构建
- ✓ AnswerRetriever 服务的完整性

---

## 依赖关系

```
api.py
├── services/vector_search.py
│   └── db.VectorStore
├── services/ai_responder.py
│   └── llm.completion
└── answer_retriever.py (重构后)
    ├── services/vector_search.py
    └── services/ai_responder.py
```

---

## 注意事项

1. **导入路径**: 服务模块使用绝对导入，确保在 `src` 目录下运行
2. **单例模式**: 所有服务都提供单例实例，推荐直接使用而非重复创建
3. **向后兼容**: `answer_retriever.retriever` 接口保持不变，现有代码无需修改
4. **服务组合**: 推荐在业务逻辑中直接使用 `vector_search` 和 `ai_responder`，而非通过 `retriever` 间接调用

---

## 版本历史

- **v1.1.0** (2026-03-06): 重构 `answer_retriever.py`，拆分为独立服务模块
- **v1.0.0**: 初始版本，所有功能在 `answer_retriever.py` 中
