from datetime import datetime
import re
from typing import Optional, Any
from pydantic import BaseModel, field_validator

class RegisterRequest(BaseModel):
    full_name: str
    email:     str
    password:  str
    role:      Optional[str] = "auditor"
    username:  Optional[str] = None

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        v = v.strip()
        if len(v) < 2:
            raise ValueError("Full name must be at least 2 characters.")
        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", v):
            raise ValueError("Invalid email format (e.g. auditor@example.com).")
        return v

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("Password must contain at least one letter (a-z, A-Z).")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit (0-9).")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]\\/`~]", v):
            raise ValueError("Password must contain at least one special character (!@#$%^&*...).")
        return v

class UserUpdateRequest(BaseModel):
    role:   Optional[str] = None
    status: Optional[str] = None

class UserOut(BaseModel):
    id:            str
    username:      Optional[str] = None
    full_name:     str
    email:         str
    role:          str
    status:        Optional[str] = "active"
    created_at:    Optional[datetime] = None
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True

    @field_validator("id", mode="before")
    @classmethod
    def stringify_id(cls, v: Any) -> str:
        return str(v)
