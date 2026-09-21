from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import Response
from starlette.requests import Request

from src.config.middlewares import prometheus_http_middleware


@pytest.mark.asyncio
async def test_metrics_endpoint_is_skipped(monkeypatch):
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/metrics",
            "headers": [],
            "query_string": b"",
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 80),
            "scheme": "http",
        }
    )

    response = Response(status_code=200)
    call_next = AsyncMock(return_value=response)

    count_labels = Mock()
    latency_labels = Mock()

    monkeypatch.setattr(
        "src.config.metrics.REQUEST_COUNT.labels",
        count_labels,
    )
    monkeypatch.setattr(
        "src.config.metrics.REQUEST_LATENCY.labels",
        latency_labels,
    )

    result = await prometheus_http_middleware(request, call_next)

    assert result is response
    call_next.assert_awaited_once_with(request)
    count_labels.assert_not_called()
    latency_labels.assert_not_called()
