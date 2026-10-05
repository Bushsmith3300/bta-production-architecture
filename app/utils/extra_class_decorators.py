from functools import wraps

from flask import (
    session,
    redirect,
    url_for,
    flash
)

from app.models import (
    ExtraClassTeacher,
    ExtraClassTeacherAccount
)


def extra_class_teacher_required(view_function):
    """
    Protect routes that are accessible only to
    authenticated Extra Class teachers.
    """

    @wraps(view_function)
    def decorated_function(*args, **kwargs):

        # =================================================
        # CHECK TEACHER SESSION
        # =================================================

        teacher_id = session.get(
            "extra_class_teacher_id"
        )

        account_id = session.get(
            "extra_class_teacher_account_id"
        )

        if not teacher_id or not account_id:

            flash(
                "Please log in to access the teacher portal.",
                "danger"
            )

            return redirect(
                url_for(
                    "extra_class_auth.teacher_login"
                )
            )

        # =================================================
        # FIND TEACHER ACCOUNT
        # =================================================

        account = (
            ExtraClassTeacherAccount.query
            .filter_by(
                id=account_id,
                teacher_id=teacher_id
            )
            .first()
        )

        if not account:

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
                "Your teacher account could not be found. "
                "Please log in again.",
                "danger"
            )

            return redirect(
                url_for(
                    "extra_class_auth.teacher_login"
                )
            )

        # =================================================
        # CHECK ACCOUNT STATUS
        # =================================================

        if not account.is_active:

            session.clear()

            flash(
                "Your teacher account is inactive. "
                "Please contact the administrator.",
                "danger"
            )

            return redirect(
                url_for(
                    "extra_class_auth.teacher_login"
                )
            )

        # =================================================
        # FIND TEACHER PROFILE
        # =================================================

        teacher = (
            ExtraClassTeacher.query
            .filter_by(id=teacher_id)
            .first()
        )

        if not teacher:

            session.clear()

            flash(
                "Your teacher profile could not be found.",
                "danger"
            )

            return redirect(
                url_for(
                    "extra_class_auth.teacher_login"
                )
            )

        # =================================================
        # CHECK TEACHER STATUS
        # =================================================

        if not teacher.is_active:

            session.clear()

            flash(
                "Your teacher profile is inactive. "
                "Please contact the administrator.",
                "danger"
            )

            return redirect(
                url_for(
                    "extra_class_auth.teacher_login"
                )
            )

        # =================================================
        # ATTACH TEACHER TO REQUEST
        # =================================================

        session["extra_class_teacher_name"] = (
            f"{teacher.first_name} {teacher.surname}"
        )

        session["extra_class_teacher_code"] = (
            teacher.teacher_code
        )

        return view_function(*args, **kwargs)

    return decorated_function