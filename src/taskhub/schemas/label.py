from pydantic import BaseModel, ConfigDict, Field, field_validator

from taskhub.core.constants import (
    COLOR_HEX_REGEX,
    DEFAULT_LABEL_COLOR,
    LABEL_NAME_MAX_LENGTH,
)


class LabelBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=LABEL_NAME_MAX_LENGTH)
    color: str = Field(
        default=DEFAULT_LABEL_COLOR,
        pattern=COLOR_HEX_REGEX,
        description="Mã màu HEX (ví dụ: #10B981)",
    )

    @field_validator("name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Label name cannot be empty or only whitespace")
        return v


class LabelCreate(LabelBase):
    pass


class LabelUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=LABEL_NAME_MAX_LENGTH)
    color: str | None = Field(
        default=None,
        pattern=COLOR_HEX_REGEX,
        description="Mã màu HEX (ví dụ: #10B981)",
    )

    @field_validator("name")
    @classmethod
    def strip_update_name(cls, v: str | None) -> str | None:
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Label name cannot be empty or only whitespace")
        return v


class LabelResponse(BaseModel):
    id: int
    project_id: int
    name: str
    color: str

    model_config = ConfigDict(from_attributes=True)
