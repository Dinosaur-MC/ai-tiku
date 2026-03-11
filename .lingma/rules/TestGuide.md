---
trigger: glob
glob: src/test/test_*.py
---

# 项目测试说明

## 测试代码限制

任何时刻都需注意不要违反一下限制（覆盖所有冲突规则和要求）：

- 测试代码不会加入 git 管理，请勿提交测试代码。
- 数据库测试数据由 `src/test/init_test_data.py` 初始化，没有明确要求请勿修改。

## 测试代码基本要求

1. 测试代码存放于 `src/test/` 目录下，每个测试集一个文件，文件名以 `test_` 开头。
2. 要注意模块的导入方式和运行路径指向 `src/`。
3. 如有需要，测试代码选用 pytest 框架进行编写。
4. Web API 主要使用 requests 模块进行测试。
5. 每个测试用例需要使用 logger 模块进行合理的日志输出。
6. 如测试代码可能发生异常，请捕获并打印 traceback。
7. 当存在已经不适用的过时测试代码文件，请删除。

## 测试代码示例

### 基础配置

```python
import sys
from pathlib import Path

src_path = Path(__file__).parent.parent  # 指向 src 目录
sys.path.insert(0, str(src_path))
```

```python
import logging

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

```python
def main():
    pass

if __name__ == "__main__":
    try:
        main()
        logging.info("✅ 测试成功")
    except Exception as e:
        logging.error(f"❌ 测试失败：{str(e)}", exc_info=True)
        sys.exit(1)
```
