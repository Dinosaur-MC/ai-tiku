from fastapi import (
    APIRouter,
    FastAPI,
    status,
    HTTPException,
    Depends,
    Query,
)
from pydantic import BaseModel, Field
from typing import Optional, List, Union, Dict
from db import db
from services.vector_search import vector_search
from services.ai_service import ai_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter()


# 请求/响应模型
class QueryRequest(BaseModel):
    """查询请求模型"""

    title: Optional[str] = Field(None, description="题目内容（与 q、question 三选一）")
    q: Optional[str] = Field(None, description="题目内容（与 title、question 三选一）")
    question: Optional[str] = Field(None, description="题目内容（与 title、q 三选一）")
    options: Optional[str] = Field(None, description="选项内容，多个用换行符分隔")
    type: Optional[str] = Field("unknown", description="题目类型")
    more: Optional[bool] = Field(False, description="是否返回多个结果（已禁用）")

    def get_question_text(self) -> str:
        """获取题目文本（优先级：title > q > question）"""
        return self.title or self.q or self.question or ""

    def get_options_list(self) -> Optional[List[str]]:
        """解析选项列表"""
        if not self.options:
            return None
        return [opt.strip() for opt in self.options.split("\n") if opt.strip()]


class SingleResultData(BaseModel):
    """单条结果数据模型"""

    question: str
    answer: str
    times: int
    ai: bool = False


class MultiResultItem(BaseModel):
    """多条结果中的单项"""

    question: str
    answer: str
    ai: bool = False


class MultiResultData(BaseModel):
    """多条结果数据模型"""

    results: List[MultiResultItem]
    times: int


class QueryResponse(BaseModel):
    """查询响应模型"""

    code: int = Field(1, description="1 表示有答案，0 表示无答案")
    message: str = "请求成功"
    data: Union[SingleResultData, MultiResultData]


class InfoResponse(BaseModel):
    """信息响应模型"""

    code: int = Field(1, description="1 表示成功，0 表示失败")
    message: str = "请求成功"
    data: Dict[str, int]


def verify_token(token: str = Query(..., description="用户凭证")):
    """验证 token"""
    token_info = db.get_token_by_value(token)
    if not token_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 token，请在题库个人中心获取有效 token",
        )
    if token_info.remaining_queries <= 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token 配额已用完，请充值或联系管理员",
        )
    return token_info


@router.get("/query", response_model=QueryResponse, summary="查题接口")
async def query_question(
    token_info: dict = Depends(verify_token),
    title: Optional[str] = Query(None, description="题目内容"),
    q: Optional[str] = Query(None, description="题目内容"),
    question: Optional[str] = Query(None, description="题目内容"),
    options: Optional[str] = Query(None, description="选项内容"),
    type: Optional[str] = Query("unknown", description="题目类型"),
    more: Optional[bool] = Query(False, description="是否返回多个结果（已禁用）"),
    force_ai: Optional[bool] = Query(False, description="强制使用 AI 模型回答"),
):
    """
    查题接口 - 根据题目内容搜索答案

    **参数说明**：
    - `title`、`q`、`question` 三个字段至少提供一个，最终只会采用其中一个（优先级：`title` > `q` > `question`）
    - `more` 参数已禁用，保留仅用于兼容旧版本
    """
    # 构建查询请求
    query_text = title or q or question

    if not query_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请提供题目内容（title、q 或 question 至少一个）",
        )

    # 解析选项
    options_list = None
    if options:
        options_list = [opt.strip() for opt in options.split("\n") if opt.strip()]

    try:
        # 执行查询
        # 1. 首先尝试向量相似度搜索（除非强制使用 AI）
        result = None

        if not force_ai:
            similar_results = vector_search.search_similar(query_text, k=5)

            if similar_results:
                best_match = similar_results[0]
                result = {
                    "found": True,
                    "question": best_match["content"],
                    "answer": best_match.get("metadata", {}).get("answer", ""),
                    "ai": False,
                    "similar_results": similar_results,
                }

        # 2. 未找到相似题目或强制使用 AI，使用 LLM 生成答案
        if result is None:
            ai_answer = ai_service.generate_answer(
                query_text, options_list, type or "unknown"
            )
            result = {
                "found": True,
                "question": query_text,
                "answer": ai_answer,
                "ai": True,
                "similar_results": [],
            }

        # 更新 token 使用统计
        found = result.get("found", False)
        db.update_token_usage(token_info.id, success=found)

        # 记录查询日志
        db.log_query(token_id=token_info.id, query_text=query_text, found=found)

        # 获取更新后的 token 信息
        updated_token = db.get_token_info(token_info.id)
        remaining = updated_token.remaining_queries if updated_token else 0

        # 构建响应
        if not more:
            # 单条结果模式
            if found and result.get("answer"):
                response_data = SingleResultData(
                    question=result.get("question", query_text),
                    answer=result.get("answer", ""),
                    times=remaining,
                    ai=result.get("ai", False),
                )
                return QueryResponse(code=1, message="请求成功", data=response_data)
            else:
                # 未找到答案
                response_data = SingleResultData(
                    question="未找到答案！",
                    answer="很抱歉，题目搜索不到。",
                    times=remaining,
                    ai=False,
                )
                return QueryResponse(code=0, message="请求失败", data=response_data)
        else:
            # 多条结果模式（保留兼容）
            results = result.get("results", [])
            items = [
                MultiResultItem(
                    question=item.get("question", ""),
                    answer=item.get("answer", ""),
                    ai=item.get("ai", False),
                )
                for item in results
            ]
            response_data = MultiResultData(results=items, times=remaining)
            return QueryResponse(
                code=1 if results else 0,
                message="请求成功" if results else "请求失败",
                data=response_data,
            )

    except Exception as e:
        logger.error(f"查询失败：{str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"查询处理失败：{str(e)}",
        )


@router.get("/info", response_model=InfoResponse, summary="题库信息获取接口")
async def get_info(token_info: dict = Depends(verify_token)):
    """
    获取当前 token 的剩余调用次数、总使用次数及成功次数
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


# 注册路由到主应用
def include_router(app: FastAPI):
    """将路由注册到 FastAPI 应用"""
    app.include_router(router, prefix="/api")
