"""
SQLAlchemy Model for User
Table: users
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from app.database.base import Base

class User(Base):
    __tablename__ = "users"

    id              = Column(Integer, primary_key=True, index=True)
    email           = Column(String(128), unique=True, index=True, nullable=False)
    full_name       = Column(String(128), nullable=False)
    username        = Column(String(64), unique=True, index=True, nullable=True)
    role            = Column(String(32), default="auditor", nullable=False)
    hashed_password = Column(String(256), nullable=False)
    status          = Column(String(32), default="active", nullable=False)
    last_login_at   = Column(DateTime, nullable=True)
    
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=True)

    sessions        = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")

