"""
Services 模块 - 提供核心业务服务（基于 LangChain/LangGraph）

包含:
- vector_search: 向量搜索服务，负责常规题目检索
- ai_service: AI 服务，统一组织和调用多个 AI Agent（整合了原 AIResponder 功能）
- classification_service: 分类管理服务，负责任题分类的 CRUD 和向量库同步
"""

from services.ai_service import AIService, ai_service
from services.user_service import UserService, user_service
from services.question_service import QuestionService, question_service
from services.classification_service import ClassificationService, classification_service

__all__ = [
    "AIService",
    "ai_service",
    "UserService",
    "user_service",
    "QuestionService",
    "question_service",
    "ClassificationService",
    "classification_service",
]
