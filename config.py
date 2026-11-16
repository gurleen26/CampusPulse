"""Central configuration. Values come from the .env file (or the environment)."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# ---------------------------------------------------------------------------
# Domain constants shared by the ML code, the database validators and the UI
# ---------------------------------------------------------------------------
CATEGORIES = [
    "Network",
    "Electricity",
    "Water Supply",
    "Classroom Equipment",
    "Hostel Maintenance",
    "Cleanliness",
    "Security",
    "Other",
]
URGENCY_LEVELS = ["Low", "Medium", "High"]
STATUSES = ["Pending", "In Progress", "Resolved", "Rejected"]
LOCATIONS = [
    "Central Library",
    "Hostel Block A",
    "Hostel Block B",
    "Hostel Block C",
    "Cafeteria",
    "Computer Lab",
    "Academic Block 1",
    "Academic Block 2",
    "Admin Block",
    "Auditorium",
    "Sports Complex",
    "Main Gate",
    "Parking Area",
]

# Which department normally handles which category (used as the suggested assignment)
CATEGORY_TO_DEPARTMENT = {
    "Network": "IT Department",
    "Electricity": "Electrical Maintenance",
    "Water Supply": "Civil & Plumbing",
    "Classroom Equipment": "Academic Facilities",
    "Hostel Maintenance": "Hostel Administration",
    "Cleanliness": "Housekeeping",
    "Security": "Security Office",
    "Other": "General Administration",
}


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB_NAME = os.getenv("MONGO_DB_NAME", "campuspulse")

    ADMIN_NAME = os.getenv("ADMIN_NAME", "Campus Admin")
    ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@campuspulse.local")
    ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "Admin@123")

    UPLOAD_FOLDER = str(BASE_DIR / "uploads")
    MAX_CONTENT_LENGTH = 4 * 1024 * 1024  # 4 MB uploads
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

    SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.25"))
    RECURRING_MIN_COUNT = 3        # complaints needed to call something "recurring"
    RECURRING_WINDOW_DAYS = 30
    OVERDUE_AFTER_DAYS = 3

    DISPLAY_TIMEZONE = os.getenv("DISPLAY_TIMEZONE", "Asia/Kolkata")
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
