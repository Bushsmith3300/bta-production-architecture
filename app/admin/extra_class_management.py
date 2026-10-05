from datetime import date, datetime, timezone
import traceback
import calendar

from flask import Blueprint, render_template, flash, redirect, url_for, request

from app.extensions import db
from app.utils.decorators import admin_required, super_admin_required

from dateutil.relativedelta import relativedelta

from app.models import (
    Subject,
    ExtraClassParent,
    ExtraClassStudent,
    ExtraClassStudentParent,
    ExtraClassTeacher,
    ExtraClassSubject,
    ExtraClassEnrollment,
    ExtraClassMonthlyFee,
    ExtraClassPayment,
    ExtraClassPaymentItem,
    ExtraClassTeacherSettlement,
    ExtraClassTerm,
)


# ============================================================
# BLUEPRINT
# ============================================================

extra_class_bp = Blueprint(
    "extra_class",
    __name__,
    url_prefix="/admin/extra-classes"
)


# ============================================================
# EXTRA CLASSES SUPER ADMIN DASHBOARD
# ============================================================

@extra_class_bp.route("/super-admin/")
@super_admin_required
def super_admin_dashboard():

    try:

        # ----------------------------------------------------
        # CURRENT BILLING MONTH
        # ----------------------------------------------------

        today = date.today()

        current_month = today.replace(day=1)


        # ----------------------------------------------------
        # NEXT MONTH
        # ----------------------------------------------------

        if current_month.month == 12:

            next_month = current_month.replace(
                year=current_month.year + 1,
                month=1
            )

        else:

            next_month = current_month.replace(
                month=current_month.month + 1
            )


        # ----------------------------------------------------
        # BASIC COUNTS
        # ----------------------------------------------------

        total_students = (
            ExtraClassStudent.query
            .filter_by(is_active=True)
            .count()
        )


        total_parents = (
            ExtraClassParent.query
            .filter_by(is_active=True)
            .count()
        )


        total_teachers = (
            ExtraClassTeacher.query
            .filter_by(is_active=True)
            .count()
        )


        total_subjects = (
            ExtraClassSubject.query
            .filter_by(is_active=True)
            .count()
        )


        # ----------------------------------------------------
        # ACTIVE ENROLLMENTS
        # ----------------------------------------------------

        active_enrollments = (
            ExtraClassEnrollment.query
            .filter(
                ExtraClassEnrollment.status == "ACTIVE"
            )
            .count()
        )


        # ----------------------------------------------------
        # CURRENT MONTH FEES
        # ----------------------------------------------------

        current_fees = (
            ExtraClassMonthlyFee.query
            .filter(
                ExtraClassMonthlyFee.billing_month == current_month
            )
            .all()
        )


        current_month_fee_count = len(current_fees)


        current_month_fees = sum(
            float(fee.amount_due or 0)
            for fee in current_fees
        )


        # ----------------------------------------------------
        # FEE STATUS COUNTS
        # ----------------------------------------------------

        paid_fee_count = sum(
            1
            for fee in current_fees
            if str(fee.status).upper() == "PAID"
        )


        partial_fee_count = sum(
            1
            for fee in current_fees
            if str(fee.status).upper() == "PARTIAL"
        )


        unpaid_fee_count = sum(
            1
            for fee in current_fees
            if str(fee.status).upper() == "UNPAID"
        )


        overdue_fee_count = sum(
            1
            for fee in current_fees
            if str(fee.status).upper() == "OVERDUE"
        )


        # ----------------------------------------------------
        # SUCCESSFUL PAYMENTS
        # ----------------------------------------------------

        month_start_datetime = datetime(
        current_month.year,
        current_month.month,
        current_month.day,
        0,
        0,
        0,
        tzinfo=timezone.utc
        )

        next_month_datetime = datetime(
            next_month.year,
            next_month.month,
            next_month.day,
            0,
            0,
            0,
            tzinfo=timezone.utc
        )


        successful_payments = (
            ExtraClassPayment.query
            .filter(
                ExtraClassPayment.status == "SUCCESS",
                ExtraClassPayment.paid_at >= month_start_datetime,
                ExtraClassPayment.paid_at < next_month_datetime
            )
            .all()
        )


        payments_received = sum(
            float(payment.amount or 0)
            for payment in successful_payments
        )


        successful_payment_count = len(
            successful_payments
        )


        # ----------------------------------------------------
        # PENDING PAYMENTS
        # ----------------------------------------------------

        pending_payments = (
            ExtraClassPayment.query
            .filter(
                ExtraClassPayment.status == "PENDING"
            )
            .count()
        )


        # ----------------------------------------------------
        # FAILED PAYMENTS
        # ----------------------------------------------------

        failed_payment_count = (
            ExtraClassPayment.query
            .filter(
                ExtraClassPayment.status == "FAILED"
            )
            .count()
        )


        # ----------------------------------------------------
        # OUTSTANDING FEES
        # ----------------------------------------------------

        total_outstanding = 0


        for fee in current_fees:

            fee_amount = float(
                fee.amount_due or 0
            )


            paid_amount = 0


            payment_items = (
                ExtraClassPaymentItem.query
                .join(
                    ExtraClassPayment,
                    ExtraClassPayment.id ==
                    ExtraClassPaymentItem.payment_id
                )
                .filter(
                    ExtraClassPaymentItem.monthly_fee_id ==
                    fee.id,

                    ExtraClassPayment.status ==
                    "SUCCESS"
                )
                .all()
            )


            for item in payment_items:

                paid_amount += float(
                    item.amount or 0
                )


            balance = max(
                fee_amount - paid_amount,
                0
            )


            total_outstanding += balance


        # ----------------------------------------------------
        # TEACHER SETTLEMENTS
        # ----------------------------------------------------

        settlements = (
            ExtraClassTeacherSettlement.query
            .filter(
                ExtraClassTeacherSettlement.settlement_period ==
                current_month
            )
            .all()
        )


        total_teacher_owed = sum(
            float(settlement.amount_owed or 0)
            for settlement in settlements
        )


        total_teacher_paid = sum(
            float(settlement.amount_paid or 0)
            for settlement in settlements
        )


        total_teacher_balance = sum(
            float(settlement.balance or 0)
            for settlement in settlements
        )


        # ----------------------------------------------------
        # RECENT PAYMENTS
        # ----------------------------------------------------

        recent_payments = (
            ExtraClassPayment.query
            .order_by(
                ExtraClassPayment.created_at.desc()
            )
            .limit(10)
            .all()
        )


        # ----------------------------------------------------
        # RECENT STUDENTS
        # ----------------------------------------------------

        recent_students = (
            ExtraClassStudent.query
            .order_by(
                ExtraClassStudent.created_at.desc()
            )
            .limit(10)
            .all()
        )


        # ----------------------------------------------------
        # CURRENT MONTH DISPLAY
        # ----------------------------------------------------

        current_month_display = (
            current_month.strftime("%B %Y")
        )


        # ----------------------------------------------------
        # RENDER
        # ----------------------------------------------------

        return render_template(
            "admin/extra_classes/super_admin/extra_class_super_admin_dashboard.html",

            current_month=current_month_display,

            total_students=total_students,

            total_parents=total_parents,

            total_teachers=total_teachers,

            total_subjects=total_subjects,

            active_enrollments=active_enrollments,

            current_month_fees=current_month_fees,

            current_month_fee_count=current_month_fee_count,

            fee_count=current_month_fee_count,

            payments_received=payments_received,

            successful_payment_count=
                successful_payment_count,

            pending_payments=pending_payments,

            failed_payment_count=
                failed_payment_count,

            total_outstanding=total_outstanding,

            paid_fee_count=paid_fee_count,

            partial_fee_count=partial_fee_count,

            unpaid_fee_count=unpaid_fee_count,

            overdue_fee_count=overdue_fee_count,

            total_teacher_owed=
                total_teacher_owed,

            total_teacher_paid=
                total_teacher_paid,

            total_teacher_balance=
                total_teacher_balance,

            recent_payments=recent_payments,

            recent_students=recent_students
        )


    except Exception as e:

            db.session.rollback()

            print("=" * 70)
            print("SUPER ADMIN DASHBOARD ERROR")
            print("=" * 70)

            traceback.print_exc()

            print("=" * 70)

            raise

# ============================================================
# EXTRA CLASSES REGULAR ADMIN DASHBOARD
# ============================================================

@extra_class_bp.route("/")
@admin_required
def dashboard():
    """
    Extra Classes Administration Dashboard.

    Displays real-time statistics from the Extra Classes
    payment system.
    """

    # --------------------------------------------------------
    # Current billing month
    # --------------------------------------------------------

    today = date.today()

    # First day of the current month
    month_start = today.replace(day=1)

    # First day of the next month
    if month_start.month == 12:
        next_month = date(
            month_start.year + 1,
            1,
            1
        )
    else:
        next_month = date(
            month_start.year,
            month_start.month + 1,
            1
        )

    # Datetime boundaries for payments received this month.
    #
    # Ghana uses UTC+0, so UTC boundaries are appropriate here.
    month_start_datetime = datetime(
        month_start.year,
        month_start.month,
        month_start.day,
        0,
        0,
        0,
        tzinfo=timezone.utc
    )

    next_month_datetime = datetime(
        next_month.year,
        next_month.month,
        next_month.day,
        0,
        0,
        0,
        tzinfo=timezone.utc
    )

    try:

        # ====================================================
        # BASIC COUNTS
        # ====================================================

        # Active Extra Class students
        total_students = (
            ExtraClassStudent.query
            .filter_by(is_active=True)
            .count()
        )

        # Active parents/guardians
        total_parents = (
            ExtraClassParent.query
            .filter_by(is_active=True)
            .count()
        )

        # Active teachers
        total_teachers = (
            ExtraClassTeacher.query
            .filter_by(is_active=True)
            .count()
        )

        # Active Extra Class subjects
        total_subjects = (
            ExtraClassSubject.query
            .filter_by(is_active=True)
            .count()
        )

        # Active student-subject enrollments
        active_enrollments = (
            ExtraClassEnrollment.query
            .filter_by(status="ACTIVE")
            .count()
        )

        # ====================================================
        # CURRENT MONTH'S FEES
        # ====================================================

        current_month_fees = (
            db.session.query(
                db.func.coalesce(
                    db.func.sum(
                        ExtraClassMonthlyFee.amount_due
                    ),
                    0
                )
            )
            .filter(
                ExtraClassMonthlyFee.billing_month == month_start,
                ExtraClassMonthlyFee.status != "CANCELLED"
            )
            .scalar()
        )

        if current_month_fees is None:
            current_month_fees = 0

        # ====================================================
        # PAYMENTS RECEIVED THIS MONTH
        # ====================================================

        payments_received = (
            db.session.query(
                db.func.coalesce(
                    db.func.sum(
                        ExtraClassPayment.amount
                    ),
                    0
                )
            )
            .filter(
                ExtraClassPayment.status == "SUCCESS",
                ExtraClassPayment.paid_at >= month_start_datetime,
                ExtraClassPayment.paid_at < next_month_datetime
            )
            .scalar()
        )

        if payments_received is None:
            payments_received = 0

        # ====================================================
        # PENDING PAYMENTS
        # ====================================================

        pending_payments = (
            ExtraClassPayment.query
            .filter_by(status="PENDING")
            .count()
        )

        # ====================================================
        # PAYMENT COUNTS
        # ====================================================

        successful_payment_count = (
            ExtraClassPayment.query
            .filter(
                ExtraClassPayment.status == "SUCCESS",
                ExtraClassPayment.paid_at >= month_start_datetime,
                ExtraClassPayment.paid_at < next_month_datetime
            )
            .count()
        )

        failed_payment_count = (
            ExtraClassPayment.query
            .filter(
                ExtraClassPayment.status == "FAILED",
                ExtraClassPayment.created_at >= month_start_datetime,
                ExtraClassPayment.created_at < next_month_datetime
            )
            .count()
        )

        # ====================================================
        # CURRENT MONTH'S OUTSTANDING FEES
        # ====================================================
        #
        # A monthly fee can be paid partially.
        #
        # Therefore:
        #
        # Outstanding =
        #       amount_due
        #       -
        #       successful payment items applied to that fee
        #
        # We calculate this in Python for the dashboard rather
        # than changing the database structure.
        # ====================================================

        monthly_fees = (
            ExtraClassMonthlyFee.query
            .filter(
                ExtraClassMonthlyFee.billing_month == month_start,
                ExtraClassMonthlyFee.status != "CANCELLED"
            )
            .all()
        )

        total_outstanding = 0

        if monthly_fees:

            monthly_fee_ids = [
                fee.id
                for fee in monthly_fees
            ]

            payment_items = (
                ExtraClassPaymentItem.query
                .join(
                    ExtraClassPayment,
                    ExtraClassPayment.id
                    == ExtraClassPaymentItem.payment_id
                )
                .filter(
                    ExtraClassPaymentItem.monthly_fee_id.in_(
                        monthly_fee_ids
                    ),
                    ExtraClassPayment.status == "SUCCESS"
                )
                .all()
            )

            paid_by_fee = {}

            for item in payment_items:

                fee_id = item.monthly_fee_id

                if fee_id not in paid_by_fee:
                    paid_by_fee[fee_id] = 0

                paid_by_fee[fee_id] += float(
                    item.amount or 0
                )

            for fee in monthly_fees:

                amount_due = float(
                    fee.amount_due or 0
                )

                amount_paid = paid_by_fee.get(
                    fee.id,
                    0
                )

                outstanding = max(
                    amount_due - amount_paid,
                    0
                )

                total_outstanding += outstanding

        # ====================================================
        # FEE STATUS COUNTS
        # ====================================================

        unpaid_fees = (
            ExtraClassMonthlyFee.query
            .filter(
                ExtraClassMonthlyFee.billing_month == month_start,
                ExtraClassMonthlyFee.status == "UNPAID"
            )
            .count()
        )

        partial_fees = (
            ExtraClassMonthlyFee.query
            .filter(
                ExtraClassMonthlyFee.billing_month == month_start,
                ExtraClassMonthlyFee.status == "PARTIAL"
            )
            .count()
        )

        paid_fees = (
            ExtraClassMonthlyFee.query
            .filter(
                ExtraClassMonthlyFee.billing_month == month_start,
                ExtraClassMonthlyFee.status == "PAID"
            )
            .count()
        )

        overdue_fees = (
            ExtraClassMonthlyFee.query
            .filter(
                ExtraClassMonthlyFee.billing_month == month_start,
                ExtraClassMonthlyFee.status == "OVERDUE"
            )
            .count()
        )

        # ====================================================
        # TEACHER SETTLEMENTS
        # ====================================================

        settlement_owed = (
            db.session.query(
                db.func.coalesce(
                    db.func.sum(
                        ExtraClassTeacherSettlement.amount_owed
                    ),
                    0
                )
            )
            .filter(
                ExtraClassTeacherSettlement.settlement_period
                == month_start
            )
            .scalar()
        )

        if settlement_owed is None:
            settlement_owed = 0

        settlement_paid = (
            db.session.query(
                db.func.coalesce(
                    db.func.sum(
                        ExtraClassTeacherSettlement.amount_paid
                    ),
                    0
                )
            )
            .filter(
                ExtraClassTeacherSettlement.settlement_period
                == month_start
            )
            .scalar()
        )

        if settlement_paid is None:
            settlement_paid = 0

        settlement_balance = (
            float(settlement_owed or 0)
            - float(settlement_paid or 0)
        )

        if settlement_balance < 0:
            settlement_balance = 0

        # ====================================================
        # RECENT PAYMENTS
        # ====================================================

        recent_payments = (
            ExtraClassPayment.query
            .order_by(
                ExtraClassPayment.created_at.desc()
            )
            .limit(10)
            .all()
        )

        # ====================================================
        # RECENT STUDENTS
        # ====================================================

        recent_students = (
            ExtraClassStudent.query
            .order_by(
                ExtraClassStudent.created_at.desc()
            )
            .limit(5)
            .all()
        )

        # ====================================================
        # RECENT TEACHERS
        # ====================================================

        recent_teachers = (
            ExtraClassTeacher.query
            .order_by(
                ExtraClassTeacher.created_at.desc()
            )
            .limit(5)
            .all()
        )

        # ====================================================
        # RENDER DASHBOARD
        # ====================================================

        return render_template(
            "admin/extra_classes/extra_class_admin_dashboard.html",

            # Date information
            today=today,
            month_start=month_start,
            next_month=next_month,

            # Main statistics
            total_students=total_students,
            total_parents=total_parents,
            total_teachers=total_teachers,
            total_subjects=total_subjects,
            active_enrollments=active_enrollments,

            # Financial statistics
            current_month_fees=current_month_fees,
            payments_received=payments_received,
            total_outstanding=total_outstanding,
            pending_payments=pending_payments,

            # Payment statistics
            successful_payment_count=successful_payment_count,
            failed_payment_count=failed_payment_count,

            # Fee statistics
            unpaid_fees=unpaid_fees,
            partial_fees=partial_fees,
            paid_fees=paid_fees,
            overdue_fees=overdue_fees,

            # Teacher settlement statistics
            settlement_owed=settlement_owed,
            settlement_paid=settlement_paid,
            settlement_balance=settlement_balance,

            # Recent records
            recent_payments=recent_payments,
            recent_students=recent_students,
            recent_teachers=recent_teachers
        )

    except Exception as e:

        # ----------------------------------------------------
        # Log the error
        # ----------------------------------------------------

        print(
            "ERROR: Extra Classes dashboard failed:",
            str(e)
        )

        # ----------------------------------------------------
        # Roll back the SQLAlchemy session
        # ----------------------------------------------------

        db.session.rollback()

        # ----------------------------------------------------
        # Show a friendly error message
        # ----------------------------------------------------

        flash(
            "Unable to load the Extra Classes dashboard. "
            "Please try again.",
            "danger"
        )

        return redirect(
            url_for("main.index")
        )



# ============================================================
# SUPER ADMIN — PARENTS MANAGEMENT
# ============================================================

@extra_class_bp.route("/super-admin/parents")
@super_admin_required
def super_admin_parents():
    parents = ExtraClassParent.query.order_by(
        ExtraClassParent.first_name.asc(),
        ExtraClassParent.surname.asc()
    ).all()

    return render_template(
        "admin/extra_classes/super_admin/extra_class_super_admin_parents.html",
        parents=parents
    )



# ------------------------------------------------------------
# SUPER ADMIN — ADD PARENT
# ------------------------------------------------------------

@extra_class_bp.route(
    "/super-admin-add-parent",
    methods=["GET", "POST"]
)
@super_admin_required
def super_admin_add_parent():

    if request.method == "POST":

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

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not first_name or not surname or not phone:

            flash(
                "First name, surname and phone are required.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/extra_class_super_admin_add_parent.html"
            )

        try:

            # ------------------------------------------------
            # CREATE PARENT
            # ------------------------------------------------

            parent = ExtraClassParent(
                first_name=first_name,
                surname=surname,
                phone=phone,
                email=email or None,
                is_active=True
            )

            db.session.add(parent)
            db.session.commit()

            flash(
                f"Parent '{first_name} {surname}' "
                "was added successfully.",
                "success"
            )

            return redirect(
                url_for(
                    "extra_class.super_admin_parents"
                )
            )

        except Exception as e:

            db.session.rollback()

            print(
                "SUPER ADMIN ADD PARENT ERROR:",
                e
            )

            flash(
                "Unable to add the parent. Please try again.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/"
                "extra_class_super_admin_add_parent.html"
            )

    return render_template(
        "admin/extra_classes/super_admin/extra_class_super_admin_add_parent.html"
    )


# ------------------------------------------------------------
# SUPER ADMIN — VIEW PARENT
# ------------------------------------------------------------

@extra_class_bp.route(
    "/super-admin-view-parent/<int:parent_id>"
)
@super_admin_required
def super_admin_view_parent(parent_id):

    parent = (
        ExtraClassParent.query
        .filter_by(id=parent_id)
        .first()
    )

    if not parent:

        flash(
            "Parent not found.",
            "danger"
        )

        return redirect(
            url_for(
                "extra_class.super_admin_parents"
            )
        )

    return render_template(
        "admin/extra_classes/super_admin/"
        "extra_class_super_admin_view_parent.html",
        parent=parent
    )


# ------------------------------------------------------------
# SUPER ADMIN — EDIT PARENT
# ------------------------------------------------------------

@extra_class_bp.route(
    "/super-admin-edit-parent/<int:parent_id>",
    methods=["GET", "POST"]
)
@super_admin_required
def super_admin_edit_parent(parent_id):

    parent = (
        ExtraClassParent.query
        .filter_by(id=parent_id)
        .first()
    )

    if not parent:

        flash(
            "Parent not found.",
            "danger"
        )

        return redirect(
            url_for(
                "extra_class.super_admin_parents"
            )
        )

    if request.method == "POST":

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

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not first_name or not surname or not phone:

            flash(
                "First name, surname and phone are required.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/"
                "extra_class_super_admin_edit_parent.html",
                parent=parent
            )

        try:

            # ------------------------------------------------
            # UPDATE PARENT
            # ------------------------------------------------

            parent.first_name = first_name
            parent.surname = surname
            parent.phone = phone
            parent.email = email or None

            db.session.commit()

            flash(
                f"Parent '{parent.first_name} "
                f"{parent.surname}' "
                "was updated successfully.",
                "success"
            )

            return redirect(
                url_for(
                    "extra_class.super_admin_view_parent",
                    parent_id=parent.id
                )
            )

        except Exception as e:

            db.session.rollback()

            print(
                "SUPER ADMIN EDIT PARENT ERROR:",
                e
            )

            flash(
                "Unable to update the parent. "
                "Please try again.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/"
                "extra_class_super_admin_edit_parent.html",
                parent=parent
            )

    return render_template(
        "admin/extra_classes/super_admin/"
        "extra_class_super_admin_edit_parent.html",
        parent=parent
    )


# ------------------------------------------------------------
# SUPER ADMIN — LINK STUDENT TO PARENT
# ------------------------------------------------------------

@extra_class_bp.route(
    "/super-admin-link-parent-student/<int:parent_id>",
    methods=["GET", "POST"]
)
@super_admin_required
def super_admin_link_parent_student(parent_id):

    parent = (
        ExtraClassParent.query
        .filter_by(id=parent_id)
        .first()
    )

    if not parent:

        flash(
            "Parent not found.",
            "danger"
        )

        return redirect(
            url_for(
                "extra_class.super_admin_parents"
            )
        )


    # --------------------------------------------------------
    # GET ACTIVE STUDENTS
    # --------------------------------------------------------

    students = (
        ExtraClassStudent.query
        .filter_by(is_active=True)
        .order_by(
            ExtraClassStudent.first_name.asc(),
            ExtraClassStudent.surname.asc()
        )
        .all()
    )

    if request.method == "POST":

        student_id = request.form.get(
            "student_id",
            type=int
        )

        relationship = request.form.get(
            "relationship",
            ""
        ).strip()

        is_primary = (
            request.form.get("is_primary") == "1"
        )

        # ----------------------------------------------------
        # VALIDATE STUDENT
        # ----------------------------------------------------

        if not student_id:

            flash(
                "Please select a student.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/"
                "extra_class_super_admin_link_student.html",
                parent=parent,
                students=students
            )

        # ----------------------------------------------------
        # VALIDATE RELATIONSHIP
        # ----------------------------------------------------

        if not relationship:

            flash(
                "Please enter the relationship to the student.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/"
                "extra_class_super_admin_link_student.html",
                parent=parent,
                students=students
            )

        # ----------------------------------------------------
        # FIND STUDENT
        # ----------------------------------------------------

        student = (
            ExtraClassStudent.query
            .filter_by(id=student_id)
            .first()
        )

        if not student:

            flash(
                "Student not found.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/"
                "extra_class_super_admin_link_student.html",
                parent=parent,
                students=students
            )

        # ----------------------------------------------------
        # STUDENT MUST BE ACTIVE
        # ----------------------------------------------------

        if not student.is_active:

            flash(
                "The selected student is inactive.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/"
                "extra_class_super_admin_link_student.html",
                parent=parent,
                students=students
            )

        # ----------------------------------------------------
        # CHECK EXISTING LINK
        # ----------------------------------------------------

        existing_link = (
            ExtraClassStudentParent.query
            .filter_by(
                student_id=student.id,
                parent_id=parent.id
            )
            .first()
        )

        if existing_link:

            flash(
                "This student is already linked to this parent.",
                "warning"
            )

            return redirect(
                url_for(
                    "extra_class.super_admin_view_parent",
                    parent_id=parent.id
                )
            )

        try:

            # ------------------------------------------------
            # HANDLE PRIMARY PARENT
            # ------------------------------------------------

            if is_primary:

                existing_primary_links = (
                    ExtraClassStudentParent.query
                    .filter_by(
                        student_id=student.id,
                        is_primary=True
                    )
                    .all()
                )

                for link in existing_primary_links:
                    link.is_primary = False

            # ------------------------------------------------
            # CREATE LINK
            # ------------------------------------------------

            link = ExtraClassStudentParent(
                student_id=student.id,
                parent_id=parent.id,
                relationship=relationship,
                is_primary=is_primary
            )

            db.session.add(link)
            db.session.commit()

            flash(
                f"{student.first_name} {student.surname} "
                "has been linked to the parent successfully.",
                "success"
            )

            return redirect(
                url_for(
                    "extra_class.super_admin_view_parent",
                    parent_id=parent.id
                )
            )

        except Exception as e:

            db.session.rollback()

            print(
                "SUPER ADMIN LINK PARENT TO STUDENT ERROR:",
                e
            )

            flash(
                "Unable to link the student to the parent. "
                "Please try again.",
                "danger"
            )

    return render_template(
        "admin/extra_classes/super_admin/"
        "extra_class_super_admin_link_student.html",
        parent=parent,
        students=students
    )



# ============================================================
# SUPER ADMIN — TOGGLE PARENT STATUS
# ============================================================

@extra_class_bp.route(
    "/super-admin/toggle-parent-status/<int:parent_id>/",
    methods=["POST"]
)
@super_admin_required
def super_admin_toggle_parent_status(parent_id):

    parent = ExtraClassParent.query.get_or_404(parent_id)

    parent.is_active = not parent.is_active

    try:
        db.session.commit()

        if parent.is_active:
            flash(
                f"{parent.first_name} {parent.surname} has been activated successfully.",
                "success"
            )
        else:
            flash(
                f"{parent.first_name} {parent.surname} has been deactivated successfully.",
                "success"
            )

    except Exception as e:

        db.session.rollback()

        print("SUPER ADMIN TOGGLE PARENT STATUS ERROR:", e)

        flash(
            "Unable to change the parent's status. Please try again.",
            "danger"
        )

    return redirect(
        url_for("extra_class.super_admin_parents")
    )
    


# ============================================================
# SUPER ADMIN — STUDENTS CRUD
# ============================================================

# ============================================================
# SUPER ADMIN — STUDENTS MANAGEMENT
# ============================================================

@extra_class_bp.route("/super-admin/students")
@super_admin_required
def super_admin_students():
    students = ExtraClassStudent.query.order_by(
        ExtraClassStudent.created_at.desc()
    ).all()

    return render_template(
        "admin/extra_classes/super_admin/extra_class_super_admin_students.html",
        students=students
    )


# ------------------------------------------------------------
# SUPER ADMIN — ADD STUDENT
# ------------------------------------------------------------

@extra_class_bp.route(
    "/super-admin-add-student",
    methods=["GET", "POST"]
)
@super_admin_required
def super_admin_add_student():

    if request.method == "POST":

        student_code = request.form.get(
            "student_code",
            ""
        ).strip()

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

        school = request.form.get(
            "school",
            ""
        ).strip()

        class_name = request.form.get(
            "class_name",
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

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not student_code or not first_name or not surname:

            flash(
                "Student code, first name and surname are required.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/"
                "extra_class_super_admin_add_student.html"
            )

        # ----------------------------------------------------
        # CHECK DUPLICATE STUDENT CODE
        # ----------------------------------------------------

        existing_student = (
            ExtraClassStudent.query
            .filter_by(
                student_code=student_code
            )
            .first()
        )

        if existing_student:

            flash(
                "A student with this student code already exists.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/"
                "extra_class_super_admin_add_student.html"
            )

        try:

            # ------------------------------------------------
            # CREATE STUDENT
            # ------------------------------------------------

            student = ExtraClassStudent(
                student_code=student_code,
                first_name=first_name,
                surname=surname,
                other_name=other_name or None,
                school=school or None,
                class_name=class_name or None,
                phone=phone or None,
                email=email or None,
                is_active=True
            )

            db.session.add(student)
            db.session.commit()

            flash(
                f"Student '{first_name} {surname}' "
                "was added successfully.",
                "success"
            )

            return redirect(
                url_for(
                    "extra_class.super_admin_students"
                )
            )

        except Exception as e:

            db.session.rollback()

            print(
                "SUPER ADMIN ADD STUDENT ERROR:",
                e
            )

            flash(
                "Unable to add the student. "
                "Please try again.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/"
                "extra_class_super_admin_add_student.html"
            )

    return render_template(
        "admin/extra_classes/super_admin/"
        "extra_class_super_admin_add_student.html"
    )



# ------------------------------------------------------------
# SUPER ADMIN — VIEW STUDENT
# ------------------------------------------------------------

@extra_class_bp.route(
    "/super-admin-view-student/<int:student_id>"
)
@super_admin_required
def super_admin_view_student(student_id):

    student = (
        ExtraClassStudent.query
        .filter_by(id=student_id)
        .first()
    )

    if not student:

        flash(
            "Student not found.",
            "danger"
        )

        return redirect(
            url_for(
                "extra_class.super_admin_students"
            )
        )

    return render_template(
        "admin/extra_classes/super_admin/"
        "extra_class_super_admin_view_student.html",
        student=student
    )


# ------------------------------------------------------------
# SUPER ADMIN — EDIT STUDENT
# ------------------------------------------------------------

@extra_class_bp.route(
    "/super-admin-edit-student/<int:student_id>",
    methods=["GET", "POST"]
)
@super_admin_required
def super_admin_edit_student(student_id):

    student = (
        ExtraClassStudent.query
        .filter_by(id=student_id)
        .first()
    )

    if not student:

        flash(
            "Student not found.",
            "danger"
        )

        return redirect(
            url_for(
                "extra_class.super_admin_students"
            )
        )

    if request.method == "POST":

        student_code = request.form.get(
            "student_code",
            ""
        ).strip()

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

        school = request.form.get(
            "school",
            ""
        ).strip()

        class_name = request.form.get(
            "class_name",
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

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not student_code or not first_name or not surname:

            flash(
                "Student code, first name and surname are required.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/"
                "extra_class_super_admin_edit_student.html",
                student=student
            )

        # ----------------------------------------------------
        # CHECK DUPLICATE STUDENT CODE
        # ----------------------------------------------------

        duplicate_student = (
            ExtraClassStudent.query
            .filter(
                ExtraClassStudent.student_code == student_code,
                ExtraClassStudent.id != student.id
            )
            .first()
        )

        if duplicate_student:

            flash(
                "Another student is already using this student code.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/"
                "extra_class_super_admin_edit_student.html",
                student=student
            )

        try:

            # ------------------------------------------------
            # UPDATE STUDENT
            # ------------------------------------------------

            student.student_code = student_code
            student.first_name = first_name
            student.surname = surname
            student.other_name = other_name or None
            student.school = school or None
            student.class_name = class_name or None
            student.phone = phone or None
            student.email = email or None

            db.session.commit()

            flash(
                f"Student '{student.first_name} "
                f"{student.surname}' "
                "was updated successfully.",
                "success"
            )

            return redirect(
                url_for(
                    "extra_class.super_admin_view_student",
                    student_id=student.id
                )
            )

        except Exception as e:

            db.session.rollback()

            print(
                "SUPER ADMIN EDIT STUDENT ERROR:",
                e
            )

            flash(
                "Unable to update the student. "
                "Please try again.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/"
                "extra_class_super_admin_edit_student.html",
                student=student
            )

    return render_template(
        "admin/extra_classes/super_admin/"
        "extra_class_super_admin_edit_student.html",
        student=student
    )


# ------------------------------------------------------------
# SUPER ADMIN — LINK PARENT TO STUDENT
# ------------------------------------------------------------

@extra_class_bp.route(
    "/super-admin-link-student-parent/<int:student_id>/",
    methods=["GET", "POST"]
)
@super_admin_required
def super_admin_link_student_parent(student_id):

    student = (
        ExtraClassStudent.query
        .filter_by(id=student_id)
        .first()
    )

    if not student:

        flash(
            "Student not found.",
            "danger"
        )

        return redirect(
            url_for(
                "extra_class.super_admin_students"
            )
        )

    # --------------------------------------------------------
    # GET ACTIVE PARENTS
    # --------------------------------------------------------

    parents = (
        ExtraClassParent.query
        .filter_by(is_active=True)
        .order_by(
            ExtraClassParent.first_name.asc(),
            ExtraClassParent.surname.asc()
        )
        .all()
    )

    if request.method == "POST":

        parent_id = request.form.get(
            "parent_id",
            type=int
        )

        relationship = request.form.get(
            "relationship",
            ""
        ).strip()

        is_primary = (
            request.form.get("is_primary") == "1"
        )

        # ----------------------------------------------------
        # VALIDATE PARENT
        # ----------------------------------------------------

        if not parent_id:

            flash(
                "Please select a parent.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/"
                "extra_class_super_admin_link_parent.html",
                student=student,
                parents=parents
            )

        # ----------------------------------------------------
        # VALIDATE RELATIONSHIP
        # ----------------------------------------------------

        if not relationship:

            flash(
                "Please enter the relationship to the student.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/"
                "extra_class_super_admin_link_parent.html",
                student=student,
                parents=parents
            )

        # ----------------------------------------------------
        # FIND PARENT
        # ----------------------------------------------------

        parent = (
            ExtraClassParent.query
            .filter_by(id=parent_id)
            .first()
        )

        if not parent:

            flash(
                "Parent not found.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/"
                "extra_class_super_admin_link_parent.html",
                student=student,
                parents=parents
            )

        # ----------------------------------------------------
        # PARENT MUST BE ACTIVE
        # ----------------------------------------------------

        if not parent.is_active:

            flash(
                "The selected parent is inactive.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/"
                "extra_class_super_admin_link_parent.html",
                student=student,
                parents=parents
            )

        # ----------------------------------------------------
        # CHECK EXISTING LINK
        # ----------------------------------------------------

        existing_link = (
            ExtraClassStudentParent.query
            .filter_by(
                student_id=student.id,
                parent_id=parent.id
            )
            .first()
        )

        if existing_link:

            flash(
                "This parent is already linked to this student.",
                "warning"
            )

            return redirect(
                url_for(
                    "extra_class.super_admin_view_student",
                    student_id=student.id
                )
            )

        try:

            # ------------------------------------------------
            # HANDLE PRIMARY PARENT
            # ------------------------------------------------

            if is_primary:

                existing_primary_links = (
                    ExtraClassStudentParent.query
                    .filter_by(
                        student_id=student.id,
                        is_primary=True
                    )
                    .all()
                )

                for link in existing_primary_links:
                    link.is_primary = False

            # ------------------------------------------------
            # CREATE LINK
            # ------------------------------------------------

            link = ExtraClassStudentParent(
                student_id=student.id,
                parent_id=parent.id,
                relationship=relationship,
                is_primary=is_primary
            )

            db.session.add(link)
            db.session.commit()

            flash(
                f"{parent.first_name} {parent.surname} "
                f"has been linked to {student.first_name} "
                f"{student.surname} successfully.",
                "success"
            )

            return redirect(
                url_for(
                    "extra_class.super_admin_view_student",
                    student_id=student.id
                )
            )

        except Exception as e:

            db.session.rollback()

            print(
                "SUPER ADMIN LINK STUDENT TO PARENT ERROR:",
                e
            )

            flash(
                "Unable to link the parent to the student. "
                "Please try again.",
                "danger"
            )

    return render_template(
        "admin/extra_classes/super_admin/"
        "extra_class_super_admin_link_parent.html",
        student=student,
        parents=parents
    )
 
 
  
# ============================================================
# SUPER ADMIN — TOGGLE STUDENT STATUS
# ============================================================

@extra_class_bp.route(
    "/super-admin-toggle-student-status/<int:student_id>/",
    methods=["POST"]
)
@super_admin_required
def super_admin_toggle_student_status(student_id):

    student = ExtraClassStudent.query.get_or_404(student_id)

    student.is_active = not student.is_active

    try:
        db.session.commit()

        if student.is_active:
            flash(
                f"{student.first_name} {student.surname} has been activated successfully.",
                "success"
            )
        else:
            flash(
                f"{student.first_name} {student.surname} has been deactivated successfully.",
                "success"
            )

    except Exception as e:

        db.session.rollback()

        print("SUPER ADMIN TOGGLE STUDENT STATUS ERROR:", e)

        flash(
            "Unable to change the student's status. Please try again.",
            "danger"
        )

    return redirect(
        url_for("extra_class.super_admin_students")
    )



 
    
# ============================================================
# REGULAR ADMIN - STUDENTS MANAGEMENT
# ============================================================

@extra_class_bp.route("/students")
@admin_required
def students():
   

    students = (
        ExtraClassStudent.query
        .order_by(
            ExtraClassStudent.created_at.desc()
        )
        .all()
    )

    return render_template(
        "admin/extra_classes/extra_class_students.html",
        students=students
    )
    
  

# ============================================================
# SUPER ADMIN - EXTRA CLASS TERMS
# ============================================================


# ============================================================
# SUPER ADMIN - VIEW EXTRA CLASS TERMS
# ============================================================

@extra_class_bp.route("/super-admin/terms")
@super_admin_required
def super_admin_terms():
    terms = (
        ExtraClassTerm.query
        .order_by(
            ExtraClassTerm.start_date.desc(),
            ExtraClassTerm.created_at.desc()
        )
        .all()
    )

    return render_template(
        "admin/extra_classes/super_admin/extra_class_super_admin_terms.html",
        terms=terms
    )


# ============================================================
# SUPER ADMIN - ADD EXTRA CLASS TERM
# ============================================================

@extra_class_bp.route(
    "/super-admin-add-term",
    methods=["GET", "POST"]
)
@super_admin_required
def super_admin_add_term():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        start_date_text = request.form.get("start_date", "").strip()
        end_date_text = request.form.get("end_date", "").strip()

        # ----------------------------------------------------
        # Validate term name
        # ----------------------------------------------------

        if not name:
            flash(
                "Please enter a term name.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/"
                "extra_class_super_admin_add_term.html"
            )

        # ----------------------------------------------------
        # Validate dates
        # ----------------------------------------------------

        try:
            start_date = datetime.strptime(
                start_date_text,
                "%Y-%m-%d"
            ).date()

            end_date = datetime.strptime(
                end_date_text,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            flash(
                "Please enter valid start and end dates.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/"
                "extra_class_super_admin_add_term.html"
            )

        # ----------------------------------------------------
        # Validate date range
        # ----------------------------------------------------

        if end_date < start_date:

            flash(
                "The end date cannot be earlier than the start date.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/"
                "extra_class_super_admin_add_term.html"
            )

        # ----------------------------------------------------
        # Prevent duplicate term names
        # ----------------------------------------------------

        existing_term = (
            ExtraClassTerm.query
            .filter(
                db.func.lower(ExtraClassTerm.name)
                == name.lower()
            )
            .first()
        )

        if existing_term:

            flash(
                "A term with this name already exists.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/"
                "extra_class_super_admin_add_term.html"
            )

        # ----------------------------------------------------
        # Create the term
        # ----------------------------------------------------

        term = ExtraClassTerm(
            name=name,
            start_date=start_date,
            end_date=end_date,
            is_active=True
        )

        db.session.add(term)
        db.session.commit()

        flash(
            f"Term '{name}' created successfully.",
            "success"
        )

        return redirect(
            url_for("extra_class.super_admin_terms")
        )

    return render_template(
        "admin/extra_classes/super_admin/"
        "extra_class_super_admin_add_term.html"
    )


# ============================================================
# SUPER ADMIN - EDIT EXTRA CLASS TERM
# ============================================================

@extra_class_bp.route(
    "/super-admin-edit-term/<int:term_id>",
    methods=["GET", "POST"]
)
@super_admin_required
def super_admin_edit_term(term_id):

    term = ExtraClassTerm.query.get_or_404(term_id)

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        start_date_text = request.form.get("start_date", "").strip()
        end_date_text = request.form.get("end_date", "").strip()

        # ----------------------------------------------------
        # Validate term name
        # ----------------------------------------------------

        if not name:

            flash(
                "Please enter a term name.",
                "danger"
            )

            return redirect(
                url_for(
                    "extra_class.super_admin_edit_term",
                    term_id=term.id
                )
            )

        # ----------------------------------------------------
        # Validate dates
        # ----------------------------------------------------

        try:

            start_date = datetime.strptime(
                start_date_text,
                "%Y-%m-%d"
            ).date()

            end_date = datetime.strptime(
                end_date_text,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            flash(
                "Please enter valid start and end dates.",
                "danger"
            )

            return redirect(
                url_for(
                    "extra_class.super_admin_edit_term",
                    term_id=term.id
                )
            )

        # ----------------------------------------------------
        # Validate date range
        # ----------------------------------------------------

        if end_date < start_date:

            flash(
                "The end date cannot be earlier than the start date.",
                "danger"
            )

            return redirect(
                url_for(
                    "extra_class.super_admin_edit_term",
                    term_id=term.id
                )
            )

        # ----------------------------------------------------
        # Prevent duplicate term names
        # ----------------------------------------------------

        existing_term = (
            ExtraClassTerm.query
            .filter(
                db.func.lower(ExtraClassTerm.name)
                == name.lower(),
                ExtraClassTerm.id != term.id
            )
            .first()
        )

        if existing_term:

            flash(
                "Another term with this name already exists.",
                "danger"
            )

            return redirect(
                url_for(
                    "extra_class.super_admin_edit_term",
                    term_id=term.id
                )
            )

        # ----------------------------------------------------
        # Update term
        # ----------------------------------------------------

        term.name = name
        term.start_date = start_date
        term.end_date = end_date

        db.session.commit()

        flash(
            "Term updated successfully.",
            "success"
        )

        return redirect(
            url_for("extra_class.super_admin_terms")
        )

    return render_template(
        "admin/extra_classes/super_admin/"
        "extra_class_super_admin_edit_term.html",
        term=term
    )


# ============================================================
# SUPER ADMIN - TOGGLE EXTRA CLASS TERM STATUS
# ============================================================

@extra_class_bp.route(
    "/super-admin-toggle-term-status/<int:term_id>/",
    methods=["POST"]
)
@super_admin_required
def super_admin_toggle_term_status(term_id):

    term = ExtraClassTerm.query.get_or_404(term_id)

    term.is_active = not term.is_active

    db.session.commit()

    status = (
        "activated"
        if term.is_active
        else "deactivated"
    )

    flash(
        f"Term '{term.name}' has been {status}.",
        "success"
    )

    return redirect(
        url_for("extra_class.super_admin_terms")
    )

  
    
# ============================================================
#REGULAR ADMIN ADD EXTRA CLASS STUDENT
# ============================================================

@extra_class_bp.route("/students/add", methods=["GET", "POST"])
@admin_required
def add_student():
    """
    Register a new Extra Class student.
    """

    if request.method == "POST":

        # ----------------------------------------------------
        # Get form values
        # ----------------------------------------------------

        student_code = request.form.get(
            "student_code",
            ""
        ).strip()

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

        school = request.form.get(
            "school",
            ""
        ).strip()

        class_name = request.form.get(
            "class_name",
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

        # ----------------------------------------------------
        # Validate required fields
        # ----------------------------------------------------

        if not student_code:
            flash(
                "Student Code is required.",
                "danger"
            )
            return render_template(
                "admin/extra_classes/extra_class_add_student.html"
            )

        if not first_name:
            flash(
                "First Name is required.",
                "danger"
            )
            return render_template(
                "admin/extra_classes/extra_class_add_student.html"
            )

        if not surname:
            flash(
                "Surname is required.",
                "danger"
            )
            return render_template(
                "admin/extra_classes/extra_class_add_student.html"
            )

        # ----------------------------------------------------
        # Check Student Code uniqueness
        # ----------------------------------------------------

        existing_student = (
            ExtraClassStudent.query
            .filter_by(
                student_code=student_code
            )
            .first()
        )

        if existing_student:

            flash(
                f"Student Code '{student_code}' "
                "is already registered.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/extra_class_add_student.html",
                student_code=student_code,
                first_name=first_name,
                surname=surname,
                other_name=other_name,
                school=school,
                class_name=class_name,
                phone=phone,
                email=email
            )

        # ----------------------------------------------------
        # Create student
        # ----------------------------------------------------

        student = ExtraClassStudent(
            student_code=student_code,
            first_name=first_name,
            surname=surname,
            other_name=other_name or None,
            school=school or None,
            class_name=class_name or None,
            phone=phone or None,
            email=email or None,
            is_active=True
        )

        try:

            db.session.add(student)

            db.session.commit()

            flash(
                f"Student '{first_name} {surname}' "
                "was registered successfully.",
                "success"
            )

            return redirect(
                url_for("extra_class.students")
            )

        except Exception as e:

            db.session.rollback()

            print(
                "ERROR: Failed to create Extra Class student:",
                str(e)
            )

            flash(
                "Unable to register the student. "
                "Please try again.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/extra_class_add_student.html",
                student_code=student_code,
                first_name=first_name,
                surname=surname,
                other_name=other_name,
                school=school,
                class_name=class_name,
                phone=phone,
                email=email
            )

    # --------------------------------------------------------
    # GET request
    # --------------------------------------------------------

    return render_template(
        "admin/extra_classes/extra_class_add_student.html"
    )    



# ============================================================
# EDIT EXTRA CLASS STUDENT
# ============================================================

@extra_class_bp.route("/students/<int:student_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_student(student_id):
    """
    Edit an existing Extra Class student.

    Student Code is intentionally not editable because it is
    the unique identifier used to identify the student.
    """

    # --------------------------------------------------------
    # Find student
    # --------------------------------------------------------

    student = (
        ExtraClassStudent.query
        .filter_by(id=student_id)
        .first()
    )

    if not student:

        flash(
            "Student not found.",
            "danger"
        )

        return redirect(
            url_for("extra_class.students")
        )

    # --------------------------------------------------------
    # Handle form submission
    # --------------------------------------------------------

    if request.method == "POST":

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

        school = request.form.get(
            "school",
            ""
        ).strip()

        class_name = request.form.get(
            "class_name",
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

        # ----------------------------------------------------
        # Validate required fields
        # ----------------------------------------------------

        if not first_name:

            flash(
                "First Name is required.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/extra_class_edit_student.html",
                student=student
            )

        if not surname:

            flash(
                "Surname is required.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/extra_class_edit_student.html",
                student=student
            )

        # ----------------------------------------------------
        # Update student
        # ----------------------------------------------------

        student.first_name = first_name
        student.surname = surname
        student.other_name = other_name or None
        student.school = school or None
        student.class_name = class_name or None
        student.phone = phone or None
        student.email = email or None

        try:

            db.session.commit()

            flash(
                f"Student '{student.first_name} "
                f"{student.surname}' was updated successfully.",
                "success"
            )

            return redirect(
                url_for("extra_class.students")
            )

        except Exception as e:

            db.session.rollback()

            print(
                "ERROR: Failed to update Extra Class student:",
                str(e)
            )

            flash(
                "Unable to update the student. "
                "Please try again.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/extra_class_edit_student.html",
                student=student
            )

    # --------------------------------------------------------
    # GET request
    # --------------------------------------------------------

    return render_template(
        "admin/extra_classes/extra_class_edit_student.html",
        student=student
    )



# ============================================================
# ACTIVATE / DEACTIVATE EXTRA CLASS STUDENT
# ============================================================

@extra_class_bp.route(
    "/students/<int:student_id>/toggle-status/",
    methods=["POST"]
)
@admin_required
def toggle_student_status(student_id):
    """
    Activate or deactivate an Extra Class student.

    Students are never deleted. Their existing enrollments,
    fees, payments and other historical records are preserved.
    """

    # --------------------------------------------------------
    # Find the student
    # --------------------------------------------------------

    student = (
        ExtraClassStudent.query
        .filter_by(id=student_id)
        .first()
    )

    if not student:

        flash(
            "Student not found.",
            "danger"
        )

        return redirect(
            url_for("extra_class.students")
        )

    try:

        # ----------------------------------------------------
        # Toggle status
        # ----------------------------------------------------

        student.is_active = not student.is_active

        db.session.commit()

        # ----------------------------------------------------
        # Success message
        # ----------------------------------------------------

        if student.is_active:

            flash(
                f"{student.first_name} {student.surname} "
                "has been activated successfully.",
                "success"
            )

        else:

            flash(
                f"{student.first_name} {student.surname} "
                "has been deactivated successfully.",
                "warning"
            )

    except Exception as e:

        db.session.rollback()

        print(
            "ERROR: Failed to change Extra Class student status:",
            str(e)
        )

        flash(
            "Unable to change the student's status. "
            "Please try again.",
            "danger"
        )

    return redirect(
        url_for("extra_class.students")
    )



# ============================================================
# PARENT MANAGEMENT
# ============================================================

@extra_class_bp.route("/parents")
@admin_required
def parents():

    parents = (
        ExtraClassParent.query
        .order_by(
            ExtraClassParent.first_name.asc(),
            ExtraClassParent.surname.asc()
        )
        .all()
    )

    return render_template(
        "admin/extra_classes/extra_class_parents.html",
        parents=parents
    )
    
    
    
@extra_class_bp.route("/parents/add", methods=["GET", "POST"])
@admin_required
def add_parent():

    if request.method == "POST":

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

        # ================================================
        # VALIDATION
        # ================================================

        if not first_name or not surname or not phone:

            flash(
                "First name, surname and phone are required.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/extra_class_add_parent.html"
            )

        # ================================================
        # CREATE PARENT
        # ================================================

        try:

            parent = ExtraClassParent(
                first_name=first_name,
                surname=surname,
                phone=phone,
                email=email or None,
                is_active=True
            )

            db.session.add(parent)

            db.session.commit()

            flash(
                "Parent added successfully.",
                "success"
            )

            return redirect(
                url_for("extra_class.parents")
            )

        except Exception as e:

            db.session.rollback()

            print(
                "ERROR ADDING PARENT:",
                e
            )

            flash(
                "An error occurred while adding the parent.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/extra_class_add_parent.html"
            )

    # ================================================
    # GET
    # ================================================

    return render_template(
        "admin/extra_classes/extra_class_add_parent.html"
    )    
    
    
    
    
@extra_class_bp.route(
    "/parents/<int:parent_id>/edit",
    methods=["GET", "POST"]
)
@admin_required
def edit_parent(parent_id):

    parent = ExtraClassParent.query.filter_by(
        id=parent_id
    ).first()

    if not parent:

        flash(
            "Parent not found.",
            "danger"
        )

        return redirect(
            url_for("extra_class.parents")
        )

    if request.method == "POST":

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

        # ================================================
        # VALIDATION
        # ================================================

        if not first_name or not surname or not phone:

            flash(
                "First name, surname and phone are required.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/extra_class_edit_parent.html",
                parent=parent
            )

        # ================================================
        # UPDATE PARENT
        # ================================================

        try:

            parent.first_name = first_name
            parent.surname = surname
            parent.phone = phone
            parent.email = email or None

            db.session.commit()

            flash(
                "Parent updated successfully.",
                "success"
            )

            return redirect(
                url_for("extra_class.parents")
            )

        except Exception as e:

            db.session.rollback()

            print(
                "ERROR EDITING PARENT:",
                e
            )

            flash(
                "An error occurred while updating the parent.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/extra_class_edit_parent.html",
                parent=parent
            )

    # ================================================
    # GET
    # ================================================

    return render_template(
        "admin/extra_classes/extra_class_edit_parent.html",
        parent=parent
    )    
    
    

@extra_class_bp.route(
    "/parents/<int:parent_id>/toggle-status",
    methods=["POST"]
)
@admin_required
def toggle_parent_status(parent_id):

    parent = ExtraClassParent.query.filter_by(
        id=parent_id
    ).first()

    if not parent:

        flash(
            "Parent not found.",
            "danger"
        )

        return redirect(
            url_for("extra_class.parents")
        )

    try:

        parent.is_active = not parent.is_active

        db.session.commit()

        if parent.is_active:

            flash(
                "Parent activated successfully.",
                "success"
            )

        else:

            flash(
                "Parent deactivated successfully.",
                "warning"
            )

    except Exception as e:

        db.session.rollback()

        print(
            "ERROR TOGGLING PARENT STATUS:",
            e
        )

        flash(
            "An error occurred while changing the parent's status.",
            "danger"
        )

    return redirect(
        url_for("extra_class.parents")
    )
    


@extra_class_bp.route("/students/<int:student_id>")
@admin_required
def view_student(student_id):
    student = ExtraClassStudent.query.filter_by(id=student_id).first()

    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for("extra_class.students"))

    return render_template(
        "admin/extra_classes/extra_class_view_student.html",
        student=student
    )
    


    
@extra_class_bp.route(
    "/students/<int:student_id>/link-parent",
    methods=["GET"]
)
@admin_required
def link_student_parent_form(student_id):
    student = ExtraClassStudent.query.filter_by(id=student_id).first()

    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for("extra_class.students"))

    # Get active parents who are not already linked
    linked_parent_ids = [
        link.parent_id
        for link in student.parent_links
    ]

    if linked_parent_ids:
        parents = (
            ExtraClassParent.query
            .filter(
                ExtraClassParent.is_active.is_(True),
                ~ExtraClassParent.id.in_(linked_parent_ids)
            )
            .order_by(
                ExtraClassParent.first_name.asc(),
                ExtraClassParent.surname.asc()
            )
            .all()
        )
    else:
        parents = (
            ExtraClassParent.query
            .filter_by(is_active=True)
            .order_by(
                ExtraClassParent.first_name.asc(),
                ExtraClassParent.surname.asc()
            )
            .all()
        )

    return render_template(
        "admin/extra_classes/extra_class_link_parent.html",
        student=student,
        parents=parents
    )    



@extra_class_bp.route(
    "/students/<int:student_id>/link-parent",
    methods=["POST"]
)
@admin_required
def link_student_parent(student_id):
    student = ExtraClassStudent.query.filter_by(id=student_id).first()

    if not student:
        flash("Student not found.", "danger")
        return redirect(url_for("extra_class.students"))

    parent_id = request.form.get("parent_id", type=int)
    relationship = request.form.get("relationship", "").strip()
    is_primary = request.form.get("is_primary") == "1"

    # Validate parent selection
    if not parent_id:
        flash("Please select a parent or guardian.", "danger")
        return redirect(
            url_for(
                "extra_class.link_student_parent_form",
                student_id=student.id
            )
        )

    # Validate relationship
    if not relationship:
        flash("Please select the relationship to the student.", "danger")
        return redirect(
            url_for(
                "extra_class.link_student_parent_form",
                student_id=student.id
            )
        )

    # Find parent
    parent = ExtraClassParent.query.filter_by(id=parent_id).first()

    if not parent:
        flash("Parent not found.", "danger")
        return redirect(
            url_for(
                "extra_class.link_student_parent_form",
                student_id=student.id
            )
        )

    # Prevent duplicate relationship
    existing_link = (
        ExtraClassStudentParent.query
        .filter_by(
            student_id=student.id,
            parent_id=parent.id
        )
        .first()
    )

    if existing_link:
        flash(
            "This parent is already linked to this student.",
            "warning"
        )
        return redirect(
            url_for(
                "extra_class.view_student",
                student_id=student.id
            )
        )

    try:

        # If this parent becomes primary,
        # remove primary status from other parents
        # linked to this student.
        if is_primary:

            existing_primary_links = (
                ExtraClassStudentParent.query
                .filter_by(
                    student_id=student.id,
                    is_primary=True
                )
                .all()
            )

            for link in existing_primary_links:
                link.is_primary = False

        # Create relationship
        link = ExtraClassStudentParent(
            student_id=student.id,
            parent_id=parent.id,
            relationship=relationship,
            is_primary=is_primary
        )

        db.session.add(link)
        db.session.commit()

        flash(
            f"{parent.first_name} {parent.surname} "
            f"has been linked to {student.first_name} "
            f"{student.surname} successfully.",
            "success"
        )

    except Exception as e:

        db.session.rollback()

        print(
            "ERROR LINKING STUDENT TO PARENT:",
            e
        )

        flash(
            "An error occurred while linking the parent.",
            "danger"
        )

    return redirect(
        url_for(
            "extra_class.view_student",
            student_id=student.id
        )
    )


    
@extra_class_bp.route("/parents/<int:parent_id>")
@admin_required
def view_parent(parent_id):

    parent = ExtraClassParent.query.filter_by(
        id=parent_id
    ).first()

    if not parent:

        flash(
            "Parent not found.",
            "danger"
        )

        return redirect(
            url_for("extra_class.parents")
        )

    return render_template(
        "admin/extra_classes/extra_class_view_parent.html",
        parent=parent
    )
    
    
    

@extra_class_bp.route(
    "/parents/<int:parent_id>/link-student",
    methods=["GET"]
)
@admin_required
def link_parent_student_form(parent_id):
    parent = ExtraClassParent.query.filter_by(id=parent_id).first()

    if not parent:
        flash("Parent not found.", "danger")
        return redirect(url_for("extra_class.parents"))

    # Get active students for the selection list
    students = (
        ExtraClassStudent.query
        .filter_by(is_active=True)
        .order_by(
            ExtraClassStudent.first_name.asc(),
            ExtraClassStudent.surname.asc()
        )
        .all()
    )

    return render_template(
        "admin/extra_classes/extra_class_link_student.html",
        parent=parent,
        students=students
    )




@extra_class_bp.route("/parents/<int:parent_id>/link-student", methods=["POST"])
@admin_required
def link_parent_student(parent_id):
    parent = ExtraClassParent.query.filter_by(id=parent_id).first()

    if not parent:
        flash("Parent not found.", "danger")
        return redirect(url_for("extra_class.parents"))

    # Get submitted form values
    student_id = request.form.get("student_id", type=int)
    relationship = request.form.get("relationship", "").strip()
    is_primary = request.form.get("is_primary") == "1"

    # Validate student selection
    if not student_id:
        flash("Please select a student.", "danger")
        return redirect(
            url_for(
                "extra_class.view_parent",
                parent_id=parent.id
            )
        )

    # Validate relationship
    if not relationship:
        flash("Please enter the relationship to the student.", "danger")
        return redirect(
            url_for(
                "extra_class.view_parent",
                parent_id=parent.id
            )
        )

    # Find the student
    student = ExtraClassStudent.query.filter_by(id=student_id).first()

    if not student:
        flash("Student not found.", "danger")
        return redirect(
            url_for(
                "extra_class.view_parent",
                parent_id=parent.id
            )
        )

    # Prevent duplicate parent-student links
    existing_link = (
        ExtraClassStudentParent.query
        .filter_by(
            student_id=student.id,
            parent_id=parent.id
        )
        .first()
    )

    if existing_link:
        flash(
            "This student is already linked to this parent.",
            "warning"
        )
        return redirect(
            url_for(
                "extra_class.view_parent",
                parent_id=parent.id
            )
        )

    try:
        # If this parent is being made the primary parent,
        # remove primary status from the student's other parents.
        if is_primary:
            existing_primary_links = (
                ExtraClassStudentParent.query
                .filter_by(
                    student_id=student.id,
                    is_primary=True
                )
                .all()
            )

            for link in existing_primary_links:
                link.is_primary = False

        # Create the new relationship
        link = ExtraClassStudentParent(
            student_id=student.id,
            parent_id=parent.id,
            relationship=relationship,
            is_primary=is_primary
        )

        db.session.add(link)
        db.session.commit()

        flash(
            f"{student.first_name} {student.surname} "
            "has been linked to the parent successfully.",
            "success"
        )

    except Exception as e:
        db.session.rollback()

        print("ERROR LINKING PARENT TO STUDENT:", e)

        flash(
            "An error occurred while linking the student.",
            "danger"
        )

    return redirect(
        url_for(
            "extra_class.view_parent",
            parent_id=parent.id
        )
    )


    
    
# ============================================================
# TEACHER MANAGEMENT
# ============================================================

@extra_class_bp.route("/teachers")
@admin_required
def teachers():

    teachers = ExtraClassTeacher.query.order_by(
        ExtraClassTeacher.created_at.desc()
    ).all()

    # Count unique subjects currently assigned to teachers
    subjects_covered = (
        db.session.query(
            ExtraClassSubject.subject_id
        )
        .filter(
            ExtraClassSubject.teacher_id.isnot(None)
        )
        .distinct()
        .count()
    )

    return render_template(
        "admin/extra_classes/super_admin/extra_class_teachers.html",
        teachers=teachers,
        subjects_covered=subjects_covered
    )


# ============================================================
# ADD TEACHER
# ============================================================

@extra_class_bp.route("/teachers/add", methods=["GET", "POST"])
@admin_required
def add_teacher():

    if request.method == "POST":

        first_name = request.form.get("first_name", "").strip()
        surname = request.form.get("surname", "").strip()
        teacher_code = request.form.get("teacher_code", "").strip()
        phone = request.form.get("phone", "").strip()
        email = request.form.get("email", "").strip()

        # Required fields
        if not first_name or not surname or not phone:

            flash(
                "First name, surname and phone number are required.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/extra_class_add_teacher.html"
            )

        # Teacher code uniqueness
        if teacher_code:

            existing_teacher = ExtraClassTeacher.query.filter_by(
                teacher_code=teacher_code
            ).first()

            if existing_teacher:

                flash(
                    "That teacher code is already in use.",
                    "danger"
                )

                return render_template(
                    "admin/extra_classes/super_admin/extra_class_add_teacher.html"
                )

        teacher = ExtraClassTeacher(
            teacher_code=teacher_code or None,
            first_name=first_name,
            surname=surname,
            phone=phone,
            email=email or None,
            is_active=True
        )

        db.session.add(teacher)

        try:

            db.session.commit()

            flash(
                "Teacher added successfully.",
                "success"
            )

            return redirect(
                url_for("extra_class.teachers")
            )

        except Exception as e:

            db.session.rollback()

            print("ADD TEACHER ERROR:", e)

            flash(
                "Unable to add teacher. Please try again.",
                "danger"
            )

    return render_template(
        "admin/extra_classes/super_admin/extra_class_add_teacher.html"
    )


# ============================================================
# VIEW TEACHER
# ============================================================

@extra_class_bp.route("/teachers/<int:teacher_id>")
@admin_required
def view_teacher(teacher_id):

    teacher = ExtraClassTeacher.query.get_or_404(
        teacher_id
    )

    return render_template(
        "admin/extra_classes/super_admin/extra_class_view_teacher.html",
        teacher=teacher
    )


# ============================================================
# EDIT TEACHER
# ============================================================

@extra_class_bp.route(
    "/teachers/<int:teacher_id>/edit",
    methods=["GET", "POST"]
)
@admin_required
def edit_teacher(teacher_id):

    teacher = ExtraClassTeacher.query.get_or_404(
        teacher_id
    )

    if request.method == "POST":

        first_name = request.form.get(
            "first_name",
            ""
        ).strip()

        surname = request.form.get(
            "surname",
            ""
        ).strip()

        teacher_code = request.form.get(
            "teacher_code",
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

        if not first_name or not surname or not phone:

            flash(
                "First name, surname and phone number are required.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/extra_class_edit_teacher.html",
                teacher=teacher
            )

        # Check teacher code belongs to another teacher
        if teacher_code:

            existing_teacher = (
                ExtraClassTeacher.query
                .filter(
                    ExtraClassTeacher.teacher_code == teacher_code,
                    ExtraClassTeacher.id != teacher.id
                )
                .first()
            )

            if existing_teacher:

                flash(
                    "That teacher code is already assigned to another teacher.",
                    "danger"
                )

                return render_template(
                    "admin/extra_classes/super_admin/extra_class_edit_teacher.html",
                    teacher=teacher
                )

        teacher.first_name = first_name
        teacher.surname = surname
        teacher.teacher_code = teacher_code or None
        teacher.phone = phone
        teacher.email = email or None

        try:

            db.session.commit()

            flash(
                "Teacher updated successfully.",
                "success"
            )

            return redirect(
                url_for(
                    "extra_class.view_teacher",
                    teacher_id=teacher.id
                )
            )

        except Exception as e:

            db.session.rollback()

            print("EDIT TEACHER ERROR:", e)

            flash(
                "Unable to update teacher. Please try again.",
                "danger"
            )

    return render_template(
        "admin/extra_classes/super_admin/extra_class_edit_teacher.html",
        teacher=teacher
    )




# ============================================================
# TOGGLE TEACHER STATUS
# ============================================================

@extra_class_bp.route(
    "/teachers/<int:teacher_id>/toggle-status",
    methods=["POST"]
)
@admin_required
def toggle_teacher_status(teacher_id):

    teacher = ExtraClassTeacher.query.get_or_404(
        teacher_id
    )

    teacher.is_active = not teacher.is_active

    try:

        db.session.commit()

        if teacher.is_active:

            flash(
                f"{teacher.first_name} {teacher.surname} has been activated.",
                "success"
            )

        else:

            flash(
                f"{teacher.first_name} {teacher.surname} has been deactivated.",
                "success"
            )

    except Exception as e:

        db.session.rollback()

        print("TOGGLE TEACHER ERROR:", e)

        flash(
            "Unable to change teacher status.",
            "danger"
        )

    return redirect(
        url_for("extra_class.teachers")
    )



# ============================================================
# SUBJECT MANAGEMENT
# ============================================================

@extra_class_bp.route("/subjects")
@super_admin_required
def subjects():

    subjects = (
        ExtraClassSubject.query
        .order_by(
            ExtraClassSubject.created_at.desc()
        )
        .all()
    )

    # Statistics
    total_subjects = len(subjects)

    active_subjects = sum(
        1 for subject in subjects
        if subject.is_active
    )

    inactive_subjects = total_subjects - active_subjects

    assigned_teachers = sum(
        1 for subject in subjects
        if subject.teacher_id is not None
    )

    return render_template(
        "admin/extra_classes/super_admin/extra_class_subjects.html",
        subjects=subjects,
        total_subjects=total_subjects,
        active_subjects=active_subjects,
        inactive_subjects=inactive_subjects,
        assigned_teachers=assigned_teachers
    )



# ============================================================
# ADD EXTRA CLASS SUBJECT
# ============================================================

@extra_class_bp.route("/subjects/add", methods=["GET", "POST"])
@super_admin_required
def add_subject():

    # Existing BTA subjects
    bta_subjects = (
        Subject.query
        .filter_by(is_active=True)
        .order_by(Subject.display_order.asc(), Subject.name.asc())
        .all()
    )

    # Extra Class teachers
    teachers = (
        ExtraClassTeacher.query
        .filter_by(is_active=True)
        .order_by(
            ExtraClassTeacher.first_name.asc(),
            ExtraClassTeacher.surname.asc()
        )
        .all()
    )

    if request.method == "POST":

        subject_id = request.form.get("subject_id", "").strip()
        teacher_id = request.form.get("teacher_id", "").strip()
        monthly_fee = request.form.get("monthly_fee", "").strip()

        # ----------------------------------------------------
        # VALIDATION
        # ----------------------------------------------------

        if not subject_id:
            flash("Please select a subject.", "danger")
            return render_template(
                "admin/extra_classes/super_admin/extra_class_add_subject.html",
                bta_subjects=bta_subjects,
                teachers=teachers
            )

        if not monthly_fee:
            flash("Please enter the monthly fee.", "danger")
            return render_template(
                "admin/extra_classes/super_admin/extra_class_add_subject.html",
                bta_subjects=bta_subjects,
                teachers=teachers
            )

        try:
            subject_id = int(subject_id)

            if teacher_id:
                teacher_id = int(teacher_id)
            else:
                teacher_id = None

            monthly_fee = float(monthly_fee)

            if monthly_fee < 0:
                raise ValueError

        except (ValueError, TypeError):
            flash("Please enter valid subject, teacher and fee information.", "danger")
            return render_template(
                "admin/extra_classes/super_admin/extra_class_add_subject.html",
                bta_subjects=bta_subjects,
                teachers=teachers
            )

        # ----------------------------------------------------
        # CHECK THAT SUBJECT EXISTS
        # ----------------------------------------------------

        bta_subject = Subject.query.get(subject_id)

        if not bta_subject:
            flash("The selected subject does not exist.", "danger")
            return render_template(
                "admin/extra_classes/super_admin/extra_class_add_subject.html",
                bta_subjects=bta_subjects,
                teachers=teachers
            )

        # ----------------------------------------------------
        # PREVENT DUPLICATE EXTRA CLASS SUBJECT
        # ----------------------------------------------------

        existing_subject = ExtraClassSubject.query.filter_by(
            subject_id=subject_id
        ).first()

        if existing_subject:
            flash(
                f"{bta_subject.name} is already registered as an Extra Class subject.",
                "warning"
            )
            return render_template(
                "admin/extra_classes/super_admin/extra_class_add_subject.html",
                bta_subjects=bta_subjects,
                teachers=teachers
            )

        # ----------------------------------------------------
        # CHECK TEACHER IF SELECTED
        # ----------------------------------------------------

        if teacher_id:

            teacher = ExtraClassTeacher.query.get(teacher_id)

            if not teacher or not teacher.is_active:
                flash("The selected teacher is not available.", "danger")
                return render_template(
                    "admin/extra_classes/super_admin/extra_class_add_subject.html",
                    bta_subjects=bta_subjects,
                    teachers=teachers
                )

        # ----------------------------------------------------
        # CREATE EXTRA CLASS SUBJECT
        # ----------------------------------------------------

        extra_subject = ExtraClassSubject(
            subject_id=subject_id,
            teacher_id=teacher_id,
            monthly_fee=monthly_fee,
            is_active=True
        )

        db.session.add(extra_subject)

        try:
            db.session.commit()

            flash(
                f"{bta_subject.name} has been added to Extra Classes successfully.",
                "success"
            )

            return redirect(
                url_for("extra_class.subjects")
            )

        except Exception as e:

            db.session.rollback()

            print("ADD EXTRA CLASS SUBJECT ERROR:", e)

            flash(
                "Unable to add the Extra Class subject. Please try again.",
                "danger"
            )

    return render_template(
        "admin/extra_classes/super_admin/extra_class_add_subject.html",
        bta_subjects=bta_subjects,
        teachers=teachers
    )


# ============================================================
# EDIT EXTRA CLASS SUBJECT
# ============================================================

@extra_class_bp.route(
    "/subjects/<int:extra_subject_id>/edit",
    methods=["GET", "POST"]
)
@super_admin_required
def edit_subject(extra_subject_id):

    extra_subject = ExtraClassSubject.query.get_or_404(
        extra_subject_id
    )

    teachers = (
        ExtraClassTeacher.query
        .filter_by(is_active=True)
        .order_by(
            ExtraClassTeacher.first_name.asc(),
            ExtraClassTeacher.surname.asc()
        )
        .all()
    )

    if request.method == "POST":

        teacher_id = request.form.get("teacher_id", "").strip()
        monthly_fee = request.form.get("monthly_fee", "").strip()

        # ----------------------------------------------------
        # VALIDATE MONTHLY FEE
        # ----------------------------------------------------

        if not monthly_fee:
            flash("Please enter the monthly fee.", "danger")

            return render_template(
                "admin/extra_classes/super_admin/extra_class_edit_subject.html",
                extra_subject=extra_subject,
                teachers=teachers
            )

        try:
            monthly_fee = float(monthly_fee)

            if monthly_fee < 0:
                raise ValueError

        except (ValueError, TypeError):

            flash(
                "Please enter a valid monthly fee.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/extra_class_edit_subject.html",
                extra_subject=extra_subject,
                teachers=teachers
            )

        # ----------------------------------------------------
        # VALIDATE TEACHER
        # ----------------------------------------------------

        if teacher_id:

            try:
                teacher_id = int(teacher_id)

            except (ValueError, TypeError):

                flash(
                    "Please select a valid teacher.",
                    "danger"
                )

                return render_template(
                    "admin/extra_classes/super_admin/extra_class_edit_subject.html",
                    extra_subject=extra_subject,
                    teachers=teachers
                )

            teacher = ExtraClassTeacher.query.get(teacher_id)

            if not teacher or not teacher.is_active:

                flash(
                    "The selected teacher is not available.",
                    "danger"
                )

                return render_template(
                    "admin/extra_classes/super_admin/extra_class_edit_subject.html",
                    extra_subject=extra_subject,
                    teachers=teachers
                )

        else:
            teacher_id = None

        # ----------------------------------------------------
        # UPDATE SUBJECT
        # ----------------------------------------------------

        extra_subject.teacher_id = teacher_id
        extra_subject.monthly_fee = monthly_fee

        try:

            db.session.commit()

            flash(
                f"{extra_subject.subject.name} has been updated successfully.",
                "success"
            )

            return redirect(
                url_for(
                    "extra_class.view_subject",
                    extra_subject_id=extra_subject.id
                )
            )

        except Exception as e:

            db.session.rollback()

            print(
                "EDIT EXTRA CLASS SUBJECT ERROR:",
                e
            )

            flash(
                "Unable to update the Extra Class subject. Please try again.",
                "danger"
            )

    return render_template(
        "admin/extra_classes/super_admin/extra_class_edit_subject.html",
        extra_subject=extra_subject,
        teachers=teachers
    )



# ============================================================
# VIEW EXTRA CLASS SUBJECT
# ============================================================

@extra_class_bp.route("/subjects/<int:extra_subject_id>")
@super_admin_required
def view_subject(extra_subject_id):

    extra_subject = ExtraClassSubject.query.get_or_404(
        extra_subject_id
    )

    return render_template(
        "admin/extra_classes/super_admin/extra_class_view_subject.html",
        extra_subject=extra_subject
    )



# ============================================================
# TOGGLE EXTRA CLASS SUBJECT STATUS
# ============================================================

@extra_class_bp.route(
    "/subjects/<int:extra_subject_id>/toggle-status",
    methods=["POST"]
)
@super_admin_required
def toggle_subject_status(extra_subject_id):

    extra_subject = ExtraClassSubject.query.get_or_404(
        extra_subject_id
    )

    extra_subject.is_active = not extra_subject.is_active

    try:

        db.session.commit()

        if extra_subject.is_active:

            flash(
                f"{extra_subject.subject.name} has been activated successfully.",
                "success"
            )

        else:

            flash(
                f"{extra_subject.subject.name} has been deactivated successfully.",
                "success"
            )

    except Exception as e:

        db.session.rollback()

        print(
            "TOGGLE EXTRA CLASS SUBJECT ERROR:",
            e
        )

        flash(
            "Unable to change the subject status. Please try again.",
            "danger"
        )

    return redirect(
        url_for("extra_class.subjects")
    )
    
    
    
# ============================================================
# ENROLLMENT MANAGEMENT
# ============================================================

@extra_class_bp.route("/enrollments")
@admin_required
def enrollments():

    enrollments = (
        ExtraClassEnrollment.query
        .order_by(
            ExtraClassEnrollment.created_at.desc()
        )
        .all()
    )

    total_enrollments = len(enrollments)

    active_enrollments = sum(
        1
        for enrollment in enrollments
        if enrollment.status == "ACTIVE"
    )

    inactive_enrollments = sum(
        1
        for enrollment in enrollments
        if enrollment.status == "INACTIVE"
    )

    completed_enrollments = sum(
        1
        for enrollment in enrollments
        if enrollment.status == "COMPLETED"
    )

    cancelled_enrollments = sum(
        1
        for enrollment in enrollments
        if enrollment.status == "CANCELLED"
    )

    return render_template(
        "admin/extra_classes/super_admin/extra_class_enrollments.html",
        enrollments=enrollments,
        total_enrollments=total_enrollments,
        active_enrollments=active_enrollments,
        inactive_enrollments=inactive_enrollments,
        completed_enrollments=completed_enrollments,
        cancelled_enrollments=cancelled_enrollments
    )


# ============================================================
# ENROLL A STUDENT FOR EXTRA CLASSES
# ============================================================

@extra_class_bp.route("/add-enrollment/", methods=["GET", "POST"])
@super_admin_required
def add_enrollment():

    students = ExtraClassStudent.query.filter_by(
        is_active=True
    ).order_by(
        ExtraClassStudent.first_name.asc(),
        ExtraClassStudent.surname.asc()
    ).all()

    extra_subjects = ExtraClassSubject.query.filter_by(
        is_active=True
    ).order_by(
        ExtraClassSubject.created_at.desc()
    ).all()

    terms = ExtraClassTerm.query.filter_by(
        is_active=True
    ).order_by(
        ExtraClassTerm.start_date.desc()
    ).all()

    if request.method == "POST":

        student_id = request.form.get(
            "student_id", ""
        ).strip()

        extra_class_subject_id = request.form.get(
            "extra_class_subject_id", ""
        ).strip()

        term_id = request.form.get(
            "term_id", ""
        ).strip()

        start_date = request.form.get(
            "start_date", ""
        ).strip()

        # --------------------------------
        # REQUIRED FIELD VALIDATION
        # --------------------------------

        if (
            not student_id
            or not extra_class_subject_id
            or not term_id
            or not start_date
        ):

            flash(
                "Please complete all required fields.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/"
                "extra_class_add_enrollment.html",
                students=students,
                extra_subjects=extra_subjects,
                terms=terms
            )

        # --------------------------------
        # CONVERT IDs
        # --------------------------------

        try:

            student_id = int(student_id)
            extra_class_subject_id = int(
                extra_class_subject_id
            )
            term_id = int(term_id)

        except ValueError:

            flash(
                "Invalid student, subject, or term selection.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/"
                "extra_class_add_enrollment.html",
                students=students,
                extra_subjects=extra_subjects,
                terms=terms
            )

        # --------------------------------
        # START DATE
        # --------------------------------

        try:

            enrollment_start_date = datetime.strptime(
                start_date,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            flash(
                "Invalid enrollment start date.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/"
                "extra_class_add_enrollment.html",
                students=students,
                extra_subjects=extra_subjects,
                terms=terms
            )

        # --------------------------------
        # GET STUDENT
        # --------------------------------

        student = ExtraClassStudent.query.get(
            student_id
        )

        if not student or not student.is_active:

            flash(
                "The selected student is not available.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/"
                "extra_class_add_enrollment.html",
                students=students,
                extra_subjects=extra_subjects,
                terms=terms
            )

        # --------------------------------
        # GET EXTRA CLASS SUBJECT
        # --------------------------------

        extra_subject = ExtraClassSubject.query.get(
            extra_class_subject_id
        )

        if not extra_subject or not extra_subject.is_active:

            flash(
                "The selected Extra Class subject is not available.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/"
                "extra_class_add_enrollment.html",
                students=students,
                extra_subjects=extra_subjects,
                terms=terms
            )

        # --------------------------------
        # GET TERM
        # --------------------------------

        term = ExtraClassTerm.query.get(term_id)

        if not term or not term.is_active:

            flash(
                "The selected term is not available.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/"
                "extra_class_add_enrollment.html",
                students=students,
                extra_subjects=extra_subjects,
                terms=terms
            )

        # --------------------------------
        # VALIDATE START DATE AGAINST TERM
        # --------------------------------

        if enrollment_start_date < term.start_date:

            flash(
                "The enrollment start date cannot be before "
                "the selected term starts.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/"
                "extra_class_add_enrollment.html",
                students=students,
                extra_subjects=extra_subjects,
                terms=terms
            )

        if enrollment_start_date > term.end_date:

            flash(
                "The enrollment start date cannot be after "
                "the selected term ends.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/"
                "extra_class_add_enrollment.html",
                students=students,
                extra_subjects=extra_subjects,
                terms=terms
            )

        # --------------------------------
        # PREVENT DUPLICATE ENROLLMENT
        # --------------------------------

        existing_enrollment = ExtraClassEnrollment.query.filter_by(
            student_id=student.id,
            extra_class_subject_id=extra_subject.id
        ).first()

        if existing_enrollment:

            flash(
                "This student is already enrolled in the selected subject.",
                "warning"
            )

            return render_template(
                "admin/extra_classes/super_admin/"
                "extra_class_add_enrollment.html",
                students=students,
                extra_subjects=extra_subjects,
                terms=terms
            )

        # --------------------------------
        # CREATE ENROLLMENT
        # --------------------------------

        enrollment = ExtraClassEnrollment(
            student_id=student.id,
            term_id=term.id,
            extra_class_subject_id=extra_subject.id,
            start_date=enrollment_start_date,
            status="ACTIVE"
        )

        db.session.add(enrollment)

        # --------------------------------
        # SAVE
        # --------------------------------

        try:

            db.session.commit()

            flash(
                f"{student.first_name} {student.surname} "
                f"has been enrolled successfully.",
                "success"
            )

            return redirect(
                url_for("extra_class.enrollments")
            )

        except Exception as e:

            db.session.rollback()

            print(
                "ADD EXTRA CLASS ENROLLMENT ERROR:",
                e
            )

            flash(
                "Unable to create the enrollment. Please try again.",
                "danger"
            )

    return render_template(
        "admin/extra_classes/super_admin/"
        "extra_class_add_enrollment.html",
        students=students,
        extra_subjects=extra_subjects,
        terms=terms
    )
    
     

# ============================================================
# VIEW STUDENT ENROLLED IN EXTRA CLASSES
# ============================================================


@extra_class_bp.route("/view-enrollment/<int:enrollment_id>")
@super_admin_required
def view_enrollment(enrollment_id):

    enrollment = ExtraClassEnrollment.query.get_or_404(
        enrollment_id
    )

    return render_template(
        "admin/extra_classes/super_admin/extra_class_view_enrollment.html",
        enrollment=enrollment
    )



@extra_class_bp.route(
    "/edit-enrollment/<int:enrollment_id>",
    methods=["GET", "POST"]
)
@super_admin_required
def edit_enrollment(enrollment_id):

    enrollment = ExtraClassEnrollment.query.get_or_404(
        enrollment_id
    )

    # -------------------------------------------------
    # LOAD STUDENTS
    # -------------------------------------------------
    students = ExtraClassStudent.query.filter(
        db.or_(
            ExtraClassStudent.is_active.is_(True),
            ExtraClassStudent.id == enrollment.student_id
        )
    ).order_by(
        ExtraClassStudent.first_name.asc(),
        ExtraClassStudent.surname.asc()
    ).all()

    # -------------------------------------------------
    # LOAD ACTIVE EXTRA CLASS SUBJECTS
    # Include the currently selected subject even if
    # it has subsequently been deactivated.
    # -------------------------------------------------
    extra_subjects = ExtraClassSubject.query.filter(
        db.or_(
            ExtraClassSubject.is_active.is_(True),
            ExtraClassSubject.id == enrollment.extra_class_subject_id
        )
    ).order_by(
        ExtraClassSubject.created_at.desc()
    ).all()

    # -------------------------------------------------
    # LOAD ACTIVE TERMS
    # Include the enrollment's current term even if
    # it is no longer active.
    # -------------------------------------------------
    terms = ExtraClassTerm.query.filter(
        db.or_(
            ExtraClassTerm.is_active.is_(True),
            ExtraClassTerm.id == enrollment.term_id
        )
    ).order_by(
        ExtraClassTerm.start_date.desc()
    ).all()

    # -------------------------------------------------
    # POST
    # -------------------------------------------------
    if request.method == "POST":

        student_id = request.form.get(
            "student_id",
            ""
        ).strip()

        extra_class_subject_id = request.form.get(
            "extra_class_subject_id",
            ""
        ).strip()

        term_id = request.form.get(
            "term_id",
            ""
        ).strip()

        start_date = request.form.get(
            "start_date",
            ""
        ).strip()

        end_date = request.form.get(
            "end_date",
            ""
        ).strip()

        status = request.form.get(
            "status",
            ""
        ).strip().upper()

        # -------------------------------------------------
        # REQUIRED FIELD VALIDATION
        # -------------------------------------------------
        if (
            not student_id
            or not extra_class_subject_id
            or not term_id
            or not start_date
        ):
            flash(
                "Please complete all required fields.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/extra_class_edit_enrollment.html",
                enrollment=enrollment,
                students=students,
                extra_subjects=extra_subjects,
                terms=terms
            )

        # -------------------------------------------------
        # CONVERT IDs
        # -------------------------------------------------
        try:
            student_id = int(student_id)
            extra_class_subject_id = int(
                extra_class_subject_id
            )
            term_id = int(term_id)

        except ValueError:
            flash(
                "Invalid student, subject or term selection.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/extra_class_edit_enrollment.html",
                enrollment=enrollment,
                students=students,
                extra_subjects=extra_subjects,
                terms=terms
            )

        # -------------------------------------------------
        # START DATE
        # -------------------------------------------------
        try:
            enrollment_start_date = datetime.strptime(
                start_date,
                "%Y-%m-%d"
            ).date()

        except ValueError:
            flash(
                "Invalid enrollment start date.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/extra_class_edit_enrollment.html",
                enrollment=enrollment,
                students=students,
                extra_subjects=extra_subjects,
                terms=terms
            )

        # -------------------------------------------------
        # END DATE
        # -------------------------------------------------
        enrollment_end_date = None

        if end_date:

            try:
                enrollment_end_date = datetime.strptime(
                    end_date,
                    "%Y-%m-%d"
                ).date()

            except ValueError:
                flash(
                    "Invalid enrollment end date.",
                    "danger"
                )

                return render_template(
                    "admin/extra_classes/super_admin/extra_class_edit_enrollment.html",
                    enrollment=enrollment,
                    students=students,
                    extra_subjects=extra_subjects,
                    terms=terms
                )

        # -------------------------------------------------
        # DATE CONSISTENCY
        # -------------------------------------------------
        if (
            enrollment_end_date
            and enrollment_end_date < enrollment_start_date
        ):
            flash(
                "End date cannot be earlier than the start date.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/extra_class_edit_enrollment.html",
                enrollment=enrollment,
                students=students,
                extra_subjects=extra_subjects,
                terms=terms
            )

        # -------------------------------------------------
        # STATUS VALIDATION
        # -------------------------------------------------
        allowed_statuses = {
            "ACTIVE",
            "INACTIVE",
            "COMPLETED",
            "CANCELLED"
        }

        if status not in allowed_statuses:
            flash(
                "Invalid enrollment status.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/extra_class_edit_enrollment.html",
                enrollment=enrollment,
                students=students,
                extra_subjects=extra_subjects,
                terms=terms
            )

        # -------------------------------------------------
        # GET STUDENT
        # -------------------------------------------------
        student = ExtraClassStudent.query.get(
            student_id
        )

        if not student or not student.is_active:
            flash(
                "The selected student is not available.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/extra_class_edit_enrollment.html",
                enrollment=enrollment,
                students=students,
                extra_subjects=extra_subjects,
                terms=terms
            )

        # -------------------------------------------------
        # GET EXTRA CLASS SUBJECT
        # -------------------------------------------------
        extra_subject = ExtraClassSubject.query.get(
            extra_class_subject_id
        )

        if not extra_subject or not extra_subject.is_active:
            flash(
                "The selected Extra Class subject is not available.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/extra_class_edit_enrollment.html",
                enrollment=enrollment,
                students=students,
                extra_subjects=extra_subjects,
                terms=terms
            )

        # -------------------------------------------------
        # GET TERM
        # -------------------------------------------------
        term = ExtraClassTerm.query.get(
            term_id
        )

        if not term:
            flash(
                "The selected term could not be found.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/extra_class_edit_enrollment.html",
                enrollment=enrollment,
                students=students,
                extra_subjects=extra_subjects,
                terms=terms
            )

        # -------------------------------------------------
        # TERM DATE VALIDATION
        # -------------------------------------------------
        if enrollment_start_date < term.start_date:

            flash(
                "Enrollment start date cannot be earlier than the term start date.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/extra_class_edit_enrollment.html",
                enrollment=enrollment,
                students=students,
                extra_subjects=extra_subjects,
                terms=terms
            )

        if enrollment_start_date > term.end_date:

            flash(
                "Enrollment start date cannot be later than the term end date.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/extra_class_edit_enrollment.html",
                enrollment=enrollment,
                students=students,
                extra_subjects=extra_subjects,
                terms=terms
            )

        if (
            enrollment_end_date
            and enrollment_end_date > term.end_date
        ):

            flash(
                "Enrollment end date cannot be later than the term end date.",
                "danger"
            )

            return render_template(
                "admin/extra_classes/super_admin/extra_class_edit_enrollment.html",
                enrollment=enrollment,
                students=students,
                extra_subjects=extra_subjects,
                terms=terms
            )

        # -------------------------------------------------
        # DUPLICATE ENROLLMENT CHECK
        # Same student + same subject + same term
        # -------------------------------------------------
        existing_enrollment = ExtraClassEnrollment.query.filter(
            ExtraClassEnrollment.student_id == student.id,
            ExtraClassEnrollment.extra_class_subject_id == extra_subject.id,
            ExtraClassEnrollment.term_id == term.id,
            ExtraClassEnrollment.id != enrollment.id
        ).first()

        if existing_enrollment:

            flash(
                "This student is already enrolled in the selected subject for this term.",
                "warning"
            )

            return render_template(
                "admin/extra_classes/super_admin/extra_class_edit_enrollment.html",
                enrollment=enrollment,
                students=students,
                extra_subjects=extra_subjects,
                terms=terms
            )

        # -------------------------------------------------
        # CHECK FOR EXISTING MONTHLY FEES
        # -------------------------------------------------
        existing_fees = ExtraClassMonthlyFee.query.filter_by(
            enrollment_id=enrollment.id
        ).first()

        # -------------------------------------------------
        # PROTECT BILLING HISTORY
        # -------------------------------------------------
        if existing_fees:

            billing_changed = (
                enrollment.student_id != student.id
                or enrollment.extra_class_subject_id != extra_subject.id
                or enrollment.term_id != term.id
                or enrollment.start_date != enrollment_start_date
            )

            if billing_changed:

                flash(
                    "This enrollment already has monthly fees. "
                    "Student, subject, term and start date cannot be changed "
                    "after billing records have been generated.",
                    "warning"
                )

                return render_template(
                    "admin/extra_classes/super_admin/extra_class_edit_enrollment.html",
                    enrollment=enrollment,
                    students=students,
                    extra_subjects=extra_subjects,
                    terms=terms
                )

        # -------------------------------------------------
        # UPDATE ENROLLMENT
        # -------------------------------------------------
        enrollment.student_id = student.id

        enrollment.extra_class_subject_id = (
            extra_subject.id
        )

        enrollment.term_id = term.id

        enrollment.start_date = (
            enrollment_start_date
        )

        enrollment.end_date = (
            enrollment_end_date
        )

        enrollment.status = status

        # -------------------------------------------------
        # SAVE
        # -------------------------------------------------
        try:

            db.session.commit()

            flash(
                "Enrollment updated successfully.",
                "success"
            )

            return redirect(
                url_for(
                    "extra_class.view_enrollment",
                    enrollment_id=enrollment.id
                )
            )

        except Exception as e:

            db.session.rollback()

            print(
                "EDIT EXTRA CLASS ENROLLMENT ERROR:",
                e
            )

            flash(
                "Unable to update the enrollment. Please try again.",
                "danger"
            )

    # -------------------------------------------------
    # GET REQUEST
    # -------------------------------------------------
    return render_template(
        "admin/extra_classes/super_admin/extra_class_edit_enrollment.html",
        enrollment=enrollment,
        students=students,
        extra_subjects=extra_subjects,
        terms=terms
    )


# ============================================================
# HELPER FUNCTION - CALCULATE MONTHLY FEE DUE DATE
# ============================================================


def _calculate_fee_due_date(enrollment_start_date, billing_month):
    """
    Calculate the monthly fee due date using the student's
    enrollment day as the recurring payment day.

    Example:
        Enrollment: 2026-09-10
        September fee -> 2026-09-10
        October fee   -> 2026-10-10
        November fee  -> 2026-11-10

    If the month does not contain the enrollment day,
    the due date is clamped to the last day of that month.

    Example:
        Enrollment: January 31
        February due date -> February 28/29
    """

    last_day = calendar.monthrange(
        billing_month.year,
        billing_month.month
    )[1]

    due_day = min(
        enrollment_start_date.day,
        last_day
    )

    return date(
        billing_month.year,
        billing_month.month,
        due_day
    )



def _calculate_proration(remaining_days):
    """
    Determine the school-rule proration percentage
    based on the number of days remaining in the
    final billing cycle.

    1–7 days   = 25%
    8–14 days  = 50%
    15–21 days = 75%
    22+ days   = 100%
    """

    if remaining_days <= 0:
        return {
            "type": "NONE",
            "percentage": 0,
            "reason": "No billable days remain in the billing cycle."
        }

    if remaining_days <= 7:
        return {
            "type": "QUARTER_MONTH",
            "percentage": 25,
            "reason": (
                f"Final billing cycle has {remaining_days} "
                "days remaining."
            )
        }

    if remaining_days <= 14:
        return {
            "type": "HALF_MONTH",
            "percentage": 50,
            "reason": (
                f"Final billing cycle has {remaining_days} "
                "days remaining."
            )
        }

    if remaining_days <= 21:
        return {
            "type": "THREE_QUARTER_MONTH",
            "percentage": 75,
            "reason": (
                f"Final billing cycle has {remaining_days} "
                "days remaining."
            )
        }

    return {
        "type": "NONE",
        "percentage": 100,
        "reason": (
            f"Final billing cycle has {remaining_days} "
            "days remaining."
        )
    }


def _calculate_enrollment_monthly_fees(enrollment):
    """
    Calculate monthly fee information for an enrollment.

    Rules:
    - Billing is monthly.
    - The billing cycle follows the enrollment start day.
    - The initial enrollment month receives the full monthly charge.
    - A final shortened billing cycle is prorated using:
        1–7 days   = 25%
        8–14 days  = 50%
        15–21 days = 75%
        22+ days   = 100%
    - billing_month is always the first day of the
      calendar month containing the billing cycle start.
    """

    if not enrollment:
        raise ValueError("Enrollment is required.")

    if not enrollment.term:
        raise ValueError(
            "Enrollment must have a semester."
        )

    if not enrollment.extra_class_subject:
        raise ValueError(
            "Enrollment must have an Extra Class subject."
        )

    if not enrollment.start_date:
        raise ValueError(
            "Enrollment must have a start date."
        )

    term = enrollment.term
    subject = enrollment.extra_class_subject

    enrollment_start = enrollment.start_date

    # The enrollment cannot continue beyond the semester.
    
    effective_end = term.end_date

    # If the enrollment has its own end date,
    # use whichever comes first.
    
    if enrollment.end_date:
        effective_end = min(
            effective_end,
            enrollment.end_date
        )

    if effective_end < enrollment_start:
        return []

    # ---------------------------------------------
    # STANDARD MONTHLY FEE
    # ---------------------------------------------
    standard_amount = subject.monthly_fee

    if standard_amount is None:
        raise ValueError(
            "The selected Extra Class subject does not "
            "have a monthly fee."
        )

    # Keep Decimal precision for money.
    from decimal import Decimal

    standard_amount = Decimal(
        str(standard_amount)
    )

    fee_rows = []

    # ---------------------------------------------
    # BILLING CYCLES
    # ---------------------------------------------
    cycle_start = enrollment_start

    while cycle_start <= effective_end:

        # The student's normal monthly cycle.
        next_cycle_start = (
            cycle_start + relativedelta(months=1)
        )

        normal_cycle_end = (
            next_cycle_start - relativedelta(days=1)
        )

        # The actual date up to which the student
        # can be billed.
        actual_cycle_end = min(
            normal_cycle_end,
            effective_end
        )

        # -----------------------------------------
        # BILLABLE DAYS
        # -----------------------------------------
        billable_days = (
            actual_cycle_end - cycle_start
        ).days + 1

        # -----------------------------------------
        # IS THIS A SHORTENED FINAL CYCLE?
        # -----------------------------------------
        is_shortened_cycle = (
            actual_cycle_end < normal_cycle_end
        )

        if is_shortened_cycle:

            proration = _calculate_proration(
                billable_days
            )

        else:

            proration = {
                "type": "NONE",
                "percentage": 100,
                "reason": None
            }

        # -----------------------------------------
        # CALCULATE AMOUNT
        # -----------------------------------------
        amount_due = (
            standard_amount
            * Decimal(
                str(proration["percentage"])
            )
            / Decimal("100")
        )

        amount_due = amount_due.quantize(
            Decimal("0.01")
        )

        # -----------------------------------------
        # BILLING MONTH
        # -----------------------------------------
        billing_month = date(
            cycle_start.year,
            cycle_start.month,
            1
        )

        # -----------------------------------------
        # DUE DATE
        # -----------------------------------------
        due_date = _calculate_fee_due_date(
            enrollment_start,
            billing_month
        )

        fee_rows.append({
            "student_id": enrollment.student_id,

            "enrollment_id": enrollment.id,

            "term_id": term.id,

            "extra_class_subject_id": (
                enrollment.extra_class_subject_id
            ),

            "billing_month": billing_month,

            "standard_amount": standard_amount,

            "amount_due": amount_due,

            "proration_type": (
                proration["type"]
            ),

            "proration_percentage": (
                proration["percentage"]
            ),

            "proration_reason": (
                proration["reason"]
            ),

            "due_date": due_date,

            # -------------------------------------
            # BILLING-CYCLE INFORMATION
            # -------------------------------------
            "cycle_start": cycle_start,

            "normal_cycle_end": normal_cycle_end,

            "actual_cycle_end": actual_cycle_end,

            "billable_days": billable_days,

            "is_shortened_cycle": (
                is_shortened_cycle
            )
        })

        # -----------------------------------------
        # NEXT BILLING CYCLE
        # -----------------------------------------
        cycle_start = next_cycle_start

    return fee_rows


@extra_class_bp.route(
    "/test-fee-calculation/<int:enrollment_id>"
)
@super_admin_required
def test_fee_calculation(enrollment_id):

    enrollment = ExtraClassEnrollment.query.get_or_404(
        enrollment_id
    )

    try:

        fee_rows = _calculate_enrollment_monthly_fees(
            enrollment
        )

    except Exception as e:

        print(
            "FEE CALCULATION TEST ERROR:",
            e
        )

        flash(
            f"Fee calculation failed: {str(e)}",
            "danger"
        )

        return redirect(
            url_for(
                "extra_class.view_enrollment",
                enrollment_id=enrollment.id
            )
        )

    return render_template(
        "admin/extra_classes/super_admin/test_fee_calculation.html",
        enrollment=enrollment,
        fee_rows=fee_rows
    )


# ============================================================
# GENERATE MONTHLY FEES FOR AN ENROLLMENT
# ============================================================

@extra_class_bp.route(
    "/generate-monthly-fees/<int:enrollment_id>",
    methods=["POST"]
)
@super_admin_required
def generate_monthly_fees(enrollment_id):
    """
    Generate the actual monthly fee records for an enrollment.

    Rules:
    - Only ACTIVE enrollments can generate fees.
    - Uses the tested monthly-fee calculation helper.
    - Does not create duplicate monthly fees.
    - Existing fee records are never overwritten.
    - Supports normal and prorated final billing periods.
    """

    # --------------------------------------------------------
    # GET ENROLLMENT
    # --------------------------------------------------------

    enrollment = (
        ExtraClassEnrollment.query
        .filter_by(id=enrollment_id)
        .first()
    )

    if not enrollment:

        flash(
            "Enrollment not found.",
            "danger"
        )

        return redirect(
            url_for("extra_class.enrollments")
        )

    # --------------------------------------------------------
    # ONLY ACTIVE ENROLLMENTS CAN GENERATE FEES
    # --------------------------------------------------------

    if enrollment.status != "ACTIVE":

        flash(
            "Monthly fees can only be generated for an active enrollment.",
            "warning"
        )

        return redirect(
            url_for(
                "extra_class.view_enrollment",
                enrollment_id=enrollment.id
            )
        )

    # --------------------------------------------------------
    # REQUIRED BILLING RELATIONSHIPS
    # --------------------------------------------------------

    if not enrollment.term:

        flash(
            "This enrollment does not have a semester assigned.",
            "danger"
        )

        return redirect(
            url_for(
                "extra_class.view_enrollment",
                enrollment_id=enrollment.id
            )
        )

    if not enrollment.extra_class_subject:

        flash(
            "This enrollment does not have an Extra Class subject assigned.",
            "danger"
        )

        return redirect(
            url_for(
                "extra_class.view_enrollment",
                enrollment_id=enrollment.id
            )
        )

    if enrollment.extra_class_subject.monthly_fee is None:

        flash(
            "The selected subject does not have a monthly fee configured.",
            "danger"
        )

        return redirect(
            url_for(
                "extra_class.view_enrollment",
                enrollment_id=enrollment.id
            )
        )

    # --------------------------------------------------------
    # CALCULATE FEES
    # --------------------------------------------------------

    try:

        fee_rows = _calculate_enrollment_monthly_fees(
            enrollment
        )

    except Exception as e:

        print(
            "MONTHLY FEE CALCULATION ERROR:",
            e
        )

        traceback.print_exc()

        flash(
            f"Unable to calculate monthly fees: {str(e)}",
            "danger"
        )

        return redirect(
            url_for(
                "extra_class.view_enrollment",
                enrollment_id=enrollment.id
            )
        )

    # --------------------------------------------------------
    # NO BILLABLE PERIODS
    # --------------------------------------------------------

    if not fee_rows:

        flash(
            "No billable periods were found for this enrollment.",
            "warning"
        )

        return redirect(
            url_for(
                "extra_class.view_enrollment",
                enrollment_id=enrollment.id
            )
        )

    # --------------------------------------------------------
    # GENERATE FEE RECORDS
    # --------------------------------------------------------

    created_count = 0
    skipped_count = 0

    try:

        for fee_data in fee_rows:

            # ------------------------------------------------
            # CHECK FOR EXISTING FEE
            # ------------------------------------------------
            #
            # The database already has a unique constraint on:
            #
            # student_id
            # extra_class_subject_id
            # billing_month
            #
            # We also check here so the user receives a clean
            # result instead of a database integrity error.
            # ------------------------------------------------

            existing_fee = (
                ExtraClassMonthlyFee.query
                .filter_by(
                    student_id=fee_data["student_id"],
                    extra_class_subject_id=(fee_data["extra_class_subject_id"]),
                    billing_month=(
                        fee_data["billing_month"]
                    )
                )
                .first()
            )

            if existing_fee:

                skipped_count += 1

                continue

            # ------------------------------------------------
            # CREATE MONTHLY FEE
            # ------------------------------------------------

            monthly_fee = ExtraClassMonthlyFee(
                student_id=fee_data["student_id"],

                enrollment_id=fee_data["enrollment_id"],

                term_id=fee_data["term_id"],

                extra_class_subject_id=(
                    fee_data["extra_class_subject_id"]
                ),

                billing_month=fee_data["billing_month"],

                standard_amount=(
                    fee_data["standard_amount"]
                ),

                amount_due=(
                    fee_data["amount_due"]
                ),

                proration_type=(
                    fee_data["proration_type"]
                ),

                proration_percentage=(
                    fee_data["proration_percentage"]
                ),

                proration_reason=(
                    fee_data["proration_reason"]
                ),

                due_date=(
                    fee_data["due_date"]
                ),

                status="UNPAID"
            )

            db.session.add(monthly_fee)

            created_count += 1

        # ----------------------------------------------------
        # SAVE EVERYTHING
        # ----------------------------------------------------

        db.session.commit()

        # ----------------------------------------------------
        # SUCCESS MESSAGE
        # ----------------------------------------------------

        if created_count > 0 and skipped_count == 0:

            flash(
                f"{created_count} monthly fee record"
                f"{'s' if created_count != 1 else ''} "
                "generated successfully.",
                "success"
            )

        elif created_count > 0 and skipped_count > 0:

            flash(
                f"{created_count} new monthly fee record"
                f"{'s' if created_count != 1 else ''} "
                f"generated. "
                f"{skipped_count} existing record"
                f"{'s were' if skipped_count != 1 else ' was'} "
                "skipped to prevent duplicates.",
                "success"
            )

        else:

            flash(
                "All monthly fee records for this enrollment "
                "already exist. No duplicates were created.",
                "info"
            )

        return redirect(
            url_for(
                "extra_class.view_enrollment",
                enrollment_id=enrollment.id
            )
        )

    except Exception as e:

        # ----------------------------------------------------
        # ROLLBACK
        # ----------------------------------------------------

        db.session.rollback()

        print(
            "=" * 70
        )
        print(
            "GENERATE MONTHLY FEES ERROR"
        )
        print(
            "=" * 70
        )

        traceback.print_exc()

        print(
            "=" * 70
        )

        flash(
            "Unable to generate monthly fees. "
            "No fee records were saved.",
            "danger"
        )

        return redirect(
            url_for(
                "extra_class.view_enrollment",
                enrollment_id=enrollment.id
            )
        )


# =========================
# MONTHLY FEES
# =========================

@extra_class_bp.route("/fees")
@super_admin_required
def fees():
    """
    Display generated monthly Extra Class fees.
    """

    monthly_fees = (
        ExtraClassMonthlyFee.query
        .order_by(
            ExtraClassMonthlyFee.billing_month.desc(),
            ExtraClassMonthlyFee.id.desc()
        )
        .all()
    )

    return render_template(
        "admin/extra_classes/super_admin/extra_class_fees.html",
        monthly_fees=monthly_fees
    )



# ============================================================
# PAYMENTS
# ============================================================

@extra_class_bp.route("/payments")
@admin_required
def payments():
    """
    Extra Class payment management page.
    """

    payments = (
        ExtraClassPayment.query
        .order_by(
            ExtraClassPayment.created_at.desc()
        )
        .all()
    )

    return render_template(
        "admin/extra_classes/payments.html",
        payments=payments
    )


# ============================================================
# TEACHER SETTLEMENTS
# ============================================================

@extra_class_bp.route("/settlements")
@admin_required
def settlements():
    """
    Extra Class teacher settlement management page.
    """

    settlements = (
        ExtraClassTeacherSettlement.query
        .order_by(
            ExtraClassTeacherSettlement.settlement_period.desc(),
            ExtraClassTeacherSettlement.created_at.desc()
        )
        .all()
    )

    return render_template(
        "admin/extra_classes/settlements.html",
        settlements=settlements
    )