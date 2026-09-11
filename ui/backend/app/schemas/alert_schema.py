# Pydantic schemas for request and response validation
from typing import List, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field

class RiskFactor(BaseModel):
    name: str
    contribution: float

class AlertResponse(BaseModel):
    transaction_id: str
    risk_score: float
    inspection_status: str
    model_version: Optional[str] = "GBT_v1.0"
    latency_ms: Optional[int] = 120
    scored_at: Optional[str] = None

class TransactionDetailResponse(BaseModel):
    transaction_id: str
    risk_score: float
    inspection_status: str
    model_version: Optional[str] = "GBT_v1.0"
    latency_ms: Optional[int] = 120
    top_risk_factors: Optional[List[RiskFactor]] = []
    source_account: Optional[str] = None
    dest_account: Optional[str] = None
    amount: Optional[float] = None
    trans_type: Optional[str] = None
    channel: Optional[str] = None
    timestamp: Optional[str] = None

class VerdictSubmissionRequest(BaseModel):
    decision: int = Field(..., description="1 for Fraud, 0 for Legitimate")
    auditor: str = Field(..., min_length=1, description="Auditor username or ID")
    reason: str = Field(..., min_length=1, description="Reason category or remarks")
    handling_time_seconds: int = Field(..., ge=0, description="Handling duration in seconds")

class VerdictResponse(BaseModel):
    status: str
    transaction_id: str
    message: str