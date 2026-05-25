"""系统管理接口"""
import logging

from fastapi import APIRouter

from app.config import get_config
from app.services.token_manager import TokenManager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/config")
async def get_system_config():
    """获取系统配置（不包含敏感信息）"""
    config = get_config()
    return {
        "corp_id": config.wechat.corp_id,
        "agent_id": config.wechat.agent_id,
        "debug": config.app.debug
    }


@router.post("/token/refresh")
async def refresh_token():
    """强制刷新 access_token"""
    try:
        token_manager = TokenManager()
        token = await token_manager.refresh_token()
        return {"access_token": token}
    except Exception as e:
        logger.error(f"刷新 access_token 失败: {e}")
        return {"error": str(e)}