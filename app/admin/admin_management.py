from flask import Blueprint, render_template, flash, redirect, url_for
from app.extensions import db
from app.models import User
from app.utils.decorators import super_admin_required

admin_management_bp = Blueprint(
    "admin_management",
    __name__, url_prefix = "/super-admin/admin-management"
)

# ------- Manage Administrators ----------------

@admin_management_bp.route("/")
@super_admin_required
def index():

    admins = User.query.filter(
        User.role.in_(["admin", "super_admin"])
    ).all()

    total_admins = User.query.filter_by(role="admin").count()

    total_super_admins = User.query.filter_by(
        role="super_admin"
    ).count()

    active_admins = User.query.filter_by(
        role="admin",
        is_active=True
    ).count()

    suspended_admins = User.query.filter_by(
        role="admin",
        is_active=False
    ).count()

    return render_template(
        "admin_template/admin_management.html",
        admins=admins,
        total_admins=total_admins,
        total_super_admins=total_super_admins,
        active_admins=active_admins,
        suspended_admins=suspended_admins
    )


# ------- Suspend Administrator ----------------

@admin_management_bp.route(
    "/admin/<int:user_id>/suspend",
    methods=["POST"]
)
@super_admin_required
def suspend_admin(user_id):

    user = User.query.get_or_404(user_id)
    name = user.first_name
    
    if user.role == "super_admin":
        flash(
            "Super admins cannot be suspended.",
            "danger"
        )
        return redirect(
            url_for("admin_management.index")
        )

    user.is_active = False

    db.session.commit()

    flash(
       f"Administrator {name} has been suspended.",
        "warning"
    )

    return redirect(
        url_for("admin_management.index")
    )


# ------- Activate Administrator ----------------

@admin_management_bp.route(
    "/admin/<int:user_id>/activate",
    methods=["POST"]
)
@super_admin_required
def activate_admin(user_id):

    user = User.query.get_or_404(user_id)
    name = user.first_name

    user.is_active = True

    db.session.commit()

    flash(
       f"Administrator {name} has been activated.",
        "success"
    )

    return redirect(
        url_for("admin_management.index")
    )


# ------- Demote Administrator ----------------

@admin_management_bp.route(
    "/admin/<int:user_id>/demote",
    methods=["POST"]
)
@super_admin_required
def demote_admin(user_id):

    user = User.query.get_or_404(user_id)
    name = user.first_name

    if user.role == "super_admin":
        flash(
            "Super admin cannot be demoted.",
            "danger"
        )
        return redirect(
            url_for("admin_management.index")
        )

    user.role = "student"

    db.session.commit()

    flash(
       f"Administrator {name} has been demoted.",
        "success"
    )

    return redirect(
        url_for("admin_management.index")
    )