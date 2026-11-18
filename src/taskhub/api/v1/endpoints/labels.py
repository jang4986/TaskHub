from typing import Annotated

from fastapi import APIRouter, Path, status

from taskhub.api.deps import CurrentActiveUser, LabelServ
from taskhub.schemas.label import LabelCreate, LabelResponse, LabelUpdate

router = APIRouter()


@router.post(
    "/projects/{project_id}/labels",
    response_model=LabelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a label for a project",
    description=(
        "Creates a new label within the specified project. "
        "Requires write permissions on the workspace/project."
    ),
    responses={
        status.HTTP_201_CREATED: {"description": "Label successfully created"},
        status.HTTP_403_FORBIDDEN: {"description": "Insufficient permissions to create labels"},
        status.HTTP_404_NOT_FOUND: {"description": "Project not found"},
        status.HTTP_409_CONFLICT: {
            "description": "Label with this name already exists in the project"
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "description": "Validation error or invalid color format"
        },
    },
)
async def create_label(
    project_id: Annotated[int, Path(ge=1, description="Target Project ID")],
    data: LabelCreate,
    current_user: CurrentActiveUser,
    service: LabelServ,
) -> LabelResponse:
    label = await service.create_label(
        project_id=project_id,
        user_id=current_user.id,
        data=data,
    )
    return LabelResponse.model_validate(label)


@router.get(
    "/projects/{project_id}/labels",
    response_model=list[LabelResponse],
    summary="List labels of a project",
    description="Retrieves all labels defined for the given project.",
    responses={
        status.HTTP_200_OK: {"description": "List of labels retrieved successfully"},
        status.HTTP_403_FORBIDDEN: {"description": "Not a member of this workspace"},
        status.HTTP_404_NOT_FOUND: {"description": "Project not found"},
    },
)
async def list_labels(
    project_id: Annotated[int, Path(ge=1, description="Target Project ID")],
    current_user: CurrentActiveUser,
    service: LabelServ,
) -> list[LabelResponse]:
    labels = await service.list_labels(
        project_id=project_id,
        user_id=current_user.id,
    )
    return [LabelResponse.model_validate(label) for label in labels]


@router.patch(
    "/labels/{label_id}",
    response_model=LabelResponse,
    summary="Update a label",
    description="Updates label details (name, color). Cannot set name or color to null.",
    responses={
        status.HTTP_200_OK: {"description": "Label updated successfully"},
        status.HTTP_403_FORBIDDEN: {"description": "Insufficient permissions to update label"},
        status.HTTP_404_NOT_FOUND: {"description": "Label not found or access denied"},
        status.HTTP_409_CONFLICT: {"description": "Label with new name already exists"},
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "description": "Field cannot be null or invalid format"
        },
    },
)
async def update_label(
    label_id: Annotated[int, Path(ge=1, description="Target Label ID")],
    data: LabelUpdate,
    current_user: CurrentActiveUser,
    service: LabelServ,
) -> LabelResponse:
    label = await service.update_label(
        label_id=label_id,
        user_id=current_user.id,
        data=data,
    )
    return LabelResponse.model_validate(label)


@router.delete(
    "/labels/{label_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a label",
    description="Permanently deletes a label and detaches it from all associated tasks.",
    responses={
        status.HTTP_204_NO_CONTENT: {"description": "Label deleted successfully"},
        status.HTTP_403_FORBIDDEN: {"description": "Insufficient permissions to delete label"},
        status.HTTP_404_NOT_FOUND: {"description": "Label not found or access denied"},
    },
)
async def delete_label(
    label_id: Annotated[int, Path(ge=1, description="Target Label ID")],
    current_user: CurrentActiveUser,
    service: LabelServ,
) -> None:
    await service.delete_label(
        label_id=label_id,
        user_id=current_user.id,
    )


@router.post(
    "/tasks/{task_id}/labels/{label_id}",
    response_model=LabelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Attach a label to a task",
    description="Attaches an existing project label to a task within the same project.",
    responses={
        status.HTTP_201_CREATED: {"description": "Label attached to task successfully"},
        status.HTTP_400_BAD_REQUEST: {"description": "Label belongs to a different project"},
        status.HTTP_403_FORBIDDEN: {
            "description": "Insufficient permissions to modify task labels"
        },
        status.HTTP_404_NOT_FOUND: {"description": "Task or Label not found"},
        status.HTTP_409_CONFLICT: {"description": "Label is already attached to this task"},
    },
)
async def attach_label_to_task(
    task_id: Annotated[int, Path(ge=1, description="Target Task ID")],
    label_id: Annotated[int, Path(ge=1, description="Target Label ID")],
    current_user: CurrentActiveUser,
    service: LabelServ,
) -> LabelResponse:
    label = await service.assign_label_to_task(
        task_id=task_id,
        label_id=label_id,
        user_id=current_user.id,
    )
    return LabelResponse.model_validate(label)


@router.delete(
    "/tasks/{task_id}/labels/{label_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Detach a label from a task",
    description="Detaches a label from a task. Returns 404 if the label was not attached.",
    responses={
        status.HTTP_204_NO_CONTENT: {"description": "Label detached successfully"},
        status.HTTP_400_BAD_REQUEST: {"description": "Label belongs to a different project"},
        status.HTTP_403_FORBIDDEN: {
            "description": "Insufficient permissions to modify task labels"
        },
        status.HTTP_404_NOT_FOUND: {"description": "Task, Label, or attachment not found"},
    },
)
async def detach_label_from_task(
    task_id: Annotated[int, Path(ge=1, description="Target Task ID")],
    label_id: Annotated[int, Path(ge=1, description="Target Label ID")],
    current_user: CurrentActiveUser,
    service: LabelServ,
) -> None:
    await service.remove_label_from_task(
        task_id=task_id,
        label_id=label_id,
        user_id=current_user.id,
    )
