import math
from typing import Optional, Dict, Any

from app.database.session import SessionLocal
from app.modules.alerts.repository import alert_repository
from app.modules.users.service import user_service
from app.modules.transactions.service import transaction_service
from app.common.cache import TTLCache
from app.common.helpers import safe_int
from app.common.constants import CACHE_TTL_SUMMARY
from app.common.helpers import resolve_amount_range
from app.config.settings import settings

class AlertService:
    def __init__(self):
        self._summary_cache = TTLCache(default_ttl_seconds=CACHE_TTL_SUMMARY)

    def get_alerts_summary(self, inspector_id: Optional[str] = None) -> Dict[str, Any]:
        cache_key = str(inspector_id or "").strip()
        cached = self._summary_cache.get(cache_key)
        if cached:
            return cached

        db = SessionLocal()
        try:
            resolved_uid = None
            if inspector_id and str(inspector_id).strip():
                resolved_uid = user_service.resolve_user_id(db, inspector_id)

            row = alert_repository.get_summary_row(db, resolved_uid=resolved_uid)
            if resolved_uid is not None:
                total_alerts = row[0] or 0
                pending_count = row[1] or 0
                processed_count = row[2] or 0
                critical_count = row[3] or 0
                confirmed_fraud = row[4] or 0
                cleared_legit = row[5] or 0
                max_risk = row[6] or 0.0
                my_processed = row[7] or 0
                my_fraud = row[8] or 0
                my_legit = row[9] or 0
            else:
                total_alerts = row[0] or 0
                pending_count = row[1] or 0
                processed_count = row[2] or 0
                critical_count = row[3] or 0
                confirmed_fraud = row[4] or 0
                cleared_legit = row[5] or 0
                max_risk = row[6] or 0.0
                my_processed = 0
                my_fraud = 0
                my_legit = 0

            res = {
                "total_alerts": safe_int(total_alerts),
                "pending_count": safe_int(pending_count),
                "processed_count": safe_int(processed_count),
                "critical_count": safe_int(critical_count),
                "confirmed_fraud_count": safe_int(confirmed_fraud),
                "cleared_legitimate_count": safe_int(cleared_legit),
                "my_processed_count": safe_int(my_processed),
                "my_confirmed_fraud_count": safe_int(my_fraud),
                "my_cleared_legitimate_count": safe_int(my_legit),
                "max_risk_score": round(float(max_risk), 4),
                "sla_target_daily": settings.DAILY_ALERT_CAPACITY,
            }
            self._summary_cache.set(cache_key, res)
            return res
        finally:
            db.close()

    def get_pending_alerts(
        self,
        page: int = 1,
        limit: int = 50,
        offset: Optional[int] = None,
        search: Optional[str] = None,
        channel: Optional[str] = None,
        amount_range: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        sort_by: Optional[str] = "risk_score",
        order: Optional[str] = "desc",
    ) -> Dict[str, Any]:
        min_amount, max_amount = resolve_amount_range(amount_range, min_amount, max_amount)
        db = SessionLocal()
        try:
            records, total_filtered, has_filter = alert_repository.get_pending_alerts_raw(
                db=db,
                page=page,
                limit=limit,
                offset=offset,
                search=search,
                channel=channel,
                min_amount=min_amount,
                max_amount=max_amount,
                sort_by=sort_by,
                order=order,
            )

            if not has_filter:
                summary = self.get_alerts_summary()
                total = summary.get("pending_count", 0)
            else:
                total = total_filtered

            data = [transaction_service.tx_to_dict(r) for r in records]
            total_pages = math.ceil(total / limit) if limit > 0 else 1

            return {
                "status": "success",
                "data": data,
                "total": total,
                "page": page,
                "limit": limit,
                "offset": offset if offset is not None else max(0, (page - 1) * limit),
                "total_pages": max(1, total_pages),
            }
        finally:
            db.close()

    def get_cdf_alerts(self, starting_version: Optional[int] = None, limit: int = 200) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            rows, current_max_version, mode = alert_repository.get_cdf_alerts_raw(db, starting_version=starting_version, limit=limit)
            changes = []
            for r in rows:
                changes.append({
                    "transaction_id": str(r.transaction_id),
                    "source_account": str(r.source_account or ""),
                    "dest_account": str(r.dest_account or ""),
                    "amount": float(r.amount or 0.0),
                    "channel": str(r.channel or ""),
                    "risk_score": float(r.risk_score or 0.0),
                    "prediction_label": int(r.prediction_label) if r.prediction_label is not None else None,
                    "inspection_status": r.inspection_status,
                    "model_version": r.model_version,
                    "timestamp": str(r.timestamp) if r.timestamp else None,
                    "delta_commit_version": int(r.delta_commit_version) if r.delta_commit_version is not None else None,
                    "top_risk_factors": r.top_risk_factors or [],
                })

            batch_max_version = (
                max(
                    (c["delta_commit_version"] for c in changes if c["delta_commit_version"] is not None),
                    default=current_max_version,
                )
            )

            return {
                "status": "success",
                "mode": mode,
                "table": "transactions (serving table synced from gold.risk_scores)",
                "starting_version": starting_version if starting_version is not None else -1,
                "next_version": batch_max_version,
                "current_max_version": current_max_version,
                "total_changes": len(changes),
                "has_more": len(changes) == limit,
                "changes": changes,
            }
        finally:
            db.close()

alert_service = AlertService()
