from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from taskhub.api.deps import get_auth_service, get_current_active_user
from taskhub.models.user import User
from taskhub.schemas.token import Token
from taskhub.schemas.user import UserCreate, UserResponse
from taskhub.services.auth_service import AuthService

router = APIRouter()


@router.post(
    "/auth/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(
    user_in: UserCreate,
    auth_service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    user = await auth_service.register(user_in=user_in)
    return UserResponse.model_validate(user)


@router.post(
    "/auth/login",
    response_model=Token,
    summary="Login to obtain JWT access token (supports form or JSON)",
)
async def login(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> Token:
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        body = await request.json()
        email = body.get("email") or body.get("username")
        password = body.get("password")
    else:
        form = await request.form()
        email = form.get("username") or form.get("email")
        password = form.get("password")

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password are required",
        )

    user = await auth_service.authenticate(email=str(email), password=str(password))
    return auth_service.create_user_token(user)


@router.get(
    "/auth/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_me(
    current_user: User = Depends(get_current_active_user),
) -> UserResponse:
    return UserResponse.model_validate(current_user)
