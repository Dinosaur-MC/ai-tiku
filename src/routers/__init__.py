"""
路由器模块
包含所有 API 版本的路由定义
"""

from routers.api_v1 import router as api_v1_router
from routers.api_v2 import router as api_v2_router

__all__ = [
    "api_v1_router",
    "api_v2_router",
]
