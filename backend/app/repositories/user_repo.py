from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional
from app.models.user import User, UserRole

class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    # 1. البحث عن مستخدم بواسطة الإيميل
    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()

    # 2. البحث عن مستخدم بواسطة الـ ID
    def get_by_id(self, user_id: UUID) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()

    # 3. إنشاء مستخدم جديد
    def create_user(self, email: str, password_hash: str, role: UserRole = UserRole.JOB_SEEKER) -> User:
        user = User(
            email=email,
            password_hash=password_hash,
            role=role.value if isinstance(role, UserRole) else role
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
    def update_password(self, user_id: UUID, new_password_hash: str) -> None:
        user = self.get_by_id(user_id)
        if user:
            user.password_hash = new_password_hash
            self.db.commit()