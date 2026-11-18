from pydantic import BaseModel, Field


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str | None = None
    role: str | None = None
    type: str | None = None
    jti: str | None = None


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., description="JWT Refresh Token")
