from dotenv import load_dotenv

load_dotenv()

from pathlib import Path
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import logging


# 配置日志
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

app = FastAPI(
    title="AI-Tiku API",
    description="AI 题库答题服务系统，提供查题及题库信息查询功能",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI 文档路径
    redoc_url="/redoc",  # ReDoc 文档路径
    openapi_url="/openapi.json",  # OpenAPI schema 路径
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 导入并注册 API 路由（先注册 API 路由）
from api import include_router as include_api_router

include_api_router(app)


# 健康检查端点
@app.get("/health", tags=["Health"])
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


# 根路径重定向到 UI 页面
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
    # 如果存在 favicon.ico 则返回，否则返回 404
    favicon_path = Path(__file__).parent / "favicon.ico"
    if favicon_path.exists():
        return FileResponse(favicon_path)
    else:
        from fastapi.responses import Response

        return Response(status_code=404)


def main():
    print("Hello from ai-tiku!")
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
