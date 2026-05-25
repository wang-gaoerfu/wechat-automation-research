"""Pydantic models/schemas for Personal WeChat."""
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SendTextRequest(BaseModel):
    """Request model for sending text messages."""
    wxid: str = Field(..., description="WeChat ID of the recipient")
    content: str = Field(..., description="Message content")
    aters: Optional[List[str]] = Field(default=None, description="WXIDs to @")
    auto_python: bool = Field(default=True, description="Auto detect and execute Python code in response")


class SendImageRequest(BaseModel):
    """Request model for sending image messages."""
    wxid: str = Field(..., description="WeChat ID of the recipient")
    image_path: str = Field(..., description="Path to the image file")


class SendFileRequest(BaseModel):
    """Request model for sending file messages."""
    wxid: str = Field(..., description="WeChat ID of the recipient")
    file_path: str = Field(..., description="Path to the file")


class MessageCallbackRequest(BaseModel):
    """Request model for message callback webhook."""
    wxid: str = Field(..., description="Sender's WeChat ID")
    content: str = Field(..., description="Message content")
    msg_id: str = Field(..., description="Message ID")
    msg_type: int = Field(..., description="Message type")
    timestamp: int = Field(..., description="Unix timestamp")
    roomid: Optional[str] = Field(default=None, description="Room ID for group messages")


class MessageCallbackResponse(BaseModel):
    """Response model for message callback webhook."""
    success: bool = True
    reply: Optional[str] = Field(default=None, description="Auto-reply content")


class ContactInfo(BaseModel):
    """Contact information model."""
    wxid: str
    name: str
    remark: Optional[str] = None
    country: Optional[str] = None
    province: Optional[str] = None
    city: Optional[str] = None
    avatar: Optional[str] = None


class ContactListResponse(BaseModel):
    """Response model for contact list."""
    contacts: List[ContactInfo]
    total: int


class AutoReplyRule(BaseModel):
    """Auto-reply rule configuration."""
    keyword: str
    reply: str
    enabled: bool = True


class WCFStatusResponse(BaseModel):
    """WeChatFerry connection status."""
    connected: bool
    host: str
    port: int
    uptime: Optional[int] = None


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None


class SendTextResponse(BaseModel):
    """Response model for send text operation."""
    success: bool
    msg_id: Optional[str] = None
    error: Optional[str] = None


class SendImageResponse(BaseModel):
    """Response model for send image operation."""
    success: bool
    msg_id: Optional[str] = None
    error: Optional[str] = None