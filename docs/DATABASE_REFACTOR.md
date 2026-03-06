# 数据库模型重构说明

## 概述

本项目已完成从原生 SQLite 到 SQLModel ORM 框架的迁移，所有数据库表类现在都统一放置在 `src/models` 目录下，通过 ORM 框架自动同步结构到数据库和操作数据，避免了直接使用 SQL 代码。

## 目录结构

```
src/models/
├── __init__.py           # 包导出文件
├── base.py              # 基础模型类
├── token.py             # API Token 模型
├── question.py          # Question 题目模型
├── query_log.py         # Query Log 查询日志模型
├── category.py          # Category 分类模型
└── question_category.py # Question-Category 关联模型
```

## 数据库模型列表

### 1. ApiToken (`token.py`)
API 用户凭证表
- **字段**：id, token, total_queries, success_queries, remaining_queries, created_at, updated_at
- **关系**：与 QueryLog 一对多

### 2. Question (`question.py`)
题库主表
- **字段**：id, question_text, answer_text, is_ai_generated, source, created_at, updated_at
- **关系**：与 QuestionCategory 一对多

### 3. QueryLog (`query_log.py`)
查询日志表
- **字段**：id, token_id, query_text, found, created_at
- **关系**：与 ApiToken 多对一

### 4. Category (`category.py`)
分类表
- **字段**：id, name, description
- **关系**：与 QuestionCategory 一对多

### 5. QuestionCategory (`question_category.py`)
题目 - 分类关联表（多对多）
- **字段**：question_id, category_id
- **关系**：连接 Question 和 Category

## 主要改进

### 1. 使用 SQLModel ORM
- ✅ 所有数据库操作通过 ORM 方法，不使用原生 SQL
- ✅ 类型安全，支持 Pydantic 模型验证
- ✅ 自动创建数据库表结构

### 2. 代码示例对比

#### ❌ 之前（使用原生 SQL）
```python
cursor.execute('''
    INSERT INTO api_tokens (token, total_queries, success_queries, remaining_queries)
    VALUES (?, ?, ?, ?)
''', (token, 0, 0, remaining_queries))
```

#### ✅ 现在（使用 SQLModel）
```python
db_token = ApiToken(
    token=token,
    total_queries=0,
    success_queries=0,
    remaining_queries=remaining_queries
)
session.add(db_token)
session.commit()
session.refresh(db_token)
```

### 3. 查询操作对比

#### ❌ 之前（使用原生 SQL）
```python
cursor.execute("SELECT * FROM api_tokens WHERE token = ?", (token,))
row = cursor.fetchone()
```

#### ✅ 现在（使用 SQLModel）
```python
statement = select(ApiToken).where(ApiToken.token == token)
result = session.exec(statement)
token_info = result.first()
```

## 使用方法

### 初始化数据库和测试数据
```bash
# 首次运行或重置测试数据
python src/test/init_test_data.py
```

### 在代码中使用
```python
from db import db

# 创建 token
token = db.create_token("my_token", 1000)

# 添加题目
question_id = db.add_question(
    question_text="什么是 SQLModel？",
    answer_text="SQLModel 是一个用于操作 SQL 数据库的 ORM 框架"
)

# 搜索题目
results = db.search_questions("SQLModel")

# 记录日志
db.log_query(
    token_id=token.id,
    query_text="SQLModel 测试",
    found=True
)
```

## 技术栈
- **SQLModel**: ORM 框架（基于 SQLAlchemy 和 Pydantic）
- **SQLite**: 数据库引擎
- **FastAPI**: Web 框架

## 优势

1. **类型安全**: 所有模型都有明确的类型定义
2. **代码简洁**: 无需编写 SQL 语句
3. **易于维护**: 模型定义集中在 `src/models` 目录
4. **自动同步**: 数据库表结构自动创建和更新
5. **IDE 支持**: 更好的自动补全和错误检查

## 注意事项

- 所有数据库模型类必须放在 `src/models` 目录下
- 避免直接编写 SQL 代码，使用 ORM 方法操作数据
- 使用 `session.commit()` 提交事务
- 使用 `session.refresh()` 刷新对象状态

## 相关文件
- `src/db.py` - 数据库操作类（基于 SQLModel）
- `src/test/init_test_data.py` - 测试数据初始化脚本（仅用于测试）
- `src/test/test_sqlmodel.py` - SQLModel 模型测试脚本
- `src/api.py` - API 接口（已适配 SQLModel）

## 项目结构规范

### 目录组织
```
project/
├── src/
│   ├── models/          # 数据库模型（ORM）
│   ├── test/            # 测试脚本和测试数据初始化
│   ├── agents/          # AI Agent 业务逻辑
│   ├── prompts/         # Prompt 模板
│   └── ...
├── docs/                # 所有文档
├── data/                # 数据文件（数据库、向量索引等）
└── ...
```

### 代码组织原则
1. **所有数据库模型** → `src/models/`
2. **所有测试代码** → `src/test/`
3. **所有文档** → `docs/`
4. **前后端分离** → Python 只负责路由，前端代码独立文件
