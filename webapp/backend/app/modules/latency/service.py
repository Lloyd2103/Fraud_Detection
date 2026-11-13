from typing import Dict, Any
from app.database.session import SessionLocal
from app.modules.latency.repository import latency_repository
from app.common.cache import TTLCache
from app.common.helpers import safe_int
from app.common.constants import CACHE_TTL_LATENCY
from app.config.settings import settings

class LatencyService:
    def __init__(self):
        self._cache = TTLCache(default_ttl_seconds=CACHE_TTL_LATENCY)

    def get_latency_stats(self) -> Dict[str, Any]:
        cached = self._cache.get("latency_stats")
        if cached:
            return cached

        db = SessionLocal()
        try:
            row = latency_repository.get_latency_metrics_row(db)
            if row and row[4] and row[4] > 0:
                p50 = safe_int(row[0])
                p95 = safe_int(row[1])
                p99 = safe_int(row[2])
                pmax = safe_int(row[3])
                n = safe_int(row[4])
                count_2s = safe_int(row[5])
                count_5s = safe_int(row[6])
                sla_2s_rate = round((count_2s / n) * 100, 2)
                sla_5s_rate = round((count_5s / n) * 100, 2)
            else:
                p50 = p95 = p99 = pmax = 0
                n = 0
                sla_2s_rate = 0.0
                sla_5s_rate = 0.0

            if n == 0:
                status = "NO_DATA"
                status_reason = "No latency measurements are available in the serving table."
            elif sla_2s_rate >= 95.0 and p95 <= 2000 and p99 <= 5000:
                status = "HEALTHY"
                status_reason = "All latency indicators meet the SLA targets (P95 <= 2.0s, P99 <= 5.0s, within-2s rate >= 95%)"
            elif sla_5s_rate >= 95.0:
                status = "WARNING"
                reasons = []
                if p99 > 5000:
                    reasons.append(f"P99 {(p99/1000):.2f}s exceeds 5s")
                if p95 > 2000:
                    reasons.append(f"P95 {(p95/1000):.2f}s exceeds 2s")
                if sla_2s_rate < 95.0:
                    reasons.append(f"within-2s rate is {sla_2s_rate}% (< 95%)")
                status_reason = ", ".join(reasons) if reasons else f"Within-5s rate is {sla_5s_rate}%"
            else:
                status = "CRITICAL"
                status_reason = f"Within-5s rate is low ({sla_5s_rate}% < 95%)"

            res = {
                "p50_latency_ms": p50,
                "p95_latency_ms": p95,
                "p99_latency_ms": p99,
                "max_latency_ms": pmax,
                "sla_limit_ms": int(settings.SLA_LATENCY_MAX_SECONDS * 1000),
                "sla_compliance_rate": sla_5s_rate,
                "sla_compliance_rate_pct": sla_5s_rate,
                "sla_2s_rate": sla_2s_rate,
                "sla_5s_rate": sla_5s_rate,
                "total_measured_alerts": n,
                "status": status,
                "status_reason": status_reason,
            }
            self._cache.set("latency_stats", res)
            return res
        finally:
            db.close()

latency_service = LatencyService()

