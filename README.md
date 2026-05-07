# AI-Tiku

AI 题库答题服务系统 - 基于 AI 的智能题库查询和答题解决方案。

## 📋 目录

- [功能特性](#功能特性)
- [系统架构](#系统架构)
- [快速开始](#快速开始)
- [API 文档](#api-文档)
- [Web 界面](#web-界面)
- [开发指南](#开发指南)
- [配置说明](#配置说明)

## ✨ 功能特性

### 核心功能

- **🔍 智能查题** - 基于向量相似度搜索题目，支持多种题型
- **🤖 AI 辅助答题** - 当题库中没有匹配答案时，使用 LLM 生成答案
- **📊 配额管理** - Token 级别的调用次数统计和限制
- **📝 题目分类** - 自动将题目分类到合适的知识类别
- **✅ 答案复审** - 审核和修正 AI 生成的答案，确保准确性
- **💬 RAG 对话** - 基于检索增强生成的对话式问答

### 技术特性

- **多模型支持** - 支持 Ollama、OpenAI 等多种大模型后端
- **向量检索** - 基于 FAISS 的高效向量相似度搜索
- **流式输出** - 支持 SSE 流式响应，提升用户体验
- **异步处理** - 完整的异步 IO 支持，高并发场景优化
- **RESTful API** - 标准化的 REST API 接口
- **响应式 UI** - 基于 MDUI 的现代化 Web 界面

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────┐
│              Web UI (MDUI)                   │
│         查询界面 | 结果展示 | 全屏查看        │
└────────────────┬────────────────────────────┘
                 │ HTTP/REST API
┌────────────────▼────────────────────────────┐
│              FastAPI Application             │
│    ┌──────────┐  ┌──────────┐  ┌─────────┐ │
│    │ /query   │  │ /info    │  │ /health │ │
│    └──────────┘  └──────────┘  └─────────┘ │
└────────────────┬────────────────────────────┘
                 │
    ┌────────────┼────────────┐
    │            │            │
┌───▼────┐  ┌───▼────┐  ┌───▼─────────┐
│ Answer │  │ Agents │  │  Database   │
│Retriever│  │ Layer  │  │   Manager   │
│        │  │        │  │             │
│• Search│  │• Class │  │ • SQLite    │
│• AI Gen│  │• Review│  │ • FAISS     │
│• Rank  │  │• RAG   │  │ • Vectors   │
└────────┘  └────────┘  └─────────────┘
                 │
         ┌───────┴───────┐
         │               │
    ┌────▼────┐    ┌─────▼─────┐
    │ Prompts │    │ LLM Layer │
    │ Templates│    │           │
    │         │    │• Embedding│
    │• Class  │    │• Completion│
    │• Query  │    │• Chat     │
    │• Review │    │• Stream   │
    └─────────┘    └───────────┘
```

### 模块说明

1. **Web UI 层** (`ui.py`)
   - 基于 MDUI 组件库的现代化界面
   - 支持全屏查看、结果复制
   - 响应式设计，适配各种屏幕

2. **API 层** (`api.py`)
   - `/query` - 查题接口
   - `/info` - 配额查询接口
   - Token 验证和配额管理

3. **Answer Retriever** (`answer_retriever.py`)
   - 向量相似度搜索
   - AI 答案生成
   - 结果排序和过滤

4. **Agents 层** (`agents/`)
   - `classification.py` - 题目分类 Agent
   - `reviewer.py` - 答案复审 Agent
   - `rag_chat.py` - RAG 对话 Agent

5. **Database 层** (`db.py`)
   - SQLite 关系型数据库
   - FAISS 向量数据库
   - 数据持久化管理

6. **LLM 层** (`src/utils/llm.py`)
   - 统一的模型调用接口
   - 支持流式和异步操作
   - 多模型后端适配

7. **Prompts 层** (`prompts/`)
   - 分类提示词模板
   - 查询提示词模板
   - 复审提示词模板

## 🚀 快速开始

### 环境要求

- Python 3.12+
- Ollama（使用本地模型时需要）或兼容 OpenAI 的接口服务
- uv 或 pip（包管理工具）

### 1. 安装依赖

```bash
# 使用 uv（推荐）
uv install

# 或使用 pip
pip install -e .
```

### 2. 配置环境变量

```bash
# 复制配置文件
cp .env.example .env
```

本项目支持 `ollama` 与通用 `openai_compatible` provider，模型路由与初始化逻辑集中在 `src/utils/llm.py`。

支持的 provider：
- `ollama`
- `openai_compatible`

按能力分别配置 `CHAT_*`、`COMPLETION_*`、`EMBEDDING_*`、`VISION_*` 环境变量：

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
VISION_PROVIDER=ollama
VISION_MODEL=llava:7b
VISION_BASE_URL=http://localhost:11434
VISION_API_KEY=
VISION_TEMPERATURE=0.1
```

视觉能力说明：
- `VISION_PROVIDER=openai_compatible` 时需要显式配置 `VISION_MODEL`、`VISION_BASE_URL`、`VISION_API_KEY`
- `VISION_PROVIDER=ollama` 时需要 `VISION_MODEL`，`VISION_API_KEY` 可留空
- 上层统一通过 `analyze_images(prompt, image_urls)` 调用视觉能力，因此业务层不需要区分 provider

混合 provider 配置示例：

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

### 3. 初始化数据库

```bash
python src/init_db.py
```

这将创建：
- 测试 Token（test123456, demo789012, user345678）
- 题目分类（政治理论、历史文化、科学技术等）
- 示例题目（8 道精选题目）

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

## 📖 API 文档

### 查题接口

**GET** `/api/v1/query`

根据题目内容搜索答案。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| token | string | 是 | 用户凭证 |
| question | string | 是 | 题目内容（与 title、q 三选一） |
| title | string | 否 | 题目内容（优先级最高） |
| q | string | 否 | 题目内容 |
| options | string | 否 | 选项内容，多个用换行分隔 |
| type | string | 否 | 题目类型（single/multiple/judgement/completion/unknown） |
| stream | boolean | 否 | 设为 `true` 时启用 SSE 心跳流式响应 |

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
- 如果视觉能力不可用或图片解析失败，请求不会中断，而是降级为“文本 + 原始 URL”继续答题

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

### 配额查询接口

**GET** `/api/info`

获取当前 token 的调用次数统计。

#### 请求参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| token | string | 是 | 用户凭证 |

#### 响应示例

``json
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

## 🎨 Web 界面

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

## 💻 开发指南

### 项目结构

```
ai-tiku/
├── src/
│   ├── agents/          # Agent 层
│   │   ├── classification.py
│   │   ├── reviewer.py
│   │   └── rag_chat.py
│   ├── prompts/         # 提示词模板
│   │   ├── classify.py
│   │   ├── query.py
│   │   └── review.py
│   ├── answer_retriever.py
│   ├── api.py
│   ├── db.py
│   ├── utils/             # DB / VectorStore / LLM / JWT 工具
│   │   └── llm.py         # Provider 路由与模型初始化
│   ├── main.py
│   ├── ui.py
│   └── init_db.py
├── data/                # 数据目录（自动生成）
│   ├── db.sqlite3
│   └── embeddings/
├── .env                 # 环境变量配置
├── .env.example         # 配置示例
├── pyproject.toml       # 项目配置
└── README.md            # 项目文档
```

### 添加新题目

```python
from src.db import db
from src.agents.rag_chat import rag_chat

# 添加到数据库
question_id = db.add_question(
    question_text="你的题目内容",
    answer_text="正确答案",
    is_ai_generated=False,
    source="题库来源"
)

# 添加到向量库
rag_chat.add_document(
    question="你的题目内容",
    answer="正确答案",
    metadata={"question_id": question_id}
)
```

### 使用分类 Agent

```python
from src.agents.classification import classifier

# 对题目进行分类
categories = classifier.classify(
    question_text="题目内容",
    options=["选项 A", "选项 B"]
)

# 分配分类
classifier.assign_to_question(question_id, [category_id])
```

### 使用复审 Agent

```python
from src.agents.reviewer import reviewer

# 复审答案
result = reviewer.review(
    question="题目内容",
    answer="待审核的答案",
    options=["选项 A", "选项 B"],
    question_type="single"
)

print(f"是否正确：{result['is_correct']}")
print(f"置信度：{result['confidence']}")
```

### 使用 RAG 对话

```python
from src.agents.rag_chat import rag_chat

# 对话式问答
response = rag_chat.chat("你的问题")
print(response['answer'])
print(response['sources'])  # 引用来源
```

## ⚙️ 配置说明

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| MODEL_TEMPERATURE | 0.1 | 全局默认温度 |
| CHAT_PROVIDER | ollama | Chat provider，可选 `ollama` / `openai_compatible` |
| CHAT_MODEL | qwen3.5:2b | Chat 模型名称 |
| CHAT_BASE_URL | http://localhost:11434 | Chat provider 接口地址 |
| CHAT_API_KEY | 空 | Chat provider API Key |
| CHAT_TEMPERATURE | 0.1 | Chat 温度，未设置时可回退到全局温度 |
| COMPLETION_PROVIDER | ollama | Completion provider，可选 `ollama` / `openai_compatible` |
| COMPLETION_MODEL | qwen3.5:2b | Completion 模型名称 |
| COMPLETION_BASE_URL | http://localhost:11434 | Completion provider 接口地址 |
| COMPLETION_API_KEY | 空 | Completion provider API Key |
| COMPLETION_TEMPERATURE | 0.1 | Completion 温度，未设置时可回退到全局温度 |
| EMBEDDING_PROVIDER | ollama | Embedding provider，可选 `ollama` / `openai_compatible` |
| EMBEDDING_MODEL | nomic-embed-text | Embedding 模型名称 |
| EMBEDDING_BASE_URL | http://localhost:11434 | Embedding provider 接口地址 |
| EMBEDDING_API_KEY | 空 | Embedding provider API Key |
| DATABASE_PATH | data/db.sqlite3 | SQLite 数据库路径 |
| EMBEDDINGS_DIR | data/embeddings | 向量库目录 |

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
MODEL_TEMPERATURE=0.1

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

### 自定义模型

如需切换模型或 provider，修改 `.env` 文件中的对应能力配置：

```bash
CHAT_PROVIDER=openai_compatible
CHAT_MODEL=gpt-4o-mini
CHAT_BASE_URL=https://api.openai.com/v1
CHAT_API_KEY=your-openai-compatible-key

COMPLETION_PROVIDER=ollama
COMPLETION_MODEL=llama3.2:3b
COMPLETION_BASE_URL=http://localhost:11434

EMBEDDING_PROVIDER=openai_compatible
EMBEDDING_MODEL=text-embedding-3-small
EMBEDDING_BASE_URL=https://api.openai.com/v1
EMBEDDING_API_KEY=your-openai-compatible-key
```

## 📊 数据库表结构

### api_tokens - 用户凭证表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 ID |
| token | TEXT | 用户唯一凭证 |
| total_queries | INTEGER | 总查询次数 |
| success_queries | INTEGER | 成功查询次数 |
| remaining_queries | INTEGER | 剩余查询次数 |

### questions - 题目表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 题目 ID |
| question_text | TEXT | 题目内容 |
| answer_text | TEXT | 答案内容 |
| is_ai_generated | INTEGER | 是否 AI 生成 |
| source | TEXT | 题目来源 |

### categories - 分类表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 分类 ID |
| name | TEXT | 分类名称 |
| description | TEXT | 分类描述 |

## 🔒 安全建议

1. **Token 管理**：不要将真实 Token 提交到版本控制
2. **环境变量**：敏感信息使用环境变量存储
3. **访问控制**：生产环境配置适当的认证和限流机制
4. **日志审计**：定期查看 query_logs 表监控使用情况

## 📝 许可证

本项目采用 MIT 许可证。

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📧 联系方式

- 项目地址：https://github.com/your-org/ai-tiku
- 问题反馈：请提交 Issue
