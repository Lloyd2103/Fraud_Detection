"""
Alerts Schemas
"""
from typing import Optional, List, Any
from pydantic import BaseModel

class AlertItemOut(BaseModel):
    transaction_id: str
    source_account: str
    dest_account: Optional[str] = None
    trans_type: Optional[str] = "TRANSFER"
    amount: float
    channel: Optional[str] = "ONLINE"
    timestamp: Optional[str] = None
    received_at: Optional[str] = None
    risk_score: float
    prediction_label: int = 1
    model_version: Optional[str] = "GBT_v1.0"
    latency_ms: Optional[int] = None
    inspection_status: str = "PENDING"
    decision_label: Optional[int] = None
    inspector_id: Optional[str] = None
    reason: Optional[str] = None
    decision_timestamp: Optional[str] = None
    top_risk_factors: Optional[List[Any]] = []
    old_balance_source: Optional[float] = None
    new_balance_source: Optional[float] = None
    old_balance_dest: Optional[float] = None
    new_balance_dest: Optional[float] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

class AlertSummaryOut(BaseModel):
    total_alerts: int
    pending_count: int
    processed_count: int
    critical_count: int
    confirmed_fraud_count: int
    cleared_legitimate_count: int
    my_processed_count: int
    my_confirmed_fraud_count: int
    my_cleared_legitimate_count: int
    max_risk_score: float
    sla_target_daily: int = 200

