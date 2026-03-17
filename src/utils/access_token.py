"""
Token 生成与验证工具
提供安全的 Token 生成、验证和管理功能
"""

import secrets
import base64
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

import jwt
from fastapi import HTTPException, status
import os


def generate_token(length: int = 32) -> str:
    """
    生成随机安全的 Token

    Args:
        length: Token 长度（字节数），默认 32 字节

    Returns:
        URL 安全的 Base64 编码 Token 字符串
    """
    # 使用 secrets 模块生成加密安全的随机字节
    random_bytes = secrets.token_bytes(length)
    # Base64 编码并转换为 URL 安全格式
    token = base64.urlsafe_b64encode(random_bytes).decode("utf-8")
    # 移除填充字符
    return token.rstrip("=")


def generate_api_key(prefix: str = "ak") -> str:
    """
    生成带前缀的 API Key

    Args:
        prefix: 前缀标识，默认 "ak" (API Key)

    Returns:
        格式化的 API Key（如：ak_xxxxxxxxxxxxx）
    """
    token = generate_token(24)
    return f"{prefix}_{token}"


def generate_secret_key(prefix: str = "sk") -> str:
    """
    生成带前缀的密钥（Secret Key）

    Args:
        prefix: 前缀标识，默认 "sk" (Secret Key)

    Returns:
        格式化的 Secret Key
    """
    token = generate_token(32)
    return f"{prefix}_{token}"


# JWT 配置
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 360


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
):
    """
    创建 JWT 访问令牌

    Args:
        data: 要编码到令牌中的数据，通常包含用户标识
        expires_delta: 令牌过期时间间隔，如果未提供则使用默认值

    Returns:
        编码后的 JWT 令牌字符串
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_access_token(token: str) -> Dict[str, Any]:
    """
    验证 JWT 访问令牌

    Args:
        token: 要验证的 JWT 令牌字符串

    Returns:
        解码后的令牌数据

    Raises:
        HTTPException: 当令牌无效或已过期时
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="令牌已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌",
            headers={"WWW-Authenticate": "Bearer"},
        )


def hash_token(token: str) -> str:
    """
    对 Token 进行哈希处理，用于安全存储

    Args:
        token: 明文 Token

    Returns:
        SHA-256 哈希值（十六进制字符串）
    """
    import hashlib

    return hashlib.sha256(token.encode()).hexdigest()


def verify_token_format(token: str) -> bool:
    """
    验证 Token 格式是否符合预期

    Args:
        token: 要验证的 Token 字符串

    Returns:
        True 如果格式有效，否则 False
    """
    if not token or not isinstance(token, str):
        return False
    # 简单的格式检查：长度合理且不包含空格
    return len(token) >= 16 and " " not in token
