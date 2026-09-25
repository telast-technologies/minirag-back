from enum import Enum


class EmbeddingDocumentType(str, Enum):
    DOCUMENT = "document"
    QUERY = "query"
