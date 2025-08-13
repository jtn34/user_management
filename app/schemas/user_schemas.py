# app/schemas/user_schemas.py
from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any, Optional, List
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.models.user_model import UserRole
from app.utils.nickname_gen import generate_nickname


# -------------------------
# Helpers
# -------------------------
def _validate_url(url: Optional[str]) -> Optional[str]:
    if url is None:
        return url
    url_regex = r"^https?:\/\/[^\s/$.?#].[^\s]*$"
    if not re.match(url_regex, url):
        raise ValueError("Invalid URL format")
    return url


# -------------------------
# Base / Shared
# -------------------------
class UserBase(BaseModel):
    email: EmailStr = Field(..., example="john.doe@example.com")
    nickname: Optional[str] = Field(
        None, min_length=3, pattern=r"^[\w-]+$", example=generate_nickname()
    )
    first_name: Optional[str] = Field(None, example="John")
    last_name: Optional[str] = Field(None, example="Doe")
    bio: Optional[str] = Field(
        None, example="Experienced software developer specializing in web applications."
    )
    profile_picture_url: Optional[str] = Field(
        None, example="https://example.com/profiles/john.jpg"
    )
    linkedin_profile_url: Optional[str] = Field(
        None, example="https://linkedin.com/in/johndoe"
    )
    github_profile_url: Optional[str] = Field(
        None, example="https://github.com/johndoe"
    )
    role: UserRole

    # v2-style validators
    @field_validator(
        "profile_picture_url", "linkedin_profile_url", "github_profile_url", mode="before"
    )
    @classmethod
    def _urls(cls, v: Optional[str]) -> Optional[str]:
        return _validate_url(v)

    class Config:
        from_attributes = True
        populate_by_name = True


# -------------------------
# Create / Update Inputs
# -------------------------
class UserCreate(UserBase):
    email: EmailStr = Field(..., example="john.doe@example.com")
    password: str = Field(..., example="Secure*1234")


class UserUpdate(BaseModel):
    # Partial update (admin-style, broader than /me)
    email: Optional[EmailStr] = Field(None, example="john.doe@example.com")
    nickname: Optional[str] = Field(
        None, min_length=3, pattern=r"^[\w-]+$", example="john_doe123"
    )
    first_name: Optional[str] = Field(None, example="John")
    last_name: Optional[str] = Field(None, example="Doe")
    bio: Optional[str] = Field(
        None, example="Experienced software developer specializing in web applications."
    )
    profile_picture_url: Optional[str] = Field(
        None, example="https://example.com/profiles/john.jpg"
    )
    linkedin_profile_url: Optional[str] = Field(
        None, example="https://linkedin.com/in/johndoe"
    )
    github_profile_url: Optional[str] = Field(
        None, example="https://github.com/johndoe"
    )
    role: Optional[UserRole] = Field(None, example="AUTHENTICATED")

    @field_validator(
        "profile_picture_url", "linkedin_profile_url", "github_profile_url", mode="before"
    )
    @classmethod
    def _urls(cls, v: Optional[str]) -> Optional[str]:
        return _validate_url(v)

    @model_validator(mode="before")
    @classmethod
    def _at_least_one(cls, values):
        # fail if body is empty OR all provided values are falsy
        if not values or not any(v is not None for v in values.values()):
            raise ValueError("At least one field must be provided for update")
        return values


# PATCH /profile/me (the user’s own editable fields)
class ProfileUpdate(BaseModel):
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=2000)
    location: Optional[str] = Field(None, max_length=120)
    extra_fields: Optional[dict[str, Any]] = None

    @model_validator(mode="before")
    @classmethod
    def _at_least_one(cls, values):
        if not values or not any(v is not None for v in values.values()):
            raise ValueError("At least one field must be provided for update")
        return values


# Managers/Admins upgrade a user’s professional status
class AdminUpgradeRequest(BaseModel):
    user_id: UUID
    professional: bool = Field(..., description="True to upgrade; False to clear.")
    reason: Optional[str] = Field(None, max_length=500)


# -------------------------
# Outputs
# -------------------------
class UserResponse(BaseModel):
    id: UUID = Field(..., example=uuid.uuid4())
    email: EmailStr = Field(..., example="john.doe@example.com")
    nickname: Optional[str] = Field(
        None, min_length=3, pattern=r"^[\w-]+$", example=generate_nickname()
    )
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    bio: Optional[str] = None
    profile_picture_url: Optional[str] = None
    linkedin_profile_url: Optional[str] = None
    github_profile_url: Optional[str] = None
    role: UserRole

    # Expose "professional" to clients; map from DB's is_professional
    professional: bool = Field(
        alias="is_professional", default=False, example=True, description="Professional status"
    )

    class Config:
        from_attributes = True
        populate_by_name = True


class UserDetail(UserResponse):
    location: Optional[str] = None
    extra_fields: Optional[dict[str, Any]] = None
    professional_status_updated_at: Optional[datetime] = None
    professional_upgraded_by_id: Optional[UUID] = None


class LoginRequest(BaseModel):
    email: str = Field(..., example="john.doe@example.com")
    password: str = Field(..., example="Secure*1234")


class ErrorResponse(BaseModel):
    error: str = Field(..., example="Not Found")
    details: Optional[str] = Field(None, example="The requested resource was not found.")


class UserListResponse(BaseModel):
    items: List[UserResponse] = Field(
        ...,
        example=[
            {
                "id": uuid.uuid4(),
                "nickname": generate_nickname(),
                "email": "john.doe@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "bio": "Experienced developer",
                "role": "AUTHENTICATED",
                "profile_picture_url": "https://example.com/profiles/john.jpg",
                "linkedin_profile_url": "https://linkedin.com/in/johndoe",
                "github_profile_url": "https://github.com/johndoe",
                "professional": True,
            }
        ],
    )
    total: int = Field(..., example=100)
    page: int = Field(..., example=1)
    size: int = Field(..., example=10)