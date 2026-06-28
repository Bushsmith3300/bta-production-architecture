# app/routes/api_routes.py

from flask import Blueprint, current_app


api_bp = Blueprint(
    "api",
    __name__
)


# ---------------- DB CHECK ----------------
@api_bp.route("/db-check")
def db_check():

    return {
        "database_url": str(
            current_app.config[
                "SQLALCHEMY_DATABASE_URI"
            ]
        )
    }