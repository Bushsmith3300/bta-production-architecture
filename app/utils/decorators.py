from functools import wraps

from flask import session, redirect, url_for, flash

from app.models import User


# ============================================================
# LOGIN REQUIRED
# ============================================================

def login_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):

        if "user_id" not in session:

            flash(
                "Please log in first.",
                "warning"
            )

            return redirect(
                url_for("auth.login")
            )

        user = User.query.get(
            session["user_id"]
        )

        if not user:

            session.clear()

            return redirect(
                url_for("auth.login")
            )

        if not user.is_active:

            session.clear()

            flash(
                "Your account has been suspended.",
                "danger"
            )

            return redirect(
                url_for("auth.login")
            )

        return f(*args, **kwargs)

    return decorated_function


# ============================================================
# SUPER ADMIN REQUIRED
# ============================================================

def super_admin_required(f):

    @login_required
    @wraps(f)
    def decorated_function(*args, **kwargs):

        user = User.query.get(
            session["user_id"]
        )

        if user.role != "super_admin":

            flash(
                "You do not have permission to access that page.",
                "danger"
            )

            return redirect(
                url_for("dashboard.dashboard")
            )

        return f(*args, **kwargs)

    return decorated_function


# ============================================================
# ADMIN REQUIRED
# ============================================================

def admin_required(f):

    @login_required
    @wraps(f)
    def decorated_function(*args, **kwargs):

        user = User.query.get(
            session["user_id"]
        )

        if user.role not in [
            "admin",
            "super_admin"
        ]:

            flash(
                "You do not have permission to access that page.",
                "danger"
            )

            return redirect(
                url_for("dashboard.dashboard")
            )

        return f(*args, **kwargs)

    return decorated_function


# ============================================================
# ADMIN SUBJECT REQUIRED
# ============================================================

def admin_subject_required(f):
    @login_required
    @wraps(f)
    def decorated_function(*args, **kwargs):

        user = User.query.get(
            session["user_id"]
        )

        # ----------------------------------------------------
        # SUPER ADMIN
        # ----------------------------------------------------
        # Super admins can manage all subjects.

        if user.role == "super_admin":

            return f(*args, **kwargs)


        # ----------------------------------------------------
        # REGULAR ADMIN
        # ----------------------------------------------------

        if user.role != "admin":

            flash(
                "You do not have permission to access that page.",
                "danger"
            )

            return redirect(
                url_for("dashboard.dashboard")
            )


        # ----------------------------------------------------
        # CHECK SUBJECT ASSIGNMENT
        # ----------------------------------------------------

        if not user.subject:

            flash(
                "Your administrator account has not been assigned a subject yet. Please contact the Super Admin.",
                "warning"
            )

            return redirect(
                url_for("regular_admin.no_subject")
            )


        # ----------------------------------------------------
        # KEEP SESSION SUBJECT UP TO DATE
        # ----------------------------------------------------
        # This is important. If the Super Admin assigns or
        # changes the admin's subject, we don't want the
        # session to keep an old subject value.

        session["subject"] = user.subject
        session["role"] = user.role


        return f(*args, **kwargs)

    return decorated_function