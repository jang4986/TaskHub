from typing import Any

from starlette.concurrency import run_in_threadpool

from taskhub.core.exceptions import (
    FieldCannotBeBlankError,
    IncorrectCurrentPasswordError,
    NewPasswordSameAsOldError,
)
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
                raise FieldCannotBeBlankError("full_name")
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
            raise IncorrectCurrentPasswordError()

        is_same = await run_in_threadpool(verify_password, data.new_password, user.hashed_password)
        if is_same:
            raise NewPasswordSameAsOldError()

        # Invalidate all prior tokens (Comment 2: token rotation on password change)
        user.token_version += 1
        new_hashed = await run_in_threadpool(get_password_hash, data.new_password)
        await self.user_repo.update(
            db_obj=user,
            obj_in={"hashed_password": new_hashed, "token_version": user.token_version},
        )
        await self.user_repo.db.commit()
