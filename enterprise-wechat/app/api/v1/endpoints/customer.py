"""客户管理接口"""
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException

from app.models.schemas import CreateContactQrRequest, GetCustomerListRequest, AddTagRequest
from app.services.customer_service import CustomerService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/qr")
async def create_contact_qr(request: CreateContactQrRequest):
    """创建联系我二维码"""
    try:
        service = CustomerService()
        result = await service.create_contact_qr(
            scene=request.scene,
            style=request.style,
            limit=request.limit
        )
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"创建联系我二维码失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list")
async def get_customer_list(user_id: str):
    """获取客户列表"""
    try:
        service = CustomerService()
        result = await service.get_customer_list(user_id)
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"获取客户列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tag")
async def add_customer_tag(request: AddTagRequest):
    """为客户添加标签"""
    try:
        service = CustomerService()
        result = await service.add_tag(
            user_id=request.user_id,
            external_userid=request.external_userid,
            tag_id_list=request.tag_id_list
        )
        return {"status": "success", "data": result}
    except Exception as e:
        logger.error(f"添加客户标签失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))