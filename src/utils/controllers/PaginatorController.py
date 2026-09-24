from collections.abc import Iterator
from typing import TypeVar

from fastapi_pagination import Page, Params, paginate

T = TypeVar("T")


class Paginator:
    def __init__(self, items: list[T], page_size: int = 50):
        self.items = items
        self.page_size = page_size

    def get_page(self) -> Iterator[Page[T]]:
        for page_idx, _ in enumerate(range(0, len(self.items), self.page_size), start=1):
            yield paginate(self.items, Params(page=page_idx, size=self.page_size))
