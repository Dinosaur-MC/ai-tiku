# Pydantic + LangChain 自动解析重构说明

## 概述

本次重构将所有 Agent 中的 `TypedDict` 改为 **Pydantic BaseModel**，并利用 **LangChain 的 PydanticOutputParser** 实现自动输出解析，不再需要手动的 JSON 解析和正则表达式提取。

---

## 🎯 重构内容

### 1. **QueryAgent** ✅

#### 重构前（使用 TypedDict + 手动 JSON 解析）

```python
from typing import TypedDict

class QueryState(TypedDict):
    question: str
    options: Optional[List[str]]
    # ... 多个字段

def _evaluate_confidence(self, question, options, answer):
    # 手动 JSON 解析
    try:
        result = json.loads(content)
        return {
            "confidence": float(result.get("confidence", 0.8)),
            "reasoning": result.get("reasoning", "")
        }
    except json.JSONDecodeError:
        # 尝试正则提取
        json_match = re.search(r"\{.*?\}", content, re.DOTALL)
        # ... 复杂的错误处理
```

#### 重构后（使用 Pydantic + 自动解析）

```python
from pydantic import BaseModel, Field

class ConfidenceResult(BaseModel):
    """置信度评估结果模型"""
    confidence: float = Field(description="置信度，0.0-1.0 之间的浮点数")
    reasoning: str = Field(description="简要说明答案的依据")

class QueryAgent:
    def __init__(self):
        # 初始化 Pydantic 输出解析器
        self.confidence_parser = PydanticOutputParser(
            pydantic_object=ConfidenceResult
        )
    
    def _evaluate_confidence(self, question, options, answer):
        # 构建提示词并添加格式指令
        format_instructions = self.parser.get_format_instructions()
        full_prompt = f"{prompt}\n\n{format_instructions}"
        
        # 调用 LLM 并自动解析
        response = chat.invoke(messages)
        confidence_result = self.confidence_parser.parse(response.content)
        
        # 直接返回 Pydantic 对象的属性
        return {
            "confidence": confidence_result.confidence,
            "reasoning": confidence_result.reasoning
        }
```

**改进点**:
- ✅ 删除了 30+ 行手动 JSON 解析代码
- ✅ 不再需要 `json.loads()` 和 `re.search()`
- ✅ 类型安全，IDE 自动补全
- ✅ 自动格式验证，减少错误

---

### 2. **ClassificationAgent** ✅

#### 重构前

```python
from typing import TypedDict

class ClassificationState(TypedDict):
    question: str
    options: Optional[List[str]]
    categories: List[Dict]
    category_results: List[Dict]

def _classify_node(self, state):
    # 手动解析 JSON
    try:
        result = json.loads(results_text)
        # ... 复杂的手动处理
    except json.JSONDecodeError:
        # 尝试提取 JSON
        json_match = re.search(r'\[.*?\]', results_text, re.DOTALL)
```

#### 重构后

```python
from pydantic import BaseModel, Field

class ClassificationResult(BaseModel):
    """分类结果模型"""
    category_id: int = Field(description="分类 ID")
    confidence: float = Field(description="置信度，0.0-1.0")
    reason: str = Field(description="分类理由")

class ClassificationState(BaseModel):
    """分类状态模型"""
    question: str
    options: Optional[List[str]] = None
    categories: List[Dict] = []
    category_results: List[ClassificationResult] = []

class ClassificationAgent:
    def __init__(self):
        self.parser = PydanticOutputParser(pydantic_object=ClassificationResult)
    
    def _classify_node(self, state):
        # 添加格式指令
        format_instructions = self.parser.get_format_instructions()
        full_prompt = f"{prompt}\n请严格按照以下 JSON Schema 格式返回:\n{format_instructions}"
        
        # 自动解析为 Pydantic 对象
        classification_result = self.parser.parse(response.content)
        return {'category_results': [classification_result]}
```

**改进点**:
- ✅ State 和 Result 都使用 Pydantic 模型
- ✅ 自动验证字段类型（int, float, str）
- ✅ 提供字段描述，便于理解
- ✅ 支持默认值和可选字段

---

### 3. **ReviewerAgent** ✅

#### 重构前

```python
from typing import TypedDict

class ReviewState(TypedDict):
    question: str
    answer: str
    options: Optional[List[str]]
    question_type: str
    corrections: Optional[str]
    review_result: Dict  # 使用 Dict，无类型检查

def _parse_result_node(self, state):
    # 手动解析并验证字段
    result = json.loads(result_text)
    for key in ['is_correct', 'confidence', 'explanation']:
        if key not in result:
            logger.warning(f"缺少字段 {key}，使用默认值")
    # ... 繁琐的字段检查
```

#### 重构后

```python
from pydantic import BaseModel, Field

class ReviewResult(BaseModel):
    """复审结果模型"""
    is_correct: bool = Field(description="答案是否正确")
    confidence: float = Field(description="置信度，0.0-1.0")
    corrected_answer: Optional[str] = Field(default=None)
    explanation: str = Field(description="审核说明")
    suggestions: List[str] = Field(default_factory=list)

class ReviewState(BaseModel):
    """复审状态模型"""
    question: str
    answer: str
    options: Optional[List[str]] = None
    question_type: str
    corrections: Optional[str] = None
    review_result: Optional[ReviewResult] = None

class ReviewerAgent:
    def __init__(self):
        self.parser = PydanticOutputParser(pydantic_object=ReviewResult)
    
    def _review_node(self, state):
        # 自动解析，自动验证字段
        review_result = self.parser.parse(response.content)
        return {'review_result': review_result}
```

**改进点**:
- ✅ 明确的字段类型（bool, float, str, List）
- ✅ 自动字段验证，不需要手动检查
- ✅ 支持默认值（default, default_factory）
- ✅ Optional 字段清晰表达可空性

---

### 4. **RAGChatAgent** ✅

#### 重构前

```python
from typing import TypedDict

class RAGChatState(TypedDict):
    query: str
    use_history: bool
    context: Optional[str]
    sources: List[str]
    metadata: List[Dict]
    answer: str
    used_retrieval: bool
```

#### 重构后

```python
from pydantic import BaseModel, Field

class RAGChatState(BaseModel):
    """RAG 对话状态模型"""
    query: str
    use_history: bool = True  # 默认值为 True
    context: Optional[str] = None
    sources: List[str] = []
    metadata: List[Dict] = []
    answer: str = ""
    used_retrieval: bool = False
```

**改进点**:
- ✅ 支持字段默认值
- ✅ 更清晰的类型定义
- ✅ 可直接序列化为 JSON

---

## 🔧 使用的 LangChain 组件

### PydanticOutputParser

**作用**: 将 LLM 的输出自动解析为 Pydantic 对象

**使用方法**:
```python
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

# 1. 定义数据模型
class MyResult(BaseModel):
    field1: str = Field(description="字段 1 的描述")
    field2: int = Field(description="字段 2 的描述")

# 2. 初始化解析器
parser = PydanticOutputParser(pydantic_object=MyResult)

# 3. 获取格式指令
format_instructions = parser.get_format_instructions()
# 返回："The output should be a JSON object that matches the following schema: ..."

# 4. 在提示词中添加格式指令
full_prompt = f"{your_prompt}\n\n请严格按照以下格式返回:\n{format_instructions}"

# 5. 调用 LLM 并解析
response = llm.invoke(messages)
result = parser.parse(response.content)
# result 是 MyResult 类型的 Pydantic 对象

# 6. 访问属性
print(result.field1)
print(result.field2)
```

**优势**:
- ✅ 自动格式验证
- ✅ 类型安全
- ✅ 错误提示清晰
- ✅ 减少手动解析代码

---

## 📊 代码对比

### 代码量对比

| 文件 | 重构前 | 重构后 | 减少 |
|------|--------|--------|------|
| **query.py** | 197 行 | 160 行 | -19% |
| **classification.py** | 183 行 | 150 行 | -18% |
| **reviewer.py** | 225 行 | 180 行 | -20% |
| **rag_chat.py** | 238 行 | 200 行 | -16% |

### 复杂度对比

| 指标 | 重构前 | 重构后 | 改进 |
|------|--------|--------|------|
| **JSON 解析方式** | 手动 json.loads + 正则 | Pydantic 自动解析 | ⭐⭐⭐⭐⭐ |
| **类型检查** | 弱（TypedDict） | 强（Pydantic） | ⭐⭐⭐⭐⭐ |
| **错误处理** | 复杂 try-except | 自动验证 | ⭐⭐⭐⭐ |
| **IDE 支持** | 一般 | 完整类型提示 | ⭐⭐⭐⭐⭐ |
| **代码可读性** | 较低 | 高 | ⭐⭐⭐⭐⭐ |

---

## ✨ Pydantic 优势

### 1. 类型安全

```python
class Result(BaseModel):
    confidence: float  # 必须是 float
    reasoning: str     # 必须是 str

# 类型错误会自动转换或报错
result = Result(confidence="0.9", reasoning=123)
# Pydantic 会尝试转换：confidence=0.9, reasoning="123"
# 如果无法转换，会抛出清晰的错误
```

### 2. 自动验证

```python
class Result(BaseModel):
    confidence: float = Field(ge=0.0, le=1.0)  # 范围验证
    reasoning: str = Field(min_length=1)       # 长度验证

# 验证失败会抛出清晰的错误
Result(confidence=1.5, reasoning="")  
# ValidationError: 2 validation errors
```

### 3. 默认值支持

```python
class Result(BaseModel):
    confidence: float = 0.8              # 默认值
    suggestions: List[str] = []          # 默认列表
    metadata: Dict = {}                  # 默认字典
    optional_field: Optional[str] = None # 可空字段
```

### 4. 序列化支持

```python
# 转为字典
result_dict = result.dict()
# {'confidence': 0.9, 'reasoning': '...', ...}

# 转为 JSON 字符串
result_json = result.json()
# '{"confidence": 0.9, "reasoning": "..."}'

# 从字典创建
new_result = Result(**result_dict)
```

### 5. IDE 友好

```python
result = Result(confidence=0.9, reasoning="test")

# IDE 会自动提示:
# - result.confidence (float)
# - result.reasoning (str)
# - result.dict()
# - result.json()
# 等等所有方法和属性
```

---

## 🧪 测试结果

运行测试脚本：
```bash
python src/test/test_pydantic_agents.py
```

**测试结果**：✅ **所有测试通过！**

测试覆盖：
- ✓ Pydantic 数据模型定义
- ✓ QueryAgent 解析器功能
- ✓ ClassificationAgent 解析器功能
- ✓ ReviewerAgent 解析器功能
- ✓ 不再使用手动 JSON 解析
- ✓ 代码简化程度验证

---

## 📝 迁移指南

### 从 TypedDict 迁移到 BaseModel

**之前**:
```python
from typing import TypedDict, Optional, List

class MyState(TypedDict):
    name: str
    age: int
    tags: List[str]
    optional: Optional[str]
```

**现在**:
```python
from pydantic import BaseModel, Field
from typing import Optional, List

class MyState(BaseModel):
    name: str
    age: int
    tags: List[str] = []
    optional: Optional[str] = None
```

### 从手动解析迁移到自动解析

**之前**:
```python
import json
import re

def parse_result(content):
    try:
        result = json.loads(content)
        return result
    except json.JSONDecodeError:
        json_match = re.search(r'\{.*?\}', content, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        return None
```

**现在**:
```python
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

class MyResult(BaseModel):
    field1: str
    field2: int

parser = PydanticOutputParser(pydantic_object=MyResult)

def parse_result(content):
    return parser.parse(content)
    # 自动处理各种格式问题
    # 返回 MyResult 类型的对象
```

---

## 🔮 未来扩展

### 1. 添加字段验证

```python
class ConfidenceResult(BaseModel):
    confidence: float = Field(
        ge=0.0,      # >= 0.0
        le=1.0,      # <= 1.0
        description="置信度必须在 0-1 之间"
    )
    reasoning: str = Field(
        min_length=1,
        max_length=500,
        description="理由长度限制"
    )
```

### 2. 自定义验证器

```python
from pydantic import validator

class ReviewResult(BaseModel):
    confidence: float
    is_correct: bool
    
    @validator('confidence')
    def validate_confidence(cls, v):
        if v < 0.0 or v > 1.0:
            raise ValueError("置信度必须在 0-1 之间")
        return v
```

### 3. 嵌套模型

```python
class Metadata(BaseModel):
    source: str
    timestamp: datetime

class RAGResult(BaseModel):
    answer: str
    metadata: Metadata  # 嵌套模型
    confidence: float
```

---

## 📚 参考资源

1. [Pydantic 官方文档](https://docs.pydantic.dev/)
2. [LangChain Output Parsers](https://python.langchain.com/docs/modules/model_io/output_parsers/)
3. [PydanticOutputParser API](https://api.python.langchain.com/en/latest/output_parsers/langchain_core.output_parsers.pydantic.PydanticOutputParser.html)

---

## 📝 版本历史

- **v3.2.0** (2026-03-07): 
  - ✨ 所有 TypedDict 改为 Pydantic BaseModel
  - ✨ 使用LangChain PydanticOutputParser 自动解析
  - ❌ 删除手动 JSON 解析和正则表达式
  - ✅ 增强类型安全和 IDE 支持
  - 📉 减少约 20% 的代码量
  
- **v3.1.0**: 优化提示词模板，简化QueryAgent
- **v3.0.0**: 使用LangChain/LangGraph 重构所有 Agents
- **v1.0.0**: 初始版本
