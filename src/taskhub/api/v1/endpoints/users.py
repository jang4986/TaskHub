from fastapi import APIRouter, Depends, Query, Response

from taskhub.api.deps import UserRepo, require_roles
from taskhub.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from taskhub.core.enums import UserRole
from taskhub.schemas.user import UserResponse

router = APIRouter()


@router.get(
    "/users",
    response_model=list[UserResponse],
    summary="List users (Admin only)",
    dependencies=[Depends(require_roles([UserRole.ADMIN]))],
)
async def list_users(
    response: Response,
    user_repo: UserRepo,
    skip: int = Query(0, ge=0, description="Number of items to skip"),
    limit: int = Query(
        DEFAULT_PAGE_SIZE,
        ge=1,
        le=MAX_PAGE_SIZE,
        description="Max number of items to return",
    ),
) -> list[UserResponse]:
    users, total = await user_repo.get_multi_with_total(skip=skip, limit=limit)
    response.headers["X-Total-Count"] = str(total)
    return [UserResponse.model_validate(u) for u in users]
