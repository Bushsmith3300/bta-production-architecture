from datetime import date, datetime, timezone
import calendar

from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    flash,
    session
)

from app.extensions import db

from app.models import (
    ExtraClassTeacher,
    ExtraClassTeacherAccount,
    ExtraClassSubject,
    ExtraClassEnrollment,
    ExtraClassMonthlyFee,
    ExtraClassPayment,
    ExtraClassPaymentItem,
    ExtraClassTerm,
    ExtraClassStudent,
    ExtraClassParent,
    ExtraClassStudentParent,
)

from app.utils.extra_class_decorators import (
    extra_class_teacher_required
)


# ============================================================
# BLUEPRINT
# ============================================================

extra_class_teacher_bp = Blueprint(
    "extra_class_teacher",
    __name__,
    url_prefix="/extra-classes/teacher"
)

# ============================================================
# MONTHLY FEE GENERATION
# ============================================================

def _next_billing_date(current_date, billing_day):
    """Return the next monthly billing date, clamped to month-end."""
    year = current_date.year
    month = current_date.month + 1

    if month == 13:
        month = 1
        year += 1

    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, min(billing_day, last_day))


def _final_proration(days_remaining):
    """Apply the agreed final-cycle proration rules."""
    if days_remaining <= 7:
        return (
            "QUARTER_MONTH",
            25,
            f"{days_remaining} days remaining in the final billing cycle"
        )
    if days_remaining <= 14:
        return (
            "HALF_MONTH",
            50,
            f"{days_remaining} days remaining in the final billing cycle"
        )
    if days_remaining <= 21:
        return (
            "THREE_QUARTER_MONTH",
            75,
            f"{days_remaining} days remaining in the final billing cycle"
        )

    return (
        "NONE",
        100,
        f"{days_remaining} days remaining in the final billing cycle"
    )


def generate_enrollment_monthly_fees(enrollment):
    """
    Generate monthly fee records for one active enrollment.

    The teacher's ExtraClassSubject.monthly_fee is copied into
    standard_amount as the historical fee snapshot.

    The initial enrollment month is always charged in full.
    Later billing cycles follow the enrollment day, clamped to
    month-end. The final cycle ends on the enrollment term end date
    and uses the agreed proration rules.
    """

    if not enrollment:
        raise ValueError("Enrollment is required.")

    if enrollment.status != "ACTIVE":
        raise ValueError("Only active enrollments can generate monthly fees.")

    if not enrollment.start_date:
        raise ValueError("Enrollment start date is required.")

    if not enrollment.end_date:
        raise ValueError("Enrollment end date is required.")

    extra_subject = (
        ExtraClassSubject.query
        .filter_by(id=enrollment.extra_class_subject_id)
        .first()
    )

    if not extra_subject:
        raise ValueError("The class subject could not be found.")

    standard_amount = float(extra_subject.monthly_fee or 0)

    if standard_amount < 0:
        raise ValueError("The class monthly fee cannot be negative.")

    billing_day = enrollment.start_date.day
    current_due_date = enrollment.start_date

    created_count = 0
    existing_count = 0

    while current_due_date <= enrollment.end_date:

        billing_month = current_due_date.replace(day=1)

        next_due_date = _next_billing_date(
            current_due_date,
            billing_day
        )

        is_final_cycle = next_due_date > enrollment.end_date

        if is_final_cycle:
            days_remaining = (
                enrollment.end_date - current_due_date
            ).days + 1

            (
                proration_type,
                proration_percentage,
                proration_reason
            ) = _final_proration(days_remaining)

            # The initial enrollment month is ALWAYS full.
            if current_due_date == enrollment.start_date:
                proration_type = "NONE"
                proration_percentage = 100
                proration_reason = (
                    "Initial enrollment month charged in full"
                )

            amount_due = round(
                standard_amount
                * (proration_percentage / 100),
                2
            )
        else:
            proration_type = "NONE"
            proration_percentage = 100
            proration_reason = None
            amount_due = round(standard_amount, 2)

        existing_fee = (
            ExtraClassMonthlyFee.query
            .filter(
                ExtraClassMonthlyFee.student_id
                == enrollment.student_id,
                ExtraClassMonthlyFee.extra_class_subject_id
                == enrollment.extra_class_subject_id,
                ExtraClassMonthlyFee.billing_month
                == billing_month
            )
            .first()
        )

        if existing_fee:
            existing_count += 1
        else:
            fee = ExtraClassMonthlyFee(
                student_id=enrollment.student_id,
                enrollment_id=enrollment.id,
                term_id=enrollment.term_id,
                extra_class_subject_id=(
                    enrollment.extra_class_subject_id
                ),
                billing_month=billing_month,
                standard_amount=standard_amount,
                amount_due=amount_due,
                proration_type=proration_type,
                proration_percentage=proration_percentage,
                proration_reason=proration_reason,
                due_date=current_due_date,
                status="UNPAID"
            )

            db.session.add(fee)
            created_count += 1

        current_due_date = next_due_date

    return created_count, existing_count


# ============================================================
# FINANCIAL HELPERS
# ============================================================

def calculate_enrollment_outstanding(enrollment_id):
    """Return the true outstanding balance for an enrollment.

    Outstanding = non-cancelled fees - successful payments applied to
    those fees. This keeps all teacher views consistent with Class Fees.
    """

    monthly_fees = (
        ExtraClassMonthlyFee.query
        .filter(
            ExtraClassMonthlyFee.enrollment_id == enrollment_id
        )
        .all()
    )

    total_fees = 0.0
    total_paid = 0.0

    for fee in monthly_fees:
        if str(fee.status or "").upper() == "CANCELLED":
            continue

        total_fees += float(fee.amount_due or 0)

        payment_items = (
            ExtraClassPaymentItem.query
            .join(
                ExtraClassPayment,
                ExtraClassPayment.id == ExtraClassPaymentItem.payment_id
            )
            .filter(
                ExtraClassPaymentItem.monthly_fee_id == fee.id,
                ExtraClassPayment.status == "SUCCESS"
            )
            .all()
        )

        total_paid += sum(
            float(item.amount or 0)
            for item in payment_items
        )

    return max(total_fees - total_paid, 0.0)


# ============================================================
# TEACHER DASHBOARD
# ============================================================

@extra_class_teacher_bp.route("/dashboard")
@extra_class_teacher_required
def teacher_dashboard():

    teacher_id = session.get(
        "extra_class_teacher_id"
    )

    # --------------------------------------------------------
    # LOAD TEACHER
    # --------------------------------------------------------

    teacher = (
        ExtraClassTeacher.query
        .filter_by(id=teacher_id)
        .first_or_404()
    )

    # --------------------------------------------------------
    # ASSIGNED SUBJECTS
    #
    # Only active subjects assigned to this teacher.
    # --------------------------------------------------------

    assigned_subjects = (
        ExtraClassSubject.query
        .filter(
            ExtraClassSubject.teacher_id == teacher.id,
            ExtraClassSubject.is_active.is_(True)
        )
        .order_by(
            ExtraClassSubject.created_at.asc()
        )
        .all()
    )

    # --------------------------------------------------------
    # SUBJECT IDS
    # --------------------------------------------------------

    subject_ids = [
        subject.id
        for subject in assigned_subjects
    ]

    # --------------------------------------------------------
    # DEFAULT DASHBOARD VALUES
    # --------------------------------------------------------

    total_students = 0
    active_enrollments = 0

    current_month_fees = 0
    current_month_paid = 0
    current_month_outstanding = 0

    successful_payment_count = 0

    current_month = date.today().replace(
        day=1
    )

    # ========================================================
    # TEACHER STATISTICS
    # ========================================================

    if subject_ids:

        # ----------------------------------------------------
        # ACTIVE ENROLLMENTS
        # ----------------------------------------------------

        active_enrollments = (
            ExtraClassEnrollment.query
            .filter(
                ExtraClassEnrollment
                .extra_class_subject_id
                .in_(subject_ids),

                ExtraClassEnrollment.status == "ACTIVE"
            )
            .count()
        )

        # ----------------------------------------------------
        # UNIQUE ACTIVE STUDENTS
        # ----------------------------------------------------

        total_students = (
            db.session.query(
                db.func.count(
                    db.distinct(
                        ExtraClassEnrollment.student_id
                    )
                )
            )
            .filter(
                ExtraClassEnrollment
                .extra_class_subject_id
                .in_(subject_ids),

                ExtraClassEnrollment.status == "ACTIVE"
            )
            .scalar()
            or 0
        )

        # ----------------------------------------------------
        # CURRENT MONTH FEES
        # ----------------------------------------------------

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
                ExtraClassMonthlyFee
                .extra_class_subject_id
                .in_(subject_ids),

                ExtraClassMonthlyFee.billing_month
                == current_month,

                ExtraClassMonthlyFee.status
                != "CANCELLED"
            )
            .scalar()
            or 0
        )

        # ----------------------------------------------------
        # CURRENT MONTH FEE RECORDS
        # ----------------------------------------------------

        current_fees = (
            ExtraClassMonthlyFee.query
            .filter(
                ExtraClassMonthlyFee
                .extra_class_subject_id
                .in_(subject_ids),

                ExtraClassMonthlyFee.billing_month
                == current_month,

                ExtraClassMonthlyFee.status
                != "CANCELLED"
            )
            .all()
        )

        # ----------------------------------------------------
        # PAYMENT AMOUNT APPLIED TO CURRENT MONTH FEES
        #
        # Only SUCCESS payments are counted.
        # ----------------------------------------------------

        for fee in current_fees:

            payment_items = (
                ExtraClassPaymentItem.query
                .join(
                    ExtraClassPayment,
                    ExtraClassPayment.id
                    == ExtraClassPaymentItem.payment_id
                )
                .filter(
                    ExtraClassPaymentItem.monthly_fee_id
                    == fee.id,

                    ExtraClassPayment.status
                    == "SUCCESS"
                )
                .all()
            )

            paid_for_fee = sum(
                float(item.amount or 0)
                for item in payment_items
            )

            current_month_paid += paid_for_fee

            current_month_outstanding += max(
                float(fee.amount_due or 0)
                - paid_for_fee,
                0
            )

        # ----------------------------------------------------
        # SUCCESSFUL PAYMENTS THIS MONTH
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

        if current_month.month == 12:

            next_month = date(
                current_month.year + 1,
                1,
                1
            )

        else:

            next_month = date(
                current_month.year,
                current_month.month + 1,
                1
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

        successful_payment_count = (
            db.session.query(
                db.func.count(
                    db.distinct(
                        ExtraClassPayment.id
                    )
                )
            )
            .join(
                ExtraClassPaymentItem,
                ExtraClassPayment.id
                == ExtraClassPaymentItem.payment_id
            )
            .join(
                ExtraClassMonthlyFee,
                ExtraClassMonthlyFee.id
                == ExtraClassPaymentItem.monthly_fee_id
            )
            .filter(
                ExtraClassPayment.status
                == "SUCCESS",

                ExtraClassPayment.paid_at
                >= month_start_datetime,

                ExtraClassPayment.paid_at
                < next_month_datetime,

                ExtraClassMonthlyFee
                .extra_class_subject_id
                .in_(subject_ids)
            )
            .scalar()
            or 0
        )

    # ========================================================
    # CURRENT SEMESTERS
    #
    # A semester is shown when it is attached to an active
    # enrollment belonging to one of this teacher's subjects.
    # ========================================================

    current_semesters = []

    if subject_ids:

        current_semesters = (
            db.session.query(
                ExtraClassTerm
            )
            .join(
                ExtraClassEnrollment,
                ExtraClassEnrollment.term_id
                == ExtraClassTerm.id
            )
            .join(
                ExtraClassSubject,
                ExtraClassSubject.id
                == ExtraClassEnrollment
                .extra_class_subject_id
            )
            .filter(
                ExtraClassSubject.teacher_id
                == teacher.id,

                ExtraClassEnrollment.status
                == "ACTIVE",

                ExtraClassEnrollment.term_id
                .isnot(None)
            )
            .distinct()
            .order_by(
                ExtraClassTerm.start_date.desc()
            )
            .all()
        )

    # --------------------------------------------------------
    # ONLY SHOW SEMESTERS CURRENTLY COVERING TODAY
    # --------------------------------------------------------

    today = date.today()

    active_semesters = [
        semester
        for semester in current_semesters
        if semester
        and semester.start_date <= today
        and semester.end_date >= today
        and semester.is_active
    ]

    # ========================================================
    # RECENT PAYMENTS
    # ========================================================

    recent_payments = []

    if subject_ids:

        recent_payments = (
            ExtraClassPayment.query
            .join(
                ExtraClassPaymentItem,
                ExtraClassPayment.id
                == ExtraClassPaymentItem.payment_id
            )
            .join(
                ExtraClassMonthlyFee,
                ExtraClassMonthlyFee.id
                == ExtraClassPaymentItem.monthly_fee_id
            )
            .filter(
                ExtraClassMonthlyFee
                .extra_class_subject_id
                .in_(subject_ids)
            )
            .order_by(
                ExtraClassPayment.created_at.desc()
            )
            .distinct()
            .limit(8)
            .all()
        )

    # ========================================================
    # CLASS SUMMARY
    # ========================================================

    class_summaries = []

    for extra_subject in assigned_subjects:

        class_student_count = (
            db.session.query(
                db.func.count(
                    db.distinct(
                        ExtraClassEnrollment.student_id
                    )
                )
            )
            .filter(
                ExtraClassEnrollment
                .extra_class_subject_id
                == extra_subject.id,

                ExtraClassEnrollment.status
                == "ACTIVE"
            )
            .scalar()
            or 0
        )

        class_summaries.append({
            "subject": extra_subject,
            "student_count": class_student_count
        })

    # ========================================================
    # CURRENT MONTH DISPLAY
    # ========================================================

    current_month_display = (
        current_month.strftime("%B %Y")
    )

    # ========================================================
    # RENDER
    # ========================================================

    return render_template(
        "extra_class_teacher_dashboard.html",

        teacher=teacher,

        assigned_subjects=assigned_subjects,

        class_summaries=class_summaries,

        total_students=total_students,

        active_enrollments=active_enrollments,

        current_month_fees=float(
            current_month_fees or 0
        ),

        current_month_paid=float(
            current_month_paid or 0
        ),

        current_month_outstanding=float(
            current_month_outstanding or 0
        ),

        successful_payment_count=
            successful_payment_count,

        current_month_display=
            current_month_display,

        active_semesters=
            active_semesters,

        recent_payments=
            recent_payments
    )
    
  
# ============================================================
# MAIN SIDEBAR NAVIGATION
# ============================================================

@extra_class_teacher_bp.route("/my-class", methods=["GET"])
@extra_class_teacher_required
def teacher_my_class():
    """Open the single class assigned to the logged-in teacher."""
    teacher_id = session.get("extra_class_teacher_id")

    extra_subject = (
        ExtraClassSubject.query
        .filter(
            ExtraClassSubject.teacher_id == teacher_id,
            ExtraClassSubject.is_active.is_(True)
        )
        .order_by(ExtraClassSubject.created_at.asc())
        .first()
    )

    if not extra_subject:
        flash("No active class is currently assigned to your teacher account.", "warning")
        return redirect(url_for("extra_class_teacher.teacher_dashboard"))

    return redirect(
        url_for("extra_class_teacher.view_class", class_id=extra_subject.id)
    )


@extra_class_teacher_bp.route("/my-students", methods=["GET"])
@extra_class_teacher_required
def teacher_my_students():
    """Open students for the teacher's single assigned class."""
    teacher_id = session.get("extra_class_teacher_id")

    extra_subject = (
        ExtraClassSubject.query
        .filter(
            ExtraClassSubject.teacher_id == teacher_id,
            ExtraClassSubject.is_active.is_(True)
        )
        .order_by(ExtraClassSubject.created_at.asc())
        .first()
    )

    if not extra_subject:
        flash("No active class is currently assigned to your teacher account.", "warning")
        return redirect(url_for("extra_class_teacher.teacher_dashboard"))

    return redirect(
        url_for("extra_class_teacher.class_students", class_id=extra_subject.id)
    )


@extra_class_teacher_bp.route("/fees-payments", methods=["GET"])
@extra_class_teacher_required
def teacher_fees_payments():
    """Open payment activity for the teacher's single assigned class."""
    teacher_id = session.get("extra_class_teacher_id")

    extra_subject = (
        ExtraClassSubject.query
        .filter(
            ExtraClassSubject.teacher_id == teacher_id,
            ExtraClassSubject.is_active.is_(True)
        )
        .order_by(ExtraClassSubject.created_at.asc())
        .first()
    )

    if not extra_subject:
        flash("No active class is currently assigned to your teacher account.", "warning")
        return redirect(url_for("extra_class_teacher.teacher_dashboard"))

    return redirect(
        url_for("extra_class_teacher.class_payments", class_id=extra_subject.id)
    )


@extra_class_teacher_bp.route("/semester", methods=["GET"])
@extra_class_teacher_required
def teacher_semester():
    """Temporary Semester landing page until semester management is completed."""
    return render_template(
        "extra_class_teacher_feature_coming_soon.html",
        feature_title="Semester",
        feature_icon="📅",
        feature_message="Semester management is the next teacher-portal feature to be completed."
    )


@extra_class_teacher_bp.route("/financial-reports", methods=["GET"])
@extra_class_teacher_required
def teacher_financial_reports():
    """Temporary Financial Reports landing page until reports are completed."""
    return render_template(
        "extra_class_teacher_feature_coming_soon.html",
        feature_title="Financial Reports",
        feature_icon="📊",
        feature_message="Financial reporting is planned for the teacher portal and will use the class fee and payment records already in the system."
    )


# ============================================================
# LEGACY MY CLASSES ROUTE
# ============================================================

@extra_class_teacher_bp.route("/classes", methods=["GET"])
@extra_class_teacher_required
def teacher_classes():
    """
    Legacy compatibility route.

    Each Extra Class Teacher is assigned to one subject/class, so there is
    no longer a class-selection page. Existing bookmarks or old template
    links to /classes are redirected to the teacher's single class.
    """
    return redirect(url_for("extra_class_teacher.teacher_my_class"))


# ============================================================
# VIEW CLASS
# ============================================================

@extra_class_teacher_bp.route(
    "/classes/<int:class_id>/view",
    methods=["GET"]
)
@extra_class_teacher_required
def view_class(class_id):
    """
    Read-only overview of one Extra Class.

    This page is intentionally separate from Manage Class:
    - View Class = class information, financial summary and quick links.
    - Manage Class = actions for Students, Semester, Fees, Payments and Reports.

    The class must belong to the logged-in teacher.
    """

    teacher_id = session.get("extra_class_teacher_id")

    # --------------------------------------------------------
    # VERIFY CLASS BELONGS TO THE LOGGED-IN TEACHER
    # --------------------------------------------------------

    extra_subject = (
        ExtraClassSubject.query
        .filter(
            ExtraClassSubject.id == class_id,
            ExtraClassSubject.teacher_id == teacher_id
        )
        .first_or_404()
    )

    teacher = (
        ExtraClassTeacher.query
        .filter_by(id=teacher_id)
        .first_or_404()
    )

    # --------------------------------------------------------
    # ACTIVE ENROLLMENTS
    # --------------------------------------------------------

    active_enrollments = (
        ExtraClassEnrollment.query
        .filter(
            ExtraClassEnrollment.extra_class_subject_id == class_id,
            ExtraClassEnrollment.status == "ACTIVE"
        )
        .all()
    )

    student_count = len({
        enrollment.student_id
        for enrollment in active_enrollments
    })

    enrollment_count = len(active_enrollments)

    # --------------------------------------------------------
    # CURRENT SEMESTER
    # --------------------------------------------------------

    today = date.today()

    current_semester = (
        db.session.query(ExtraClassTerm)
        .join(
            ExtraClassEnrollment,
            ExtraClassEnrollment.term_id == ExtraClassTerm.id
        )
        .filter(
            ExtraClassEnrollment.extra_class_subject_id == class_id,
            ExtraClassEnrollment.status == "ACTIVE",
            ExtraClassTerm.is_active.is_(True),
            ExtraClassTerm.start_date <= today,
            ExtraClassTerm.end_date >= today
        )
        .order_by(
            ExtraClassTerm.start_date.desc()
        )
        .first()
    )

    # --------------------------------------------------------
    # FINANCIAL SUMMARY
    # --------------------------------------------------------

    monthly_fees = (
        ExtraClassMonthlyFee.query
        .filter(
            ExtraClassMonthlyFee.extra_class_subject_id == class_id
        )
        .all()
    )

    total_fees = sum(
        float(fee.amount_due or 0)
        for fee in monthly_fees
        if str(fee.status or "").upper() != "CANCELLED"
    )

    paid_amount = (
        db.session.query(
            db.func.coalesce(
                db.func.sum(ExtraClassPaymentItem.amount),
                0
            )
        )
        .join(
            ExtraClassPayment,
            ExtraClassPayment.id == ExtraClassPaymentItem.payment_id
        )
        .filter(
            ExtraClassPaymentItem.extra_class_subject_id == class_id,
            ExtraClassPayment.status == "SUCCESS"
        )
        .scalar()
        or 0
    )

    pending_amount = (
        db.session.query(
            db.func.coalesce(
                db.func.sum(ExtraClassPaymentItem.amount),
                0
            )
        )
        .join(
            ExtraClassPayment,
            ExtraClassPayment.id == ExtraClassPaymentItem.payment_id
        )
        .filter(
            ExtraClassPaymentItem.extra_class_subject_id == class_id,
            ExtraClassPayment.status == "PENDING"
        )
        .scalar()
        or 0
    )

    outstanding = max(
        float(total_fees) - float(paid_amount),
        0.0
    )

    successful_payment_count = (
        db.session.query(
            db.func.count(
                db.distinct(ExtraClassPayment.id)
            )
        )
        .join(
            ExtraClassPaymentItem,
            ExtraClassPaymentItem.payment_id == ExtraClassPayment.id
        )
        .filter(
            ExtraClassPaymentItem.extra_class_subject_id == class_id,
            ExtraClassPayment.status == "SUCCESS"
        )
        .scalar()
        or 0
    )

    return render_template(
        "extra_class_teacher_class_view.html",
        teacher=teacher,
        extra_subject=extra_subject,
        student_count=student_count,
        enrollment_count=enrollment_count,
        current_semester=current_semester,
        total_fees=float(total_fees),
        paid_amount=float(paid_amount),
        pending_amount=float(pending_amount),
        outstanding=float(outstanding),
        successful_payment_count=successful_payment_count
    )


# ============================================================
# MANAGE CLASS
# ============================================================

@extra_class_teacher_bp.route(
    "/classes/<int:class_id>/manage",
    methods=["GET"]
)
@extra_class_teacher_required
def manage_class(class_id):

    teacher_id = session.get("extra_class_teacher_id")

    # --------------------------------------------------------
    # LOAD THE CLASS
    #
    # IMPORTANT:
    # The class must belong to the logged-in teacher.
    # --------------------------------------------------------

    extra_subject = (
        ExtraClassSubject.query
        .filter(
            ExtraClassSubject.id == class_id,
            ExtraClassSubject.teacher_id == teacher_id
        )
        .first_or_404()
    )

    # --------------------------------------------------------
    # LOAD ACTIVE ENROLLMENTS
    # --------------------------------------------------------

    active_enrollments = (
        ExtraClassEnrollment.query
        .filter(
            ExtraClassEnrollment.extra_class_subject_id
            == extra_subject.id,

            ExtraClassEnrollment.status == "ACTIVE"
        )
        .all()
    )

    # --------------------------------------------------------
    # STUDENT COUNT
    # --------------------------------------------------------

    student_count = (
        db.session.query(
            db.func.count(
                db.distinct(
                    ExtraClassEnrollment.student_id
                )
            )
        )
        .filter(
            ExtraClassEnrollment.extra_class_subject_id
            == extra_subject.id,

            ExtraClassEnrollment.status == "ACTIVE"
        )
        .scalar()
        or 0
    )

    # --------------------------------------------------------
    # ENROLLMENT COUNT
    # --------------------------------------------------------

    enrollment_count = len(active_enrollments)

    # --------------------------------------------------------
    # LOAD SEMESTERS FOR THIS CLASS
    # --------------------------------------------------------

    semesters = (
        ExtraClassTerm.query
        .join(
            ExtraClassEnrollment,
            ExtraClassEnrollment.term_id
            == ExtraClassTerm.id
        )
        .filter(
            ExtraClassEnrollment
            .extra_class_subject_id
            == extra_subject.id
        )
        .distinct()
        .order_by(
            ExtraClassTerm.start_date.desc()
        )
        .all()
    )

    # --------------------------------------------------------
    # CURRENT SEMESTER
    # --------------------------------------------------------

    today = date.today()

    current_semester = None

    for semester in semesters:

        if (
            semester.is_active
            and semester.start_date <= today
            and semester.end_date >= today
        ):
            current_semester = semester
            break

    return render_template(
        "extra_class_teacher_manage_class.html",

        teacher=(
            ExtraClassTeacher.query
            .filter_by(id=teacher_id)
            .first_or_404()
        ),

        extra_subject=extra_subject,

        student_count=student_count,

        enrollment_count=enrollment_count,

        semesters=semesters,

        current_semester=current_semester
    )    
  
  
  
@extra_class_teacher_bp.route(
    "/classes/<int:class_id>/students/add",
    methods=["GET", "POST"]
)
@extra_class_teacher_required
def add_class_student(class_id):
    """
    Add / identify a student for a teacher's class.

    Responsibilities:
    - Create or identify the student.
    - Create or identify the parent/guardian.
    - Link the parent/guardian to the student.
    - Do NOT create an enrollment here.
    - Enrollment remains handled by the separate enrollment route.
    """

    teacher_id = session.get("extra_class_teacher_id")

    # ---------------------------------------------------------
    # 1. Verify class belongs to logged-in teacher
    # ---------------------------------------------------------
    extra_subject = (
        ExtraClassSubject.query
        .filter(
            ExtraClassSubject.id == class_id,
            ExtraClassSubject.teacher_id == teacher_id,
            ExtraClassSubject.is_active.is_(True)
        )
        .first_or_404()
    )

    # ---------------------------------------------------------
    # 2. GET
    # ---------------------------------------------------------
    if request.method == "GET":
        return render_template(
            "extra_class_teacher_add_student.html",
            extra_subject=extra_subject,
            form_data={}
        )

    # ---------------------------------------------------------
    # 3. POST
    # ---------------------------------------------------------
    action = request.form.get("action", "check_student").strip()

    # =========================================================
    # STUDENT INFORMATION
    # =========================================================

    first_name = request.form.get("first_name", "").strip()
    surname = request.form.get("surname", "").strip()
    other_name = request.form.get("other_name", "").strip()
    school = request.form.get("school", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()

    # =========================================================
    # PARENT / GUARDIAN INFORMATION
    # =========================================================

    parent_first_name = request.form.get("parent_first_name", "").strip()
    parent_surname = request.form.get("parent_surname", "").strip()
    parent_phone = request.form.get("parent_phone", "").strip()
    parent_email = request.form.get("parent_email", "").strip()
    parent_relationship = request.form.get("parent_relationship", "").strip()
    parent_is_primary = request.form.get("parent_is_primary") == "1"

    form_data = {
        "first_name": first_name,
        "surname": surname,
        "other_name": other_name,
        "school": school,
        "phone": phone,
        "email": email,
        "parent_first_name": parent_first_name,
        "parent_surname": parent_surname,
        "parent_phone": parent_phone,
        "parent_email": parent_email,
        "parent_relationship": parent_relationship,
        "parent_is_primary": parent_is_primary,
    }

    # =========================================================
    # 4. BASIC STUDENT VALIDATION
    # =========================================================

    if not first_name:
        flash("Student first name is required.", "danger")
        return render_template(
            "extra_class_teacher_add_student.html",
            extra_subject=extra_subject,
            form_data=form_data
        )

    if not surname:
        flash("Student surname is required.", "danger")
        return render_template(
            "extra_class_teacher_add_student.html",
            extra_subject=extra_subject,
            form_data=form_data
        )

    # =========================================================
    # 5. PARENT VALIDATION
    # =========================================================

    if not parent_first_name:
        flash("Parent/guardian first name is required.", "danger")
        return render_template(
            "extra_class_teacher_add_student.html",
            extra_subject=extra_subject,
            form_data=form_data
        )

    if not parent_surname:
        flash("Parent/guardian surname is required.", "danger")
        return render_template(
            "extra_class_teacher_add_student.html",
            extra_subject=extra_subject,
            form_data=form_data
        )

    if not parent_phone:
        flash("Parent/guardian phone number is required.", "danger")
        return render_template(
            "extra_class_teacher_add_student.html",
            extra_subject=extra_subject,
            form_data=form_data
        )

    if not parent_relationship:
        flash(
            "Please select the parent's relationship to the student.",
            "danger"
        )
        return render_template(
            "extra_class_teacher_add_student.html",
            extra_subject=extra_subject,
            form_data=form_data
        )

    # =========================================================
    # HELPER: FIND / CREATE PARENT AND LINK TO STUDENT
    # =========================================================

    def attach_parent_to_student(student):
        """
        Find an existing parent by phone number or create a new
        parent, then create/update the student-parent relationship.
        """

        parent = (
            ExtraClassParent.query
            .filter(ExtraClassParent.phone == parent_phone)
            .first()
        )

        # -----------------------------------------------------
        # Existing parent
        # -----------------------------------------------------
        if parent:

            if not parent.is_active:
                raise ValueError(
                    "A parent/guardian with this phone number already "
                    "exists but is inactive. Please contact an administrator."
                )

            existing_link = (
                ExtraClassStudentParent.query
                .filter(
                    ExtraClassStudentParent.student_id == student.id,
                    ExtraClassStudentParent.parent_id == parent.id
                )
                .first()
            )

            if existing_link:
                existing_link.relationship = parent_relationship

                if parent_is_primary:
                    existing_link.is_primary = True

                    (
                        ExtraClassStudentParent.query
                        .filter(
                            ExtraClassStudentParent.student_id == student.id,
                            ExtraClassStudentParent.id != existing_link.id
                        )
                        .update(
                            {"is_primary": False},
                            synchronize_session=False
                        )
                    )

                return parent, existing_link, False

            # This parent already exists but is not linked to this student.
            if parent_is_primary:
                (
                    ExtraClassStudentParent.query
                    .filter(
                        ExtraClassStudentParent.student_id == student.id
                    )
                    .update(
                        {"is_primary": False},
                        synchronize_session=False
                    )
                )

            link = ExtraClassStudentParent(
                student_id=student.id,
                parent_id=parent.id,
                relationship=parent_relationship,
                is_primary=parent_is_primary
            )

            db.session.add(link)
            return parent, link, False

        # -----------------------------------------------------
        # No parent found. Create one.
        # -----------------------------------------------------
        parent = ExtraClassParent(
            first_name=parent_first_name,
            surname=parent_surname,
            phone=parent_phone,
            email=parent_email or None,
            is_active=True
        )

        db.session.add(parent)
        db.session.flush()

        link = ExtraClassStudentParent(
            student_id=student.id,
            parent_id=parent.id,
            relationship=parent_relationship,
            is_primary=parent_is_primary
        )

        db.session.add(link)
        return parent, link, True

    # =========================================================
    # 6. CREATE NEW STUDENT
    # =========================================================

    if action == "create_new":

        existing_query = (
            ExtraClassStudent.query
            .filter(
                db.func.lower(ExtraClassStudent.first_name) == first_name.lower(),
                db.func.lower(ExtraClassStudent.surname) == surname.lower()
            )
        )

        if school:
            existing_query = existing_query.filter(
                db.func.lower(ExtraClassStudent.school) == school.lower()
            )

        if other_name:
            existing_query = existing_query.filter(
                db.func.lower(ExtraClassStudent.other_name) == other_name.lower()
            )

        existing_student = existing_query.first()

        if existing_student:
            flash(
                f"Student already exists with code {existing_student.student_code}.",
                "warning"
            )
            return redirect(
                url_for(
                    "extra_class_teacher.enroll_class_student",
                    class_id=extra_subject.id,
                    student_id=existing_student.id
                )
            )

        try:
            import secrets

            temporary_code = f"TEMP-{secrets.token_hex(12).upper()}"

            student = ExtraClassStudent(
                student_code=temporary_code,
                first_name=first_name,
                surname=surname,
                other_name=other_name or None,
                school=school or None,
                phone=phone or None,
                email=email or None,
                is_active=True
            )

            db.session.add(student)
            db.session.flush()

            generated_code = f"BTA-{student.id:06d}"

            code_exists = (
                ExtraClassStudent.query
                .filter(
                    ExtraClassStudent.student_code == generated_code,
                    ExtraClassStudent.id != student.id
                )
                .first()
            )

            if code_exists:
                raise ValueError(
                    f"Generated student code {generated_code} already exists."
                )

            student.student_code = generated_code

            parent, parent_link, parent_created = attach_parent_to_student(student)

            # Student + parent + relationship are committed together.
            db.session.commit()

            if parent_created:
                flash(
                    f"Student created successfully. Student Code: "
                    f"{student.student_code}. Parent/guardian was also registered.",
                    "success"
                )
            else:
                flash(
                    f"Student created successfully. Student Code: "
                    f"{student.student_code}. Existing parent/guardian was linked.",
                    "success"
                )

            return redirect(
                url_for(
                    "extra_class_teacher.enroll_class_student",
                    class_id=extra_subject.id,
                    student_id=student.id
                )
            )

        except Exception as exc:
            db.session.rollback()
            flash(
                f"Unable to create student: {str(exc)}",
                "danger"
            )
            return render_template(
                "extra_class_teacher_add_student.html",
                extra_subject=extra_subject,
                form_data=form_data
            )

    # =========================================================
    # 7. EXISTING STUDENT SEARCH
    # =========================================================

    if action == "check_student":

        query = (
            ExtraClassStudent.query
            .filter(
                db.func.lower(ExtraClassStudent.first_name) == first_name.lower(),
                db.func.lower(ExtraClassStudent.surname) == surname.lower()
            )
        )

        if school:
            query = query.filter(
                db.func.lower(ExtraClassStudent.school) == school.lower()
            )

        if other_name:
            query = query.filter(
                db.func.lower(ExtraClassStudent.other_name) == other_name.lower()
            )

        matching_students = (
            query
            .order_by(ExtraClassStudent.first_name.asc())
            .all()
        )

        if matching_students:

            # IMPORTANT:
            # Do not immediately redirect when there is exactly one match.
            # The teacher must be allowed to confirm/add the parent first.
            if len(matching_students) == 1:
                student = matching_students[0]

                flash(
                    f"Student found: {student.student_code}. "
                    "Please review the parent information and continue.",
                    "success"
                )

                return render_template(
                    "extra_class_teacher_add_student.html",
                    extra_subject=extra_subject,
                    form_data=form_data,
                    matching_students=[student],
                    student_found=True
                )

            return render_template(
                "extra_class_teacher_add_student.html",
                extra_subject=extra_subject,
                form_data=form_data,
                matching_students=matching_students,
                student_found=True
            )

        return render_template(
            "extra_class_teacher_add_student.html",
            extra_subject=extra_subject,
            form_data=form_data,
            matching_students=[],
            student_found=False,
            no_match=True
        )

    # =========================================================
    # 8. EXISTING STUDENT SELECTED
    # =========================================================

    if action == "enroll_existing":

        student_id = request.form.get("student_id", type=int)

        if not student_id:
            flash("Invalid student selected.", "danger")
            return redirect(
                url_for(
                    "extra_class_teacher.add_class_student",
                    class_id=extra_subject.id
                )
            )

        student = (
            ExtraClassStudent.query
            .filter_by(id=student_id)
            .first()
        )

        if not student:
            flash("Student could not be found.", "danger")
            return redirect(
                url_for(
                    "extra_class_teacher.add_class_student",
                    class_id=extra_subject.id
                )
            )

        try:
            parent, parent_link, parent_created = attach_parent_to_student(student)

            db.session.commit()

            if parent_created:
                flash(
                    "Parent/guardian was registered and linked to the student.",
                    "success"
                )
            else:
                flash(
                    "Parent/guardian was linked to the student.",
                    "success"
                )

            return redirect(
                url_for(
                    "extra_class_teacher.enroll_class_student",
                    class_id=extra_subject.id,
                    student_id=student.id
                )
            )

        except Exception as exc:
            db.session.rollback()
            flash(
                f"Unable to save parent/guardian: {str(exc)}",
                "danger"
            )
            return redirect(
                url_for(
                    "extra_class_teacher.add_class_student",
                    class_id=extra_subject.id
                )
            )

    # =========================================================
    # 9. UNKNOWN ACTION
    # =========================================================

    flash("Invalid student action.", "danger")

    return redirect(
        url_for(
            "extra_class_teacher.add_class_student",
            class_id=extra_subject.id
        )
    )
    
    

#========================================================
# ENROLL STUDENT IN EXTRA CLASS
# ========================================================    
    
    
@extra_class_teacher_bp.route(
    "/classes/<int:class_id>/students/<int:student_id>/enroll",
    methods=["GET", "POST"]
)
@extra_class_teacher_required
def enroll_class_student(class_id, student_id):
    """
    Enroll an existing student into the teacher's class.

    The student must already exist.

    Enrollment-specific information:
        - Semester
        - Form
        - Class
        - Start Date

    Subject and teacher are determined automatically from class_id
    and the logged-in teacher.
    """

    teacher_id = session.get("extra_class_teacher_id")

    # ---------------------------------------------------------
    # 1. Verify that this class belongs to the logged-in teacher
    # ---------------------------------------------------------
    extra_subject = (
        ExtraClassSubject.query
        .filter(
            ExtraClassSubject.id == class_id,
            ExtraClassSubject.teacher_id == teacher_id,
            ExtraClassSubject.is_active.is_(True)
        )
        .first_or_404()
    )

    # ---------------------------------------------------------
    # 2. Find the student
    # ---------------------------------------------------------
    student = (
        ExtraClassStudent.query
        .filter_by(id=student_id)
        .first_or_404()
    )

    # ---------------------------------------------------------
    # 3. Load active semesters
    # ---------------------------------------------------------
    semesters = (
        ExtraClassTerm.query
        .filter(
            ExtraClassTerm.is_active.is_(True)
        )
        .order_by(
            ExtraClassTerm.start_date.desc()
        )
        .all()
    )

    # ---------------------------------------------------------
    # 4. Check whether this student already has an enrollment
    #    for this teacher's subject/class.
    #
    #    Because of the unique constraint:
    #
    #    (student_id, extra_class_subject_id)
    #
    #    we must reuse the existing enrollment.
    # ---------------------------------------------------------
    existing_enrollment = (
        ExtraClassEnrollment.query
        .filter(
            ExtraClassEnrollment.student_id == student.id,
            ExtraClassEnrollment.extra_class_subject_id
            == extra_subject.id
        )
        .first()
    )

    # ---------------------------------------------------------
    # 5. GET
    # ---------------------------------------------------------
    if request.method == "GET":

        # If already actively enrolled, don't allow another
        # active enrollment to be created.
        if (
            existing_enrollment
            and existing_enrollment.status == "ACTIVE"
        ):
            flash(
                "This student is already enrolled in this class.",
                "warning"
            )

            return redirect(
                url_for(
                    "extra_class_teacher.view_class_student",
                    class_id=extra_subject.id,
                    student_id=student.id
                )
            )

        return render_template(
            "extra_class_teacher_enroll_student.html",
            extra_subject=extra_subject,
            student=student,
            semesters=semesters,
            existing_enrollment=existing_enrollment,
            form_data={}
        )

    # ---------------------------------------------------------
    # 6. POST
    # ---------------------------------------------------------
    term_id = request.form.get("term_id", type=int)
    form = request.form.get("form", "").strip().upper()
    class_name = request.form.get("class_name", "").strip()
    start_date_string = request.form.get("start_date", "").strip()

    form_data = {
        "term_id": term_id,
        "form": form,
        "class_name": class_name,
        "start_date": start_date_string,
    }

    # ---------------------------------------------------------
    # 7. Validate semester
    # ---------------------------------------------------------
    if not term_id:
        flash("Please select a semester.", "danger")

        return render_template(
            "extra_class_teacher_enroll_student.html",
            extra_subject=extra_subject,
            student=student,
            semesters=semesters,
            existing_enrollment=existing_enrollment,
            form_data=form_data
        )

    semester = (
        ExtraClassTerm.query
        .filter(
            ExtraClassTerm.id == term_id,
            ExtraClassTerm.is_active.is_(True)
        )
        .first()
    )

    if not semester:
        flash(
            "The selected semester is not available.",
            "danger"
        )

        return render_template(
            "extra_class_teacher_enroll_student.html",
            extra_subject=extra_subject,
            student=student,
            semesters=semesters,
            existing_enrollment=existing_enrollment,
            form_data=form_data
        )

    # ---------------------------------------------------------
    # 8. Validate Form
    # ---------------------------------------------------------
    allowed_forms = {
        "FORM 1",
        "FORM 2",
        "FORM 3"
    }

    if form not in allowed_forms:
        flash(
            "Please select a valid form.",
            "danger"
        )

        return render_template(
            "extra_class_teacher_enroll_student.html",
            extra_subject=extra_subject,
            student=student,
            semesters=semesters,
            existing_enrollment=existing_enrollment,
            form_data=form_data
        )

    # ---------------------------------------------------------
    # 9. Validate class
    # ---------------------------------------------------------
    if not class_name:
        flash(
            "Please enter the student's class.",
            "danger"
        )

        return render_template(
            "extra_class_teacher_enroll_student.html",
            extra_subject=extra_subject,
            student=student,
            semesters=semesters,
            existing_enrollment=existing_enrollment,
            form_data=form_data
        )

    # ---------------------------------------------------------
    # 10. Validate start date
    # ---------------------------------------------------------
    if not start_date_string:
        flash(
            "Please select a start date.",
            "danger"
        )

        return render_template(
            "extra_class_teacher_enroll_student.html",
            extra_subject=extra_subject,
            student=student,
            semesters=semesters,
            existing_enrollment=existing_enrollment,
            form_data=form_data
        )

    try:
        start_date = datetime.strptime(
            start_date_string,
            "%Y-%m-%d"
        ).date()

    except ValueError:
        flash(
            "Please enter a valid start date.",
            "danger"
        )

        return render_template(
            "extra_class_teacher_enroll_student.html",
            extra_subject=extra_subject,
            student=student,
            semesters=semesters,
            existing_enrollment=existing_enrollment,
            form_data=form_data
        )

    # ---------------------------------------------------------
    # 11. Make sure start date falls within the semester
    # ---------------------------------------------------------
    if start_date < semester.start_date:
        flash(
            "The start date cannot be before the semester begins.",
            "danger"
        )

        return render_template(
            "extra_class_teacher_enroll_student.html",
            extra_subject=extra_subject,
            student=student,
            semesters=semesters,
            existing_enrollment=existing_enrollment,
            form_data=form_data
        )

    if start_date > semester.end_date:
        flash(
            "The start date cannot be after the semester ends.",
            "danger"
        )

        return render_template(
            "extra_class_teacher_enroll_student.html",
            extra_subject=extra_subject,
            student=student,
            semesters=semesters,
            existing_enrollment=existing_enrollment,
            form_data=form_data
        )

    # ---------------------------------------------------------
    # 12. Re-check existing enrollment immediately before
    #     writing to the database.
    # ---------------------------------------------------------
    existing_enrollment = (
        ExtraClassEnrollment.query
        .filter(
            ExtraClassEnrollment.student_id == student.id,
            ExtraClassEnrollment.extra_class_subject_id
            == extra_subject.id
        )
        .first()
    )

    # ---------------------------------------------------------
    # 13. If an ACTIVE enrollment appeared, stop.
    # ---------------------------------------------------------
    if (
        existing_enrollment
        and existing_enrollment.status == "ACTIVE"
    ):
        flash(
            "This student is already enrolled in this class.",
            "warning"
        )

        return redirect(
            url_for(
                "extra_class_teacher.view_class_student",
                class_id=extra_subject.id,
                student_id=student.id
            )
        )

    try:
        # -----------------------------------------------------
        # 14. Reactivate existing enrollment
        # -----------------------------------------------------
        if existing_enrollment:

            existing_enrollment.term_id = semester.id
            existing_enrollment.form = form
            existing_enrollment.class_name = class_name
            existing_enrollment.start_date = start_date
            existing_enrollment.end_date = semester.end_date
            existing_enrollment.status = "ACTIVE"

            enrollment = existing_enrollment

        # -----------------------------------------------------
        # 15. Create new enrollment
        # -----------------------------------------------------
        else:

            enrollment = ExtraClassEnrollment(
                student_id=student.id,
                extra_class_subject_id=extra_subject.id,
                term_id=semester.id,
                form=form,
                class_name=class_name,
                start_date=start_date,
                end_date=semester.end_date,
                status="ACTIVE"
            )

            db.session.add(enrollment)

        # Make sure the student is active.
        student.is_active = True

        # Obtain the enrollment ID before creating its fee records.
        db.session.flush()

        # Generate monthly fees. Existing records are detected and
        # are not duplicated or overwritten.
        created_fee_count, existing_fee_count = (
            generate_enrollment_monthly_fees(enrollment)
        )

        db.session.commit()

        flash(
            f"{student.first_name} {student.surname} "
            "has been enrolled successfully. "
            f"{created_fee_count} monthly fee record(s) generated.",
            "success"
        )

        return redirect(
            url_for(
                "extra_class_teacher.view_class_student",
                class_id=extra_subject.id,
                student_id=student.id
            )
        )

    except Exception as exc:

        db.session.rollback()

        flash(
            f"Unable to save enrollment: {str(exc)}",
            "danger"
        )

        return render_template(
            "extra_class_teacher_enroll_student.html",
            extra_subject=extra_subject,
            student=student,
            semesters=semesters,
            existing_enrollment=existing_enrollment,
            form_data=form_data
        )   
  
  
  
  
# ========================================================
# VIEW EXTRA CLASS STUDENTS
# ========================================================
    
    
@extra_class_teacher_bp.route(
    "/classes/<int:class_id>/students",
    methods=["GET"]
)
@extra_class_teacher_required
def class_students(class_id):

    teacher_id = session.get("extra_class_teacher_id")

    # ---------------------------------------------------------
    # VERIFY CLASS BELONGS TO LOGGED-IN TEACHER
    # ---------------------------------------------------------
    extra_subject = (
        ExtraClassSubject.query
        .filter(
            ExtraClassSubject.id == class_id,
            ExtraClassSubject.teacher_id == teacher_id
        )
        .first_or_404()
    )

    # ---------------------------------------------------------
    # ACTIVE ENROLLMENTS
    # ---------------------------------------------------------
    active_enrollments = (
        ExtraClassEnrollment.query
        .filter(
            ExtraClassEnrollment.extra_class_subject_id == extra_subject.id,
            ExtraClassEnrollment.status == "ACTIVE"
        )
        .order_by(
            ExtraClassEnrollment.created_at.desc()
        )
        .all()
    )

    students = []

    for enrollment in active_enrollments:

        student = enrollment.student

        if not student:
            continue

        # Calculate outstanding balance
        outstanding = calculate_enrollment_outstanding(
            enrollment.id
        )

        students.append({
            "student": student,
            "enrollment": enrollment,
            "outstanding": float(outstanding)
        })

    # ---------------------------------------------------------
    # INACTIVE ENROLLMENTS
    # ---------------------------------------------------------
    inactive_enrollments = (
        ExtraClassEnrollment.query
        .filter(
            ExtraClassEnrollment.extra_class_subject_id == extra_subject.id,
            ExtraClassEnrollment.status == "INACTIVE"
        )
        .order_by(
            ExtraClassEnrollment.updated_at.desc()
        )
        .all()
    )

    inactive_students = []

    for enrollment in inactive_enrollments:

        student = enrollment.student

        if not student:
            continue

        inactive_students.append({
            "student": student,
            "enrollment": enrollment
        })

    # ---------------------------------------------------------
    # TEACHER
    # ---------------------------------------------------------
    teacher = (
        ExtraClassTeacher.query
        .filter_by(id=teacher_id)
        .first_or_404()
    )

    # ---------------------------------------------------------
    # RENDER
    # ---------------------------------------------------------
    return render_template(
        "extra_class_teacher_class_students.html",
        teacher=teacher,
        extra_subject=extra_subject,
        students=students,
        inactive_students=inactive_students
    )           
    
    
    
    
# ============================================================
# VIEW INDIVIDUAL STUDENT
# ============================================================


@extra_class_teacher_bp.route(
    "/classes/<int:class_id>/students/<int:student_id>",
    methods=["GET"]
)
@extra_class_teacher_required
def view_class_student(class_id, student_id):

    teacher_id = session.get("extra_class_teacher_id")

    # ========================================================
    # VERIFY THAT THE CLASS BELONGS TO THE LOGGED-IN TEACHER
    # ========================================================

    extra_subject = (
        ExtraClassSubject.query
        .filter(
            ExtraClassSubject.id == class_id,
            ExtraClassSubject.teacher_id == teacher_id
        )
        .first_or_404()
    )

    # ========================================================
    # VERIFY THAT THE STUDENT BELONGS TO THIS CLASS
    # ========================================================

    enrollment = (
        ExtraClassEnrollment.query
        .filter(
            ExtraClassEnrollment.extra_class_subject_id
            == extra_subject.id,

            ExtraClassEnrollment.student_id
            == student_id
        )
        .first_or_404()
    )

    # ========================================================
    # GET STUDENT
    # ========================================================

    student = (
        ExtraClassStudent.query
        .filter(
            ExtraClassStudent.id == student_id
        )
        .first_or_404()
    )

    # ========================================================
    # GET TEACHER
    # ========================================================

    teacher = (
        ExtraClassTeacher.query
        .filter_by(id=teacher_id)
        .first_or_404()
    )

    # ========================================================
    # GET PARENTS / GUARDIANS
    # ========================================================

    parent_links = (
        ExtraClassStudentParent.query
        .filter(
            ExtraClassStudentParent.student_id == student.id
        )
        .order_by(
            ExtraClassStudentParent.is_primary.desc(),
            ExtraClassStudentParent.created_at.asc()
        )
        .all()
    )

    # ========================================================
    # MONTHLY FEES
    # ========================================================

    monthly_fees = (
        ExtraClassMonthlyFee.query
        .filter(
            ExtraClassMonthlyFee.enrollment_id
            == enrollment.id
        )
        .order_by(
            ExtraClassMonthlyFee.billing_month.asc()
        )
        .all()
    )

    fee_rows = []

    total_fees = 0.0
    total_paid = 0.0

    # ========================================================
    # CALCULATE ACTUAL PAID AMOUNTS
    # ========================================================

    for fee in monthly_fees:

        payment_items = (
            ExtraClassPaymentItem.query
            .join(
                ExtraClassPayment,
                ExtraClassPayment.id
                == ExtraClassPaymentItem.payment_id
            )
            .filter(
                ExtraClassPaymentItem.monthly_fee_id == fee.id,
                ExtraClassPayment.status == "SUCCESS"
            )
            .all()
        )

        paid_amount = sum(
            float(item.amount or 0)
            for item in payment_items
        )

        amount_due = float(
            fee.amount_due or 0
        )

        balance = max(
            amount_due - paid_amount,
            0.0
        )

        fee_status = str(
            fee.status or "UNPAID"
        ).upper()

        if fee_status == "CANCELLED":

            display_status = "CANCELLED"

        elif balance <= 0 and amount_due > 0:

            display_status = "PAID"

        elif paid_amount > 0:

            display_status = "PARTIAL"

        else:

            display_status = fee_status

        fee_rows.append({
            "billing_month": fee.billing_month,
            "amount_due": amount_due,
            "paid_amount": paid_amount,
            "balance": balance,
            "status": display_status
        })

        if display_status != "CANCELLED":

            total_fees += amount_due
            total_paid += paid_amount

    # ========================================================
    # TOTAL OUTSTANDING
    # ========================================================

    total_outstanding = max(
        total_fees - total_paid,
        0.0
    )

    # ========================================================
    # RENDER STUDENT PROFILE
    # ========================================================

    return render_template(
        "extra_class_teacher_view_student.html",

        teacher=teacher,

        extra_subject=extra_subject,

        student=student,

        enrollment=enrollment,

        # Parent information
        parent_links=parent_links,

        # Financial information
        fee_rows=fee_rows,

        total_fees=total_fees,

        total_paid=total_paid,

        total_outstanding=total_outstanding
    )
    
    
    
# ============================================================
# ADD PARENT / GUARDIAN TO EXISTING STUDENT
# ============================================================

@extra_class_teacher_bp.route(
    "/classes/<int:class_id>/students/<int:student_id>/parents/add",
    methods=["GET", "POST"]
)
@extra_class_teacher_required
def add_student_parent(class_id, student_id):
    """Add a parent/guardian to an existing student."""

    teacher_id = session.get("extra_class_teacher_id")

    extra_subject = (
        ExtraClassSubject.query
        .filter(
            ExtraClassSubject.id == class_id,
            ExtraClassSubject.teacher_id == teacher_id
        )
        .first_or_404()
    )

    enrollment = (
        ExtraClassEnrollment.query
        .filter(
            ExtraClassEnrollment.extra_class_subject_id == extra_subject.id,
            ExtraClassEnrollment.student_id == student_id
        )
        .first_or_404()
    )

    student = (
        ExtraClassStudent.query
        .filter(ExtraClassStudent.id == student_id)
        .first_or_404()
    )

    teacher = (
        ExtraClassTeacher.query
        .filter_by(id=teacher_id)
        .first_or_404()
    )

    if request.method == "GET":
        return render_template(
            "extra_class_teacher_add_parent.html",
            teacher=teacher,
            extra_subject=extra_subject,
            student=student,
            enrollment=enrollment,
            form_data={}
        )

    first_name = request.form.get("first_name", "").strip()
    surname = request.form.get("surname", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()
    relationship = request.form.get("relationship", "").strip()
    is_primary = request.form.get("is_primary") == "1"

    form_data = {
        "first_name": first_name,
        "surname": surname,
        "phone": phone,
        "email": email,
        "relationship": relationship,
        "is_primary": is_primary,
    }

    def render_error(message):
        flash(message, "danger")
        return render_template(
            "extra_class_teacher_add_parent.html",
            teacher=teacher,
            extra_subject=extra_subject,
            student=student,
            enrollment=enrollment,
            form_data=form_data
        )

    if not first_name:
        return render_error("Parent/guardian first name is required.")

    if not surname:
        return render_error("Parent/guardian surname is required.")

    if not phone:
        return render_error("Parent/guardian phone number is required.")

    if not relationship:
        return render_error(
            "Please select the parent's relationship to the student."
        )

    try:
        parent = (
            ExtraClassParent.query
            .filter(ExtraClassParent.phone == phone)
            .first()
        )

        if parent:
            if not parent.is_active:
                raise ValueError(
                    "A parent/guardian with this phone number already exists "
                    "but is inactive. Please contact an administrator."
                )

            existing_link = (
                ExtraClassStudentParent.query
                .filter(
                    ExtraClassStudentParent.student_id == student.id,
                    ExtraClassStudentParent.parent_id == parent.id
                )
                .first()
            )

            if existing_link:
                flash(
                    "This parent/guardian is already linked to this student.",
                    "warning"
                )
                return redirect(
                    url_for(
                        "extra_class_teacher.view_class_student",
                        class_id=extra_subject.id,
                        student_id=student.id
                    )
                )

        else:
            parent = ExtraClassParent(
                first_name=first_name,
                surname=surname,
                phone=phone,
                email=email or None,
                is_active=True
            )
            db.session.add(parent)
            db.session.flush()

        if is_primary:
            (
                ExtraClassStudentParent.query
                .filter(
                    ExtraClassStudentParent.student_id == student.id
                )
                .update(
                    {"is_primary": False},
                    synchronize_session=False
                )
            )

        parent_link = ExtraClassStudentParent(
            student_id=student.id,
            parent_id=parent.id,
            relationship=relationship,
            is_primary=is_primary
        )

        db.session.add(parent_link)
        db.session.commit()

        flash(
            f"{parent.first_name} {parent.surname} has been linked to "
            f"{student.first_name} {student.surname} successfully.",
            "success"
        )

        return redirect(
            url_for(
                "extra_class_teacher.view_class_student",
                class_id=extra_subject.id,
                student_id=student.id
            )
        )

    except Exception as exc:
        db.session.rollback()
        return render_error(
            f"Unable to add parent/guardian: {str(exc)}"
        )


# ============================================================
# EDIT STUDENT
# ============================================================

@extra_class_teacher_bp.route(
    "/classes/<int:class_id>/students/<int:student_id>/edit",
    methods=["GET", "POST"]
)
@extra_class_teacher_required
def edit_class_student(class_id, student_id):

    teacher_id = session.get("extra_class_teacher_id")

    # The class must belong to the logged-in teacher.
    extra_subject = (
        ExtraClassSubject.query
        .filter(
            ExtraClassSubject.id == class_id,
            ExtraClassSubject.teacher_id == teacher_id
        )
        .first_or_404()
    )

    # The student must belong to this teacher's class.
    enrollment = (
        ExtraClassEnrollment.query
        .filter(
            ExtraClassEnrollment.extra_class_subject_id == extra_subject.id,
            ExtraClassEnrollment.student_id == student_id
        )
        .first_or_404()
    )

    student = (
        ExtraClassStudent.query
        .filter(ExtraClassStudent.id == student_id)
        .first_or_404()
    )

    teacher = (
        ExtraClassTeacher.query
        .filter_by(id=teacher_id)
        .first_or_404()
    )

    if request.method == "GET":
        return render_template(
            "extra_class_teacher_edit_student.html",
            teacher=teacher,
            extra_subject=extra_subject,
            student=student,
            enrollment=enrollment
        )

    first_name = request.form.get("first_name", "").strip()
    surname = request.form.get("surname", "").strip()
    other_name = request.form.get("other_name", "").strip()
    school = request.form.get("school", "").strip()
    phone = request.form.get("phone", "").strip()
    email = request.form.get("email", "").strip()

    if not first_name:
        flash("First name is required.", "danger")
        return render_template(
            "extra_class_teacher_edit_student.html",
            teacher=teacher,
            extra_subject=extra_subject,
            student=student,
            enrollment=enrollment,
            form_data=request.form
        )

    if not surname:
        flash("Surname is required.", "danger")
        return render_template(
            "extra_class_teacher_edit_student.html",
            teacher=teacher,
            extra_subject=extra_subject,
            student=student,
            enrollment=enrollment,
            form_data=request.form
        )

    try:
        # Student code is intentionally NOT editable.
        student.first_name = first_name
        student.surname = surname
        student.other_name = other_name or None
        student.school = school or None
        student.phone = phone or None
        student.email = email or None

        db.session.commit()

        flash(
            f"{student.first_name} {student.surname}'s details were updated successfully.",
            "success"
        )

        return redirect(
            url_for(
                "extra_class_teacher.view_class_student",
                class_id=extra_subject.id,
                student_id=student.id
            )
        )

    except Exception as exc:
        db.session.rollback()

        flash(
            f"Unable to update student: {str(exc)}",
            "danger"
        )

        return render_template(
            "extra_class_teacher_edit_student.html",
            teacher=teacher,
            extra_subject=extra_subject,
            student=student,
            enrollment=enrollment,
            form_data=request.form
        )



    
# ============================================================
# REACTIVATE STUDENT
# ============================================================

@extra_class_teacher_bp.route(
    "/classes/<int:class_id>/students/<int:student_id>/reactivate",
    methods=["GET", "POST"]
)
@extra_class_teacher_required
def reactivate_class_student(class_id, student_id):

    teacher_id = session.get("extra_class_teacher_id")

    extra_subject = (
        ExtraClassSubject.query
        .filter(
            ExtraClassSubject.id == class_id,
            ExtraClassSubject.teacher_id == teacher_id,
            ExtraClassSubject.is_active.is_(True)
        )
        .first_or_404()
    )

    student = (
        ExtraClassStudent.query
        .filter_by(id=student_id)
        .first_or_404()
    )

    enrollment = (
        ExtraClassEnrollment.query
        .filter(
            ExtraClassEnrollment.student_id == student.id,
            ExtraClassEnrollment.extra_class_subject_id == extra_subject.id
        )
        .first_or_404()
    )

    if enrollment.status == "ACTIVE":
        flash(
            f"{student.first_name} {student.surname} is already active in this class.",
            "warning"
        )
        return redirect(
            url_for(
                "extra_class_teacher.view_class_student",
                class_id=extra_subject.id,
                student_id=student.id
            )
        )

    semesters = (
        ExtraClassTerm.query
        .filter(ExtraClassTerm.is_active.is_(True))
        .order_by(ExtraClassTerm.start_date.desc())
        .all()
    )

    teacher = (
        ExtraClassTeacher.query
        .filter_by(id=teacher_id)
        .first_or_404()
    )

    if request.method == "GET":
        return render_template(
            "extra_class_teacher_reactivate_student.html",
            teacher=teacher,
            extra_subject=extra_subject,
            student=student,
            enrollment=enrollment,
            semesters=semesters,
            form_data={}
        )

    term_id = request.form.get("term_id", type=int)
    form = request.form.get("form", "").strip().upper()
    class_name = request.form.get("class_name", "").strip()
    start_date_string = request.form.get("start_date", "").strip()

    form_data = {
        "term_id": term_id,
        "form": form,
        "class_name": class_name,
        "start_date": start_date_string,
    }

    def render_error(message):
        flash(message, "danger")
        return render_template(
            "extra_class_teacher_reactivate_student.html",
            teacher=teacher,
            extra_subject=extra_subject,
            student=student,
            enrollment=enrollment,
            semesters=semesters,
            form_data=form_data
        )

    if not term_id:
        return render_error("Please select a new semester.")

    semester = (
        ExtraClassTerm.query
        .filter(
            ExtraClassTerm.id == term_id,
            ExtraClassTerm.is_active.is_(True)
        )
        .first()
    )

    if not semester:
        return render_error("The selected semester is not available.")

    if form not in {"FORM 1", "FORM 2", "FORM 3"}:
        return render_error("Please select the student's current form.")

    if not class_name:
        return render_error("Please enter the student's current class.")

    if not start_date_string:
        return render_error("Please select a new start date.")

    try:
        start_date = datetime.strptime(
            start_date_string,
            "%Y-%m-%d"
        ).date()
    except ValueError:
        return render_error("Please enter a valid start date.")

    if start_date < semester.start_date:
        return render_error(
            "The new start date cannot be before the selected semester begins."
        )

    if start_date > semester.end_date:
        return render_error(
            "The new start date cannot be after the selected semester ends."
        )

    try:
        enrollment.term_id = semester.id
        enrollment.form = form
        enrollment.class_name = class_name
        enrollment.start_date = start_date
        enrollment.end_date = semester.end_date
        enrollment.status = "ACTIVE"

        student.is_active = True

        db.session.flush()

        created_fee_count, existing_fee_count = (
            generate_enrollment_monthly_fees(enrollment)
        )

        db.session.commit()

        flash(
            f"{student.first_name} {student.surname} has been reactivated successfully. "
            f"{created_fee_count} new monthly fee record(s) generated.",
            "success"
        )

        return redirect(
            url_for(
                "extra_class_teacher.view_class_student",
                class_id=extra_subject.id,
                student_id=student.id
            )
        )

    except Exception as exc:
        db.session.rollback()

        flash(
            f"Unable to reactivate student: {str(exc)}",
            "danger"
        )

        return render_template(
            "extra_class_teacher_reactivate_student.html",
            teacher=teacher,
            extra_subject=extra_subject,
            student=student,
            enrollment=enrollment,
            semesters=semesters,
            form_data=form_data
        )




# ============================================================
# REMOVE STUDENT FROM CLASS
# ============================================================

@extra_class_teacher_bp.route(
    "/classes/<int:class_id>/students/<int:student_id>/remove",
    methods=["POST"]
)
@extra_class_teacher_required
def remove_class_student(class_id, student_id):
    """
    Remove a student from the teacher's class.

    IMPORTANT:
    - The student record is NOT deleted.
    - The enrollment is NOT deleted.
    - Monthly fees are NOT deleted.
    - Payment history is NOT deleted.
    - The enrollment is simply changed to INACTIVE.
    """

    teacher_id = session.get(
        "extra_class_teacher_id"
    )

    # --------------------------------------------------------
    # VERIFY THAT THIS CLASS BELONGS TO THE LOGGED-IN TEACHER
    # --------------------------------------------------------

    extra_subject = (
        ExtraClassSubject.query
        .filter(
            ExtraClassSubject.id == class_id,
            ExtraClassSubject.teacher_id == teacher_id
        )
        .first_or_404()
    )

    # --------------------------------------------------------
    # FIND THE STUDENT'S ENROLLMENT IN THIS CLASS
    # --------------------------------------------------------

    enrollment = (
        ExtraClassEnrollment.query
        .filter(
            ExtraClassEnrollment.extra_class_subject_id
            == extra_subject.id,

            ExtraClassEnrollment.student_id
            == student_id
        )
        .first_or_404()
    )

    # --------------------------------------------------------
    # LOAD STUDENT
    # --------------------------------------------------------

    student = (
        ExtraClassStudent.query
        .filter(
            ExtraClassStudent.id == student_id
        )
        .first_or_404()
    )

    # --------------------------------------------------------
    # ALREADY INACTIVE
    # --------------------------------------------------------

    if enrollment.status != "ACTIVE":

        flash(
            f"{student.first_name} {student.surname} "
            "is already inactive in this class.",
            "warning"
        )

        return redirect(
            url_for(
                "extra_class_teacher.view_class_student",
                class_id=extra_subject.id,
                student_id=student.id
            )
        )

    # --------------------------------------------------------
    # CHANGE ENROLLMENT TO INACTIVE
    # --------------------------------------------------------

    try:

        enrollment.status = "INACTIVE"

        db.session.commit()

        flash(
            f"{student.first_name} {student.surname} "
            "has been removed from your class. "
            "The student's records, fees and payment history "
            "have been preserved.",
            "success"
        )

        return redirect(
            url_for(
                "extra_class_teacher.class_students",
                class_id=extra_subject.id
            )
        )

    except Exception as exc:

        db.session.rollback()

        print(
            "REMOVE CLASS STUDENT ERROR:",
            str(exc)
        )

        flash(
            "Unable to remove the student from this class. "
            "Please try again.",
            "danger"
        )

        return redirect(
            url_for(
                "extra_class_teacher.view_class_student",
                class_id=extra_subject.id,
                student_id=student.id
            )
        )




# ============================================================
# CLASS PAYMENTS
# ============================================================

@extra_class_teacher_bp.route(
    "/classes/<int:class_id>/payments",
    methods=["GET"]
)
@extra_class_teacher_required
def class_payments(class_id):
    """
    Display payment activity for this teacher's class.

    Important:
    - A payment may contain items for more than one subject.
    - Therefore, the class amount shown here is calculated from
      payment items belonging to this specific subject.
    - Only SUCCESS payments count as money received.
    - Other statuses remain visible for payment tracking.
    """

    teacher_id = session.get("extra_class_teacher_id")

    extra_subject = (
        ExtraClassSubject.query
        .filter(
            ExtraClassSubject.id == class_id,
            ExtraClassSubject.teacher_id == teacher_id
        )
        .first_or_404()
    )

    teacher = (
        ExtraClassTeacher.query
        .filter_by(id=teacher_id)
        .first_or_404()
    )

    # ---------------------------------------------------------
    # Load payment items belonging to this class.
    # ---------------------------------------------------------
    payment_items = (
        ExtraClassPaymentItem.query
        .join(
            ExtraClassPayment,
            ExtraClassPayment.id == ExtraClassPaymentItem.payment_id
        )
        .filter(
            ExtraClassPaymentItem.extra_class_subject_id
            == extra_subject.id
        )
        .order_by(
            ExtraClassPayment.created_at.desc(),
            ExtraClassPaymentItem.id.desc()
        )
        .all()
    )

    # ---------------------------------------------------------
    # Group items by payment so one transaction appears once.
    # ---------------------------------------------------------
    payment_map = {}

    for item in payment_items:

        payment = item.payment

        if not payment:
            continue

        if payment.id not in payment_map:
            payment_map[payment.id] = {
                "payment": payment,
                "class_amount": 0.0,
                "items": []
            }

        payment_map[payment.id]["class_amount"] += float(
            item.amount or 0
        )

        payment_map[payment.id]["items"].append(item)

    payment_rows = list(payment_map.values())

    total_received = 0.0
    total_pending = 0.0
    total_failed = 0.0
    successful_count = 0
    pending_count = 0
    failed_count = 0

    for row in payment_rows:

        status = str(
            row["payment"].status or ""
        ).upper()

        amount = row["class_amount"]

        if status == "SUCCESS":
            total_received += amount
            successful_count += 1

        elif status == "PENDING":
            total_pending += amount
            pending_count += 1

        elif status == "FAILED":
            total_failed += amount
            failed_count += 1

    return render_template(
        "extra_class_teacher_class_payments.html",
        teacher=teacher,
        extra_subject=extra_subject,
        payment_rows=payment_rows,
        total_received=total_received,
        total_pending=total_pending,
        total_failed=total_failed,
        successful_count=successful_count,
        pending_count=pending_count,
        failed_count=failed_count,
        total_payment_count=len(payment_rows)
    )



# ============================================================
# CLASS FEES
# ============================================================

@extra_class_teacher_bp.route(
    "/classes/<int:class_id>/fees",
    methods=["GET"]
)
@extra_class_teacher_required
def class_fees(class_id):
    """
    Display the financial summary for all active students
    in this teacher's class.

    V1 rules:
    - One student has one enrollment per teacher subject.
    - The teacher's current ExtraClassSubject.monthly_fee is the
      current agreed monthly fee.
    - Historical monthly fee records are never overwritten here.
    - Only SUCCESS payments count as money received.
    """

    teacher_id = session.get("extra_class_teacher_id")

    # ---------------------------------------------------------
    # 1. Verify the class belongs to the logged-in teacher
    # ---------------------------------------------------------
    extra_subject = (
        ExtraClassSubject.query
        .filter(
            ExtraClassSubject.id == class_id,
            ExtraClassSubject.teacher_id == teacher_id
        )
        .first_or_404()
    )

    teacher = (
        ExtraClassTeacher.query
        .filter_by(id=teacher_id)
        .first_or_404()
    )

    # ---------------------------------------------------------
    # 2. Load active enrollments
    # ---------------------------------------------------------
    enrollments = (
        ExtraClassEnrollment.query
        .filter(
            ExtraClassEnrollment.extra_class_subject_id
            == extra_subject.id,
            ExtraClassEnrollment.status == "ACTIVE"
        )
        .order_by(
            ExtraClassEnrollment.created_at.desc()
        )
        .all()
    )

    fee_students = []

    grand_total_fees = 0.0
    grand_total_paid = 0.0
    grand_total_outstanding = 0.0

    # ---------------------------------------------------------
    # 3. Calculate each student's financial position
    # ---------------------------------------------------------
    for enrollment in enrollments:

        student = enrollment.student

        if not student:
            continue

        monthly_fees = (
            ExtraClassMonthlyFee.query
            .filter(
                ExtraClassMonthlyFee.enrollment_id
                == enrollment.id
            )
            .order_by(
                ExtraClassMonthlyFee.billing_month.asc()
            )
            .all()
        )

        total_fees = 0.0
        total_paid = 0.0

        for fee in monthly_fees:

            if str(fee.status or "").upper() == "CANCELLED":
                continue

            amount_due = float(fee.amount_due or 0)

            payment_items = (
                ExtraClassPaymentItem.query
                .join(
                    ExtraClassPayment,
                    ExtraClassPayment.id
                    == ExtraClassPaymentItem.payment_id
                )
                .filter(
                    ExtraClassPaymentItem.monthly_fee_id
                    == fee.id,
                    ExtraClassPayment.status == "SUCCESS"
                )
                .all()
            )

            paid_amount = sum(
                float(item.amount or 0)
                for item in payment_items
            )

            total_fees += amount_due
            total_paid += paid_amount

        outstanding = max(
            total_fees - total_paid,
            0.0
        )

        if total_fees <= 0:
            financial_status = "NO FEES"
        elif outstanding <= 0:
            financial_status = "PAID"
        elif total_paid > 0:
            financial_status = "PARTIAL"
        else:
            financial_status = "UNPAID"

        fee_students.append({
            "student": student,
            "enrollment": enrollment,
            "monthly_fee": float(
                extra_subject.monthly_fee or 0
            ),
            "total_fees": total_fees,
            "total_paid": total_paid,
            "outstanding": outstanding,
            "status": financial_status
        })

        grand_total_fees += total_fees
        grand_total_paid += total_paid
        grand_total_outstanding += outstanding

    return render_template(
        "extra_class_teacher_class_fees.html",
        teacher=teacher,
        extra_subject=extra_subject,
        fee_students=fee_students,
        grand_total_fees=grand_total_fees,
        grand_total_paid=grand_total_paid,
        grand_total_outstanding=grand_total_outstanding
    )





