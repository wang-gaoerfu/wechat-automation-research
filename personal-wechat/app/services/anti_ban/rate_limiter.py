"""Rate limiter for anti-ban protection."""
import asyncio
from datetime import datetime, timedelta
from typing import Optional

from loguru import logger

from app.config import settings


class RateLimiter:
    """Rate limiter to prevent excessive messaging.

    Implements:
    - Daily message limit
    - Minimum interval between messages
    - Rest hours (no messages during 2-6 AM by default)
    """

    def __init__(
        self,
        daily_limit: int = None,
        min_interval: int = None,
        rest_start: int = None,
        rest_end: int = None,
    ):
        """Initialize the rate limiter.

        Args:
            daily_limit: Maximum messages per day.
            min_interval: Minimum seconds between messages.
            rest_start: Start hour of rest period (0-23).
            rest_end: End hour of rest period (0-23).
        """
        self.daily_limit = daily_limit or settings.anti_ban.daily_message_limit
        self.min_interval = min_interval or settings.anti_ban.min_send_interval
        self.rest_start = rest_start or settings.anti_ban.rest_hours.start
        self.rest_end = rest_end or settings.anti_ban.rest_hours.end

        self._sent_today = 0
        self._last_sent_time: Optional[datetime] = None
        self._reset_date: str = datetime.now().strftime("%Y-%m-%d")
        self._lock = asyncio.Lock()

    def _check_and_reset_daily_count(self) -> None:
        """Reset daily count if it's a new day."""
        today = datetime.now().strftime("%Y-%m-%d")
        if today != self._reset_date:
            self._sent_today = 0
            self._reset_date = today
            logger.debug("Daily message count reset")

    def is_in_rest_period(self) -> bool:
        """Check if current time is in the rest period.

        Returns:
            True if in rest period, False otherwise.
        """
        current_hour = datetime.now().hour
        if self.rest_start < self.rest_end:
            # Normal range (e.g., 2-6)
            return self.rest_start <= current_hour < self.rest_end
        else:
            # Wraps around midnight (e.g., 22-6)
            return current_hour >= self.rest_start or current_hour < self.rest_end

    def can_send(self) -> tuple[bool, str]:
        """Check if a message can be sent.

        Returns:
            Tuple of (can_send, reason_if_not).
        """
        self._check_and_reset_daily_count()

        if self.is_in_rest_period():
            return False, f"Rest period ({self.rest_start}:00-{self.rest_end}:00)"

        if self._sent_today >= self.daily_limit:
            return False, f"Daily limit ({self.daily_limit}) reached"

        if self._last_sent_time:
            elapsed = (datetime.now() - self._last_sent_time).total_seconds()
            if elapsed < self.min_interval:
                wait_time = self.min_interval - elapsed
                return False, f"Interval too short, wait {wait_time:.0f}s"

        return True, ""

    async def acquire(self, timeout: float = 60.0) -> bool:
        """Acquire permission to send a message.

        Blocks until permission is granted or timeout exceeded.

        Args:
            timeout: Maximum seconds to wait.

        Returns:
            True if permission acquired, False if timeout.
        """
        async with self._lock:
            start_time = datetime.now()

            while True:
                can_send, reason = self.can_send()
                if can_send:
                    return True

                if (datetime.now() - start_time).total_seconds() >= timeout:
                    logger.warning(f"Rate limiter timeout: {reason}")
                    return False

                # Wait a bit before checking again
                await asyncio.sleep(1)

    async def record_sent(self) -> None:
        """Record a successful message send."""
        async with self._lock:
            self._check_and_reset_daily_count()
            self._sent_today += 1
            self._last_sent_time = datetime.now()
            logger.debug(
                f"Message sent. Daily: {self._sent_today}/{self.daily_limit}, "
                f"Interval: {self.min_interval}s"
            )

    def get_status(self) -> dict:
        """Get current rate limiter status.

        Returns:
            Dictionary with current status.
        """
        self._check_and_reset_daily_count()
        remaining = max(0, self.daily_limit - self._sent_today)

        next_available = None
        if self._last_sent_time:
            elapsed = (datetime.now() - self._last_sent_time).total_seconds()
            if elapsed < self.min_interval:
                next_available = self.min_interval - elapsed

        return {
            "daily_limit": self.daily_limit,
            "sent_today": self._sent_today,
            "remaining": remaining,
            "min_interval": self.min_interval,
            "rest_hours": f"{self.rest_start}:00-{self.rest_end}:00",
            "is_in_rest": self.is_in_rest_period(),
            "next_available_seconds": next_available,
        }


# Global rate limiter instance
rate_limiter = RateLimiter()