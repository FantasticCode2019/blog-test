# Blog Website (FastAPI + SQLite)

A simple, production-ready blog website built with FastAPI, SQLAlchemy (SQLite), Jinja2 templates, and basic session-based authentication. Includes an admin dashboard for managing posts, categories, and tags.

## Features
- Public site
  - Home page with latest posts and pagination
  - Post detail pages with SEO-friendly slugs
  - Categories and tags browsing and detail pages with pagination
  - Full-text like search across title/summary/content
- Admin dashboard
  - Sign in/out (session cookies)
  - CRUD for posts, categories, and tags
  - Draft/publish toggle
  - Media uploads page for images (served from `/static/uploads`)
- Architecture designed for clarity and extensibility

## Tech Stack
- FastAPI (ASGI) for the web framework
- SQLAlchemy 2.0 ORM with SQLite database
- Jinja2 for server-side rendered templates
- Starlette sessions for authentication
- Passlib (bcrypt) for password hashing
- Uvicorn for local development server

## Project Structure

```
blogsite/
  app/
    main.py                # App entrypoint
    database.py            # Engine, session factory, init helpers
    models.py              # SQLAlchemy ORM models
    auth.py                # Auth routes and utilities
    deps.py                # Shared dependencies (auth guards, pagination)
    utils.py               # Helpers (slugs, time, unique slugs)
    routers/
      posts.py             # Public & admin post routes + search + uploads
      categories.py        # Admin CRUD + public listing/detail
      tags.py              # Admin CRUD + public listing/detail
    templates/
      base.html
      index.html
      list.html
      post_detail.html
      login.html
      categories.html
      tags.html
      admin/
        dashboard.html
        posts.html
        post_form.html
        categories.html
        category_form.html
        tags.html
        tag_form.html
        uploads.html
    static/
      styles.css
      uploads/            # created at runtime
  requirements.txt
```

## Setup

1. Python 3.10+ is recommended.
2. Create and activate a virtual environment (optional but recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run the development server:

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open `http://localhost:8000` in your browser.

## Default Admin User

On first run, the app will create the database tables and ensure a default admin user exists:

- Username: `admin`
- Password: `admin123`

Change the password immediately after first login from the inline change password form (coming soon) or update it in the database.

You can override the initial admin via environment variables:

- `BLOG_ADMIN_USERNAME`
- `BLOG_ADMIN_PASSWORD`
- `BLOG_SECRET_KEY` (for session signing; auto-generated if not set, but set it for production)

## Configuration

Environment variables:
- `BLOG_DATABASE_URL` (default: `sqlite:///./blog.db`)
- `BLOG_SECRET_KEY` (default: random on boot; persist for real deployments)
- `BLOG_ADMIN_USERNAME` (default: `admin`)
- `BLOG_ADMIN_PASSWORD` (default: `admin123`)

## Tips
- Image uploads are saved to `app/static/uploads/`. Use the uploaded URL in post content.
- Slugs are automatically made unique when you rename posts/categories/tags.

## Tests

For brevity, automated tests are not included in this starter. You can add pytest and starlette test client if needed.

## License

MIT