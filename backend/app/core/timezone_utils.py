"""Singapore timezone utilities."""
from __future__ import annotations

from datetime import datetime
from typing import Any

_SINGAPORE_TZ: Any = None


def get_singapore_timezone():
    """Get Singapore timezone, with caching.
    
    Uses zoneinfo (Python 3.9+) with fallback to pytz for older versions.
    The timezone object is cached after first creation.
    
    Returns:
        Timezone object for Asia/Singapore
    """
    global _SINGAPORE_TZ
    if _SINGAPORE_TZ is None:
        try:
            from zoneinfo import ZoneInfo
            _SINGAPORE_TZ = ZoneInfo("Asia/Singapore")
        except ImportError:
            # Fallback for Python < 3.9
            import pytz
            _SINGAPORE_TZ = pytz.timezone("Asia/Singapore")
    return _SINGAPORE_TZ


def get_singapore_now() -> datetime:
    """Get current datetime in Singapore timezone.
    
    Returns:
        Current datetime in Singapore timezone
    """
    return datetime.now(get_singapore_timezone())


def format_singapore_datetime(dt: datetime, format_str: str = "%Y-%m-%d %H:%M") -> str:
    """Format datetime in Singapore timezone.
    
    Args:
        dt: Datetime to format (assumed UTC if no timezone)
        format_str: strftime format string
        
    Returns:
        Formatted datetime string in Singapore timezone
    """
    if dt.tzinfo is None:
        # Assume UTC if no timezone
        from datetime import timezone as tz
        dt = dt.replace(tzinfo=tz.utc)
    dt_sg = dt.astimezone(get_singapore_timezone())
    return dt_sg.strftime(format_str)


def get_today_start_singapore() -> datetime:
    """Get start of today (00:00:00) in Singapore timezone.
    
    Returns:
        Datetime representing start of today in Singapore timezone
    """
    now = get_singapore_now()
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def parse_and_format_timestamp(timestamp: str, format_str: str = "%Y-%m-%d %H:%M") -> str:
    """Parse ISO timestamp and format in Singapore timezone.
    
    Args:
        timestamp: ISO format timestamp string
        format_str: strftime format string
        
    Returns:
        Formatted datetime string, or original string if parsing fails
    """
    from app.core.constants import UTC_Z_SUFFIX, UTC_OFFSET_SUFFIX
    
    try:
        # Normalize Z suffix to +00:00 for fromisoformat
        normalized = timestamp.replace(UTC_Z_SUFFIX, UTC_OFFSET_SUFFIX)
        dt = datetime.fromisoformat(normalized)
        return format_singapore_datetime(dt, format_str)
    except Exception:
        # Fallback: return first 16 chars (YYYY-MM-DD HH:MM) if parsing fails
        return timestamp[:16] if len(timestamp) > 16 else timestamp


def get_current_datetime_string() -> tuple[str, str]:
    """Get current date and time strings for system prompts.
    
    Returns:
        Tuple of (full_datetime_string, date_string)
        Example: ("Monday, January 15, 2024 at 14:30:45 SGT", "2024-01-15")
    """
    now = get_singapore_now()
    current_date_str = now.strftime("%Y-%m-%d")
    current_datetime_str = now.strftime("%A, %B %d, %Y at %H:%M:%S SGT")
    return current_datetime_str, current_date_str

