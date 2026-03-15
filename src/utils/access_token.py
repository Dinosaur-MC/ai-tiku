"""
Token 生成与验证工具
提供安全的 Token 生成、验证和管理功能
"""

import secrets
import base64


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
