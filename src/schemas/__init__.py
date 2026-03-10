"""
Schema 模块
包含所有 API 版本的数据模型定义
"""

# 公共模型
from .common import BaseResponse, ErrorResponse

__all__ = [
    "BaseResponse",
    "ErrorResponse",
]
