from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db, get_current_user, require_role
from app.models.user_model import User
from app.schemas.user_schemas import ProfileUpdate, AdminUpgradeRequest, UserResponse

router = APIRouter(prefix="/profile", tags=["User Profile Management"])

@router.patch("/me", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def update_profile_me(
    payload: ProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # apply only provided fields
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(current_user, field, value)
    await db.commit()
    await db.refresh(current_user)
    return current_user

@router.post("/upgrade", response_model=UserResponse, status_code=status.HTTP_200_OK)
async def upgrade_user_to_professional(
    body: AdminUpgradeRequest,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(require_role(["ADMIN", "MANAGER"])),
):
    target = await db.get(User, body.user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    target.update_professional_status(body.professional, by_user_id=actor.id)
    # if you later add a 'professional_reason' column:
    # if body.reason is not None: target.professional_reason = body.reason
    await db.commit()
    await db.refresh(target)
    return target
