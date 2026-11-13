from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.modules.fraud_summary.models import FraudSummary

class FraudSummaryRepository:
    def get_filtered(self, db: Session, trans_type: Optional[str] = None, channel: Optional[str] = None) -> List[FraudSummary]:
        q = db.query(FraudSummary)
        if trans_type and trans_type.strip() and trans_type.upper() != "ALL":
            q = q.filter(FraudSummary.trans_type.ilike(trans_type.strip()))
        if channel and channel.strip() and channel.upper() != "ALL":
            q = q.filter(FraudSummary.channel.ilike(channel.strip()))
        return q.all()

    def get_all(self, db: Session) -> List[FraudSummary]:
        return db.query(FraudSummary).all()

    def aggregate_from_transactions(self, db: Session):
        return db.execute(text("""
            SELECT 
                COALESCE(trans_type, 'UNKNOWN') AS trans_type,
                COALESCE(channel, 'UNKNOWN') AS channel,
                count(*) AS total_tx,
                COALESCE(sum(amount), 0.0) AS total_vol,
                count(*) FILTER (WHERE decision_label = 1 OR (decision_label IS NULL AND prediction_label = 1)) AS total_fraud
            FROM transactions
            GROUP BY COALESCE(trans_type, 'UNKNOWN'), COALESCE(channel, 'UNKNOWN');
        """)).fetchall()

    def upsert_summary_rows(self, db: Session, agg_rows: list, now: datetime) -> int:
        upsert_stmt = text("""
            INSERT INTO fraud_summary (
                trans_type, channel, total_transactions, total_volume, 
                total_fraud_cases, fraud_rate_percentage, calculated_at
            )
            VALUES (:tt, :ch, :total_tx, :total_vol, :total_fr, :fr_pct, :now)
            ON CONFLICT (trans_type, channel) DO UPDATE SET
                total_transactions = EXCLUDED.total_transactions,
                total_volume = EXCLUDED.total_volume,
                total_fraud_cases = EXCLUDED.total_fraud_cases,
                fraud_rate_percentage = EXCLUDED.fraud_rate_percentage,
                calculated_at = EXCLUDED.calculated_at;
        """)

        updated_count = 0
        for r in agg_rows:
            tt = str(r[0])
            ch = str(r[1])
            t_tx = int(r[2] or 0)
            t_vol = round(float(r[3] or 0.0), 2)
            t_fr = int(r[4] or 0)
            fr_pct = round((t_fr / t_tx * 100), 4) if t_tx > 0 else 0.0

            db.execute(upsert_stmt, {
                "tt": tt,
                "ch": ch,
                "total_tx": t_tx,
                "total_vol": t_vol,
                "total_fr": t_fr,
                "fr_pct": fr_pct,
                "now": now,
            })
            updated_count += 1

        db.commit()
        return updated_count

fraud_summary_repository = FraudSummaryRepository()
