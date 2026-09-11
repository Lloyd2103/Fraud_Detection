"""
Transaction Detail & Auditor Decision API Router
Complies with DeTai_2.pdf section 2.8:
- GET /api/giaodich/{id}
- POST /api/giaodich/{id}/ket-luan
Dual compatibility with:
- GET /api/transactions/{id}
- POST /api/transactions/{id}/decision
"""

from fastapi import APIRouter, HTTPException
from app.schemas.decision import InspectionDecisionRequest, InspectionDecisionResponse
from app.services.lakehouse_service import lakehouse_service

router = APIRouter(tags=["Transactions & Inspection / Giao Dich & Tham Dinh"])

@router.get("/giaodich/{transaction_id}")
@router.get("/transactions/{transaction_id}")
def get_transaction_detail(transaction_id: str):
    """
    Fetch single transaction detailed metrics:
    - Core transaction info (amount, balances, channel, type)
    - Top 3 risk factors
    - Last 20 transactions of the source account
    - Timeline plot data with current transaction highlighted
    """
    data = lakehouse_service.get_transaction_detail(transaction_id)
    if not data or not data.get("detail"):
        raise HTTPException(
            status_code=404,
            detail=f"Transaction not found with ID {transaction_id} / Khong tim thay giao dich {transaction_id}"
        )
    return data

@router.post("/giaodich/{transaction_id}/ket-luan", response_model=InspectionDecisionResponse)
@router.post("/transactions/{transaction_id}/decision", response_model=InspectionDecisionResponse)
def submit_decision(transaction_id: str, body: InspectionDecisionRequest):
    """
    Write-back inspection verdict to Delta Lake (silver.inspection_decisions)
    Feeds back into Airflow DAG 3 for weekly retraining!
    """
    try:
        label = body.label
        inspector = body.inspector_id
        reason = body.reason or "Kiem tra mau giao dich"
        processing_time = body.processing_time or 5

        result = lakehouse_service.submit_inspection_verdict(
            transaction_id=transaction_id,
            label=label,
            inspector_id=inspector,
            reason=reason,
            processing_time=processing_time
        )
        return InspectionDecisionResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving inspection verdict: {str(e)}")