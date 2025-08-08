from typing import Optional, List
from fastapi import APIRouter, Depends, Form, Request, UploadFile, File
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from pathlib import Path
import json
try:
    import markdown2  # type: ignore
except Exception:  # pragma: no cover
    markdown2 = None

from ..database import get_db_session
from ..models import Post, Category, Tag
from ..utils import generate_slug, paginate, generate_unique_slug
from ..deps import require_admin, get_site_base_url
from ..storage import get_storage

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
        # Render markdown if needed
        content_html = post.content
        try:
            if getattr(post, "content_format", "html") == "markdown" and markdown2:
                content_html = markdown2.markdown(post.content, extras=["fenced-code-blocks", "tables", "strike", "toc"])
        except Exception:
            content_html = post.content
        return request.app.state.templates.TemplateResponse(
            "post_detail.html",
            {
                "request": request,
                "post": post,
                "content_html": content_html,
                "title": post.title,
                "meta_description": post.summary or "",
            },
        )


# Public search
@router.get("/search")
def search(request: Request, q: Optional[str] = None, page: int = 1, page_size: int = 10):
    query_text = (q or "").strip()
    posts = []
    total_pages = 1
    with get_db_session() as db:
        if query_text:
            base_query = db.query(Post).filter(
                Post.is_published == True,  # noqa: E712
                func.lower(Post.title).like(f"%{query_text.lower()}%")
                | func.lower(func.coalesce(Post.summary, "")).like(f"%{query_text.lower()}%")
                | func.lower(Post.content).like(f"%{query_text.lower()}%")
            )
            total_posts = base_query.count()
            total_pages, page, offset = paginate(total_posts, page, page_size)
            posts = (
                base_query.order_by(Post.created_at.desc()).offset(offset).limit(page_size).all()
            )
        return request.app.state.templates.TemplateResponse(
            "list.html",
            {
                "request": request,
                "posts": posts,
                "page": page,
                "total_pages": total_pages,
                "title": "Search",
                "heading": f"Search results for \"{query_text}\"" if query_text else "Search",
            },
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
    content_format: str = Form("markdown"),
    cover_image_url: Optional[str] = Form(None),
    is_published: Optional[bool] = Form(False),
    category_id: Optional[int] = Form(None),
    tag_ids: Optional[List[int]] = Form(None),
):
    with get_db_session() as db:
        post = Post(
            title=title,
            slug=generate_unique_slug(db, Post, title),
            summary=summary,
            content=content,
            content_format=content_format,
            cover_image_url=cover_image_url,
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
    content_format: str = Form("markdown"),
    cover_image_url: Optional[str] = Form(None),
    is_published: Optional[bool] = Form(False),
    category_id: Optional[int] = Form(None),
    tag_ids: Optional[List[int]] = Form(None),
):
    with get_db_session() as db:
        post = db.get(Post, post_id)
        if not post:
            return RedirectResponse("/admin/posts", status_code=302)
        post.title = title
        post.slug = generate_unique_slug(db, Post, title, exclude_id=post.id)
        post.summary = summary
        post.content = content
        post.content_format = content_format
        post.cover_image_url = cover_image_url
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


# Preview unpublished post for admins
@router.get("/admin/posts/{post_id}/preview", dependencies=[Depends(require_admin)])
def preview_post(request: Request, post_id: int):
    with get_db_session() as db:
        post = db.get(Post, post_id)
        if not post:
            return request.app.state.templates.TemplateResponse(
                "post_detail.html", {"request": request, "error": "Post not found", "title": "Not Found"}, status_code=404
            )
        content_html = post.content
        try:
            if getattr(post, "content_format", "html") == "markdown" and markdown2:
                content_html = markdown2.markdown(post.content, extras=["fenced-code-blocks", "tables", "strike", "toc"])
        except Exception:
            content_html = post.content
        return request.app.state.templates.TemplateResponse(
            "post_detail.html",
            {
                "request": request,
                "post": post,
                "content_html": content_html,
                "title": post.title,
                "meta_description": post.summary or "",
            },
        )


# Autosave draft endpoint
@router.post("/admin/posts/autosave", dependencies=[Depends(require_admin)])
async def autosave_post(request: Request):
    payload = await request.json()
    post_id = payload.get("id")
    with get_db_session() as db:
        if post_id:
            post = db.get(Post, int(post_id))
        else:
            post = None
        title = payload.get("title") or "Untitled"
        content = payload.get("content") or ""
        summary = payload.get("summary")
        content_format = payload.get("content_format") or "markdown"
        cover_image_url = payload.get("cover_image_url")
        category_id = payload.get("category_id")
        tag_ids = payload.get("tag_ids") or []
        is_published = bool(payload.get("is_published") or False)
        if not post:
            post = Post(
                title=title,
                slug=generate_unique_slug(db, Post, title),
                summary=summary,
                content=content,
                content_format=content_format,
                cover_image_url=cover_image_url,
                is_published=is_published,
                category_id=category_id,
            )
        else:
            post.title = title
            post.slug = generate_unique_slug(db, Post, title, exclude_id=post.id)
            post.summary = summary
            post.content = content
            post.content_format = content_format
            post.cover_image_url = cover_image_url
            post.is_published = is_published
            post.category_id = category_id
            post.tags = db.query(Tag).filter(Tag.id.in_(tag_ids)).all() if tag_ids else []
        db.add(post)
        db.flush()
        return {"ok": True, "id": post.id}


# Admin uploads using storage backend
@router.get("/admin/uploads", dependencies=[Depends(require_admin)])
def uploads_page(request: Request):
    # For S3, we cannot list without permissions; keep page simple
    return request.app.state.templates.TemplateResponse(
        "admin/uploads.html",
        {"request": request, "title": "Uploads", "files": []},
    )


@router.post("/admin/uploads", dependencies=[Depends(require_admin)])
def handle_upload(request: Request, file: UploadFile = File(...)):
    content_type = file.content_type or ""
    if not content_type.startswith("image/"):
        return request.app.state.templates.TemplateResponse(
            "admin/uploads.html",
            {"request": request, "title": "Uploads", "error": "Only image files are allowed.", "files": []},
            status_code=400,
        )
    storage = get_storage()
    data = file.file.read()
    file_url = storage.save_file(data, content_type, file.filename or "upload")
    return request.app.state.templates.TemplateResponse(
        "admin/uploads.html",
        {"request": request, "title": "Uploads", "files": [], "uploaded_url": file_url},
    )


# RSS feed
@router.get("/rss.xml", include_in_schema=False)
def rss_feed():
    base_url = get_site_base_url().rstrip("/")
    with get_db_session() as db:
        posts = (
            db.query(Post)
            .filter(Post.is_published == True)  # noqa: E712
            .order_by(Post.created_at.desc())
            .limit(50)
            .all()
        )
    items = []
    for p in posts:
        items.append(
            f"""
            <item>
              <title>{p.title}</title>
              <link>{base_url}/post/{p.slug}</link>
              <guid isPermaLink=\"true\">{base_url}/post/{p.slug}</guid>
              <pubDate>{p.created_at.strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate>
              <description><![CDATA[{p.summary or ''}]]></description>
            </item>
            """
        )
    rss = f"""
    <?xml version=\"1.0\" encoding=\"UTF-8\"?>
    <rss version=\"2.0\">
      <channel>
        <title>Blog RSS</title>
        <link>{base_url}</link>
        <description>Latest posts</description>
        {''.join(items)}
      </channel>
    </rss>
    """
    return Response(content=rss, media_type="application/rss+xml")


# Sitemap
@router.get("/sitemap.xml", include_in_schema=False)
def sitemap():
    base_url = get_site_base_url().rstrip("/")
    static_urls = ["/", "/categories", "/tags"]
    with get_db_session() as db:
        posts = db.query(Post).filter(Post.is_published == True).all()  # noqa: E712
    urls_xml = []
    for path in static_urls:
        urls_xml.append(f"<url><loc>{base_url}{path}</loc></url>")
    for p in posts:
        urls_xml.append(f"<url><loc>{base_url}/post/{p.slug}</loc></url>")
    xml = f"""
    <?xml version=\"1.0\" encoding=\"UTF-8\"?>
    <urlset xmlns=\"http://www.sitemaps.org/schemas/sitemap/0.9\">
      {''.join(urls_xml)}
    </urlset>
    """
    return Response(content=xml, media_type="application/xml")


@router.get("/robots.txt", include_in_schema=False)
def robots_txt():
    base_url = get_site_base_url().rstrip("/")
    content = f"User-agent: *\nAllow: /\nSitemap: {base_url}/sitemap.xml\n"
    return Response(content=content, media_type="text/plain")