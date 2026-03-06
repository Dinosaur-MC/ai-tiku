# AI Agents 和提示词模板重构说明

## 概述

本次重构将项目中的所有提示词模板统一放入 `src/agents/prompts/` 目录，AI Agents 放置在 `src/agents/` 目录，并创建了 AI服务层来统一组织和调用多个Agent。

---

## 📁 新的目录结构

```
src/
├── agents/                          # AI Agents 目录
│   ├── __init__.py                 # 导出所有 Agents
│   ├── query.py                    # 题目查询 Agent（新增）
│   ├── classification.py           # 题目分类 Agent
│   ├── reviewer.py                 # 答案复审 Agent
│   ├── rag_chat.py                 # RAG 对话 Agent
│   └── prompts/                    # 提示词模板目录
│       ├── __init__.py            # 导出所有提示词模板
│       ├── query.py               # 查询提示词模板
│       ├── classify.py            # 分类提示词模板
│       └── review.py              # 复审提示词模板
├── services/                       # 服务层
│   ├── __init__.py                # 导出所有服务
│   ├── vector_search.py           # 向量搜索服务
│   ├── ai_responder.py            # AI响应服务（已更新）
│   └── ai_service.py              # AI服务（新增，统一调用 Agents）
└── test/
    ├── test_agents.py             # Agents 测试脚本（新增）
    └── test_services.py           # 服务测试脚本
```

---

## 🎯 核心组件

### 1. 提示词模板（Prompts）

**位置**: `src/agents/prompts/`

所有提示词模板统一管理，便于维护和优化：

#### query.py - 查询提示词模板
- `QUERY_SYSTEM_PROMPT`: 系统提示词，定义答题助手角色
- `QUERY_USER_PROMPT_TEMPLATE`: 用户提示词模板
- `build_query_prompt()`: 构建完整提示词的函数
- `AI_GENERATE_PROMPT`: AI 生成答案提示词
- `CONVERSATIONAL_QUERY_PROMPT`: 多轮对话提示词
- `CONFIDENCE_ANSWER_PROMPT`: 带置信度的答案生成提示词

#### classify.py - 分类提示词模板
- `CLASSIFICATION_SYSTEM_PROMPT`: 分类系统提示词
- `CLASSIFICATION_USER_PROMPT_TEMPLATE`: 分类用户模板
- `build_classification_prompt()`: 构建分类提示词
- `POST_CLASSIFICATION_PROMPT`: 分类后处理提示词

#### review.py - 复审提示词模板
- `REVIEW_SYSTEM_PROMPT`: 复审系统提示词
- `REVIEW_USER_PROMPT_TEMPLATE`: 复审用户模板
- `build_review_prompt()`: 构建复审提示词
- `BATCH_REVIEW_PROMPT`: 批量复审提示词
- `SPECIALIZED_REVIEW_PROMPTS`: 专项审核提示词字典
- `ANSWER_QUALITY_EVAL_PROMPT`: 答案质量评估提示词

**使用方式**:
```python
from agents.prompts import (
    QUERY_SYSTEM_PROMPT,
    build_query_prompt
)

# 使用模板构建提示词
prompt = build_query_prompt(
    question="什么是人工智能？",
    options=["A. 机器学习", "B. 深度学习"],
    question_type="single"
)
```

---

### 2. AI Agents

**位置**: `src/agents/`

每个 Agent 负责特定的 AI 任务：

#### QueryAgent（新增）⭐
**文件**: `query.py`
- **职责**: 根据题目内容生成答案
- **主要方法**:
  - `answer(question, options, question_type, return_confidence)`: 回答题目
  - `_answer_direct()`: 直接生成答案
  - `_answer_with_confidence()`: 生成答案并评估置信度
  - `batch_answer(questions)`: 批量回答
  - `get_statistics()`: 获取统计信息
  - `clear_history()`: 清空历史

**单例**: `query_agent`

#### ClassificationAgent
**文件**: `classification.py`
- **职责**: 自动将题目分类到合适的类别
- **主要方法**:
  - `classify(question_text, options)`: 对题目进行分类
  - `add_category(name, description)`: 添加新分类
  - `assign_to_question(question_id, category_ids)`: 分配分类
  - `get_categories_for_question(question_id)`: 获取题目分类

**单例**: `classifier`

#### ReviewerAgent
**文件**: `reviewer.py`
- **职责**: 审核和修正 AI 生成的答案
- **主要方法**:
  - `review(question, answer, options, question_type, corrections)`: 复审答案
  - `batch_review(qa_pairs)`: 批量复审
  - `get_review_statistics()`: 获取复审统计
  - `clear_history()`: 清空历史

**单例**: `reviewer`

#### RAGChatAgent
**文件**: `rag_chat.py`
- **职责**: 基于检索增强生成（RAG）的对话式问答
- **主要方法**:
  - `chat(query, use_history)`: 对话式问答
  - `stream_chat(query, use_history)`: 流式对话
  - `add_document(question, answer)`: 添加文档
  - `batch_add_documents(qa_pairs)`: 批量添加文档
  - `clear_history()`: 清空对话历史

**单例**: `rag_chat`

---

### 3. AI服务层

**位置**: `src/services/`

#### AIService（新增）⭐
**文件**: `ai_service.py`

统一组织和协调多个 AI Agent 完成复杂任务：

**主要方法**:

1. **`answer_question(question, options, question_type, auto_review)`**
   - 回答题目（可选自动复审）
   - 如果 `auto_review=True`，会自动调用 ReviewerAgent 审核答案

2. **`classify_and_answer(question, options)`**
   - 先分类再回答
   - 返回分类结果和答案

3. **`full_process(question, options, question_type)`**
   - 完整流程：分类 → 回答 → 复审
   - 返回所有处理结果和统计信息

4. **`chat(query, use_history)`**
   - RAG 对话式问答
   - 使用 RAGChatAgent

5. **`batch_process(questions)`**
   - 批量处理题目
   - 对每个题目执行完整流程

6. **`get_all_statistics()`**
   - 获取所有 Agent 的统计信息

7. **`clear_all_history()`**
   - 清空所有历史记录

**单例**: `ai_service`

#### AIResponder（已更新）
**文件**: `ai_responder.py`

现在基于 QueryAgent 实现，保持向后兼容：

```python
from services.ai_responder import ai_responder

# 生成答案
answer = ai_responder.generate_answer(
    question="什么是人工智能？",
    options=["A. 机器学习", "B. 深度学习"],
    question_type="single"
)

# 生成答案并评估置信度
result = ai_responder.generate_answer_with_confidence(
    question="什么是人工智能？"
)
print(f"答案：{result['answer']}")
print(f"置信度：{result['confidence']}")
print(f"推理：{result['reasoning']}")
```

---

## 🔄 使用示例

### 示例 1：直接使用 QueryAgent

```python
from agents.query import query_agent

result = query_agent.answer(
    question="什么是人工智能？",
    options=["A. 机器学习", "B. 深度学习"],
    question_type="single"
)
print(f"答案：{result['answer']}")
```

### 示例 2：使用 AI服务进行完整流程

```python
from services.ai_service import ai_service

result = ai_service.full_process(
    question="什么是人工智能？",
    options=["A. 机器学习", "B. 深度学习"],
    question_type="single"
)

print(f"分类：{result['categories']}")
print(f"原始答案：{result['original_answer']}")
print(f"最终答案：{result['final_answer']}")
print(f"是否修正：{result['was_corrected']}")
print(f"复审结果：{result['review_result']}")
```

### 示例 3：自动复审答案

```python
from services.ai_service import ai_service

result = ai_service.answer_question(
    question="矛盾论是谁提出的？",
    question_type="judgement",
    auto_review=True  # 自动复审
)

if result['was_corrected']:
    print(f"答案已修正：{result['answer']}")
else:
    print(f"答案正确：{result['answer']}")
```

### 示例 4：RAG 对话

```python
from services.ai_service import ai_service

response = ai_service.chat(
    query="马克思主义的基本原理有哪些？",
    use_history=True
)

print(f"回答：{response['answer']}")
print(f"参考来源：{response['sources']}")
```

---

## ✅ 重构优势

### 1. 提示词模板统一管理
- 所有提示词集中在 `agents/prompts/` 目录
- 便于优化和维护
- 支持复用和组合

### 2. Agent 职责清晰
- 每个 Agent 负责单一职责
- 易于独立测试和扩展
- 符合单一职责原则

### 3. 服务层统一协调
- AIService 统一调用多个Agent
- 支持复杂业务流程编排
- 提供多种处理模式（简单、分类、复审等）

### 4. 向后兼容
- 保留原有单例模式
- `ai_responder` 接口保持不变
- 现有代码无需修改

### 5. 可扩展性强
- 易于添加新的 Agent
- 易于添加新的提示词模板
- 支持灵活的服务组合

---

## 🧪 测试验证

运行测试脚本验证所有组件：

```bash
python src/test/test_agents.py
```

测试覆盖：
- ✓ 提示词模板加载和使用
- ✓ QueryAgent 功能
- ✓ ClassificationAgent 功能
- ✓ ReviewerAgent 功能
- ✓ RAGChatAgent 功能
- ✓ AIService 集成功能

---

## 📊 依赖关系

```
services/ai_service.py
├── agents/query.py
│   └── agents/prompts/query.py
├── agents/classification.py
│   └── agents/prompts/classify.py
├── agents/reviewer.py
│   └── agents/prompts/review.py
└── agents/rag_chat.py

services/ai_responder.py
└── agents/query.py
    └── agents/prompts/query.py
```

---

## 📝 迁移指南

### 从旧版本迁移

如果你之前使用 `ai_responder`，现在可以：

1. **继续使用原有方式**（向后兼容）：
```python
from services.ai_responder import ai_responder
answer = ai_responder.generate_answer(question, options, question_type)
```

2. **使用新的 QueryAgent**（推荐）：
```python
from agents.query import query_agent
result = query_agent.answer(question, options, question_type)
# 可获取更多详细信息，如置信度
```

3. **使用 AIService**（完整流程）：
```python
from services.ai_service import ai_service
result = ai_service.full_process(question, options, question_type)
# 包含分类、回答、复审全流程
```

---

## 🎯 最佳实践

1. **简单场景**：使用 `ai_responder.generate_answer()`
2. **需要置信度**：使用 `query_agent.answer(return_confidence=True)`
3. **需要质量保证**：使用 `ai_service.answer_question(auto_review=True)`
4. **完整流程**：使用 `ai_service.full_process()`
5. **对话场景**：使用 `ai_service.chat()`

---

## 🔮 未来扩展

1. **添加新 Agent**:
   - 在 `agents/` 目录创建新的 Agent 类
   - 在 `agents/__init__.py` 中导出
   - 在 `AIService` 中集成

2. **添加新提示词**:
   - 在 `agents/prompts/` 目录创建新模板
   - 在 `agents/prompts/__init__.py` 中导出

3. **扩展 AIService**:
   - 添加新的业务方法
   - 组合不同的 Agent
   - 实现新的工作流程

---

## 📚 版本历史

- **v2.0.0** (2026-03-06): 
  - ✨ 新增 QueryAgent
  - ✨ 新增 AIService 统一服务层
  - 📦 所有提示词模板移入 `agents/prompts/`
  - 🔄 重构 AIResponder 使用 QueryAgent
  - ✅ 完整的测试覆盖

- **v1.1.0**: 拆分 answer_retriever 为 vector_search 和 ai_responder
- **v1.0.0**: 初始版本
