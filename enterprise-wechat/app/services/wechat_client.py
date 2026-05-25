"""企业微信 API 客户端"""
import logging
from typing import Dict, Any, Optional

import httpx

from app.config import get_config
from app.services.token_manager import TokenManager

logger = logging.getLogger(__name__)


class WeChatClient:
    """企业微信 API 客户端"""

    BASE_URL = "https://qyapi.weixin.qq.com/cgi-bin"

    def __init__(self):
        self._token_manager = TokenManager()
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """获取 HTTP 客户端"""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    async def close(self):
        """关闭 HTTP 客户端"""
        if self._http_client and not self._http_client.is_closed:
            await self._http_client.aclose()

    async def _request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        retry: int = 3
    ) -> Dict[str, Any]:
        """统一请求方法（支持重试）"""
        client = await self._get_client()

        for attempt in range(retry):
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data
                )
                response.raise_for_status()
                result = response.json()

                # 检查错误码
                if result.get("errcode", 0) != 0:
                    logger.warning(f"API 调用失败: {result}")
                    # token 过期时重试
                    if result.get("errcode") == 40014 or result.get("errcode") == 42001:
                        if attempt < retry - 1:
                            logger.info("Token 过期，刷新后重试...")
                            await self._token_manager.refresh_token()
                            continue

                return result

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP 错误: {e}")
                if attempt >= retry - 1:
                    raise
            except Exception as e:
                logger.error(f"请求异常: {e}")
                if attempt >= retry - 1:
                    raise

        return {"errcode": -1, "errmsg": "请求失败"}

    async def get_access_token(self, corp_id: str, corp_secret: str) -> Dict[str, Any]:
        """获取 access_token"""
        url = f"{self.BASE_URL}/gettoken"
        params = {"corpid": corp_id, "corpsecret": corp_secret}
        return await self._request("GET", url, params=params)

    async def message_send(
        self,
        access_token: str,
        agent_id: str,
        message: Dict[str, Any]
    ) -> Dict[str, Any]:
        """发送消息"""
        url = f"{self.BASE_URL}/message/send"
        params = {"access_token": access_token}
        data = {
            "touser": "@all",
            "msgtype": message.get("msgtype", "text"),
            "agentid": agent_id,
            **message
        }
        # 如果指定了用户，覆盖默认的 @all
        if message.get("touser"):
            data["touser"] = message["touser"]
        return await self._request("POST", url, params=params, json_data=data)

    async def message_send_text(
        self,
        access_token: str,
        agent_id: str,
        content: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """发送文本消息"""
        message = {
            "msgtype": "text",
            "text": {"content": content}
        }
        if user_id:
            message["touser"] = user_id
        return await self.message_send(access_token, agent_id, message)

    async def message_send_markdown(
        self,
        access_token: str,
        agent_id: str,
        content: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """发送 Markdown 消息"""
        message = {
            "msgtype": "markdown",
            "markdown": {"content": content}
        }
        if user_id:
            message["touser"] = user_id
        return await self.message_send(access_token, agent_id, message)

    async def message_send_group(
        self,
        access_token: str,
        agent_id: str,
        user_list: list,
        content: str
    ) -> Dict[str, Any]:
        """群发消息"""
        message = {
            "msgtype": "text",
            "text": {"content": content},
            "touser": "|".join(user_list)
        }
        return await self.message_send(access_token, agent_id, message)

    async def external_contact_list(
        self,
        access_token: str,
        user_id: str
    ) -> Dict[str, Any]:
        """获取客户列表"""
        url = f"{self.BASE_URL}/externalcontact/list"
        params = {"access_token": access_token, "userid": user_id}
        return await self._request("GET", url, params=params)

    async def external_contact_add_tag(
        self,
        access_token: str,
        user_id: str,
        external_userid: str,
        tag_id_list: list
    ) -> Dict[str, Any]:
        """为客户添加标签"""
        url = f"{self.BASE_URL}/externalcontact/mark_tag"
        params = {"access_token": access_token}
        data = {
            "userid": user_id,
            "external_userid": external_userid,
            "tag_id_list": tag_id_list
        }
        return await self._request("POST", url, params=params, json_data=data)

    async def contact_way_create(
        self,
        access_token: str,
        scene: str,
        style: int = 1,
        limit: int = 1
    ) -> Dict[str, Any]:
        """创建联系我二维码"""
        url = f"{self.BASE_URL}/contact_way/create"
        params = {"access_token": access_token}
        data = {
            "scene": scene,
            "style": style,
            "limit": limit,
            "type": 2  # 临时二维码
        }
        return await self._request("POST", url, params=params, json_data=data)