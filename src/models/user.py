"""
User 模型
"""

from typing import Optional
from datetime import datetime, timezone
from sqlmodel import Field, Column
from sqlalchemy import Enum
import enum
from . import BaseModel


class UserRole(str, enum.Enum):
    """用户角色枚举"""

    ADMIN = "admin"
    USER = "user"


class UserStatus(str, enum.Enum):
    """用户状态枚举"""

    ACTIVE = "active"
    DISABLED = "disabled"


class User(BaseModel, table=True):
    """用户表"""

    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True)
    password: str = Field()
    email: Optional[str] = Field(default=None, unique=True, index=True)
    role: UserRole = Field(default=UserRole.USER, sa_column=Column(Enum(UserRole)))
    status: UserStatus = Field(
        default=UserStatus.ACTIVE, sa_column=Column(Enum(UserStatus))
    )
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
