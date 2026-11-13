from typing import Optional
from fastapi import APIRouter, Depends, Query
from app.core.guards import require_roles
from app.modules.fraud_summary.service import fraud_summary_service

router = APIRouter(tags=["fraud-summary"])

@router.get("/fraud-summary")
def get_fraud_summary(
    trans_type: Optional[str] = Query(None, description="Transaction type filter: TRANSFER, PAYMENT, CASH_OUT"),
    channel: Optional[str] = Query(None, description="Channel filter: ONLINE, POS, ATM"),
):
    return fraud_summary_service.get_summary(trans_type=trans_type, channel=channel)

@router.get("/fraud-summary/overall")
def get_fraud_summary_overall():
    return fraud_summary_service.get_overall()

@router.post("/fraud-summary/recalculate", dependencies=[Depends(require_roles("admin"))])
def recalculate_fraud_summary():
    return fraud_summary_service.recalculate()

