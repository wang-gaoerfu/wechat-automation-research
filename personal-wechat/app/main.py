"""FastAPI application entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from app.api.v1 import api_router
from app.config import settings
from app.db.database import init_db
from app.services.connection_manager import connection_manager
from app.services.message_handler import message_handler


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Starting Personal WeChat Automation Service...")

    # Initialize database
    try:
        await init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")

    # Start connection manager
    try:
        await connection_manager.start()
        logger.info("Connection manager started")
    except Exception as e:
        logger.error(f"Connection manager start failed: {e}")

    # Initialize LLM service
    if settings.llm.api_key:
        from app.services.llm_service import llm_service
        llm_config = {
            "provider": settings.llm.provider,
            "api_key": settings.llm.api_key,
            "base_url": settings.llm.base_url,
            "model": settings.llm.model,
        }
        llm_service.initialize(llm_config)
        logger.info(f"LLM 服务已初始化: {settings.llm.provider}")

        # 设置 LLM 回复函数到消息处理器
        async def llm_reply_func(wxid: str, content: str) -> str:
            return await llm_service.chat(
                user_message=content,
                system_prompt="你是一个智能微信助手，请用简洁友好的方式回复用户。"
            )
        message_handler.set_llm_reply_func(llm_reply_func)
    else:
        logger.warning("LLM API Key 未配置，LLM 功能不可用")

    # Initialize RAG service
    if settings.rag.enabled and settings.rag.embedding_api_key:
        from app.services.rag_service import rag_service
        rag_config = {
            "embedding_provider": settings.rag.embedding_provider,
            "embedding_api_key": settings.rag.embedding_api_key,
            "embedding_base_url": settings.rag.embedding_base_url,
            "collection_name": settings.rag.collection_name,
            "persist_directory": settings.rag.persist_directory,
        }
        rag_service.initialize(rag_config)
        logger.info("RAG 服务已初始化")

        # 设置 RAG 回复函数到消息处理器
        async def rag_reply_func(wxid: str, content: str) -> str:
            context = await rag_service.get_relevant_context(
                query=content,
                context_length=3,
                similarity_threshold=0.5
            )
            if context:
                prompt = f"根据以下知识库内容回答用户问题：\n\n{context}\n\n用户问题：{content}"
            else:
                prompt = content
            return await llm_service.chat(
                user_message=prompt,
                system_prompt="你是一个智能微信助手，请根据提供的知识库内容回答用户问题。如果知识库没有相关信息，请如实告知。"
            )
        message_handler.set_rag_reply_func(rag_reply_func)
    elif settings.rag.enabled:
        logger.warning("RAG Embedding API Key 未配置，知识库功能不可用")

    # 初始化知识库管理器
    from app.services.kb_manager import kb_manager
    kb_manager.initialize()
    logger.info("知识库管理器已初始化")

    yield

    # Shutdown
    logger.info("Shutting down Personal WeChat Automation Service...")
    await connection_manager.stop()


# Create FastAPI app
app = FastAPI(
    title="Personal WeChat Automation API",
    description="API for WeChat automation using WeChatFerry with LLM and RAG",
    version="1.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.app.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "detail": str(exc)},
    )


# Include API router
app.include_router(api_router, prefix="/api/v1")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    from app.services.llm_service import llm_service
    from app.services.rag_service import rag_service

    return {
        "service": "Personal WeChat Automation API",
        "version": "1.1.0",
        "docs": "/docs",
        "llm_initialized": llm_service.is_initialized(),
        "rag_initialized": rag_service.is_initialized(),
    }


# Ready endpoint
@app.get("/ready")
async def ready():
    """Readiness check endpoint."""
    from app.services.llm_service import llm_service
    from app.services.rag_service import rag_service

    return {
        "ready": True,
        "wcf_connected": connection_manager.connected,
        "llm_initialized": llm_service.is_initialized(),
        "rag_initialized": rag_service.is_initialized(),
    }