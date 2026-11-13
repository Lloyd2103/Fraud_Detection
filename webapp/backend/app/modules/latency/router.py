from fastapi import APIRouter, Depends
from app.core.guards import require_roles
from app.modules.latency.service import latency_service

router = APIRouter(tags=["latency"])

@router.get("/latency/stats", dependencies=[Depends(require_roles("analyst", "admin"))])
def get_latency_statistics():
    return latency_service.get_latency_stats()

