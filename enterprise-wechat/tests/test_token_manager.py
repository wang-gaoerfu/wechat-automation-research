"""Token 管理器测试"""
import asyncio
import time
from unittest.mock import AsyncMock, patch

import pytest

from app.services.token_manager import TokenManager


class TestTokenManager:
    """TokenManager 测试类"""

    @pytest.fixture(autouse=True)
    def setup_method(self):
        """每个测试方法前清空单例"""
        TokenManager._instance = None

    @pytest.fixture
    def mock_config(self):
        """模拟配置"""
        with patch("app.services.token_manager.get_config") as mock:
            config = type("Config", (), {})()
            config.wechat.corp_id = "test_corp_id"
            config.wechat.corp_secret = "test_corp_secret"
            mock.return_value = config
            yield mock

    @pytest.fixture
    def mock_wechat_client(self):
        """模拟 WeChatClient"""
        with patch("app.services.token_manager.WeChatClient") as mock:
            client = mock.return_value
            client.get_access_token = AsyncMock(return_value={
                "access_token": "test_token_12345",
                "expires_in": 7200
            })
            yield mock

    @pytest.mark.asyncio
    async def test_get_access_token_first_time(self, mock_config, mock_wechat_client):
        """测试首次获取 token"""
        manager = TokenManager()
        token = await manager.get_access_token()

        assert token == "test_token_12345"
        mock_wechat_client.return_value.get_access_token.assert_called_once_with(
            corp_id="test_corp_id",
            corp_secret="test_corp_secret"
        )

    @pytest.mark.asyncio
    async def test_get_access_token_cached(self, mock_config, mock_wechat_client):
        """测试 token 缓存（不重复获取）"""
        manager = TokenManager()

        # 首次获取
        token1 = await manager.get_access_token()
        # 再次获取（应该使用缓存）
        token2 = await manager.get_access_token()

        assert token1 == token2
        # 只应该调用一次
        mock_wechat_client.return_value.get_access_token.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_token(self, mock_config, mock_wechat_client):
        """测试强制刷新 token"""
        manager = TokenManager()

        # 首次获取
        token1 = await manager.get_access_token()
        # 强制刷新
        token2 = await manager.refresh_token()

        assert token2 == "test_token_12345"
        assert token1 == token2
        # 应该调用两次（首次 + 刷新）
        assert mock_wechat_client.return_value.get_access_token.call_count == 2

    @pytest.mark.asyncio
    async def test_clear_cache(self, mock_config, mock_wechat_client):
        """测试清除缓存"""
        manager = TokenManager()

        # 首次获取
        await manager.get_access_token()
        # 清除缓存
        manager.clear_cache()
        # 再次获取
        await manager.get_access_token()

        # 清除后应该再次调用 API
        assert mock_wechat_client.return_value.get_access_token.call_count == 2

    @pytest.mark.asyncio
    async def test_concurrent_access(self, mock_config, mock_wechat_client):
        """测试并发访问（并发安全）"""
        manager = TokenManager()

        # 并发获取
        tasks = [manager.get_access_token() for _ in range(10)]
        tokens = await asyncio.gather(*tasks)

        # 所有 token 应该相同
        assert all(t == "test_token_12345" for t in tokens)
        # API 只应该被调用一次
        assert mock_wechat_client.return_value.get_access_token.call_count == 1