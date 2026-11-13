"""
SQLAlchemy Models for UserSession and PasswordReset
Tables: user_sessions, password_resets
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database.base import Base

class UserSession(Base):
    __tablename__ = "user_sessions"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_jti   = Column(String(64), unique=True, index=True, nullable=False)
    ip_address  = Column(String(45), nullable=True)
    user_agent  = Column(String(255), nullable=True)
    expires_at  = Column(DateTime, nullable=False)
    is_revoked  = Column(Boolean, default=False, nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

    user        = relationship("User", back_populates="sessions")

class PasswordReset(Base):
    __tablename__ = "password_resets"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    email       = Column(String(128), index=True, nullable=False)
    otp_code    = Column(String(16), nullable=False)
    expires_at  = Column(DateTime, nullable=False)
    is_used     = Column(Boolean, default=False, nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False)

