"""
Services 模块 - 提供核心业务服务（基于 LangChain/LangGraph）

包含:
- vector_search: 向量搜索服务，负责常规题目检索
- ai_service: AI服务，统一组织和调用多个 AI Agent（整合了原 AIResponder 功能）
"""

from services.vector_search import VectorSearch, vector_search
from services.ai_service import AIService, ai_service

__all__ = [
    'VectorSearch',
    'vector_search',
    'AIService',
    'ai_service',
]
