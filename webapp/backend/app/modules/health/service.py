from datetime import datetime, timezone
from typing import Dict, Any
from app.config.settings import settings
from app.database.session import SessionLocal
from app.modules.health.repository import health_repository
from app.integrations.kafka import check_kafka_connectivity
from app.common.cache import TTLCache
from app.common.constants import CACHE_TTL_HEALTH

class HealthService:
    def __init__(self):
        self._cache = TTLCache(default_ttl_seconds=CACHE_TTL_HEALTH)

    def get_system_health(self) -> Dict[str, Any]:
        return {
            "status": "UP",
            "app": settings.APP_NAME,
            "lakehouse_base": settings.LAKEHOUSE_BASE,
            "namenode": f"{settings.NAMENODE_HOST}:{settings.NAMENODE_PORT}",
            "kafka_broker": settings.KAFKA_BOOTSTRAP_SERVERS,
            "sla_latency_limit": f"{settings.SLA_LATENCY_MAX_SECONDS}s",
            "version": settings.APP_VERSION,
        }

    def get_pipeline_health(self) -> Dict[str, Any]:
        cached = self._cache.get("pipeline_health")
        if cached:
            return cached

        kafka_reachable, _, _ = check_kafka_connectivity()

        db = SessionLocal()
        try:
            last_alert_age_seconds = health_repository.get_last_alert_age_seconds(db)
        except Exception:
            last_alert_age_seconds = None
        finally:
            db.close()

        if not kafka_reachable or last_alert_age_seconds is None or last_alert_age_seconds > 3600:
            detector_state = "DOWN"
        elif last_alert_age_seconds < 120:
            detector_state = "ACTIVE"
        else:
            detector_state = "IDLE"

        res = {
            "kafka_reachable": kafka_reachable,
            "last_alert_age_seconds": last_alert_age_seconds,
            "detector_state": detector_state,
            "checked_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        self._cache.set("pipeline_health", res)
        return res

health_service = HealthService()

