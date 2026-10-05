from datetime import datetime

from app.extensions import db


class ExtraClassStudent(db.Model):
    __tablename__ = "extra_class_students"

    id = db.Column(
        db.BigInteger,
        primary_key=True
    )

    student_code = db.Column(
        db.String(50),
        unique=True,
        nullable=False,
        index=True
    )

    first_name = db.Column(
        db.String(100),
        nullable=False
    )

    surname = db.Column(
        db.String(100),
        nullable=False
    )

    other_name = db.Column(
        db.String(100),
        nullable=True
    )

    school = db.Column(
        db.String(200),
        nullable=True
    )

    class_name = db.Column(
        db.String(100),
        nullable=True
    )

    phone = db.Column(
        db.String(30),
        nullable=True
    )

    email = db.Column(
        db.String(200),
        nullable=True
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
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

    parent_links = db.relationship(
        "ExtraClassStudentParent",
        back_populates="student",
        cascade="all, delete-orphan"
    )

    enrollments = db.relationship(
        "ExtraClassEnrollment",
        back_populates="student"
    )

    monthly_fees = db.relationship(
        "ExtraClassMonthlyFee",
        back_populates="student"
    )

    payments = db.relationship(
        "ExtraClassPayment",
        back_populates="student"
    )

    def __repr__(self):
        return (
            f"<ExtraClassStudent "
            f"{self.student_code}: "
            f"{self.first_name} {self.surname}>"
        )