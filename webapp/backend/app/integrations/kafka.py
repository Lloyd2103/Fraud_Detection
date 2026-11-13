"""
Kafka integration helpers: broker socket reachability check.
Rule BE4 compliant: does NOT import any modules/.
"""
import socket
from typing import Optional, Tuple

from app.config.settings import settings


def _first_broker() -> Tuple[str, int]:
    first = (settings.KAFKA_BOOTSTRAP_SERVERS.split(",")[0] or "").strip()
    host, _, port = first.partition(":")
    return host or "localhost", int(port) if port.isdigit() else 9092


def check_kafka_connectivity(host: Optional[str] = None, port: Optional[int] = None, timeout: float = 2.0) -> Tuple[bool, str, int]:
    """Return (reachable, host, port). Defaults come from KAFKA_BOOTSTRAP_SERVERS."""
    default_host, default_port = _first_broker()
    kafka_host = host or default_host
    kafka_port = port or default_port
    try:
        with socket.create_connection((kafka_host, kafka_port), timeout=timeout):
            return True, kafka_host, kafka_port
    except OSError:
        return False, kafka_host, kafka_port
