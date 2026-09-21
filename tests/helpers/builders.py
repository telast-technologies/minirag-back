from sqlmodel.ext.asyncio.session import AsyncSession

from src.users.models import User
from tests.factories import UserFactory


async def create_user(
    db_session: AsyncSession,
    **user_kwargs,
) -> User:
    user = UserFactory.build(**user_kwargs)
    db_session.add(user)
    await db_session.flush()
    return user
