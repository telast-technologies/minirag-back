from datetime import datetime
from uuid import UUID

from fastapi import File, Form, UploadFile
from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl

from src.utils.schemas import E164PhoneNumber


class RegisterUserSchema(BaseModel):
    username: str
    password: str = Field(..., min_length=8, max_length=128)
    email: EmailStr
    phone: E164PhoneNumber = Field(..., example="+1234567890", description="Phone number in E.164 format")


class LoginUserSchema(BaseModel):
    username: str
    password: str = Field(..., min_length=8, max_length=128)


class UserDetailSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    email: EmailStr
    phone: E164PhoneNumber = Field(..., example="+1234567890", description="Phone number in E.164 format")
    avatar: HttpUrl | None = None
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime


class TokenSchema(BaseModel):
    access_token: str
    access_token_expires: datetime


class UserDetailWithAccessTokenSchema(UserDetailSchema, TokenSchema):
    pass


class UpdateProfileSchema(BaseModel):
    avatar: UploadFile | None = None
    email: EmailStr | None = None
    phone: E164PhoneNumber | None = None

    @classmethod
    def as_form(
        cls,
        avatar: UploadFile | None = File(None),
        email: EmailStr | None = Form(None),
        phone: E164PhoneNumber | None = Form(None),
    ):
        return cls(
            avatar=avatar,
            email=email,
            phone=phone,
        )


class RequestUsernameSchema(BaseModel):
    username: str


class ChangePasswordSchema(BaseModel):
    old_password: str = Field(..., min_length=8, max_length=128)
    new_password: str = Field(..., min_length=8, max_length=128)
