"""WeChat callback endpoint for message reception."""
from fastapi import APIRouter, HTTPException

from app.models.schemas import MessageCallbackRequest, MessageCallbackResponse
from app.services.message_handler import message_handler

router = APIRouter()


@router.post("/callback", response_model=MessageCallbackResponse)
async def receive_message(request: MessageCallbackRequest) -> MessageCallbackResponse:
    """Receive and process WeChat message callbacks.

    This endpoint is called by the WCF client when messages are received.
    It handles auto-replies and returns the response.

    Args:
        request: Message callback request with wxid, content, etc.

    Returns:
        MessageCallbackResponse with optional auto-reply.
    """
    try:
        response = await message_handler.handle_callback_request(request)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))