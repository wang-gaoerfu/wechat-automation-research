"""LLM Service Tests"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.llm_service import (
    LLMService, Message, OpenAILLM, ClaudeLLM, OllamaLLM, SenseNovaLLM
)


class TestMessage:
    """Message dataclass tests"""

    def test_message_creation(self):
        """Test creating a message"""
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"


class TestLLMService:
    """LLMService unit tests"""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test"""
        LLMService._instance = None

    def test_singleton_pattern(self):
        """Test singleton pattern"""
        instance1 = LLMService.get_instance()
        instance2 = LLMService.get_instance()
        assert instance1 is instance2

    def test_initialize_openai(self):
        """Test initializing OpenAI provider"""
        service = LLMService.get_instance()
        config = {
            "provider": "openai",
            "api_key": "test_key",
            "model": "gpt-4o-mini"
        }
        service.initialize(config)
        assert service.is_initialized() is True
        assert service.provider_type == "openai"

    def test_initialize_sensenova(self):
        """Test initializing SenseNova provider"""
        service = LLMService.get_instance()
        config = {
            "provider": "sensenova",
            "api_key": "test_key",
            "base_url": "https://token.sensenova.cn/v1",
            "model": "sensenova-6.7-flash-lite"
        }
        service.initialize(config)
        assert service.is_initialized() is True
        assert service.provider_type == "sensenova"

    def test_initialize_ollama(self):
        """Test initializing Ollama provider"""
        service = LLMService.get_instance()
        config = {
            "provider": "ollama",
            "model": "llama3.2"
        }
        service.initialize(config)
        assert service.is_initialized() is True
        assert service.provider_type == "ollama"

    def test_initialize_invalid_provider(self):
        """Test initializing with invalid provider"""
        service = LLMService.get_instance()
        config = {
            "provider": "invalid",
            "api_key": "test_key"
        }
        with pytest.raises(ValueError):
            service.initialize(config)

    @pytest.mark.asyncio
    async def test_chat_not_initialized(self):
        """Test chat without initialization"""
        service = LLMService.get_instance()
        with pytest.raises(RuntimeError):
            await service.chat("Hello")


class TestOpenAILLM:
    """OpenAI LLM tests"""

    @pytest.fixture
    def llm(self):
        """Create OpenAI LLM instance"""
        return OpenAILLM(
            api_key="test_key",
            model="gpt-4o-mini"
        )

    @pytest.mark.asyncio
    async def test_chat_success(self, llm):
        """Test successful chat request"""
        mock_response = {
            "choices": [{
                "message": {"content": "Hello! How can I help?"}
            }]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = MagicMock(
                json=AsyncMock(return_value=mock_response),
                raise_for_status=MagicMock()
            )
            mock_client.return_value.__aenter__.return_value = mock_instance

            result = await llm.chat([Message(role="user", content="Hi")])
            assert result == "Hello! How can I help?"


class TestSenseNovaLLM:
    """SenseNova LLM tests"""

    @pytest.fixture
    def llm(self):
        """Create SenseNova LLM instance"""
        return SenseNovaLLM(
            api_key="test_key",
            model="sensenova-6.7-flash-lite"
        )

    @pytest.mark.asyncio
    async def test_chat_success(self, llm):
        """Test successful chat request"""
        mock_response = {
            "choices": [{
                "message": {"content": "你好，我是SenseNova助手"}
            }]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = MagicMock(
                json=AsyncMock(return_value=mock_response),
                raise_for_status=MagicMock()
            )
            mock_client.return_value.__aenter__.return_value = mock_instance

            result = await llm.chat([Message(role="user", content="你好")])
            assert result == "你好，我是SenseNova助手"

    @pytest.mark.asyncio
    async def test_chat_with_custom_model(self, llm):
        """Test chat with custom model"""
        mock_response = {
            "choices": [{
                "message": {"content": "Response"}
            }]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = MagicMock(
                json=AsyncMock(return_value=mock_response),
                raise_for_status=MagicMock()
            )
            mock_client.return_value.__aenter__.return_value = mock_instance

            result = await llm.chat(
                [Message(role="user", content="Hello")],
                model="deepseek-v4-flash"
            )
            assert result == "Response"


class TestOllamaLLM:
    """Ollama LLM tests"""

    @pytest.fixture
    def llm(self):
        """Create Ollama LLM instance"""
        return OllamaLLM(
            base_url="http://localhost:11434",
            model="llama3.2"
        )

    @pytest.mark.asyncio
    async def test_chat_success(self, llm):
        """Test successful chat request"""
        mock_response = {
            "message": {"content": "Hello from Ollama"}
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = MagicMock(
                json=AsyncMock(return_value=mock_response),
                raise_for_status=MagicMock()
            )
            mock_client.return_value.__aenter__.return_value = mock_instance

            result = await llm.chat([Message(role="user", content="Hi")])
            assert result == "Hello from Ollama"