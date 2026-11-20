from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from taskhub.api.deps import AuthServ, CurrentActiveUser
from taskhub.schemas.token import RefreshTokenRequest, Token
from taskhub.schemas.user import UserCreate, UserResponse

router = APIRouter()


@router.post(
    "/auth/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    user_in: UserCreate,
    auth_service: AuthServ,
) -> UserResponse:
    user = await auth_service.register(user_in=user_in)
    return UserResponse.model_validate(user)


@router.post(
    "/auth/login",
    response_model=Token,
    summary="Login to obtain JWT access token using OAuth2 standard form",
)
async def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    auth_service: AuthServ,
) -> Token:
    user = await auth_service.authenticate(
        email=form_data.username,
        password=form_data.password,
    )
    return auth_service.create_user_token(user)


@router.get(
    "/auth/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_me(
    current_user: CurrentActiveUser,
) -> UserResponse:
    return UserResponse.model_validate(current_user)


@router.post(
    "/auth/refresh",
    response_model=Token,
    summary="Refresh access token and rotate refresh token",
)
async def refresh_token(
    refresh_in: RefreshTokenRequest,
    auth_service: AuthServ,
) -> Token:
    return await auth_service.refresh_token(refresh_in.refresh_token)


@router.post(
    "/auth/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Logout user and revoke refresh token",
)
async def logout(
    current_user: CurrentActiveUser,
    refresh_in: RefreshTokenRequest,
    auth_service: AuthServ,
) -> None:
    await auth_service.logout(
        current_user=current_user,
        refresh_token_str=refresh_in.refresh_token,
    )
