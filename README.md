# AI-Tiku

AI 题库答题服务系统 - 基于 AI 的智能题库查询和答题解决方案。

## 目录

- [功能特性](#功能特性)
- [系统架构](#系统架构)
- [快速开始](#快速开始)
- [API 文档](#api-文档)
- [Web 界面](#web-界面)
- [开发指南](#开发指南)
- [配置说明](#配置说明)
- [数据库表结构](#数据库表结构)

## 功能特性

### 核心功能

- **智能查题** - 基于向量相似度搜索题目，支持多种题型
- **AI 辅助答题** - 当题库中没有匹配答案时，使用 LLM 生成答案
- **配额管理** - Token 级别的调用次数统计和限制
- **题目分类** - 自动将题目分类到合适的知识类别
- **答案复审** - 审核和修正 AI 生成的答案，确保准确性
- **RAG 对话** - 基于检索增强生成的对话式问答
- **图片分析** - 支持对题干和选项图片进行视觉理解与分析

### 技术特性

- **多模型支持** - 支持 Ollama、OpenAI 等多种大模型后端
- **向量检索** - 基于 FAISS 的高效向量相似度搜索
- **流式输出** - 支持 SSE 流式响应，提升用户体验
- **异步处理** - 完整的异步 IO 支持，高并发场景优化
- **RESTful API** - 标准化的 REST API 接口，v1/v2 版本并存
- **响应式 UI** - 基于 MDUI 的现代化 Web 界面
- **SQLModel** - 基于 SQLModel + SQLAlchemy 的 ORM 数据层

## 系统架构

```
┌─────────────────────────────────────────────┐
│              Web UI (MDUI)                   │
│         index.html | 查询界面 | 结果展示      │
└────────────────┬────────────────────────────┘
                 │ HTTP/REST API
┌────────────────▼────────────────────────────┐
│              FastAPI Application             │
│         main.py (CORS, 异常处理, 路由注册)    │
└────────────────┬────────────────────────────┘
                 │
    ┌────────────┼────────────┬───────────┐
    │            │            │           │
┌───▼────┐  ┌───▼────┐  ┌───▼───┐  ┌───▼─────┐
│ v1 API │  │ v2 API │  │ Auth  │  │ Services│
│Router  │  │Router  │  │Depends│  │  Layer  │
│        │  │        │  │       │  │         │
│/query  │  │/categor│  │verify │  │question │
│/info   │  │/classfy│  │_token │  │_service │
│        │  │/quest..│  │JWT    │  │ai_service│
└────────┘  └────────┘  └───────┘  │classifi.│
                                    │_service │
                                    │user_serv│
                                    └────┬────┘
                                         │
              ┌──────────────────────────┼──────────┐
              │                          │          │
         ┌────▼────┐              ┌──────▼─────┐    │
         │ Agents  │              │ Persistence│    │
         │ Layer   │              │   Layer    │    │
         │         │              │            │    │
         │• query  │              │• utils/dbc│    │
         │• classi │              │  (Database │    │
         │• review │              │   + Vector │    │
         │• rag_ch │              │    Store)  │    │
         │• prompts│              │• SQLite    │    │
         └────┬────┘              │• FAISS     │    │
              │                   └────────────┘    │
              │                                     │
         ┌────▼────┐                        ┌───────▼──────┐
         │ LLM     │                        │  Utils       │
         │ Layer   │                        │              │
         │         │                        │• option_     │
         │• llm.py │                        │  images.py   │
         │• comple │                        │• vision_     │
         │  tion   │                        │  inputs.py   │
         │• embed  │                        │• access_     │
         │• chat   │                        │  token.py    │
         │• stream │                        │• string_     │
         └─────────┘                        │  tool.py     │
                                            └──────────────┘
```

### 模块说明

1. **Web UI 层** (`src/index.html`)
    - 基于 MDUI 2 组件库的现代化界面
    - 支持全屏查看、结果复制
    - 响应式设计，适配各种屏幕

2. **API 路由层** (`routers/api_v1.py`, `routers/api_v2.py`)
    - `GET /api/v1/query` - 查题接口
    - `GET /api/v1/info` - 配额查询接口
    - `GET/POST /api/v2/categories` - 分类管理（v2 尚在完善中）
    - Token 验证和配额管理

3. **认证层** (`dependencies.py`)
    - `verify_api_token()` - API Token 验证
    - `get_current_user()` - JWT 用户身份验证
    - `get_current_active_user()` - 激活用户验证

4. **服务层** (`services/`)
    - `question_service.py` - 题目 CRUD、语义搜索
    - `classification_service.py` - 分类 CRUD、题目分类分配
    - `ai_service.py` - AI 编排（查询/分类/复审/RAG 对话）
    - `user_service.py` - 用户注册/认证/API Key 管理

5. **Agent 层** (`agents/`)
    - `query.py` - 答题 Agent（支持图片分析工具）
    - `classification.py` - 题目分类 Agent（LangGraph + Pydantic）
    - `reviewer.py` - 答案复审 Agent
    - `rag_chat.py` - RAG 对话 Agent

6. **Prompts 层** (`agents/prompts/`)
    - `query.py` - 查询提示词模板
    - `classify.py` - 分类提示词模板
    - `review.py` - 复审提示词模板

7. **持久化层** (`utils/dbc.py`)
    - `Database` 类 - SQLite 关系型数据库（基于 SQLModel）
    - `VectorStore` 类 - FAISS 向量数据库
    - 按分类存储 FAISS 索引

8. **LLM 层** (`utils/llm.py`)
    - 统一的模型调用接口（Provider 路由）
    - 支持流式和异步操作
    - 多模型后端适配（Ollama / OpenAI-compatible）

9. **模型层** (`models/`)
    - `User`, `ApiKey`, `Question`, `Category`, `QuestionCategory`, `QueryLog`
    - 所有模型基于 SQLModel，支持自动迁移

## 快速开始

### 环境要求

- Python 3.12+
- Ollama（使用本地模型时需要）或兼容 OpenAI 的接口服务
- uv 或 pip（包管理工具）

### 1. 安装依赖

```bash
# 使用 uv（推荐）
uv sync

# 或使用 pip
pip install -e .
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

本项目支持 `ollama` 与通用 `openai_compatible` provider，模型路由与初始化逻辑集中在 `utils/llm.py`，按能力分别配置 `CHAT_*`、`COMPLETION_*`、`EMBEDDING_*` 环境变量。视觉能力 `VISION_*` 可选。

```bash
# Chat provider
CHAT_PROVIDER=ollama
CHAT_MODEL=qwen3.5:2b
CHAT_BASE_URL=http://localhost:11434
CHAT_API_KEY=
CHAT_TEMPERATURE=0.1

# Completion provider
COMPLETION_PROVIDER=ollama
COMPLETION_MODEL=qwen3.5:2b
COMPLETION_BASE_URL=http://localhost:11434
COMPLETION_API_KEY=
COMPLETION_TEMPERATURE=0.1

# Embedding provider
EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_BASE_URL=http://localhost:11434
EMBEDDING_API_KEY=

# Optional vision provider
VISION_PROVIDER=
VISION_MODEL=
VISION_BASE_URL=
VISION_API_KEY=
VISION_TEMPERATURE=0.1
```

视觉能力说明：
- `VISION_PROVIDER=openai_compatible` 时需要显式配置 `VISION_MODEL`、`VISION_BASE_URL`、`VISION_API_KEY`
- `VISION_PROVIDER=ollama` 时需要 `VISION_MODEL`，`VISION_API_KEY` 可留空
- 上层统一通过 `analyze_images(prompt, image_urls)` 调用视觉能力，因此业务层不需要区分 provider

### 3. 初始化测试数据

```bash
python src/test/init_test_data.py
```

这将创建：
- 测试用户（admin, user1, user2）
- 测试 Token（admin_token_123, user1_token_456, user2_token_789, demo_token_000）
- 题目分类（政治理论、历史文化、科学技术等）
- 示例题目（12 道涵盖多种题型的题目）
- FAISS 向量索引

### 4. 启动服务

```bash
python src/main.py
```

服务将在 `http://localhost:8000` 启动。

### 5. 访问系统

- **Web 界面**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs
- **ReDoc 文档**: http://localhost:8000/redoc
- **健康检查**: http://localhost:8000/health
- **OpenAPI Schema**: http://localhost:8000/openapi.json

## API 文档

### API 版本

系统提供两套 API 版本：

| 版本 | 前缀 | 功能 |
|------|------|------|
| v1 | `/api/v1` | 查题、信息查询（保持向后兼容） |
| v2 | `/api/v2` | 分类管理、AI 自动分类 |

### v1 查题接口

**GET** `/api/v1/query`

根据题目内容搜索答案。

#### 请求参数

| 参数     | 类型    | 必填 | 说明                                                     |
| -------- | ------- | ---- | -------------------------------------------------------- |
| token    | string  | 是   | 用户凭证                                                 |
| question | string  | 否   | 题目内容（与 title、q 三选一）                           |
| title    | string  | 否   | 题目内容（优先级最高）                                   |
| q        | string  | 否   | 题目内容                                                 |
| options  | string  | 否   | 选项内容，多个用换行分隔                                 |
| type     | string  | 否   | 题目类型（single/multiple/judgement/completion/essay/unknown） |
| subject  | string  | 否   | 科目/课程名称                                            |
| stream   | boolean | 否   | 设为 `true` 时启用 SSE 心跳流式响应                      |
| force_ai | boolean | 否   | 设为 `true` 时强制使用 AI 模型回答，跳过向量检索        |

#### 响应说明

- 默认返回 `application/json`
- `stream=true` 时返回 `text/event-stream`
- 查询处理中每 15 秒发送一次 `heartbeat` 事件
- 最后一条 `result` 事件包含完整 JSON 结果，结构与普通查询响应一致

#### 选项图片说明

当 `options` 中包含图片 URL 时：

- 系统会先提取并归一化图片链接（包括去重、清理拼接/包裹噪音）
- 如果已启用 `VISION_PROVIDER`，会对图片做基础理解并把结果注入选项文本
- 对于图片型选项，查询 Agent 还能按需调用图片分析工具做二次查看
- 如果视觉能力不可用或图片解析失败，请求不会中断，而是降级为"文本 + 原始 URL"继续答题

#### 示例请求

```bash
curl -N "http://localhost:8000/api/v1/query?token=demo_token_000&title=中国梦的本质是什么？&stream=true"
```

#### SSE 事件示例

```text
event: heartbeat
data: {}

event: result
data: {"code": 1, "message": "请求成功", "data": {"question": "中国梦的本质是什么？", "answer": "实现中华民族伟大复兴，本质是国家富强、民族振兴、人民幸福。", "times": 999, "ai": false}}
```

#### 非流式响应示例

```json
{
    "code": 1,
    "message": "请求成功",
    "data": {
        "question": "中国梦的本质是什么？",
        "answer": "实现中华民族伟大复兴，本质是国家富强、民族振兴、人民幸福。",
        "times": 999,
        "ai": false
    }
}
```

### v1 配额查询接口

**GET** `/api/v1/info`

获取当前 token 的调用次数统计。

#### 请求参数

| 参数  | 类型   | 必填 | 说明     |
| ----- | ------ | ---- | -------- |
| token | string | 是   | 用户凭证 |

#### 响应示例

```json
{
    "code": 1,
    "message": "请求成功",
    "data": {
        "times": 1000,
        "user_times": 5000,
        "success_times": 4800
    }
}
```

### v2 分类管理接口

目前 v2 主要提供分类管理功能，更多题目 CRUD 端点待完善。

| 方法   | 路径                                        | 说明                   |
| ------ | ------------------------------------------- | ---------------------- |
| GET    | `/api/v2/categories`                        | 获取所有分类列表       |
| POST   | `/api/v2/categories`                        | 创建新分类             |
| DELETE | `/api/v2/categories/{category_id}`          | 删除分类               |
| POST   | `/api/v2/questions/{question_id}/categories`| 分配题目到多个分类     |
| GET    | `/api/v2/questions/{question_id}/categories`| 获取题目的所有分类     |
| POST   | `/api/v2/questions/{question_id}/categories/remove?category_id=X` | 从题目移除分类 |
| POST   | `/api/v2/classify/ai`                       | AI 自动分类            |

## Web 界面

### 主要功能

1. **题目查询**
   - 输入 Token 和题目内容
   - 选择题目类型
   - 填写选项（可选）
   - 一键搜索答案

2. **结果展示**
   - JSON 格式化显示
   - 成功/失败标识
   - 实时加载状态

3. **全屏查看**
   - 点击"全屏查看"按钮
   - 90% 屏幕空间展示详情
   - 支持 ESC 键关闭

4. **结果复制**
   - 一键复制到剪贴板
   - 即时反馈提示

### 界面截图

访问 http://localhost:8000 查看完整界面。

## 开发指南

### 项目结构

```
ai-tiku/
├── src/
│   ├── agents/           # AI Agent 层
│   │   ├── __init__.py
│   │   ├── query.py          # 答题 Agent（含图片分析工具）
│   │   ├── classification.py # 分类 Agent（LangGraph）
│   │   ├── reviewer.py       # 复审 Agent
│   │   ├── rag_chat.py       # RAG 对话 Agent
│   │   └── prompts/          # 提示词模板
│   │       ├── classify.py
│   │       ├── query.py
│   │       └── review.py
│   ├── models/           # SQLModel 数据模型
│   │   ├── user.py
│   │   ├── api_key.py
│   │   ├── question.py
│   │   ├── category.py
│   │   ├── question_category.py
│   │   └── query_log.py
│   ├── routers/          # API 路由
│   │   ├── api_v1.py         # 查题/信息接口
│   │   └── api_v2.py         # 分类管理接口
│   ├── schemas/          # Pydantic 请求/响应模型
│   │   ├── common.py
│   │   ├── v1.py
│   │   └── v2.py
│   ├── services/         # 业务逻辑层
│   │   ├── question_service.py
│   │   ├── classification_service.py
│   │   ├── ai_service.py
│   │   └── user_service.py
│   ├── utils/            # 工具模块
│   │   ├── dbc.py            # Database + VectorStore
│   │   ├── llm.py            # Provider 路由与 LLM 调用
│   │   ├── option_images.py  # 选项图片处理
│   │   ├── vision_inputs.py  # 视觉输入处理
│   │   ├── access_token.py   # JWT 工具
│   │   └── string_tool.py    # 字符串工具
│   ├── test/             # 测试数据
│   │   └── init_test_data.py
│   ├── dependencies.py   # FastAPI 依赖注入
│   ├── main.py           # 应用入口
│   └── index.html        # Web UI
├── tests/                # 测试用例
│   ├── agents/test_query.py
│   ├── routers/test_api_v1.py
│   ├── routers/test_api_v1_query_stream.py
│   ├── services/test_ai_service.py
│   └── utils/
│       ├── test_llm.py
│       ├── test_option_images.py
│       └── test_vision_inputs.py
├── data/                 # 运行时数据（自动生成）
│   ├── db.sqlite3
│   └── embeddings/
├── docs/                 # 设计文档
├── .env                  # 环境变量配置
├── .env.example          # 配置示例
├── pyproject.toml        # 项目配置
└── README.md
```

### 添加新题目

```python
from src.utils.dbc import db
from src.models.question import Question

# 添加到数据库
question = db.create(Question(
    question_title="题目内容",
    question_type="single",
    question_options="A. 选项A\nB. 选项B",
    answer_text="正确答案",
    is_ai_generated=False,
    source="题库来源",
))

# 添加到向量库
from src.utils.dbc import VectorStore
vector_store = VectorStore(category_id=0, category_name="全部题目")
vector_store.add_documents([question])
```

### 使用分类 Agent

```python
from src.agents.classification import classifier

# 设置可用分类（由 service 层传入，而非 Agent 自行查询）
classifier.set_categories(categories)

# 对题目进行分类
ai_results = classifier.classify(
    question_text="题目内容",
    options=["选项 A", "选项 B"]
)

for result in ai_results:
    print(f"分类 ID: {result.category_id}, 置信度: {result.confidence}")
```

### 使用 AI 服务（推荐方式）

```python
from src.services.ai_service import ai_service

# AI 生成答案
answer = ai_service.generate_answer(
    title="题目内容",
    options=["选项 A", "选项 B"],
    question_type="single",
    subject="科目名称",
)

# 先分类再回答
result = ai_service.classify_and_answer(
    question="题目内容",
    options=["选项 A", "选项 B"],
)
```

## 配置说明

### 环境变量

| 变量名                 | 默认值                 | 说明                                                     |
| ---------------------- | ---------------------- | -------------------------------------------------------- |
| MODEL_TEMPERATURE      | 0.1                    | 全局默认温度                                             |
| CHAT_PROVIDER          | ollama                 | Chat provider，可选 `ollama` / `openai_compatible`       |
| CHAT_MODEL             | qwen3.5:2b             | Chat 模型名称                                            |
| CHAT_BASE_URL          | http://localhost:11434 | Chat provider 接口地址                                   |
| CHAT_API_KEY           | 空                     | Chat provider API Key                                    |
| CHAT_TEMPERATURE       | 0.1                    | Chat 温度                                                |
| COMPLETION_PROVIDER    | ollama                 | Completion provider                                      |
| COMPLETION_MODEL       | qwen3.5:2b             | Completion 模型名称                                      |
| COMPLETION_BASE_URL    | http://localhost:11434 | Completion provider 接口地址                             |
| COMPLETION_API_KEY     | 空                     | Completion provider API Key                              |
| COMPLETION_TEMPERATURE | 0.1                    | Completion 温度                                          |
| EMBEDDING_PROVIDER     | ollama                 | Embedding provider                                       |
| EMBEDDING_MODEL        | nomic-embed-text       | Embedding 模型名称                                       |
| EMBEDDING_BASE_URL     | http://localhost:11434 | Embedding provider 接口地址                              |
| EMBEDDING_API_KEY      | 空                     | Embedding provider API Key                               |
| VISION_PROVIDER        | 空                     | Vision provider（可选，`ollama` / `openai_compatible`）  |
| VISION_MODEL           | 空                     | Vision 模型名称                                          |
| VISION_BASE_URL        | 空                     | Vision provider 接口地址                                 |
| VISION_API_KEY         | 空                     | Vision provider API Key                                  |

### Provider 配置

本项目支持 `ollama` 与通用 `openai_compatible` provider，模型路由与初始化逻辑集中在 `src/utils/llm.py`。

- `ollama`：适合本地模型部署，通常使用 `http://localhost:11434`
- `openai_compatible`：适合任何兼容 OpenAI 接口协议的服务，且当 `*_PROVIDER=openai_compatible` 时必须显式配置对应的 `*_MODEL`、`*_BASE_URL`、`*_API_KEY`

### Ollama 配置

确保已安装并运行 Ollama 服务：

```bash
# 拉取模型
ollama pull qwen3.5:2b
ollama pull nomic-embed-text

# 启动服务
ollama serve
```

### 混合 Provider 示例

```bash
CHAT_PROVIDER=openai_compatible
CHAT_MODEL=gpt-4o-mini
CHAT_BASE_URL=https://api.openai.com/v1
CHAT_API_KEY=your-openai-compatible-key
CHAT_TEMPERATURE=0.1

COMPLETION_PROVIDER=ollama
COMPLETION_MODEL=qwen3.5:2b
COMPLETION_BASE_URL=http://localhost:11434
COMPLETION_API_KEY=
COMPLETION_TEMPERATURE=0.1

EMBEDDING_PROVIDER=ollama
EMBEDDING_MODEL=nomic-embed-text
EMBEDDING_BASE_URL=http://localhost:11434
EMBEDDING_API_KEY=
```

## 数据库表结构

### users - 用户表

| 字段      | 类型    | 说明                               |
| --------- | ------- | ---------------------------------- |
| id        | INTEGER | 主键 ID                            |
| username  | TEXT    | 用户名（唯一）                     |
| password  | TEXT    | 密码（argon2 哈希）                |
| email     | TEXT    | 邮箱（唯一）                       |
| role      | TEXT    | 角色（admin / user）               |
| status    | TEXT    | 状态（active / disabled）          |
| updated_at| DATETIME| 更新时间                           |

### api_keys - API 凭证表

| 字段              | 类型    | 说明                     |
| ----------------- | ------- | ------------------------ |
| id                | INTEGER | 主键 ID                  |
| token             | TEXT    | 用户唯一凭证（唯一）     |
| owner_id          | INTEGER | 所属用户 ID（外键）      |
| total_queries     | INTEGER | 总查询次数               |
| success_queries   | INTEGER | 成功查询次数             |
| remaining_queries | INTEGER | 剩余查询次数             |
| status            | TEXT    | 状态（active/disabled/exhausted/expired） |
| updated_at        | DATETIME| 更新时间                 |

### questions - 题目表

| 字段            | 类型    | 说明                                   |
| --------------- | ------- | -------------------------------------- |
| id              | INTEGER | 题目 ID                                |
| question_type   | TEXT    | 题目类型（single/multiple/judgement/completion/essay/unknown） |
| question_title  | TEXT    | 题目内容                               |
| question_options| TEXT    | 选项内容（多行文本）                   |
| answer_text     | TEXT    | 答案内容                               |
| is_ai_generated | INTEGER | 是否 AI 生成                           |
| review_status   | TEXT    | 审核状态（pending/approved/rejected）  |
| source          | TEXT    | 题目来源                               |
| updated_at      | DATETIME| 更新时间                               |

### categories - 分类表

| 字段        | 类型    | 说明         |
| ----------- | ------- | ------------ |
| id          | INTEGER | 分类 ID      |
| name        | TEXT    | 分类名称（唯一） |
| description | TEXT    | 分类描述     |

### question_categories - 题目分类关联表

| 字段        | 类型    | 说明                  |
| ----------- | ------- | --------------------- |
| id          | INTEGER | 主键 ID               |
| question_id | INTEGER | 题目 ID（外键）       |
| category_id | INTEGER | 分类 ID（外键）       |

### query_logs - 查询日志表

| 字段     | 类型    | 说明                   |
| -------- | ------- | ---------------------- |
| id       | INTEGER | 主键 ID                |
| token_id | INTEGER | Token ID（外键）       |
| query_text| TEXT   | 查询内容               |
| found    | INTEGER | 是否找到答案           |

## 安全建议

1. **Token 管理**：不要将真实 Token 提交到版本控制
2. **环境变量**：敏感信息使用环境变量存储
3. **访问控制**：生产环境配置适当的认证和限流机制
4. **日志审计**：定期查看 query_logs 表监控使用情况

## 许可证

本项目采用 MIT 许可证。

## 贡献

欢迎提交 Issue 和 Pull Request！

## 联系方式

- 项目地址：https://github.com/your-org/ai-tiku
- 问题反馈：请提交 Issue
