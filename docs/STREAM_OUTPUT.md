# QueryAgent 流式输出说明

## 概述

QueryAgent 现已支持 **LLM 流式输出**，可以在 LLM 生成答案时实时显示响应内容，便于调试和观察模型生成过程。

---

## 🎯 功能特性

### 1. **实时输出 LLM 响应** ✅

在调用 LLM 时，答案会逐字/逐句地实时输出到控制台，而不是等待完整响应后再显示。

**效果**:
```
[LLM 实时响应]: 中华民族伟大复兴是实现中国梦的核心内涵...
```

### 2. **支持两种模式的流式输出** ✅

#### 模式 1: 简单回答（流式）
```python
result = query_agent.answer(
    question="中国梦是什么？",
    question_type="completion"
)
# 输出：[LLM 实时响应]: <实时显示答案内容>
```

#### 模式 2: 带置信度评估（双重流式）
```python
result = query_agent.answer(
    question="马克思主义的基本原理有哪些？",
    return_confidence=True
)
# 输出：
# [LLM 实时响应]: <实时显示答案内容>
# [置信度评估]: <实时显示置信度 JSON>
```

---

## 💡 使用方法

### 基本用法

```python
from agents.query import query_agent

# 简单回答（会自动流式输出）
result = query_agent.answer(
    question="谁是矛盾论的作者？",
    options=["A. 马克思", "B. 毛泽东", "C. 列宁"],
    question_type="single"
)

print(f"最终答案：{result['answer']}")
```

### 带置信度的回答

```python
# 带置信度评估（两次流式输出）
result = query_agent.answer(
    question="什么是人工智能？",
    return_confidence=True
)

print(f"答案：{result['answer']}")
print(f"置信度：{result['confidence']}")
print(f"理由：{result['reasoning']}")
```

### 批量处理

```python
questions = [
    {"question": "题目 1", "type": "single"},
    {"question": "题目 2", "type": "completion"},
]

results = query_agent.batch_answer(questions)
# 每道题都会流式输出
```

---

## 🔧 实现原理

### 核心代码

```python
# 使用 chat.stream() 替代 chat.invoke()
answer_chunks = []
print("\n[LLM 实时响应]: ", end="", flush=True)

for chunk in chat.stream(messages):
    content = chunk.content if hasattr(chunk, 'content') else str(chunk)
    if content:
        answer_chunks.append(content)
        # 实时输出到控制台
        print(content, end="", flush=True)

# 合并所有片段
answer = "".join(answer_chunks).strip()
```

### 关键组件

1. **`chat.stream(messages)`**: LangChain 的流式 API
2. **`print(..., end="", flush=True)`**: 实时输出不换行
3. **`answer_chunks`**: 收集所有响应片段
4. **`"".join(answer_chunks)`**: 合并为完整答案

---

## 📊 输出示例

### 示例 1: 填空题

```
【测试】中国梦是什么？
------------------------------------------------------------
2026-03-07 00:17:53 - agents.query - INFO - 开始调用 LLM（流式输出）...

[LLM 实时响应]: 中华民族伟大复兴
============================================================
✅ 最终答案：中华民族伟大复兴
============================================================
```

### 示例 2: 选择题

```
【测试】谁是矛盾论的作者？
------------------------------------------------------------
2026-03-07 00:18:00 - agents.query - INFO - 开始调用 LLM（流式输出）...

[LLM 实时响应]: B
============================================================
✅ 最终答案：B
============================================================
```

### 示例 3: 带置信度评估

```
【测试】马克思主义的基本原理有哪些？
------------------------------------------------------------
2026-03-07 00:18:10 - agents.query - INFO - 开始调用 LLM（流式输出）...

[LLM 实时响应]: 马克思主义基本原理包括：
1. 辩证唯物主义
2. 历史唯物主义
3. 剩余价值理论
...

2026-03-07 00:18:20 - agents.query - INFO - 开始评估置信度（流式输出）...

[置信度评估]: {
  "confidence": 0.95,
  "reasoning": "答案涵盖了马克思主义的核心原理"
}

============================================================
✅ 最终答案：马克思主义基本原理包括...
✅ 置信度：0.95
✅ 理由：答案涵盖了马克思主义的核心原理
============================================================
```

---

## 🎛️ 日志级别说明

### DEBUG 级别
```
收到查询请求：question='中国梦是什么？...', type=completion, confidence=False
系统提示：你是一个专业的题库答题助手...
用户提示：【填空题】
题目：中国梦是什么？
答案：
置信度评估提示：题目：中国梦是什么？...
```

### INFO 级别
```
开始调用 LLM（流式输出）...
LLM 流式输出完成，答案长度：120
开始评估置信度（流式输出）...
置信度解析成功：confidence=0.95
```

### WARNING/ERROR 级别
```
置信度评估失败：JSON 解析失败，使用默认值
查询失败：网络连接超时
```

---

## 🧪 测试方法

### 运行测试脚本

```bash
# 简单测试
python src/test/test_stream_simple.py

# 完整测试
python src/test/test_stream_output.py
```

### 查看日志

```bash
# 显示详细日志
export LOG_LEVEL=DEBUG
python src/test/test_stream_simple.py
```

---

## ⚙️ 配置选项

### 启用/禁用实时输出

目前实时输出是**默认启用**的。如需禁用，可以注释掉相关代码：

```python
# 禁用实时输出（仅记录日志）
for chunk in chat.stream(messages):
    content = chunk.content if hasattr(chunk, 'content') else str(chunk)
    if content:
        answer_chunks.append(content)
        # print(content, end="", flush=True)  # 注释掉这行禁用输出
```

### 自定义输出格式

```python
# 修改输出前缀
print("[我的自定义前缀]: ", end="", flush=True)

# 修改输出颜色（需要 colorama 库）
from colorama import Fore
print(Fore.GREEN + "[LLM]: " + Fore.RESET, end="", flush=True)
```

---

## 📈 性能对比

| 模式 | 优点 | 缺点 |
|------|------|------|
| **流式输出** | - 实时可见<br>- 便于调试<br>- 用户体验好 | - 略微增加 I/O 开销 |
| **非流式** | - 代码简洁<br>- I/O 较少 | - 需等待完整响应<br>- 调试不便 |

**建议**: 
- ✅ **开发/调试环境**: 使用流式输出
- ✅ **生产环境**: 根据需求选择（推荐保留）

---

## 🔮 未来扩展

### 1. 可配置的输出回调

```python
def custom_output_callback(content: str):
    """自定义输出回调"""
    # 可以输出到文件、网络等
    pass

result = query_agent.answer(
    question="...",
    output_callback=custom_output_callback
)
```

### 2. 异步流式支持

```python
async def stream_answer():
    async for chunk in chat.astream(messages):
        print(chunk.content, end="", flush=True)
```

### 3. 进度条显示

```python
from tqdm import tqdm

for chunk in tqdm(chat.stream(messages), desc="生成中"):
    print(chunk.content, end="", flush=True)
```

---

## 📚 相关文档

- [`src/agents/query.py`](file://f:\Dinosaur_MC\Studio\Project\ai-tiku\src\agents\query.py) - QueryAgent实现
- [`src/test/test_stream_output.py`](file://f:\Dinosaur_MC\Studio\Project\ai-tiku\src\test\test_stream_output.py) - 流式输出测试
- [LangChain Streaming Docs](https://python.langchain.com/docs/modules/model_io/llms/streaming)

---

## 📝 版本历史

- **v3.3.0** (2026-03-07): 
  - ✨ 添加 LLM 流式输出支持
  - ✨ 实时显示答案生成过程
  - ✨ 支持置信度评估流式输出
  - ✨ 优化调试体验
  
- **v3.2.0**: 使用 Pydantic + LangChain 自动解析
- **v3.1.0**: 优化提示词模板，简化QueryAgent
- **v3.0.0**: 使用LangChain/LangGraph 重构
