"""Contact management endpoints."""
from typing import List

from fastapi import APIRouter, HTTPException

from app.models.schemas import ContactInfo, ContactListResponse
from app.services.contact_service import contact_service

router = APIRouter()


@router.get("/list", response_model=ContactListResponse)
async def get_contact_list() -> ContactListResponse:
    """Get the contact list.

    Returns:
        ContactListResponse with list of contacts.
    """
    try:
        contacts = await contact_service.get_contact_list()
        return ContactListResponse(contacts=contacts, total=len(contacts))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{wxid}", response_model=ContactInfo)
async def get_contact(wxid: str) -> ContactInfo:
    """Get a specific contact by wxid.

    Args:
        wxid: Contact's WeChat ID.

    Returns:
        ContactInfo for the specified contact.
    """
    try:
        contact = await contact_service.get_contact(wxid)
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        return contact
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync")
async def sync_contacts() -> dict:
    """Synchronize contacts to the database.

    Returns:
        Dictionary with sync status.
    """
    try:
        count = await contact_service.sync_to_database()
        return {"success": True, "synced": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))