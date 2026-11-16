"""Serves uploaded complaint images - only to the owner of the complaint or an administrator."""
from flask import Blueprint, abort, current_app, send_from_directory
from flask_login import current_user, login_required

from database.mongodb import get_db

bp = Blueprint("files", __name__)


@bp.route("/uploads/<path:filename>")
@login_required
def uploaded_file(filename):
    c = get_db().complaints.find_one({"image_filename": filename}, {"student_id": 1})
    if not c or (current_user.role != "admin" and c["student_id"] != current_user.user_id):
        abort(404)
    return send_from_directory(current_app.config["UPLOAD_FOLDER"], filename)
