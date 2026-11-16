"""Test fixtures. Tests use their own database (campuspulse_test) - your real data is never touched."""
import io
import re

import pytest

from config import Config

Config.MONGO_DB_NAME = "campuspulse_test"      # must be set before the app/database modules are used

from database.mongodb import get_client, get_db, init_db     # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _fresh_database():
    init_db()                                   # fails early with a clear message if MongoDB is down
    get_client().drop_database(Config.MONGO_DB_NAME)
    init_db()
    yield
    get_client().drop_database(Config.MONGO_DB_NAME)


@pytest.fixture()
def app(tmp_path):
    from app import create_app
    app = create_app({"TESTING": True, "UPLOAD_FOLDER": str(tmp_path)}, init_database=False)
    return app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db():
    return get_db()


def csrf_from(client, url="/login"):
    html = client.get(url).get_data(as_text=True)
    return re.search(r'name="csrf-token" content="([0-9a-f]+)"', html).group(1)


def post(client, url, data=None, page="/login", **kw):
    data = dict(data or {})
    data["csrf_token"] = csrf_from(client, page)
    return client.post(url, data=data, **kw)


def login(client, email, password):
    return post(client, "/login", {"email": email, "password": password})


def register(client, name, email, password="Passw0rdX"):
    return post(client, "/register", {"name": name, "email": email, "password": password, "confirm": password},
                page="/register")


@pytest.fixture()
def student_client(app):
    c = app.test_client()
    email = f"s_{id(c)}@test.com"
    assert register(c, "Test Student", email).status_code == 302
    assert login(c, email, "Passw0rdX").status_code == 302
    c.student_email = email
    return c


@pytest.fixture()
def admin_client(app):
    c = app.test_client()
    assert login(c, Config.ADMIN_EMAIL, Config.ADMIN_PASSWORD).status_code == 302
    return c
