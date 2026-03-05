from fastapi import FastAPI, APIRouter, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
from pathlib import Path

router = APIRouter()

# 获取当前文件所在目录
CURRENT_DIR = Path(__file__).parent


@router.get("/", response_class=HTMLResponse)
async def ui_page():
    """主页面 - 返回 index.html"""
    return FileResponse(CURRENT_DIR / "index.html")


def include_router(app: FastAPI):
    """将 UI 路由注册到 FastAPI 应用"""
    app.include_router(router)
