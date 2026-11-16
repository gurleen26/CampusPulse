"""MongoDB connection (PyMongo), collection creation with validation, indexes and seed data."""
import sys
from datetime import datetime, timezone

from pymongo import ASCENDING, DESCENDING, MongoClient, ReturnDocument
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from werkzeug.security import generate_password_hash

from config import CATEGORY_TO_DEPARTMENT, Config
from database.schemas import VALIDATORS

_client = None


def utcnow() -> datetime:
    """Naive UTC datetime (this is what PyMongo returns when reading BSON dates)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_client() -> MongoClient:
    global _client
    if _client is None:
        _client = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=6000)
    return _client


def get_db():
    return get_client()[Config.MONGO_DB_NAME]


def check_connection() -> None:
    """Fail early with a friendly message when MongoDB is not reachable."""
    try:
        get_client().admin.command("ping")
    except (ServerSelectionTimeoutError, ConnectionFailure) as exc:
        print("\n[ERROR] Cannot connect to MongoDB.")
        print(f"        MONGO_URI = {Config.MONGO_URI.split('@')[-1]}")
        print("        - Local MongoDB: install MongoDB Community Server and make sure the service is running.")
        print("        - Atlas: set MONGO_URI in the .env file and allow your IP address in Atlas > Network Access.")
        print(f"        Details: {exc.__class__.__name__}\n")
        sys.exit(1)


def next_id(prefix: str, counter_name: str) -> str:
    """Auto-increment business ids (CMP1001, USR1001 ...) with an atomic counter document."""
    doc = get_db().counters.find_one_and_update(
        {"_id": counter_name}, {"$inc": {"seq": 1}}, upsert=True, return_document=ReturnDocument.AFTER
    )
    return f"{prefix}{1000 + doc['seq']}"


def _apply_validators(db) -> None:
    existing = set(db.list_collection_names())
    for name, validator in VALIDATORS.items():
        if name in existing:
            db.command("collMod", name, validator=validator, validationLevel="strict", validationAction="error")
        else:
            db.create_collection(name, validator=validator, validationLevel="strict", validationAction="error")


def _create_indexes(db) -> None:
    db.users.create_index([("email", ASCENDING)], unique=True, name="uniq_email")
    db.users.create_index([("user_id", ASCENDING)], unique=True, name="uniq_user_id")

    c = db.complaints
    c.create_index([("complaint_id", ASCENDING)], unique=True, name="uniq_complaint_id")
    c.create_index([("status", ASCENDING), ("created_at", DESCENDING)], name="status_created")
    c.create_index([("predicted_category", ASCENDING), ("location", ASCENDING)], name="category_location")
    c.create_index([("student_id", ASCENDING), ("created_at", DESCENDING)], name="student_created")
    c.create_index([("created_at", DESCENDING)], name="created_desc")
    c.create_index([("assigned_department", ASCENDING), ("status", ASCENDING)], name="dept_status")
    c.create_index([("title", "text"), ("description", "text")], name="text_search")

    db.departments.create_index([("department_name", ASCENDING)], unique=True, name="uniq_department")
    db.feedback.create_index([("complaint_id", ASCENDING)], unique=True, name="uniq_feedback_per_complaint")


DEPARTMENTS = [
    ("IT Department", "Network, Wi-Fi and computer-related issues", "it@campuspulse.local", ["Network"]),
    ("Electrical Maintenance", "Power supply, wiring, lights, fans and AC", "electrical@campuspulse.local", ["Electricity"]),
    ("Civil & Plumbing", "Water supply, pipes, taps and drainage", "plumbing@campuspulse.local", ["Water Supply"]),
    ("Academic Facilities", "Projectors, smart boards, benches and lab equipment", "academics@campuspulse.local", ["Classroom Equipment"]),
    ("Hostel Administration", "Hostel rooms, mess and hostel facilities", "hostel@campuspulse.local", ["Hostel Maintenance"]),
    ("Housekeeping", "Cleaning, waste collection and pest control", "housekeeping@campuspulse.local", ["Cleanliness"]),
    ("Security Office", "Campus safety, CCTV, gates and theft", "security@campuspulse.local", ["Security"]),
    ("General Administration", "Fees, ID cards, transport and other requests", "admin@campuspulse.local", ["Other"]),
]


def _seed_departments(db) -> None:
    for name, resp, email, cats in DEPARTMENTS:
        db.departments.update_one(
            {"department_name": name},
            {"$setOnInsert": {"department_name": name, "responsibility": resp,
                              "contact_email": email, "categories": cats}},
            upsert=True,
        )


def _seed_admin(db) -> None:
    if db.users.find_one({"role": "admin"}):
        return
    db.users.insert_one({
        "user_id": next_id("USR", "users"),
        "name": Config.ADMIN_NAME,
        "email": Config.ADMIN_EMAIL.lower(),
        "password_hash": generate_password_hash(Config.ADMIN_PASSWORD),
        "role": "admin",
        "created_at": utcnow(),
    })
    print(f"[DB] Admin account created: {Config.ADMIN_EMAIL}  (password from .env)")


def init_db():
    """Create collections (with validation), indexes and starter data. Safe to run repeatedly."""
    check_connection()
    db = get_db()
    _apply_validators(db)
    _create_indexes(db)
    _seed_departments(db)
    _seed_admin(db)
    return db


assert set(CATEGORY_TO_DEPARTMENT.values()) == {d[0] for d in DEPARTMENTS}, "department list out of sync"
