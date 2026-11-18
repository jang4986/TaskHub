from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from taskhub.api.deps import CurrentActiveUser, UserRepo, UserServ, require_roles
from taskhub.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from taskhub.core.enums import UserRole
from taskhub.schemas.user import (
    ChangePasswordRequest,
    MessageResponse,
    UserProfileUpdate,
    UserResponse,
)

router = APIRouter()


@router.get(
    "/users/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_my_profile(
    current_user: CurrentActiveUser,
) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.patch(
    "/users/me",
    response_model=UserResponse,
    summary="Update current user profile",
)
async def update_my_profile(
    current_user: CurrentActiveUser,
    profile_in: UserProfileUpdate,
    user_service: UserServ,
) -> UserResponse:
    updated = await user_service.update_profile(user=current_user, data=profile_in)
    return UserResponse.model_validate(updated)


@router.post(
    "/users/change-password",
    response_model=MessageResponse,
    summary="Change user password",
)
async def change_password(
    current_user: CurrentActiveUser,
    password_in: ChangePasswordRequest,
    user_service: UserServ,
) -> MessageResponse:
    await user_service.change_password(user=current_user, data=password_in)
    return MessageResponse(detail="Password updated successfully")


@router.get(
    "/users",
    response_model=list[UserResponse],
    summary="List users (Admin only)",
    dependencies=[Depends(require_roles([UserRole.ADMIN]))],
)
async def list_users(
    response: Response,
    user_repo: UserRepo,
    skip: Annotated[int, Query(ge=0, description="Number of items to skip")] = 0,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=MAX_PAGE_SIZE,
            description="Max number of items to return",
        ),
    ] = DEFAULT_PAGE_SIZE,
) -> list[UserResponse]:
    users, total = await user_repo.get_multi_with_total(skip=skip, limit=limit)
    response.headers["X-Total-Count"] = str(total)
    return [UserResponse.model_validate(u) for u in users]
