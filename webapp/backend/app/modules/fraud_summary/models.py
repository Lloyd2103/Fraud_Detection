from datetime import datetime
from sqlalchemy import Column, BigInteger, Float, String, DateTime
from app.database.base import Base

class FraudSummary(Base):
    __tablename__ = "fraud_summary"

    rowid = Column(BigInteger, primary_key=True, autoincrement=True)
    trans_type = Column(String(64), nullable=True)
    channel = Column(String(64), nullable=True)
    total_transactions = Column(BigInteger, nullable=False, default=0)
    total_volume = Column(Float, nullable=True, default=0.0)
    total_fraud_cases = Column(BigInteger, nullable=True, default=0)
    fraud_rate_percentage = Column(Float, nullable=True, default=0.0)
    calculated_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {
            "trans_type": self.trans_type,
            "channel": self.channel,
            "total_transactions": int(self.total_transactions or 0),
            "total_volume": round(float(self.total_volume or 0.0), 2),
            "total_fraud_cases": int(self.total_fraud_cases or 0),
            "fraud_rate_percentage": round(float(self.fraud_rate_percentage or 0.0), 4),
            "calculated_at": self.calculated_at.isoformat() if self.calculated_at else None,
        }

