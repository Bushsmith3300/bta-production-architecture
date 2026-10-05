from datetime import datetime

from app.extensions import db


class ExtraClassStudentParent(db.Model):
    __tablename__ = "extra_class_student_parents"

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

    parent_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "extra_class_parents.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    relationship = db.Column(
        db.String(50),
        nullable=True
    )

    is_primary = db.Column(
        db.Boolean,
        nullable=False,
        default=False
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
        back_populates="parent_links"
    )

    parent = db.relationship(
        "ExtraClassParent",
        back_populates="student_links"
    )

    # ====================================
    # CONSTRAINT
    # ====================================

    __table_args__ = (
        db.UniqueConstraint(
            "student_id",
            "parent_id",
            name="uq_extra_class_student_parent"
        ),
    )

    def __repr__(self):
        return (
            f"<ExtraClassStudentParent "
            f"student={self.student_id} "
            f"parent={self.parent_id}>"
        )