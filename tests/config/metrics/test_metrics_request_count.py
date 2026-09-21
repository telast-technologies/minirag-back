from unittest.mock import Mock

import pytest
from fastapi import Response
from starlette.requests import Request

from src.config.middlewares import prometheus_http_middleware


@pytest.mark.asyncio
async def test_request_count_increments_with_method_path_and_status(monkeypatch):
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/users",
            "headers": [],
            "query_string": b"",
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
            "scheme": "http",
        }
    )

    response = Response(status_code=201)

    async def call_next(req):
        return response

    count_child = Mock()
    count_labels = Mock(return_value=count_child)

    monkeypatch.setattr(
        "src.config.metrics.REQUEST_COUNT.labels",
        count_labels,
    )
    monkeypatch.setattr(
        "src.config.metrics.REQUEST_LATENCY.labels",
        Mock(return_value=Mock()),
    )

    result = await prometheus_http_middleware(request, call_next)

    assert result is response
    count_labels.assert_called_once_with(
        method="POST",
        path="/api/v1/users",
        status_code="201",
    )
    count_child.inc.assert_called_once()
