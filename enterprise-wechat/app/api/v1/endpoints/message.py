"""消息发送接口"""
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException

from app.models.schemas import SendTextRequest, SendMarkdownRequest, SendGroupMessageRequest
from app.services.message_service import MessageService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/text")
async def send_text_message(request: SendTextRequest):
    """发送文本消息"""
    try:
        service = MessageService()
        result = await service.send_text(
            user_id=request.user_id,
            content=request.content,
            agent_id=request.agent_id
        )
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"发送文本消息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/markdown")
async def send_markdown_message(request: SendMarkdownRequest):
    """发送 Markdown 消息"""
    try:
        service = MessageService()
        result = await service.send_markdown(
            user_id=request.user_id,
            content=request.content,
            agent_id=request.agent_id
        )
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"发送 Markdown 消息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/group")
async def send_group_message(request: SendGroupMessageRequest):
    """群发消息（每日最多4次）"""
    try:
        service = MessageService()
        result = await service.send_group_message(
            user_list=request.user_list,
            content=request.content,
            agent_id=request.agent_id
        )
        return {"status": "success", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"发送群发消息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))