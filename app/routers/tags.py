from typing import Optional
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func

from ..database import get_db_session
from ..models import Tag
from ..utils import generate_slug
from ..deps import require_admin

router = APIRouter()


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
        tag = Tag(name=name, slug=generate_slug(name))
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
            tag.slug = generate_slug(name)
            db.add(tag)
        return RedirectResponse("/admin/tags", status_code=302)


@router.post("/admin/tags/{tag_id}/delete", dependencies=[Depends(require_admin)])
def delete_tag(request: Request, tag_id: int):
    with get_db_session() as db:
        tag = db.get(Tag, tag_id)
        if tag:
            db.delete(tag)
        return RedirectResponse("/admin/tags", status_code=302)