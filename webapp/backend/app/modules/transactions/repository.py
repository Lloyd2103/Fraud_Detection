from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from sqlalchemy.dialects.postgresql import insert
from app.modules.transactions.models import Transaction

class TransactionRepository:
    def get_by_id(self, db: Session, transaction_id: str) -> Optional[Transaction]:
        return db.query(Transaction).filter(Transaction.transaction_id == transaction_id).first()

    def get_account_history(self, db: Session, source_account: str, limit: int = 20) -> List[Transaction]:
        return db.query(Transaction).filter(
            Transaction.source_account == source_account
        ).order_by(Transaction.timestamp.desc()).limit(limit).all()

    def update_verdict_fields(
        self,
        db: Session,
        transaction_id: str,
        inspection_status: str,
        decision_label: int,
        inspector_id: Optional[int],
        reason: Optional[str],
        updated_at: datetime,
    ) -> Optional[Transaction]:
        tx = self.get_by_id(db, transaction_id)
        if not tx:
            return None
        tx.inspection_status = inspection_status
        tx.decision_label = decision_label
        tx.inspector_id = inspector_id
        tx.reason = reason
        tx.updated_at = updated_at
        return tx

    def update_fields(self, db: Session, transaction_id: str, update_data: Dict[str, Any]) -> Optional[Transaction]:
        tx = self.get_by_id(db, transaction_id)
        if not tx:
            return None
        if update_data.get("inspection_status") is not None:
            tx.inspection_status = str(update_data["inspection_status"])
        if "decision_label" in update_data:
            val = update_data["decision_label"]
            if val is None or val == "" or str(val).lower() == "null":
                tx.decision_label = None
            else:
                tx.decision_label = int(val)
                tx.inspection_status = "CONFIRMED_FRAUD" if tx.decision_label == 1 else "CLEARED_LEGITIMATE"
        if update_data.get("inspector_id") is not None:
            tx.inspector_id = update_data["inspector_id"]
        if update_data.get("reason") is not None:
            tx.reason = str(update_data["reason"])
        tx.updated_at = datetime.utcnow()
        return tx

    def batch_upsert(self, db: Session, records: List[Dict[str, Any]], chunk_size: int = 100):
        for i in range(0, len(records), chunk_size):
            chunk = records[i : i + chunk_size]
            stmt = insert(Transaction).values(chunk)
            update_dict = {
                "risk_score": stmt.excluded.risk_score,
                "latency_ms": stmt.excluded.latency_ms,
                "top_risk_factors": stmt.excluded.top_risk_factors,
                "delta_commit_version": func.greatest(
                    Transaction.delta_commit_version,
                    stmt.excluded.delta_commit_version,
                ),
                "updated_at": stmt.excluded.updated_at,
            }
            upsert_stmt = stmt.on_conflict_do_update(
                index_elements=["transaction_id"],
                set_=update_dict,
                where=or_(
                    Transaction.inspection_status.in_(["PENDING", "NEW"]),
                    Transaction.inspection_status.is_(None),
                ),
            )
            db.execute(upsert_stmt)

transaction_repository = TransactionRepository()
