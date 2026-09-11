"""
Alert Queue API Router
Provides real-time fraud alert feed for auditor triage.
Complies with DeTai_2.pdf section 2.8:
- GET /api/canhbao?trang_thai=moi
- Dual compatibility with GET /api/alerts?status=new
"""

from typing import Optional, List
from fastapi import APIRouter, Query
from app.services.lakehouse_service import lakehouse_service

router = APIRouter(tags=["Alert Queue & Canh Bao"])

@router.get("/canhbao")
@router.get("/alerts")
def get_alerts(
    status: Optional[str] = Query(default=None, description="Filter: new / processed / all"),
    trang_thai: Optional[str] = Query(default=None, description="Filter: moi / da_xu_ly / tat_ca"),
    limit: int = Query(default=50, ge=1, le=200, description="Max alerts to retrieve"),
    gioi_han: Optional[int] = Query(default=None, ge=1, le=200, description="Gioi han so ban ghi"),
    search: Optional[str] = Query(default=None, description="Search by ID or account number"),
    tim_kiem: Optional[str] = Query(default=None, description="Tim kiem theo ma hoac tai khoan")
):
    """
    Fetch prioritized queue of suspicious transactions from Gold risk_scores / diem_rui_ro table.
    Complies with GET /api/canhbao?trang_thai=moi (DeTai2.pdf Section 2.8).
    """
    effective_limit = gioi_han or limit or 50
    effective_search = tim_kiem or search
    alerts = lakehouse_service.get_alert_queue(
        status=status,
        trang_thai=trang_thai,
        limit=effective_limit,
        search=effective_search,
        tim_kiem=effective_search
    )
    return alerts

@router.get("/canhbao/tong-quan")
@router.get("/alerts/summary")
def get_alerts_summary():
    """
    Summary metrics for the alert queue badge and dashboard header.
    """
    all_alerts = lakehouse_service.get_alert_queue(status="all", limit=200)
    pending = [a for a in all_alerts if a.get("inspection_status") in ("PENDING", "NEW", "moi", None)]
    processed = [a for a in all_alerts if a.get("inspection_status") in ("PROCESSED", "da_xu_ly")]
    critical = [a for a in pending if float(a.get("risk_score") or a.get("diem_rui_ro") or 0.0) >= 0.80]

    return {
        "total_alerts": len(all_alerts),
        "tong_so_canh_bao": len(all_alerts),
        "pending_count": len(pending),
        "so_canh_bao_chua_xu_ly": len(pending),
        "processed_count": len(processed),
        "so_canh_bao_da_xu_ly": len(processed),
        "critical_count": len(critical),
        "so_canh_bao_nghiem_trong": len(critical),
        "max_risk_score": max([float(a.get("risk_score") or a.get("diem_rui_ro") or 0) for a in pending], default=0.0),
        "diem_rui_ro_cao_nhat": max([float(a.get("risk_score") or a.get("diem_rui_ro") or 0) for a in pending], default=0.0),
        "sla_target_daily": 200,
        "chi_tieu_ngay": 200
    }

@router.get("/canhbao/cdf")
@router.get("/alerts/cdf")
def get_alerts_cdf(
    starting_version: int = Query(default=0, ge=0, description="Delta Table Version to stream changes from"),
    phien_ban_bat_dau: Optional[int] = Query(default=None, ge=0, description="Phien ban Delta bat dau doc")
):
    """
    Delta Lake Change Data Feed (CDF) Endpoint (DeTai_2.pdf 2.7).
    Web app reads CDF of gold.diem_rui_ro to incrementally update the alert queue without scanning the full table.
    """
    eff_version = phien_ban_bat_dau if phien_ban_bat_dau is not None else starting_version
    return lakehouse_service.get_cdf_alerts(starting_version=eff_version)