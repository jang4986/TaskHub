from typing import Any, Generic, Optional, Type, TypeVar, Union
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from taskhub.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class BaseRepository(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    def __init__(self, model: Type[ModelType], db: AsyncSession) -> None:
        self.model = model
        self.db = db

    async def get(self, id: Any) -> Optional[ModelType]:
        stmt = select(self.model).where(self.model.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_multi(self, skip: int = 0, limit: int = 20) -> list[ModelType]:
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create(self, obj_in: Union[CreateSchemaType, dict[str, Any]]) -> ModelType:
        if isinstance(obj_in, dict):
            create_data = obj_in
        else:
            create_data = obj_in.model_dump()
        db_obj = self.model(**create_data)
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def update(
        self,
        db_obj: ModelType,
        obj_in: Union[UpdateSchemaType, dict[str, Any]],
    ) -> ModelType:
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        self.db.add(db_obj)
        await self.db.flush()
        await self.db.refresh(db_obj)
        return db_obj

    async def remove(self, id: Any) -> Optional[ModelType]:
        obj = await self.get(id)
        if obj is not None:
            await self.db.delete(obj)
            await self.db.flush()
        return obj
