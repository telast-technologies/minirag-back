from fastapi_pagination import paginate, Params, Page
from typing import TypeVar, List, Iterator

T = TypeVar('T')

class Paginator:
    def __init__(self, items: List[T], page_size: int = 50):
        self.items = items
        self.page_size = page_size
        # Calculate total pages manually to know when to stop the loop
        self.total_pages = (len(items) + page_size - 1) // page_size

    def get_page(self) -> Iterator[Page[T]]:
        """
        Yields `fastapi-pagination` Page objects one by one.
        Each Page contains .items, .total, .page, .size, and .pages metadata.
        """
        for page_num in range(1, self.total_pages + 1):
            # `paginate` handles the list slicing and creates a Pydantic Page model
            yield paginate(self.items, Params(page=page_num, size=self.page_size))