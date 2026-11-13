import re
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text, or_, cast, String
from app.modules.transactions.models import Transaction

VN_TZ = timezone(timedelta(hours=7))

class VerdictRepository:
    def insert_decision(
        self,
        db: Session,
        transaction_id: str,
        label: int,
        status: str,
        inspector_id: Optional[int],
        reason: Optional[str],
        proc_time: int = 0
    ) -> None:
        db.execute(text("""
            INSERT INTO inspection_decisions (
                transaction_id, decision_label, inspection_status, inspector_id, reason, processing_time, decided_at
            ) VALUES (
                :tx_id, :label, :status, :inspector_id, :reason, :proc_time, CURRENT_TIMESTAMP
            );
        """), {
            "tx_id": transaction_id,
            "label": int(label),
            "status": status,
            "inspector_id": inspector_id,
            "reason": reason or "Auditor decision",
            "proc_time": proc_time if proc_time is not None else 0,
        })
        db.flush()

    def get_latest_decision_time_for_tx(self, db: Session, transaction_id: str) -> Optional[datetime]:
        row = db.execute(
            text("SELECT decided_at FROM inspection_decisions WHERE transaction_id = :tx_id ORDER BY decided_at DESC LIMIT 1"),
            {"tx_id": transaction_id}
        ).fetchone()
        return row[0] if (row and row[0]) else None

    def get_inspected_alerts_raw(
        self,
        db: Session,
        page: int = 1,
        limit: int = 50,
        search: Optional[str] = None,
        channel: Optional[str] = None,
        inspector_id: Optional[Any] = None,
        resolved_uid: Optional[int] = None,
        from_time: Optional[str] = None,
        to_time: Optional[str] = None,
        offset: Optional[int] = None,
        min_amt: Optional[float] = None,
        max_amt: Optional[float] = None,
    ) -> Tuple[List[Transaction], int, Dict[str, datetime]]:
        q = db.query(Transaction).filter(
            or_(
                Transaction.decision_label.isnot(None),
                Transaction.inspection_status.in_(["CONFIRMED_FRAUD", "CLEARED_LEGITIMATE"])
            )
        )

        if channel and channel != "ALL":
            q = q.filter(Transaction.channel == channel)

        if inspector_id is not None and str(inspector_id).strip() != "":
            if resolved_uid is not None:
                q = q.filter(Transaction.inspector_id == resolved_uid)
            else:
                q = q.filter(Transaction.transaction_id == "__NEVER_MATCH__")

        if (from_time and str(from_time).strip()) or (to_time and str(to_time).strip()):
            start_utc = None
            end_utc = None
            if from_time and str(from_time).strip():
                fv = str(from_time).strip()
                if re.match(r"^\d{4}-\d{2}-\d{2}$", fv):
                    d = datetime.strptime(fv, "%Y-%m-%d").date()
                    dt_vn = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=VN_TZ)
                    start_utc = dt_vn.astimezone(timezone.utc)
                elif re.match(r"^\d{4}-\d{2}$", fv):
                    dt = datetime.strptime(fv, "%Y-%m")
                    dt_vn = datetime(dt.year, dt.month, 1, 0, 0, 0, tzinfo=VN_TZ)
                    start_utc = dt_vn.astimezone(timezone.utc)
                else:
                    try:
                        dt_iso = datetime.fromisoformat(fv)
                        start_utc = dt_iso.astimezone(timezone.utc) if dt_iso.tzinfo else dt_iso.replace(tzinfo=VN_TZ).astimezone(timezone.utc)
                    except Exception:
                        pass

            if to_time and str(to_time).strip():
                tv = str(to_time).strip()
                if re.match(r"^\d{4}-\d{2}-\d{2}$", tv):
                    d = datetime.strptime(tv, "%Y-%m-%d").date()
                    dt_vn = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=VN_TZ) + timedelta(days=1)
                    end_utc = dt_vn.astimezone(timezone.utc)
                elif re.match(r"^\d{4}-\d{2}$", tv):
                    dt = datetime.strptime(tv, "%Y-%m")
                    y_next = dt.year + 1 if dt.month == 12 else dt.year
                    m_next = 1 if dt.month == 12 else dt.month + 1
                    dt_vn = datetime(y_next, m_next, 1, 0, 0, 0, tzinfo=VN_TZ)
                    end_utc = dt_vn.astimezone(timezone.utc)
                else:
                    try:
                        dt_iso = datetime.fromisoformat(tv)
                        end_utc = dt_iso.astimezone(timezone.utc) if dt_iso.tzinfo else dt_iso.replace(tzinfo=VN_TZ).astimezone(timezone.utc)
                    except Exception:
                        pass

            dec_sql = text("""
                WITH latest_decisions AS (
                    SELECT DISTINCT ON (transaction_id)
                        transaction_id,
                        decided_at
                    FROM inspection_decisions
                    ORDER BY transaction_id, decided_at DESC
                )
                SELECT transaction_id FROM latest_decisions
                WHERE (:start_utc IS NULL OR decided_at >= :start_utc)
                  AND (:end_utc IS NULL OR decided_at < :end_utc)
            """)
            d_rows = db.execute(dec_sql, {"start_utc": start_utc, "end_utc": end_utc}).fetchall()
            matching_tx_ids = [r[0] for r in d_rows]
            q = q.filter(Transaction.transaction_id.in_(matching_tx_ids))

        if min_amt is not None:
            q = q.filter(Transaction.amount >= min_amt)
        if max_amt is not None:
            q = q.filter(Transaction.amount <= max_amt)

        if search and search.strip():
            term = f"%{search.strip()}%"
            q = q.filter(or_(
                Transaction.transaction_id.ilike(term),
                Transaction.source_account.ilike(term),
                Transaction.dest_account.ilike(term),
                cast(Transaction.inspector_id, String).ilike(term),
                Transaction.reason.ilike(term),
            ))

        q = q.order_by(Transaction.updated_at.desc(), Transaction.timestamp.desc())
        total = q.count()
        if offset is None:
            offset = max(0, (page - 1) * limit)

        records = q.offset(offset).limit(limit).all()

        decided_at_map = {}
        if records:
            tx_ids = [r.transaction_id for r in records]
            dec_rows = db.execute(
                text("SELECT transaction_id, max(decided_at) FROM inspection_decisions WHERE transaction_id = ANY(:tx_ids) GROUP BY transaction_id"),
                {"tx_ids": tx_ids}
            ).fetchall()
            for d_tx_id, d_time in dec_rows:
                decided_at_map[d_tx_id] = d_time

        return records, total, decided_at_map

    def get_latest_decisions_for_stats(self, db: Session, start_utc: datetime, end_utc: datetime):
        sql = text("""
            WITH latest_decisions AS (
                SELECT DISTINCT ON (transaction_id)
                    decision_id,
                    transaction_id,
                    decision_label,
                    inspection_status,
                    inspector_id,
                    processing_time,
                    decided_at,
                    (decided_at AT TIME ZONE 'Asia/Ho_Chi_Minh') as decided_at_vn
                FROM inspection_decisions
                ORDER BY transaction_id, decided_at DESC
            )
            SELECT 
                decision_id,
                transaction_id,
                decision_label,
                inspection_status,
                inspector_id,
                processing_time,
                decided_at,
                decided_at_vn,
                to_char(decided_at_vn, 'YYYY-MM-DD') as day_vn
            FROM latest_decisions
            WHERE decided_at >= :start_utc AND decided_at < :end_utc
            ORDER BY decided_at DESC;
        """)
        return db.execute(sql, {"start_utc": start_utc, "end_utc": end_utc}).fetchall()

    def get_users_for_admin_stats(self, db: Session):
        return db.execute(text("SELECT id, username, full_name FROM users;")).fetchall()

verdict_repository = VerdictRepository()
