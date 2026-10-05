from datetime import datetime, timezone

from app.extensions import db


class ExtraClassPayment(db.Model):
    __tablename__ = "extra_class_payments"

    id = db.Column(
        db.BigInteger,
        primary_key=True
    )

    student_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "extra_class_students.id",
            ondelete="RESTRICT"
        ),
        nullable=False,
        index=True
    )

    parent_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "extra_class_parents.id",
            ondelete="RESTRICT"
        ),
        nullable=False,
        index=True
    )

    amount = db.Column(
        db.Numeric(12, 2),
        nullable=False
    )

    currency = db.Column(
        db.String(3),
        nullable=False,
        default="GHS"
    )

    payment_reference = db.Column(
        db.String(100),
        unique=True,
        nullable=False,
        index=True
    )

    gateway_reference = db.Column(
        db.String(200),
        nullable=True,
        index=True
    )

    payment_method = db.Column(
        db.String(30),
        nullable=False
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="PENDING",
        index=True
    )

    paid_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now()
    )

    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.func.now(),
        onupdate=db.func.now()
    )

    # ====================================
    # RELATIONSHIPS
    # ====================================

    student = db.relationship(
        "ExtraClassStudent",
        back_populates="payments"
    )

    parent = db.relationship(
        "ExtraClassParent",
        back_populates="payments"
    )

    payment_items = db.relationship(
        "ExtraClassPaymentItem",
        back_populates="payment",
        cascade="all, delete-orphan"
    )

    # ====================================
    # CONSTRAINTS
    # ====================================

    __table_args__ = (
        db.CheckConstraint(
            "amount > 0",
            name="ck_extra_class_payment_amount"
        ),

        db.CheckConstraint(
            "payment_method IN "
            "('MOBILE_MONEY', 'CARD', 'BANK_TRANSFER', 'OTHER')",
            name="ck_extra_class_payment_method"
        ),

        db.CheckConstraint(
            "status IN "
            "('PENDING', 'SUCCESS', 'FAILED', 'CANCELLED', 'REFUNDED')",
            name="ck_extra_class_payment_status"
        ),
    )

    def __repr__(self):
        return (
            f"<ExtraClassPayment "
            f"{self.payment_reference} "
            f"amount={self.amount} "
            f"status={self.status}>"
        )