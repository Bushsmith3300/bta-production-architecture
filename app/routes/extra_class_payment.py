from datetime import datetime
import hashlib
import hmac
from uuid import uuid4
from sqlalchemy import text
import os
import requests
from flask import (
    Blueprint,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    current_app,
    jsonify,
)
from app.extensions import db, csrf
from app.models import (
    ExtraClassStudent,
    ExtraClassParent,
    ExtraClassStudentParent,
    ExtraClassEnrollment,
    ExtraClassMonthlyFee,
    ExtraClassPayment,
    ExtraClassPaymentItem,
)

extra_class_payment_bp = Blueprint(
    "extra_class_payment",
    __name__,
    url_prefix="/extra-classes/pay",
)


def _successful_paid_for_fee(fee_id):
    items = (
        ExtraClassPaymentItem.query
        .join(
            ExtraClassPayment,
            ExtraClassPayment.id == ExtraClassPaymentItem.payment_id,
        )
        .filter(
            ExtraClassPaymentItem.monthly_fee_id == fee_id,
            ExtraClassPayment.status == "SUCCESS",
        )
        .all()
    )
    return sum(float(item.amount or 0) for item in items)


def _pending_payment_for_fee(fee_id, student_id=None):
    """Return the latest pending payment attached to a monthly fee."""
    query = (
        ExtraClassPayment.query
        .join(
            ExtraClassPaymentItem,
            ExtraClassPayment.id == ExtraClassPaymentItem.payment_id,
        )
        .filter(
            ExtraClassPaymentItem.monthly_fee_id == fee_id,
            ExtraClassPayment.status == "PENDING",
        )
    )

    if student_id is not None:
        query = query.filter(ExtraClassPayment.student_id == student_id)

    return query.order_by(
        ExtraClassPayment.created_at.desc()
    ).first()


def _successful_payment_for_fee(fee_id, student_id=None):
    """Return the latest successful payment attached to a monthly fee."""
    query = (
        ExtraClassPayment.query
        .join(
            ExtraClassPaymentItem,
            ExtraClassPayment.id == ExtraClassPaymentItem.payment_id,
        )
        .filter(
            ExtraClassPaymentItem.monthly_fee_id == fee_id,
            ExtraClassPayment.status == "SUCCESS",
        )
    )

    if student_id is not None:
        query = query.filter(ExtraClassPayment.student_id == student_id)

    return query.order_by(
        ExtraClassPayment.paid_at.desc(),
        ExtraClassPayment.created_at.desc(),
    ).first()


def _build_student_outstanding(student):
    """
    Build the parent's fee view.

    A fee can be:
    PAID               - fully covered by SUCCESS payments.
    PAYMENT PROCESSING - a PENDING payment already exists.
    PARTIAL            - partially paid and no pending transaction.
    UNPAID             - nothing has been successfully paid.
    """
    rows = []
    total_outstanding = 0.0

    enrollments = (
        ExtraClassEnrollment.query
        .filter(
            ExtraClassEnrollment.student_id == student.id,
            ExtraClassEnrollment.status == "ACTIVE",
        )
        .order_by(ExtraClassEnrollment.created_at.asc())
        .all()
    )

    for enrollment in enrollments:
        extra_subject = enrollment.extra_class_subject

        if not extra_subject or not extra_subject.is_active:
            continue

        subject_name = (
            extra_subject.subject.name
            if extra_subject.subject
            else "Subject"
        )

        teacher_name = (
            f"{extra_subject.teacher.first_name} "
            f"{extra_subject.teacher.surname}"
            if extra_subject.teacher
            else "Teacher"
        )

        fees = (
            ExtraClassMonthlyFee.query
            .filter(
                ExtraClassMonthlyFee.enrollment_id == enrollment.id,
                ExtraClassMonthlyFee.status != "CANCELLED",
            )
            .order_by(ExtraClassMonthlyFee.billing_month.asc())
            .all()
        )

        subject_rows = []

        for fee in fees:
            amount_due = float(fee.amount_due or 0)
            amount_paid = _successful_paid_for_fee(fee.id)
            outstanding = max(amount_due - amount_paid, 0.0)

            pending_payment = _pending_payment_for_fee(
                fee.id,
                student.id
            )

            successful_payment = _successful_payment_for_fee(
                fee.id,
                student.id
            )

            if amount_due <= 0:
                payment_status = "NO FEE"
            elif outstanding <= 0:
                payment_status = "PAID"
            elif pending_payment:
                payment_status = "PAYMENT PROCESSING"
            elif amount_paid > 0:
                payment_status = "PARTIAL"
            else:
                payment_status = "UNPAID"

            is_payable = (
                outstanding > 0
                and pending_payment is None
                and successful_payment is None
            )

            subject_rows.append({
                "fee_id": fee.id,
                "fee": fee,
                "billing_month": fee.billing_month,
                "amount_due": amount_due,
                "amount_paid": amount_paid,
                "outstanding": outstanding,
                "due_date": fee.due_date,
                "status": str(fee.status or "UNPAID").upper(),
                "payment_status": payment_status,
                "is_paid": payment_status == "PAID",
                "is_pending": payment_status == "PAYMENT PROCESSING",
                "is_payable": is_payable,
                "pending_payment": pending_payment,
                "successful_payment": successful_payment,
            })

            if is_payable:
                total_outstanding += outstanding

        if subject_rows:
            rows.append({
                "enrollment": enrollment,
                "extra_subject": extra_subject,
                "subject_name": subject_name,
                "teacher_name": teacher_name,
                "fees": subject_rows,
                "subject_outstanding": sum(
                    row["outstanding"]
                    for row in subject_rows
                    if row["is_payable"]
                ),
            })

    return rows, total_outstanding



def _get_verified_payment_context():
    """Return the verified student and parent, or None if the session is invalid."""
    student_id = session.get("extra_class_payment_student_id")
    parent_id = session.get("extra_class_payment_parent_id")

    if not student_id or not parent_id:
        return None

    student = (
        ExtraClassStudent.query
        .filter(
            ExtraClassStudent.id == student_id,
            ExtraClassStudent.is_active.is_(True),
        )
        .first()
    )

    parent = (
        ExtraClassParent.query
        .filter(
            ExtraClassParent.id == parent_id,
            ExtraClassParent.is_active.is_(True),
        )
        .first()
    )

    if not student or not parent:
        return None

    linked = (
        ExtraClassStudentParent.query
        .filter(
            ExtraClassStudentParent.student_id == student.id,
            ExtraClassStudentParent.parent_id == parent.id,
        )
        .first()
    )

    if not linked:
        return None

    return student, parent


def _get_payable_fee_rows(student, selected_fee_ids=None):
    """Rebuild payable fee data from the database; never trust browser amounts."""
    selected_fee_ids = set(selected_fee_ids or [])
    fee_rows = []

    enrollments = (
        ExtraClassEnrollment.query
        .filter(
            ExtraClassEnrollment.student_id == student.id,
            ExtraClassEnrollment.status == "ACTIVE",
        )
        .order_by(ExtraClassEnrollment.created_at.asc())
        .all()
    )

    for enrollment in enrollments:
        extra_subject = enrollment.extra_class_subject
        if not extra_subject or not extra_subject.is_active:
            continue

        fees = (
            ExtraClassMonthlyFee.query
            .filter(
                ExtraClassMonthlyFee.enrollment_id == enrollment.id,
                ExtraClassMonthlyFee.student_id == student.id,
                ExtraClassMonthlyFee.status != "CANCELLED",
            )
            .order_by(ExtraClassMonthlyFee.billing_month.asc())
            .all()
        )

        for fee in fees:
            amount_due = float(fee.amount_due or 0)
            amount_paid = _successful_paid_for_fee(fee.id)
            outstanding = max(amount_due - amount_paid, 0.0)

            pending_payment = _pending_payment_for_fee(
                fee.id,
                student.id
            )

            if outstanding <= 0 or pending_payment:
                continue

            fee_rows.append({
                "fee": fee,
                "enrollment": enrollment,
                "extra_subject": extra_subject,
                "subject_name": (
                    extra_subject.subject.name
                    if extra_subject.subject
                    else "Subject"
                ),
                "teacher_name": (
                    f"{extra_subject.teacher.first_name} "
                    f"{extra_subject.teacher.surname}"
                    if extra_subject.teacher
                    else "Teacher"
                ),
                "amount_due": amount_due,
                "amount_paid": amount_paid,
                "outstanding": outstanding,
                "selected": fee.id in selected_fee_ids,
            })

    return fee_rows


def _group_fee_rows(fee_rows):
    """Group validated fee rows by Extra Class subject for the summary page."""
    groups = {}
    for row in fee_rows:
        key = row["extra_subject"].id
        if key not in groups:
            groups[key] = {
                "subject_name": row["subject_name"],
                "teacher_name": row["teacher_name"],
                "fees": [],
                "subject_total": 0.0,
            }

        groups[key]["fees"].append(row)
        groups[key]["subject_total"] += row["outstanding"]

    return list(groups.values())


@extra_class_payment_bp.route("/", methods=["GET", "POST"])
def payment_home():
    if request.method == "POST":
        student_code = request.form.get("student_code", "").strip()
        parent_phone = request.form.get("parent_phone", "").strip()

        if not student_code:
            flash("Please enter the student's Student Code.", "danger")
            return render_template(
                "extra_class_payment_home.html",
                student_code=student_code,
                parent_phone=parent_phone,
            )

        if not parent_phone:
            flash("Please enter the parent or guardian phone number.", "danger")
            return render_template(
                "extra_class_payment_home.html",
                student_code=student_code,
                parent_phone=parent_phone,
            )

        student = (
            ExtraClassStudent.query
            .filter(
                ExtraClassStudent.student_code == student_code,
                ExtraClassStudent.is_active.is_(True),
            )
            .first()
        )

        if not student:
            flash(
                "We could not find an active student with that Student Code.",
                "danger",
            )
            return render_template(
                "extra_class_payment_home.html",
                student_code=student_code,
                parent_phone=parent_phone,
            )

        matching_link = (
            db.session.query(ExtraClassStudentParent)
            .join(
                ExtraClassParent,
                ExtraClassParent.id == ExtraClassStudentParent.parent_id,
            )
            .filter(
                ExtraClassStudentParent.student_id == student.id,
                ExtraClassParent.phone == parent_phone,
                ExtraClassParent.is_active.is_(True),
            )
            .first()
        )

        if not matching_link:
            flash(
                "The Student Code and parent/guardian phone number could not be verified.",
                "danger",
            )
            return render_template(
                "extra_class_payment_home.html",
                student_code=student_code,
                parent_phone=parent_phone,
            )

        fee_groups, total_outstanding = _build_student_outstanding(student)

        session["extra_class_payment_student_id"] = student.id
        session["extra_class_payment_parent_id"] = matching_link.parent_id
        session.pop("extra_class_payment_selected_fee_ids", None)

        return render_template(
            "extra_class_payment_outstanding.html",
            student=student,
            parent=matching_link.parent,
            fee_groups=fee_groups,
            total_outstanding=total_outstanding,
        )

    return render_template("extra_class_payment_home.html")


@extra_class_payment_bp.route("/select-fees", methods=["POST"])
def select_fees():
    context = _get_verified_payment_context()

    if not context:
        session.pop("extra_class_payment_student_id", None)
        session.pop("extra_class_payment_parent_id", None)
        session.pop("extra_class_payment_selected_fee_ids", None)
        flash("Your payment session has expired. Please verify again.", "danger")
        return redirect(url_for("extra_class_payment.payment_home"))

    student, parent = context

    raw_fee_ids = request.form.getlist("fee_ids")

    if not raw_fee_ids:
        fee_groups, total_outstanding = _build_student_outstanding(student)
        flash("Please select at least one fee to continue.", "warning")
        return render_template(
            "extra_class_payment_outstanding.html",
            student=student,
            parent=parent,
            fee_groups=fee_groups,
            total_outstanding=total_outstanding,
        )

    try:
        selected_fee_ids = {int(value) for value in raw_fee_ids}
    except (TypeError, ValueError):
        flash("One or more selected fees are invalid.", "danger")
        return redirect(url_for("extra_class_payment.payment_home"))

    payable_rows = _get_payable_fee_rows(student, selected_fee_ids)
    payable_by_id = {row["fee"].id: row for row in payable_rows}

    # The browser can submit any IDs it wants. Only IDs that the server
    # independently confirms as payable for this verified student survive.
    invalid_ids = selected_fee_ids - set(payable_by_id.keys())

    if invalid_ids:
        flash(
            "One or more selected fees are no longer available for payment. "
            "Please review the outstanding fees again.",
            "warning",
        )
        fee_groups, total_outstanding = _build_student_outstanding(student)
        return render_template(
            "extra_class_payment_outstanding.html",
            student=student,
            parent=parent,
            fee_groups=fee_groups,
            total_outstanding=total_outstanding,
        )

    selected_rows = [payable_by_id[fee_id] for fee_id in selected_fee_ids]
    selected_rows.sort(
        key=lambda row: (
            row["subject_name"].lower(),
            row["fee"].billing_month,
        )
    )

    selected_total = sum(row["outstanding"] for row in selected_rows)

    if selected_total <= 0:
        flash("The selected fees have no outstanding balance.", "warning")
        return redirect(url_for("extra_class_payment.payment_home"))

    session["extra_class_payment_selected_fee_ids"] = [
        row["fee"].id for row in selected_rows
    ]

    return render_template(
        "extra_class_payment_summary.html",
        student=student,
        parent=parent,
        fee_groups=_group_fee_rows(selected_rows),
        selected_total=selected_total,
    )




def _lock_monthly_fees(fee_ids):
    """
    Acquire PostgreSQL transaction-level advisory locks for the selected
    monthly fees.

    The locks are held until the current database transaction commits or
    rolls back. Sorting the IDs gives concurrent requests a consistent
    lock order and avoids deadlocks when parents select multiple fees.
    """
    for fee_id in sorted({int(value) for value in fee_ids}):
        db.session.execute(
            text("SELECT pg_advisory_xact_lock(:fee_id)"),
            {"fee_id": fee_id},
        )




def _paystack_secret_key():
    """Return the Paystack secret key for the current environment."""
    return (
        current_app.config.get("PAYSTACK_SECRET_KEY")
        or os.getenv("PAYSTACK_SECRET_KEY")
    )


def _paystack_headers():
    secret_key = _paystack_secret_key()
    if not secret_key:
        raise RuntimeError("PAYSTACK_SECRET_KEY is not configured.")
    return {
        "Authorization": f"Bearer {secret_key}",
        "Content-Type": "application/json",
        "Cache-Control": "no-cache",
    }


def _paystack_initialize(payment, parent, student):
    """
    Initialize the existing local payment with Paystack.
    Paystack expects the amount in the currency's smallest unit.
    """
    customer_email = getattr(parent, "email", None)
    if not customer_email:
        customer_email = (
            current_app.config.get("PAYSTACK_TEST_EMAIL")
            or os.getenv("PAYSTACK_TEST_EMAIL")
        )

    if not customer_email:
        raise RuntimeError(
            "No customer email is available. Add parent.email or "
            "configure PAYSTACK_TEST_EMAIL."
        )

    amount_kobo = int(round(float(payment.amount) * 100))

    payload = {
        "email": customer_email,
        "amount": str(amount_kobo),
        "currency": payment.currency,
        "reference": payment.payment_reference,
        "callback_url": url_for(
            "extra_class_payment.paystack_callback",
            _external=True,
        ),
        "metadata": {
            "payment_id": payment.id,
            "student_id": student.id,
            "parent_id": parent.id,
            "student_code": student.student_code,
            "payment_reference": payment.payment_reference,
        },
    }

    response = requests.post(
        "https://api.paystack.co/transaction/initialize",
        headers=_paystack_headers(),
        json=payload,
        timeout=30,
    )

    try:
        data = response.json()
    except ValueError:
        data = {}

    if not response.ok or not data.get("status"):
        message = data.get("message") or "Paystack transaction initialization failed."
        raise RuntimeError(message)

    return data["data"]


def _paystack_verify(reference):
    response = requests.get(
        f"https://api.paystack.co/transaction/verify/{reference}",
        headers=_paystack_headers(),
        timeout=30,
    )

    try:
        data = response.json()
    except ValueError:
        data = {}

    if not response.ok or not data.get("status"):
        message = data.get("message") or "Paystack verification failed."
        raise RuntimeError(message)

    return data["data"]


@extra_class_payment_bp.route("/create-payment", methods=["POST"])
def create_payment():
    """
    Create a PENDING payment transaction from the server-verified fee selection.

    This route does not charge the parent yet. It creates the transaction and
    its fee allocation records so the payment can be handed to a gateway in
    the next stage.
    """
    context = _get_verified_payment_context()

    if not context:
        session.pop("extra_class_payment_student_id", None)
        session.pop("extra_class_payment_parent_id", None)
        session.pop("extra_class_payment_selected_fee_ids", None)
        flash("Your payment session has expired. Please verify again.", "danger")
        return redirect(url_for("extra_class_payment.payment_home"))

    student, parent = context

    selected_fee_ids = session.get(
        "extra_class_payment_selected_fee_ids",
        [],
    )

    if not selected_fee_ids:
        flash("No fees have been selected for payment.", "warning")
        return redirect(url_for("extra_class_payment.payment_home"))

    try:
        selected_fee_ids = {int(value) for value in selected_fee_ids}
    except (TypeError, ValueError):
        session.pop("extra_class_payment_selected_fee_ids", None)
        flash("The selected payment fees are invalid. Please start again.", "danger")
        return redirect(url_for("extra_class_payment.payment_home"))

    # Acquire a PostgreSQL transaction-level lock for every selected
    # monthly fee BEFORE checking whether a pending payment exists.
    #
    # This closes the race condition where two requests both pass the
    # application-level "no pending payment" check at nearly the same time.
    _lock_monthly_fees(selected_fee_ids)

    # Rebuild the payable rows AFTER acquiring the locks. A competing
    # request that was waiting on one of these locks will now see the
    # committed transaction and its pending payment.
    payable_rows = _get_payable_fee_rows(student, selected_fee_ids)
    payable_by_id = {row["fee"].id: row for row in payable_rows}

    invalid_ids = selected_fee_ids - set(payable_by_id.keys())
    if invalid_ids:
        session.pop("extra_class_payment_selected_fee_ids", None)
        flash(
            "One or more selected fees are no longer available for payment. "
            "Please review the outstanding fees again.",
            "warning",
        )
        return redirect(url_for("extra_class_payment.payment_home"))

    selected_rows = [
        payable_by_id[fee_id]
        for fee_id in selected_fee_ids
    ]
    selected_rows.sort(
        key=lambda row: (
            row["subject_name"].lower(),
            row["fee"].billing_month,
        )
    )

    # Final server-side protection against duplicate pending transactions.
    # The advisory locks above ensure this check is performed serially for
    # the same monthly fee when concurrent requests arrive.
    for row in selected_rows:
        existing_pending = _pending_payment_for_fee(
            row["fee"].id,
            student.id
        )

        if existing_pending:
            session.pop("extra_class_payment_selected_fee_ids", None)

            flash(
                "A payment is already being processed for one or more "
                "of the selected fees. Please check the payment status "
                "before trying again.",
                "warning",
            )

            fee_groups, total_outstanding = _build_student_outstanding(
                student
            )

            return render_template(
                "extra_class_payment_outstanding.html",
                student=student,
                parent=parent,
                fee_groups=fee_groups,
                total_outstanding=total_outstanding,
            )

    selected_total = sum(
        row["outstanding"]
        for row in selected_rows
    )

    if selected_total <= 0:
        session.pop("extra_class_payment_selected_fee_ids", None)
        flash("The selected fees have no outstanding balance.", "warning")
        return redirect(url_for("extra_class_payment.payment_home"))

    # A payment method is collected now so the transaction has the method
    # selected by the parent. The actual gateway charge will be connected
    # in the next stage.
    payment_method = request.form.get(
        "payment_method",
        "MOBILE_MONEY",
    ).strip().upper()

    allowed_methods = {
        "MOBILE_MONEY",
        "CARD",
        "BANK_TRANSFER",
        "OTHER",
    }

    if payment_method not in allowed_methods:
        flash("Please select a valid payment method.", "danger")
        return redirect(
            url_for("extra_class_payment.payment_home")
        )

    payment_reference = f"BTA-EC-{datetime.utcnow():%Y%m%d%H%M%S}-{uuid4().hex[:8].upper()}"

    payment = ExtraClassPayment(
        student_id=student.id,
        parent_id=parent.id,
        amount=selected_total,
        currency="GHS",
        payment_reference=payment_reference,
        gateway_reference=None,
        payment_method=payment_method,
        status="PENDING",
        paid_at=None,
    )

    try:
        db.session.add(payment)
        db.session.flush()

        for row in selected_rows:
            fee = row["fee"]
            extra_subject = row["extra_subject"]

            payment_item = ExtraClassPaymentItem(
                payment_id=payment.id,
                monthly_fee_id=fee.id,
                extra_class_subject_id=extra_subject.id,
                teacher_id=extra_subject.teacher_id,
                amount=row["outstanding"],
            )
            db.session.add(payment_item)

        # Save the local payment first so Paystack metadata can safely
        # reference its database ID.
        db.session.commit()

        # Now initialize the transaction with Paystack.
        paystack_data = _paystack_initialize(payment, parent, student)

        payment.gateway_reference = paystack_data.get("reference")
        db.session.commit()

    except Exception as exc:
        db.session.rollback()
        current_app.logger.exception("Paystack payment initialization failed: %s", exc)
        flash(
            f"We could not start the Paystack payment: {exc}",
            "danger",
        )
        return redirect(
            url_for("extra_class_payment.payment_home")
        )

    session["extra_class_payment_id"] = payment.id
    session.pop("extra_class_payment_selected_fee_ids", None)

    # Redirect the parent directly to Paystack's hosted checkout.
    return redirect(paystack_data["authorization_url"])



@extra_class_payment_bp.route("/paystack/webhook", methods=["POST"])
@csrf.exempt
def paystack_webhook():
    """
    Receive Paystack server-to-server payment events.

    Paystack signs the raw request body with HMAC-SHA512. The signature is
    verified before any database work is performed. Only a signed
    ``charge.success`` event for a matching BTA payment reference can mark
    the local payment as SUCCESS.

    Repeated success events are intentionally idempotent: once a payment is
    SUCCESS, later copies of the same event do not change it again.
    """
    raw_body = request.get_data(cache=True)
    signature = request.headers.get("x-paystack-signature", "").strip()
    secret_key = _paystack_secret_key()

    if not secret_key:
        current_app.logger.error(
            "Paystack webhook rejected: PAYSTACK_SECRET_KEY is not configured."
        )
        return jsonify({"status": "error"}), 500

    expected_signature = hmac.new(
        secret_key.encode("utf-8"),
        raw_body,
        hashlib.sha512,
    ).hexdigest()

    if not signature or not hmac.compare_digest(
        expected_signature,
        signature,
    ):
        current_app.logger.warning("Invalid Paystack webhook signature.")
        return jsonify({"status": "error"}), 401

    payload = request.get_json(silent=True) or {}
    event_name = str(payload.get("event") or "").strip().lower()

    # We currently need only successful transaction events. Other signed
    # Paystack events are acknowledged so Paystack does not retry them.
    if event_name != "charge.success":
        return jsonify({"status": "ignored"}), 200

    data = payload.get("data") or {}
    reference = str(data.get("reference") or "").strip()

    if not reference:
        current_app.logger.warning(
            "Paystack charge.success webhook had no transaction reference."
        )
        return jsonify({"status": "ignored"}), 200

    # BTA transaction references always begin with BTA-EC-. This also keeps
    # unrelated Paystack transactions out of this payment workflow.
    if not reference.startswith("BTA-EC-"):
        return jsonify({"status": "ignored"}), 200

    payment = (
        ExtraClassPayment.query
        .filter(ExtraClassPayment.payment_reference == reference)
        .first()
    )

    if not payment:
        current_app.logger.warning(
            "Paystack webhook received for unknown BTA reference: %s",
            reference,
        )
        return jsonify({"status": "ignored"}), 200

    paystack_status = str(data.get("status") or "").lower()
    returned_amount = int(data.get("amount") or 0)
    returned_currency = str(data.get("currency") or "").upper()
    expected_amount = int(round(float(payment.amount) * 100))
    expected_currency = str(payment.currency).upper()

    # Never mark a payment successful unless Paystack's signed payload agrees
    # with the exact BTA reference, amount, and currency.
    if paystack_status != "success":
        current_app.logger.warning(
            "Paystack charge.success event had unexpected status for %s: %s",
            reference,
            paystack_status,
        )
        return jsonify({"status": "ignored"}), 200

    if returned_amount != expected_amount or returned_currency != expected_currency:
        current_app.logger.error(
            "Paystack amount/currency mismatch for %s: returned %s %s; expected %s %s",
            reference,
            returned_amount,
            returned_currency,
            expected_amount,
            expected_currency,
        )
        # The event is authenticated but cannot safely be applied to this
        # BTA payment. A 200 prevents endless retries of an invalid payload.
        return jsonify({"status": "ignored"}), 200

    # Idempotency: Paystack may deliver the same webhook more than once.
    # Never downgrade or re-process an already successful payment.
    if payment.status == "SUCCESS":
        return jsonify({"status": "ok", "message": "Already processed"}), 200

    # Do not allow a late success webhook to silently revive a transaction
    # that BTA has already marked as refunded. A PENDING payment is the normal
    # state that charge.success is expected to transition.
    if payment.status not in {"PENDING", "FAILED"}:
        current_app.logger.warning(
            "Ignoring charge.success for payment %s in status %s.",
            reference,
            payment.status,
        )
        return jsonify({"status": "ignored"}), 200

    payment.status = "SUCCESS"
    payment.gateway_reference = reference

    paid_at = data.get("paid_at")
    if paid_at:
        try:
            payment.paid_at = datetime.fromisoformat(
                str(paid_at).replace("Z", "+00:00")
            )
        except ValueError:
            current_app.logger.warning(
                "Invalid Paystack paid_at for %s; leaving paid_at unchanged.",
                reference,
            )
    elif payment.paid_at is None:
        payment.paid_at = datetime.utcnow()

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        current_app.logger.exception(
            "Failed to save Paystack webhook payment %s.",
            reference,
        )
        return jsonify({"status": "error"}), 500

    current_app.logger.info(
        "Paystack webhook confirmed BTA payment %s as SUCCESS.",
        reference,
    )
    return jsonify({"status": "ok"}), 200


@extra_class_payment_bp.route("/paystack/callback", methods=["GET"])
def paystack_callback():
    """
    Paystack redirects the customer here after checkout.
    Never trust the callback alone: verify the reference server-side.
    """
    reference = request.args.get("reference", "").strip()

    if not reference:
        flash("No Paystack transaction reference was returned.", "danger")
        return redirect(url_for("extra_class_payment.payment_home"))

    payment = (
        ExtraClassPayment.query
        .filter(ExtraClassPayment.payment_reference == reference)
        .first()
    )

    if not payment:
        flash("The Paystack transaction could not be matched to a BTA payment.", "danger")
        return redirect(url_for("extra_class_payment.payment_home"))

    try:
        verified = _paystack_verify(reference)
    except Exception as exc:
        current_app.logger.exception("Paystack verification failed: %s", exc)
        return render_template(
            "extra_class_payment_result.html",
            payment=payment,
            verified_status="ERROR",
            message="We could not verify the payment yet. Please try again.",
        )

    paystack_status = str(verified.get("status", "")).lower()

    # Protect against amount/currency mismatches.
    expected_amount = int(round(float(payment.amount) * 100))
    returned_amount = int(verified.get("amount") or 0)
    returned_currency = str(verified.get("currency") or "").upper()

    if (
        paystack_status == "success"
        and returned_amount == expected_amount
        and returned_currency == str(payment.currency).upper()
    ):
        payment.status = "SUCCESS"
        payment.gateway_reference = verified.get("reference") or reference
        paid_at = verified.get("paid_at")
        payment.paid_at = (
            datetime.fromisoformat(paid_at.replace("Z", "+00:00"))
            if paid_at
            else datetime.utcnow()
        )
        db.session.commit()

        return render_template(
            "extra_class_payment_result.html",
            payment=payment,
            verified_status="SUCCESS",
            message="Payment successful. Your Extra Classes payment has been confirmed.",
        )

    if paystack_status in {"pending", "ongoing", "processing"}:
        return render_template(
            "extra_class_payment_result.html",
            payment=payment,
            verified_status="PENDING",
            message="Your payment is still being processed. Please check your payment status again shortly.",
        )

    payment.status = "FAILED"
    payment.gateway_reference = verified.get("reference") or reference
    db.session.commit()

    return render_template(
        "extra_class_payment_result.html",
        payment=payment,
        verified_status="FAILED",
        message="The Paystack payment was not successful. No successful payment has been recorded.",
    )


@extra_class_payment_bp.route("/start-over")
def start_over():
    session.pop("extra_class_payment_student_id", None)
    session.pop("extra_class_payment_parent_id", None)
    session.pop("extra_class_payment_selected_fee_ids", None)
    session.pop("extra_class_payment_id", None)

    return redirect(url_for("extra_class_payment.payment_home"))
