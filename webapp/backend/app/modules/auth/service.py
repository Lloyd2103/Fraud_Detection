import os
import uuid
import secrets
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional, Tuple, Dict, Any, List
from sqlalchemy.orm import Session

from app.modules.auth.repository import auth_repository
from app.modules.users.service import user_service
from app.core.security import verify_password, hash_password, create_jwt_token, decode_jwt_token
from app.core.exceptions import UnauthorizedError, BadRequestError

class AuthService:
    def authenticate_user(self, db: Session, email_or_username: str, password: str):
        identifier = email_or_username.strip()
        user = user_service.get_user_by_email(db, identifier) or user_service.get_user_by_username(db, identifier)
        if not user:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    def login(
        self,
        db: Session,
        email_or_username: str,
        password: str,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[str, Any]:
        user = self.authenticate_user(db, email_or_username, password)
        if not user:
            raise UnauthorizedError("Incorrect email or password")

        if getattr(user, "status", "active") != "active":
            raise UnauthorizedError("Your account is pending Administrator approval before sign-in. Please contact an Admin.")

        token_jti = str(uuid.uuid4())
        payload = {
            "sub": user.email,
            "username": user.username or user.email.split("@")[0],
            "user_id": user.id,
            "role": user.role,
            "jti": token_jti,
        }
        token_str, expire_at = create_jwt_token(payload)

        # Record session in auth repository
        auth_repository.create_session(
            db=db,
            user_id=user.id,
            token_jti=token_jti,
            ip_address=client_ip,
            user_agent=user_agent,
            expires_at=expire_at,
        )

        # Update last login via users module service
        user_service.update_last_login(db, user.id)

        return token_str, user

    def logout(self, db: Session, token: Optional[str]) -> None:
        if token:
            payload = decode_jwt_token(token)
            if payload and payload.get("jti"):
                auth_repository.revoke_session(db, payload.get("jti"))

    def get_user_sessions(self, db: Session, user_id: int) -> List[Dict[str, Any]]:
        sessions = auth_repository.get_user_sessions(db, user_id)
        return [{
            "id": str(s.id),
            "token_jti": s.token_jti,
            "ip_address": s.ip_address,
            "user_agent": s.user_agent,
            "expires_at": str(s.expires_at),
            "is_revoked": s.is_revoked,
            "created_at": str(s.created_at)
        } for s in sessions]

    def forgot_password(self, db: Session, email: str) -> Dict[str, Any]:
        clean_email = email.strip().lower()
        user = user_service.get_user_by_email(db, clean_email)
        if not user:
            raise BadRequestError("No account found with this email address.")
        if user.status != "active":
            raise BadRequestError("This account is currently deactivated or locked.")

        otp_code = f"{secrets.randbelow(1000000):06d}"
        self._send_otp_email(clean_email, otp_code, user.full_name)
        auth_repository.create_password_reset(db, clean_email, otp_code, user_id=user.id, expires_in_minutes=10)
        return {
            "status": "success",
            "message": f"Verification code sent to {clean_email}. Valid for 10 minutes."
        }

    def verify_otp(self, db: Session, email: str, otp_code: str) -> Dict[str, Any]:
        pr = auth_repository.get_latest_valid_otp(db, email, otp_code)
        if not pr:
            raise BadRequestError("Invalid or expired OTP verification code.")
        return {
            "status": "success",
            "message": "OTP verified successfully. You may now reset your password.",
            "verified": True
        }

    def reset_password(self, db: Session, email: str, otp_code: str, new_password: str) -> Dict[str, Any]:
        pr = auth_repository.get_latest_valid_otp(db, email, otp_code)
        if not pr:
            raise BadRequestError("Invalid or expired OTP verification code.")

        user = user_service.get_user_by_email(db, email)
        if not user:
            raise BadRequestError("User account not found.")

        # Update password on user entity via direct attribute (or user_service)
        user.hashed_password = hash_password(new_password)
        db.commit()

        # Mark OTP used and revoke existing sessions
        auth_repository.mark_otp_used(db, pr)
        auth_repository.revoke_all_user_sessions(db, user.id)

        return {
            "status": "success",
            "message": "Password reset successfully. Please log in with your new password."
        }

    def _send_otp_email(self, to_email: str, otp_code: str, user_name: str) -> None:
        smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        smtp_user = os.getenv("SMTP_USER", "")
        smtp_password = os.getenv("SMTP_PASSWORD", "")
        from_email = os.getenv("SMTP_FROM_EMAIL", smtp_user)
        smtp_from_name = os.getenv("SMTP_FROM_NAME", "Fraud Detection Platform")

        if not smtp_user or not smtp_password:
            # Fallback for dev mode
            print(f"[AUTH DEV] OTP code for {to_email}: {otp_code}")
            return

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"[{otp_code}] Your Fraud Detection Password Reset Code"
            msg["From"] = f"{smtp_from_name} <{from_email}>"
            msg["To"] = to_email

            text_part = MIMEText(f"Hello {user_name},\n\nYour code is: {otp_code}\nValid for 10 minutes.", "plain")
            msg.attach(text_part)

            context = ssl.create_default_context()
            with smtplib.SMTP(smtp_host, smtp_port, timeout=12) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                server.login(smtp_user, smtp_password)
                server.sendmail(from_email, [to_email], msg.as_string())
        except Exception as exc:
            raise BadRequestError(f"Failed to send email to {to_email}: {str(exc)}")

auth_service = AuthService()
