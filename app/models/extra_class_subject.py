from datetime import datetime

from app.extensions import db


class ExtraClassSubject(db.Model):
    __tablename__ = "extra_class_subjects"

    id = db.Column(
        db.BigInteger,
        primary_key=True
    )

    # ============================================================
    # EXISTING BTA SUBJECT
    # ============================================================

    # References the existing BTA subjects table.
    #
    # Teachers will only be allowed to select subjects
    # where subjects.is_active = TRUE.
    subject_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "subjects.id",
            ondelete="RESTRICT"
        ),
        nullable=False,
        index=True
    )


    # ============================================================
    # TEACHER
    # ============================================================

    # One teacher = one Extra Class subject.
    #
    # Multiple teachers can teach the same subject.
    #
    # Example:
    #
    # Teacher A -> Chemistry
    # Teacher B -> Chemistry
    # Teacher C -> Chemistry
    #
    # But:
    #
    # Teacher A -> Chemistry
    # Teacher A -> Biology
    #
    # is NOT allowed.
    teacher_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "extra_class_teachers.id",
            ondelete="RESTRICT"
        ),
        nullable=False,
        index=True
    )


    # ============================================================
    # MONTHLY FEE
    # ============================================================

    # This is the monthly fee for THIS teacher's class.
    #
    # Therefore different teachers teaching the same subject
    # can have different monthly fees.
    monthly_fee = db.Column(
        db.Numeric(12, 2),
        nullable=False
    )


    # ============================================================
    # STATUS
    # ============================================================

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True,
        index=True
    )


    # ============================================================
    # TIMESTAMPS
    # ============================================================

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


    # ============================================================
    # RELATIONSHIPS
    # ============================================================

    subject = db.relationship(
        "Subject",
        back_populates="extra_class_subjects"
    )


    teacher = db.relationship(
        "ExtraClassTeacher",
        back_populates="subjects"
    )


    enrollments = db.relationship(
        "ExtraClassEnrollment",
        back_populates="extra_class_subject"
    )


    monthly_fees = db.relationship(
        "ExtraClassMonthlyFee",
        back_populates="extra_class_subject"
    )


    payment_items = db.relationship(
        "ExtraClassPaymentItem",
        back_populates="extra_class_subject"
    )


    # ============================================================
    # DATABASE CONSTRAINTS
    # ============================================================

    __table_args__ = (

        # --------------------------------------------------------
        # ONE TEACHER = ONE SUBJECT
        # --------------------------------------------------------

        db.UniqueConstraint(
            "teacher_id",
            name="uq_extra_class_teacher_subject"
        ),


        # --------------------------------------------------------
        # MONTHLY FEE CANNOT BE NEGATIVE
        # --------------------------------------------------------

        db.CheckConstraint(
            "monthly_fee >= 0",
            name="ck_extra_class_subject_monthly_fee"
        ),

    )


    def __repr__(self):

        return (
            f"<ExtraClassSubject "
            f"teacher_id={self.teacher_id} "
            f"subject_id={self.subject_id}>"
        )