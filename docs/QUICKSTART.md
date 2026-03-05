# AI-Tiku 快速入门指南

欢迎使用 AI-Tiku 智能题库答题系统！本指南将帮助您快速上手。

## 📦 安装步骤

### 1. 安装依赖

**方式一：使用 uv（推荐）**

```bash
uv install
```

**方式二：使用 pip**

```bash
pip install -r requirements.txt
```

### 2. 配置 Ollama

确保已安装 Ollama，并下载所需模型：

```bash
# 拉取语言模型
ollama pull qwen3.5:2b

# 拉取嵌入模型
ollama pull nomic-embed-text

# 启动 Ollama 服务（如果未运行）
ollama serve
```

### 3. 配置环境变量

```bash
# 复制示例配置
cp .env.example .env

# 编辑 .env 文件（通常无需修改默认值）
MODEL_NAME=qwen3.5:2b
EMBEDDING_MODEL_NAME=nomic-embed-text
MODEL_TEMPERATURE=0.1
```

## 🚀 启动系统

### 方式一：快速启动（推荐）

```bash
python start.py
```

这将自动完成：
- 检查 Ollama 服务
- 初始化数据库（首次运行）
- 启动 Web 服务器

### 方式二：分步启动

```bash
# 1. 初始化数据库（首次运行）
python src/init_db.py

# 2. 启动服务
python src/main.py
```

## 🌐 访问系统

服务启动后，打开浏览器访问：

- **Web 界面**: http://localhost:8000
- **API 文档**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/health

## 🎯 基本使用

### 使用 Web 界面查题

1. **输入 Token**
   - 默认测试 Token: `test123456`
   
2. **输入题目**
   - 在"题目内容"框中输入要查询的题目
   
3. **选择题型（可选）**
   - 单选题、多选题、判断题等
   
4. **填写选项（可选）**
   - 如果是选择题，可填写选项帮助 AI 判断
   
5. **点击"搜索答案"**
   - 等待片刻，查看结果

### 全屏查看结果

- 点击结果下方的"全屏查看"按钮
- 结果将以 90% 屏幕空间展示
- 按 ESC 或点击右上角 × 关闭

### 复制结果

- 点击"复制结果"按钮
- 结果将复制到剪贴板

## 🧪 测试系统

运行测试脚本验证功能：

```bash
python src/test_api.py
```

这将测试：
- ✓ 健康检查端点
- ✓ 根路径访问
- ✓ 简单查题
- ✓ 带选项查题
- ✓ 配额查询
- ✓ 无效 Token 处理

## 📝 使用示例

### 示例 1：查询政治理论题目

**输入：**
```
Token: test123456
题目：中国梦的本质是什么？
题型：未知题型
```

**输出：**
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

### 示例 2：查询带选项的单选题

**输入：**
```
Token: test123456
题目：马克思主义活的灵魂是？
题型：单选题
选项：
A. 实事求是
B. 具体问题具体分析
C. 理论联系实际
D. 群众路线
```

**输出：**
```json
{
  "code": 1,
  "message": "请求成功",
  "data": {
    "question": "马克思主义活的灵魂是？",
    "answer": "B",
    "times": 998,
    "ai": true
  }
}
```

### 示例 3：查询配额信息

**输入：**
```
Token: test123456
```

**输出：**
```json
{
  "code": 1,
  "message": "请求成功",
  "data": {
    "times": 998,
    "user_times": 2,
    "success_times": 2
  }
}
```

## 🔧 常见问题

### Q1: 提示"无法连接到服务器"

**解决方案：**
1. 确认服务已启动（`python src/main.py`）
2. 检查端口 8000 是否被占用
3. 尝试访问 http://localhost:8000/health

### Q2: 提示"无效的 token"

**解决方案：**
1. 确认 Token 拼写正确
2. 使用测试 Token：`test123456`
3. 运行 `python src/init_db.py` 重新初始化

### Q3: AI 生成答案不准确

**解决方案：**
1. 提供更详细的选项信息
2. 指定正确的题型
3. 考虑人工录入准确答案到题库

### Q4: Ollama 连接失败

**解决方案：**
```bash
# 检查 Ollama 是否运行
ollama list

# 重启 Ollama 服务
ollama serve
```

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

## 🛠️ 进阶使用

### 添加新题目

```python
from src.db import db
from src.agents.rag_chat import rag_chat

# 添加到数据库
q_id = db.add_question(
    question_text="你的题目",
    answer_text="正确答案",
    source="自定义题库"
)

# 添加到向量库
rag_chat.add_document(
    question="你的题目",
    answer="正确答案",
    metadata={"id": q_id}
)
```

### 使用 API 编程调用

```python
import requests

response = requests.get(
    "http://localhost:8000/api/query",
    params={
        "token": "test123456",
        "question": "中国梦的本质是什么？"
    }
)

result = response.json()
print(result['data']['answer'])
```

## 📞 获取帮助

如遇到其他问题：

1. 查看日志输出
2. 访问 API 文档：http://localhost:8000/docs
3. 提交 Issue 反馈

---

**祝您使用愉快！** 🎉
