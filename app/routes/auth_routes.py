
# app/routes/auth_routes.py
import time
import re

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from app.extensions import db

from app.models import (
    User,
    UserProgress
)


from sqlalchemy import text

from werkzeug.security import check_password_hash
import time


auth_bp = Blueprint(
    "auth",
    __name__
)


@auth_bp.route("/raw-test")
def raw_test():

    start = time.time()
    print("Starting raw SQL")

    result = db.session.execute(
        text("SELECT 1")
    )

    print("Raw SQL finished:", time.time() - start)

    return "OK"

@auth_bp.route("/user-test")
def user_test():

    start = time.time()
    print("Starting user query")

    user = User.query.first()

    print("User query finished:", time.time() - start)

    return "OK"

# ---------------- REGISTER ----------------
@auth_bp.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        first_name = request.form.get(
            "first_name",
            ""
        ).strip()

        surname = request.form.get(
            "surname",
            ""
        ).strip()

        other_name = request.form.get(
            "other_name",
            ""
        ).strip()

        # VALIDATION
        if not username or len(username) < 3:
            flash(
                "Username must be at least 3 characters",
                "error"
            )
            return redirect(url_for("auth.register"))

        if not re.match(r"^[a-z0-9_]+$", username):
            flash(
                "Username can only contain letters, numbers, and underscore",
                "error"
            )
            return redirect(url_for("auth.register"))

        if len(password) < 6:
            flash(
                "Password must be at least 6 characters",
                "error"
            )
            return redirect(url_for("auth.register"))

        if password != confirm_password:
            flash(
                "Passwords do not match",
                "error"
            )
            return redirect(url_for("auth.register"))

        existing_user = User.query.filter_by(
            username=username
        ).first()

        if existing_user:
            flash(
                "You already have an account",
                "error"
            )
            return redirect(url_for("auth.login"))

        new_user = User(
            username=username,
            password=generate_password_hash(password),
            first_name=first_name,
            surname=surname,
            other_name=other_name
        )

        db.session.add(new_user)
        db.session.flush()

        progress = UserProgress(
            user_id=new_user.id
        )

        db.session.add(progress)
        db.session.commit()

        flash(
            "Registration successful",
            "success"
        )

        return redirect(url_for("auth.login"))

    return render_template("register.html")


# ---------------- LOGIN ----------------
@auth_bp.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip().lower()

        password = request.form.get(
            "password",
            ""
        )


        user = User.query.filter_by(
            username=username
        ).first()


        if not user:
            print("No user found")

        if not user or not check_password_hash(
            user.password,
            password
        ):

            flash(
                "Invalid username or password",
                "error"
            )
            return redirect(url_for("auth.login"))

       

        if not user.is_active:
            flash(
                "Your account has been suspended. Contact an Administrator",
                "error"
            )
            return redirect(url_for("auth.login"))

        session.clear()


        session["user_id"] = user.id
        session["username"] = user.username

        session.permanent = True

        return redirect(
            url_for("dashboard.dashboard")
        )

    return render_template("login.html")


# ---------------- LOGOUT ----------------
@auth_bp.route("/logout", methods=["GET"])
def logout():

    session.clear()

    flash(
        "You have been logged out",
        "success"
    )

    return redirect(url_for("auth.login"))
