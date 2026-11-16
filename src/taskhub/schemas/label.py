from pydantic import BaseModel, ConfigDict, Field


class LabelBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    color: str = Field(
        default="#3B82F6",
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="Mã màu HEX (ví dụ: #3B82F6)",
    )


class LabelCreate(LabelBase):
    pass


class LabelUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    color: str | None = Field(
        None,
        pattern=r"^#[0-9A-Fa-f]{6}$",
        description="Mã màu HEX (ví dụ: #3B82F6)",
    )


class LabelResponse(LabelBase):
    id: int
    project_id: int

    model_config = ConfigDict(from_attributes=True)
