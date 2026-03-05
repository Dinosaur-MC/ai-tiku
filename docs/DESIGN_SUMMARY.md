# AI-Tiku 系统设计与实现总结

## 📋 项目概述

AI-Tiku 是一个基于人工智能的题库答题服务系统，提供题目查询、答案生成、智能分类、答案复审等功能。系统采用 FastAPI 作为 Web 框架，结合 LangChain 和 Ollama 实现 AI 能力，使用 FAISS 进行向量检索。

## 🎯 核心功能

### 1. 查题接口 (`/api/query`)
- **功能**: 根据题目内容搜索答案
- **特性**: 
  - 支持向量相似度搜索
  - AI 辅助生成答案
  - 支持多种题型（单选、多选、判断、填空等）
  - Token 配额管理
  
### 2. 配额查询接口 (`/api/info`)
- **功能**: 获取用户 Token 的使用统计
- **返回**: 剩余次数、总使用次数、成功次数

### 3. Web 界面
- **技术栈**: HTML5 + MDUI
- **特性**:
  - 响应式设计
  - 全屏查看（90% 屏幕空间）
  - 结果复制
  - 实时加载状态

## 🏗️ 系统架构

```
┌─────────────────────────────────────┐
│         Web UI (MDUI)               │
│   http://localhost:8000             │
└──────────────┬──────────────────────┘
               │ REST API
┌──────────────▼──────────────────────┐
│      FastAPI Application            │
│  ┌──────────┐  ┌─────────────────┐  │
│  │ /query   │  │ /info           │  │
│  └────┬─────┘  └────────┬────────┘  │
└───────┼─────────────────┼───────────┘
        │                 │
┌───────▼────────┐  ┌────▼────────────┐
│ AnswerRetriever│  │  Database       │
│                │  │  • SQLite       │
│ • Vector Search│  │  • FAISS        │
│ • AI Generator │  │  • Vectors      │
└────────────────┘  └─────────────────┘
        │
┌───────▼──────────────────────────────┐
│         Agents Layer                 │
│  ┌──────────┐  ┌────────┐  ┌──────┐ │
│  │Classification│Review│  │ RAG  │ │
│  └──────────┘  └────────┘  └──────┘ │
└──────────────────────────────────────┘
        │
┌───────▼──────────────────────────────┐
│         Prompts Layer                │
│  • classify.py  • query.py          │
│  • review.py                         │
└──────────────────────────────────────┘
```

## 📁 文件结构

```
ai-tiku/
├── src/
│   ├── agents/              # Agent 层
│   │   ├── classification.py    - 题目分类 Agent
│   │   ├── reviewer.py          - 答案复审 Agent
│   │   └── rag_chat.py          - RAG 对话 Agent
│   ├── prompts/             # 提示词模板
│   │   ├── classify.py          - 分类提示词
│   │   ├── query.py             - 查询提示词
│   │   └── review.py            - 复审提示词
│   ├── main.py              # 应用入口
│   ├── api.py               # API 路由
│   ├── db.py                # 数据库管理
│   ├── llm.py               # LLM 封装
│   ├── answer_retriever.py  # 答案检索器
│   ├── ui.py                # Web UI
│   ├── init_db.py           # 数据库初始化
│   └── test_api.py          # API 测试
├── data/                    # 数据目录（自动生成）
│   ├── db.sqlite3           - SQLite 数据库
│   └── embeddings/          - FAISS 向量索引
├── .env                     # 环境变量配置
├── .env.example             # 配置示例
├── requirements.txt         # Python 依赖
├── pyproject.toml           # 项目配置
├── README.md                # 项目文档
├── QUICKSTART.md            # 快速入门
└── start.py                 # 快速启动脚本
```

## 🔧 技术栈

### 后端
- **Python 3.12+**: 主要编程语言
- **FastAPI**: Web 框架
- **Uvicorn**: ASGI 服务器

### 数据库
- **SQLite**: 关系型数据库
- **FAISS**: 向量数据库
- **SQLModel**: ORM 框架

### AI/ML
- **LangChain**: AI 应用框架
- **Ollama**: 本地 LLM 运行环境
- **Qwen3.5**: 语言模型
- **Nomic Embed Text**: 嵌入模型

### 前端
- **MDUI**: Material Design UI 组件库
- **HTML5/CSS3**: 页面结构和样式

## 💾 数据库设计

### 1. api_tokens - 用户凭证表
```sql
CREATE TABLE api_tokens (
    id INTEGER PRIMARY KEY,
    token TEXT UNIQUE,
    total_queries INTEGER DEFAULT 0,
    success_queries INTEGER DEFAULT 0,
    remaining_queries INTEGER DEFAULT 0,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
```

### 2. questions - 题目表
```sql
CREATE TABLE questions (
    id INTEGER PRIMARY KEY,
    question_text TEXT,
    answer_text TEXT,
    is_ai_generated INTEGER DEFAULT 0,
    source TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
```

### 3. categories - 分类表
```sql
CREATE TABLE categories (
    id INTEGER PRIMARY KEY,
    name TEXT,
    description TEXT
)
```

### 4. query_logs - 查询日志表
```sql
CREATE TABLE query_logs (
    id INTEGER PRIMARY KEY,
    token_id INTEGER,
    query_text TEXT,
    found INTEGER DEFAULT 0,
    created_at TIMESTAMP,
    FOREIGN KEY (token_id) REFERENCES api_tokens(id)
)
```

## 🔑 核心模块说明

### 1. Database Manager (`db.py`)
**功能**:
- SQLite 数据库连接管理
- FAISS 向量索引管理
- CRUD 操作封装

**关键类**:
- `Database`: SQLite 操作类
- `VectorStore`: FAISS 向量存储类

### 2. Answer Retriever (`answer_retriever.py`)
**功能**:
- 向量相似度搜索
- AI 答案生成
- 结果排序

**工作流程**:
1. 接收查询请求
2. 在 FAISS 中检索相似题目
3. 如果找到，返回匹配答案
4. 如果未找到，使用 LLM 生成答案
5. 返回结果

### 3. Classification Agent (`agents/classification.py`)
**功能**:
- 自动题目分类
- 多类别分配
- 分类置信度评估

**使用方法**:
```python
from agents.classification import classifier
categories = classifier.classify("题目内容")
```

### 4. Reviewer Agent (`agents/reviewer.py`)
**功能**:
- 答案质量审核
- 错误纠正
- 改进建议生成

**输出**:
- is_correct: 是否正确
- confidence: 置信度
- corrected_answer: 修正答案
- explanation: 审核说明

### 5. RAG Chat Agent (`agents/rag_chat.py`)
**功能**:
- 检索增强生成
- 对话式问答
- 引用来源标注

**特性**:
- 支持流式输出
- 对话历史管理
- 批量文档添加

### 6. LLM Wrapper (`llm.py`)
**功能**:
- 统一模型调用接口
- 同步/异步支持
- 流式生成支持

**方法**:
- `invoke()`: 同步调用
- `ainvoke()`: 异步调用
- `stream()`: 流式生成
- `chat_invoke()`: 聊天模式

## 🚀 启动流程

### 1. 环境准备
```bash
# 安装依赖
uv install

# 下载模型
ollama pull qwen3.5:2b
ollama pull nomic-embed-text
```

### 2. 初始化数据库
```bash
python src/init_db.py
```

**创建内容**:
- 3 个测试 Token
- 6 个题目分类
- 8 道示例题目

### 3. 启动服务
```bash
python src/main.py
# 或
python start.py
```

### 4. 访问系统
- Web 界面：http://localhost:8000
- API 文档：http://localhost:8000/docs

## 🧪 测试验证

运行测试脚本：
```bash
python src/test_api.py
```

**测试项**:
- ✓ 健康检查
- ✓ 根路径
- ✓ 简单查题
- ✓ 带选项查题
- ✓ 配额查询
- ✓ 无效 Token

## 📊 预置数据

### Token
| Token | 剩余次数 | 用途 |
|-------|---------|------|
| test123456 | 1000 | 主要测试 |
| demo789012 | 500 | 演示使用 |
| user345678 | 100 | 用户体验 |

### 分类
1. 政治理论
2. 历史文化
3. 科学技术
4. 法律法规
5. 经济社会
6. 教育心理

### 题目示例
- 中国梦的本质是什么？
- 马克思主义活的灵魂是？
- 抗日战争爆发于哪一年？
- 光在真空中的传播速度是多少？

## 🔒 安全特性

1. **Token 验证**: 所有 API 调用需要有效 Token
2. **配额限制**: 防止滥用
3. **日志记录**: 所有查询记录在案
4. **CORS 配置**: 跨域访问控制

## 🎨 UI 特性

1. **响应式设计**: 适配各种屏幕尺寸
2. **全屏查看**: 90% 屏幕空间展示详情
3. **一键复制**: 快速复制结果到剪贴板
4. **实时反馈**: 加载状态和错误提示
5. **美观界面**: MDUI Material Design 风格

## 📈 扩展方向

### 功能扩展
- [ ] 用户注册登录系统
- [ ] 题目批量导入导出
- [ ] 答案人工审核界面
- [ ] 统计分析仪表板
- [ ] 题目难度评估

### 技术优化
- [ ] Redis 缓存层
- [ ] Elasticsearch 全文检索
- [ ] Docker 容器化部署
- [ ] CI/CD 自动化
- [ ] 性能监控告警

### 模型升级
- [ ] 支持更多 LLM 后端
- [ ] 模型负载均衡
- [ ] 答案质量评分
- [ ] 智能题目推荐

## 💡 最佳实践

### 1. 题目录入
```python
# 推荐：同时添加到数据库和向量库
q_id = db.add_question(question, answer)
rag_chat.add_document(question, answer)
```

### 2. API 调用
```python
# 推荐：添加错误处理
try:
    response = requests.get(url, params=params)
    response.raise_for_status()
    result = response.json()
except requests.exceptions.RequestException as e:
    print(f"请求失败：{e}")
```

### 3. Token 管理
```bash
# 推荐：使用环境变量存储敏感信息
export TIKU_TOKEN="your_token_here"
```

## 🎓 学习资源

- **FastAPI 官方文档**: https://fastapi.tiangolo.com/
- **LangChain 文档**: https://python.langchain.com/
- **Ollama 文档**: https://ollama.ai/
- **FAISS 文档**: https://faiss.ai/
- **MDUI 文档**: https://mdui.org/

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

---

**开发团队**: AI-Tiku Team  
**最后更新**: 2026-03-05
