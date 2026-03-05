from dotenv import load_dotenv
from fastapi.responses import FileResponse

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

app = FastAPI(
    title="AI-Tiku API",
    description="AI 题库答题服务系统，提供查题及题库信息查询功能",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 导入并注册 API 路由
from api import include_router as include_api_router

include_api_router(app)

# 导入并注册 UI 路由
from ui import include_router as include_ui_router

include_ui_router(app)


# 健康检查端点
@app.get("/health", tags=["Health"])
async def health_check():
    """健康检查"""
    return {"status": "healthy"}


@app.get("/", tags=["Root"])
async def root():
    """根路径"""
    return {"message": "Welcome to AI-Tiku API", "docs": "/docs", "health": "/health"}


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    """图标"""
    return FileResponse("favicon.ico")


def main():
    print("Hello from ai-tiku!")
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
