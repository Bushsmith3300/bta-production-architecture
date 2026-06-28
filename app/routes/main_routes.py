# app/routes/main_routes.py

from flask import Blueprint, render_template


main_bp = Blueprint(
    "main",
    __name__
)


# ---------------- HOME ----------------
@main_bp.route("/")
def index():
    return render_template("index.html")


@main_bp.route("/about")
def about():
    return render_template("aboutpage.html")


@main_bp.route("/contact")
def contact():
    return render_template("contactpage.html")


# ---------------- ERROR HANDLER ----------------
@main_bp.app_errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500