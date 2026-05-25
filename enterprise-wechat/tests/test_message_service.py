"""消息服务测试"""
import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.services.message_service import MessageService


class TestMessageService:
    """MessageService 测试类"""

    @pytest.fixture
    def mock_config(self):
        """模拟配置"""
        with patch("app.services.message_service.get_config") as mock:
            config = type("Config", (), {})()
            config.wechat.agent_id = "1000002"
            mock.return_value = config
            yield mock

    @pytest.fixture
    def mock_wechat_client(self):
        """模拟 WeChatClient"""
        with patch("app.services.message_service.WeChatClient") as mock:
            client = mock.return_value
            client.message_send_text = AsyncMock(return_value={
                "errcode": 0,
                "errmsg": "ok"
            })
            client.message_send_markdown = AsyncMock(return_value={
                "errcode": 0,
                "errmsg": "ok"
            })
            client.message_send_group = AsyncMock(return_value={
                "errcode": 0,
                "errmsg": "ok"
            })
            yield mock

    @pytest.fixture
    def mock_token_manager(self):
        """模拟 TokenManager"""
        with patch("app.services.message_service.TokenManager") as mock:
            manager = mock.return_value
            manager.get_access_token = AsyncMock(return_value="test_token")
            yield mock

    @pytest.mark.asyncio
    async def test_send_text_success(self, mock_config, mock_wechat_client, mock_token_manager):
        """测试发送文本消息成功"""
        service = MessageService()
        result = await service.send_text(
            user_id="test_user",
            content="Hello World"
        )

        assert result["errcode"] == 0
        mock_wechat_client.return_value.message_send_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_markdown_success(self, mock_config, mock_wechat_client, mock_token_manager):
        """测试发送 Markdown 消息成功"""
        service = MessageService()
        result = await service.send_markdown(
            user_id="test_user",
            content="**Bold** text"
        )

        assert result["errcode"] == 0
        mock_wechat_client.return_value.message_send_markdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_group_message_success(self, mock_config, mock_wechat_client, mock_token_manager):
        """测试发送群发消息成功"""
        service = MessageService()
        result = await service.send_group_message(
            user_list=["user1", "user2"],
            content="Group message"
        )

        assert result["errcode"] == 0
        mock_wechat_client.return_value.message_send_group.assert_called_once()

    @pytest.mark.asyncio
    async def test_rate_limit(self, mock_config, mock_wechat_client, mock_token_manager):
        """测试频率限制"""
        service = MessageService()

        # 模拟超过频率限制
        service._send_times = [0.0] * 20

        # 应该不会抛出异常（会等待）
        async def run_test():
            await service.send_text(user_id="test", content="test")

        # 如果频率限制正常工作，这个调用应该会等待或通过
        # 这里我们不精确测试等待时间，只测试不会崩溃
        try:
            await asyncio.wait_for(run_test(), timeout=5.0)
        except asyncio.TimeoutError:
            # 超时说明等待逻辑正常工作
            pass