from typing import Optional
from pydantic import BaseModel

class FraudSummaryItem(BaseModel):
    trans_type: Optional[str] = None
    channel: Optional[str] = None
    total_transactions: int
    total_volume: float
    total_fraud_cases: int
    fraud_rate_percentage: float
    calculated_at: Optional[str] = None

class OverallSummaryResponse(BaseModel):
    total_transactions: int
    total_volume: float
    total_fraud_cases: int
    overall_fraud_rate_percentage: float
    categories_monitored: int
    last_calculated_at: Optional[str] = None
    channel_breakdown: Optional[dict] = None
    trans_type_breakdown: Optional[dict] = None
