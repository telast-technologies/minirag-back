from enum import Enum


class AssetStatus(str, Enum):
    PENDING = "pending"
    PROCESSED = "processed"
    INDEXED = "indexed"
    FAILED = "failed"


class AssetType(str, Enum):
    TEXT = "text"
    FILE = "file"
    URL = "url"
