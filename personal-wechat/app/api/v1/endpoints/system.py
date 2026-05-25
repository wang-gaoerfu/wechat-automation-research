"""System and health check endpoints."""
from fastapi import APIRouter, HTTPException

from app.models.schemas import WCFStatusResponse
from app.services.connection_manager import connection_manager
from app.services.anti_ban.rate_limiter import rate_limiter
from app.config import settings

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint.

    Returns:
        Health status dictionary.
    """
    return {
        "status": "healthy",
        "service": "personal-wechat",
        "version": "1.0.0",
    }


@router.get("/status/wcf", response_model=WCFStatusResponse)
async def get_wcf_status() -> WCFStatusResponse:
    """Get WeChatFerry connection status.

    Returns:
        WCFStatusResponse with connection details.
    """
    return WCFStatusResponse(
        connected=connection_manager.connected,
        host=settings.wcf.host,
        port=settings.wcf.port,
        uptime=connection_manager.uptime,
    )


@router.get("/status/rate-limiter")
async def get_rate_limiter_status() -> dict:
    """Get rate limiter status.

    Returns:
        Rate limiter status dictionary.
    """
    return rate_limiter.get_status()


@router.post("/reconnect")
async def reconnect_wcf() -> dict:
    """Force reconnect to WeChatFerry.

    Returns:
        Reconnection result.
    """
    try:
        success = await connection_manager.force_reconnect()
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))