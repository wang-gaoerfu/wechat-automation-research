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
    """Application lifespan handler.

    Handles startup and shutdown events.
    """
    # Startup
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

    yield

    # Shutdown
    logger.info("Shutting down Personal WeChat Automation Service...")
    await connection_manager.stop()


# Create FastAPI app
app = FastAPI(
    title="Personal WeChat Automation API",
    description="API for WeChat automation using WeChatFerry",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.app.cors_origins if hasattr(settings.app, 'cors_origins') else ["http://localhost:3000", "http://localhost:8080"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions.

    Args:
        request: FastAPI request.
        exc: Exception that was raised.

    Returns:
        JSON error response.
    """
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
    """Root endpoint.

    Returns:
        Welcome message.
    """
    return {
        "service": "Personal WeChat Automation API",
        "version": "1.0.0",
        "docs": "/docs",
    }


# Ready endpoint
@app.get("/ready")
async def ready():
    """ Readiness check endpoint.

    Returns:
        Ready status.
    """
    return {
        "ready": True,
        "wcf_connected": connection_manager.connected,
    }