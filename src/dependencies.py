"""
公共依赖注入模块
提供跨版本共享的依赖项（如 token 验证）
"""

from fastapi import Depends, HTTPException, status
from db import db
import logging

logger = logging.getLogger(__name__)


def verify_token(token: str) -> dict:
    """
    验证 API Token

    Args:
        token: 用户凭证

    Returns:
        token_info: Token 信息对象

    Raises:
        HTTPException: 当 token 无效或配额用完时
    """
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


# 可重用的依赖项装饰器
TokenDep = Depends(verify_token)
