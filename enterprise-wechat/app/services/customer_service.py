"""客户服务"""
import logging
from typing import Dict, Any, List, Optional

from app.services.wechat_client import WeChatClient
from app.services.token_manager import TokenManager

logger = logging.getLogger(__name__)


class CustomerService:
    """客户服务"""

    def __init__(self):
        self._client = WeChatClient()
        self._token_manager = TokenManager()

    async def create_contact_qr(
        self,
        scene: str,
        style: int = 1,
        limit: int = 1
    ) -> Dict[str, Any]:
        """创建联系我二维码"""
        access_token = await self._token_manager.get_access_token()

        result = await self._client.contact_way_create(
            access_token=access_token,
            scene=scene,
            style=style,
            limit=limit
        )

        logger.info(f"创建联系我二维码: {result}")
        return result

    async def get_customer_list(self, user_id: str) -> Dict[str, Any]:
        """获取客户列表"""
        access_token = await self._token_manager.get_access_token()

        result = await self._client.external_contact_list(
            access_token=access_token,
            user_id=user_id
        )

        logger.info(f"获取客户列表 {user_id}: {result}")
        return result

    async def add_tag(
        self,
        user_id: str,
        external_userid: str,
        tag_id_list: List[str]
    ) -> Dict[str, Any]:
        """为客户添加标签"""
        access_token = await self._token_manager.get_access_token()

        result = await self._client.external_contact_add_tag(
            access_token=access_token,
            user_id=user_id,
            external_userid=external_userid,
            tag_id_list=tag_id_list
        )

        logger.info(f"为客户 {external_userid} 添加标签: {result}")
        return result