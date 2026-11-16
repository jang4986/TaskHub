from typing import Annotated

from fastapi import APIRouter, Path, status

from taskhub.api.deps import CurrentActiveUser, LabelServ
from taskhub.schemas.label import LabelCreate, LabelResponse, LabelUpdate

router = APIRouter()


@router.post(
    "/projects/{id}/labels",
    response_model=LabelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a label for a project",
)
async def create_label(
    id: Annotated[int, Path(ge=1, description="Project ID")],
    data: LabelCreate,
    current_user: CurrentActiveUser,
    service: LabelServ,
) -> LabelResponse:
    label = await service.create_label(
        project_id=id,
        user_id=current_user.id,
        data=data,
    )
    return LabelResponse.model_validate(label)


@router.get(
    "/projects/{id}/labels",
    response_model=list[LabelResponse],
    summary="List labels of a project",
)
async def list_labels(
    id: Annotated[int, Path(ge=1, description="Project ID")],
    current_user: CurrentActiveUser,
    service: LabelServ,
) -> list[LabelResponse]:
    labels = await service.list_labels(
        project_id=id,
        user_id=current_user.id,
    )
    return [LabelResponse.model_validate(label) for label in labels]


@router.patch(
    "/labels/{id}",
    response_model=LabelResponse,
    summary="Update a label",
)
async def update_label(
    id: Annotated[int, Path(ge=1, description="Label ID")],
    data: LabelUpdate,
    current_user: CurrentActiveUser,
    service: LabelServ,
) -> LabelResponse:
    label = await service.update_label(
        label_id=id,
        user_id=current_user.id,
        data=data,
    )
    return LabelResponse.model_validate(label)


@router.delete(
    "/labels/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a label",
)
async def delete_label(
    id: Annotated[int, Path(ge=1, description="Label ID")],
    current_user: CurrentActiveUser,
    service: LabelServ,
) -> None:
    await service.delete_label(
        label_id=id,
        user_id=current_user.id,
    )


@router.post(
    "/tasks/{id}/labels/{label_id}",
    response_model=LabelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Attach a label to a task",
)
async def attach_label_to_task(
    id: Annotated[int, Path(ge=1, description="Task ID")],
    label_id: Annotated[int, Path(ge=1, description="Label ID")],
    current_user: CurrentActiveUser,
    service: LabelServ,
) -> LabelResponse:
    label = await service.assign_label_to_task(
        task_id=id,
        label_id=label_id,
        user_id=current_user.id,
    )
    return LabelResponse.model_validate(label)


@router.delete(
    "/tasks/{id}/labels/{label_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Detach a label from a task",
)
async def detach_label_from_task(
    id: Annotated[int, Path(ge=1, description="Task ID")],
    label_id: Annotated[int, Path(ge=1, description="Label ID")],
    current_user: CurrentActiveUser,
    service: LabelServ,
) -> None:
    await service.remove_label_from_task(
        task_id=id,
        label_id=label_id,
        user_id=current_user.id,
    )
