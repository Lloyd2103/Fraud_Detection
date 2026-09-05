"""
Pydantic Schemas for Fraud Inspection Decisions and Auditor Verdicts.
Complies with DeTai_2.pdf silver.inspection_decisions specifications.
"""

from typing import Optional
from pydantic import BaseModel, Field

class InspectionDecisionRequest(BaseModel):
    label: int = Field(..., description="0 = Legitimate, 1 = Fraud")
    inspector_id: str = Field(default="Auditor_01", description="Auditor / Inspector ID")
    reason: Optional[str] = Field(default="Suspicious transaction pattern", description="Reason for verdict")
    processing_time_seconds: Optional[int] = Field(default=5, description="Inspection duration in seconds")

class InspectionDecisionResponse(BaseModel):
    status: str
    message: str
    transaction_id: str
    label: int
    inspector_id: str
    decision_timestamp: str