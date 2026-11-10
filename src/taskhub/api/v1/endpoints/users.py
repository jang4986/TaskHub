from fastapi import APIRouter, Depends, Query

from taskhub.api.deps import get_user_repo, require_roles
from taskhub.enums.common import UserRole
from taskhub.models.user import User
from taskhub.repositories.user_repo import UserRepository
from taskhub.schemas.user import UserResponse

router = APIRouter()


@router.get(
    "/users",
    response_model=list[UserResponse],
    summary="List users (Admin only)",
    dependencies=[Depends(require_roles([UserRole.ADMIN]))],
)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    user_repo: UserRepository = Depends(get_user_repo),
) -> list[UserResponse]:
    users = await user_repo.get_multi(skip=skip, limit=limit)
    return [UserResponse.model_validate(u) for u in users]
