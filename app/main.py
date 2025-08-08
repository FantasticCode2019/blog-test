import os
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.templating import Jinja2Templates

from .database import engine
from .models import Base, User
from .auth import router as auth_router, hash_password
from .routers import posts as posts_router
from .routers import categories as categories_router
from .routers import tags as tags_router
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
                )
            )


# Routers
app.include_router(auth_router)
app.include_router(posts_router.router)
app.include_router(categories_router.router)
app.include_router(tags_router.router)


@app.get("/healthz", include_in_schema=False)
def healthz():
    return {"status": "ok"}