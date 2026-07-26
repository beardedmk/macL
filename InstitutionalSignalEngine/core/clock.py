"""
Clock module for the Institutional Signal Intelligence Engine.

Provides a centralized, thread-safe time utility for the entire application.
All timestamps generated are strictly timezone-aware based on the configured
market timezone.
"""

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from config import config


class Clock:
    """
    Centralized time utility providing timezone-aware datetime operations 
    and market session checks.
    """

    def __init__(self) -> None:
        """
        Initializes the clock with the configured timezone and parses 
        market session time boundaries from the configuration.
        """
        self._tz: ZoneInfo = ZoneInfo(config.market.timezone)
        
        # Parse time boundaries from configuration
        self._pre_open: time = datetime.strptime(config.market.pre_open, "%H:%M").time()
        self._pre_open_end: time = datetime.strptime(config.market.pre_open_end, "%H:%M").time()
        self._market_open: time = datetime.strptime(config.market.market_open, "%H:%M").time()
        self._market_close: time = datetime.strptime(config.market.market_close, "%H:%M").time()

    def now(self) -> datetime:
        """Returns the current timezone-aware datetime."""
        return datetime.now(self._tz)

    def now_str(self) -> str:
        """Returns the current timezone-aware datetime as a formatted string."""
        return self.now().strftime("%Y-%m-%d %H:%M:%S")

    def today(self) -> date:
        """Returns the current timezone-aware date."""
        return self.now().date()

    def current_time(self) -> time:
        """Returns the current timezone-aware time."""
        return self.now().time()

    def is_weekend(self) -> bool:
        """Checks if the current day is Saturday or Sunday."""
        return self.now().weekday() >= 5

    def is_pre_open(self) -> bool:
        """
        Checks if the current time falls within the pre-open session.
        Returns False if it is a weekend.
        """
        if self.is_weekend():
            return False
        t = self.current_time()
        return self._pre_open <= t < self._pre_open_end

    def is_market_open(self) -> bool:
        """
        Checks if the current time falls within regular market hours.
        Returns False if it is a weekend.
        """
        if self.is_weekend():
            return False
        t = self.current_time()
        return self._market_open <= t < self._market_close

    def seconds_since_market_open(self) -> float:
        """
        Calculates the number of seconds elapsed since the market open time today.
        Returns a negative value if the market has not yet opened.
        """
        now = self.now()
        open_dt = now.replace(
            hour=self._market_open.hour, 
            minute=self._market_open.minute, 
            second=0, 
            microsecond=0
        )
        return (now - open_dt).total_seconds()

    def seconds_until_market_close(self) -> float:
        """
        Calculates the number of seconds remaining until the market close time today.
        Returns a negative value if the market has already closed.
        """
        now = self.now()
        close_dt = now.replace(
            hour=self._market_close.hour, 
            minute=self._market_close.minute, 
            second=0, 
            microsecond=0
        )
        return (close_dt - now).total_seconds()