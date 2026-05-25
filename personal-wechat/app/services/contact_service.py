"""Contact service for managing WeChat contacts."""
from typing import Dict, List, Optional

from loguru import logger

from app.db.database import AsyncSessionLocal, ContactRepository
from app.models.schemas import ContactInfo
from app.services.wcf_client import wcf_client


class ContactService:
    """Service for managing contacts.

    Provides contact retrieval, caching, and synchronization.
    """

    def __init__(self):
        self._client = wcf_client
        self._cache: Dict[str, ContactInfo] = {}
        self._cache_enabled = True

    async def get_contact_list(self, use_cache: bool = True) -> List[ContactInfo]:
        """Get the contact list.

        Args:
            use_cache: Whether to use cached contacts.

        Returns:
            List of ContactInfo objects.
        """
        if use_cache and self._cache:
            return list(self._cache.values())

        try:
            contacts_data = await self._client.get_contacts()
            contacts = []

            for c in contacts_data:
                contact = ContactInfo(
                    wxid=c.get("wxid", ""),
                    name=c.get("name", ""),
                    remark=c.get("remark"),
                    country=c.get("country"),
                    province=c.get("province"),
                    city=c.get("city"),
                    avatar=c.get("avatar"),
                )
                contacts.append(contact)
                self._cache[contact.wxid] = contact

            logger.info(f"Retrieved {len(contacts)} contacts")
            return contacts

        except Exception as e:
            logger.error(f"Failed to get contacts: {e}")
            return []

    async def get_contact(self, wxid: str) -> Optional[ContactInfo]:
        """Get a specific contact by wxid.

        Args:
            wxid: Contact's WeChat ID.

        Returns:
            ContactInfo if found, None otherwise.
        """
        # Check cache first
        if self._cache_enabled and wxid in self._cache:
            return self._cache[wxid]

        try:
            contact_data = await self._client.get_contact_info(wxid)
            if contact_data:
                contact = ContactInfo(
                    wxid=contact_data.get("wxid", wxid),
                    name=contact_data.get("name", ""),
                    remark=contact_data.get("remark"),
                    country=contact_data.get("country"),
                    province=contact_data.get("province"),
                    city=contact_data.get("city"),
                    avatar=contact_data.get("avatar"),
                )
                self._cache[wxid] = contact
                return contact
        except Exception as e:
            logger.error(f"Failed to get contact {wxid}: {e}")

        return None

    async def sync_to_database(self) -> int:
        """Synchronize contacts to the database.

        Returns:
            Number of contacts synced.
        """
        contacts = await self.get_contact_list(use_cache=False)
        synced = 0

        async with AsyncSessionLocal() as session:
            repo = ContactRepository(session)
            for contact in contacts:
                try:
                    await repo.save_contact(
                        wxid=contact.wxid,
                        name=contact.name,
                        remark=contact.remark,
                        country=contact.country,
                        province=contact.province,
                        city=contact.city,
                        avatar=contact.avatar,
                    )
                    synced += 1
                except Exception as e:
                    logger.error(f"Failed to sync contact {contact.wxid}: {e}")

        logger.info(f"Synced {synced} contacts to database")
        return synced

    async def get_db_contacts(self) -> List[Dict]:
        """Get contacts from the database.

        Returns:
            List of contact dictionaries from database.
        """
        async with AsyncSessionLocal() as session:
            repo = ContactRepository(session)
            return await repo.get_all_contacts()

    def clear_cache(self) -> None:
        """Clear the contact cache."""
        self._cache.clear()
        logger.debug("Contact cache cleared")


# Global contact service instance
contact_service = ContactService()