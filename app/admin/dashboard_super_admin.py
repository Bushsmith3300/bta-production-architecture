
from flask import Blueprint, render_template, session
from app.models import User
from app.utils.decorators import super_admin_required


super_admin_bp = Blueprint("dashboard_super_admin", __name__, url_prefix="/super-admin")


@super_admin_bp.route("/")
@super_admin_required
def dashboard():

    users = User.query.all()

    user = User.query.get(session["user_id"])

    total_users = User.query.count()

    total_admins = User.query.filter_by(role="admin").count()

    total_active_users = User.query.filter_by(is_active=True).count()

    total_suspended_users = User.query.filter_by(is_active=False).count()

    return render_template(
        "super_admin/dashboard_super_admin.html",
        user=user,
        users=users,
        total_users=total_users,
        total_admins=total_admins,
        total_active_users=total_active_users,
        total_suspended_users=total_suspended_users
    )