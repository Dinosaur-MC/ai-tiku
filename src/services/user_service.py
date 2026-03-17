"""
用户认证服务

创建用户，认证用户，创建API密钥
"""

from typing import Optional
from datetime import timedelta

from fastapi import HTTPException, status
from passlib.context import CryptContext

from models import User, UserRole, ApiKey
from utils.dbc import db
from utils.access_token import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
)

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


class UserService:
    def register_user(
        self, username: str, password: str, email: Optional[str] = None
    ) -> User:
        # 检查用户名是否已存在
        existing_user = db.read_one_by_condition(User, User.username == username)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="用户名已存在"
            )

        # 创建新用户
        hashed_password = pwd_context.hash(password)
        user = User(
            username=username, password=hashed_password, email=email, role=UserRole.USER
        )
        db.create(user)
        return user

    def authenticate_user(self, username: str, password: str):
        user = db.read_one_by_condition(User, User.username == username)
        if not user or not pwd_context.verify(password, user.password):
            return None
        return user

    def login_for_access_token(self, username: str, password: str):
        user = self.authenticate_user(username, password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户名或密码错误",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 创建JWT
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": user.username,
                "role": user.role.value,
                "status": user.status.value,
            },
            expires_delta=access_token_expires,
        )

        return {
            "token_type": "bearer",
            "access_token": access_token,
        }

    def create_api_key(self, user_id: int, capacity: int) -> ApiKey:
        db_api_key = ApiKey(owner_id=user_id, remaining_queries=capacity)
        db.create(db_api_key)
        return db_api_key


user_service = UserService()
