"""End-to-end tests of the web application (register, login, submit, admin actions, security rules)."""
import io

from database import repository as repo
from tests.conftest import csrf_from, login, post, register

COMPLAINT = {"title": "Wi-Fi not working", "description": "The Wi-Fi has not been working in the central library since morning.",
             "location": "Central Library"}


def submit(client, **override):
    data = dict(COMPLAINT, **override)
    return post(client, "/student/complaint/new", data, page="/student/complaint/new")


def last_complaint_id(resp):
    return resp.headers["Location"].rstrip("/").split("/")[-1]


def test_pages_load_for_anonymous(client):
    for url in ("/", "/login", "/register"):
        assert client.get(url).status_code == 200


def test_register_validation_and_duplicates(client):
    r = post(client, "/register", {"name": "A", "email": "bad", "password": "short", "confirm": "different"}, page="/register")
    assert r.status_code == 400
    assert register(client, "Dup User", "dup_user@test.com").status_code == 302
    assert register(client, "Dup User", "dup_user@test.com").status_code == 400


def test_login_wrong_password(client, student_client):
    r = login(client, student_client.student_email, "WrongPass1")
    assert r.status_code == 401


def test_csrf_is_enforced(client):
    r = client.post("/login", data={"email": "a@b.co", "password": "x"})
    assert r.status_code == 400


def test_access_control(client, student_client, admin_client):
    assert client.get("/student/").status_code == 302                 # anonymous -> login
    assert client.get("/admin/").status_code == 302
    assert student_client.get("/admin/").status_code == 403           # student cannot open admin pages
    assert student_client.get("/admin/complaints").status_code == 403
    assert admin_client.get("/student/").status_code == 403           # admin is not a student


def test_student_submits_and_sees_prediction(student_client):
    r = submit(student_client)
    assert r.status_code == 302
    cid = last_complaint_id(r)
    page = student_client.get(f"/student/complaint/{cid}").get_data(as_text=True)
    assert "Network" in page and "Pending" in page
    doc = repo.get_complaint(cid)
    assert doc["predicted_category"] == "Network" and doc["final_urgency"] == doc["predicted_urgency"]


def test_complaint_validation_errors(student_client):
    assert submit(student_client, title="abc").status_code == 400
    assert submit(student_client, description="short").status_code == 400
    assert submit(student_client, location="Moon").status_code == 400


def test_student_cannot_see_other_students_complaint(student_client, app):
    cid = last_complaint_id(submit(student_client))
    other = app.test_client()
    register(other, "Other Student", "other_student@test.com")
    login(other, "other_student@test.com", "Passw0rdX")
    assert other.get(f"/student/complaint/{cid}").status_code == 404


def test_similar_complaint_warning(student_client):
    first = last_complaint_id(submit(student_client))
    resp = student_client.post("/student/api/analyze", json={
        "title": "Library internet down", "description": "Unable to connect to the Wi-Fi in the library",
        "location": "Central Library"}, headers={"X-CSRF-Token": csrf_from(student_client, "/student/")})
    data = resp.get_json()
    assert data["ready"] and data["prediction"]["category"] == "Network"
    assert any(s["complaint_id"] == first for s in data["similar"])


def test_fake_image_upload_rejected(student_client):
    r = post(student_client, "/student/complaint/new",
             dict(COMPLAINT, image=(io.BytesIO(b"this is not an image"), "evil.png")),
             page="/student/complaint/new", content_type="multipart/form-data")
    assert r.status_code == 400


def test_real_image_upload_accepted_and_protected(student_client, admin_client, app):
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 40
    r = post(student_client, "/student/complaint/new",
             dict(COMPLAINT, image=(io.BytesIO(png), "photo.png")),
             page="/student/complaint/new", content_type="multipart/form-data")
    assert r.status_code == 302
    doc = repo.get_complaint(last_complaint_id(r))
    name = doc["image_filename"]
    assert name and name.endswith(".png")
    assert student_client.get(f"/uploads/{name}").status_code == 200
    assert admin_client.get(f"/uploads/{name}").status_code == 200
    other = app.test_client()
    register(other, "Nosy", "nosy@test.com")
    login(other, "nosy@test.com", "Passw0rdX")
    assert other.get(f"/uploads/{name}").status_code == 404


def test_admin_workflow_and_feedback(student_client, admin_client):
    cid = last_complaint_id(submit(student_client))
    url = f"/admin/complaints/{cid}/update"
    page = f"/admin/complaints/{cid}"

    # cannot go In Progress before a department is assigned
    post(admin_client, url, {"action": "status", "status": "In Progress"}, page=page)
    assert repo.get_complaint(cid)["status"] == "Pending"

    post(admin_client, url, {"action": "assign", "department": "IT Department"}, page=page)
    post(admin_client, url, {"action": "urgency", "urgency": "High"}, page=page)
    post(admin_client, url, {"action": "status", "status": "In Progress", "note": "working on it"}, page=page)
    doc = repo.get_complaint(cid)
    assert doc["assigned_department"] == "IT Department" and doc["final_urgency"] == "High"
    assert doc["status"] == "In Progress"

    # invalid values are rejected
    post(admin_client, url, {"action": "status", "status": "Finished"}, page=page)
    assert repo.get_complaint(cid)["status"] == "In Progress"

    # feedback is refused until resolved
    fb_url = f"/student/complaint/{cid}/feedback"
    post(student_client, fb_url, {"rating": "5"}, page=f"/student/complaint/{cid}")
    assert repo.get_feedback(cid) is None

    post(admin_client, url, {"action": "status", "status": "Resolved"}, page=page)
    post(student_client, fb_url, {"rating": "5", "feedback": "Thanks"}, page=f"/student/complaint/{cid}")
    assert repo.get_feedback(cid)["rating"] == 5
    assert len(repo.get_complaint(cid)["status_history"]) == 3


def test_student_cannot_change_status(student_client):
    cid = last_complaint_id(submit(student_client))
    r = post(student_client, f"/admin/complaints/{cid}/update", {"action": "status", "status": "Resolved"},
             page="/student/")
    assert r.status_code == 403
    assert repo.get_complaint(cid)["status"] == "Pending"


def test_admin_pages_filters_and_csv(admin_client, student_client):
    submit(student_client)
    for url in ("/admin/", "/admin/complaints", "/admin/complaints?category=Network&status=Pending",
                "/admin/complaints?q=Wi-Fi", "/admin/complaints?category=<script>"):
        assert admin_client.get(url).status_code == 200
    csv_resp = admin_client.get("/admin/export.csv?category=Network")
    assert csv_resp.status_code == 200 and csv_resp.mimetype == "text/csv"
    assert "complaint_id" in csv_resp.get_data(as_text=True)
