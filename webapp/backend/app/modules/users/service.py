from typing import Optional, List, Any
from sqlalchemy.orm import Session
from app.modules.users.models import User
from app.modules.users.repository import user_repository
from app.core.security import hash_password
from app.core.exceptions import BadRequestError, NotFoundError

class UserService:
    def register_user(self, db: Session, full_name: str, email: str, password: str, username: Optional[str] = None) -> User:
        clean_email = email.strip()
        if user_repository.get_by_email(db, clean_email):
            raise BadRequestError("Email already registered")

        derived_username = (username.strip() if username else None) or clean_email.split("@")[0]
        if username and user_repository.get_by_username(db, derived_username):
            raise BadRequestError("Username already exists")

        hashed = hash_password(password)
        # New registrations require Admin approval, so status defaults to 'disabled'
        return user_repository.create(
            db=db,
            full_name=full_name.strip(),
            email=clean_email,
            hashed_password=hashed,
            username=derived_username,
            role="auditor",
            status="disabled",
        )

    def get_user_by_id(self, db: Session, user_id: int) -> Optional[User]:
        return user_repository.get_by_id(db, user_id)

    def get_user_by_email(self, db: Session, email: str) -> Optional[User]:
        return user_repository.get_by_email(db, email.strip())

    def get_user_by_username(self, db: Session, username: str) -> Optional[User]:
        return user_repository.get_by_username(db, username.strip())

    def list_users(self, db: Session) -> List[User]:
        return user_repository.get_all(db)

    def update_user_role_status(self, db: Session, user_id: int, role: Optional[str] = None, status: Optional[str] = None, current_user: Optional[Any] = None) -> User:
        target = user_repository.get_by_id(db, user_id)
        if not target:
            raise NotFoundError("User not found")

        if current_user and str(getattr(current_user, "id", "")) == str(target.id):
            if role is not None and role != "admin":
                raise BadRequestError("Admin cannot demote self")
            if status is not None and status == "disabled":
                raise BadRequestError("Admin cannot disable self")

        if role is not None:
            if role not in ("auditor", "analyst", "admin"):
                raise BadRequestError(f"Invalid role '{role}'. Must be auditor, analyst, or admin")

        if status is not None:
            if status not in ("active", "disabled"):
                raise BadRequestError(f"Invalid status '{status}'. Must be active or disabled")

        user = user_repository.update_role_status(db, user_id=user_id, role=role, status=status)
        return user

    def update_last_login(self, db: Session, user_id: int) -> None:
        user_repository.update_last_login(db, user_id)

    def resolve_user_id(self, db: Session, inspector_id_or_name: Optional[Any]) -> Optional[int]:
        if not inspector_id_or_name:
            return None
        val_str = str(inspector_id_or_name).strip()
        if not val_str:
            return None
        try:
            val_int = int(val_str)
            user = user_repository.get_by_id(db, val_int)
            if user:
                return user.id
        except ValueError:
            pass
        user = user_repository.get_by_username(db, val_str) or user_repository.get_by_email(db, val_str)
        if user:
            return user.id
        return None

user_service = UserService()
