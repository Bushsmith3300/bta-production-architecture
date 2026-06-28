# app/routes/class_routes.py

from flask import (
    Blueprint,
    session,
    redirect,
    url_for,
    flash
)

from app.models import (
    User,
)

from app.utils.decorators import login_required


class_bp = Blueprint(
    "classroom",
    __name__
)


# ---------------- ENTER CLASS ----------------
@class_bp.route("/enter_class")
@login_required

def enter_class():

    user = User.query.get(
        session["user_id"]
    )

    if not user:
        session.clear()
        return redirect(url_for("auth.login"))

    status = LiveClass.query.first()

    if not status or not status.is_live:

        flash(
            "Class is not live yet",
            "error"
        )

        return redirect(
            url_for("dashboard.dashboard")
        )

    return redirect(status.link)