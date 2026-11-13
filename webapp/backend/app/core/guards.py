"""
Security Guards & Authentication Dependencies
Centralizes get_current_user, require_roles, and verify_internal_secret.
"""
import secrets
from typing import Optional, Any
from fastapi import Depends, HTTPException, Header, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.core.security import decode_jwt_token
from app.database.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

def require_roles(*allowed_roles: str):
    def role_checker(current_user: Any = Depends(get_current_user)):
        if getattr(current_user, "role", None) not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Role '{getattr(current_user, 'role', '')}' is not authorized to access this resource."
            )
        return current_user
    return role_checker

def get_current_user(
    request: Request,
    token_header: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Any:
    from app.modules.users.models import User
    from app.modules.auth.models import UserSession

    token = None
    if token_header:
        token = token_header
    elif request and hasattr(request, "cookies"):
        cookie_val = request.cookies.get("access_token")
        if cookie_val:
            token = cookie_val.replace("Bearer ", "").strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please sign in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 1. Decode JWT Token
    payload = decode_jwt_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    sub = payload.get("sub")
    user_id = payload.get("user_id")
    token_jti = payload.get("jti")

    # 2. Check Database for Revoked Session
    if token_jti:
        sess = db.query(UserSession).filter(UserSession.token_jti == token_jti).first()
        if sess and sess.is_revoked:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has been revoked. Please sign in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # 3. Retrieve User by email/username then ID
    user = None
    if sub:
        user = db.query(User).filter(User.email == sub).first() or db.query(User).filter(User.username == sub).first()
    if not user and user_id:
        user = db.query(User).filter(User.id == user_id).first()

    if user is None or user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or account is deactivated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user

def verify_internal_secret(
    x_pipeline_secret: Optional[str] = Header(None, alias="X-Pipeline-Secret")
):
    expected_secret = settings.PIPELINE_INTERNAL_SECRET
    if not expected_secret:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: PIPELINE_INTERNAL_SECRET is not configured on the server"
        )
    if not x_pipeline_secret or not secrets.compare_digest(x_pipeline_secret, expected_secret):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Invalid or missing pipeline internal secret"
        )
    return True
