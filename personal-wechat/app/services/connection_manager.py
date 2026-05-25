"""Connection manager for WeChatFerry with auto-reconnect."""
import asyncio
from datetime import datetime, timedelta
from typing import Optional

from loguru import logger

from app.config import settings
from app.services.wcf_client import wcf_client


class ConnectionManager:
    """Manages WeChatFerry connection with heartbeat and auto-reconnect.

    Uses exponential backoff for reconnection attempts.
    """

    def __init__(self):
        self._client = wcf_client
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._reconnect_attempts = 0
        self._last_heartbeat: Optional[datetime] = None
        self._uptime: Optional[datetime] = None

    @property
    def connected(self) -> bool:
        """Check if connected to WCF."""
        return self._client.connected

    @property
    def uptime(self) -> Optional[int]:
        """Get uptime in seconds since connected."""
        if self._uptime:
            return int((datetime.now() - self._uptime).total_seconds())
        return None

    async def start(self) -> bool:
        """Start the connection manager.

        Returns:
            True if initial connection successful.
        """
        self._running = True
        self._uptime = None

        # Initial connection
        success = await self._client.connect()
        if success:
            self._uptime = datetime.now()
            self._reconnect_attempts = 0
            self._start_heartbeat()
            return True

        # Start reconnection loop
        self._task = asyncio.create_task(self._reconnect_loop())
        return False

    async def stop(self) -> None:
        """Stop the connection manager."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        await self._client.disconnect()
        logger.info("Connection manager stopped")

    async def _reconnect_loop(self) -> None:
        """Reconnection loop with exponential backoff."""
        while self._running and not self._client.connected:
            self._reconnect_attempts += 1
            max_attempts = settings.wcf.max_reconnect_attempts
            interval = settings.wcf.reconnect_interval

            # Exponential backoff
            wait_time = min(interval * (2 ** (self._reconnect_attempts - 1)), 300)
            logger.info(
                f"Reconnect attempt {self._reconnect_attempts}/{max_attempts} "
                f"in {wait_time} seconds"
            )

            await asyncio.sleep(wait_time)

            if not self._running:
                break

            success = await self._client.connect()
            if success:
                self._uptime = datetime.now()
                self._reconnect_attempts = 0
                self._start_heartbeat()
                logger.info("Reconnected to WCF successfully")
                return

            if self._reconnect_attempts >= max_attempts:
                logger.error(
                    f"Max reconnection attempts ({max_attempts}) reached. "
                    "Manual intervention required."
                )
                # Reset attempts to allow eventual retry after long wait
                self._reconnect_attempts = 0
                await asyncio.sleep(60)

    def _start_heartbeat(self) -> None:
        """Start the heartbeat task."""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeat to keep connection alive."""
        while self._running and self._client.connected:
            try:
                # Simple heartbeat - get self wxid to verify connection
                await asyncio.to_thread(self._client._client.get_self_wxid)
                self._last_heartbeat = datetime.now()
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Heartbeat failed: {e}")
                self._last_heartbeat = None
                # Trigger reconnection if heartbeat fails
                if self._running:
                    await self._client.disconnect()
                    self._task = asyncio.create_task(self._reconnect_loop())
                break

    async def force_reconnect(self) -> bool:
        """Force an immediate reconnection attempt.

        Returns:
            True if reconnection successful.
        """
        self._reconnect_attempts = 0
        await self._client.disconnect()
        success = await self._client.connect()
        if success:
            self._uptime = datetime.now()
            self._start_heartbeat()
        return success


# Global connection manager instance
connection_manager = ConnectionManager()