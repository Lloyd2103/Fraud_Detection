from typing import Optional

from fastapi import APIRouter, Depends, Path, Query

from app.core.guards import require_roles, get_current_user
from app.modules.time_travel.service import time_travel_service

router = APIRouter(tags=["time-travel"])

_TABLE_HELP = "Delta table: features, silver/transactions, silver/customer_states, silver/inspection_decisions, gold/risk_scores"


@router.get("/audit/time-travel/{delta_version}", dependencies=[Depends(require_roles("analyst", "admin"))])
def audit_time_travel(
    delta_version: int = Path(..., ge=0, description="Delta table version number"),
    table: str = Query("gold/risk_scores", description=_TABLE_HELP),
):
    return time_travel_service.get_time_travel_audit(delta_version=delta_version, table_name=table)


# `/kiemtoan/{version}` is kept as a legacy alias of `/audit/by-version/{version}`.
@router.get("/audit/by-version/{version}", dependencies=[Depends(require_roles("analyst", "admin"))])
@router.get("/kiemtoan/{version}", dependencies=[Depends(require_roles("analyst", "admin"))], include_in_schema=False)
def audit_by_version(
    version: str = Path(..., description="Model version (e.g. 'GBT_20261016_1541') or a Delta version number"),
    table: Optional[str] = Query(None, description="Optional Delta table (defaults to the table linked in model_registry, else features)"),
):
    return time_travel_service.audit_by_version(version=version, table=table)


@router.post("/audit/rerun-eval/{delta_version}", dependencies=[Depends(require_roles("analyst", "admin"))])
def rerun_audit_evaluation(
    delta_version: int = Path(..., ge=0, description="Delta table version number"),
    table: str = Query("gold/risk_scores", description="Reference table"),
    force_recompute: bool = Query(False, description="Ignore saved evaluation results (admin only)"),
    current_user=Depends(get_current_user),
):
    is_admin = getattr(current_user, "role", "") == "admin"
    return time_travel_service.rerun_evaluation(
        delta_version=delta_version,
        table_name=table,
        force_recompute=force_recompute,
        is_admin=is_admin,
    )


@router.get("/audit/trail", dependencies=[Depends(require_roles("analyst", "admin"))])
def get_audit_trail(limit: int = Query(50, ge=1, le=500)):
    return time_travel_service.get_audit_trail(limit=limit)


@router.get("/audit/commits", dependencies=[Depends(require_roles("analyst", "admin"))])
def get_delta_commits(
    limit: int = Query(145, ge=1, le=2000),
    table: str = Query("gold/risk_scores", description=_TABLE_HELP),
):
    return time_travel_service.get_delta_commits(limit=limit, table_name=table)
