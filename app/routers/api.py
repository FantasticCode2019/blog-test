from typing import Optional, List
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select

from ..database import get_db_session
from ..models import Post
from ..utils import generate_unique_slug
from ..deps import get_api_token

router = APIRouter()


class PostIn(BaseModel):
    title: str
    content: str
    summary: Optional[str] = None
    slug: Optional[str] = None
    is_published: bool = False
    content_format: str = "markdown"
    cover_image_url: Optional[str] = None


class PostOut(BaseModel):
    id: int
    title: str
    slug: str
    summary: Optional[str]
    is_published: bool

    model_config = {
        'from_attributes': True
    }


def _check_token(x_api_key: Optional[str]):
    if not x_api_key or x_api_key != get_api_token():
        raise HTTPException(status_code=401, detail="Unauthorized")


@router.get("/posts", response_model=List[PostOut])
def list_posts(x_api_key: Optional[str] = Header(None)):
    _check_token(x_api_key)
    with get_db_session() as db:
        posts = db.query(Post).order_by(Post.created_at.desc()).all()
        return posts


@router.get("/posts/{slug}", response_model=PostOut)
def get_post(slug: str, x_api_key: Optional[str] = Header(None)):
    _check_token(x_api_key)
    with get_db_session() as db:
        post = db.query(Post).filter(Post.slug == slug).first()
        if not post:
            raise HTTPException(status_code=404, detail="Not found")
        return post


@router.post("/posts", response_model=PostOut)
def create_or_update_post(payload: PostIn, x_api_key: Optional[str] = Header(None)):
    _check_token(x_api_key)
    with get_db_session() as db:
        if payload.slug:
            post = db.query(Post).filter(Post.slug == payload.slug).first()
        else:
            post = None
        if not post:
            post = Post(
                title=payload.title,
                slug=generate_unique_slug(db, Post, payload.title),
                content=payload.content,
                summary=payload.summary,
                is_published=payload.is_published,
                content_format=payload.content_format,
                cover_image_url=payload.cover_image_url,
            )
        else:
            post.title = payload.title
            post.slug = generate_unique_slug(db, Post, payload.title, exclude_id=post.id)
            post.content = payload.content
            post.summary = payload.summary
            post.is_published = payload.is_published
            post.content_format = payload.content_format
            post.cover_image_url = payload.cover_image_url
        db.add(post)
        db.flush()
        return post