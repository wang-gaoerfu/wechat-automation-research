"""Models 模块"""
from app.models.schemas import (
    SendTextRequest,
    SendMarkdownRequest,
    SendGroupMessageRequest,
    CreateContactQrRequest,
    GetCustomerListRequest,
    AddTagRequest
)

__all__ = [
    "SendTextRequest",
    "SendMarkdownRequest",
    "SendGroupMessageRequest",
    "CreateContactQrRequest",
    "GetCustomerListRequest",
    "AddTagRequest"
]