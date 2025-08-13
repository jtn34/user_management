# app/models/user_model.py
from builtins import bool, int, str
from datetime import datetime, timezone
from enum import Enum
import uuid

from sqlalchemy import (
    Column, String, Integer, DateTime, Boolean, func, Enum as SQLAlchemyEnum, ForeignKey  # NEW: ForeignKey
)
from sqlalchemy.dialects.postgresql import UUID, ENUM
# NEW: JSONB import
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class UserRole(Enum):
    """Enumeration of user roles within the application, stored as ENUM in the database."""
    ANONYMOUS = "ANONYMOUS"
    AUTHENTICATED = "AUTHENTICATED"
    MANAGER = "MANAGER"
    ADMIN = "ADMIN"


class User(Base):
    """
    Represents a user within the application, corresponding to the 'users' table in the database.
    """
    __tablename__ = "users"
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nickname: Mapped[str] = Column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = Column(String(255), unique=True, nullable=False, index=True)
    first_name: Mapped[str] = Column(String(100), nullable=True)
    last_name: Mapped[str] = Column(String(100), nullable=True)

    # Profile fields
    bio: Mapped[str] = Column(String(500), nullable=True)
    profile_picture_url: Mapped[str] = Column(String(255), nullable=True)
    linkedin_profile_url: Mapped[str] = Column(String(255), nullable=True)
    github_profile_url: Mapped[str] = Column(String(255), nullable=True)
    location: Mapped[str] = Column(String(120), nullable=True)  # NEW

    # Role & auth
    role: Mapped[UserRole] = Column(SQLAlchemyEnum(UserRole, name='UserRole', create_constraint=True), nullable=False)
    email_verified: Mapped[bool] = Column(Boolean, default=False, nullable=False)
    hashed_password: Mapped[str] = Column(String(255), nullable=False)
    verification_token = Column(String, nullable=True)

    # Professional status
    is_professional: Mapped[bool] = Column(Boolean, default=False, nullable=False)
    professional_status_updated_at: Mapped[datetime] = Column(DateTime(timezone=True), nullable=True)
    professional_upgraded_by_id: Mapped[uuid.UUID | None] = mapped_column(  # NEW
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    extra_fields: Mapped[dict | None] = Column(JSONB, nullable=True)  # NEW

    # Account / activity
    last_login_at: Mapped[datetime] = Column(DateTime(timezone=True), nullable=True)
    failed_login_attempts: Mapped[int] = Column(Integer, default=0)
    is_locked: Mapped[bool] = Column(Boolean, default=False)
    created_at: Mapped[datetime] = Column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<User {self.nickname}, Role: {self.role.name}>"

    # --- Account controls ---
    def lock_account(self):
        self.is_locked = True

    def unlock_account(self):
        self.is_locked = False

    def verify_email(self):
        self.email_verified = True

    def has_role(self, role_name: UserRole) -> bool:
        return self.role == role_name

    # --- Professional status helpers ---
    def mark_professional(self, by_user_id: uuid.UUID | None):
        """Set professional true, stamp time/by."""
        self.is_professional = True
        # Use server-side now() or Python-side; keeping your style consistent:
        self.professional_status_updated_at = func.now()
        self.professional_upgraded_by_id = by_user_id

    def clear_professional(self):
        """Unset professional and clear metadata."""
        self.is_professional = False
        self.professional_status_updated_at = func.now()
        self.professional_upgraded_by_id = None

    def update_professional_status(self, status: bool, by_user_id: uuid.UUID | None = None):
        """Back-compat method that delegates to helpers."""
        if status:
            self.mark_professional(by_user_id)
        else:
            self.clear_professional()