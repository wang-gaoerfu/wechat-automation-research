"""FastAPI 入口"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import get_config
from app.api.v1.router import api_router

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("企业微信自动化服务启动")
    config = get_config()
    logger.info(f"Corp ID: {config.wechat.corp_id}")
    yield
    logger.info("企业微信自动化服务关闭")


app = FastAPI(
    title="企业微信自动化服务",
    description="基于 FastAPI 的企业微信自动化服务",
    version="1.0.0",
    lifespan=lifespan
)

# 注册路由
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "ok", "service": "enterprise-wechat"}