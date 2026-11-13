"""
SQLAlchemy Model for Transaction
Table: transactions
"""
from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, Text, JSON, Index, ForeignKey
from sqlalchemy.orm import relationship
from app.database.base import Base

class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id    = Column(String(64), primary_key=True, index=True)
    source_account    = Column(String(64), nullable=False, index=True)
    dest_account      = Column(String(64), nullable=True, index=True)
    trans_type        = Column(String(32), nullable=True)
    amount            = Column(Float, nullable=False, default=0.0)
    channel           = Column(String(32), nullable=True)
    timestamp         = Column(DateTime, nullable=True, index=True)
    received_at       = Column(DateTime, nullable=True)
    
    risk_score        = Column(Float, nullable=False, default=0.0, index=True)
    prediction_label  = Column(Integer, default=1, nullable=False)
    model_version     = Column(String(32), default="GBT_v1.0")
    latency_ms        = Column(Integer, nullable=True)
    
    inspection_status = Column(String(32), default="PENDING", index=True)
    decision_label    = Column(Integer, nullable=True)
    inspector_id      = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    reason            = Column(Text, nullable=True)
    
    top_risk_factors  = Column(JSON, nullable=True)
    old_balance_source = Column(Float, nullable=True)
    new_balance_source = Column(Float, nullable=True)
    old_balance_dest   = Column(Float, nullable=True)
    new_balance_dest   = Column(Float, nullable=True)

    delta_commit_version = Column(Integer, nullable=True, index=True)

    created_at        = Column(DateTime, default=datetime.utcnow)
    updated_at        = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    inspector         = relationship("User", foreign_keys=[inspector_id])

    __table_args__ = (
        Index("idx_tx_pending_risk", "inspection_status", risk_score.desc()),
        Index("idx_tx_cdf_version", "delta_commit_version"),
    )

