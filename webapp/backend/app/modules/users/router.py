from fastapi import APIRouter, Depends, Path, Request
from app.database.session import get_db
from app.core.guards import require_roles, get_current_user
from app.modules.users.schemas import RegisterRequest, UserUpdateRequest, UserOut
from app.modules.users.service import user_service
from app.core.limiter import limiter

router = APIRouter(tags=["users"])

@router.post("/auth/register", response_model=UserOut, status_code=201)
@limiter.limit("5/minute")
def register(request: Request, req: RegisterRequest, db = Depends(get_db)):
    return user_service.register_user(
        db=db,
        full_name=req.full_name,
        email=req.email,
        password=req.password,
        username=req.username,
    )

@router.get("/auth/users", dependencies=[Depends(require_roles("admin"))])
def get_all_users(db = Depends(get_db)):
    users = user_service.list_users(db)
    return [{
        "id": str(u.id),
        "username": u.username,
        "full_name": u.full_name,
        "email": u.email,
        "role": u.role,
        "status": u.status,
        "created_at": u.created_at.strftime("%Y-%m-%dT%H:%M:%SZ") if u.created_at else None,
        "last_login_at": u.last_login_at.strftime("%Y-%m-%dT%H:%M:%SZ") if u.last_login_at else None,
    } for u in users]

@router.patch("/auth/users/{user_id}", response_model=UserOut, dependencies=[Depends(require_roles("admin"))])
def update_user_role_status(
    user_id: int = Path(..., description="Target User ID"),
    req: UserUpdateRequest = ...,
    db = Depends(get_db),
    current_user = Depends(get_current_user),
):
    return user_service.update_user_role_status(
        db=db,
        user_id=user_id,
        role=req.role,
        status=req.status,
        current_user=current_user,
    )

