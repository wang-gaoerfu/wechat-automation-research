"""Token 管理服务"""
import asyncio
import logging
import time
from typing import Optional

from app.config import get_config
from app.services.wechat_client import WeChatClient

logger = logging.getLogger(__name__)


class TokenManager:
    """Token 管理器（单例）"""

    _instance: Optional["TokenManager"] = None
    _lock: asyncio.Lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._access_token: Optional[str] = None
        self._expire_time: float = 0
        self._refresh_before: int = 300  # 提前5分钟刷新
        self._client = WeChatClient()
        self._refreshing = False

    async def get_access_token(self) -> str:
        """获取 access_token（自动刷新）"""
        # 检查是否需要刷新
        if self._should_refresh():
            await self.refresh_token()
        return self._access_token or ""

    def _should_refresh(self) -> bool:
        """检查是否需要刷新 token"""
        if not self._access_token:
            return True
        # 提前5分钟刷新
        return time.time() >= (self._expire_time - self._refresh_before)

    async def refresh_token(self) -> str:
        """刷新 access_token（并发安全）"""
        async with self._lock:
            # 双重检查
            if not self._should_refresh() and self._access_token:
                return self._access_token

            config = get_config()
            try:
                logger.info("正在刷新 access_token...")
                resp = await self._client.get_access_token(
                    corp_id=config.wechat.corp_id,
                    corp_secret=config.wechat.corp_secret
                )

                self._access_token = resp["access_token"]
                self._expire_time = time.time() + resp.get("expires_in", 7200)
                logger.info(f"access_token 刷新成功，有效期: {resp.get('expires_in')}秒")
                return self._access_token

            except Exception as e:
                logger.error(f"刷新 access_token 失败: {e}")
                raise

    def clear_cache(self):
        """清除 token 缓存（用于退出或切换账号）"""
        self._access_token = None
        self._expire_time = 0