"""
CampusPulse - Smart Campus Complaint & Issue Management System
"""
import os

from flask import Flask, jsonify, render_template, request
from flask_login import LoginManager

import utils
from config import CATEGORIES, STATUSES, URGENCY_LEVELS, Config


def create_app(overrides=None, init_database=True):
    app = Flask(__name__)
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)

    if init_database:
        from database.mongodb import init_db
        from ml.predict import ensure_models
        init_db()           # connects to MongoDB, creates validated collections + indexes + seed data
        ensure_models()     # trains the ML models on first run

    from routes import admin, auth, files, student
    app.register_blueprint(auth.bp)
    app.register_blueprint(student.bp)
    app.register_blueprint(admin.bp)
    app.register_blueprint(files.bp)

    login_manager = LoginManager(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"
    login_manager.user_loader(auth.load_user)

    # ----- template helpers -----
    app.jinja_env.filters["dt"] = utils.local_time
    app.jinja_env.globals.update(
        csrf_token=utils.csrf_token, STATUS_BADGE=utils.STATUS_BADGE, URGENCY_BADGE=utils.URGENCY_BADGE,
        ALL_CATEGORIES=CATEGORIES, ALL_STATUSES=STATUSES, ALL_URGENCIES=URGENCY_LEVELS)

    @app.before_request
    def _csrf_protect():
        if request.method in ("POST", "PUT", "PATCH", "DELETE"):
            utils.verify_csrf()

    @app.after_request
    def _security_headers(resp):
        resp.headers.setdefault("X-Content-Type-Options", "nosniff")
        resp.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        resp.headers.setdefault("Referrer-Policy", "same-origin")
        return resp

    def _error(code, title, message):
        if request.path.startswith("/student/api/"):
            return jsonify({"error": message}), code
        return render_template("errors/error.html", code=code, title=title, message=message), code

    @app.errorhandler(400)
    def e400(e):
        return _error(400, "Bad request", getattr(e, "description", "The request could not be processed."))

    @app.errorhandler(403)
    def e403(e):
        return _error(403, "Access denied", "You do not have permission to open this page.")

    @app.errorhandler(404)
    def e404(e):
        return _error(404, "Not found", "The page or record you asked for does not exist.")

    @app.errorhandler(413)
    def e413(e):
        return _error(413, "File too large", "Uploaded images must be smaller than 4 MB.")

    @app.errorhandler(500)
    def e500(e):
        return _error(500, "Something went wrong", "An unexpected error occurred. Please try again.")

    return app


if __name__ == "__main__":
    application = create_app()
    port = int(os.getenv("PORT", "5000"))
    print(f"\n  CampusPulse is running ->  http://127.0.0.1:{port}\n")
    application.run(host="127.0.0.1", port=port, debug=os.getenv("FLASK_DEBUG", "0") == "1", use_reloader=False)
