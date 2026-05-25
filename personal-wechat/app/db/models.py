"""SQLAlchemy models for the database."""
from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String, Text

from app.db.database import Base


class Message(Base):
    """Message model for storing chat messages."""

    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    wxid = Column(String(100), nullable=False, index=True)
    content = Column(Text, nullable=False)
    msg_id = Column(String(100), unique=True, nullable=False)
    msg_type = Column(Integer, nullable=False)
    direction = Column(String(20), nullable=False)  # 'received' or 'sent'
    created_at = Column(DateTime, default=datetime.now())


class Contact(Base):
    """Contact model for storing WeChat contacts."""

    __tablename__ = "contacts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    wxid = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    remark = Column(String(255))
    country = Column(String(50))
    province = Column(String(50))
    city = Column(String(50))
    avatar = Column(String(500))
    updated_at = Column(DateTime, default=datetime.now(), onupdate=datetime.now())


class AutoReplyRule(Base):
    """Auto-reply rule model."""

    __tablename__ = "auto_reply_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    keyword = Column(String(255), nullable=False, unique=True)
    reply = Column(Text, nullable=False)
    enabled = Column(Integer, default=1)  # 1 = enabled, 0 = disabled
    created_at = Column(DateTime, default=datetime.now())