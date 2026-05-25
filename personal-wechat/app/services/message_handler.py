"""Message handler for processing incoming WeChat messages."""
import asyncio
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

from app.db.database import AsyncSessionLocal, MessageRepository
from app.models.schemas import (
    AutoReplyRule,
    MessageCallbackRequest,
    MessageCallbackResponse,
)
from app.services.anti_ban.rate_limiter import rate_limiter
from app.services.anti_ban.content_gen import content_generator
from app.services.anti_ban.behavior import behavior_simulator
from app.services.wcf_client import wcf_client


class MessageHandler:
    """Handler for incoming WeChat messages.

    Features:
    - Message reception and storage
    - Keyword-based auto-reply
    - RAG/LLM integration interface
    - Message callbacks
    """

    def __init__(self):
        self._client = wcf_client
        self._callbacks: List[Callable] = []
        self._auto_reply_rules: List[AutoReplyRule] = []
        self._llm_reply_func: Optional[Callable] = None
        self._rag_reply_func: Optional[Callable] = None
        self._enabled = True

    def set_llm_reply_func(self, func: Callable[[str, str], Coroutine[Any, Any, str]]) -> None:
        """Set the LLM reply function.

        Args:
            func: Async function that takes (wxid, message) and returns reply string.
        """
        self._llm_reply_func = func

    def set_rag_reply_func(self, func: Callable[[str, str], Coroutine[Any, Any, str]]) -> None:
        """Set the RAG reply function.

        Args:
            func: Async function that takes (wxid, message) and returns reply string.
        """
        self._rag_reply_func = func

    async def handle_message(self, message: Dict[str, Any]) -> Optional[str]:
        """Handle an incoming message.

        Args:
            message: Message dictionary with wxid, content, etc.

        Returns:
            Reply content if auto-replied, None otherwise.
        """
        if not self._enabled:
            return None

        try:
            # Extract message data
            wxid = message.get("wxid", "")
            content = message.get("content", "")
            msg_id = message.get("msg_id", "")
            msg_type = message.get("msg_type", 0)
            roomid = message.get("roomid")

            if not wxid or not content:
                return None

            # Save to database
            await self._save_message(
                wxid=wxid,
                content=content,
                msg_id=msg_id,
                msg_type=msg_type,
                direction="received",
            )

            # Notify callbacks
            await self._notify_callbacks(message)

            # Process auto-reply
            return await self._process_auto_reply(wxid, content, roomid)

        except Exception as e:
            logger.error(f"Error handling message: {e}")
            return None

    async def handle_callback_request(
        self, request: MessageCallbackRequest
    ) -> MessageCallbackResponse:
        """Handle a message callback HTTP request.

        Args:
            request: Message callback request.

        Returns:
            MessageCallbackResponse with optional reply.
        """
        message = {
            "wxid": request.wxid,
            "content": request.content,
            "msg_id": request.msg_id,
            "msg_type": request.msg_type,
            "timestamp": request.timestamp,
            "roomid": request.roomid,
        }

        reply = await self.handle_message(message)

        return MessageCallbackResponse(
            success=True,
            reply=reply,
        )

    async def _process_auto_reply(
        self,
        wxid: str,
        content: str,
        roomid: Optional[str] = None,
    ) -> Optional[str]:
        """Process auto-reply for a message.

        Args:
            wxid: Sender's WeChat ID.
            content: Message content.
            roomid: Room ID if group message.

        Returns:
            Reply content if auto-replied.
        """
        # Check keyword rules first
        for rule in self._auto_reply_rules:
            if rule.enabled and rule.keyword in content:
                reply = rule.reply
                # Apply content generation for diversity
                reply = content_generator.process(reply)
                await self._send_reply(wxid, reply, roomid)
                return reply

        # Try RAG if available
        if self._rag_reply_func:
            try:
                reply = await self._rag_reply_func(wxid, content)
                if reply:
                    reply = content_generator.process(reply)
                    await self._send_reply(wxid, reply, roomid)
                    return reply
            except Exception as e:
                logger.error(f"RAG reply error: {e}")

        # Try LLM if available
        if self._llm_reply_func:
            try:
                reply = await self._llm_reply_func(wxid, content)
                if reply:
                    reply = content_generator.process(reply)
                    await self._send_reply(wxid, reply, roomid)
                    return reply
            except Exception as e:
                logger.error(f"LLM reply error: {e}")

        return None

    async def _send_reply(
        self,
        wxid: str,
        content: str,
        roomid: Optional[str] = None,
    ) -> None:
        """Send a reply message.

        Args:
            wxid: Recipient's WeChat ID.
            content: Reply content.
            roomid: Room ID if group message.
        """
        # Check rate limit before sending
        can_send, reason = rate_limiter.can_send()
        if not can_send:
            logger.warning(f"Cannot send reply: {reason}")
            return

        await rate_limiter.acquire()

        try:
            target_wxid = roomid if roomid else wxid
            await behavior_simulator.simulate_typing(
                self._client.send_text, target_wxid, content
            )
            await rate_limiter.record_sent()

            # Save sent message
            await self._save_message(
                wxid=target_wxid,
                content=content,
                msg_id=f"reply_{datetime.now().timestamp()}",
                msg_type=1,
                direction="sent",
            )

            logger.debug(f"Sent reply to {target_wxid}: {content[:50]}...")
        except Exception as e:
            logger.error(f"Failed to send reply: {e}")

    async def _save_message(
        self,
        wxid: str,
        content: str,
        msg_id: str,
        msg_type: int,
        direction: str,
    ) -> None:
        """Save a message to the database.

        Args:
            wxid: WeChat ID.
            content: Message content.
            msg_id: Message ID.
            msg_type: Message type.
            direction: 'received' or 'sent'.
        """
        try:
            async with AsyncSessionLocal() as session:
                repo = MessageRepository(session)
                await repo.save_message(
                    wxid=wxid,
                    content=content,
                    msg_id=msg_id,
                    msg_type=msg_type,
                    direction=direction,
                )
        except Exception as e:
            logger.error(f"Failed to save message: {e}")

    async def _notify_callbacks(self, message: Dict[str, Any]) -> None:
        """Notify registered callbacks of a message.

        Args:
            message: Message dictionary.
        """
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    callback(message)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    def register_callback(self, callback: Callable) -> None:
        """Register a callback for received messages.

        Args:
            callback: Async function to call with message data.
        """
        self._callbacks.append(callback)

    def add_auto_reply_rule(self, keyword: str, reply: str, enabled: bool = True) -> None:
        """Add an auto-reply rule.

        Args:
            keyword: Keyword to match.
            reply: Reply content.
            enabled: Whether the rule is enabled.
        """
        rule = AutoReplyRule(keyword=keyword, reply=reply, enabled=enabled)
        self._auto_reply_rules.append(rule)

    def remove_auto_reply_rule(self, keyword: str) -> bool:
        """Remove an auto-reply rule.

        Args:
            keyword: Keyword of the rule to remove.

        Returns:
            True if rule was removed.
        """
        for i, rule in enumerate(self._auto_reply_rules):
            if rule.keyword == keyword:
                del self._auto_reply_rules[i]
                return True
        return False

    def get_auto_reply_rules(self) -> List[AutoReplyRule]:
        """Get all auto-reply rules.

        Returns:
            List of AutoReplyRule objects.
        """
        return self._auto_reply_rules.copy()


# Global message handler instance
message_handler = MessageHandler()