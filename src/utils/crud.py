from typing import Any, Generic, TypeVar

from sqlalchemy.sql import Select
from sqlmodel import SQLModel, select

from src.config.db.session import db_session_context
from src.config.loggers import Logger

ModelType = TypeVar("ModelType", bound=SQLModel)

logger = Logger(__name__)


class CRUDBase(Generic[ModelType]):
    model: type[ModelType]

    def __init__(self, session=None):
        if session:
            self.__session = session
        else:
            try:
                self.__session = db_session_context.get()
            except LookupError:
                logger.error("Database session not found in context. Ensure 'get_db' dependency is running.")
                raise RuntimeError("Database session not found in context. Ensure 'get_db' dependency is running.")

    def set_session(self, session):
        self.__session = session

    @property
    def session(self):
        return self.__session

    def select(self, *where: Any) -> Select[Any]:
        statement = select(self.model)
        if where:
            statement = statement.where(*where)
        return statement

    async def get(self, *where: Any) -> ModelType | None:
        statement = self.select(*where)
        result = await self.session.exec(statement)
        return result.first()

    async def list(self, *where: Any, limit: int = 1000) -> list[ModelType]:
        statement = self.select(*where).limit(limit)
        result = await self.session.exec(statement)
        return result.all()

    async def exec(self, statement: Select[Any]) -> Any:
        return await self.session.exec(statement)

    async def create(self, data: dict[str, Any] | ModelType) -> ModelType:
        obj = data if isinstance(data, self.model) else self.model(**data)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def update(
        self,
        db_obj: ModelType,
        data: dict[str, Any] | SQLModel,
    ) -> ModelType:
        update_data = data if isinstance(data, dict) else data.model_dump(exclude_unset=True, exclude_none=True)

        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
            else:
                raise AttributeError(f"{type(db_obj).__name__} has no field '{field}'")

        self.session.add(db_obj)
        await self.session.flush()
        await self.session.refresh(db_obj)
        return db_obj

    async def delete(self, db_obj: ModelType) -> ModelType:
        await self.session.delete(db_obj)
        await self.session.flush()
        return db_obj
