"""
CRUD operations (PyMongo) for users, complaints and feedback.
Every function here is one clear MongoDB operation, so each can be explained in the viva.
"""
import re

from pymongo import DESCENDING
from pymongo.errors import DuplicateKeyError

from database.mongodb import get_db, next_id, utcnow


# ============================== USERS ==============================
def create_user(name, email, password_hash, role="student"):
    """CREATE - insert_one. Raises DuplicateKeyError if the e-mail already exists (unique index)."""
    doc = {
        "user_id": next_id("USR", "users"),
        "name": name,
        "email": email.lower(),
        "password_hash": password_hash,
        "role": role,
        "created_at": utcnow(),
    }
    get_db().users.insert_one(doc)
    return doc


def find_user_by_email(email):
    """READ - find_one with a filter on the unique index."""
    return get_db().users.find_one({"email": email.lower()})


def find_user_by_id(user_id):
    return get_db().users.find_one({"user_id": user_id})


# ============================ COMPLAINTS ===========================
def create_complaint(student, title, description, location, prediction, similar, image_filename=None):
    """CREATE - one complaint document with the ML prediction and first status_history entry."""
    now = utcnow()
    doc = {
        "complaint_id": next_id("CMP", "complaints"),
        "student_id": student["user_id"],
        "student_name": student["name"],
        "title": title,
        "description": description,
        "location": location,
        "predicted_category": prediction["category"],
        "category_confidence": prediction["category_confidence"],
        "predicted_urgency": prediction["urgency"],
        "urgency_confidence": prediction["urgency_confidence"],
        "final_urgency": prediction["urgency"],
        "urgency_overridden": False,
        "status": "Pending",
        "assigned_department": None,
        "image_filename": image_filename,
        "similar_complaints": [{"complaint_id": s["complaint_id"], "score": s["score"]} for s in similar],
        "status_history": [{"status": "Pending", "updated_at": now, "updated_by": student["user_id"],
                            "note": "Complaint submitted"}],
        "created_at": now,
        "updated_at": now,
        "resolved_at": None,
    }
    get_db().complaints.insert_one(doc)
    return doc


def get_complaint(complaint_id):
    """READ - find_one by business id."""
    return get_db().complaints.find_one({"complaint_id": complaint_id})


def complaints_of_student(student_id, limit=100):
    """READ - find + filter + sort + limit (uses the student_created compound index)."""
    return list(get_db().complaints.find({"student_id": student_id}).sort("created_at", DESCENDING).limit(limit))


def search_complaints(filters=None, text=None, page=1, per_page=15):
    """READ - dynamic filter (category/urgency/location/status/department) + optional $text search + paging."""
    filters = filters or {}
    query = {}
    mapping = {"category": "predicted_category", "urgency": "final_urgency", "location": "location",
               "status": "status", "department": "assigned_department"}
    for key, field in mapping.items():
        if filters.get(key):
            query[field] = filters[key]
    if filters.get("department") == "__none__":
        query["assigned_department"] = None
    if text:
        query["$text"] = {"$search": text}
    coll = get_db().complaints
    total = coll.count_documents(query)
    cursor = (coll.find(query).sort("created_at", DESCENDING)
              .skip((page - 1) * per_page).limit(per_page))
    return list(cursor), total


def candidates_for_similarity(limit=500):
    """READ - recent complaints (only the fields needed) used by the similarity search."""
    cur = (get_db().complaints
           .find({}, {"_id": 0, "complaint_id": 1, "title": 1, "description": 1, "location": 1,
                      "status": 1, "predicted_category": 1})
           .sort("created_at", DESCENDING).limit(limit))
    out = []
    for c in cur:
        c["text"] = f"{c['title']}. {c['description']}"
        out.append(c)
    return out


def update_status(complaint_id, new_status, admin_id, note=""):
    """UPDATE - $set the new status and $push an entry into the embedded status_history array."""
    now = utcnow()
    entry = {"status": new_status, "updated_at": now, "updated_by": admin_id}
    if note:
        entry["note"] = note
    res = get_db().complaints.update_one(
        {"complaint_id": complaint_id},
        {"$set": {"status": new_status, "updated_at": now,
                  "resolved_at": now if new_status == "Resolved" else None},
         "$push": {"status_history": entry}},
    )
    return res.modified_count == 1


def assign_department(complaint_id, department_name):
    """UPDATE - $set assigned_department."""
    res = get_db().complaints.update_one(
        {"complaint_id": complaint_id},
        {"$set": {"assigned_department": department_name, "updated_at": utcnow()}})
    return res.matched_count == 1


def override_urgency(complaint_id, urgency):
    """UPDATE - admin overrides the advisory ML urgency (predicted_urgency stays unchanged)."""
    res = get_db().complaints.update_one(
        {"complaint_id": complaint_id},
        {"$set": {"final_urgency": urgency, "urgency_overridden": True, "updated_at": utcnow()}})
    return res.matched_count == 1


def delete_complaint(complaint_id):
    """DELETE - delete_one (used by the demo script; not exposed in the web UI)."""
    return get_db().complaints.delete_one({"complaint_id": complaint_id}).deleted_count == 1


# ============================= FEEDBACK ============================
def add_feedback(complaint_id, student_id, rating, text):
    """CREATE - one feedback per complaint (unique index). Returns False if feedback already exists."""
    doc = {"complaint_id": complaint_id, "student_id": student_id, "rating": int(rating),
           "feedback": text or "", "created_at": utcnow()}
    try:
        get_db().feedback.insert_one(doc)
        return True
    except DuplicateKeyError:
        return False


def get_feedback(complaint_id):
    return get_db().feedback.find_one({"complaint_id": complaint_id})


def list_departments():
    return list(get_db().departments.find({}, {"_id": 0}).sort("department_name", 1))


def escape_regex(s):
    return re.escape(s)
