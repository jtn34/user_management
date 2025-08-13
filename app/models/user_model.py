# app/models/user_model.py
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Enum as SQLEnum

from app.database import Base


class UserRole(Enum):
    ANONYMOUS = "ANONYMOUS"
    AUTHENTICATED = "AUTHENTICATED"
    MANAGER = "MANAGER"
    ADMIN = "ADMIN"


class User(Base):
    __tablename__ = "users"
    __mapper_args__ = {"eager_defaults": True}

    # Identity
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nickname: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    first_name: Mapped[str | None] = mapped_column(String(100))
    last_name: Mapped[str | None] = mapped_column(String(100))

    # Profile
    bio: Mapped[str | None] = mapped_column(String(500))
    profile_picture_url: Mapped[str | None] = mapped_column(String(255))
    linkedin_profile_url: Mapped[str | None] = mapped_column(String(255))
    github_profile_url: Mapped[str | None] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(120))
    extra_fields: Mapped[dict | None] = mapped_column(JSONB)

    # Auth / role
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, name="UserRole", create_constraint=True),
        nullable=False,
        default=UserRole.AUTHENTICATED,
    )
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    verification_token: Mapped[str | None] = mapped_column(String(255))

    # Professional status
    is_professional: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    professional_status_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        server_default=None,
        onupdate=func.now(),
        index=True,
    )
    professional_upgraded_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
    )
    professional_upgraded_by: Mapped["User"] = relationship(
        "User", remote_side="User.id", lazy="joined"
    )

    # Account / activity
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<User {self.nickname}, Role: {self.role.name}>"

    # --- Account controls ---
    def lock_account(self) -> None:
        self.is_locked = True

    def unlock_account(self) -> None:
        self.is_locked = False

    def verify_email(self) -> None:
        self.email_verified = True

    def has_role(self, role_name: UserRole) -> bool:
        return self.role == role_name

    # --- Professional status helpers ---
    def mark_professional(self, by_user_id: uuid.UUID | None) -> None:
        """Set professional True and stamp who/when (Python timestamp)."""
        self.is_professional = True
        self.professional_status_updated_at = datetime.now(timezone.utc)
        self.professional_upgraded_by_id = by_user_id

    def clear_professional(self) -> None:
        """Unset professional and stamp when cleared."""
        self.is_professional = False
        self.professional_status_updated_at = datetime.now(timezone.utc)
        self.professional_upgraded_by_id = None

    def update_professional_status(self, status: bool, by_user_id: uuid.UUID | None = None) -> None:
        if status:
            self.mark_professional(by_user_id)
        else:
            self.clear_professional()