from typing import Optional
from fastapi import APIRouter, Depends, Query
from app.core.guards import require_roles
from app.modules.alerts.schemas import AlertSummaryOut
from app.modules.alerts.service import alert_service

router = APIRouter(tags=["alerts"])

@router.get("/alerts", dependencies=[Depends(require_roles("auditor", "admin"))])
def get_alerts(
    status: Optional[str] = Query(None, description="Status filter: PENDING, PROCESSED, ALL"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=200, description="Page limit"),
    search: Optional[str] = Query(None, description="Search transaction_id, accounts, reason"),
    channel: Optional[str] = Query(None, description="Channel filter: ONLINE, POS, ATM"),
    amount_range: Optional[str] = Query(None, description="Amount range: GT_5M, 1M_5M, LT_1M"),
    min_amount: Optional[float] = Query(None, ge=0.0, description="Minimum transaction amount"),
    max_amount: Optional[float] = Query(None, ge=0.0, description="Maximum transaction amount"),
    sort_by: Optional[str] = Query("risk_score", description="Sort column (prefix with '-' or append ':desc' for descending)"),
    order: Optional[str] = Query("desc", description="Sort order: asc, desc"),
    offset: Optional[int] = Query(None, ge=0, description="Manual offset bypasses page calculation"),
):
    return alert_service.get_pending_alerts(
        page=page,
        limit=limit,
        offset=offset,
        search=search,
        channel=channel,
        amount_range=amount_range,
        min_amount=min_amount,
        max_amount=max_amount,
        sort_by=sort_by,
        order=order,
    )

@router.get("/alerts/summary", response_model=AlertSummaryOut, dependencies=[Depends(require_roles("auditor", "admin"))])
def get_alerts_summary():
    return alert_service.get_alerts_summary()

@router.get("/alerts/cdf", dependencies=[Depends(require_roles("auditor", "admin"))])
def get_alerts_cdf(
    starting_version: int = Query(0, ge=0, description="Delta commit version cursor"),
    limit: int = Query(200, ge=1, le=1000, description="Max change records to return"),
):
    return alert_service.get_cdf_alerts(starting_version=starting_version, limit=limit)

