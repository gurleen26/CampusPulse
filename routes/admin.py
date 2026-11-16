"""Administrator module: dashboard/analytics, complaint list with filters, assign, status, override, CSV export."""
import csv
import io

from flask import (Blueprint, Response, abort, current_app, flash, redirect, render_template,
                   request, url_for)
from flask_login import current_user

from analytics import build_dashboard
from config import CATEGORIES, CATEGORY_TO_DEPARTMENT, LOCATIONS, STATUSES, URGENCY_LEVELS
from database import repository as repo
from utils import admin_required, clean_str

bp = Blueprint("admin", __name__, url_prefix="/admin")

FILTER_KEYS = ("category", "urgency", "location", "status", "department")


def _filters_from_request():
    f = {k: request.args.get(k, "") for k in FILTER_KEYS}
    valid = {"category": CATEGORIES, "urgency": URGENCY_LEVELS, "location": LOCATIONS, "status": STATUSES}
    for key, allowed in valid.items():        # ignore tampered values
        if f[key] not in allowed:
            f[key] = ""
    return f


@bp.route("/")
@admin_required
def dashboard():
    return render_template("admin/dashboard.html", data=build_dashboard(),
                           overdue_days=current_app.config["OVERDUE_AFTER_DAYS"],
                           recurring_days=current_app.config["RECURRING_WINDOW_DAYS"],
                           recurring_min=current_app.config["RECURRING_MIN_COUNT"])


@bp.route("/complaints")
@admin_required
def complaints():
    filters = _filters_from_request()
    q = clean_str(request.args.get("q"), 80)
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = 15
    rows, total = repo.search_complaints(filters, q or None, page, per_page)
    pages = max((total + per_page - 1) // per_page, 1)
    qs = {k: v for k, v in {**filters, "q": q}.items() if v}      # active filters, reused in links
    return render_template("admin/complaints.html", rows=rows, total=total, page=page, pages=pages,
                           filters=filters, q=q, qs=qs, categories=CATEGORIES, urgencies=URGENCY_LEVELS,
                           locations=LOCATIONS, statuses=STATUSES, departments=repo.list_departments())


@bp.route("/complaints/<complaint_id>")
@admin_required
def complaint_detail(complaint_id):
    c = repo.get_complaint(complaint_id)
    if not c:
        abort(404)
    similar = []
    ids = [s["complaint_id"] for s in c.get("similar_complaints", [])]
    if ids:
        similar = list(repo.get_db().complaints.find(
            {"complaint_id": {"$in": ids}}, {"_id": 0, "complaint_id": 1, "title": 1, "status": 1, "location": 1}))
    return render_template("admin/complaint_detail.html", c=c, similar=similar, statuses=STATUSES,
                           urgencies=URGENCY_LEVELS, departments=repo.list_departments(),
                           suggested=CATEGORY_TO_DEPARTMENT.get(c["predicted_category"]),
                           feedback=repo.get_feedback(complaint_id))


@bp.route("/complaints/<complaint_id>/update", methods=["POST"])
@admin_required
def update_complaint(complaint_id):
    c = repo.get_complaint(complaint_id)
    if not c:
        abort(404)
    action = request.form.get("action")
    if action == "assign":
        names = {d["department_name"] for d in repo.list_departments()}
        dept = request.form.get("department", "")
        if dept in names:
            repo.assign_department(complaint_id, dept)
            flash(f"Assigned to {dept}.", "success")
        else:
            flash("Unknown department.", "danger")
    elif action == "status":
        status = request.form.get("status", "")
        if status in STATUSES:
            if status in ("In Progress", "Resolved") and not c.get("assigned_department"):
                flash("Assign a department before moving the complaint forward.", "warning")
            elif status == c["status"]:
                flash("The complaint already has this status.", "info")
            else:
                repo.update_status(complaint_id, status, current_user.user_id, clean_str(request.form.get("note"), 300))
                flash(f"Status changed to {status}.", "success")
        else:
            flash("Invalid status.", "danger")
    elif action == "urgency":
        urgency = request.form.get("urgency", "")
        if urgency in URGENCY_LEVELS:
            repo.override_urgency(complaint_id, urgency)
            flash(f"Urgency set to {urgency} (ML prediction kept for reference).", "success")
        else:
            flash("Invalid urgency.", "danger")
    else:
        flash("Unknown action.", "danger")
    return redirect(url_for("admin.complaint_detail", complaint_id=complaint_id))


def _csv_safe(value):
    """Stop spreadsheet formula injection when the CSV is opened in Excel."""
    s = "" if value is None else str(value)
    return "'" + s if s[:1] in ("=", "+", "-", "@") else s


@bp.route("/export.csv")
@admin_required
def export_csv():
    filters = _filters_from_request()
    q = clean_str(request.args.get("q"), 80)
    rows, _ = repo.search_complaints(filters, q or None, 1, 100000)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["complaint_id", "created_at", "student_id", "title", "description", "location", "category",
                "predicted_urgency", "final_urgency", "status", "assigned_department", "resolved_at"])
    for c in rows:
        w.writerow([_csv_safe(x) for x in (
            c["complaint_id"], c["created_at"], c["student_id"], c["title"], c["description"], c["location"],
            c["predicted_category"], c["predicted_urgency"], c["final_urgency"], c["status"],
            c.get("assigned_department"), c.get("resolved_at"))])
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=campuspulse_complaints.csv"})
