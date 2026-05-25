"""消息服务"""
import asyncio
import logging
import time
from typing import Optional, List

import aiosqlite

from app.config import get_config
from app.services.wechat_client import WeChatClient
from app.services.token_manager import TokenManager

logger = logging.getLogger(__name__)


class MessageService:
    """消息服务"""

    # 频率限制：20次/分钟
    RATE_LIMIT = 20
    RATE_WINDOW = 60  # 秒
    # 群发限制：4次/日
    GROUP_MESSAGE_DAILY_LIMIT = 4

    def __init__(self):
        self._client = WeChatClient()
        self._token_manager = TokenManager()
        self._send_times: List[float] = []
        self._send_lock = asyncio.Lock()

    def _get_db_path(self) -> str:
        """获取数据库路径"""
        config = get_config()
        db_url = config.database.url
        db_path = db_url.replace("sqlite:///", "")
        if db_path.startswith("./"):
            db_path = db_path[2:]
        return db_path

    async def _get_daily_group_count(self) -> int:
        """获取今日群发次数"""
        today = time.strftime("%Y-%m-%d")
        db_path = self._get_db_path()
        async with aiosqlite.connect(db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT send_count FROM group_messages WHERE send_date = ?",
                (today,)
            ) as cursor:
                row = await cursor.fetchone()
                return row["send_count"] if row else 0

    async def _increment_daily_group_count(self):
        """增加今日群发次数"""
        today = time.strftime("%Y-%m-%d")
        db_path = self._get_db_path()
        async with aiosqlite.connect(db_path) as conn:
            await conn.execute("""
                INSERT INTO group_messages (send_date, send_count, updated_at)
                VALUES (?, 1, CURRENT_TIMESTAMP)
                ON CONFLICT(send_date) DO UPDATE SET
                    send_count = send_count + 1,
                    updated_at = CURRENT_TIMESTAMP
            """, (today,))
            await conn.commit()

    async def _check_rate_limit(self):
        """检查频率限制"""
        async with self._send_lock:
            now = time.time()
            # 清理过期的记录
            self._send_times = [t for t in self._send_times if now - t < self.RATE_WINDOW]

            if len(self._send_times) >= self.RATE_LIMIT:
                oldest = self._send_times[0]
                wait_time = self.RATE_WINDOW - (now - oldest)
                if wait_time > 0:
                    logger.warning(f"频率限制触发，等待 {wait_time:.1f} 秒")
                    await asyncio.sleep(wait_time)
                    # 再次清理
                    now = time.time()
                    self._send_times = [t for t in self._send_times if now - t < self.RATE_WINDOW]

            self._send_times.append(now)

    async def send_text(
        self,
        user_id: str,
        content: str,
        agent_id: Optional[str] = None
    ) -> dict:
        """发送文本消息"""
        await self._check_rate_limit()

        config = get_config()
        agent_id = agent_id or config.wechat.agent_id
        access_token = await self._token_manager.get_access_token()

        result = await self._client.message_send_text(
            access_token=access_token,
            agent_id=agent_id,
            content=content,
            user_id=user_id
        )

        logger.info(f"发送文本消息给 {user_id}: {result}")
        return result

    async def send_markdown(
        self,
        user_id: str,
        content: str,
        agent_id: Optional[str] = None
    ) -> dict:
        """发送 Markdown 消息"""
        await self._check_rate_limit()

        config = get_config()
        agent_id = agent_id or config.wechat.agent_id
        access_token = await self._token_manager.get_access_token()

        result = await self._client.message_send_markdown(
            access_token=access_token,
            agent_id=agent_id,
            content=content,
            user_id=user_id
        )

        logger.info(f"发送 Markdown 消息给 {user_id}: {result}")
        return result

    async def send_group_message(
        self,
        user_list: List[str],
        content: str,
        agent_id: Optional[str] = None
    ) -> dict:
        """群发消息（每日最多4次）"""
        # 检查每日发送次数（从数据库读取）
        daily_count = await self._get_daily_group_count()
        if daily_count >= self.GROUP_MESSAGE_DAILY_LIMIT:
            raise ValueError("群发消息每日最多发送4次")

        await self._check_rate_limit()

        config = get_config()
        agent_id = agent_id or config.wechat.agent_id
        access_token = await self._token_manager.get_access_token()

        result = await self._client.message_send_group(
            access_token=access_token,
            agent_id=agent_id,
            user_list=user_list,
            content=content
        )

        await self._increment_daily_group_count()
        logger.info(f"发送群发消息给 {len(user_list)} 人: {result}")
        return result