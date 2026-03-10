from dotenv import load_dotenv

load_dotenv()

from pathlib import Path
from starlette.exceptions import HTTPException
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import logging

from schemas.common import BaseResponse, ErrorResponse


# 配置日志
logging.basicConfig(
    level=logging.DEBUG, format="[%(asctime)s] %(name)s - %(levelname)s: %(message)s"
)
logger = logging.getLogger(__name__)

# ========== 创建主应用实例 ==========
app = FastAPI(
    title="AI-Tiku API",
    description="AI 题库答题服务系统，提供查题及题库信息查询功能",
    version="2.0.0",  # 更新版本号
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
    debug=True,
)


# ========== 全局异常处理器 ==========
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP 异常处理器 - 将 HTTPException 转换为统一的 ErrorResponse 格式"""

    logger.error(f"HTTP 异常：{str(exc)}", exc_info=True)
    import traceback

    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            code=exc.status_code,
            message=exc.detail,
            detail=traceback.format_exc() if app.debug else None,
        ).model_dump(exclude_none=True),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """通用异常处理器 - 捕获所有未处理的异常"""

    logger.error(f"未处理的异常：{str(exc)}", exc_info=True)

    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            code=500,
            message="Internal Server Error",
            detail=str(exc) if app.debug else None,
        ).model_dump(exclude_none=True),
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== 导入并注册各版本 API 路由 ==========
from routers.api_v1 import router as api_v1_router
from routers.api_v2 import router as api_v2_router

# 注册 v1 版本（保持向后兼容）
app.include_router(api_v1_router)

# 注册 v2 版本（新版本）
app.include_router(api_v2_router)


# ========== 健康检查端点 ==========
@app.get("/health", tags=["Health"])
async def health_check():
    """健康检查"""
    return BaseResponse(code=0, message="健康检查通过", data={"status": "healthy"})


# ========== 根路径和页面 ==========
@app.get("/", tags=["Root"])
async def root():
    """根路径 - 返回 UI 页面"""
    return FileResponse(Path(__file__).parent / "index.html")


@app.head("/", tags=["Root"])
async def root_head():
    """根路径 HEAD 请求 - 返回响应头"""
    return Response()


# favicon 处理
@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """图标"""
    favicon_path = Path(__file__).parent / "favicon.ico"
    if favicon_path.exists():
        return FileResponse(favicon_path)
    else:
        return Response(status_code=404)


# ========== API 文档入口 ==========
@app.get("/docs", tags=["Documentation"], summary="API 文档导航")
async def documentation_navigation():
    """
    API 文档导航页面

    提供所有版本文档的访问入口
    """
    docs_path = Path(__file__).parent / "web" / "docs_index.html"
    return FileResponse(docs_path)


def main():
    print("Hello from ai-tiku!")
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
