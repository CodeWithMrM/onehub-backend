from fastapi import APIRouter, Depends
from prisma.models import User

from app.core.dependencies import require_authenticated_user
from app.db.prisma import db
from app.schemas.auth import MeResponse, UpdateMeRequest

router = APIRouter(tags=["Customer"])


@router.get("/me", response_model=MeResponse, summary="Get the authenticated user's profile")
async def get_me(user: User = Depends(require_authenticated_user)):
    return user


@router.patch("/me", response_model=MeResponse, summary="Update basic profile fields")
async def update_me(
    payload: UpdateMeRequest, user: User = Depends(require_authenticated_user)
):
    data = {k: v for k, v in payload.model_dump().items() if v is not None}
    if not data:
        return user
    return await db.user.update(where={"id": user.id}, data=data)
