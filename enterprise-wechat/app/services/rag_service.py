"""RAG 服务 - 基于 ChromaDB 的知识库检索增强生成（多知识库版本）"""
import asyncio
import logging
import os
import uuid
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.config import Settings
from chromadb.api.models import Collection
import httpx

from app.config import get_config

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Embedding 服务 - 文本向量化"""

    def __init__(self, provider: str = "openai", api_key: str = "", base_url: str = ""):
        self.provider = provider
        self.api_key = api_key
        self.base_url = base_url

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """将文本列表转换为向量"""
        if self.provider in ("openai", "sensenova"):
            return await self._openai_embed(texts)
        elif self.provider == "ollama":
            return await self._ollama_embed(texts)
        else:
            raise ValueError(f"不支持的 embedding provider: {self.provider}")

    async def _openai_embed(self, texts: List[str]) -> List[List[float]]:
        """OpenAI/SenseNova Embedding API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "text-embedding-3-small",
            "input": texts
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url or 'https://api.openai.com'}/v1/embeddings",
                headers=headers,
                json=payload,
                timeout=30.0
            )
            response.raise_for_status()
            data = response.json()
            return [item["embedding"] for item in data["data"]]

    async def _ollama_embed(self, texts: List[str]) -> List[List[float]]:
        """Ollama Embedding API"""
        embeddings = []
        async with httpx.AsyncClient() as client:
            for text in texts:
                response = await client.post(
                    f"{self.base_url or 'http://localhost:11434'}/api/embeddings",
                    json={"model": "nomic-embed-text", "prompt": text},
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                embeddings.append(data["embedding"])
        return embeddings


class RAGService:
    """RAG 服务 - 多知识库版本（按场景隔离）"""

    _instance: Optional["RAGService"] = None

    def __init__(self):
        self._client: Optional[chromadb.Client] = None
        self._collections: Dict[str, Collection] = {}  # 场景名 -> Collection
        self._embedding_service: Optional[EmbeddingService] = None
        self._initialized = False
        self._default_collection_name: str = "knowledge_base"
        self._persist_directory: str = "./data/chromadb"

    @classmethod
    def get_instance(cls) -> "RAGService":
        """获取单例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def initialize(self, config: Dict[str, Any]) -> None:
        """初始化 RAG 服务"""
        embedding_provider = config.get("embedding_provider", "openai")
        embedding_api_key = config.get("embedding_api_key", "")
        embedding_base_url = config.get("embedding_base_url", "")

        self._embedding_service = EmbeddingService(
            provider=embedding_provider,
            api_key=embedding_api_key,
            base_url=embedding_base_url
        )

        self._persist_directory = config.get("persist_directory", "./data/chromadb")
        os.makedirs(self._persist_directory, exist_ok=True)

        self._default_collection_name = config.get("collection_name", "knowledge_base")

        # 初始化 ChromaDB 客户端（持久化）
        self._client = chromadb.Client(Settings(
            anonymized_telemetry=False,
            allow_reset=True,
            persist_directory=self._persist_directory
        ))

        self._initialized = True
        logger.info(f"RAG 服务初始化完成，持久化目录: {self._persist_directory}")

    def _get_collection(self, collection_name: str) -> Collection:
        """获取或创建指定名称的 Collection"""
        if collection_name not in self._collections:
            self._collections[collection_name] = self._client.get_or_create_collection(
                name=collection_name,
                metadata={"description": f"Knowledge Base: {collection_name}"}
            )
        return self._collections[collection_name]

    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        collection_name: Optional[str] = None,
        ids: Optional[List[str]] = None,
        metadata: Optional[List[Dict[str, Any]]] = None
    ) -> List[str]:
        """添加文档到指定知识库"""
        if not self._initialized:
            raise RuntimeError("RAG 服务未初始化")

        if not documents:
            return []

        collection_name = collection_name or self._default_collection_name
        collection = self._get_collection(collection_name)

        if ids is None:
            ids = [str(uuid.uuid4()) for _ in documents]

        contents = [doc["content"] for doc in documents]

        doc_metadata = []
        for i, doc in enumerate(documents):
            meta = doc.get("metadata", {})
            meta["_collection"] = collection_name  # 标记来源知识库
            if metadata and i < len(metadata):
                meta.update(metadata[i])
            doc_metadata.append(meta)

        embeddings = await self._embedding_service.embed_texts(contents)

        collection.add(
            embeddings=embeddings,
            documents=contents,
            metadatas=doc_metadata if doc_metadata else None,
            ids=ids
        )

        logger.info(f"添加 {len(documents)} 个文档到知识库 [{collection_name}]")
        return ids

    async def search(
        self,
        query: str,
        collection_name: Optional[str] = None,
        top_k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """搜索指定知识库"""
        if not self._initialized:
            raise RuntimeError("RAG 服务未初始化")

        collection_name = collection_name or self._default_collection_name
        collection = self._get_collection(collection_name)

        embeddings = await self._embedding_service.embed_texts([query])

        results = collection.query(
            query_embeddings=embeddings,
            n_results=top_k,
            where=filter_metadata,
            include=["documents", "metadatas", "distances"]
        )

        search_results = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                search_results.append({
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0.0
                })

        return search_results

    async def search_multi_collection(
        self,
        query: str,
        collection_names: Optional[List[str]] = None,
        top_k: int = 5
    ) -> Dict[str, List[Dict[str, Any]]]:
        """在多个知识库中搜索"""
        if not self._initialized:
            raise RuntimeError("RAG 服务未初始化")

        results = {}
        collections_to_search = collection_names or list(self._collections.keys())

        for coll_name in collections_to_search:
            try:
                coll_results = await self.search(
                    query=query,
                    collection_name=coll_name,
                    top_k=top_k
                )
                if coll_results:
                    results[coll_name] = coll_results
            except Exception as e:
                logger.error(f"搜索知识库 [{coll_name}] 失败: {e}")

        return results

    async def get_relevant_context(
        self,
        query: str,
        collection_name: Optional[str] = None,
        context_length: int = 3,
        similarity_threshold: float = 0.5
    ) -> str:
        """获取相关上下文"""
        results = await self.search(
            query=query,
            collection_name=collection_name,
            top_k=context_length
        )

        filtered = [
            r for r in results
            if r["distance"] < (1 - similarity_threshold)
        ]

        if not filtered:
            return ""

        contexts = []
        for r in filtered:
            meta = r.get("metadata", {})
            source = meta.get("source", collection_name or "未知来源")
            content = r["content"]
            contexts.append(f"[来源: {source}]\n{content}")

        return "\n\n".join(contexts)

    async def delete_documents(self, ids: List[str], collection_name: Optional[str] = None) -> None:
        """删除指定知识库中的文档"""
        if not self._initialized:
            raise RuntimeError("RAG 服务未初始化")

        collection_name = collection_name or self._default_collection_name
        collection = self._get_collection(collection_name)

        collection.delete(ids=ids)
        logger.info(f"从知识库 [{collection_name}] 删除 {len(ids)} 个文档")

    async def clear_collection(self, collection_name: Optional[str] = None) -> None:
        """清空指定知识库"""
        if not self._initialized:
            raise RuntimeError("RAG 服务未初始化")

        collection_name = collection_name or self._default_collection_name

        if collection_name in self._collections:
            self._client.delete_collection(name=collection_name)
            del self._collections[collection_name]

        # 重新创建空集合
        self._collections[collection_name] = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"description": f"Knowledge Base: {collection_name}"}
        )
        logger.info(f"知识库 [{collection_name}] 已清空")

    def list_collections(self) -> List[str]:
        """列出所有知识库"""
        if not self._initialized:
            return []
        return list(self._collections.keys())

    def count(self, collection_name: Optional[str] = None) -> int:
        """获取指定知识库文档数量"""
        if not self._initialized:
            return 0

        collection_name = collection_name or self._default_collection_name
        if collection_name not in self._collections:
            return 0
        return self._collections[collection_name].count()

    def get_all_stats(self) -> Dict[str, int]:
        """获取所有知识库统计"""
        if not self._initialized:
            return {}
        return {coll_name: coll.count() for coll_name, coll in self._collections.items()}

    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized


# 全局单例
rag_service = RAGService.get_instance()