"""Small helpers: CSRF protection, role decorators, validation, formatting."""
import re
import secrets
from datetime import datetime, timezone
from functools import wraps

from flask import abort, current_app, flash, redirect, request, session, url_for
from flask_login import current_user

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


# ------------------------------ CSRF ------------------------------
def csrf_token() -> str:
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_hex(16)
    return session["_csrf"]


def verify_csrf():
    """Called before every POST request."""
    sent = request.form.get("csrf_token") or request.headers.get("X-CSRF-Token")
    if not sent or not secrets.compare_digest(sent, session.get("_csrf", "")):
        abort(400, description="Invalid or missing CSRF token. Reload the page and try again.")


# --------------------------- role checks --------------------------
def admin_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.path))
        if current_user.role != "admin":
            abort(403)
        return view(*args, **kwargs)
    return wrapper


def student_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login", next=request.path))
        if current_user.role != "student":
            abort(403)
        return view(*args, **kwargs)
    return wrapper


def safe_next_url(target):
    """Only allow redirects to paths inside this site."""
    if target and target.startswith("/") and not target.startswith("//"):
        return target
    return None


# --------------------------- validation ---------------------------
def validate_password(pw: str):
    if len(pw) < 8:
        return "Password must be at least 8 characters."
    if not re.search(r"[A-Za-z]", pw) or not re.search(r"\d", pw):
        return "Password must contain at least one letter and one number."
    return None


def clean_str(value, max_len):
    return " ".join((value or "").split())[:max_len]


# --------------------------- formatting ---------------------------
def local_time(dt, fmt="%d %b %Y, %H:%M"):
    """Stored datetimes are naive UTC; show them in the configured time zone."""
    if not isinstance(dt, datetime):
        return "-"
    try:
        from zoneinfo import ZoneInfo
        tz = ZoneInfo(current_app.config.get("DISPLAY_TIMEZONE", "UTC"))
    except Exception:
        tz = timezone.utc
    return dt.replace(tzinfo=timezone.utc).astimezone(tz).strftime(fmt)


STATUS_BADGE = {"Pending": "warning text-dark", "In Progress": "primary",
                "Resolved": "success", "Rejected": "secondary"}
URGENCY_BADGE = {"Low": "success", "Medium": "warning text-dark", "High": "danger"}


def flash_errors(errors):
    for e in errors:
        flash(e, "danger")
