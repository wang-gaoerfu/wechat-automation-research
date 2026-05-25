"""Behavior simulator for mimicking human-like patterns."""
import asyncio
import random
import time
from typing import Any, Callable, Coroutine


class BehaviorSimulator:
    """Simulates human behavior patterns to avoid detection.

    Implements typing delays, reading delays, and irregular patterns.
    """

    def __init__(
        self,
        minTypingDelay: float = 2.0,
        maxTypingDelay: float = 8.0,
        minReadingDelay: float = 3.0,
        maxReadingDelay: float = 10.0,
    ):
        """Initialize the behavior simulator.

        Args:
            minTypingDelay: Minimum typing delay in seconds.
            maxTypingDelay: Maximum typing delay in seconds.
            minReadingDelay: Minimum reading delay in seconds.
            maxReadingDelay: Maximum reading delay in seconds.
        """
        self.minTypingDelay = minTypingDelay
        self.maxTypingDelay = maxTypingDelay
        self.minReadingDelay = minReadingDelay
        self.maxReadingDelay = maxReadingDelay

    def random_typing_delay(self) -> float:
        """Get a random typing delay.

        Returns:
            Random delay in seconds.
        """
        return random.uniform(self.minTypingDelay, self.maxTypingDelay)

    def random_reading_delay(self) -> float:
        """Get a random reading delay.

        Returns:
            Random delay in seconds.
        """
        return random.uniform(self.minReadingDelay, self.maxReadingDelay)

    async def simulate_typing(
        self,
        action: Callable[..., Coroutine[Any, Any, Any]],
        *args,
        **kwargs,
    ) -> Any:
        """Simulate human typing delay before an action.

        Args:
            action: Async function to execute after delay.
            *args: Positional arguments for the action.
            **kwargs: Keyword arguments for the action.

        Returns:
            Result of the action.
        """
        delay = self.random_typing_delay()
        await asyncio.sleep(delay)
        return await action(*args, **kwargs)

    def simulate_typing_sync(
        self,
        action: Callable,
        *args,
        **kwargs,
    ) -> Any:
        """Simulate human typing delay before a sync action.

        Args:
            action: Function to execute after delay.
            *args: Positional arguments for the action.
            **kwargs: Keyword arguments for the action.

        Returns:
            Result of the action.
        """
        delay = self.random_typing_delay()
        time.sleep(delay)
        return action(*args, **kwargs)

    async def simulate_reading(
        self,
        content_length: int,
        action: Callable[..., Coroutine[Any, Any, Any]],
        *args,
        **kwargs,
    ) -> Any:
        """Simulate human reading delay based on content length.

        Args:
            content_length: Length of content being read.
            action: Async function to execute after delay.
            *args: Positional arguments for the action.
            **kwargs: Keyword arguments for the action.

        Returns:
            Result of the action.
        """
        # Base reading time + time proportional to content length
        base_delay = self.random_reading_delay()
        content_delay = content_length * 0.05  # ~50ms per character
        total_delay = base_delay + content_delay
        await asyncio.sleep(total_delay)
        return await action(*args, **kwargs)

    def generate_irregular_interval(self, base_interval: float) -> float:
        """Generate an irregular interval with randomness.

        Args:
            base_interval: Base interval in seconds.

        Returns:
            Irregular interval with +/- 50% variation.
        """
        variation = base_interval * random.uniform(-0.5, 0.5)
        return base_interval + variation

    def should_take_break(self, messages_sent: int, period: str = "hour") -> bool:
        """Determine if a break should be taken.

        Args:
            messages_sent: Number of messages sent.
            period: Time period ('hour' or 'day').

        Returns:
            True if a break should be taken.
        """
        if period == "hour" and messages_sent > 20:
            return random.random() < 0.3
        elif period == "day" and messages_sent > 100:
            return random.random() < 0.5
        return False


# Global behavior simulator instance
behavior_simulator = BehaviorSimulator()