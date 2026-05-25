"""Database configuration and session management."""
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

# Create async engine
engine = create_async_engine(
    settings.database.url.replace("sqlite:///", "sqlite+aiosqlite:///"),
    echo=settings.app.debug,
    future=True,
)

# Create async session factory
AsyncSessionLocal = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()


async def init_db() -> None:
    """Initialize the database, creating all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency to get database session.

    Yields:
        AsyncSession: Database session.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for database session.

    Yields:
        AsyncSession: Database session.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


class MessageRepository:
    """Repository for message storage and retrieval."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_message(
        self,
        wxid: str,
        content: str,
        msg_id: str,
        msg_type: int,
        direction: str = "received",
    ) -> None:
        """Save a message to the database.

        Args:
            wxid: Sender/recipient WeChat ID.
            content: Message content.
            msg_id: Unique message ID.
            msg_type: Message type.
            direction: 'received' or 'sent'.
        """
        from app.db.models import Message  # noqa: F401

        await self.session.execute(
            text(
                """
                INSERT INTO messages (wxid, content, msg_id, msg_type, direction, created_at)
                VALUES (:wxid, :content, :msg_id, :msg_type, :direction, datetime('now'))
                """
            ),
            {"wxid": wxid, "content": content, "msg_id": msg_id, "msg_type": msg_type, "direction": direction},
        )

    async def get_messages(
        self,
        wxid: str,
        limit: int = 100,
        offset: int = 0,
    ) -> list:
        """Get messages for a specific contact.

        Args:
            wxid: WeChat ID.
            limit: Maximum number of messages to return.
            offset: Number of messages to skip.

        Returns:
            List of message records.
        """
        result = await self.session.execute(
            text(
                """
                SELECT * FROM messages
                WHERE wxid = :wxid
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
                """
            ),
            {"wxid": wxid, "limit": limit, "offset": offset},
        )
        return result.fetchall()


class ContactRepository:
    """Repository for contact storage and retrieval."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def save_contact(
        self,
        wxid: str,
        name: str,
        remark: str = None,
        country: str = None,
        province: str = None,
        city: str = None,
        avatar: str = None,
    ) -> None:
        """Save or update a contact.

        Args:
            wxid: WeChat ID.
            name: Contact name.
            remark: Remark/alias.
            country: Country.
            province: Province/State.
            city: City.
            avatar: Avatar URL or path.
        """
        await self.session.execute(
            text(
                """
                INSERT OR REPLACE INTO contacts (wxid, name, remark, country, province, city, avatar, updated_at)
                VALUES (:wxid, :name, :remark, :country, :province, :city, :avatar, datetime('now'))
                """
            ),
            {
                "wxid": wxid,
                "name": name,
                "remark": remark,
                "country": country,
                "province": province,
                "city": city,
                "avatar": avatar,
            },
        )

    async def get_contact(self, wxid: str) -> dict:
        """Get a contact by wxid.

        Args:
            wxid: WeChat ID.

        Returns:
            Contact record as dict.
        """
        result = await self.session.execute(
            text("SELECT * FROM contacts WHERE wxid = :wxid"),
            {"wxid": wxid},
        )
        row = result.fetchone()
        if row:
            return dict(row._mapping)
        return None

    async def get_all_contacts(self) -> list:
        """Get all contacts.

        Returns:
            List of contact records.
        """
        result = await self.session.execute(text("SELECT * FROM contacts ORDER BY name"))
        return list(result.fetchall())