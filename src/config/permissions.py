from typing import Annotated

import jwt
from fastapi import Depends, Request

from src.config.db.session import DBSession
from src.config.exceptions import ForbiddenException, NotFoundException, UnAuthorizedException
from src.config.settings import settings
from src.users.crud import UserCRUD
from src.users.models import User


class CurrentUser:
    def __init__(self, required: bool = True):
        self.required = required

    async def __call__(
        self,
        request: Request,
        db: DBSession,
    ) -> User | None:
        token = request.cookies.get(settings.JWT_COOKIE_NAME)

        if not token:
            if self.required:
                raise UnAuthorizedException("Not authenticated")
            return None

        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
                options={"require": ["sub"]},
            )
        except jwt.ExpiredSignatureError:
            if not self.required:
                return None
            raise UnAuthorizedException("Token expired")
        except jwt.InvalidTokenError:
            if not self.required:
                return None
            raise UnAuthorizedException("Invalid token")

        user_id = payload["sub"]
        user_crud = UserCRUD(db)
        user = await user_crud.get(User.id == user_id)

        if not user:
            if not self.required:
                return None
            raise NotFoundException("User not found")

        if not user.is_active:
            if not self.required:
                return None
            raise ForbiddenException("User is deactivated")

        return user


current_user = CurrentUser(required=True)
optional_current_user = CurrentUser(required=False)

CurrentUserDep = Annotated[User, Depends(current_user)]
OptionalCurrentUserDep = Annotated[User | None, Depends(optional_current_user)]
