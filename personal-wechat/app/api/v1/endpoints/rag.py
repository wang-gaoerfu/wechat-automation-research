"""RAG 知识库 API"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.rag_service import rag_service

router = APIRouter(prefix="/rag", tags=["RAG知识库"])


class AddDocumentRequest(BaseModel):
    """添加文档请求"""
    content: str
    source: Optional[str] = "manual"
    category: Optional[str] = "general"
    metadata: Optional[Dict[str, Any]] = None


class AddDocumentsRequest(BaseModel):
    """批量添加文档请求"""
    documents: List[Dict[str, Any]]


class SearchRequest(BaseModel):
    """搜索请求"""
    query: str
    top_k: Optional[int] = 5
    filter_metadata: Optional[Dict[str, Any]] = None


class SearchResponse(BaseModel):
    """搜索响应"""
    results: List[Dict[str, Any]]
    count: int


@router.post("/documents", response_model=Dict[str, Any])
async def add_document(request: AddDocumentRequest):
    """添加单个文档到知识库"""
    if not rag_service.is_initialized():
        raise HTTPException(status_code=500, detail="RAG 服务未初始化")

    doc = {
        "content": request.content,
        "metadata": request.metadata or {"source": request.source, "category": request.category}
    }
    doc_id = await rag_service.add_documents([doc])

    return {"success": True, "doc_id": doc_id[0]}


@router.post("/documents/batch", response_model=Dict[str, Any])
async def add_documents_batch(request: AddDocumentsRequest):
    """批量添加文档到知识库"""
    if not rag_service.is_initialized():
        raise HTTPException(status_code=500, detail="RAG 服务未初始化")

    doc_ids = await rag_service.add_documents(request.documents)

    return {"success": True, "count": len(doc_ids), "doc_ids": doc_ids}


@router.post("/search", response_model=SearchResponse)
async def search_knowledge(request: SearchRequest):
    """搜索知识库"""
    if not rag_service.is_initialized():
        raise HTTPException(status_code=500, detail="RAG 服务未初始化")

    results = await rag_service.search(
        query=request.query,
        top_k=request.top_k,
        filter_metadata=request.filter_metadata
    )

    return SearchResponse(results=results, count=len(results))


@router.get("/context/{query}")
async def get_context(query: str, context_length: int = 3, similarity_threshold: float = 0.5):
    """获取相关上下文"""
    if not rag_service.is_initialized():
        raise HTTPException(status_code=500, detail="RAG 服务未初始化")

    context = await rag_service.get_relevant_context(
        query=query,
        context_length=context_length,
        similarity_threshold=similarity_threshold
    )

    return {"context": context}


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """删除文档"""
    if not rag_service.is_initialized():
        raise HTTPException(status_code=500, detail="RAG 服务未初始化")

    await rag_service.delete_documents([doc_id])

    return {"success": True}


@router.delete("/clear")
async def clear_knowledge_base():
    """清空知识库"""
    if not rag_service.is_initialized():
        raise HTTPException(status_code=500, detail="RAG 服务未初始化")

    await rag_service.clear()

    return {"success": True}


@router.get("/stats")
async def get_stats():
    """获取知识库统计"""
    if not rag_service.is_initialized():
        raise HTTPException(status_code=500, detail="RAG 服务未初始化")

    return {
        "document_count": rag_service.count(),
        "initialized": True
    }