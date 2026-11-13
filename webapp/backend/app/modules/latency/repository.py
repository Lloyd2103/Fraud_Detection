from sqlalchemy.orm import Session
from sqlalchemy import text

class LatencyRepository:
    def get_latency_metrics_row(self, db: Session):
        latency_sql = text("""
            SELECT
                percentile_disc(0.50) WITHIN GROUP (ORDER BY latency_ms) AS p50,
                percentile_disc(0.95) WITHIN GROUP (ORDER BY latency_ms) AS p95,
                percentile_disc(0.99) WITHIN GROUP (ORDER BY latency_ms) AS p99,
                max(latency_ms) AS max_latency,
                count(*) AS total_count,
                count(*) FILTER (WHERE latency_ms <= 2000) AS count_within_2s,
                count(*) FILTER (WHERE latency_ms <= 5000) AS count_within_5s
            FROM transactions
            WHERE latency_ms IS NOT NULL AND latency_ms > 0 AND latency_ms <= 60000;
        """)
        return db.execute(latency_sql).fetchone()

latency_repository = LatencyRepository()

