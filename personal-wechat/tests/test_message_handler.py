"""Tests for message handler."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestMessageHandler:
    """Test cases for MessageHandler."""

    @pytest.fixture
    def message_handler(self):
        """Create a MessageHandler instance for testing."""
        from app.services.message_handler import MessageHandler
        return MessageHandler()

    @pytest.fixture
    def sample_message(self):
        """Create a sample message."""
        return {
            "wxid": "wxid123",
            "content": "Hello, how are you?",
            "msg_id": "msg_001",
            "msg_type": 1,
            "roomid": None,
        }

    @pytest.mark.asyncio
    async def test_handle_message(self, message_handler, sample_message):
        """Test handling a message."""
        with patch.object(message_handler, "_save_message", new_callable=AsyncMock):
            result = await message_handler.handle_message(sample_message)
            # No auto-reply configured, should return None
            assert result is None

    @pytest.mark.asyncio
    async def test_handle_message_with_keyword_reply(self, message_handler, sample_message):
        """Test handling message with keyword auto-reply."""
        message_handler.add_auto_reply_rule("Hello", "Hi there!")
        sample_message["content"] = "Hello"

        with patch.object(message_handler, "_save_message", new_callable=AsyncMock):
            with patch.object(message_handler, "_send_reply", new_callable=AsyncMock):
                result = await message_handler.handle_message(sample_message)
                assert result is not None
                assert "Hi there" in result

    @pytest.mark.asyncio
    async def test_handle_callback_request(self, message_handler):
        """Test handling callback request."""
        from app.models.schemas import MessageCallbackRequest

        request = MessageCallbackRequest(
            wxid="wxid123",
            content="Test message",
            msg_id="msg_001",
            msg_type=1,
            timestamp=1234567890,
        )

        with patch.object(message_handler, "handle_message", new_callable=AsyncMock) as mock_handle:
            mock_handle.return_value = None
            response = await message_handler.handle_callback_request(request)
            assert response.success is True
            assert response.reply is None

    @pytest.mark.asyncio
    async def test_llm_reply_integration(self, message_handler, sample_message):
        """Test LLM reply integration."""
        llm_reply = AsyncMock(return_value="LLM generated reply")
        message_handler.set_llm_reply_func(llm_reply)

        with patch.object(message_handler, "_save_message", new_callable=AsyncMock):
            with patch.object(message_handler, "_send_reply", new_callable=AsyncMock):
                result = await message_handler.handle_message(sample_message)
                assert result is not None
                llm_reply.assert_called_once()

    def test_add_auto_reply_rule(self, message_handler):
        """Test adding auto-reply rule."""
        message_handler.add_auto_reply_rule("test", "Test reply")
        rules = message_handler.get_auto_reply_rules()
        assert len(rules) == 1
        assert rules[0].keyword == "test"

    def test_remove_auto_reply_rule(self, message_handler):
        """Test removing auto-reply rule."""
        message_handler.add_auto_reply_rule("test", "Test reply")
        result = message_handler.remove_auto_reply_rule("test")
        assert result is True
        assert len(message_handler.get_auto_reply_rules()) == 0

    def test_remove_nonexistent_rule(self, message_handler):
        """Test removing non-existent rule."""
        result = message_handler.remove_auto_reply_rule("nonexistent")
        assert result is False

    def test_register_callback(self, message_handler):
        """Test registering callbacks."""
        callback = MagicMock()
        message_handler.register_callback(callback)
        assert callback in message_handler._callbacks