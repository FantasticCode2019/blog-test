from typing import Optional
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import func

from ..database import get_db_session
from ..models import Category, Post
from ..utils import generate_slug, paginate, generate_unique_slug
from ..deps import require_admin

router = APIRouter()


# Public categories listing
@router.get("/categories")
def list_categories(request: Request):
    with get_db_session() as db:
        categories = db.query(Category).order_by(Category.name.asc()).all()
        counts = dict(
            db.query(Category.id, func.count(Post.id))
            .outerjoin(Post, Post.category_id == Category.id)
            .group_by(Category.id)
            .all()
        )
        return request.app.state.templates.TemplateResponse(
            "categories.html",
            {"request": request, "title": "Categories", "categories": categories, "counts": counts},
        )


# Public category detail
@router.get("/category/{slug}")
def category_detail(request: Request, slug: str, page: int = 1, page_size: int = 10):
    with get_db_session() as db:
        category = db.query(Category).filter(Category.slug == slug).first()
        if not category:
            return request.app.state.templates.TemplateResponse(
                "list.html", {"request": request, "posts": [], "page": 1, "total_pages": 1, "title": "Not Found", "heading": "Category not found"}, status_code=404
            )
        base_query = db.query(Post).filter(Post.is_published == True, Post.category_id == category.id)  # noqa: E712
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
                "title": category.name,
                "heading": f"Category: {category.name}",
            },
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
        category = Category(name=name, slug=generate_unique_slug(db, Category, name))
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
            category.slug = generate_unique_slug(db, Category, name, exclude_id=category.id)
            db.add(category)
        return RedirectResponse("/admin/categories", status_code=302)


@router.post("/admin/categories/{category_id}/delete", dependencies=[Depends(require_admin)])
def delete_category(request: Request, category_id: int):
    with get_db_session() as db:
        category = db.get(Category, category_id)
        if category:
            db.delete(category)
        return RedirectResponse("/admin/categories", status_code=302)