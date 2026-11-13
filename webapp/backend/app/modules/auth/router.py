from fastapi import APIRouter, Depends, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from app.database.session import get_db
from app.core.guards import get_current_user
from app.modules.auth.schemas import (
    TokenOut,
    ForgotPasswordRequest,
    VerifyOtpRequest,
    ResetPasswordRequest,
)
from app.config.settings import settings
from app.modules.users.schemas import UserOut
from app.modules.auth.service import auth_service
from app.core.limiter import limiter

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=TokenOut)
@limiter.limit("10/minute")
def login(
    request: Request,
    response: Response,
    form: OAuth2PasswordRequestForm = Depends(),
    db = Depends(get_db)
):
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", "")
    token_str, user = auth_service.login(
        db=db,
        email_or_username=form.username,
        password=form.password,
        client_ip=client_ip,
        user_agent=user_agent,
    )
    response.set_cookie(
        key="access_token",
        value=f"Bearer {token_str}",
        httponly=True,
        max_age=8 * 3600,
        samesite="lax",
        secure=settings.USE_SECURE_COOKIE,
    )
    return {
        "access_token": token_str,
        "token_type": "bearer",
        "user": user,
    }

@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db = Depends(get_db)
):
    token = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "").strip()
    else:
        cookie_val = request.cookies.get("access_token")
        if cookie_val:
            token = cookie_val.replace("Bearer ", "").strip()

    auth_service.logout(db, token)
    response.delete_cookie(key="access_token")
    return {"status": "success", "message": "Logged out and session revoked successfully"}

@router.get("/me", response_model=UserOut)
def me(current_user = Depends(get_current_user)):
    return current_user

@router.get("/roles")
def get_roles():
    return [
        {"id": 1, "name": "auditor", "description": "Fraud Inspection Specialist", "permissions": "read,inspect"},
        {"id": 2, "name": "analyst", "description": "Data & Drift Analyst", "permissions": "read,drift,metrics"},
        {"id": 3, "name": "admin", "description": "Full System Administrator", "permissions": "read,inspect,retrain,admin,manage_users"},
    ]

@router.get("/sessions")
def get_user_sessions(
    current_user = Depends(get_current_user),
    db = Depends(get_db)
):
    return auth_service.get_user_sessions(db, current_user.id)

@router.post("/forgot-password")
@limiter.limit("5/minute")
def forgot_password(request: Request, req: ForgotPasswordRequest, db = Depends(get_db)):
    return auth_service.forgot_password(db, req.email)

@router.post("/verify-otp")
def verify_otp(req: VerifyOtpRequest, db = Depends(get_db)):
    return auth_service.verify_otp(db, req.email, req.otp_code)

@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest, db = Depends(get_db)):
    return auth_service.reset_password(db, req.email, req.otp_code, req.new_password)

