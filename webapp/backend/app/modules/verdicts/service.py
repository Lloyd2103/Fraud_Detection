import re
import math
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session

from app.database.session import SessionLocal, run_db_transaction
from app.modules.verdicts.repository import verdict_repository
from app.modules.users.service import user_service
from app.modules.transactions.service import transaction_service
from app.common.cache import TTLCache
from app.common.constants import CACHE_TTL_VERDICT_STATS
from app.common.helpers import resolve_amount_range
from app.core.exceptions import BadRequestError

VN_TZ = timezone(timedelta(hours=7))

class VerdictService:
    def __init__(self):
        self._stats_cache = TTLCache(default_ttl_seconds=CACHE_TTL_VERDICT_STATS)

    def record_verdict_entry(
        self,
        db: Session,
        transaction_id: str,
        label: int,
        status: str,
        inspector_id: Optional[int],
        reason: Optional[str],
        proc_time: int = 0
    ) -> None:
        verdict_repository.insert_decision(
            db=db,
            transaction_id=transaction_id,
            label=label,
            status=status,
            inspector_id=inspector_id,
            reason=reason,
            proc_time=proc_time
        )
        self._stats_cache.clear()

    def submit_inspection_verdict(
        self,
        transaction_id: str,
        label: int,
        inspector_id: str,
        reason: str,
        processing_time: int,
    ) -> Dict[str, Any]:
        now_dt = datetime.utcnow()
        decision_time = now_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        new_status = "CONFIRMED_FRAUD" if int(label) == 1 else "CLEARED_LEGITIMATE"

        def _execute_verdict_tx(session: Session):
            resolved_uid = user_service.resolve_user_id(session, inspector_id)
            if resolved_uid is None:
                raise BadRequestError(f"Auditor user identity not found or inactive: {inspector_id}")

            # 1. Update transaction table via transactions module service
            transaction_service.update_transaction_for_verdict(
                db=session,
                transaction_id=transaction_id,
                new_status=new_status,
                label=int(label),
                resolved_uid=resolved_uid,
                reason=reason,
                now_dt=now_dt,
            )

            # 2. Insert verdict into inspection_decisions via verdict repository
            verdict_repository.insert_decision(
                db=session,
                transaction_id=transaction_id,
                label=int(label),
                status=new_status,
                inspector_id=resolved_uid,
                reason=reason,
                proc_time=processing_time if processing_time is not None else 0,
            )
            return resolved_uid

        # Automatic Client-Side Transaction Retry for CockroachDB SERIALIZABLE isolation (SQLState 40001)
        resolved_uid = run_db_transaction(_execute_verdict_tx, max_retries=5, max_backoff=2)
        self._stats_cache.clear()

        return {
            "status": "success",
            "message": f"Verdict {new_status} recorded successfully in CockroachDB serving store.",
            "transaction_id": transaction_id,
            "label": label,
            "inspector_id": str(resolved_uid or inspector_id),
            "decision_timestamp": decision_time,
            "reason": reason,
            "processing_time": processing_time,
            "persisted_to_cockroachdb": True,
        }

    def get_inspected_alerts(
        self,
        page: int = 1,
        limit: int = 50,
        search: Optional[str] = None,
        channel: Optional[str] = None,
        inspector_id: Optional[Any] = None,
        from_time: Optional[str] = None,
        to_time: Optional[str] = None,
        offset: Optional[int] = None,
        amount_range: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
    ) -> Dict[str, Any]:
        min_amount, max_amount = resolve_amount_range(amount_range, min_amount, max_amount)
        db = SessionLocal()
        try:
            resolved_uid = None
            if inspector_id is not None and str(inspector_id).strip() != "":
                resolved_uid = user_service.resolve_user_id(db, inspector_id)

            records, total, decided_at_map = verdict_repository.get_inspected_alerts_raw(
                db=db,
                page=page,
                limit=limit,
                search=search,
                channel=channel,
                inspector_id=inspector_id,
                resolved_uid=resolved_uid,
                from_time=from_time,
                to_time=to_time,
                offset=offset,
                min_amt=min_amount,
                max_amt=max_amount,
            )

            data = [
                transaction_service.tx_to_dict(r, decided_at=decided_at_map.get(r.transaction_id))
                for r in records
            ]
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

    def get_verdicts_stats(
        self,
        user_id: Optional[Any] = None,
        user_role: str = "auditor",
        period: str = "day",
        date_str: Optional[str] = None,
        month_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        clean_period = str(period).strip().lower() if period else "day"
        if clean_period not in ("day", "month"):
            raise BadRequestError("Invalid period. Must be 'day' or 'month'")

        today_vn = datetime.now(VN_TZ).date()

        if clean_period == "day":
            target_date_str = str(date_str).strip() if date_str and str(date_str).strip() else today_vn.strftime("%Y-%m-%d")
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", target_date_str):
                raise BadRequestError("Invalid date format. Expected YYYY-MM-DD")
            try:
                target_date = datetime.strptime(target_date_str, "%Y-%m-%d").date()
            except ValueError:
                raise BadRequestError("Invalid date value")
            if target_date > today_vn:
                raise BadRequestError("Invalid date value")

            start_vn = datetime(target_date.year, target_date.month, target_date.day, 0, 0, 0, tzinfo=VN_TZ)
            end_vn = start_vn + timedelta(days=1)
            target_month = None
        else:
            target_month_str = str(month_str).strip() if month_str and str(month_str).strip() else today_vn.strftime("%Y-%m")
            if not re.match(r"^\d{4}-\d{2}$", target_month_str):
                raise BadRequestError("Invalid month format. Expected YYYY-MM")
            try:
                target_month = datetime.strptime(target_month_str, "%Y-%m")
            except ValueError:
                raise BadRequestError("Invalid month value")
            if target_month.date() > today_vn.replace(day=1):
                raise BadRequestError("Invalid month value")

            start_vn = datetime(target_month.year, target_month.month, 1, 0, 0, 0, tzinfo=VN_TZ)
            y_next = target_month.year + 1 if target_month.month == 12 else target_month.year
            m_next = 1 if target_month.month == 12 else target_month.month + 1
            end_vn = datetime(y_next, m_next, 1, 0, 0, 0, tzinfo=VN_TZ)

        cache_key = (str(user_id), user_role, clean_period, target_date_str if clean_period == 'day' else target_month_str)
        cached = self._stats_cache.get(cache_key)
        if cached:
            return cached

        start_utc = start_vn.astimezone(timezone.utc)
        end_utc = end_vn.astimezone(timezone.utc)

        db = SessionLocal()
        try:
            rows = verdict_repository.get_latest_decisions_for_stats(db, start_utc, end_utc)

            my_uid = None
            if user_id is not None:
                try:
                    my_uid = int(user_id)
                except (ValueError, TypeError):
                    pass

            my_rows = [r for r in rows if my_uid is not None and r.inspector_id == my_uid]
            my_total = len(my_rows)
            my_fraud = sum(1 for r in my_rows if r.decision_label == 1 or r.inspection_status == 'CONFIRMED_FRAUD')
            my_legit = sum(1 for r in my_rows if r.decision_label == 0 or r.inspection_status == 'CLEARED_LEGITIMATE')
            my_times = [r.processing_time for r in my_rows if r.processing_time is not None and r.processing_time > 0]
            my_avg_time = round(sum(my_times) / len(my_times), 1) if my_times else None

            team_total = len(rows)
            team_fraud = sum(1 for r in rows if r.decision_label == 1 or r.inspection_status == 'CONFIRMED_FRAUD')
            team_legit = sum(1 for r in rows if r.decision_label == 0 or r.inspection_status == 'CLEARED_LEGITIMATE')

            daily = []
            if clean_period == "month" and target_month is not None:
                cur_date = datetime(target_month.year, target_month.month, 1).date()
                end_date = end_vn.date()
                while cur_date < end_date:
                    d_str = cur_date.strftime("%Y-%m-%d")
                    d_mine = sum(1 for r in rows if my_uid is not None and r.inspector_id == my_uid and r.day_vn == d_str)
                    d_team = sum(1 for r in rows if r.day_vn == d_str)
                    daily.append({"date": d_str, "mine": d_mine, "team": d_team})
                    cur_date += timedelta(days=1)

            hourly = []
            if clean_period == "day":
                for h in range(24):
                    h_mine = sum(1 for r in rows if my_uid is not None and r.inspector_id == my_uid and getattr(r.decided_at_vn, "hour", None) == h)
                    h_team = sum(1 for r in rows if getattr(r.decided_at_vn, "hour", None) == h)
                    hourly.append({"hour": h, "mine": h_mine, "team": h_team})

            res = {
                "range_start": start_vn.isoformat(),
                "range_end": end_vn.isoformat(),
                "mine": {
                    "total": my_total,
                    "fraud": my_fraud,
                    "legit": my_legit,
                    "avg_processing_time": my_avg_time,
                },
                "team": {
                    "total": team_total,
                    "fraud": team_fraud,
                    "legit": team_legit,
                },
                "daily": daily,
                "hourly": hourly,
            }

            if user_role == "admin":
                users_map = {}
                u_rows = verdict_repository.get_users_for_admin_stats(db)
                for u in u_rows:
                    users_map[u.id] = {"username": u.username, "full_name": u.full_name or u.username}

                insp_groups = {}
                for r in rows:
                    insp_groups.setdefault(r.inspector_id, []).append(r)

                per_insp = []
                for i_id, i_rows in insp_groups.items():
                    i_tot = len(i_rows)
                    i_fr = sum(1 for r in i_rows if r.decision_label == 1 or r.inspection_status == 'CONFIRMED_FRAUD')
                    i_lg = sum(1 for r in i_rows if r.decision_label == 0 or r.inspection_status == 'CLEARED_LEGITIMATE')
                    u_info = users_map.get(i_id, {"username": str(i_id), "full_name": str(i_id)})
                    per_insp.append({
                        "inspector_id": i_id,
                        "username": u_info["username"],
                        "full_name": u_info["full_name"],
                        "total": i_tot,
                        "fraud": i_fr,
                        "legit": i_lg,
                        "fraud_rate": round(i_fr / i_tot, 4) if i_tot > 0 else 0.0,
                    })
                res["per_inspector"] = per_insp

            self._stats_cache.set(cache_key, res)
            return res
        finally:
            db.close()

verdict_service = VerdictService()
