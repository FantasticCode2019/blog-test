import os
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.templating import Jinja2Templates
from sqlalchemy import text

from .database import engine
from .models import Base, User
from .auth import router as auth_router, hash_password
from .routers import posts as posts_router
from .routers import categories as categories_router
from .routers import tags as tags_router
from .routers import api as api_router
from .deps import get_secret_key

app = FastAPI(title="Blog Website")

# Static files
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# Templates
templates_dir = Path(__file__).parent / "templates"
templates_dir.mkdir(parents=True, exist_ok=True)
app.state.templates = Jinja2Templates(directory=str(templates_dir))
app.state.templates.env.globals["now"] = datetime.utcnow

# Sessions
app.add_middleware(SessionMiddleware, secret_key=str(get_secret_key()))

# CORS (adjust for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    # Create tables
    Base.metadata.create_all(bind=engine)

    # Lightweight migrations for SQLite
    with engine.begin() as conn:
        # Users.role
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS __migrations_dummy__ (id INTEGER PRIMARY KEY)
        """))
        res = conn.execute(text("PRAGMA table_info(users)")).fetchall()
        user_cols = {r[1] for r in res}
        if "role" not in user_cols:
            conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'admin'"))
        # Posts.content_format and cover_image_url
        res = conn.execute(text("PRAGMA table_info(posts)")).fetchall()
        post_cols = {r[1] for r in res}
        if "content_format" not in post_cols:
            conn.execute(text("ALTER TABLE posts ADD COLUMN content_format VARCHAR(20) NOT NULL DEFAULT 'html'"))
        if "cover_image_url" not in post_cols:
            conn.execute(text("ALTER TABLE posts ADD COLUMN cover_image_url VARCHAR(500)"))

    # Ensure default admin user
    from .database import get_db_session

    admin_username = os.getenv("BLOG_ADMIN_USERNAME", "admin")
    admin_password = os.getenv("BLOG_ADMIN_PASSWORD", "admin123")

    with get_db_session() as db:
        existing = db.query(User).filter(User.username == admin_username).first()
        if not existing:
            db.add(
                User(
                    username=admin_username,
                    password_hash=hash_password(admin_password),
                    is_admin=True,
                    role="admin",
                )
            )


# Routers
app.include_router(auth_router)
app.include_router(posts_router.router)
app.include_router(categories_router.router)
app.include_router(tags_router.router)
app.include_router(api_router.router, prefix="/api")


@app.get("/healthz", include_in_schema=False)
def healthz():
    return {"status": "ok"}