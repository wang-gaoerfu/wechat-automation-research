"""API v1 路由注册"""
from fastapi import APIRouter

from app.api.v1.endpoints import wechat, message, customer, system, rag, agent, knowledge

api_router = APIRouter()

# 注册各模块路由
api_router.include_router(wechat.router, prefix="/wechat", tags=["微信回调"])
api_router.include_router(message.router, prefix="/message", tags=["消息发送"])
api_router.include_router(customer.router, prefix="/customer", tags=["客户管理"])
api_router.include_router(system.router, prefix="/system", tags=["系统管理"])
api_router.include_router(rag.router, prefix="/rag", tags=["RAG知识库"])
api_router.include_router(agent.router, prefix="/agent", tags=["Agent智能助手"])
api_router.include_router(knowledge.router, prefix="/kb", tags=["知识库管理"])