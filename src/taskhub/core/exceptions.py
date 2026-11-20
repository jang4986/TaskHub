"""Domain-specific HTTP exceptions for TaskHub."""

from fastapi import HTTPException, status


class TaskNotFoundError(HTTPException):
    def __init__(self, task_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task with id {task_id} not found",
        )


class ProjectNotFoundError(HTTPException):
    def __init__(self, project_id: int | None = None):
        detail = (
            f"Project not found (id {project_id})"
            if project_id is not None
            else "Project not found"
        )
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )


class WorkspaceNotFoundError(HTTPException):
    def __init__(self, workspace_id: int | None = None):
        detail = (
            f"Workspace with id {workspace_id} not found"
            if workspace_id is not None
            else "Workspace not found"
        )
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )


class WorkspaceAccessDeniedError(HTTPException):
    def __init__(self, detail: str = "Access forbidden: Not a member of this workspace"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class WorkspaceMemberNotFoundError(HTTPException):
    def __init__(self, user_id: int | None = None):
        detail = (
            f"Member with id {user_id} not found in this workspace"
            if user_id is not None
            else "Member not found in this workspace"
        )
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )


class UserAlreadyWorkspaceMemberError(HTTPException):
    def __init__(self, detail: str = "User is already a member of this workspace"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )


class CannotRemoveOwnerError(HTTPException):
    def __init__(self, detail: str = "Cannot remove the workspace owner"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )


class WorkspaceSlugConflictError(HTTPException):
    def __init__(self, detail: str = "Workspace with this slug already exists"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )


class UserNotFoundError(HTTPException):
    def __init__(self, user_id: int | None = None, detail: str | None = None):
        if detail is None:
            detail = (
                f"User with id {user_id} not found" if user_id is not None else "User not found"
            )
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )


class AssigneeNotFoundError(HTTPException):
    def __init__(self, assignee_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Assignee with id {assignee_id} not found",
        )


class EmailAlreadyRegisteredError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )


class InvalidCredentialsError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )


class InactiveUserError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )


class InsufficientPrivilegesError(HTTPException):
    def __init__(self, detail: str = "The user doesn't have enough privileges"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class ProjectAccessDeniedError(HTTPException):
    def __init__(self, detail: str = "You do not have permission to access this project"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class CredentialsValidationError(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


class InvalidRefreshTokenError(HTTPException):
    def __init__(self, detail: str = "Invalid or expired refresh token"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class InvalidRefreshTokenBadRequestError(HTTPException):
    def __init__(self, detail: str = "Invalid refresh token"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )


class IncorrectCurrentPasswordError(HTTPException):
    def __init__(self, detail: str = "Incorrect current password"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )


class NewPasswordSameAsOldError(HTTPException):
    def __init__(self, detail: str = "New password cannot be the same as current password"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )


class FieldCannotBeBlankError(HTTPException):
    def __init__(self, field_name: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"{field_name} cannot be blank",
        )


class FieldCannotBeNullError(HTTPException):
    def __init__(self, field_name: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Field '{field_name}' cannot be null",
        )


class LabelNotFoundError(HTTPException):
    def __init__(self, label_id: int | None = None):
        detail = (
            f"Label with id {label_id} not found" if label_id is not None else "Label not found"
        )
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )


class LabelAlreadyExistsError(HTTPException):
    def __init__(self, name: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Label with name '{name}' already exists in this project",
        )


class LabelAlreadyAttachedError(HTTPException):
    def __init__(self, detail: str = "Label already attached to this task"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )


class LabelNotAttachedError(HTTPException):
    def __init__(self, detail: str = "Label is not attached to this task"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )


class LabelProjectMismatchError(HTTPException):
    def __init__(
        self,
        detail: str = (
            "Label does not belong to the same project (does not belong to the task's project)"
        ),
    ):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )


class CommentNotFoundError(HTTPException):
    def __init__(self, comment_id: int | None = None):
        detail = (
            f"Comment with id {comment_id} not found"
            if comment_id is not None
            else "Comment not found"
        )
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )


class CommentAccessDeniedError(HTTPException):
    def __init__(self, detail: str = "You do not have permission to delete this comment"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class AssigneeMustBeWorkspaceMemberError(HTTPException):
    def __init__(
        self, detail: str = "Assignee must be a member of the project's workspace"
    ):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )


class AssigneeRoleNotAllowedError(HTTPException):
    def __init__(self, detail: str = "Assignee must have write permissions and cannot be a VIEWER"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )


class ProjectArchivedError(HTTPException):
    def __init__(self, detail: str = "Cannot modify tasks in an archived project"):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
        )
