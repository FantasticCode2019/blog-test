from math import ceil
from slugify import slugify
from typing import Iterable, Tuple


def generate_slug(text: str) -> str:
    base = slugify(text)
    return base


def paginate(total_items: int, page: int, page_size: int) -> Tuple[int, int, int]:
    """Return (total_pages, page, offset) with sane bounds."""
    if page_size <= 0:
        page_size = 10
    total_pages = max(1, ceil(total_items / page_size))
    page = max(1, min(page, total_pages))
    offset = (page - 1) * page_size
    return total_pages, page, offset