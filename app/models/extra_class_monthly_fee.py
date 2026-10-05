from datetime import datetime

from app.extensions import db


class ExtraClassMonthlyFee(db.Model):
    __tablename__ = "extra_class_monthly_fees"

    id = db.Column(
        db.BigInteger,
        primary_key=True
    )

    student_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "extra_class_students.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    enrollment_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "extra_class_enrollments.id",
            ondelete="RESTRICT"
        ),
        nullable=False,
        index=True
    )

    term_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "extra_class_terms.id",
            ondelete="RESTRICT"
        ),
        nullable=True,
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

    billing_month = db.Column(
    db.Date,
    nullable=False,
    index=True
    )


    # Standard monthly fee before any final-period adjustment
    standard_amount = db.Column(
        db.Numeric(12, 2),
        nullable=False
    )


    # Actual amount the student is required to pay
    
    amount_due = db.Column(
        db.Numeric(12, 2),
        nullable=False
    )

    # NONE, QUARTER_MONTH, HALF_MONTH, THREE_QUARTER_MONTH
    
    proration_type = db.Column(
        db.String(30),
        nullable=False,
        default="NONE"
    )


    # 100, 75, 50, or 25
    
    proration_percentage = db.Column(
        db.Numeric(5, 2),
        nullable=False,
        default=100
    )

    # Human-readable explanation of the adjustment
    
    proration_reason = db.Column(
        db.String(255),
        nullable=True
    )

    due_date = db.Column(
        db.Date,
        nullable=True
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="UNPAID",
        index=True
    )

    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )

    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    # ====================================
    # RELATIONSHIPS
    # ====================================

    student = db.relationship(
        "ExtraClassStudent",
        back_populates="monthly_fees"
    )

    enrollment = db.relationship(
        "ExtraClassEnrollment",
        back_populates="monthly_fees"
    )

    extra_class_subject = db.relationship(
        "ExtraClassSubject",
        back_populates="monthly_fees"
    )

    payment_items = db.relationship(
        "ExtraClassPaymentItem",
        back_populates="monthly_fee"
    )
    
    term = db.relationship(
        "ExtraClassTerm",
        back_populates="monthly_fees"
    )

    # ====================================
    # CONSTRAINTS
    # ====================================

    __table_args__ = (
        db.UniqueConstraint(
            "student_id",
            "extra_class_subject_id",
            "billing_month",
            name="uq_extra_class_monthly_fee"
        ),

        db.CheckConstraint(
            "amount_due >= 0",
            name="ck_extra_class_monthly_fee_amount"
        ),

        db.CheckConstraint(
            "status IN "
            "('UNPAID', 'PARTIAL', 'PAID', 'OVERDUE', 'CANCELLED')",
            name="ck_extra_class_monthly_fee_status"
        ),

        db.CheckConstraint(
            "billing_month = "
            "date_trunc('month', billing_month)::date",
            name="ck_extra_class_billing_month_first_day"
        ),
    )

    def __repr__(self):
        return (
            f"<ExtraClassMonthlyFee "
            f"student={self.student_id} "
            f"subject={self.extra_class_subject_id} "
            f"month={self.billing_month}>"
        )