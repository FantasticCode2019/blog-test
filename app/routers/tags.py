from typing import Optional
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func

from ..database import get_db_session
from ..models import Tag, Post, post_tag_table
from ..utils import generate_slug, paginate, generate_unique_slug
from ..deps import require_admin

router = APIRouter()


# Public tags listing
@router.get("/tags")
def list_tags(request: Request):
    with get_db_session() as db:
        tags = db.query(Tag).order_by(Tag.name.asc()).all()
        counts = dict(
            db.query(Tag.id, func.count(post_tag_table.c.post_id))
            .outerjoin(post_tag_table, Tag.id == post_tag_table.c.tag_id)
            .group_by(Tag.id)
            .all()
        )
        return request.app.state.templates.TemplateResponse(
            "tags.html",
            {"request": request, "title": "Tags", "tags": tags, "counts": counts},
        )


# Public tag detail
@router.get("/tag/{slug}")
def tag_detail(request: Request, slug: str, page: int = 1, page_size: int = 10):
    with get_db_session() as db:
        tag = db.query(Tag).filter(Tag.slug == slug).first()
        if not tag:
            return request.app.state.templates.TemplateResponse(
                "list.html", {"request": request, "posts": [], "page": 1, "total_pages": 1, "title": "Not Found", "heading": "Tag not found"}, status_code=404
            )
        base_query = (
            db.query(Post)
            .join(post_tag_table, post_tag_table.c.post_id == Post.id)
            .filter(Post.is_published == True, post_tag_table.c.tag_id == tag.id)  # noqa: E712
        )
        total_posts = base_query.count()
        total_pages, page, offset = paginate(total_posts, page, page_size)
        posts = base_query.order_by(Post.created_at.desc()).offset(offset).limit(page_size).all()
        return request.app.state.templates.TemplateResponse(
            "list.html",
            {
                "request": request,
                "posts": posts,
                "page": page,
                "total_pages": total_pages,
                "title": tag.name,
                "heading": f"Tag: {tag.name}",
            },
        )


@router.get("/admin/tags", dependencies=[Depends(require_admin)])
def admin_tags(request: Request):
    with get_db_session() as db:
        tags = db.query(Tag).order_by(Tag.name.asc()).all()
        return request.app.state.templates.TemplateResponse(
            "admin/tags.html",
            {"request": request, "title": "Tags", "tags": tags, "admin": True},
        )


@router.get("/admin/tags/new", dependencies=[Depends(require_admin)])
def new_tag_form(request: Request):
    return request.app.state.templates.TemplateResponse(
        "admin/tag_form.html", {"request": request, "title": "New Tag", "tag": None}
    )


@router.post("/admin/tags/new", dependencies=[Depends(require_admin)])
def create_tag(request: Request, name: str = Form(...)):
    with get_db_session() as db:
        tag = Tag(name=name, slug=generate_unique_slug(db, Tag, name))
        db.add(tag)
        return RedirectResponse("/admin/tags", status_code=302)


@router.get("/admin/tags/{tag_id}", dependencies=[Depends(require_admin)])
def edit_tag_form(request: Request, tag_id: int):
    with get_db_session() as db:
        tag = db.get(Tag, tag_id)
        return request.app.state.templates.TemplateResponse(
            "admin/tag_form.html", {"request": request, "title": "Edit Tag", "tag": tag}
        )


@router.post("/admin/tags/{tag_id}", dependencies=[Depends(require_admin)])
def update_tag(request: Request, tag_id: int, name: str = Form(...)):
    with get_db_session() as db:
        tag = db.get(Tag, tag_id)
        if tag:
            tag.name = name
            tag.slug = generate_unique_slug(db, Tag, name, exclude_id=tag.id)
            db.add(tag)
        return RedirectResponse("/admin/tags", status_code=302)


@router.post("/admin/tags/{tag_id}/delete", dependencies=[Depends(require_admin)])
def delete_tag(request: Request, tag_id: int):
    with get_db_session() as db:
        tag = db.get(Tag, tag_id)
        if tag:
            db.delete(tag)
        return RedirectResponse("/admin/tags", status_code=302)