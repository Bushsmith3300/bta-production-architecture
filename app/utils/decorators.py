# app/utils/decorators.py

from functools import wraps

from flask import session, redirect, url_for, flash
from app.models import User


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


def admin_required(f):
    @login_required
    @wraps(f)
    def decorated_function(*args, **kwargs):

        user = User.query.get(
            session["user_id"]
        )

        if user.role not in ["admin", "super_admin"]:

            flash(
                "You do not have permission to access that page.",
                "danger"
            )

            return redirect(
                url_for("dashboard.dashboard")
            )

        return f(*args, **kwargs)

    return decorated_function