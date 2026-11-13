"""
Vietnam Timezone & DateTime Formatting Utilities
Complies with Asia/Ho_Chi_Minh (+07:00) specification.
"""
from datetime import datetime, timezone, timedelta
from typing import Optional, Any

VN_TZ = timezone(timedelta(hours=7))

def get_vietnam_now() -> datetime:
    """Get current datetime in Vietnam timezone (+07:00)."""
    return datetime.now(VN_TZ)

def to_vietnam_time(dt: Optional[datetime]) -> Optional[datetime]:
    """Convert an arbitrary timezone or naive UTC datetime to Vietnam timezone."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(VN_TZ)

def format_vietnam_time(dt: Any) -> str:
    """
    Format datetime into the display string 'HH:mm:ss dd/MM/yyyy' (Vietnam time).
    """
    if dt is None:
        return "-"
    if isinstance(dt, str):
        # Return string if already formatted
        return dt
    try:
        vn_dt = to_vietnam_time(dt)
        return vn_dt.strftime("%H:%M:%S %d/%m/%Y")
    except Exception:
        return str(dt)

