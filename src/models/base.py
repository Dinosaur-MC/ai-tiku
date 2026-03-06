"""
数据库模型基类
"""
from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional


class BaseModel(SQLModel):
    """基础模型，包含通用字段"""
    pass
