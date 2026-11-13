"""
Common Type Conversion and Sanitization Helpers
"""
import math
from datetime import datetime
from typing import Any, Optional

def parse_dt(dt_str: Any) -> Optional[datetime]:
    if not dt_str:
        return None
    if isinstance(dt_str, datetime):
        return dt_str
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(dt_str)[:19], fmt)
        except Exception:
            pass
    return None

def safe_int(val: Any, default: int = 0) -> int:
    if val is None:
        return default
    try:
        if isinstance(val, (float, int)) and (math.isnan(val) or math.isinf(val)):
            return default
        s = str(val).strip()
        return default if s.lower() in ("nan", "none", "null", "") else int(float(s))
    except Exception:
        return default

def safe_float(val: Any, default: float = 0.0) -> float:
    if val is None:
        return default
    try:
        f = float(val)
        return default if (math.isnan(f) or math.isinf(f)) else f
    except Exception:
        return default

def clean_for_json(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {str(k): clean_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple, set)):
        return [clean_for_json(item) for item in obj]
    elif isinstance(obj, (int, str, bool)) or obj is None:
        return obj
    elif isinstance(obj, float):
        return None if (math.isnan(obj) or math.isinf(obj)) else obj
    elif hasattr(obj, "isoformat"):
        return obj.isoformat()
    elif hasattr(obj, "strftime"):
        return obj.strftime("%Y-%m-%d %H:%M:%S")
    return str(obj)


# Amount presets (VND) used by the alert and verdict filters.
_AMOUNT_RANGES = {
    "GT_10M": (10_000_000.0, None), "> 10M": (10_000_000.0, None), "GT10M": (10_000_000.0, None),
    "1M_10M": (1_000_000.0, 10_000_000.0), "1M-10M": (1_000_000.0, 10_000_000.0),
    "LT_1M": (None, 1_000_000.0), "< 1M": (None, 1_000_000.0), "LT1M": (None, 1_000_000.0), "UNDER_1M": (None, 1_000_000.0),
    "GT_5M": (5_000_000.0, None),
    "1M_5M": (1_000_000.0, 5_000_000.0),
}


def resolve_amount_range(amount_range: Optional[str], min_amount: Optional[float], max_amount: Optional[float]):
    """Map an amount preset to (min_amount, max_amount); unknown/empty presets leave the bounds unchanged."""
    if not amount_range:
        return min_amount, max_amount
    preset = _AMOUNT_RANGES.get(str(amount_range).strip().upper())
    if preset is None:
        return min_amount, max_amount
    lo, hi = preset
    return (lo if lo is not None else min_amount), (hi if hi is not None else max_amount)
