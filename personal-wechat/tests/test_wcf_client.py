"""Tests for WCF client."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestWCFClient:
    """Test cases for WCFClient."""

    @pytest.fixture
    def mock_wechatferry(self):
        """Create a mock WeChatFerry client."""
        with patch("app.services.wcf_client.WeChatFerry") as mock:
            instance = MagicMock()
            mock.return_value = instance
            yield instance

    @pytest.fixture
    def wcf_client(self, mock_wechatferry):
        """Create a WCFClient instance with mock."""
        from app.services.wcf_client import WCFClient
        client = WCFClient(host="localhost", port=10086)
        client._client = mock_wechatferry
        client._connected = True
        return client

    @pytest.mark.asyncio
    async def test_connect_success(self, wcf_client, mock_wechatferry):
        """Test successful connection."""
        result = await wcf_client.connect()
        assert result is True
        assert wcf_client.connected is True

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """Test connection failure."""
        from app.services.wcf_client import WCFClient
        with patch("app.services.wcf_client.WeChatFerry", side_effect=Exception("Connection failed")):
            client = WCFClient(host="localhost", port=10086)
            result = await client.connect()
            assert result is False
            assert client.connected is False

    @pytest.mark.asyncio
    async def test_send_text(self, wcf_client, mock_wechatferry):
        """Test sending text message."""
        mock_wechatferry.send_text = MagicMock(return_value="msg_123")
        result = await wcf_client.send_text("wxid123", "Hello")
        assert result == "msg_123"
        mock_wechatferry.send_text.assert_called_once_with("wxid123", "Hello")

    @pytest.mark.asyncio
    async def test_send_text_with_aters(self, wcf_client, mock_wechatferry):
        """Test sending text message with @ mentions."""
        mock_wechatferry.send_text = MagicMock(return_value="msg_124")
        result = await wcf_client.send_text("roomid", "Hello", aters=["wxid1", "wxid2"])
        assert result == "msg_124"
        mock_wechatferry.send_text.assert_called_once_with("roomid", "Hello", "wxid1,wxid2")

    @pytest.mark.asyncio
    async def test_send_image(self, wcf_client, mock_wechatferry):
        """Test sending image message."""
        mock_wechatferry.send_image = MagicMock(return_value="img_456")
        result = await wcf_client.send_image("wxid123", "/path/to/image.jpg")
        assert result == "img_456"
        mock_wechatferry.send_image.assert_called_once_with("wxid123", "/path/to/image.jpg")

    @pytest.mark.asyncio
    async def test_get_contacts(self, wcf_client, mock_wechatferry):
        """Test getting contact list."""
        mock_contacts = [
            {"wxid": "wxid1", "name": "Contact1"},
            {"wxid": "wxid2", "name": "Contact2"},
        ]
        mock_wechatferry.get_contact_list = MagicMock(return_value=mock_contacts)
        result = await wcf_client.get_contacts()
        assert len(result) == 2
        assert result[0]["wxid"] == "wxid1"

    @pytest.mark.asyncio
    async def test_get_self_wxid(self, wcf_client, mock_wechatferry):
        """Test getting self wxid."""
        mock_wechatferry.get_self_wxid = MagicMock(return_value="my_wxid")
        result = await wcf_client.get_self_wxid()
        assert result == "my_wxid"
        assert wcf_client.wxid == "my_wxid"

    @pytest.mark.asyncio
    async def test_disconnect(self, wcf_client):
        """Test disconnection."""
        await wcf_client.disconnect()
        assert wcf_client.connected is False

    def test_register_callback(self, wcf_client):
        """Test registering callbacks."""
        callback = MagicMock()
        wcf_client.register_callback(callback)
        assert callback in wcf_client._callbacks