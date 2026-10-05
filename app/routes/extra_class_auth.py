from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session,
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash,
)

from app.extensions import db

from app.models import (
    ExtraClassTeacher,
    ExtraClassTeacherAccount,
    ExtraClassSubject,
    Subject,
)

import secrets
from datetime import datetime, timezone


# ============================================================
# BLUEPRINT
# ============================================================

extra_class_auth_bp = Blueprint(
    "extra_class_auth",
    __name__,
    url_prefix="/extra-classes"
)


# ============================================================
# TEACHER CODE GENERATOR
# ============================================================

def _generate_teacher_code():
    """
    Generate a unique teacher code.

    Example:
        TCH-A1B2C3
    """

    while True:

        code = f"TCH-{secrets.token_hex(3).upper()}"

        existing = (
            ExtraClassTeacher.query
            .filter_by(teacher_code=code)
            .first()
        )

        if not existing:
            return code


# ============================================================
# TEACHER REGISTRATION
# ============================================================

@extra_class_auth_bp.route(
    "/teacher/register",
    methods=["GET", "POST"]
)
def teacher_register():

    # --------------------------------------------------------
    # Load active BTA subjects
    # --------------------------------------------------------

    subjects = (
        Subject.query
        .filter_by(is_active=True)
        .order_by(
            Subject.display_order.asc(),
            Subject.name.asc()
        )
        .all()
    )

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    if request.method == "POST":

        # ----------------------------------------------------
        # Get submitted values
        # ----------------------------------------------------

        first_name = request.form.get(
            "first_name",
            ""
        ).strip()

        surname = request.form.get(
            "surname",
            ""
        ).strip()

        phone = request.form.get(
            "phone",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        subject_id = request.form.get(
            "subject_id",
            type=int
        )

        # ----------------------------------------------------
        # FIRST NAME
        # ----------------------------------------------------

        if not first_name:

            flash(
                "Please enter your first name.",
                "danger"
            )

            return render_template(
                "extra_class_teacher_register.html",
                subjects=subjects
            )

        # ----------------------------------------------------
        # SURNAME
        # ----------------------------------------------------

        if not surname:

            flash(
                "Please enter your surname.",
                "danger"
            )

            return render_template(
                "extra_class_teacher_register.html",
                subjects=subjects
            )

        # ----------------------------------------------------
        # PHONE
        # ----------------------------------------------------

        if not phone:

            flash(
                "Please enter your phone number.",
                "danger"
            )

            return render_template(
                "extra_class_teacher_register.html",
                subjects=subjects
            )

        # ----------------------------------------------------
        # USERNAME
        # ----------------------------------------------------

        if not username:

            flash(
                "Please choose a username.",
                "danger"
            )

            return render_template(
                "extra_class_teacher_register.html",
                subjects=subjects
            )

        if len(username) < 3:

            flash(
                "Username must contain at least 3 characters.",
                "danger"
            )

            return render_template(
                "extra_class_teacher_register.html",
                subjects=subjects
            )

        if " " in username:

            flash(
                "Username must not contain spaces.",
                "danger"
            )

            return render_template(
                "extra_class_teacher_register.html",
                subjects=subjects
            )

        if "-" in username:

            flash(
                "Username must not contain hyphens.",
                "danger"
            )

            return render_template(
                "extra_class_teacher_register.html",
                subjects=subjects
            )

        if "@" in username:

            flash(
                "Username must not contain the @ symbol.",
                "danger"
            )

            return render_template(
                "extra_class_teacher_register.html",
                subjects=subjects
            )

        # ----------------------------------------------------
        # PASSWORD
        # ----------------------------------------------------

        if len(password) < 8:

            flash(
                "Password must contain at least 8 characters.",
                "danger"
            )

            return render_template(
                "extra_class_teacher_register.html",
                subjects=subjects
            )

        if password != confirm_password:

            flash(
                "Passwords do not match.",
                "danger"
            )

            return render_template(
                "extra_class_teacher_register.html",
                subjects=subjects
            )

        # ----------------------------------------------------
        # SUBJECT
        # ----------------------------------------------------

        if not subject_id:

            flash(
                "Please select the subject you teach.",
                "danger"
            )

            return render_template(
                "extra_class_teacher_register.html",
                subjects=subjects
            )

        selected_subject = (
            Subject.query
            .filter_by(
                id=subject_id,
                is_active=True
            )
            .first()
        )

        if not selected_subject:

            flash(
                "Please select a valid active subject.",
                "danger"
            )

            return render_template(
                "extra_class_teacher_register.html",
                subjects=subjects
            )

        # ----------------------------------------------------
        # USERNAME UNIQUENESS
        # ----------------------------------------------------

        existing_account = (
            ExtraClassTeacherAccount.query
            .filter_by(username=username)
            .first()
        )

        if existing_account:

            flash(
                "That username is already in use. "
                "Please choose another username.",
                "danger"
            )

            return render_template(
                "extra_class_teacher_register.html",
                subjects=subjects
            )

        # ----------------------------------------------------
        # CREATE RECORDS
        # ----------------------------------------------------

        try:

            # ------------------------------------------------
            # Generate teacher code
            # ------------------------------------------------

            teacher_code = _generate_teacher_code()

            # ------------------------------------------------
            # Create teacher
            # ------------------------------------------------

            teacher = ExtraClassTeacher(
                teacher_code=teacher_code,
                first_name=first_name,
                surname=surname,
                phone=phone,
                email=email or None,
                is_active=True,
            )

            db.session.add(teacher)

            # Get generated teacher ID
            db.session.flush()

            # ------------------------------------------------
            # Create teacher account
            # ------------------------------------------------

            account = ExtraClassTeacherAccount(
                teacher_id=teacher.id,
                username=username,

                # IMPORTANT:
                # The model field is "password", not
                # "password_hash".
                password=generate_password_hash(password),

                is_active=True,
            )

            db.session.add(account)

            # ------------------------------------------------
            # Create Extra Class subject
            # ------------------------------------------------
            #
            # One teacher = one ExtraClassSubject.
            #
            # Multiple teachers can select the same BTA
            # subject.
            #
            # Monthly fee starts at 0.00 and can later be
            # configured by the teacher.
            # ------------------------------------------------

            extra_class_subject = ExtraClassSubject(
                subject_id=selected_subject.id,
                teacher_id=teacher.id,
                monthly_fee=0,
                is_active=True,
            )

            db.session.add(extra_class_subject)

            # ------------------------------------------------
            # Save everything
            # ------------------------------------------------

            db.session.commit()

            # ------------------------------------------------
            # Success message
            # ------------------------------------------------

            flash(
                f"Registration successful! "
                f"Your Teacher Code is {teacher_code}. "
                f"Please keep it safe.",
                "success"
            )

            return redirect(
                url_for(
                    "extra_class_auth.teacher_login"
                )
            )

        except Exception:
            db.session.rollback()

            flash(
                "Registration could not be completed. "
                "Please try again.",
                "danger"
            )

    # ========================================================
    # GET
    # ========================================================

    return render_template(
        "extra_class_teacher_register.html",
        subjects=subjects
    )


# ============================================================
# TEACHER LOGIN
# ============================================================

@extra_class_auth_bp.route(
    "/teacher/login",
    methods=["GET", "POST"]
)
def teacher_login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        # ----------------------------------------------------
        # Find account
        # ----------------------------------------------------

        account = (
            ExtraClassTeacherAccount.query
            .filter_by(username=username)
            .first()
        )

        if not account:

            flash(
                "Invalid username or password.",
                "danger"
            )

            return render_template(
                "extra_class_teacher_login.html"
            )

        # ----------------------------------------------------
        # Account status
        # ----------------------------------------------------

        if not account.is_active:

            flash(
                "Your teacher account is inactive. "
                "Please contact the administrator.",
                "danger"
            )

            return render_template(
                "extra_class_teacher_login.html"
            )

        # ----------------------------------------------------
        # Verify password
        # ----------------------------------------------------

        # IMPORTANT:
        # The model field is "password", not
        # "password_hash".
        if not check_password_hash(
            account.password,
            password
        ):

            flash(
                "Invalid username or password.",
                "danger"
            )

            return render_template(
                "extra_class_teacher_login.html"
            )

        # ----------------------------------------------------
        # Find teacher
        # ----------------------------------------------------

        teacher = (
            ExtraClassTeacher.query
            .filter_by(id=account.teacher_id)
            .first()
        )

        if not teacher:

            flash(
                "Your teacher profile could not be found.",
                "danger"
            )

            return render_template(
                "extra_class_teacher_login.html"
            )

        # ----------------------------------------------------
        # Teacher status
        # ----------------------------------------------------

        if not teacher.is_active:

            flash(
                "Your teacher profile is inactive. "
                "Please contact the administrator.",
                "danger"
            )

            return render_template(
                "extra_class_teacher_login.html"
            )

        # ----------------------------------------------------
        # Create teacher session
        # ----------------------------------------------------

        session.clear()

        session["extra_class_teacher_id"] = teacher.id

        session["extra_class_teacher_account_id"] = (
            account.id
        )

        session["extra_class_teacher_name"] = (
            f"{teacher.first_name} {teacher.surname}"
        )

        session["extra_class_teacher_code"] = (
            teacher.teacher_code
        )

        # ----------------------------------------------------
        # Update last login
        # ----------------------------------------------------

        # IMPORTANT:
        # The model field is "last_login_at", not
        # "last_login".
        account.last_login_at = datetime.now(timezone.utc)

        db.session.commit()

        # ----------------------------------------------------
        # Redirect to teacher dashboard
        # ----------------------------------------------------

        return redirect(
            url_for(
                "extra_class_teacher.teacher_dashboard"
            )
        )

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    return render_template(
        "extra_class_teacher_login.html"
    )


# ============================================================
# TEACHER LOGOUT
# ============================================================

@extra_class_auth_bp.route("/teacher/logout")
def teacher_logout():

    session.pop(
        "extra_class_teacher_id",
        None
    )

    session.pop(
        "extra_class_teacher_account_id",
        None
    )

    session.pop(
        "extra_class_teacher_name",
        None
    )

    session.pop(
        "extra_class_teacher_code",
        None
    )

    flash(
        "You have been logged out successfully.",
        "success"
    )

    return redirect(
        url_for(
            "extra_class_auth.teacher_login"
        )
    )