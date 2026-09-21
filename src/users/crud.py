from src.users.models import User
from src.utils.crud import CRUDBase


class UserCRUD(CRUDBase[User]):
    model = User

    async def delete(self, db_obj: User) -> User:
        return await super().update(db_obj, {"is_active": False})
