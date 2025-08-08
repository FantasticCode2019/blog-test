from math import ceil
from slugify import slugify
from typing import Iterable, Tuple
from typing import Optional, Type


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


# Unique slug utilities

def _is_slug_taken(db_session, model: Type, slug: str, exclude_id: Optional[int] = None) -> bool:
    query = db_session.query(model).filter(model.slug == slug)
    if exclude_id is not None:
        query = query.filter(model.id != exclude_id)
    return db_session.query(query.exists()).scalar()


def generate_unique_slug(db_session, model: Type, text: str, exclude_id: Optional[int] = None) -> str:
    base = generate_slug(text)
    candidate = base
    suffix = 1
    while _is_slug_taken(db_session, model, candidate, exclude_id=exclude_id):
        candidate = f"{base}-{suffix}"
        suffix += 1
    return candidate