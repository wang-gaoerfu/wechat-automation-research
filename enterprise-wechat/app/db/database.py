"""数据库连接管理"""
import logging
from typing import AsyncGenerator

import aiosqlite

from app.config import get_config

logger = logging.getLogger(__name__)


async def get_db() -> AsyncGenerator:
    """获取数据库连接"""
    config = get_config()
    db_url = config.database.url

    # 解析 SQLAlchemy URL
    db_path = db_url.replace("sqlite:///", "")
    if db_path.startswith("./"):
        db_path = db_path[2:]

    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row
    try:
        yield conn
    finally:
        await conn.close()


async def init_db():
    """初始化数据库"""
    config = get_config()
    db_url = config.database.url

    db_path = db_url.replace("sqlite:///", "")
    if db_path.startswith("./"):
        db_path = db_path[2:]

    async with aiosqlite.connect(db_path) as conn:
        # 创建消息记录表
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                msg_type TEXT NOT NULL,
                content TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                sent_at TIMESTAMP
            )
        """)

        # 创建客户记录表
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS customers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                external_userid TEXT UNIQUE NOT NULL,
                user_id TEXT NOT NULL,
                name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 创建标签记录表
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tag_id TEXT UNIQUE NOT NULL,
                tag_name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 创建群发记录表
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS group_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                send_date DATE NOT NULL,
                send_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(send_date)
            )
        """)

        await conn.commit()
        logger.info(f"数据库初始化完成: {db_path}")