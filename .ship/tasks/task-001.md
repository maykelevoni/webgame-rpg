# Task 001: Project scaffold + Django settings + Neon connection

## Description
Create the Django project skeleton wired to Neon Postgres via an env var, plus
project meta files. No game logic yet — just a runnable, DB-connected shell.

## Files
- `requirements.txt` (create)
- `.env.example` (create)
- `.gitignore` (create)
- `manage.py` (create)
- `config/__init__.py` `config/settings.py` `config/urls.py` `config/wsgi.py` `config/asgi.py` (create)
- `game/__init__.py` `game/apps.py` (create — empty app registered)
- `README.md` (create — short intro + setup steps stub)

## Requirements
1. `requirements.txt`: django, dj-database-url, psycopg[binary], python-dotenv, pytest, pytest-django.
2. `settings.py`: load `.env` with python-dotenv; `DATABASES["default"]` from
   `dj_database_url.parse(os.environ["DATABASE_URL"], conn_health_checks=True, ssl_require=True)`.
3. Installed apps include `django.contrib.admin/auth/...`, `game`.
4. `STATIC_URL`/`STATICFILES_DIRS` set so `game/static/` is served; templates dir includes `game/templates`.
5. Auth redirects: `LOGIN_REDIRECT_URL="/play/"`, `LOGOUT_REDIRECT_URL="/"`, `LOGIN_URL="/accounts/login/"`.
6. `.env.example` documents `DATABASE_URL=postgres://USER:PASSWORD@HOST/dbname?sslmode=require` and `SECRET_KEY`, `DEBUG`.
7. `.gitignore` excludes `.env`, `__pycache__`, `*.pyc`, `db.sqlite3`, `.pytest_cache`.
8. `config/urls.py` includes `admin/` and (placeholder) includes for game + auth, so `manage.py check` passes.

## Acceptance Criteria
- [ ] `python manage.py check` passes (with a dummy/local DATABASE_URL it imports cleanly).
- [ ] Secret key + DEBUG read from env; `.env` is gitignored.
- [ ] `game` app is registered.

## Dependencies
- none

## Commit Message
chore: scaffold Django project wired to Neon Postgres
