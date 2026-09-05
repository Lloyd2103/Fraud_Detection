"""
Alert Queue API Router
Provides real-time fraud alert feed for auditor triage.
Complies with DeTai_2.pdf section 2.8:
- GET /api/alerts?status=new
"""

from typing import Optional, List
from fastapi import APIRouter, Query
from app.services.lakehouse_service import lakehouse_service

router = APIRouter(tags=["Alert Queue"])

@router.get("/alerts")
def get_alerts(
    status: Optional[str] = Query(default="new", description="Filter: new / processed / all"),
    limit: int = Query(default=50, ge=1, le=200, description="Max alerts to retrieve"),
    search: Optional[str] = Query(default=None, description="Search by ID or account number")
):
    """
    Fetch prioritized queue of suspicious transactions from Gold risk_scores table.
    Sorted descending by risk_score.
    """
    effective_status = status or "new"
    alerts = lakehouse_service.get_alert_queue(status=effective_status, limit=limit, search=search)
    return alerts

@router.get("/alerts/summary")
def get_alerts_summary():
    """
    Summary metrics for the alert queue badge and dashboard header.
    """
    all_alerts = lakehouse_service.get_alert_queue(status="all", limit=200)
    pending = [a for a in all_alerts if a.get("inspection_status") in ("PENDING", "NEW", None)]
    processed = [a for a in all_alerts if a.get("inspection_status") == "PROCESSED"]
    critical = [a for a in pending if float(a.get("risk_score", 0.0)) >= 0.80]
    
    return {
        "total_alerts": len(all_alerts),
        "pending_count": len(pending),
        "processed_count": len(processed),
        "critical_count": len(critical),
        "max_risk_score": max([float(a.get("risk_score", 0)) for a in pending], default=0.0),
        "sla_target_daily": 200
    }