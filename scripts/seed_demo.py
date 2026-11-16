"""
Fills MongoDB with DEMO data so the dashboards and analytics have something to show:
8 demo students, ~150 complaints spread over the last 60 days, status history, feedback.

    python -m scripts.seed_demo            # seed only if there are no complaints yet
    python -m scripts.seed_demo --reset    # delete complaints/feedback first, then seed again

Demo student login: student1@example.com ... student8@example.com / Student@123
"""
import random
import sys
from datetime import timedelta

from werkzeug.security import generate_password_hash

from config import CATEGORY_TO_DEPARTMENT, LOCATIONS
from data.generate_dataset import CATEGORIES as GEN_CATEGORIES
from data.generate_dataset import make_row
from database import repository as repo
from database.mongodb import get_db, init_db, next_id, utcnow
from ml import predict as ml

DEMO_PASSWORD = "Student@123"
# hours (min, max) a department typically needs to start / finish work - gives the reports variety
SPEED = {
    "IT Department": (1, 10, 4, 36), "Electrical Maintenance": (2, 14, 6, 60),
    "Civil & Plumbing": (4, 30, 12, 120), "Academic Facilities": (3, 20, 8, 80),
    "Hostel Administration": (3, 24, 10, 100), "Housekeeping": (1, 8, 2, 24),
    "Security Office": (1, 6, 2, 30), "General Administration": (6, 48, 24, 160),
}
RECURRING_STORY = [
    "Wi-Fi is not working in the central library since morning.",
    "Unable to connect to library internet, connection unavailable.",
    "Internet connection is very slow in the central library today.",
    "Library Wi-Fi keeps disconnecting, cannot download study material.",
    "Wifi down in central library again, third time this week.",
]


def _title(text):
    """Short title = the complaint text cut at a word boundary (max ~70 characters)."""
    text = text.strip()
    if len(text) <= 70:
        return text.rstrip(".")
    return text[:70].rsplit(" ", 1)[0].rstrip(".,") + "..."


def seed(reset=False, total=150, seed_value=7):
    db = init_db()
    if reset:
        db.complaints.delete_many({})
        db.feedback.delete_many({})
        db.counters.delete_one({"_id": "complaints"})
    elif db.complaints.count_documents({}) > 0:
        print("[seed] Complaints already exist - nothing to do (use --reset to rebuild).")
        return

    rng = random.Random(seed_value)
    students = []
    for i in range(1, 9):
        email = f"student{i}@example.com"
        u = repo.find_user_by_email(email) or repo.create_user(
            f"Demo Student {i}", email, generate_password_hash(DEMO_PASSWORD))
        students.append(u)

    now = utcnow()
    cats = list(GEN_CATEGORIES)
    jobs = []                                    # (text, location, created_at)
    for _ in range(total):
        text, _, _, loc = make_row(rng, rng.choice(cats))
        age_hours = rng.random() ** 1.3 * 60 * 24
        jobs.append((text, loc, now - timedelta(hours=age_hours)))
    for k, text in enumerate(RECURRING_STORY):   # a deliberate recurring issue for the demo
        jobs.append((text, "Central Library", now - timedelta(days=5 - k, hours=rng.randint(0, 6))))
    jobs.sort(key=lambda j: j[2])

    complaints, feedback = [], []
    for text, loc, created in jobs:
        pred = ml.predict(text)
        dept = CATEGORY_TO_DEPARTMENT[pred["category"]]
        st_lo, st_hi, fin_lo, fin_hi = SPEED[dept]
        student = rng.choice(students)
        age_days = (now - created).total_seconds() / 86400

        history = [{"status": "Pending", "updated_at": created, "updated_by": student["user_id"],
                    "note": "Complaint submitted"}]
        status, assigned, resolved_at = "Pending", None, None
        roll = rng.random()
        resolved_p = 0.85 if age_days > 14 else 0.55 if age_days > 3 else 0.15
        progress_p = 0.10 if age_days > 14 else 0.30 if age_days > 3 else 0.25
        reject_p = 0.04
        if roll < reject_p:
            status = "Rejected"
            history.append({"status": "Rejected", "updated_at": created + timedelta(hours=rng.randint(2, 30)),
                            "updated_by": "USR1001", "note": "Not a campus issue"})
        elif roll < reject_p + resolved_p or roll < reject_p + resolved_p + progress_p:
            assigned = dept
            t_prog = created + timedelta(hours=rng.uniform(st_lo, st_hi))
            if t_prog < now:
                status = "In Progress"
                history.append({"status": "In Progress", "updated_at": t_prog, "updated_by": "USR1001",
                                "note": f"Assigned to {dept}"})
                if roll < reject_p + resolved_p:
                    t_res = t_prog + timedelta(hours=rng.uniform(fin_lo, fin_hi))
                    if t_res < now:
                        status, resolved_at = "Resolved", t_res
                        history.append({"status": "Resolved", "updated_at": t_res, "updated_by": "USR1001",
                                        "note": "Issue fixed"})
            else:
                assigned = dept          # assigned but work not started yet
        cid = next_id("CMP", "complaints")
        complaints.append({
            "complaint_id": cid, "student_id": student["user_id"], "student_name": student["name"],
            "title": _title(text), "description": text, "location": loc,
            "predicted_category": pred["category"], "category_confidence": pred["category_confidence"],
            "predicted_urgency": pred["urgency"], "urgency_confidence": pred["urgency_confidence"],
            "final_urgency": pred["urgency"], "urgency_overridden": False,
            "status": status, "assigned_department": assigned, "image_filename": None,
            "similar_complaints": [], "status_history": history,
            "created_at": created, "updated_at": history[-1]["updated_at"], "resolved_at": resolved_at,
        })
        if status == "Resolved" and rng.random() < 0.6:
            fast = (resolved_at - created).total_seconds() / 3600 < 48
            rating = rng.choice([4, 5, 5]) if fast else rng.choice([2, 3, 4, 4])
            feedback.append({"complaint_id": cid, "student_id": student["user_id"], "rating": rating,
                             "feedback": rng.choice(["Resolved quickly, thanks.", "Good work.", "Took a while but fixed.",
                                                     "Please be faster next time.", ""]),
                             "created_at": resolved_at + timedelta(hours=rng.randint(1, 20))})

    db.complaints.insert_many(complaints)
    if feedback:
        db.feedback.insert_many(feedback)
    print(f"[seed] Inserted {len(complaints)} complaints, {len(feedback)} feedback entries, "
          f"{len(students)} demo students (password: {DEMO_PASSWORD}).")


if __name__ == "__main__":
    seed(reset="--reset" in sys.argv)
