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

    # 初始化 LLM 服务
    if config.llm.api_key:
        from app.services.llm_service import llm_service
        llm_config = {
            "provider": config.llm.provider,
            "api_key": config.llm.api_key,
            "base_url": config.llm.base_url,
            "model": config.llm.model,
        }
        llm_service.initialize(llm_config)
        logger.info(f"LLM 服务已初始化: {config.llm.provider}")
    else:
        logger.warning("LLM API Key 未配置，LLM 功能不可用")

    # 初始化 RAG 服务
    if config.rag.enabled and config.rag.embedding_api_key:
        from app.services.rag_service import rag_service
        rag_config = {
            "embedding_provider": config.rag.embedding_provider,
            "embedding_api_key": config.rag.embedding_api_key,
            "embedding_base_url": config.rag.embedding_base_url,
            "collection_name": config.rag.collection_name,
            "persist_directory": config.rag.persist_directory,
        }
        rag_service.initialize(rag_config)
        logger.info("RAG 服务已初始化")
    elif config.rag.enabled:
        logger.warning("RAG Embedding API Key 未配置，知识库功能不可用")
    else:
        logger.info("RAG 功能已禁用")

    # 初始化 Agent 服务
    if config.agent.enabled:
        from app.services.agent_service import agent_service
        from app.services.message_service import MessageService
        message_service = MessageService()
        agent_config = {
            "llm": llm_config if config.llm.api_key else {},
            "rag": rag_config if config.rag.enabled and config.rag.embedding_api_key else {},
        }
        agent_service.initialize(agent_config, message_service)
        logger.info("Agent 服务已初始化")
    else:
        logger.info("Agent 功能已禁用")

    # 初始化知识库管理器
    from app.services.kb_manager import kb_manager
    kb_manager.initialize()
    logger.info("知识库管理器已初始化")

    yield

    logger.info("企业微信自动化服务关闭")


app = FastAPI(
    title="企业微信自动化服务",
    description="基于 FastAPI 的企业微信自动化服务，支持 LLM + RAG 知识库",
    version="1.1.0",
    lifespan=lifespan
)

# 注册路由
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    """健康检查"""
    from app.services.llm_service import llm_service
    from app.services.rag_service import rag_service
    from app.services.agent_service import agent_service

    return {
        "status": "ok",
        "service": "enterprise-wechat",
        "llm_initialized": llm_service.is_initialized(),
        "rag_initialized": rag_service.is_initialized(),
        "agent_initialized": agent_service.is_initialized(),
    }