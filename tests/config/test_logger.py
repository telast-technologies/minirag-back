# tests/config/test_loggers.py

import logging

import pytest

from src.config.loggers import Logger


class FakePythonLogger:
    def __init__(self):
        self.calls = []

    def info(self, message):
        self.calls.append(("info", message))

    def error(self, message):
        self.calls.append(("error", message))

    def debug(self, message):
        self.calls.append(("debug", message))

    def warning(self, message):
        self.calls.append(("warning", message))

    def critical(self, message):
        self.calls.append(("critical", message))

    def exception(self, message):
        self.calls.append(("exception", message))


def test_logger_initializes_python_logger():
    logger = Logger("my.module")
    assert logger.logger is logging.getLogger("my.module")


@pytest.mark.parametrize(
    "method_name, expected_logging_method",
    [
        ("info", "info"),
        ("error", "error"),
        ("debug", "debug"),
        ("warning", "warning"),
        ("critical", "critical"),
    ],
)
def test_logger_delegates_to_underlying_logger(method_name, expected_logging_method):
    logger = Logger("test.logger")
    fake_logger = FakePythonLogger()
    logger.logger = fake_logger

    getattr(logger, method_name)("hello world")

    assert fake_logger.calls == [(expected_logging_method, "hello world")]


def test_logger_exception_delegates_to_exception():
    logger = Logger("test.logger")
    fake_logger = FakePythonLogger()
    logger.logger = fake_logger

    logger.exception("boom")

    assert fake_logger.calls == [("exception", "boom")]


def test_basic_config_can_be_called_without_error():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    assert True
