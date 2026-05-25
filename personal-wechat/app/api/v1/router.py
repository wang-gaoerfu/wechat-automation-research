"""API v1 router."""
from fastapi import APIRouter

from app.api.v1.endpoints import wechat, message, contact, system, rag, knowledge

api_router = APIRouter()

api_router.include_router(wechat.router, prefix="/wechat", tags=["wechat"])
api_router.include_router(message.router, prefix="/message", tags=["message"])
api_router.include_router(contact.router, prefix="/contact", tags=["contact"])
api_router.include_router(system.router, prefix="/system", tags=["system"])
api_router.include_router(rag.router, prefix="/rag", tags=["RAG知识库"])
api_router.include_router(knowledge.router, prefix="/kb", tags=["知识库管理"])