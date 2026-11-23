from typing import Annotated

from fastapi import APIRouter, Path, Response, status

from taskhub.api.deps import CommentServ, CurrentActiveUser, Pagination
from taskhub.schemas.comment import CommentCreate, CommentResponse

router = APIRouter()


@router.post(
    "/tasks/{task_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a comment to a task",
    description=(
        "Adds a new comment to a specified task. "
        "Available to workspace members with read/view access to the task."
    ),
    responses={
        status.HTTP_201_CREATED: {"description": "Comment created successfully"},
        status.HTTP_403_FORBIDDEN: {"description": "Not a member of the workspace"},
        status.HTTP_404_NOT_FOUND: {"description": "Task not found"},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": "Comment content cannot be empty"},
    },
)
async def create_comment(
    task_id: Annotated[int, Path(ge=1, description="Target Task ID")],
    data: CommentCreate,
    current_user: CurrentActiveUser,
    service: CommentServ,
) -> CommentResponse:
    comment = await service.create_comment(
        task_id=task_id,
        author_id=current_user.id,
        data=data,
    )
    return CommentResponse.model_validate(comment)


@router.get(
    "/tasks/{task_id}/comments",
    response_model=list[CommentResponse],
    summary="List comments of a task",
    description=(
        "Returns a paginated list of comments for the specified task, "
        "ordered chronologically. Returns total count in X-Total-Count header."
    ),
    responses={
        status.HTTP_200_OK: {"description": "List of comments retrieved successfully"},
        status.HTTP_403_FORBIDDEN: {"description": "Not a member of the workspace"},
        status.HTTP_404_NOT_FOUND: {"description": "Task not found"},
    },
)
async def list_comments(
    task_id: Annotated[int, Path(ge=1, description="Target Task ID")],
    response: Response,
    current_user: CurrentActiveUser,
    service: CommentServ,
    pagination: Pagination,
) -> list[CommentResponse]:
    comments, total = await service.list_task_comments(
        task_id=task_id,
        user_id=current_user.id,
        skip=pagination.offset,
        limit=pagination.limit,
    )
    response.headers["X-Total-Count"] = str(total)
    return [CommentResponse.model_validate(c) for c in comments]


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a comment",
    description=(
        "Deletes a comment. Only the comment author (if still an active member) "
        "or workspace OWNER can delete comments."
    ),
    responses={
        status.HTTP_204_NO_CONTENT: {"description": "Comment deleted successfully"},
        status.HTTP_403_FORBIDDEN: {
            "description": "Insufficient permissions to delete this comment"
        },
        status.HTTP_404_NOT_FOUND: {"description": "Comment not found or access denied"},
    },
)
async def delete_comment(
    comment_id: Annotated[int, Path(ge=1, description="Target Comment ID")],
    current_user: CurrentActiveUser,
    service: CommentServ,
) -> None:
    await service.delete_comment(
        comment_id=comment_id,
        user_id=current_user.id,
    )
