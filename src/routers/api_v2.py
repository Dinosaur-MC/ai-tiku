"""
API v2 版本路由定义
"""

from fastapi import APIRouter
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v2",
    tags=["API v2"],
)
