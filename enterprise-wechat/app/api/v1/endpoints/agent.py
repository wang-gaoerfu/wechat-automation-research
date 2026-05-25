"""Agent 智能助手 API"""
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.agent_service import agent_service
from app.services.llm_service import llm_service, Message

router = APIRouter(prefix="/agent", tags=["Agent智能助手"])


class ChatRequest(BaseModel):
    """对话请求"""
    message: str
    user_id: Optional[str] = ""
    use_rag: Optional[bool] = True
    history: Optional[List[Dict[str, str]]] = None


class ChatResponse(BaseModel):
    """对话响应"""
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None


class ToolCallRequest(BaseModel):
    """工具调用请求"""
    tool_name: str
    arguments: Dict[str, Any]


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """与智能助手对话"""
    if not agent_service.is_initialized():
        raise HTTPException(status_code=500, detail="Agent 服务未初始化")

    # 转换 history 格式
    history_messages = None
    if request.history:
        history_messages = [
            Message(role=msg["role"], content=msg["content"])
            for msg in request.history
        ]

    response = await agent_service.process_message(
        user_message=request.message,
        user_id=request.user_id,
        use_rag=request.use_rag,
        conversation_history=history_messages
    )

    return ChatResponse(
        content=response.content,
        tool_calls=[{"tool_name": tc.tool_name, "arguments": tc.arguments} for tc in response.tool_calls]
    )


@router.get("/tools")
async def get_available_tools():
    """获取所有可用工具"""
    if not agent_service.is_initialized():
        raise HTTPException(status_code=500, detail="Agent 服务未初始化")

    tools = agent_service.get_available_tools()
    return {"tools": tools}


@router.post("/llm/chat")
async def llm_chat(message: str, system_prompt: Optional[str] = ""):
    """直接调用 LLM（不经过 Agent）"""
    if not llm_service.is_initialized():
        raise HTTPException(status_code=500, detail="LLM 服务未初始化")

    response = await llm_service.chat(
        user_message=message,
        system_prompt=system_prompt
    )

    return {"response": response}


@router.get("/status")
async def get_status():
    """获取 Agent 服务状态"""
    from app.services.rag_service import rag_service

    return {
        "agent_initialized": agent_service.is_initialized(),
        "llm_initialized": llm_service.is_initialized(),
        "rag_initialized": rag_service.is_initialized(),
        "llm_provider": llm_service.provider_type if llm_service.is_initialized() else None,
    }