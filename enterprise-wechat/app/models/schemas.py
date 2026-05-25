"""Pydantic 模型定义"""
from typing import List, Optional

from pydantic import BaseModel, Field


class SendTextRequest(BaseModel):
    """发送文本消息请求"""
    user_id: str = Field(..., description="目标用户ID")
    content: str = Field(..., min_length=1, max_length=2048, description="消息内容")
    agent_id: Optional[str] = Field(None, description="应用AgentID，默认使用配置中的AgentID")


class SendMarkdownRequest(BaseModel):
    """发送 Markdown 消息请求"""
    user_id: str = Field(..., description="目标用户ID")
    content: str = Field(..., min_length=1, max_length=2048, description="Markdown 内容")
    agent_id: Optional[str] = Field(None, description="应用AgentID")


class SendGroupMessageRequest(BaseModel):
    """群发消息请求"""
    user_list: List[str] = Field(..., min_length=1, description="用户ID列表")
    content: str = Field(..., min_length=1, max_length=2048, description="消息内容")
    agent_id: Optional[str] = Field(None, description="应用AgentID")


class CreateContactQrRequest(BaseModel):
    """创建联系我二维码请求"""
    scene: str = Field(..., description="场景值，用于统计")
    style: int = Field(1, description="二维码样式")
    limit: int = Field(1, ge=1, le=100, description="限制扫码次数")


class GetCustomerListRequest(BaseModel):
    """获取客户列表请求"""
    user_id: str = Field(..., description="员工ID")


class AddTagRequest(BaseModel):
    """为客户添加标签请求"""
    user_id: str = Field(..., description="员工ID")
    external_userid: str = Field(..., description="客户ID")
    tag_id_list: List[str] = Field(..., min_length=1, description="标签ID列表")


class MessageResponse(BaseModel):
    """消息响应"""
    status: str
    data: Optional[dict] = None
    error: Optional[str] = None


class CustomerResponse(BaseModel):
    """客户响应"""
    status: str
    data: Optional[dict] = None
    error: Optional[str] = None