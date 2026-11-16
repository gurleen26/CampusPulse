"""Database tests: validation rules, unique indexes, CRUD and aggregation (run against real MongoDB)."""
import pytest
from pymongo.errors import DuplicateKeyError, WriteError
from werkzeug.security import generate_password_hash

from database import aggregations as agg
from database import repository as repo
from database.mongodb import next_id, utcnow

PRED = {"category": "Network", "category_confidence": 0.9, "urgency": "Medium", "urgency_confidence": 0.8}


def make_student(db):
    return repo.create_user("Dummy Student", f"dummy{next_id('X', 'testseq')}@test.com", generate_password_hash("Passw0rdX"))


def valid_complaint(student):
    return repo.create_complaint(student, "Wi-Fi not working", "Wi-Fi is unavailable in the library", "Central Library", PRED, [])


def test_next_id_increments(db):
    a, b = next_id("T", "tmp_counter"), next_id("T", "tmp_counter")
    assert a != b and int(b[1:]) == int(a[1:]) + 1


def test_unique_email_index(db):
    s = make_student(db)
    with pytest.raises(DuplicateKeyError):
        repo.create_user("Other", s["email"], generate_password_hash("Passw0rdX"))


def test_validator_rejects_bad_documents(db):
    s = make_student(db)
    good = valid_complaint(s)
    bad = {k: v for k, v in good.items() if k != "_id"}
    bad["complaint_id"] = "CMP9999991"

    for field, value in [("status", "Done"), ("location", "Moon"), ("predicted_category", "Food"),
                         ("title", "abc"), ("student_id", "bad id"), ("created_at", "2026-01-01")]:
        doc = dict(bad, **{field: value})
        with pytest.raises(WriteError):
            db.complaints.insert_one(doc)

    missing = dict(bad)
    del missing["description"]
    with pytest.raises(WriteError):
        db.complaints.insert_one(missing)


def test_feedback_validation_and_uniqueness(db):
    s = make_student(db)
    c = valid_complaint(s)
    with pytest.raises(WriteError):
        db.feedback.insert_one({"complaint_id": c["complaint_id"], "student_id": s["user_id"], "rating": 9, "created_at": utcnow()})
    assert repo.add_feedback(c["complaint_id"], s["user_id"], 5, "great")
    assert not repo.add_feedback(c["complaint_id"], s["user_id"], 4, "again")


def test_user_validator_rejects_bad_email_and_role(db):
    base = {"user_id": "USR9999991", "name": "Abc", "email": "a@b.co", "password_hash": "x" * 30,
            "role": "student", "created_at": utcnow()}
    for field, value in [("email", "not-an-email"), ("role", "superuser")]:
        with pytest.raises(WriteError):
            db.users.insert_one(dict(base, **{field: value}))


def test_crud_lifecycle(db):
    s = make_student(db)
    c = valid_complaint(s)
    cid = c["complaint_id"]
    assert repo.get_complaint(cid)["status"] == "Pending"

    assert repo.assign_department(cid, "IT Department")
    assert repo.update_status(cid, "In Progress", "USR1001", "started")
    assert repo.update_status(cid, "Resolved", "USR1001", "fixed")
    doc = repo.get_complaint(cid)
    assert doc["status"] == "Resolved" and doc["resolved_at"] is not None
    assert [h["status"] for h in doc["status_history"]] == ["Pending", "In Progress", "Resolved"]

    assert repo.override_urgency(cid, "High")
    doc = repo.get_complaint(cid)
    assert doc["final_urgency"] == "High" and doc["predicted_urgency"] == "Medium" and doc["urgency_overridden"]

    rows, total = repo.search_complaints({"status": "Resolved", "category": "Network"}, None, 1, 10)
    assert total >= 1
    rows, _ = repo.search_complaints({}, "Wi-Fi library", 1, 10)       # $text search
    assert any(r["complaint_id"] == cid for r in rows)

    assert repo.delete_complaint(cid)
    assert repo.get_complaint(cid) is None


def test_aggregations_return_expected_shapes(db):
    s = make_student(db)
    for _ in range(3):
        c = valid_complaint(s)
        repo.assign_department(c["complaint_id"], "IT Department")
        repo.update_status(c["complaint_id"], "In Progress", "USR1001")
        repo.update_status(c["complaint_id"], "Resolved", "USR1001")
        repo.add_feedback(c["complaint_id"], s["user_id"], 4, "ok")

    counts = {r["_id"]: r["count"] for r in agg.run(agg.category_counts())}
    assert counts["Network"] >= 3
    assert agg.summary_numbers()["total"] >= 3
    rec = agg.run(agg.recurring_issues(30, 3))
    assert any(r["_id"] == {"category": "Network", "location": "Central Library"} for r in rec)
    perf = {r["_id"]: r for r in agg.run(agg.department_performance())}
    assert perf["IT Department"]["resolved"] >= 3 and perf["IT Department"]["resolution_rate"] > 0
    fb = {r["_id"]: r for r in agg.run(agg.feedback_by_department(), "feedback")}
    assert fb["IT Department"]["avg_rating"] == 4.0
    assert agg.run(agg.first_response_time_by_category())
    assert agg.run(agg.resolution_time_buckets())
    assert agg.run(agg.top_reporters(3))
