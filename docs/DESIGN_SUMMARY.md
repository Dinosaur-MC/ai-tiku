# AI-Tiku 系统设计与实现总结

## 📋 项目概述

AI-Tiku 是一个基于人工智能的题库答题服务系统，提供题目查询、答案生成、智能分类、答案复审等功能。当前实现基于 FastAPI、LangChain、LangGraph、FAISS 与多 provider LLM 能力，支持文本模型、嵌入模型与视觉模型的独立配置。

## 🎯 当前核心功能

### 1. 查题接口 (`/api/v1/query`)
- **功能**: 根据题目内容搜索答案
- **特性**:
  - 支持向量相似度搜索
  - AI 辅助生成答案
  - 支持多种题型（单选、多选、判断、填空等）
  - 支持 `title > q > question` 的请求优先级
  - 支持 `stream=true` 的 SSE 心跳流式响应
  - 支持选择题选项中的图片 URL 预处理、视觉摘要与按需图片分析工具
  - Token 配额管理

### 2. 配额查询接口 (`/api/v1/info`)
- **功能**: 获取用户 Token 的使用统计
- **返回**: 剩余次数、总使用次数、成功次数

### 3. Web 界面
- **技术栈**: 直接由 FastAPI 提供的静态 HTML 页面
- **特性**:
  - 响应式设计
  - 结果复制
  - 基本查询交互

## 🏗️ 当前系统架构

```
FastAPI Router
  ├─ src/routers/api_v1.py
  ├─ src/routers/api_v2.py
  │
  ▼
Service Layer
  ├─ src/services/ai_service.py
  ├─ src/services/question_service.py
  ├─ src/services/classification_service.py
  └─ src/services/user_service.py
  │
  ▼
Agent Layer
  ├─ src/agents/query.py
  ├─ src/agents/classification.py
  ├─ src/agents/reviewer.py
  └─ src/agents/rag_chat.py
  │
  ▼
Persistence / Retrieval
  ├─ src/utils/dbc.py
  ├─ SQLite
  └─ FAISS
  │
  ▼
LLM Layer
  ├─ src/utils/llm.py
  ├─ src/utils/option_images.py
  └─ src/utils/vision_inputs.py
```

## 📁 当前文件结构

```
ai-tiku/
├── src/
│   ├── agents/                  # Agent 层
│   │   ├── query.py             - 查题 Agent（含图片工具分支）
│   │   ├── classification.py    - 题目分类 Agent
│   │   ├── reviewer.py          - 答案复审 Agent
│   │   └── rag_chat.py          - RAG 对话 Agent
│   ├── prompts/                 # 提示词模板
│   ├── routers/                 # 路由层
│   │   ├── api_v1.py            - 查题与配额接口
│   │   └── api_v2.py            - 分类与管理接口
│   ├── services/                # 服务层
│   │   ├── ai_service.py        - AI 编排服务
│   │   ├── question_service.py
│   │   ├── classification_service.py
│   │   └── user_service.py
│   ├── schemas/
│   ├── models/
│   ├── utils/
│   │   ├── llm.py               - Provider 配置、重试、视觉适配
│   │   ├── option_images.py     - 选项图片 URL 解析与清理
│   │   ├── vision_inputs.py     - Ollama 视觉输入准备
│   │   ├── dbc.py               - SQLite + FAISS
│   │   └── access_token.py
│   ├── dependencies.py
│   ├── main.py                  - 应用入口
│   ├── index.html               - Web 界面
│   └── test/
├── tests/                       # First-party pytest 测试
├── data/
├── docs/
├── .env
├── .env.example
├── pyproject.toml
└── README.md
```

## 🔧 Provider 与模型配置

当前模型能力按职责拆分为：
- `CHAT_*`
- `COMPLETION_*`
- `EMBEDDING_*`
- `VISION_*`

### 支持的 provider
- `ollama`
- `openai_compatible`

### Vision 说明
- `VISION_PROVIDER=openai_compatible`
  - 需要 `VISION_MODEL`、`VISION_BASE_URL`、`VISION_API_KEY`
- `VISION_PROVIDER=ollama`
  - 需要 `VISION_MODEL`
  - `VISION_API_KEY` 可留空
  - 视觉输入支持 URL 直传或下载后编码

## 💡 当前关键设计点

### 1. 选项图片预处理
- 从 `options` 中提取图片 URL
- 处理重复、拼接、markdown 包裹等噪音
- 输出增强后的选项文本
- 当视觉能力启用时，注入基础图片理解结果

### 2. QueryAgent 图片工具路径
- 非图片场景继续走普通 completion 路径
- 图片型选项场景可切换到带工具的答题路径
- 工具输出仍复用现有格式校正逻辑

### 3. Vision provider 抽象
- 上层统一调用 `analyze_images(prompt, image_urls)`
- `llm.py` 内部按 provider 构建 adapter
- `vision_inputs.py` 处理 Ollama 图片输入准备差异

### 4. SSE 查询流
- `/api/v1/query?stream=true` 支持心跳流式响应
- 查询进行中发送 `heartbeat`
- 最终通过 `result` 事件返回完整 JSON 结果

## 🧪 当前测试覆盖

仓库已有 first-party `pytest` 测试，覆盖：
- `tests/utils/test_llm.py`
- `tests/utils/test_option_images.py`
- `tests/utils/test_vision_inputs.py`
- `tests/agents/test_query.py`
- `tests/services/test_ai_service.py`
- `tests/routers/test_api_v1.py`
- `tests/routers/test_api_v1_query_stream.py`

常用命令：

```bash
uv run pytest tests -v
uv run pytest tests/utils/test_llm.py -v
uv run pytest tests/routers/test_api_v1.py -v
```

## 🚀 当前启动流程

### 1. 安装依赖
```bash
uv sync
```

### 2. 配置环境变量
```bash
cp .env.example .env
```

### 3. 初始化测试数据
```bash
python src/test/init_test_data.py
```

### 4. 启动服务
```bash
python src/main.py
```

## 📌 备注

- 本文档描述的是当前 `src/` 代码树，不再以历史旧布局为准。
- 旧文档中提到的 `api.py`、`db.py`、`answer_retriever.py`、`ui.py`、`start.py` 等不再是主实现入口。
- 若与更老文档冲突，以当前 README、CLAUDE.md 和 `src/` 实现为准。
