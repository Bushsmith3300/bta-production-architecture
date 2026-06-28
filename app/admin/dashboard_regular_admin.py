from flask import Blueprint, render_template
from app.utils.decorators import admin_required
from app.models import User, Question, Announcement


admin_bp = Blueprint("regular_admin",  __name__, url_prefix = "/admin")


@admin_bp.route("/")
@admin_required
def dashboard():

    total_students = User.query.filter_by(role="student").count()

    total_questions = Question.query.count()

    total_announcements = Announcement.query.count()


    dashboard_data = {
        "students": total_students,
        "questions": total_questions,
        "announcements": total_announcements
    }

    return render_template(
        "admin_template/dashboard_regular_admin.html",
         data=dashboard_data
    )