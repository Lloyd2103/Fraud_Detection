from typing import Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.common.vn_time import VN_TZ
from app.modules.transactions.models import Transaction


class HealthRepository:
    def get_last_alert_age_seconds(self, db: Session) -> Optional[int]:
        """Seconds since the newest alert was received.

        `transactions.received_at` is `timestamp without time zone` and holds
        Vietnam local time (UTC+7) written by the producer, so a naive value is
        interpreted as Vietnam time, not UTC. A negative result (clock skew) is
        clamped to 0 so it can never look "fresher than now".
        """
        max_rcv = db.query(func.max(Transaction.received_at)).scalar()
        if max_rcv:
            if max_rcv.tzinfo is None:
                max_rcv = max_rcv.replace(tzinfo=VN_TZ)
            utc_now = datetime.now(timezone.utc)
            return max(0, int((utc_now - max_rcv).total_seconds()))
        return None


health_repository = HealthRepository()
