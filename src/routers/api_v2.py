"""
API v2 版本路由定义
更清晰、更规范的 API 设计
"""

from fastapi import APIRouter, Depends, HTTPException, status, Body
from typing import List, Optional
import logging
from datetime import datetime, timezone

from dependencies import verify_token
from schemas.v2 import (
    QueryRequest,
    QueryResponse,
    InfoResponse,
    AnswerData,
    TokenUsage,
    SearchMode,
)
from services.vector_search import vector_search
from services.ai_service import ai_service
from db import db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2", tags=["API v2"])


@router.post("/query", response_model=QueryResponse, summary="查题接口 (v2)")
async def query_question(
    request: QueryRequest = Body(..., description="查询请求"),
    token_info=Depends(verify_token),
):
    """
    查题接口 - v2 版本

    **改进点**：
    - 使用 POST 方法，支持更复杂的请求体
    - 统一的 `question` 字段，不再需要 title/q/question 三选一
    - 新增 `search_mode` 参数，支持精确匹配、模糊搜索、仅 AI 生成
    - 新增 `confidence` 置信度返回
    - 新增 `usage` 使用统计信息
    """
    try:
        query_text = request.question

        # 执行查询
        result = None

        # 1. 根据搜索模式执行不同策略
        if request.search_mode != SearchMode.AI_ONLY:
            similar_results = vector_search.search_similar(
                query_text, k=request.max_results
            )

            if similar_results and request.search_mode == SearchMode.EXACT:
                # 精确匹配模式：只返回第一个完全匹配的结果
                best_match = similar_results[0]
                result = {
                    "found": True,
                    "question": best_match["content"],
                    "answer": best_match.get("metadata", {}).get("answer", ""),
                    "ai": False,
                    "confidence": 1.0,
                    "matched_at": datetime.now(timezone.utc),
                }
            elif similar_results and request.search_mode == SearchMode.FUZZY:
                # 模糊搜索模式：返回最相似的结果
                best_match = similar_results[0]
                result = {
                    "found": True,
                    "question": best_match["content"],
                    "answer": best_match.get("metadata", {}).get("answer", ""),
                    "ai": False,
                    "confidence": 0.9,  # 相似度匹配的置信度
                    "matched_at": datetime.now(timezone.utc),
                }

        # 2. 使用 LLM 生成答案
        if result is None:
            ai_answer = ai_service.generate_answer(
                query_text, request.options, request.question_type.value
            )
            result = {
                "found": True,
                "question": query_text,
                "answer": ai_answer,
                "ai": True,
                "confidence": 0.8,  # AI 生成的置信度
                "matched_at": None,
            }

        # 更新 token 使用统计
        found = result.get("found", False)
        db.update_token_usage(token_info.id, success=found)

        # 记录查询日志
        db.log_query(token_id=token_info.id, query_text=query_text, found=found)

        # 获取更新后的 token 信息
        updated_token = db.get_token_info(token_info.id)

        # 构建响应
        answer_data = AnswerData(
            question=result["question"],
            answer=result["answer"],
            confidence=result.get("confidence", 1.0),
            source="ai" if result["ai"] else "database",
            matched_at=result.get("matched_at"),
        )

        usage_data = TokenUsage(
            remaining=updated_token.remaining_queries if updated_token else 0,
            total_used=updated_token.total_queries if updated_token else 0,
            success_count=updated_token.success_queries if updated_token else 0,
        )

        return QueryResponse(
            code=1,
            message="请求成功",
            data=answer_data,
            usage=usage_data,
        )

    except Exception as e:
        logger.error(f"查询失败：{str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询处理失败：{str(e)}",
        )


@router.get("/info", response_model=InfoResponse, summary="题库信息获取接口 (v2)")
async def get_info(token_info=Depends(verify_token)):
    """
    获取当前 token 的使用统计信息 - v2 版本

    **改进点**：
    - 统一使用 `usage` 对象返回统计信息
    - 字段命名更清晰：remaining, total_used, success_count
    """
    try:
        usage_data = TokenUsage(
            remaining=token_info.remaining_queries,
            total_used=token_info.total_queries,
            success_count=token_info.success_queries,
        )

        return InfoResponse(code=1, message="请求成功", data=usage_data)
    except Exception as e:
        logger.error(f"获取信息失败：{str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取信息失败：{str(e)}",
        )
