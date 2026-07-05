from flask import Blueprint, render_template, session

from app.utils.decorators import admin_required

from app.models import (
    Question,
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
@admin_required
def dashboard():

    total_questions = Question.query.count()

    total_assignments = Assignment.query.count()

    total_assignment_questions = AssignmentQuestion.query.count()

    pending_submissions = AssignmentSubmission.query.filter_by(
      submit_status="pending"
    ).count()

    total_live_classes = LiveClass.query.count()

    total_announcements = Announcement.query.count()

    class_status = (LiveClass.query.filter_by(is_live=True).first())

    recent_activity = [
        "Created a new assignment",
        "Started a live class",
        "Published an announcement",
        "Added new assignment questions"
    ]

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

    return render_template(
        "admin/dashboard_regular_admin.html",
        data=dashboard_data
    )