from fastapi import APIRouter, Depends

from app.core.guards import require_roles, verify_internal_secret
from app.modules.model_governance.schemas import ModelRegistryCreatePayload
from app.modules.model_governance.service import model_governance_service

router = APIRouter(tags=["model-governance"])


@router.get("/audit/model-performance", dependencies=[Depends(require_roles("analyst", "admin"))])
def get_model_performance():
    return model_governance_service.get_model_performance()


@router.get("/audit/model-registry", dependencies=[Depends(require_roles("analyst", "admin"))])
def list_model_registry():
    return model_governance_service.list_registry()


# Dual route: POST /api/audit/model-registry and POST /api/model-registry (called by the training pipeline).
@router.post("/audit/model-registry", dependencies=[Depends(verify_internal_secret)])
@router.post("/model-registry", dependencies=[Depends(verify_internal_secret)])
def register_model(payload: ModelRegistryCreatePayload):
    return model_governance_service.register_model(payload.model_dump(exclude_unset=True))
