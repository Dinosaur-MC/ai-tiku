# AI-Tiku 快速入门指南

欢迎使用 AI-Tiku 智能题库答题系统！本指南将帮助您快速上手当前版本。

## 📦 安装步骤

### 1. 安装依赖

**方式一：使用 uv（推荐）**

```bash
uv sync
```

**方式二：使用 pip**

```bash
pip install -r requirements.txt
```

### 2. 配置模型与环境变量

复制配置文件：

```bash
cp .env.example .env
```

最小 Ollama 本地配置示例：

```bash
MODEL_TEMPERATURE=0.1

CHAT_PROVIDER=ollama
CHAT_MODEL=qwen3.5:2b
CHAT_BASE_URL=http://localhost:11434
CHAT_API_KEY=
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

VISION_PROVIDER=ollama
VISION_MODEL=llava:7b
VISION_BASE_URL=http://localhost:11434
VISION_API_KEY=
VISION_TEMPERATURE=0.1
```

### 3. 准备 Ollama 模型（本地模型时）

确保已安装并运行 Ollama，并下载所需模型：

```bash
# 拉取语言模型
ollama pull qwen3.5:2b

# 拉取嵌入模型
ollama pull nomic-embed-text

# 拉取视觉模型（如果要启用图片理解）
ollama pull llava:7b

# 启动 Ollama 服务（如果未运行）
ollama serve
```

### 4. 初始化测试数据

```bash
python src/test/init_test_data.py
```

### 5. 启动系统

```bash
python src/main.py
```

## 🌐 访问系统

服务启动后，打开浏览器访问：

- **Web 界面**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **健康检查**: http://localhost:8000/health

## 🎯 基本使用

### 使用 Web 界面查题

1. 输入 Token（如测试 Token: `test123456`）
2. 输入题目内容
3. 选择题型（可选）
4. 填写选项（可选）
5. 点击“搜索答案”

### 选择题选项中的图片 URL

如果选择题选项里包含图片 URL：
- 系统会自动提取并归一化图片链接
- 视觉能力启用时会对选项图片做基础理解
- 对图片型选项，Query Agent 还能按需调用图片分析工具进一步查看
- 如果视觉能力不可用或图片解析失败，请求不会中断，而会降级为“文本 + 原始 URL”继续答题

## 🧪 测试系统

### 运行完整测试

```bash
uv run pytest tests -v
```

### 运行常用聚焦测试

```bash
uv run pytest tests/utils/test_llm.py -v
uv run pytest tests/routers/test_api_v1.py -v
uv run pytest tests/services/test_ai_service.py -v
```

## 📝 示例

### 示例 1：普通查题

```bash
curl "http://localhost:8000/api/v1/query?token=test123456&title=中国梦的本质是什么？"
```

### 示例 2：带图片型选项的查题

```bash
curl "http://localhost:8000/api/v1/query?token=test123456&title=以下采用的是直接类比法的是（+）&options=A.%20https://img.test/a.png%0AB.%20普通选项&type=single"
```

### 示例 3：SSE 流式查题

```bash
curl -N "http://localhost:8000/api/v1/query?token=test123456&title=中国梦的本质是什么？&stream=true"
```

## 🔧 常见问题

### Q1: Ollama 连接失败

**解决方案：**

```bash
ollama list
ollama serve
```

### Q2: 图片选项没有被理解

**检查项：**
1. `VISION_PROVIDER` 是否已配置
2. `VISION_MODEL` 是否为支持视觉的模型
3. 图片 URL 是否可访问
4. 如果使用 Ollama，确认视觉模型已下载

### Q3: 提示“无效的 token”

**解决方案：**
1. 确认 Token 拼写正确
2. 使用测试 Token：`test123456`
3. 运行 `python src/test/init_test_data.py` 重新初始化测试数据

## 📊 预置数据

系统初始化后包含：

### 测试 Token
- `test123456` (1000 次)
- `demo789012` (500 次)
- `user345678` (100 次)

### 题目分类
- 政治理论
- 历史文化
- 科学技术
- 法律法规
- 经济社会
- 教育心理

### 示例题目
- 8 道精选题目，涵盖各分类
