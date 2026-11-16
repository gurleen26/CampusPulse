"""Registration, login and logout."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import UserMixin, current_user, login_required, login_user, logout_user
from pymongo.errors import DuplicateKeyError, WriteError
from werkzeug.security import check_password_hash, generate_password_hash

from database import repository as repo
from utils import EMAIL_RE, clean_str, flash_errors, safe_next_url, validate_password

bp = Blueprint("auth", __name__)


class User(UserMixin):
    """Thin wrapper so Flask-Login can work with a MongoDB user document."""

    def __init__(self, doc):
        self.user_id = doc["user_id"]
        self.name = doc["name"]
        self.email = doc["email"]
        self.role = doc["role"]

    def get_id(self):
        return self.user_id


def load_user(user_id):
    doc = repo.find_user_by_id(user_id)
    return User(doc) if doc else None


def _home_for(user):
    return url_for("admin.dashboard") if user.role == "admin" else url_for("student.dashboard")


@bp.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(_home_for(current_user))
    return render_template("index.html")


@bp.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(_home_for(current_user))
    if request.method == "POST":
        name = clean_str(request.form.get("name"), 80)
        email = clean_str(request.form.get("email"), 120).lower()
        pw, pw2 = request.form.get("password", ""), request.form.get("confirm", "")
        errors = []
        if len(name) < 2:
            errors.append("Please enter your full name.")
        if not EMAIL_RE.match(email):
            errors.append("Please enter a valid e-mail address.")
        pw_err = validate_password(pw)
        if pw_err:
            errors.append(pw_err)
        if pw != pw2:
            errors.append("Passwords do not match.")
        if errors:
            flash_errors(errors)
            return render_template("auth/register.html", name=name, email=email), 400
        try:
            repo.create_user(name, email, generate_password_hash(pw), role="student")
        except DuplicateKeyError:
            flash("An account with this e-mail already exists.", "danger")
            return render_template("auth/register.html", name=name, email=email), 400
        except WriteError:
            flash("Could not create the account (database validation failed).", "danger")
            return render_template("auth/register.html", name=name, email=email), 400
        flash("Account created. Please log in.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(_home_for(current_user))
    if request.method == "POST":
        email = clean_str(request.form.get("email"), 120).lower()
        doc = repo.find_user_by_email(email) if email else None
        if doc and check_password_hash(doc["password_hash"], request.form.get("password", "")):
            user = User(doc)
            login_user(user)
            return redirect(safe_next_url(request.args.get("next")) or _home_for(user))
        flash("Invalid e-mail or password.", "danger")
        return render_template("auth/login.html", email=email), 401
    return render_template("auth/login.html")


@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for("auth.login"))
