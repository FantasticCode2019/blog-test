from typing import Optional
from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi import status
from fastapi.responses import RedirectResponse
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .database import get_db_session
from .models import User

router = APIRouter(include_in_schema=False)

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


@router.get("/login")
def login_form(request: Request):
    return request.app.state.templates.TemplateResponse(
        "login.html",
        {"request": request, "title": "Sign In"},
    )


@router.post("/login")
def login(
    request: Request,
    response: Response,
    username: str = Form(...),
    password: str = Form(...),
):
    with get_db_session() as db:
        user: Optional[User] = db.query(User).filter(User.username == username).first()
        if not user or not verify_password(password, user.password_hash):
            # Re-render login with error
            return request.app.state.templates.TemplateResponse(
                "login.html",
                {"request": request, "title": "Sign In", "error": "Invalid credentials"},
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        request.session["user"] = {"id": user.id, "username": user.username, "is_admin": user.is_admin}
        return RedirectResponse("/admin", status_code=status.HTTP_302_FOUND)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=status.HTTP_302_FOUND)