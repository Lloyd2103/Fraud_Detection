from typing import Optional, List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text, or_, cast, String
from app.modules.transactions.models import Transaction

class AlertRepository:
    def get_pending_alerts_raw(
        self,
        db: Session,
        page: int = 1,
        limit: int = 50,
        offset: Optional[int] = None,
        search: Optional[str] = None,
        channel: Optional[str] = None,
        min_amount: Optional[float] = None,
        max_amount: Optional[float] = None,
        sort_by: Optional[str] = "risk_score",
        order: Optional[str] = "desc",
    ) -> Tuple[List[Transaction], int, bool]:
        q = db.query(Transaction).filter(
            Transaction.inspection_status.in_(["PENDING", "NEW", None])
        )

        has_filter = bool(
            (search and search.strip()) or
            (channel and channel.strip() and channel.upper() != "ALL") or
            (min_amount is not None) or
            (max_amount is not None)
        )

        if search and search.strip():
            term = f"%{search.strip()}%"
            q = q.filter(or_(
                Transaction.transaction_id.ilike(term),
                Transaction.source_account.ilike(term),
                Transaction.dest_account.ilike(term),
                cast(Transaction.inspector_id, String).ilike(term),
                Transaction.reason.ilike(term),
            ))

        if channel and channel.strip() and channel.upper() != "ALL":
            q = q.filter(Transaction.channel == channel.strip().upper())

        if min_amount is not None:
            q = q.filter(Transaction.amount >= min_amount)

        if max_amount is not None:
            q = q.filter(Transaction.amount <= max_amount)

        sort_fields = []
        if sort_by:
            raw_parts = [p.strip() for p in str(sort_by).split(",") if p.strip()]
            default_order = (order or "desc").strip().lower()
            for part in raw_parts:
                if ":" in part:
                    f_name, f_dir = part.split(":", 1)
                    sort_fields.append((f_name.strip().lower(), "asc" if f_dir.strip().lower() == "asc" else "desc"))
                else:
                    sort_fields.append((part.strip().lower(), default_order))

        if not sort_fields:
            sort_fields = [("risk_score", "desc")]

        order_clauses = []
        for f_name, f_order in sort_fields:
            col = None
            if f_name == "timestamp":
                col = Transaction.timestamp
            elif f_name == "amount":
                col = Transaction.amount
            elif f_name in ("risk_score", "risk_core", "score"):
                col = Transaction.risk_score
            if col is not None:
                order_clauses.append(col.asc().nullslast() if f_order == "asc" else col.desc().nullslast())

        order_clauses.append(Transaction.transaction_id.asc())
        q = q.order_by(*order_clauses)

        total = q.count() if has_filter else 0
        if offset is None:
            offset = max(0, (page - 1) * limit)

        records = q.offset(offset).limit(limit).all()
        return records, total, has_filter

    def get_summary_row(self, db: Session, resolved_uid: Optional[int] = None):
        if resolved_uid is not None:
            summary_sql = text("""
                SELECT
                    count(*) AS total_alerts,
                    count(*) FILTER (WHERE inspection_status IN ('PENDING', 'NEW') OR inspection_status IS NULL) AS pending_count,
                    count(*) FILTER (WHERE inspection_status IN ('PROCESSED', 'CONFIRMED_FRAUD', 'CLEARED_LEGITIMATE') OR decision_label IS NOT NULL) AS processed_count,
                    count(*) FILTER (WHERE (inspection_status IN ('PENDING', 'NEW') OR inspection_status IS NULL) AND risk_score >= 0.80) AS critical_count,
                    count(*) FILTER (WHERE inspection_status = 'CONFIRMED_FRAUD' OR decision_label = 1) AS confirmed_fraud_count,
                    count(*) FILTER (WHERE inspection_status = 'CLEARED_LEGITIMATE' OR decision_label = 0) AS cleared_legitimate_count,
                    max(CASE WHEN inspection_status IN ('PENDING', 'NEW') OR inspection_status IS NULL THEN risk_score ELSE NULL END) AS max_risk_score,
                    count(*) FILTER (WHERE inspector_id = :uid AND (inspection_status IN ('PROCESSED', 'CONFIRMED_FRAUD', 'CLEARED_LEGITIMATE') OR decision_label IS NOT NULL)) AS my_processed_count,
                    count(*) FILTER (WHERE inspector_id = :uid AND (inspection_status = 'CONFIRMED_FRAUD' OR decision_label = 1)) AS my_confirmed_fraud_count,
                    count(*) FILTER (WHERE inspector_id = :uid AND (inspection_status = 'CLEARED_LEGITIMATE' OR decision_label = 0)) AS my_cleared_legitimate_count
                FROM transactions;
            """)
            return db.execute(summary_sql, {"uid": resolved_uid}).fetchone()
        else:
            summary_sql = text("""
                SELECT
                    count(*) AS total_alerts,
                    count(*) FILTER (WHERE inspection_status IN ('PENDING', 'NEW') OR inspection_status IS NULL) AS pending_count,
                    count(*) FILTER (WHERE inspection_status IN ('PROCESSED', 'CONFIRMED_FRAUD', 'CLEARED_LEGITIMATE') OR decision_label IS NOT NULL) AS processed_count,
                    count(*) FILTER (WHERE (inspection_status IN ('PENDING', 'NEW') OR inspection_status IS NULL) AND risk_score >= 0.80) AS critical_count,
                    count(*) FILTER (WHERE inspection_status = 'CONFIRMED_FRAUD' OR decision_label = 1) AS confirmed_fraud_count,
                    count(*) FILTER (WHERE inspection_status = 'CLEARED_LEGITIMATE' OR decision_label = 0) AS cleared_legitimate_count,
                    max(CASE WHEN inspection_status IN ('PENDING', 'NEW') OR inspection_status IS NULL THEN risk_score ELSE NULL END) AS max_risk_score
                FROM transactions;
            """)
            return db.execute(summary_sql).fetchone()

    def get_cdf_alerts_raw(self, db: Session, starting_version: Optional[int] = None, limit: int = 200) -> Tuple[List[Transaction], int, str]:
        max_ver_row = db.execute(
            text("SELECT COALESCE(MAX(delta_commit_version), 0) FROM transactions")
        ).scalar()
        current_max_version = int(max_ver_row) if max_ver_row is not None else 0

        q = db.query(Transaction)

        if starting_version is not None and starting_version >= 0:
            q = q.filter(Transaction.delta_commit_version > starting_version)
            mode = "incremental"
        else:
            q = q.filter(Transaction.inspection_status.in_(["PENDING", "NEW", None]))
            mode = "initial_snapshot"

        q = q.order_by(
            Transaction.delta_commit_version.asc().nullslast(),
            Transaction.risk_score.desc().nullslast(),
        )
        q = q.limit(limit)
        return q.all(), current_max_version, mode

alert_repository = AlertRepository()
