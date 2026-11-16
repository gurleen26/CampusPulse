"""Student module: dashboard, submit complaint, live analysis, track status, feedback."""
import os
import uuid
from collections import Counter

from flask import (Blueprint, abort, current_app, flash, jsonify, redirect, render_template,
                   request, url_for)
from flask_login import current_user
from pymongo.errors import WriteError

from config import LOCATIONS
from database import repository as repo
from ml.predict import get_similarity_vectorizer, predict
from ml.preprocess import combine_title_description
from ml.similarity import find_similar
from utils import clean_str, student_required

bp = Blueprint("student", __name__, url_prefix="/student")

MAGIC = {  # file signatures used to confirm an upload really is an image
    "png": [b"\x89PNG\r\n\x1a\n"], "jpg": [b"\xff\xd8\xff"], "jpeg": [b"\xff\xd8\xff"],
    "gif": [b"GIF87a", b"GIF89a"], "webp": [b"RIFF"],
}


def analyze(title, description, location):
    """Run the ML module: predict category + urgency and look for similar complaints."""
    text = combine_title_description(title, description)
    prediction = predict(text)
    similar = find_similar(text, repo.candidates_for_similarity(), get_similarity_vectorizer(),
                           location=location, threshold=current_app.config["SIMILARITY_THRESHOLD"])
    return prediction, similar


def _save_image(file_storage):
    """Validate (extension + file signature) and store an uploaded image. Returns filename or None."""
    if not file_storage or not file_storage.filename:
        return None, None
    ext = file_storage.filename.rsplit(".", 1)[-1].lower() if "." in file_storage.filename else ""
    if ext not in current_app.config["ALLOWED_IMAGE_EXTENSIONS"]:
        return None, "Only PNG, JPG, GIF or WEBP images are allowed."
    head = file_storage.stream.read(12)
    file_storage.stream.seek(0)
    if not any(head.startswith(sig) for sig in MAGIC[ext]):
        return None, "The uploaded file is not a valid image."
    name = f"{uuid.uuid4().hex}.{ext}"
    os.makedirs(current_app.config["UPLOAD_FOLDER"], exist_ok=True)
    file_storage.save(os.path.join(current_app.config["UPLOAD_FOLDER"], name))
    return name, None


@bp.route("/")
@student_required
def dashboard():
    complaints = repo.complaints_of_student(current_user.user_id)
    counts = Counter(c["status"] for c in complaints)
    return render_template("student/dashboard.html", complaints=complaints, counts=counts)


@bp.route("/api/analyze", methods=["POST"])
@student_required
def api_analyze():
    """Called by JavaScript while the student types - shows the prediction before submitting."""
    data = request.get_json(silent=True) or {}
    title = clean_str(data.get("title"), 120)
    description = clean_str(data.get("description"), 2000)
    location = data.get("location") if data.get("location") in LOCATIONS else None
    if len(title) + len(description) < 10:
        return jsonify({"ready": False})
    prediction, similar = analyze(title, description, location)
    return jsonify({
        "ready": True, "prediction": prediction,
        "similar": [{"complaint_id": s["complaint_id"], "title": s["title"], "status": s["status"],
                     "score": s["score"]} for s in similar],
    })


@bp.route("/complaint/new", methods=["GET", "POST"])
@student_required
def new_complaint():
    if request.method == "POST":
        title = clean_str(request.form.get("title"), 120)
        description = clean_str(request.form.get("description"), 2000)
        location = request.form.get("location", "")
        errors = []
        if len(title) < 5:
            errors.append("Title must be at least 5 characters.")
        if len(description) < 10:
            errors.append("Please describe the problem in at least 10 characters.")
        if location not in LOCATIONS:
            errors.append("Please choose a campus location.")
        image_name = None
        if not errors:
            image_name, img_err = _save_image(request.files.get("image"))
            if img_err:
                errors.append(img_err)
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("student/new_complaint.html", locations=LOCATIONS, form=request.form), 400

        prediction, similar = analyze(title, description, location)
        student = {"user_id": current_user.user_id, "name": current_user.name}
        try:
            doc = repo.create_complaint(student, title, description, location, prediction, similar, image_name)
        except WriteError:
            flash("The database rejected this complaint (validation failed). Please check the fields.", "danger")
            return render_template("student/new_complaint.html", locations=LOCATIONS, form=request.form), 400
        flash(f"Complaint {doc['complaint_id']} submitted. Predicted category: "
              f"{prediction['category']}, urgency: {prediction['urgency']}.", "success")
        return redirect(url_for("student.complaint_detail", complaint_id=doc["complaint_id"]))
    return render_template("student/new_complaint.html", locations=LOCATIONS, form={})


def _own_complaint_or_404(complaint_id):
    c = repo.get_complaint(complaint_id)
    if not c or c["student_id"] != current_user.user_id:
        abort(404)          # students can never see other students' complaints
    return c


@bp.route("/complaint/<complaint_id>")
@student_required
def complaint_detail(complaint_id):
    c = _own_complaint_or_404(complaint_id)
    similar_ids = [s["complaint_id"] for s in c.get("similar_complaints", [])]
    similar = []
    if similar_ids:
        similar = list(repo.get_db().complaints.find(
            {"complaint_id": {"$in": similar_ids}}, {"_id": 0, "complaint_id": 1, "title": 1, "status": 1, "location": 1}))
    return render_template("student/complaint_detail.html", c=c, similar=similar,
                           feedback=repo.get_feedback(complaint_id))


@bp.route("/complaint/<complaint_id>/feedback", methods=["POST"])
@student_required
def submit_feedback(complaint_id):
    c = _own_complaint_or_404(complaint_id)
    if c["status"] != "Resolved":
        flash("Feedback can only be given after the complaint is resolved.", "warning")
        return redirect(url_for("student.complaint_detail", complaint_id=complaint_id))
    try:
        rating = int(request.form.get("rating", ""))
    except ValueError:
        rating = 0
    if rating not in range(1, 6):
        flash("Please choose a rating from 1 to 5.", "danger")
    elif repo.add_feedback(complaint_id, current_user.user_id, rating, clean_str(request.form.get("feedback"), 500)):
        flash("Thank you for your feedback!", "success")
    else:
        flash("You have already submitted feedback for this complaint.", "info")
    return redirect(url_for("student.complaint_detail", complaint_id=complaint_id))
