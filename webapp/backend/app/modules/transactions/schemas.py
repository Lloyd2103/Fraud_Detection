from typing import Optional, Any, List
from pydantic import BaseModel, Field

class TransactionUpdateRequest(BaseModel):
    inspection_status: Optional[str] = Field(default=None, description="Status: PENDING, CONFIRMED_FRAUD, CLEARED_LEGITIMATE")
    decision_label: Optional[int] = Field(default=None, description="0 = Legitimate, 1 = Fraud")
    inspector_id: Optional[str] = Field(default=None, description="Auditor ID or email")
    reason: Optional[str] = Field(default=None, description="Investigation reason / notes")

class TransactionDetailResponse(BaseModel):
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

