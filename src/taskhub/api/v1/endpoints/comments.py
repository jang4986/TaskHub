from typing import Annotated

from fastapi import APIRouter, Path, Query, Response, status

from taskhub.api.deps import CommentServ, CurrentActiveUser
from taskhub.core.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from taskhub.schemas.comment import CommentCreate, CommentResponse

router = APIRouter()


@router.post(
    "/tasks/{id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a comment to a task",
)
async def create_comment(
    id: Annotated[int, Path(ge=1, description="Task ID")],
    data: CommentCreate,
    current_user: CurrentActiveUser,
    service: CommentServ,
) -> CommentResponse:
    comment = await service.create_comment(
        task_id=id,
        author_id=current_user.id,
        data=data,
    )
    return CommentResponse.model_validate(comment)


@router.get(
    "/tasks/{id}/comments",
    response_model=list[CommentResponse],
    summary="List comments of a task",
)
async def list_comments(
    id: Annotated[int, Path(ge=1, description="Task ID")],
    response: Response,
    current_user: CurrentActiveUser,
    service: CommentServ,
    page: Annotated[int, Query(ge=1, description="Page number")] = 1,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=MAX_PAGE_SIZE,
            description="Max number of items to return",
        ),
    ] = DEFAULT_PAGE_SIZE,
    skip: Annotated[int | None, Query(ge=0, description="Number of items to skip")] = None,
) -> list[CommentResponse]:
    offset = skip if skip is not None else (page - 1) * limit
    comments, total = await service.list_comments(
        task_id=id,
        user_id=current_user.id,
        skip=offset,
        limit=limit,
    )
    response.headers["X-Total-Count"] = str(total)
    return [CommentResponse.model_validate(c) for c in comments]


@router.delete(
    "/comments/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a comment",
)
async def delete_comment(
    id: Annotated[int, Path(ge=1, description="Comment ID")],
    current_user: CurrentActiveUser,
    service: CommentServ,
) -> None:
    await service.delete_comment(
        comment_id=id,
        user_id=current_user.id,
    )
