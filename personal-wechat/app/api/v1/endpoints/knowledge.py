"""知识库管理 API - 文件上传、文档管理"""
import os
from typing import Any, Dict, List, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from app.services.kb_manager import kb_manager
from app.services.rag_service import rag_service

router = APIRouter(prefix="/kb", tags=["知识库管理"])


class CollectionRequest(BaseModel):
    """创建/切换知识库请求"""
    name: str


class UploadRequest(BaseModel):
    """上传请求"""
    filename: str
    content: str
    collection: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class WatchPathRequest(BaseModel):
    """添加监控路径请求"""
    path: str
    collection: str
    file_types: Optional[List[str]] = None
    recursive: bool = True


class SearchRequest(BaseModel):
    """跨知识库搜索请求"""
    query: str
    collections: Optional[List[str]] = None
    top_k: int = 5


class SearchResponse(BaseModel):
    """搜索响应"""
    results: Dict[str, List[Dict[str, Any]]]
    total: int


@router.post("/upload")
async def upload_document(request: UploadRequest):
    """上传文档到知识库"""
    if not kb_manager.is_initialized():
        raise HTTPException(status_code=500, detail="知识库管理器未初始化")

    result = await kb_manager.upload_document(
        content=request.content,
        filename=request.filename,
        collection_name=request.collection,
        metadata=request.metadata
    )

    return result


@router.post("/upload/file")
async def upload_file(
    file: UploadFile = File(...),
    collection: Optional[str] = Form(None),
    path: Optional[str] = Form(None)
):
    """上传本地文件到知识库"""
    if not kb_manager.is_initialized():
        raise HTTPException(status_code=500, detail="知识库管理器未初始化")

    if path:
        result = await kb_manager.upload_file(
            file_path=path,
            collection_name=collection
        )
        return result

    content = await file.read()
    try:
        content_str = content.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="文件编码不支持，请使用 UTF-8 编码")

    result = await kb_manager.upload_document(
        content=content_str,
        filename=file.filename or "uploaded_file.txt",
        collection_name=collection
    )

    return result


@router.post("/collections/{collection}/add")
async def add_to_collection(
    collection: str,
    content: str,
    filename: str = "document.txt",
    metadata: Optional[Dict[str, Any]] = None
):
    """添加文档到指定知识库"""
    if not kb_manager.is_initialized():
        raise HTTPException(status_code=500, detail="知识库管理器未初始化")

    result = await kb_manager.upload_document(
        content=content,
        filename=filename,
        collection_name=collection,
        metadata=metadata
    )

    return result


@router.get("/collections")
async def list_collections():
    """列出所有知识库"""
    if not rag_service.is_initialized():
        raise HTTPException(status_code=500, detail="RAG 服务未初始化")

    collections = kb_manager.list_collections()
    stats = {}

    for coll in collections:
        try:
            stats[coll] = {
                "document_count": rag_service.count(coll)
            }
        except Exception:
            stats[coll] = {"document_count": 0}

    return {
        "collections": collections,
        "stats": stats
    }


@router.get("/collections/{collection}/stats")
async def get_collection_stats(collection: str):
    """获取指定知识库统计"""
    if not rag_service.is_initialized():
        raise HTTPException(status_code=500, detail="RAG 服务未初始化")

    return {
        "collection": collection,
        "document_count": rag_service.count(collection)
    }


@router.delete("/collections/{collection}")
async def delete_collection(collection: str):
    """删除知识库"""
    if not kb_manager.is_initialized():
        raise HTTPException(status_code=500, detail="知识库管理器未初始化")

    await kb_manager.delete_collection(collection)

    return {"success": True, "message": f"知识库 [{collection}] 已删除"}


@router.post("/search/multi")
async def search_multi_collection(request: SearchRequest):
    """在多个知识库中搜索"""
    if not rag_service.is_initialized():
        raise HTTPException(status_code=500, detail="RAG 服务未初始化")

    results = await rag_service.search_multi_collection(
        query=request.query,
        collection_names=request.collections,
        top_k=request.top_k
    )

    total = sum(len(r) for r in results.values())

    return SearchResponse(results=results, total=total)


@router.post("/watch")
async def add_watch_path(request: WatchPathRequest):
    """添加自动监控路径"""
    if not kb_manager.is_initialized():
        raise HTTPException(status_code=500, detail="知识库管理器未初始化")

    if not os.path.exists(request.path):
        raise HTTPException(status_code=400, detail=f"路径不存在: {request.path}")

    kb_manager.add_watch_path(
        path=request.path,
        collection_name=request.collection,
        file_types=request.file_types,
        recursive=request.recursive
    )

    return {
        "success": True,
        "message": f"开始监控路径 [{request.path}] -> 知识库 [{request.collection}]"
    }


@router.post("/watch/start")
async def start_file_watcher(interval: int = 60):
    """启动文件监控服务"""
    if not kb_manager.is_initialized():
        raise HTTPException(status_code=500, detail="知识库管理器未初始化")

    await kb_manager.start_file_watcher(interval)

    return {"success": True, "message": "文件监控服务已启动"}


@router.post("/watch/stop")
async def stop_file_watcher():
    """停止文件监控服务"""
    kb_manager.stop_file_watcher()

    return {"success": True, "message": "文件监控服务已停止"}


@router.get("/watch/status")
async def get_watch_status():
    """获取文件监控状态"""
    return {
        "running": kb_manager._file_watcher._running,
        "watched_paths": [
            {"path": config["path"], "collection": coll}
            for coll, config in kb_manager._file_watcher._watchers.items()
        ]
    }


@router.post("/documents/delete")
async def delete_documents(
    doc_ids: List[str],
    collection: Optional[str] = None
):
    """删除指定文档"""
    if not rag_service.is_initialized():
        raise HTTPException(status_code=500, detail="RAG 服务未初始化")

    await rag_service.delete_documents(ids=doc_ids, collection_name=collection)

    return {"success": True, "count": len(doc_ids)}


@router.delete("/clear")
async def clear_knowledge_base(collection: Optional[str] = None):
    """清空知识库"""
    if not rag_service.is_initialized():
        raise HTTPException(status_code=500, detail="RAG 服务未初始化")

    await rag_service.clear_collection(collection_name=collection)

    return {"success": True}