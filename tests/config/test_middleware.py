# tests/config/test_middleware.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.sessions import SessionMiddleware

from src.config.middlewares import MIDDLEWARES, limiter, rate_limit_dependency
from src.config.settings import settings


def test_middlewares_structure():
    assert len(MIDDLEWARES) == 4
    assert MIDDLEWARES[0]["middleware"] is CORSMiddleware
    assert MIDDLEWARES[1]["middleware"] is SessionMiddleware
    assert MIDDLEWARES[2]["middleware"] is BaseHTTPMiddleware
    assert MIDDLEWARES[3]["middleware"] is SlowAPIMiddleware


def test_cors_middleware_configuration_is_correct():
    cors_config = MIDDLEWARES[0]
    assert cors_config["options"]["allow_origins"]
    assert cors_config["options"]["allow_credentials"] is True
    assert cors_config["options"]["allow_methods"]
    assert cors_config["options"]["allow_headers"]


def test_session_middleware_configuration_uses_settings_secret():
    session_config = MIDDLEWARES[1]
    assert session_config["options"]["secret_key"] == settings.SESSION_SECRET_KEY


def test_prometheus_middleware_configuration_is_correct():
    middleware_config = MIDDLEWARES[2]
    assert middleware_config["middleware"] is BaseHTTPMiddleware
    assert callable(middleware_config["options"]["dispatch"])


def test_slowapi_middleware_configuration_is_correct():
    slowapi_config = MIDDLEWARES[3]
    assert slowapi_config["middleware"] is SlowAPIMiddleware
    assert isinstance(slowapi_config["options"], dict)


def test_middlewares_can_be_added_to_fastapi_app():
    app = FastAPI()
    for item in MIDDLEWARES:
        app.add_middleware(item["middleware"], **item["options"])

    assert len(app.user_middleware) == len(MIDDLEWARES)


def test_rate_limiter_is_initialized():
    assert limiter is not None
    assert hasattr(limiter, "limit")


def test_rate_limit_dependency_uses_limiter(monkeypatch):
    captured = {}

    def fake_limit(rate):
        captured["rate"] = rate

        def wrapped(request):
            captured["request"] = request
            return "mocked-rate-limit-result"

        return wrapped

    monkeypatch.setattr(limiter, "limit", fake_limit)
    fake_request = object()

    result = rate_limit_dependency(fake_request)

    assert captured["rate"] == "10/minute"
    assert captured["request"] is fake_request
    assert result == "mocked-rate-limit-result"
