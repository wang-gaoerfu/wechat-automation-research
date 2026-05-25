"""Tests for rate limiter."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch


class TestRateLimiter:
    """Test cases for RateLimiter."""

    @pytest.fixture
    def rate_limiter(self):
        """Create a RateLimiter instance for testing."""
        from app.services.anti_ban.rate_limiter import RateLimiter
        return RateLimiter(
            daily_limit=100,
            min_interval=5,
            rest_start=2,
            rest_end=6,
        )

    def test_can_send_within_limits(self, rate_limiter):
        """Test sending within limits."""
        can_send, reason = rate_limiter.can_send()
        # Note: This might fail if during rest hours
        if not rate_limiter.is_in_rest_period():
            assert can_send is True
            assert reason == ""

    def test_daily_limit_reached(self, rate_limiter):
        """Test daily limit enforcement."""
        # Set sent_today to daily limit
        rate_limiter._sent_today = rate_limiter.daily_limit
        can_send, reason = rate_limiter.can_send()
        assert can_send is False
        assert "Daily limit" in reason

    def test_interval_too_short(self, rate_limiter):
        """Test minimum interval enforcement."""
        rate_limiter._sent_today = 0
        rate_limiter._last_sent_time = datetime.now()
        can_send, reason = rate_limiter.can_send()
        assert can_send is False
        assert "Interval too short" in reason

    def test_rest_period(self, rate_limiter):
        """Test rest period detection."""
        # Test with different hours
        with patch("app.services.anti_ban.rate_limiter.datetime") as mock_dt:
            # Test during rest hours (3 AM)
            mock_dt.now.return_value = datetime(2024, 1, 1, 3, 0, 0)
            mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            assert rate_limiter.is_in_rest_period() is True

            # Test outside rest hours (10 AM)
            mock_dt.now.return_value = datetime(2024, 1, 1, 10, 0, 0)
            assert rate_limiter.is_in_rest_period() is False

    @pytest.mark.asyncio
    async def test_acquire_success(self, rate_limiter):
        """Test successful acquire."""
        # Mock can_send to return True
        with patch.object(rate_limiter, "can_send", return_value=(True, "")):
            result = await rate_limiter.acquire(timeout=1.0)
            assert result is True

    @pytest.mark.asyncio
    async def test_acquire_timeout(self, rate_limiter):
        """Test acquire timeout."""
        # Mock can_send to always return False
        with patch.object(rate_limiter, "can_send", return_value=(False, "Test")):
            result = await rate_limiter.acquire(timeout=0.5)
            assert result is False

    @pytest.mark.asyncio
    async def test_record_sent(self, rate_limiter):
        """Test recording sent messages."""
        initial_count = rate_limiter._sent_today
        await rate_limiter.record_sent()
        assert rate_limiter._sent_today == initial_count + 1
        assert rate_limiter._last_sent_time is not None

    def test_get_status(self, rate_limiter):
        """Test getting status."""
        status = rate_limiter.get_status()
        assert "daily_limit" in status
        assert "sent_today" in status
        assert "remaining" in status
        assert "min_interval" in status
        assert status["daily_limit"] == 100

    def test_reset_daily_count(self, rate_limiter):
        """Test daily count reset."""
        rate_limiter._sent_today = 50
        rate_limiter._reset_date = "2020-01-01"  # Old date
        rate_limiter._check_and_reset_daily_count()
        assert rate_limiter._sent_today == 0