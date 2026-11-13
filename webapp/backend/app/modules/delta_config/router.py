from fastapi import APIRouter, Depends
from app.core.guards import require_roles
from app.modules.delta_config.service import delta_config_service

router = APIRouter(prefix="/delta", tags=["delta-config"])

@router.get("/config", dependencies=[Depends(require_roles("analyst", "admin"))])
def get_delta_configuration():
    return delta_config_service.get_delta_configuration()

