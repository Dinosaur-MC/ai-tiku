"""
公共依赖注入模块
提供跨版本共享的依赖项（如 token 验证）
"""

from fastapi import Depends, HTTPException, status
import logging
from models import ApiKey, User, UserStatus
from utils.dbc import db
from utils.access_token import verify_access_token

logger = logging.getLogger(__name__)


def get_db():
    """数据库会话依赖"""
    session = db.get_session()
    try:
        yield session
    finally:
        session.close()


def verify_api_token(token: str) -> ApiKey:
    """
    验证 API Token

    Args:
        token: 用户凭证

    Returns:
        token_info: Token 信息对象

    Raises:
        HTTPException: 当 token 无效或配额用完时
    """
    token_info = db.read_one_by_condition(ApiKey, ApiKey.token == token)

    if not token_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 API token，请在题库个人中心获取有效 API token",
        )

    if token_info.remaining_queries <= 0:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API Token 配额已用完，请充值或联系管理员",
        )

    return token_info


def get_current_user(token: str) -> User:
    """
    根据 JWT 令牌获取当前用户

    Args:
        token: 经过验证的令牌

    Returns:
        当前用户对象

    Raises:
        HTTPException: 当用户不存在时
    """
    payload = verify_access_token(token)
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无法验证凭据",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.read_one_by_condition(User, User.username == username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def get_current_active_user(current_user: User = Depends(get_current_user)):
    """
    获取当前激活用户

    Args:
        current_user: 当前用户

    Returns:
        激活状态的用户

    Raises:
        HTTPException: 当用户未激活时
    """
    if current_user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="用户未激活")
    return current_user


# 可重用的依赖项装饰器
ApiTokenDep = Depends(verify_api_token)
CurrentUserDep = Depends(get_current_user)
CurrentActiveUserDep = Depends(get_current_active_user)
