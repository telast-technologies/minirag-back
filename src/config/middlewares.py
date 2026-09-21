from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from src.config.metrics import prometheus_http_middleware
from src.config.settings import settings

limiter = Limiter(key_func=get_remote_address)


MIDDLEWARES = [
    {
        "middleware": CORSMiddleware,
        "options": {
            "allow_origins": ["*"],
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        },
    },
    {
        "middleware": SessionMiddleware,
        "options": {
            "secret_key": settings.SESSION_SECRET_KEY,
        },
    },
    {
        "middleware": BaseHTTPMiddleware,
        "options": {
            "dispatch": prometheus_http_middleware,
        },
    },
    {
        "middleware": SlowAPIMiddleware,
        "options": {},
    },
]


def rate_limit_dependency(request: Request):
    """
    Dependency function for rate limiting.

    Applies rate limiting to API endpoints.

    Args:
        request (Request): The incoming HTTP request.

    Returns:
        Rate limited request.
    """
    return limiter.limit("10/minute")(request)
