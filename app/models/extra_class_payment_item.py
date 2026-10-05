from datetime import datetime

from app.extensions import db


class ExtraClassPaymentItem(db.Model):
    __tablename__ = "extra_class_payment_items"

    id = db.Column(
        db.BigInteger,
        primary_key=True
    )

    payment_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "extra_class_payments.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    monthly_fee_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "extra_class_monthly_fees.id",
            ondelete="RESTRICT"
        ),
        nullable=False,
        index=True
    )

    extra_class_subject_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "extra_class_subjects.id",
            ondelete="RESTRICT"
        ),
        nullable=False,
        index=True
    )

    # Snapshot of the teacher at the time of payment.
    teacher_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "extra_class_teachers.id",
            ondelete="RESTRICT"
        ),
        nullable=True,
        index=True
    )

    amount = db.Column(
        db.Numeric(12, 2),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )

    # ====================================
    # RELATIONSHIPS
    # ====================================

    payment = db.relationship(
        "ExtraClassPayment",
        back_populates="payment_items"
    )

    monthly_fee = db.relationship(
        "ExtraClassMonthlyFee",
        back_populates="payment_items"
    )

    extra_class_subject = db.relationship(
        "ExtraClassSubject",
        back_populates="payment_items"
    )

    teacher = db.relationship(
        "ExtraClassTeacher",
        back_populates="payment_items"
    )

    # ====================================
    # CONSTRAINTS
    # ====================================

    __table_args__ = (
        db.UniqueConstraint(
            "payment_id",
            "monthly_fee_id",
            name="uq_extra_class_payment_item"
        ),

        db.CheckConstraint(
            "amount > 0",
            name="ck_extra_class_payment_item_amount"
        ),
    )

    def __repr__(self):
        return (
            f"<ExtraClassPaymentItem "
            f"payment={self.payment_id} "
            f"monthly_fee={self.monthly_fee_id} "
            f"amount={self.amount}>"
        )