from flask import (
    Blueprint,
    render_template,
    flash,
    redirect,
    url_for,
    request
)

from app.extensions import db

from app.models import User, Question

from app.utils.decorators import super_admin_required


# ============================================================
# BLUEPRINT
# ============================================================

admin_management_bp = Blueprint(
    "admin_management",
    __name__,
    url_prefix="/super-admin/admin-management"
)


# ============================================================
# MANAGE ADMINISTRATORS
# ============================================================

@admin_management_bp.route("/")
@super_admin_required
def index():

    admins = User.query.filter(
        User.role.in_(["admin", "super_admin"])
    ).all()

    total_admins = User.query.filter_by(
        role="admin"
    ).count()

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
        "super_admin/admin_management.html",
        admins=admins,
        total_admins=total_admins,
        total_super_admins=total_super_admins,
        active_admins=active_admins,
        suspended_admins=suspended_admins
    )


# ============================================================
# ASSIGN SUBJECT
# ============================================================

@admin_management_bp.route(
    "/admin/<int:user_id>/assign-subject",
    methods=["GET", "POST"]
)
@super_admin_required
def assign_subject(user_id):

    user = User.query.get_or_404(user_id)

    # Super Admins have access to all subjects.
    if user.role == "super_admin":
        flash(
            "Super admins have access to all subjects and do not need a subject assignment.",
            "warning"
        )

        return redirect(
            url_for("admin_management.index")
        )

    # Only regular administrators can be assigned subjects.
    if user.role != "admin":
        flash(
            "Only administrators can be assigned subjects.",
            "danger"
        )

        return redirect(
            url_for("admin_management.index")
        )

    # Get all subjects currently available in the question bank.
    subjects = (
        db.session.query(Question.subject)
        .filter(
            Question.subject.isnot(None),
            Question.subject != ""
        )
        .distinct()
        .order_by(Question.subject)
        .all()
    )

    subjects = [
        subject[0]
        for subject in subjects
    ]

    # --------------------------------------------------------
    # SAVE SUBJECT
    # --------------------------------------------------------

    if request.method == "POST":

        selected_subject = request.form.get(
            "subject",
            ""
        ).strip()

        if not selected_subject:

            flash(
                "Please select a subject.",
                "danger"
            )

            return render_template(
                "super_admin/assign_subject.html",
                admin=user,
                subjects=subjects
            )

        # Make sure the selected subject actually exists
        # in the question bank.
        if selected_subject not in subjects:

            flash(
                "Invalid subject selected.",
                "danger"
            )

            return render_template(
                "super_admin/assign_subject.html",
                admin=user,
                subjects=subjects
            )

        # Save the subject assignment.
        user.subject = selected_subject

        db.session.commit()

        flash(
            f"{user.first_name} has been assigned to {selected_subject}.",
            "success"
        )

        return redirect(
            url_for("admin_management.index")
        )

    # --------------------------------------------------------
    # DISPLAY ASSIGN SUBJECT PAGE
    # --------------------------------------------------------

    return render_template(
        "super_admin/assign_subject.html",
        admin=user,
        subjects=subjects
    )


# ============================================================
# SUSPEND ADMINISTRATOR
# ============================================================

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


# ============================================================
# ACTIVATE ADMINISTRATOR
# ============================================================

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


# ============================================================
# DEMOTE ADMINISTRATOR
# ============================================================

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

    # Remove the subject assignment when the user
    # is no longer an administrator.
    user.subject = None

    db.session.commit()

    flash(
        f"Administrator {name} has been demoted.",
        "success"
    )

    return redirect(
        url_for("admin_management.index")
    )



# ============================================================
# REMOVE SUBJECT
# ============================================================

@admin_management_bp.route("/admin/<int:user_id>/remove-subject", methods=["POST"])
@super_admin_required
def remove_subject(user_id):

    user = User.query.get_or_404(user_id)

    # Super Admins do not have subject assignments.
    if user.role == "super_admin":

        flash(
            "Super admins have access to all subjects and cannot have a subject removed.",
            "warning"
        )

        return redirect(
            url_for("admin_management.index")
        )

    # Only regular administrators can have subjects removed.
    if user.role != "admin":

        flash(
            "Only administrators can have a subject removed.",
            "danger"
        )

        return redirect(
            url_for("admin_management.index")
        )

    # Make sure there is actually a subject to remove.
    if not user.subject:

        flash(
            f"{user.first_name} does not currently have a subject assigned.",
            "warning"
        )

        return redirect(
            url_for("admin_management.index")
        )

    removed_subject = user.subject

    # Remove the subject assignment.
    user.subject = None

    db.session.commit()

    flash(
        f"{removed_subject} has been removed from {user.first_name}'s account.",
        "success"
    )

    return redirect(
        url_for("admin_management.index")
    )