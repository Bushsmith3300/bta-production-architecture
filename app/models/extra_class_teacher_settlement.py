from datetime import datetime

from app.extensions import db


class ExtraClassTeacherSettlement(db.Model):
    __tablename__ = "extra_class_teacher_settlements"

    id = db.Column(
        db.BigInteger,
        primary_key=True
    )

    teacher_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "extra_class_teachers.id",
            ondelete="RESTRICT"
        ),
        nullable=False,
        index=True
    )

    # Always store the first day of the settlement month.
    # Example: 2026-09-01 = September 2026.
    settlement_period = db.Column(
        db.Date,
        nullable=False,
        index=True
    )

    amount_owed = db.Column(
        db.Numeric(12, 2),
        nullable=False
    )

    amount_paid = db.Column(
        db.Numeric(12, 2),
        nullable=False,
        default=0
    )

    # This column already exists in Supabase.
    # It represents amount_owed - amount_paid.
    balance = db.Column(
        db.Numeric(12, 2),
        nullable=False
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="UNPAID",
        index=True
    )

    paid_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True
    )

    notes = db.Column(
        db.Text,
        nullable=True
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
    # RELATIONSHIP
    # ====================================

    teacher = db.relationship(
        "ExtraClassTeacher",
        back_populates="settlements"
    )

    # ====================================
    # CONSTRAINTS
    # ====================================

    __table_args__ = (
        db.UniqueConstraint(
            "teacher_id",
            "settlement_period",
            name="uq_extra_class_teacher_settlement"
        ),

        db.CheckConstraint(
            "amount_owed >= 0",
            name="ck_extra_class_settlement_amount_owed"
        ),

        db.CheckConstraint(
            "amount_paid >= 0",
            name="ck_extra_class_settlement_amount_paid"
        ),

        db.CheckConstraint(
            "amount_paid <= amount_owed",
            name="ck_extra_class_settlement_paid_limit"
        ),

        db.CheckConstraint(
            "settlement_period = "
            "date_trunc('month', settlement_period)::date",
            name="ck_extra_class_settlement_first_day"
        ),

        db.CheckConstraint(
            "status IN ('UNPAID', 'PARTIAL', 'PAID')",
            name="ck_extra_class_settlement_status"
        ),
    )

    def __repr__(self):
        return (
            f"<ExtraClassTeacherSettlement "
            f"teacher={self.teacher_id} "
            f"period={self.settlement_period} "
            f"owed={self.amount_owed}>"
        )