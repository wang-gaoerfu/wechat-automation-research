"""WeChatFerry client wrapper for RPC communication."""
import asyncio
from typing import Any, Callable, Dict, List, Optional

from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings


class WCFClient:
    """WeChatFerry RPC client wrapper.

    Provides async wrapper around the WeChatFerry RPC calls.
    """

    def __init__(self, host: str = None, port: int = None):
        """Initialize the WCF client.

        Args:
            host: WCF server host.
            port: WCF server port.
        """
        self.host = host or settings.wcf.host
        self.port = port or settings.wcf.port
        self._connected = False
        self._wxid: Optional[str] = None
        self._callbacks: List[Callable] = []
        self._receive_task: Optional[asyncio.Task] = None

    @property
    def connected(self) -> bool:
        """Check if the client is connected."""
        return self._connected

    @property
    def wxid(self) -> Optional[str]:
        """Get the current WeChat ID."""
        return self._wxid

    async def connect(self) -> bool:
        """Connect to the WCF server.

        Returns:
            True if connection successful, False otherwise.
        """
        try:
            # Import here to avoid circular imports
            from wechatferry import WeChatFerry

            self._client = WeChatFerry(self.host, self.port)
            self._connected = True
            logger.info(f"Connected to WCF at {self.host}:{self.port}")

            # Get current wxid
            try:
                self._wxid = await self.get_self_wxid()
            except Exception:
                pass

            return True
        except Exception as e:
            logger.error(f"Failed to connect to WCF: {e}")
            self._connected = False
            return False

    async def disconnect(self) -> None:
        """Disconnect from the WCF server."""
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
        self._connected = False
        logger.info("Disconnected from WCF")

    def register_callback(self, callback: Callable) -> None:
        """Register a callback for received messages.

        Args:
            callback: Async function to call with message data.
        """
        self._callbacks.append(callback)

    async def _notify_callbacks(self, message: Dict[str, Any]) -> None:
        """Notify all registered callbacks of a new message.

        Args:
            message: Message data dictionary.
        """
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(message)
                else:
                    callback(message)
            except Exception as e:
                logger.error(f"Error in message callback: {e}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def _rpc_call(self, method: str, *args, **kwargs) -> Any:
        """Make an RPC call with retry logic.

        Args:
            method: RPC method name.
            *args: Positional arguments for the method.
            **kwargs: Keyword arguments for the method.

        Returns:
            Result of the RPC call.
        """
        if not self._connected:
            raise ConnectionError("Not connected to WCF server")

        try:
            func = getattr(self._client, method, None)
            if func is None:
                raise AttributeError(f"WCF method '{method}' not found")

            result = await asyncio.to_thread(func, *args, **kwargs)
            return result
        except Exception as e:
            logger.error(f"RPC call {method} failed: {e}")
            raise

    async def get_self_wxid(self) -> str:
        """Get the current WeChat ID.

        Returns:
            The wxid of the logged-in user.
        """
        result = await self._rpc_call("get_self_wxid")
        self._wxid = result
        return result

    async def send_text(
        self,
        wxid: str,
        content: str,
        aters: Optional[List[str]] = None,
    ) -> str:
        """Send a text message.

        Args:
            wxid: Recipient's WeChat ID.
            content: Message content.
            aters: List of wxids to @.

        Returns:
            Message ID if successful.
        """
        if aters:
            result = await self._rpc_call("send_text", wxid, content, ",".join(aters))
        else:
            result = await self._rpc_call("send_text", wxid, content)
        return result

    async def send_image(self, wxid: str, image_path: str) -> str:
        """Send an image message.

        Args:
            wxid: Recipient's WeChat ID.
            image_path: Path to the image file.

        Returns:
            Message ID if successful.
        """
        result = await self._rpc_call("send_image", wxid, image_path)
        return result

    async def send_file(self, wxid: str, file_path: str) -> str:
        """Send a file message.

        Args:
            wxid: Recipient's WeChat ID.
            file_path: Path to the file.

        Returns:
            Message ID if successful.
        """
        result = await self._rpc_call("send_file", wxid, file_path)
        return result

    async def get_contacts(self) -> List[Dict[str, Any]]:
        """Get the contact list.

        Returns:
            List of contact dictionaries.
        """
        result = await self._rpc_call("get_contact_list")
        if isinstance(result, str):
            import json
            return json.loads(result)
        return result or []

    async def get_contact_info(self, wxid: str) -> Dict[str, Any]:
        """Get detailed contact information.

        Args:
            wxid: Contact's WeChat ID.

        Returns:
            Contact information dictionary.
        """
        result = await self._rpc_call("get_contact_info", wxid)
        if isinstance(result, str):
            import json
            return json.loads(result)
        return result or {}

    async def send_xml(self, wxid: str, xml_content: str, msg_type: int = 1) -> str:
        """Send XML message (supports rich media links, etc).

        Args:
            wxid: Recipient's WeChat ID.
            xml_content: XML content string.
            msg_type: Message type (1=text, 3=image, etc).

        Returns:
            Message ID if successful.
        """
        result = await self._rpc_call("send_xml", wxid, xml_content, msg_type)
        return result

    async def get_dbs(self) -> List[str]:
        """Get list of databases.

        Returns:
            List of database names.
        """
        result = await self._rpc_call("get_dbs")
        return result or []

    async def get_tables(self, db_name: str) -> List[str]:
        """Get tables in a database.

        Args:
            db_name: Database name.

        Returns:
            List of table names.
        """
        result = await self._rpc_call("get_tables", db_name)
        return result or []

    async def get_db_data(self, db_name: str, table_name: str, limit: int = 100) -> List[Dict]:
        """Get data from a table.

        Args:
            db_name: Database name.
            table_name: Table name.
            limit: Maximum rows to return.

        Returns:
            List of row dictionaries.
        """
        result = await self._rpc_call("get_db_data", db_name, table_name, limit)
        if isinstance(result, str):
            import json
            return json.loads(result)
        return result or []


# Global client instance
wcf_client = WCFClient()