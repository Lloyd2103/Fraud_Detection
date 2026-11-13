import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database.session import SessionLocal
from app.modules.transactions.models import Transaction
from app.modules.transactions.repository import transaction_repository
from app.modules.users.service import user_service
from app.common.helpers import safe_int, safe_float
from app.core.exceptions import NotFoundError

def to_iso_z(dt: Any) -> Optional[str]:
    if not dt:
        return None
    if isinstance(dt, str):
        s = dt.strip()
        if not s:
            return None
        if s.endswith("Z") or "+" in s:
            return s
        return s.replace(" ", "T") + "Z"
    if hasattr(dt, "strftime"):
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    return str(dt)

class TransactionService:
    def tx_to_dict(self, tx: Transaction, decided_at: Any = None) -> Dict[str, Any]:
        ts_str = to_iso_z(tx.timestamp)
        rcv_str = to_iso_z(tx.received_at)
        dec_ts = to_iso_z(decided_at) if decided_at else (to_iso_z(tx.updated_at) if tx.decision_label is not None else None)

        return {
            "transaction_id": str(tx.transaction_id),
            "source_account": str(tx.source_account or ""),
            "dest_account": str(tx.dest_account or ""),
            "amount": safe_float(tx.amount),
            "trans_type": tx.trans_type,
            "channel": tx.channel,
            "timestamp": ts_str,
            "received_at": rcv_str,
            "risk_score": safe_float(tx.risk_score),
            "prediction_label": safe_int(tx.prediction_label) if tx.prediction_label is not None else None,
            "model_version": tx.model_version,
            "latency_ms": safe_int(tx.latency_ms) if tx.latency_ms is not None else None,
            "inspection_status": str(tx.inspection_status or "PENDING"),
            "decision_label": tx.decision_label,
            "inspector_id": str(tx.inspector_id) if tx.inspector_id is not None else None,
            "inspector_name": tx.inspector.full_name if getattr(tx, "inspector", None) else (str(tx.inspector_id) if tx.inspector_id else None),
            "inspector_username": tx.inspector.username if getattr(tx, "inspector", None) else None,
            "inspector_email": tx.inspector.email if getattr(tx, "inspector", None) else None,
            "inspector_role": tx.inspector.role if getattr(tx, "inspector", None) else None,
            "reason": tx.reason,
            "decision_timestamp": dec_ts,
            "top_risk_factors": tx.top_risk_factors or [],
            "old_balance_source": safe_float(tx.old_balance_source),
            "new_balance_source": safe_float(tx.new_balance_source),
            "old_balance_dest": safe_float(tx.old_balance_dest),
            "new_balance_dest": safe_float(tx.new_balance_dest),
            "created_at": to_iso_z(tx.created_at),
            "updated_at": to_iso_z(tx.updated_at),
        }

    def get_transaction_detail(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        db = SessionLocal()
        try:
            tx = transaction_repository.get_by_id(db, transaction_id)
            if not tx:
                return None

            decided_at = None
            if tx.decision_label is not None:
                row = db.execute(
                    text("SELECT decided_at FROM inspection_decisions WHERE transaction_id = :tx_id ORDER BY decided_at DESC LIMIT 1"),
                    {"tx_id": transaction_id}
                ).fetchone()
                if row and row[0]:
                    decided_at = row[0]

            detail = self.tx_to_dict(tx, decided_at=decided_at)
            history_rows = transaction_repository.get_account_history(db, tx.source_account, limit=20)
            history = [self.tx_to_dict(h) for h in history_rows]

            timeline = [
                {
                    "time": str(h.get("timestamp") or ""),
                    "amount": safe_float(h.get("amount")),
                    "is_current": str(h.get("transaction_id") or "") == transaction_id,
                    "trans_type": str(h.get("trans_type") or ""),
                    "is_fraud": safe_int(h.get("decision_label") if h.get("decision_label") is not None else h.get("prediction_label")),
                }
                for h in history
            ]

            raw_factors = tx.top_risk_factors or []
            if isinstance(raw_factors, str):
                try:
                    raw_factors = json.loads(raw_factors)
                except Exception:
                    raw_factors = []
            if isinstance(raw_factors, dict):
                raw_factors = list(raw_factors.values())

            risk_factors: List[Dict[str, Any]] = []
            for item in raw_factors:
                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    name, val = str(item[0]), item[1]
                    contrib = None
                elif isinstance(item, dict):
                    name = str(item.get("feature_name") or item.get("name") or "")
                    val = item.get("value")
                    contrib = safe_float(item.get("contribution") if item.get("contribution") is not None else item.get("weight"))
                else:
                    continue
                risk_factors.append({
                    "name": name,
                    "feature_name": name,
                    "weight": contrib,
                    "contribution": contrib,
                    "value": val,
                    "description": "",
                    "severity": "CRITICAL" if (contrib is not None and abs(contrib) >= 0.5) or safe_float(tx.risk_score) >= 0.8 else "NORMAL",
                })

            return {
                "detail": detail,
                "risk_score": detail["risk_score"],
                "risk_factors": risk_factors,
                "recent_history": history,
                "timeline_points": timeline,
                "model_version": detail["model_version"],
            }
        finally:
            db.close()

    def update_transaction(self, transaction_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        db = SessionLocal()
        try:
            inspector_input = update_data.get("inspector_id")
            resolved_uid = user_service.resolve_user_id(db, inspector_input) if inspector_input else None
            data_to_update = dict(update_data)
            if resolved_uid:
                data_to_update["inspector_id"] = resolved_uid

            tx = transaction_repository.update_fields(db, transaction_id, data_to_update)
            if not tx:
                return None
            
            # If verdict changed via PUT, record to inspection_decisions as well
            if tx.decision_label is not None and "decision_label" in update_data:
                from app.modules.verdicts.service import verdict_service
                verdict_service.record_verdict_entry(
                    db=db,
                    transaction_id=transaction_id,
                    label=tx.decision_label,
                    status=tx.inspection_status,
                    inspector_id=tx.inspector_id,
                    reason=tx.reason or "Updated via PUT /transactions",
                    proc_time=0
                )

            db.commit()
            db.refresh(tx)
            return self.tx_to_dict(tx)
        finally:
            db.close()

    def update_transaction_for_verdict(
        self,
        db: Session,
        transaction_id: str,
        new_status: str,
        label: int,
        resolved_uid: Optional[int],
        reason: Optional[str],
        now_dt: datetime,
    ) -> Transaction:
        tx = transaction_repository.update_verdict_fields(
            db=db,
            transaction_id=transaction_id,
            inspection_status=new_status,
            decision_label=label,
            inspector_id=resolved_uid,
            reason=reason,
            updated_at=now_dt,
        )
        if not tx:
            raise NotFoundError(f"Transaction not found: {transaction_id}")
        return tx


transaction_service = TransactionService()
