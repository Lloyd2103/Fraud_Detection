from fastapi import APIRouter
from app.modules.health.service import health_service

router = APIRouter(tags=["health"])

@router.get("/health")
def health_check():
    return health_service.get_system_health()

@router.get("/health/pipeline")
def get_pipeline_health():
    return health_service.get_pipeline_health()

