from typing import Any

from fastapi import HTTPException, status
from starlette.concurrency import run_in_threadpool

from taskhub.core.security import get_password_hash, verify_password
from taskhub.models.user import User
from taskhub.repositories.user_repo import UserRepository
from taskhub.schemas.user import ChangePasswordRequest, UserProfileUpdate


class UserService:
    def __init__(self, user_repo: UserRepository) -> None:
        self.user_repo = user_repo

    async def update_profile(self, user: User, data: UserProfileUpdate) -> User:
        update_data: dict[str, Any] = {}
        if data.full_name is not None:
            trimmed = data.full_name.strip()
            if not trimmed:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="full_name cannot be blank",
                )
            update_data["full_name"] = trimmed

        if update_data:
            updated_user = await self.user_repo.update(db_obj=user, obj_in=update_data)
            await self.user_repo.db.commit()
            return updated_user
        return user

    async def change_password(self, user: User, data: ChangePasswordRequest) -> None:
        is_valid = await run_in_threadpool(
            verify_password, data.current_password, user.hashed_password
        )
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect current password",
            )

        is_same = await run_in_threadpool(verify_password, data.new_password, user.hashed_password)
        if is_same:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="New password cannot be the same as current password",
            )

        new_hashed = await run_in_threadpool(get_password_hash, data.new_password)
        await self.user_repo.update(db_obj=user, obj_in={"hashed_password": new_hashed})
        await self.user_repo.db.commit()
