from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from app.modules.users.models import User

class UserRepository:
    def get_by_id(self, db: Session, user_id: int) -> Optional[User]:
        return db.query(User).filter(User.id == user_id).first()

    def get_by_email(self, db: Session, email: str) -> Optional[User]:
        return db.query(User).filter(User.email == email).first()

    def get_by_username(self, db: Session, username: str) -> Optional[User]:
        return db.query(User).filter(User.username == username).first()

    def get_all(self, db: Session) -> List[User]:
        return db.query(User).order_by(User.id.asc()).all()

    def create(self, db: Session, full_name: str, email: str, hashed_password: str, username: str, role: str = "auditor", status: str = "disabled") -> User:
        user = User(
            email=email,
            full_name=full_name,
            username=username,
            role=role,
            hashed_password=hashed_password,
            status=status,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def update_role_status(self, db: Session, user_id: int, role: Optional[str] = None, status: Optional[str] = None) -> Optional[User]:
        user = self.get_by_id(db, user_id)
        if not user:
            return None
        if role is not None:
            user.role = role
        if status is not None:
            user.status = status
        db.commit()
        db.refresh(user)
        return user

    def update_last_login(self, db: Session, user_id: int) -> None:
        user = self.get_by_id(db, user_id)
        if user:
            user.last_login_at = datetime.utcnow()
            db.commit()

user_repository = UserRepository()

