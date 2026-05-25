"""Message sending endpoints."""
from fastapi import APIRouter, HTTPException

from app.models.schemas import SendTextRequest, SendTextResponse, SendImageRequest, SendImageResponse
from app.services.wcf_client import wcf_client
from app.services.anti_ban.rate_limiter import rate_limiter
from app.services.anti_ban.content_gen import content_generator

router = APIRouter()


@router.post("/text", response_model=SendTextResponse)
async def send_text(request: SendTextRequest) -> SendTextResponse:
    """Send a text message.

    Args:
        request: SendTextRequest with wxid and content.

    Returns:
        SendTextResponse with success status and msg_id.
    """
    try:
        # Check rate limit
        can_send, reason = rate_limiter.can_send()
        if not can_send:
            return SendTextResponse(success=False, error=f"Rate limited: {reason}")

        await rate_limiter.acquire(timeout=30)

        # Process content for diversity
        content = content_generator.process(request.content)

        # Send message
        msg_id = await wcf_client.send_text(request.wxid, content, request.aters)
        await rate_limiter.record_sent()

        return SendTextResponse(success=True, msg_id=msg_id)
    except Exception as e:
        return SendTextResponse(success=False, error=str(e))


@router.post("/image", response_model=SendImageResponse)
async def send_image(request: SendImageRequest) -> SendImageResponse:
    """Send an image message.

    Args:
        request: SendImageRequest with wxid and image_path.

    Returns:
        SendImageResponse with success status and msg_id.
    """
    try:
        # Check rate limit
        can_send, reason = rate_limiter.can_send()
        if not can_send:
            return SendImageResponse(success=False, error=f"Rate limited: {reason}")

        await rate_limiter.acquire(timeout=30)

        # Send message
        msg_id = await wcf_client.send_image(request.wxid, request.image_path)
        await rate_limiter.record_sent()

        return SendImageResponse(success=True, msg_id=msg_id)
    except Exception as e:
        return SendImageResponse(success=False, error=str(e))