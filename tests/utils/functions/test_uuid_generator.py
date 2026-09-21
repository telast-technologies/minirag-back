# tests/utils/test_uuid_generator.py

import re
from unittest.mock import patch

from src.utils.generators import UUIDGenerator


def test_uuid_generator_returns_prefixed_value():
    with patch("src.utils.generators.uuid4") as mock_uuid4:
        mock_uuid4.return_value.hex = "abc123"
        result = UUIDGenerator("user")

    assert result == "user_abc123"


def test_uuid_generator_adds_prefix_and_underscore():
    with patch("src.utils.generators.uuid4") as mock_uuid4:
        mock_uuid4.return_value.hex = "deadbeef"
        result = UUIDGenerator("order")

    assert result.startswith("order_")


def test_uuid_generator_uses_uuid_hex_format():
    with patch("src.utils.generators.uuid4") as mock_uuid4:
        mock_uuid4.return_value.hex = "1234567890abcdef1234567890abcdef"
        result = UUIDGenerator("item")

    assert re.fullmatch(r"item_[0-9a-f]{32}", result)
