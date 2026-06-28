from flask import Blueprint, render_template, redirect, url_for, flash
from app.utils.decorators import super_admin_required
from app.extensions import db
from app.models import User

users_management_bp = Blueprint(
    "users_management",
    __name__,
    url_prefix="/super-admin/users-management"
)


# ---------------- VIEW USERS ----------------
@users_management_bp.route("/")
@super_admin_required
def index():

    users = User.query.order_by(User.id.desc()).all()

    total_users = len(users)
    total_admins = User.query.filter_by(role="admin").count()
    total_active_users = User.query.filter_by(is_active=True).count()
    total_suspended_users = User.query.filter_by(is_active=False).count()

    return render_template(
        "admin_template/users_management.html",
        users=users,
        total_users=total_users,
        total_admins=total_admins,
        total_active_users=total_active_users,
        total_suspended_users=total_suspended_users
    )


# ---------------- PROMOTE TO USER TO ADMIN ----------------
@users_management_bp.route("/<int:user_id>/make-admin", methods=["POST"])
@super_admin_required
def make_admin(user_id):

    user = User.query.get_or_404(user_id)
    name = user.first_name

    # Prevent modifying super admin
    if user.role == "super_admin":
        flash("Cannot modify a super admin.", "danger")
        return redirect(url_for("users_management.index"))

    user.role = "admin"
    db.session.commit()

    flash(f"{name} has been promoted to admin.", "success")
    return redirect(url_for("users_management.index"))


# ---------------- DEMOTE AN ADMIN TO USER ----------------
@users_management_bp.route("/<int:user_id>/remove-admin", methods=["POST"])
@super_admin_required
def remove_admin(user_id):

    user = User.query.get_or_404(user_id)
    name = user.first_name

    # Prevent modifying super admin
    if user.role == "super_admin":
        flash("Cannot modify a super admin.", "danger")
        return redirect(url_for("users_management.index"))

    user.role = "student"
    db.session.commit()

    flash(f"Admin privileges removed from {name}", "warning")
    return redirect(url_for("users_management.index"))


# ---------------- SUSPEND USER ----------------
@users_management_bp.route("/<int:user_id>/suspend", methods=["POST"])
@super_admin_required
def suspend_user(user_id):

    user = User.query.get_or_404(user_id)
    name = user.first_name

    # Prevent suspending super admin
    if user.role == "super_admin":
        flash("Cannot suspend a super admin.", "danger")
        return redirect(url_for("users_management.index"))

    user.is_active = False
    db.session.commit()

    flash(f"{name} has been suspended.", "warning")
    return redirect(url_for("users_management.index"))


# ---------------- ACTIVATE USER ----------------
@users_management_bp.route("/<int:user_id>/activate", methods=["POST"])
@super_admin_required
def activate_user(user_id):

    user = User.query.get_or_404(user_id)
    name = user.first_name

    user.is_active = True
    db.session.commit()

    flash(f"{name} has been activated.", "success")
    return redirect(url_for("users_management.index"))


# ---------------- DELETE USER ----------------
@users_management_bp.route("/<int:user_id>/delete", methods=["POST"])
@super_admin_required
def delete_user(user_id):

    user = User.query.get_or_404(user_id)
    name = user.first_name

    # Prevent deleting super admin
    if user.role == "super_admin":
        flash("Cannot delete a super admin.", "danger")
        return redirect(url_for("users_management.index"))

    db.session.delete(user)
    db.session.commit()

    flash(f"{name} has been deleted successfully.", "success")
    return redirect(url_for("users_management.index"))