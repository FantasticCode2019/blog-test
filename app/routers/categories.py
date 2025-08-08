from typing import Optional
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func

from ..database import get_db_session
from ..models import Category, Post
from ..utils import generate_slug
from ..deps import require_admin

router = APIRouter()


@router.get("/categories")
def list_categories(request: Request):
    with get_db_session() as db:
        categories = db.query(Category).order_by(Category.name.asc()).all()
        return request.app.state.templates.TemplateResponse(
            "admin/categories.html",
            {"request": request, "title": "Categories", "categories": categories},
        )


@router.get("/admin/categories", dependencies=[Depends(require_admin)])
def admin_categories(request: Request):
    with get_db_session() as db:
        categories = db.query(Category).order_by(Category.name.asc()).all()
        return request.app.state.templates.TemplateResponse(
            "admin/categories.html",
            {"request": request, "title": "Categories", "categories": categories, "admin": True},
        )


@router.get("/admin/categories/new", dependencies=[Depends(require_admin)])
def new_category_form(request: Request):
    return request.app.state.templates.TemplateResponse(
        "admin/category_form.html", {"request": request, "title": "New Category", "category": None}
    )


@router.post("/admin/categories/new", dependencies=[Depends(require_admin)])
def create_category(request: Request, name: str = Form(...)):
    with get_db_session() as db:
        category = Category(name=name, slug=generate_slug(name))
        db.add(category)
        return RedirectResponse("/admin/categories", status_code=302)


@router.get("/admin/categories/{category_id}", dependencies=[Depends(require_admin)])
def edit_category_form(request: Request, category_id: int):
    with get_db_session() as db:
        category = db.get(Category, category_id)
        return request.app.state.templates.TemplateResponse(
            "admin/category_form.html", {"request": request, "title": "Edit Category", "category": category}
        )


@router.post("/admin/categories/{category_id}", dependencies=[Depends(require_admin)])
def update_category(request: Request, category_id: int, name: str = Form(...)):
    with get_db_session() as db:
        category = db.get(Category, category_id)
        if category:
            category.name = name
            category.slug = generate_slug(name)
            db.add(category)
        return RedirectResponse("/admin/categories", status_code=302)


@router.post("/admin/categories/{category_id}/delete", dependencies=[Depends(require_admin)])
def delete_category(request: Request, category_id: int):
    with get_db_session() as db:
        category = db.get(Category, category_id)
        if category:
            db.delete(category)
        return RedirectResponse("/admin/categories", status_code=302)