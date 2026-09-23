from fastapi import APIRouter, Depends, Request, Response, status

from src.config.db.session import DBSession
from src.config.exceptions import BadRequestException, InternalServerException
from src.config.loggers import Logger
from src.config.permissions import CurrentUserDep
from src.config.settings import settings
from src.users.api.v1.schemas import (
    ChangePasswordSchema,
    LoginUserSchema,
    RegisterUserSchema,
    RequestUsernameSchema,
    TokenSchema,
    UpdateProfileSchema,
    UserDetailSchema,
    UserDetailWithAccessTokenSchema,
)
from src.users.crud import UserCRUD
from src.users.models import User
from src.users.services.tokens import TokenManager
from src.utils.abstracts.validators import UniqueValidator

logger = Logger(name=__name__)
router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.post("/register", response_model=UserDetailSchema, status_code=status.HTTP_201_CREATED)
@settings.LIMITER.limit("50/minute")
async def register_user(
    request: Request,
    body: RegisterUserSchema,
    db: DBSession,
):
    user_crud = UserCRUD()
    validator = UniqueValidator(user_crud)

    await validator.check(
        username=body.username,
        email=body.email,
        phone=body.phone,
    )
    data = body.model_dump()

    hashed_password = request.app.state.hashing.encode(data.pop("password"))
    user_data = {**data, "password": hashed_password}

    try:
        new_user = await user_crud.create(user_data)
        await db.commit()
        await db.refresh(new_user)
        logger.info(f"Registered new user: {new_user.username}")
        return UserDetailSchema.model_validate(new_user)
    except Exception:
        await db.rollback()
        raise InternalServerException("Failed to register user")


@router.post("/login", response_model=UserDetailWithAccessTokenSchema)
@settings.LIMITER.limit("100/minute")
async def login_user(
    request: Request,
    response: Response,
    db: DBSession,
    body: LoginUserSchema,
):
    user_crud = UserCRUD()
    user = await user_crud.get(User.username == body.username)

    if not user or not request.app.state.hashing.decode(body.password, user.password) or not user.is_active:
        raise BadRequestException("Invalid username or password")

    token_manager = TokenManager(user)
    token_manager.set_cookies(response)

    logger.info(f"User logged in: {user.username}")

    user_data = UserDetailSchema.model_validate(user)
    token_data = TokenSchema(**token_manager.get_access_token())

    return UserDetailWithAccessTokenSchema(
        **user_data.model_dump(),
        **token_data.model_dump(),
    )


@router.post("/refresh_token", response_model=TokenSchema)
@settings.LIMITER.limit("100/minute")
async def refresh_token(
    request: Request,
    response: Response,
    user: CurrentUserDep,
):
    token_manager = TokenManager(user)
    token_manager.get_refresh_token_cookie(request)
    token_manager.set_access_token_cookie(response)

    logger.info(f"Refreshed access token for user: {user.username}")
    return TokenSchema(**token_manager.get_access_token())


@router.post("/logout", response_model=dict)
@settings.LIMITER.limit("100/minute")
async def logout(
    request: Request,
    response: Response,
    user: CurrentUserDep,
):
    token_manager = TokenManager(user)
    token_manager.clear_cookies(response)
    return {}


@router.get("/profile", response_model=UserDetailSchema)
@settings.LIMITER.limit("100/minute")
async def get_profile(
    request: Request,
    db: DBSession,
    user: CurrentUserDep,
):
    await db.refresh(user)
    return UserDetailSchema.model_validate(user)


@router.patch("/profile", response_model=UserDetailSchema)
@settings.LIMITER.limit("50/minute")
async def update_profile(
    request: Request,
    db: DBSession,
    user: CurrentUserDep,
    body: UpdateProfileSchema = Depends(UpdateProfileSchema.as_form),
):
    user_crud = UserCRUD()
    # Exclude unset and None values so optional form fields that are omitted
    # (but received as explicit `None` by FastAPI form dependency) do not
    # overwrite existing DB values with NULL.
    update_data = body.model_dump(exclude_unset=True, exclude_none=True)
    updated_user = await user_crud.update(user, update_data)

    await db.commit()

    logger.info(f"Updated profile for user: {updated_user.username}")
    return UserDetailSchema.model_validate(updated_user)


@router.delete("/profile", response_model=UserDetailSchema, status_code=status.HTTP_200_OK)
@settings.LIMITER.limit("50/minute")
async def delete_profile(
    request: Request,
    db: DBSession,
    user: CurrentUserDep,
):
    user_crud = UserCRUD()
    deleted_user = await user_crud.delete(user)
    await db.commit()

    logger.info(f"Deleted user account: {user.username}")
    return UserDetailSchema.model_validate(deleted_user)


@router.patch("/request_username", response_model=UserDetailSchema)
@settings.LIMITER.limit("50/minute")
async def request_username_change(
    request: Request,
    db: DBSession,
    user: CurrentUserDep,
    body: RequestUsernameSchema,
):
    user_crud = UserCRUD()
    validator = UniqueValidator(user_crud)

    if body.username != user.username:
        await validator.check(username=body.username)

    updated_user = await user_crud.update(user, {"username": body.username})
    await db.commit()

    logger.info(f"Username changed: {user.username} -> {body.username}")
    return UserDetailSchema.model_validate(updated_user)


@router.patch("/change_password", response_model=UserDetailSchema)
@settings.LIMITER.limit("50/minute")
async def change_password(
    request: Request,
    db: DBSession,
    user: CurrentUserDep,
    body: ChangePasswordSchema,
):
    if not request.app.state.hashing.decode(body.old_password, user.password):
        raise BadRequestException("Old password is incorrect")

    if body.old_password == body.new_password:
        raise BadRequestException("New password cannot be the same as old password")

    user_crud = UserCRUD()
    new_hashed_password = request.app.state.hashing.encode(body.new_password)
    updated_user = await user_crud.update(user, {"password": new_hashed_password})

    await db.commit()

    logger.info(f"User changed password: {user.username}")
    return UserDetailSchema.model_validate(updated_user)
