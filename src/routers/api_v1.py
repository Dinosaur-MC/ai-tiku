"""
API v1 版本路由定义
保持与现有 API 完全兼容
"""

import asyncio
import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse

from dependencies import verify_api_token
from schemas.v1 import (
    QueryRequest,
    QueryResponse,
    SingleResultData,
    MultiResultData,
    MultiResultItem,
    InfoResponse,
)
from services.question_service import question_service
from services.ai_service import ai_service
from models import ApiKey

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1",
    tags=["API v1"],
)


def _execute_query_sync(
    token_info: ApiKey,
    query_text: str,
    options_list,
    question_type: str,
    subject: str,
    more: bool,
    force_ai: bool,
) -> QueryResponse:
    result = None

    if not force_ai:
        similar_results = question_service.search_similar_questions(
            query=query_text,
            k=5,
            score_threshold=0.7,
        )

        if similar_results:
            best_match = similar_results[0]
            result = {
                "found": True,
                "question": best_match.get("text", ""),
                "answer": best_match.get("answer_text", ""),
                "ai": False,
                "similar_results": similar_results,
            }

    if result is None:
        ai_answer = ai_service.generate_answer(
            query_text,
            options_list,
            question_type or "unknown",
            subject,
        )
        result = {
            "found": True,
            "question": query_text,
            "answer": ai_answer,
            "ai": True,
            "similar_results": [],
        }

    if not more:
        if result.get("found") and result.get("answer"):
            response_data = SingleResultData(
                question=result.get("question", query_text),
                answer=result.get("answer", ""),
                times=token_info.remaining_queries,
                ai=result.get("ai", False),
            )
            return QueryResponse(code=1, message="请求成功", data=response_data)

        response_data = SingleResultData(
            question="未找到答案！",
            answer="很抱歉，题目搜索不到。",
            times=token_info.remaining_queries,
            ai=False,
        )
        return QueryResponse(code=0, message="请求失败", data=response_data)

    results: list[dict] = result.get("similar_results", [])
    items = [
        MultiResultItem(
            question=item.get("text", ""),
            answer=item.get("answer_text", ""),
            ai=False,
        )
        for item in results
    ]
    response_data = MultiResultData(results=items, times=token_info.remaining_queries)
    return QueryResponse(
        code=1 if results else 0,
        message="请求成功" if results else "请求失败",
        data=response_data,
    )


async def _execute_query(
    token_info: ApiKey,
    query_text: str,
    options_list,
    question_type: str,
    subject: str,
    more: bool,
    force_ai: bool,
) -> QueryResponse:
    return await asyncio.to_thread(
        _execute_query_sync,
        token_info,
        query_text,
        options_list,
        question_type,
        subject,
        more,
        force_ai,
    )


async def _stream_query_response(
    token_info: ApiKey,
    query_text: str,
    options_list,
    question_type: str,
    subject: str,
    more: bool,
    force_ai: bool,
):
    task = asyncio.create_task(
        _execute_query(
            token_info,
            query_text,
            options_list,
            question_type,
            subject,
            more,
            force_ai,
        )
    )

    try:
        while True:
            done, _ = await asyncio.wait({task}, timeout=15)
            if task in done:
                response = task.result()
                payload = response.model_dump()
                yield f"event: result\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                return

            yield "event: heartbeat\ndata: {}\n\n"
    except Exception as exc:
        logger.error(f"流式查询失败：{str(exc)}", exc_info=True)
        error_payload = {
            "code": 500,
            "message": f"查询处理失败：{str(exc)}",
            "data": None,
        }
        yield f"event: result\ndata: {json.dumps(error_payload, ensure_ascii=False)}\n\n"


@router.get("/query", response_model=QueryResponse, summary="查题接口 (v1)")
async def query_question(
    token_info: ApiKey = Depends(verify_api_token),
    title: Optional[str] = Query(None, description="题目内容"),
    q: Optional[str] = Query(None, description="题目内容"),
    question: Optional[str] = Query(None, description="题目内容"),
    options: Optional[str] = Query(None, description="选项内容"),
    type: Optional[str] = Query("unknown", description="题目类型"),
    subject: Optional[str] = Query(None, description="科目/课程名称"),
    more: Optional[bool] = Query(False, description="是否返回多个结果（已禁用）"),
    force_ai: Optional[bool] = Query(False, description="强制使用 AI 模型回答"),
    stream: bool = Query(False, description="是否启用 SSE 心跳流式响应"),
):
    """
    查题接口 - 根据题目内容搜索答案 - v1 版本

    **参数说明**：
    - `title`、`q`、`question` 三个字段至少提供一个，最终只会采用其中一个（优先级：`title` > `q` > `question`）
    - `more` 参数已禁用，保留仅用于兼容旧版本
    - `stream=true` 时使用 SSE 流式返回结果
    """
    request = QueryRequest(
        title=title,
        q=q,
        question=question,
        options=options,
        type=type,
        subject=subject,
        more=more,
        stream=stream,
    )
    query_text = request.get_question_text()

    if not query_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请提供题目内容（title、q 或 question 至少一个）",
        )

    options_list = request.get_options_list()
    question_type = request.type or "unknown"

    try:
        if request.stream:
            return StreamingResponse(
                _stream_query_response(
                    token_info,
                    query_text,
                    options_list,
                    question_type,
                    request.subject,
                    bool(request.more),
                    bool(force_ai),
                ),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                },
            )

        return await _execute_query(
            token_info,
            query_text,
            options_list,
            question_type,
            request.subject,
            bool(request.more),
            bool(force_ai),
        )
    except Exception as e:
        logger.error(f"查询失败：{str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询处理失败：{str(e)}",
        )


@router.get("/info", response_model=InfoResponse, summary="题库信息获取接口 (v1)")
async def get_info(token_info: ApiKey = Depends(verify_api_token)):
    """
    获取当前 token 的剩余调用次数、总使用次数及成功次数 - v1 版本
    """
    try:
        info_data = {
            "times": token_info.remaining_queries,
            "user_times": token_info.total_queries,
            "success_times": token_info.success_queries,
        }
        return InfoResponse(code=1, message="请求成功", data=info_data)
    except Exception as e:
        logger.error(f"获取信息失败：{str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取信息失败：{str(e)}",
        )
