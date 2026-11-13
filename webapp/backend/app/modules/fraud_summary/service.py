from datetime import datetime
from typing import Optional, Dict, Any
from app.database.session import SessionLocal
from app.modules.fraud_summary.repository import fraud_summary_repository

SOURCE_LABEL = "CockroachDB table fraud_summary (aggregated from table transactions)"
SCOPE_NOTE = (
    "The serving table holds only transactions flagged by the model (risk score >= 0.5), not every transaction. "
    "'Flagged' counts and the fraud share are therefore relative to flagged rows only; "
    "the share is not a fraud rate over all card transactions. "
    "'Fraud cases' = auditor verdict when one exists, otherwise the model's predicted label. "
    "The currency of amounts is not specified in the source data."
)

class FraudSummaryService:
    def get_summary(
        self,
        trans_type: Optional[str] = None,
        channel: Optional[str] = None,
    ) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            records = fraud_summary_repository.get_filtered(db, trans_type=trans_type, channel=channel)
            items = [r.to_dict() for r in records]

            all_records = fraud_summary_repository.get_all(db)
            total_txs = sum(int(r.total_transactions or 0) for r in all_records)
            total_vol = sum(float(r.total_volume or 0.0) for r in all_records)
            total_frauds = sum(int(r.total_fraud_cases or 0) for r in all_records)
            overall_rate = round((total_frauds / total_txs * 100), 4) if total_txs > 0 else 0.0

            latest_calc = None
            if all_records:
                dates = [r.calculated_at for r in all_records if r.calculated_at]
                if dates:
                    latest_calc = max(dates).isoformat()

            by_channel = {}
            for r in all_records:
                ch = r.channel or "UNKNOWN"
                if ch not in by_channel:
                    by_channel[ch] = {"total_transactions": 0, "total_volume": 0.0, "total_fraud_cases": 0}
                by_channel[ch]["total_transactions"] += int(r.total_transactions or 0)
                by_channel[ch]["total_volume"] += round(float(r.total_volume or 0.0), 2)
                by_channel[ch]["total_fraud_cases"] += int(r.total_fraud_cases or 0)

            for ch, val in by_channel.items():
                val["fraud_rate_percentage"] = (
                    round((val["total_fraud_cases"] / val["total_transactions"] * 100), 4)
                    if val["total_transactions"] > 0
                    else 0.0
                )

            by_trans_type = {}
            for r in all_records:
                tt = r.trans_type or "UNKNOWN"
                if tt not in by_trans_type:
                    by_trans_type[tt] = {"total_transactions": 0, "total_volume": 0.0, "total_fraud_cases": 0}
                by_trans_type[tt]["total_transactions"] += int(r.total_transactions or 0)
                by_trans_type[tt]["total_volume"] += round(float(r.total_volume or 0.0), 2)
                by_trans_type[tt]["total_fraud_cases"] += int(r.total_fraud_cases or 0)

            for tt, val in by_trans_type.items():
                val["fraud_rate_percentage"] = (
                    round((val["total_fraud_cases"] / val["total_transactions"] * 100), 4)
                    if val["total_transactions"] > 0
                    else 0.0
                )

            return {
                "status": "success",
                "count": len(items),
                "data": items,
                "source": SOURCE_LABEL,
                "scope_note": SCOPE_NOTE,
                "overall": {
                    "flagged_transactions": total_txs,
                    "total_transactions": total_txs,
                    "total_volume": round(total_vol, 2),
                    "total_fraud_cases": total_frauds,
                    "overall_fraud_rate_percentage": overall_rate,
                    "last_calculated_at": latest_calc,
                },
                "by_channel": by_channel,
                "by_trans_type": by_trans_type,
            }
        finally:
            db.close()

    def get_overall(self) -> Dict[str, Any]:
        summary = self.get_summary()
        return {
            "status": "success",
            "overall": summary.get("overall", {}),
            "by_channel": summary.get("by_channel", {}),
            "by_trans_type": summary.get("by_trans_type", {}),
        }

    def recalculate(self) -> Dict[str, Any]:
        db = SessionLocal()
        try:
            agg_rows = fraud_summary_repository.aggregate_from_transactions(db)
            now = datetime.utcnow()
            updated_count = fraud_summary_repository.upsert_summary_rows(db, agg_rows, now)

            return {
                "status": "success",
                "message": f"Recomputed the CockroachDB fraud_summary table for {updated_count} groups from the transactions table. The Delta Gold layer was not touched.",
                "categories_updated": updated_count,
                "calculated_at": now.isoformat(),
            }
        except Exception as e:
            db.rollback()
            return {"status": "error", "message": f"Recompute failed: {str(e)[:200]}"}
        finally:
            db.close()

fraud_summary_service = FraudSummaryService()
