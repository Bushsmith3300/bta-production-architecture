from flask import Blueprint, render_template, session

from app.utils.decorators import admin_subject_required, login_required

from app.models import (
    Question,
    Subject,
    User,
    Assignment,
    AssignmentQuestion,
    AssignmentSubmission,
    LiveClass,
    Announcement
)

regular_admin_bp = Blueprint(
    "regular_admin",
    __name__,
    url_prefix="/admin"
)


@regular_admin_bp.route("/")
@admin_subject_required
def dashboard():
    
# ======================================================
# GET ADMIN'S ASSIGNED SUBJECT
# ======================================================

subject_name = session.get("subject")

if not subject_name:
    current_app.logger.error(
        "REGULAR ADMIN ERROR: No subject found in session."
    )
    abort(403, description="No subject has been assigned to this admin.")

admin_subject = Subject.query.filter_by(
    name=subject_name
).first()

if admin_subject is None:
    current_app.logger.error(
        "REGULAR ADMIN ERROR: Subject '%s' does not exist.",
        subject_name
    )
    abort(403, description="The assigned subject could not be found.")


# ======================================================
# COUNT QUESTIONS FOR ASSIGNED SUBJECT
# ======================================================




@regular_admin_bp.route("/no-subject")
@login_required
def no_subject():

    user = User.query.get(
        session["user_id"]
    )

    if not user:
        return redirect(
            url_for("auth.login")
        )

    if user.role == "super_admin":
        return redirect(
            url_for("dashboard_super_admin.dashboard")
        )

    if user.role != "admin":
        return redirect(
            url_for("dashboard.dashboard")
        )

    return render_template(
        "admin/no_subject.html",
        user=user
    )
