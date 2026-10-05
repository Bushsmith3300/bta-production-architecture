from datetime import datetime

from app.extensions import db


class ExtraClassEnrollment(db.Model):
    __tablename__ = "extra_class_enrollments"

    id = db.Column(db.BigInteger, primary_key=True)

    student_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "extra_class_students.id",
            ondelete="CASCADE"
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

    term_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "extra_class_terms.id",
            ondelete="RESTRICT"
        ),
        nullable=False,
        index=True
    )

    form = db.Column(
        db.String(20),
        nullable=False,
        index=True
    )

    class_name = db.Column(
        db.String(100),
        nullable=True
    )

    start_date = db.Column(
        db.Date,
        nullable=False
    )

    end_date = db.Column(
        db.Date,
        nullable=True
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="ACTIVE",
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

    student = db.relationship(
        "ExtraClassStudent",
        back_populates="enrollments"
    )

    extra_class_subject = db.relationship(
        "ExtraClassSubject",
        back_populates="enrollments"
    )

    monthly_fees = db.relationship(
        "ExtraClassMonthlyFee",
        back_populates="enrollment"
    )

    term = db.relationship(
        "ExtraClassTerm",
        back_populates="enrollments"
    )

    __table_args__ = (

        db.UniqueConstraint(
            "student_id",
            "extra_class_subject_id",
            name="uq_extra_class_enrollment"
        ),

        db.CheckConstraint(
            "status IN ('ACTIVE', 'INACTIVE', 'COMPLETED', 'CANCELLED')",
            name="ck_extra_class_enrollment_status"
        ),

        db.CheckConstraint(
            "form IN ('FORM 1', 'FORM 2', 'FORM 3')",
            name="ck_extra_class_enrollment_form"
        ),
    )