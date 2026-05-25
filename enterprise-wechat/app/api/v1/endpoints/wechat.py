"""微信回调接口"""
import logging
from typing import Dict, Any

from fastapi import APIRouter, Request, Query, Body, HTTPException
from fastapi.responses import PlainTextResponse

from app.services.callback_handler import CallbackHandler

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/callback")
async def verify_callback(
    msg_signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...)
):
    """企业微信回调验证（GET 请求）"""
    try:
        handler = CallbackHandler()
        result = handler.verify_url(msg_signature, timestamp, nonce, echostr)
        return PlainTextResponse(content=result)
    except Exception as e:
        logger.error(f"回调验证失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/callback")
async def handle_callback(
    msg_signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    body: Dict[str, Any] = Body(...)
):
    """处理企业微信回调事件（POST 请求）"""
    try:
        handler = CallbackHandler()
        result = handler.handle_callback(msg_signature, timestamp, nonce, body)
        return {"status": "ok", "result": result}
    except Exception as e:
        logger.error(f"回调处理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))