from typing import Optional
from pydantic import BaseModel, Field, model_validator

class InspectionDecisionRequest(BaseModel):
    # English field names
    label: Optional[int] = Field(default=None, description="0 = Legitimate, 1 = Fraud")
    inspector_id: Optional[str] = Field(default=None, description="Auditor / Inspector ID")
    reason: Optional[str] = Field(default=None, description="Reason for verdict")
    processing_time: Optional[int] = Field(default=None, description="Inspection duration in seconds")

    # Vietnamese field names (backward compatibility)
    nhan: Optional[int] = Field(default=None, description="0 = Hop le, 1 = Gian lan")
    nguoi_tham_dinh: Optional[str] = Field(default=None, description="Ten / Ma nguoi tham dinh")
    ly_do: Optional[str] = Field(default=None, description="Ly do ket luan")
    thoi_gian_xu_ly_giay: Optional[int] = Field(default=None, description="Thoi gian xu ly tinh bang giay")

    @model_validator(mode="after")
    def synchronize_bilingual_fields(self):
        resolved_label = self.nhan if self.nhan is not None else self.label
        if resolved_label is None:
            resolved_label = 0
        self.label = resolved_label
        self.nhan = resolved_label

        resolved_inspector = self.nguoi_tham_dinh or self.inspector_id
        self.inspector_id = resolved_inspector
        self.nguoi_tham_dinh = resolved_inspector

        resolved_reason = self.ly_do or self.reason or "Xac minh giao dich"
        self.reason = resolved_reason
        self.ly_do = resolved_reason

        resolved_time = self.thoi_gian_xu_ly_giay if self.thoi_gian_xu_ly_giay is not None else (self.processing_time if self.processing_time is not None else 0)
        self.processing_time = resolved_time
        self.thoi_gian_xu_ly_giay = resolved_time
        return self

class InspectionDecisionResponse(BaseModel):
    status: str
    message: str
    transaction_id: str
    label: int
    inspector_id: str
    decision_timestamp: str
    reason: Optional[str] = None
    processing_time: Optional[int] = None
    persisted_to_delta: bool = False
    persisted_to_cockroachdb: bool = False
    
    ma_giao_dich: Optional[str] = None
    nhan: Optional[int] = None
    nguoi_tham_dinh: Optional[str] = None
    thoi_diem_ket_luan: Optional[str] = None
    ly_do: Optional[str] = None

