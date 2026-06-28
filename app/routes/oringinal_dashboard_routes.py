from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    session,
    request,
    flash
)

from app.models.user import User
from app.models.question import Question
from app.models.announcement import Announcement
from app.models.class_status import ClassStatus
from app.models.quiz_history import QuizHistory
from app.models.user_progress import UserProgress
from app.extensions import db
from app.utils.decorators import login_required

  


# ---------------- SUBJECT SELECT ----------------
@dashboard_bp.route("/subject_select", methods=["GET", "POST"])
@login_required
def subject_select():

    user = db.session.get(User, session["user_id"])

    return render_template(
        "subject_select.html",
        user=user
    )


# ---------------- TOPIC SELECT ----------------
@dashboard_bp.route("/topic_select", methods=["GET", "POST"])
@login_required
def topic_select():

    user = db.session.get(
        User,
        session["user_id"]
    )

    if request.method == "POST":

        selected = request.form.getlist("topics")

        if not selected:

            flash(
                "Select at least one topic",
                "error"
            )

            return redirect(
                url_for("dashboard.topic_select")
            )

        return redirect(
            url_for(
                "quiz.quiz",
                topic=selected[0]
            )
        )

    return render_template(
        "topic_select.html",
        user=user
    )


# ---------------- ENTER CLASS ----------------
@dashboard_bp.route("/enter_class")
@login_required
def enter_class():

    status = ClassStatus.query.first()

    if not status or not status.is_live:

        flash(
            "Class is not live yet",
            "error"
        )

        return redirect(
            url_for("dashboard.dashboard")
        )

    return redirect(status.link)