from flask import (
Blueprint,
render_template,
session,
redirect,
url_for,
flash
)

from app.utils.decorators import (
admin_subject_required,
login_required
)

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
name,
url_prefix="/admin"
)

#======================================================

# REGULAR ADMIN DASHBOARD

#======================================================
@regular_admin_bp.route("/")
@admin_subject_required
def dashboard():

# ==================================================
# GET CURRENT USER
# ==================================================

    user = User.query.get(session["user_id"])

    if not user:
        session.clear()

        return redirect(
            url_for("auth.login")
        )

# ==================================================
# GET ADMIN'S ASSIGNED SUBJECT
# ==================================================

    admin_subject = None

    if user.role == "super_admin":

    # Super Admin can access all subjects.
    # No subject assignment is required.

        total_questions = Question.query.count()

    elif user.role == "admin":

    # Regular Admin must have an assigned subject.

        subject_name = user.subject

    if not subject_name:

            flash(
            "Your administrator account has not been assigned a subject yet. Please contact the Super Admin.",
            "warning"
            )

            return redirect(
                url_for("regular_admin.no_subject")
            )

         admin_subject = Subject.query.filter_by(
            name=subject_name).first()

        if admin_subject is None:

            flash(
            "Your assigned subject could not be found.",
            "danger"
            )

            return redirect(
                 url_for("regular_admin.no_subject")
            )

    # Keep the session subject updated.

        session["subject"] = user.subject
        session["role"] = user.role

    # Count questions for the assigned subject.

        total_questions = Question.query.filter(
            Question.subject_id == admin_subject.id
        ).count()

    else:

        flash(
        "You do not have permission to access this page.",
        "danger"
        )

        return redirect(
            url_for("dashboard.dashboard")
        )

# ==================================================
# COUNT ASSIGNMENTS
# ==================================================

    total_assignments = Assignment.query.count()

    total_assignment_questions = (
        AssignmentQuestion.query.count()
    )

# ==================================================
# COUNT PENDING SUBMISSIONS
# ==================================================

    pending_submissions = (
        AssignmentSubmission.query.filter_by(
            submit_status="pending"
        ).count()
    )

# ==================================================
# COUNT LIVE CLASSES
# ==================================================

    total_live_classes = LiveClass.query.count()

# ==================================================
# COUNT ANNOUNCEMENTS
# ==================================================

    total_announcements = Announcement.query.count()

# ==================================================
# GET CURRENT LIVE CLASS STATUS
# ==================================================

    class_status = LiveClass.query.filter_by(
        is_live=True
    ).first()

# ==================================================
# RECENT ACTIVITY
# ==================================================

    recent_activity = [
        "Created a new assignment",
        "Started a live class",
        "Published an announcement",
        "Added new assignment questions"
    ]

# ==================================================
# DASHBOARD DATA
# ==================================================

    dashboard_data = {
        "questions": total_questions,
        "assignments": total_assignments,
        "assignment_questions": total_assignment_questions,
        "pending_submissions": pending_submissions,
        "live_classes": total_live_classes,
        "announcements": total_announcements,
        "class_status": class_status,
        "recent_activity": recent_activity
    }

# ==================================================
# RENDER DASHBOARD
# ==================================================

    return render_template(
        "admin/dashboard_regular_admin.html",
        data=dashboard_data
    )

#======================================================

# ADMIN WITHOUT AN ASSIGNED SUBJECT

#======================================================

@regular_admin_bp.route("/no-subject")
@login_required
def no_subject():

    user = User.query.get(
        session["user_id"]
    )

    if not user:

        session.clear()

        return redirect(
            url_for("auth.login")
        )

# --------------------------------------------------
# SUPER ADMIN
# --------------------------------------------------

    if user.role == "super_admin":

        return redirect(
            url_for("dashboard_super_admin.dashboard")
        )

# --------------------------------------------------
# REGULAR ADMIN
# --------------------------------------------------

    if user.role != "admin":

        return redirect(
            url_for("dashboard.dashboard")
        )

# --------------------------------------------------
# DISPLAY NO-SUBJECT PAGE
# --------------------------------------------------

    return render_template(
        "admin/no_subject.html",
        user=user
    )
