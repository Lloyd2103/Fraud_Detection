"""
Latency & System Health API Router
Monitors End-to-End Latency distribution (P50, P95, P99)
Complies with DeTai_2.pdf section 2.8 requirement (< 5 seconds SLA).
"""

from fastapi import APIRouter
from app.services.lakehouse_service import lakehouse_service

router = APIRouter(tags=["Latency & SLA / Do Tre He Thong"])

@router.get("/do-tre/thong-ke")
@router.get("/latency/stats")
def get_latency_statistics():
    """
    Get End-to-End Latency distribution (P50, P95, P99) from Kafka arrival to Web UI alert.
    """
    return lakehouse_service.get_latency_stats()
