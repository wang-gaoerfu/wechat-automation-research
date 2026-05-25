"""RAG Service Tests"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.rag_service import RAGService, EmbeddingService


class TestEmbeddingService:
    """EmbeddingService tests"""

    @pytest.fixture
    def embedding_service(self):
        """Create EmbeddingService instance"""
        return EmbeddingService(
            provider="openai",
            api_key="test_key"
        )

    @pytest.mark.asyncio
    async def test_embed_texts_openai(self, embedding_service):
        """Test OpenAI embedding"""
        mock_response = {
            "data": [
                {"embedding": [0.1, 0.2, 0.3]},
                {"embedding": [0.4, 0.5, 0.6]}
            ]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_instance = AsyncMock()
            mock_instance.post.return_value = MagicMock(
                json=AsyncMock(return_value=mock_response),
                raise_for_status=MagicMock()
            )
            mock_client.return_value.__aenter__.return_value = mock_instance

            texts = ["Hello", "World"]
            result = await embedding_service.embed_texts(texts)
            assert len(result) == 2
            assert result[0] == [0.1, 0.2, 0.3]


class TestRAGService:
    """RAGService unit tests"""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test"""
        RAGService._instance = None

    def test_singleton_pattern(self):
        """Test singleton pattern"""
        instance1 = RAGService.get_instance()
        instance2 = RAGService.get_instance()
        assert instance1 is instance2

    def test_initialize(self):
        """Test initializing RAG service"""
        service = RAGService.get_instance()
        config = {
            "embedding_provider": "openai",
            "embedding_api_key": "test_key",
            "collection_name": "test_collection",
            "persist_directory": "./test_data"
        }

        with patch("chromadb.Client") as mock_chroma:
            service.initialize(config)
            assert service.is_initialized() is True

    def test_initialize_without_api_key(self):
        """Test initialization fails without API key"""
        service = RAGService.get_instance()
        config = {
            "embedding_provider": "openai",
            "embedding_api_key": "",
            "collection_name": "test"
        }

        # Should not raise but may log warning
        try:
            service.initialize(config)
        except Exception:
            pytest.fail("Should not raise exception")

    @pytest.mark.asyncio
    async def test_add_documents_not_initialized(self):
        """Test adding documents without initialization"""
        service = RAGService.get_instance()
        with pytest.raises(RuntimeError):
            await service.add_documents([{"content": "test"}])

    @pytest.mark.asyncio
    async def test_search_not_initialized(self):
        """Test searching without initialization"""
        service = RAGService.get_instance()
        with pytest.raises(RuntimeError):
            await service.search("test query")

    def test_count_not_initialized(self):
        """Test count without initialization"""
        service = RAGService.get_instance()
        assert service.count() == 0

    def test_is_initialized_false_by_default(self):
        """Test is_initialized returns False by default"""
        service = RAGService.get_instance()
        assert service.is_initialized() is False


class TestRAGIntegration:
    """RAG integration tests (with mocked ChromaDB)"""

    @pytest.fixture
    def mock_collection(self):
        """Create mock ChromaDB collection"""
        collection = MagicMock()
        collection.add = MagicMock(return_value=["id1", "id2"])
        collection.query = MagicMock(return_value={
            "documents": [["Document 1", "Document 2"]],
            "metadatas": [[{"source": "test"}, {"source": "test2"}]],
            "distances": [[0.1, 0.2]]
        })
        collection.delete = MagicMock()
        collection.count = MagicMock(return_value=2)
        return collection

    @pytest.fixture
    def mock_chroma_client(self, mock_collection):
        """Create mock ChromaDB client"""
        with patch("chromadb.Client") as mock:
            client_instance = MagicMock()
            client_instance.get_or_create_collection.return_value = mock_collection
            mock.return_value = client_instance
            yield client_instance