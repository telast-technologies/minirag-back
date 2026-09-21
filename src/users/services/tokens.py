from datetime import datetime, timedelta, timezone

import jwt

from src.config.exceptions import UnAuthorizedException
from src.config.settings import settings


class TokenManager:
    def __init__(self, user):
        self.user = user
        self.access_token = None
        self.refresh_token = None

    def generate_access_token(self) -> dict:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_TIME_OUT)
        self.access_token = jwt.encode(
            {"sub": str(self.user.id), "exp": expire},
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        return {"access_token": self.access_token, "access_token_expires": expire}

    def generate_refresh_token(self) -> dict:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_TIME_OUT)
        self.refresh_token = jwt.encode(
            {"sub": str(self.user.id), "exp": expire},
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM,
        )
        return {"refresh_token": self.refresh_token, "refresh_token_expires": expire}

    def generate_tokens(self) -> dict:
        access_token = self.generate_access_token()
        refresh_token = self.generate_refresh_token()
        return {**access_token, **refresh_token}

    def get_refresh_token_cookie(self, request) -> dict:
        refresh_token = request.cookies.get(settings.JWT_REFRESH_COOKIE_NAME)
        if not refresh_token:
            raise UnAuthorizedException("Missing refresh token cookie")

        try:
            payload = jwt.decode(
                refresh_token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise UnAuthorizedException("Refresh token expired")
        except jwt.InvalidTokenError:
            raise UnAuthorizedException("Invalid refresh token")

    def get_access_token_cookie(self, request) -> dict:
        access_token = request.cookies.get(settings.JWT_COOKIE_NAME)
        if not access_token:
            raise UnAuthorizedException("Missing access token cookie")

        try:
            payload = jwt.decode(
                access_token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise UnAuthorizedException("Access token expired")
        except jwt.InvalidTokenError:
            raise UnAuthorizedException("Invalid access token")

    def set_access_token_cookie(self, response):
        self.access_token = self.generate_access_token()
        response.set_cookie(
            key=settings.JWT_COOKIE_NAME,
            value=self.access_token["access_token"],
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
            max_age=settings.ACCESS_TOKEN_TIME_OUT * 60,
        )

    def set_refresh_token_cookie(self, response):
        self.refresh_token = self.generate_refresh_token()
        response.set_cookie(
            key=settings.JWT_REFRESH_COOKIE_NAME,
            value=self.refresh_token["refresh_token"],
            httponly=True,
            secure=settings.COOKIE_SECURE,
            samesite=settings.COOKIE_SAMESITE,
            max_age=settings.REFRESH_TOKEN_TIME_OUT * 24 * 60 * 60,
        )

    def set_cookies(self, response):
        if not self.access_token:
            self.set_access_token_cookie(response)
        if not self.refresh_token:
            self.set_refresh_token_cookie(response)

    def clear_cookies(self, response):
        response.delete_cookie(settings.JWT_COOKIE_NAME)
        response.delete_cookie(settings.JWT_REFRESH_COOKIE_NAME)

    def get_access_token(self) -> dict:
        return self.access_token
