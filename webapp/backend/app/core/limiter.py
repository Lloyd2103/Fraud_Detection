"""
Centralized Rate Limiter configuration using SlowAPI.
Provides token-bucket / sliding-window rate limiting for sensitive endpoints.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["120/minute"],
    storage_uri="memory://",
)

