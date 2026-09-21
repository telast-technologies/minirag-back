import pytest
from fastapi import HTTPException, status

from src.config import exceptions
from src.config.exceptions import (
    APIException,
    BadRequestException,
    ForbiddenException,
    InternalServerException,
    NotAcceptableException,
    NotFoundException,
    UnAuthorizedException,
)


class FakeLogger:
    def __init__(self):
        self.calls = []

    def exception(self, message):
        self.calls.append(message)


def test_api_exception_is_http_exception(monkeypatch):
    fake_logger = FakeLogger()
    monkeypatch.setattr(exceptions, "logger", fake_logger)

    exc = APIException(status.HTTP_400_BAD_REQUEST, "invalid payload")

    assert isinstance(exc, APIException)
    assert isinstance(exc, HTTPException)
    assert exc.status_code == status.HTTP_400_BAD_REQUEST
    assert exc.detail == "invalid payload"
    assert fake_logger.calls == ["Bad request: invalid payload"]


def test_api_exception_logs_default_key_when_status_code_not_mapped(monkeypatch):
    fake_logger = FakeLogger()
    monkeypatch.setattr(exceptions, "logger", fake_logger)

    exc = APIException(499, "custom error")

    assert exc.status_code == 499
    assert exc.detail == "custom error"
    assert fake_logger.calls == ["default: custom error"]


@pytest.mark.parametrize(
    "exception_class, expected_status_code, expected_detail, expected_log_message",
    [
        (
            NotFoundException,
            status.HTTP_404_NOT_FOUND,
            "Resource not found",
            "Resource not found: Resource not found",
        ),
        (
            UnAuthorizedException,
            status.HTTP_401_UNAUTHORIZED,
            "Unauthorized access",
            "Unauthorized access: Unauthorized access",
        ),
        (
            BadRequestException,
            status.HTTP_400_BAD_REQUEST,
            "Bad request",
            "Bad request: Bad request",
        ),
        (
            ForbiddenException,
            status.HTTP_403_FORBIDDEN,
            "Forbidden action",
            "Forbidden action: Forbidden action",
        ),
        (
            InternalServerException,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Internal server error",
            "Internal server error: Internal server error",
        ),
        (
            NotAcceptableException,
            status.HTTP_406_NOT_ACCEPTABLE,
            "Not acceptable",
            "Not acceptable: Not acceptable",
        ),
    ],
)
def test_exception_subclasses_use_default_values(
    monkeypatch,
    exception_class,
    expected_status_code,
    expected_detail,
    expected_log_message,
):
    fake_logger = FakeLogger()
    monkeypatch.setattr(exceptions, "logger", fake_logger)

    exc = exception_class()

    assert isinstance(exc, APIException)
    assert isinstance(exc, HTTPException)
    assert exc.status_code == expected_status_code
    assert exc.detail == expected_detail
    assert fake_logger.calls == [expected_log_message]


@pytest.mark.parametrize(
    "exception_class, custom_detail, expected_status_code, expected_log_message",
    [
        (
            NotFoundException,
            "creator not found",
            status.HTTP_404_NOT_FOUND,
            "Resource not found: creator not found",
        ),
        (
            UnAuthorizedException,
            "token expired",
            status.HTTP_401_UNAUTHORIZED,
            "Unauthorized access: token expired",
        ),
        (
            BadRequestException,
            "invalid request body",
            status.HTTP_400_BAD_REQUEST,
            "Bad request: invalid request body",
        ),
        (
            ForbiddenException,
            "you cannot access this resource",
            status.HTTP_403_FORBIDDEN,
            "Forbidden action: you cannot access this resource",
        ),
        (
            InternalServerException,
            "database is down",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Internal server error: database is down",
        ),
        (
            NotAcceptableException,
            "unsupported format",
            status.HTTP_406_NOT_ACCEPTABLE,
            "Not acceptable: unsupported format",
        ),
    ],
)
def test_exception_subclasses_accept_custom_detail(
    monkeypatch,
    exception_class,
    custom_detail,
    expected_status_code,
    expected_log_message,
):
    fake_logger = FakeLogger()
    monkeypatch.setattr(exceptions, "logger", fake_logger)

    exc = exception_class(custom_detail)

    assert exc.status_code == expected_status_code
    assert exc.detail == custom_detail
    assert fake_logger.calls == [expected_log_message]
