from typing import Any

from fastapi import APIRouter

from taskhub.api.v1.endpoints import (
    auth,
    comments,
    labels,
    notifications,
    projects,
    tasks,
    users,
    workspaces,
)
from taskhub.schemas.common import ErrorResponse

DEFAULT_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Unauthorized"},
    403: {"model": ErrorResponse, "description": "Forbidden"},
    404: {"model": ErrorResponse, "description": "Not Found"},
    422: {"description": "Validation Error"},
}

api_router = APIRouter()

api_router.include_router(auth.router, tags=["Auth"])
api_router.include_router(
    users.router,
    tags=["Users"],
    responses=DEFAULT_ERROR_RESPONSES,
)
api_router.include_router(
    workspaces.router,
    prefix="/workspaces",
    tags=["Workspaces"],
    responses=DEFAULT_ERROR_RESPONSES,
)
api_router.include_router(
    projects.router,
    tags=["Projects - Tasks"],
    responses=DEFAULT_ERROR_RESPONSES,
)
api_router.include_router(
    tasks.router,
    tags=["Tasks"],
    responses=DEFAULT_ERROR_RESPONSES,
)
api_router.include_router(
    labels.router,
    tags=["Labels"],
    responses=DEFAULT_ERROR_RESPONSES,
)
api_router.include_router(
    comments.router,
    tags=["Comments"],
    responses=DEFAULT_ERROR_RESPONSES,
)
api_router.include_router(
    notifications.router,
    tags=["Notifications"],
    responses=DEFAULT_ERROR_RESPONSES,
)
