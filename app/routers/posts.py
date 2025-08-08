from typing import Optional, List
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import get_db_session
from ..models import Post, Category, Tag
from ..utils import generate_slug, paginate
from ..deps import require_admin

router = APIRouter()


@router.get("/")
def home(request: Request, page: int = 1, page_size: int = 10):
    with get_db_session() as db:
        total_posts = db.query(func.count(Post.id)).filter(Post.is_published == True).scalar()  # noqa: E712
        total_pages, page, offset = paginate(total_posts, page, page_size)
        posts = (
            db.query(Post)
            .filter(Post.is_published == True)  # noqa: E712
            .order_by(Post.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .all()
        )
        return request.app.state.templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "posts": posts,
                "page": page,
                "total_pages": total_pages,
                "title": "Home",
            },
        )


@router.get("/post/{slug}")
def post_detail(request: Request, slug: str):
    with get_db_session() as db:
        post = db.query(Post).filter(Post.slug == slug, Post.is_published == True).first()  # noqa: E712
        if not post:
            return request.app.state.templates.TemplateResponse(
                "post_detail.html", {"request": request, "error": "Post not found", "title": "Not Found"}, status_code=404
            )
        return request.app.state.templates.TemplateResponse(
            "post_detail.html", {"request": request, "post": post, "title": post.title}
        )


# Admin area
@router.get("/admin", dependencies=[Depends(require_admin)])
def admin_dashboard(request: Request):
    return request.app.state.templates.TemplateResponse(
        "admin/dashboard.html", {"request": request, "title": "Admin"}
    )


@router.get("/admin/posts", dependencies=[Depends(require_admin)])
def admin_posts(request: Request):
    with get_db_session() as db:
        posts = db.query(Post).order_by(Post.created_at.desc()).all()
        return request.app.state.templates.TemplateResponse(
            "admin/posts.html", {"request": request, "posts": posts, "title": "Posts"}
        )


@router.get("/admin/posts/new", dependencies=[Depends(require_admin)])
def new_post_form(request: Request):
    with get_db_session() as db:
        categories = db.query(Category).order_by(Category.name.asc()).all()
        tags = db.query(Tag).order_by(Tag.name.asc()).all()
        return request.app.state.templates.TemplateResponse(
            "admin/post_form.html",
            {"request": request, "title": "New Post", "categories": categories, "tags": tags, "post": None},
        )


@router.post("/admin/posts/new", dependencies=[Depends(require_admin)])
def create_post(
    request: Request,
    title: str = Form(...),
    summary: Optional[str] = Form(None),
    content: str = Form(...),
    is_published: Optional[bool] = Form(False),
    category_id: Optional[int] = Form(None),
    tag_ids: Optional[List[int]] = Form(None),
):
    with get_db_session() as db:
        post = Post(
            title=title,
            slug=generate_slug(title),
            summary=summary,
            content=content,
            is_published=bool(is_published),
            category_id=category_id,
        )
        if tag_ids:
            post.tags = db.query(Tag).filter(Tag.id.in_(tag_ids)).all()
        db.add(post)
        db.flush()
        return RedirectResponse("/admin/posts", status_code=302)


@router.get("/admin/posts/{post_id}", dependencies=[Depends(require_admin)])
def edit_post_form(request: Request, post_id: int):
    with get_db_session() as db:
        post = db.get(Post, post_id)
        categories = db.query(Category).order_by(Category.name.asc()).all()
        tags = db.query(Tag).order_by(Tag.name.asc()).all()
        return request.app.state.templates.TemplateResponse(
            "admin/post_form.html",
            {"request": request, "title": f"Edit Post #{post_id}", "post": post, "categories": categories, "tags": tags},
        )


@router.post("/admin/posts/{post_id}", dependencies=[Depends(require_admin)])
def update_post(
    request: Request,
    post_id: int,
    title: str = Form(...),
    summary: Optional[str] = Form(None),
    content: str = Form(...),
    is_published: Optional[bool] = Form(False),
    category_id: Optional[int] = Form(None),
    tag_ids: Optional[List[int]] = Form(None),
):
    with get_db_session() as db:
        post = db.get(Post, post_id)
        if not post:
            return RedirectResponse("/admin/posts", status_code=302)
        post.title = title
        post.slug = generate_slug(title)
        post.summary = summary
        post.content = content
        post.is_published = bool(is_published)
        post.category_id = category_id
        post.tags = db.query(Tag).filter(Tag.id.in_(tag_ids)).all() if tag_ids else []
        db.add(post)
        return RedirectResponse("/admin/posts", status_code=302)


@router.post("/admin/posts/{post_id}/delete", dependencies=[Depends(require_admin)])
def delete_post(request: Request, post_id: int):
    with get_db_session() as db:
        post = db.get(Post, post_id)
        if post:
            db.delete(post)
        return RedirectResponse("/admin/posts", status_code=302)