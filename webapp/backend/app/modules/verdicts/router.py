from typing import Optional
from fastapi import APIRouter, Depends, Path, Query
from app.core.guards import require_roles, get_current_user
from app.modules.verdicts.schemas import InspectionDecisionRequest, InspectionDecisionResponse
from app.modules.verdicts.service import verdict_service

router = APIRouter(tags=["verdicts"])

@router.post(
    "/transactions/{transaction_id}/decision",
    response_model=InspectionDecisionResponse,
    dependencies=[Depends(require_roles("auditor", "admin"))],
)
def submit_decision(
    transaction_id: str = Path(..., description="Target transaction ID"),
    req: InspectionDecisionRequest = ...,
):
    res = verdict_service.submit_inspection_verdict(
        transaction_id=transaction_id,
        label=req.label,
        inspector_id=req.inspector_id,
        reason=req.reason,
        processing_time=req.processing_time,
    )
    return res

@router.get("/alerts/inspected", dependencies=[Depends(require_roles("auditor", "admin"))])
def get_inspected_alerts(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=200, description="Page limit"),
    search: Optional[str] = Query(None, description="Search query"),
    channel: Optional[str] = Query(None, description="Channel filter: ONLINE, POS, ATM"),
    amount_range: Optional[str] = Query(None, description="Preset amount range: GT_10M, 1M_10M, LT_1M"),
    inspector_id: Optional[str] = Query(None, description="Filter by auditor ID / name"),
    from_date: Optional[str] = Query(None, alias="from", description="From date/datetime YYYY-MM-DD or ISO"),
    to_date: Optional[str] = Query(None, alias="to", description="To date/datetime YYYY-MM-DD or ISO"),
    from_time: Optional[str] = Query(None, description="Start date/time fallback"),
    to_time: Optional[str] = Query(None, description="End date/time fallback"),
    offset: Optional[int] = Query(None, ge=0, description="Manual offset"),
    min_amount: Optional[float] = Query(None, ge=0.0, description="Minimum transaction amount"),
    max_amount: Optional[float] = Query(None, ge=0.0, description="Maximum transaction amount"),
):
    return verdict_service.get_inspected_alerts(
        page=page,
        limit=limit,
        search=search,
        channel=channel,
        amount_range=amount_range,
        inspector_id=inspector_id,
        from_time=from_date or from_time,
        to_time=to_date or to_time,
        offset=offset,
        min_amount=min_amount,
        max_amount=max_amount,
    )

@router.get("/verdicts/stats", dependencies=[Depends(require_roles("auditor", "admin"))])
def get_verdicts_stats(
    period: str = Query("day", description="Aggregation period: 'day' or 'month'"),
    date: Optional[str] = Query(None, description="Vietnam-time date (YYYY-MM-DD); defaults to today"),
    month: Optional[str] = Query(None, description="Vietnam-time month (YYYY-MM); defaults to the current month"),
    current_user = Depends(get_current_user),
):
    return verdict_service.get_verdicts_stats(
        user_id=current_user.id if current_user else None,
        user_role=current_user.role if current_user else "auditor",
        period=period,
        date_str=date,
        month_str=month,
    )

