import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.engine import URL

BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
BUILD_ENV: str = os.getenv("BUILD_ENV", "local")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=f"{BASE_DIR}/docker/.env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    # config variables
    ENV: str
    APP_NAME: str = f"minirag Backend API ({BUILD_ENV.capitalize()})"
    # Database configuration
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str
    POSTGRES_PORT: int
    # postgres-exporter
    DATA_SOURCE_URI: str
    DATA_SOURCE_USER: str
    DATA_SOURCE_PASS: str
    # cache and queue configuration
    REDIS_URL: str
    # security configuration
    SESSION_SECRET_KEY: str | None = None
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str
    ACCESS_TOKEN_TIME_OUT: int
    REFRESH_TOKEN_TIME_OUT: int
    # CORS configuration
    JWT_COOKIE_NAME: str = "access_token"
    JWT_REFRESH_COOKIE_NAME: str = "refresh_token"
    COOKIE_SECURE: bool = True
    COOKIE_SAMESITE: str = "lax"
    COOKIE_DOMAIN: str | None = None
    LIMITER: Limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])
    # Cloudflare R2 configuration
    AWS_ACCESS_KEY_ID: str = Field(alias="R2_ACCESS_KEY")
    AWS_SECRET_ACCESS_KEY: str = Field(alias="R2_SECRET_KEY")
    AWS_S3_BUCKET_NAME: str = Field(alias="R2_BUCKET_NAME")
    AWS_S3_ENDPOINT_URL: str = Field(alias="R2_ENDPOINT_URL")


    @property
    def DATABASE_URL_ASYNC(self) -> str:
        return URL.create(
            drivername="postgresql+asyncpg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            database=self.POSTGRES_DB,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
        ).render_as_string(hide_password=False)

    @property
    def DATABASE_URL_SYNC(self) -> str:
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            database=self.POSTGRES_DB,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
        ).render_as_string(hide_password=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
