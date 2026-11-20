from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taskhub.models.revoked_token import RevokedToken


class RevokedTokenRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def is_revoked(self, jti: str) -> bool:
        stmt = select(RevokedToken).where(RevokedToken.jti == jti)
        result = await self.db.execute(stmt)
        token = result.scalar_one_or_none()
        return token is not None

    async def revoke(
        self,
        jti: str,
        token_type: str = "refresh",
        expires_at: datetime | None = None,
    ) -> RevokedToken:
        if expires_at is None:
            expires_at = datetime.now(UTC)
        revoked = RevokedToken(
            jti=jti,
            token_type=token_type,
            expires_at=expires_at,
        )
        self.db.add(revoked)
        await self.db.flush()
        return revoked
