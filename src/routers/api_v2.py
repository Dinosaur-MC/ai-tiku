"""
API v2 版本路由定义
使用新的服务层架构，Agent 不直接访问数据库
"""

from fastapi import APIRouter, Depends, HTTPException, status, Body
from typing import List, Optional
import logging

from dependencies import verify_api_token
from schemas.v2 import (
    CategoryCreate,
    CategoryAssign,
    CategoryData,
    CategoryListResponse,
    CategoryAssignResponse,
    CategoryAIResponse,
    CategoryResult,
)
from services.classification_service import classification_service
from services.ai_service import ai_service
from agents.classification import classifier
from utils.dbc import db

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v2",
    tags=["API v2"],
)


@router.get(
    "/categories",
    response_model=CategoryListResponse,
    summary="获取所有分类列表",
)
async def get_all_categories(token_info=Depends(verify_api_token)):
    """
    获取所有可用分类列表
    
    返回系统中所有已创建的分类信息
    """
    try:
        categories = classification_service.get_all_categories()
        
        # 转换为响应模型
        category_data = [
            CategoryData(
                id=cat["id"],
                name=cat["name"],
                description=cat["description"],
            )
            for cat in categories
        ]
        
        return CategoryListResponse(
            code=1,
            message="请求成功",
            data=category_data,
        )
    except Exception as e:
        logger.error(f"获取分类列表失败：{str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取分类列表失败：{str(e)}",
        )


@router.post(
    "/categories",
    response_model=CategoryData,
    summary="创建新分类",
)
async def create_category(
    category: CategoryCreate,
    token_info=Depends(verify_api_token),
):
    """
    创建新的题目分类
    
    **请求参数**：
    - `name`: 分类名称（必填，必须唯一）
    - `description`: 分类描述（可选）
    """
    try:
        created_category = classification_service.create_category(
            name=category.name,
            description=category.description,
        )
        
        return CategoryData(
            id=created_category.id,
            name=created_category.name,
            description=created_category.description,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"创建分类失败：{str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建分类失败：{str(e)}",
        )


@router.delete(
    "/categories/{category_id}",
    summary="删除分类",
)
async def delete_category(
    category_id: int,
    token_info=Depends(verify_api_token),
):
    """
    删除指定分类
    
    **路径参数**：
    - `category_id`: 分类 ID
    
    注意：删除分类会同时删除该分类与所有题目的关联关系
    """
    try:
        success = classification_service.delete_category(category_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"分类 {category_id} 不存在",
            )
        
        return {"code": 1, "message": "删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除分类失败：{str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"删除分类失败：{str(e)}",
        )


@router.post(
    "/questions/{question_id}/categories",
    response_model=CategoryAssignResponse,
    summary="分配题目到多个分类",
)
async def assign_question_to_categories(
    question_id: int,
    category_assign: CategoryAssign,
    token_info=Depends(verify_api_token),
):
    """
    将题目分配到多个分类
    
    **路径参数**：
    - `question_id`: 题目 ID
    
    **请求参数**：
    - `category_ids`: 分类 ID 列表
    """
    try:
        relations = classification_service.assign_to_question(
            question_id=question_id,
            category_ids=category_assign.category_ids,
        )
        
        # 获取分类详情
        categories = []
        for relation in relations:
            category = classification_service.get_category_by_id(relation.category_id)
            if category:
                categories.append(
                    CategoryData(
                        id=category.id,
                        name=category.name,
                        description=category.description,
                    )
                )
        
        return CategoryAssignResponse(
            code=1,
            message="分配成功",
            data=categories,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"分配分类失败：{str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"分配分类失败：{str(e)}",
        )


@router.get(
    "/questions/{question_id}/categories",
    response_model=CategoryListResponse,
    summary="获取题目的所有分类",
)
async def get_question_categories(
    question_id: int,
    token_info=Depends(verify_api_token),
):
    """
    获取题目所属的所有分类
    
    **路径参数**：
    - `question_id`: 题目 ID
    """
    try:
        categories = classification_service.get_categories_for_question(question_id)
        
        category_data = [
            CategoryData(
                id=cat["id"],
                name=cat["name"],
                description=cat["description"],
            )
            for cat in categories
        ]
        
        return CategoryListResponse(
            code=1,
            message="获取成功",
            data=category_data,
        )
    except Exception as e:
        logger.error(f"获取题目分类失败：{str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取题目分类失败：{str(e)}",
        )


@router.post(
    "/questions/{question_id}/categories/remove",
    summary="从题目移除分类",
)
async def remove_category_from_question(
    question_id: int,
    category_id: int,
    token_info=Depends(verify_api_token),
):
    """
    从题目移除指定的分类关联
    
    **路径参数**：
    - `question_id`: 题目 ID
    - `category_id`: 分类 ID
    """
    try:
        success = classification_service.remove_from_question(
            question_id=question_id,
            category_id=category_id,
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="分类关联不存在",
            )
        
        return {"code": 1, "message": "移除成功"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"移除分类失败：{str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"移除分类失败：{str(e)}",
        )


@router.post(
    "/classify/ai",
    response_model=CategoryAIResponse,
    summary="AI 自动分类",
)
async def ai_classify_question(
    question: str = Body(..., description="题目内容"),
    options: Optional[str] = Body(None, description="选项内容，多个用换行符分隔"),
    token_info=Depends(verify_api_token),
):
    """
    使用 AI 自动将题目分类到合适的类别
    
    **请求参数**：
    - `question`: 题目内容（必填）
    - `options`: 选项内容（可选）
    
    此接口调用 LLM 分析题目内容，自动推荐最合适的分类
    """
    try:
        # 解析选项
        options_list = None
        if options:
            options_list = [opt.strip() for opt in options.split("\n") if opt.strip()]
        
        # 从 service 获取分类列表
        categories = classification_service.get_all_categories()
        
        if not categories:
            return CategoryAIResponse(
                code=0,
                message="没有可用分类，请先创建分类",
                data=[],
            )
        
        # 设置分类列表到 Agent（关键：通过参数传入，而非 Agent 自己查询）
        classifier.set_categories(categories)
        
        # 调用 AI 进行分类
        ai_results = classifier.classify(question, options_list)
        
        # 转换为响应模型
        category_results = [
            CategoryResult(
                category_id=result.category_id,
                confidence=result.confidence,
                reason=result.reason,
            )
            for result in ai_results
        ]
        
        return CategoryAIResponse(
            code=1,
            message="分类成功",
            data=category_results,
        )
    except Exception as e:
        logger.error(f"AI 分类失败：{str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"AI 分类失败：{str(e)}",
        )
