from unittest.mock import Mock

import pytest
from fastapi import Response
from starlette.requests import Request

from src.config.middlewares import prometheus_http_middleware


@pytest.mark.asyncio
async def test_request_latency_observes_duration(monkeypatch):
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/health",
            "headers": [],
            "query_string": b"",
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
            "scheme": "http",
        }
    )

    response = Response(status_code=200)

    async def call_next(req):
        return response

    latency_child = Mock()
    latency_labels = Mock(return_value=latency_child)

    monkeypatch.setattr(
        "src.config.metrics.REQUEST_COUNT.labels",
        Mock(return_value=Mock()),
    )
    monkeypatch.setattr(
        "src.config.metrics.REQUEST_LATENCY.labels",
        latency_labels,
    )

    result = await prometheus_http_middleware(request, call_next)

    assert result is response
    latency_labels.assert_called_once_with(
        method="GET",
        path="/health",
    )
    latency_child.observe.assert_called_once()

    observed_duration = latency_child.observe.call_args[0][0]
    assert isinstance(observed_duration, float)
    assert observed_duration >= 0
