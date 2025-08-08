import os
from fastapi import Depends, HTTPException, Request, status
from starlette.datastructures import Secret


def get_secret_key() -> Secret:
    key = os.getenv("BLOG_SECRET_KEY")
    if not key:
        key = "dev-secret-key-change-me"
    return Secret(key)


def require_admin(request: Request):
    user = request.session.get("user")
    if not user or not user.get("is_admin"):
        # Redirect to login
        raise HTTPException(status_code=status.HTTP_302_FOUND, headers={"Location": "/login"})
    return user


def require_user(request: Request):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=status.HTTP_302_FOUND, headers={"Location": "/login"})
    return user


def get_api_token() -> str:
    return os.getenv("API_TOKEN", "")


def get_site_base_url() -> str:
    return os.getenv("SITE_BASE_URL", "http://localhost:8000")