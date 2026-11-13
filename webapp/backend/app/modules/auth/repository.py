from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session
from app.modules.auth.models import UserSession, PasswordReset

class AuthRepository:
    def create_session(
        self,
        db: Session,
        user_id: int,
        token_jti: str,
        ip_address: Optional[str],
        user_agent: Optional[str],
        expires_at: datetime,
    ) -> UserSession:
        sess = UserSession(
            user_id=user_id,
            token_jti=token_jti,
            ip_address=ip_address,
            user_agent=user_agent[:250] if user_agent else None,
            expires_at=expires_at,
            is_revoked=False,
        )
        db.add(sess)
        db.commit()
        db.refresh(sess)
        return sess

    def get_session_by_jti(self, db: Session, token_jti: str) -> Optional[UserSession]:
        return db.query(UserSession).filter(UserSession.token_jti == token_jti).first()

    def revoke_session(self, db: Session, token_jti: str) -> bool:
        sess = self.get_session_by_jti(db, token_jti)
        if sess:
            sess.is_revoked = True
            db.commit()
            return True
        return False

    def revoke_all_user_sessions(self, db: Session, user_id: int) -> None:
        db.query(UserSession).filter(UserSession.user_id == user_id).update({"is_revoked": True})
        db.commit()

    def get_user_sessions(self, db: Session, user_id: int, limit: int = 10) -> List[UserSession]:
        return db.query(UserSession).filter(UserSession.user_id == user_id).order_by(UserSession.created_at.desc()).limit(limit).all()

    def create_password_reset(self, db: Session, email: str, otp_code: str, user_id: int, expires_in_minutes: int = 10) -> PasswordReset:
        exp = datetime.utcnow() + timedelta(minutes=expires_in_minutes)
        pr = PasswordReset(
            user_id=user_id,
            email=email.strip().lower(),
            otp_code=otp_code,
            expires_at=exp,
            is_used=False,
        )
        db.add(pr)
        db.commit()
        db.refresh(pr)
        return pr

    def get_latest_valid_otp(self, db: Session, email: str, otp_code: str) -> Optional[PasswordReset]:
        now = datetime.utcnow()
        return db.query(PasswordReset).filter(
            PasswordReset.email == email.strip().lower(),
            PasswordReset.otp_code == otp_code.strip(),
            PasswordReset.is_used == False,
            PasswordReset.expires_at > now,
        ).order_by(PasswordReset.created_at.desc()).first()

    def mark_otp_used(self, db: Session, pr: PasswordReset) -> None:
        pr.is_used = True
        db.commit()

auth_repository = AuthRepository()

