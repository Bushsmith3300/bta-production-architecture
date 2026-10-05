from datetime import datetime

from app.extensions import db


class ExtraClassParent(db.Model):
    __tablename__ = "extra_class_parents"

    id = db.Column(
        db.BigInteger,
        primary_key=True
    )

    first_name = db.Column(
        db.String(100),
        nullable=False
    )

    surname = db.Column(
        db.String(100),
        nullable=False
    )

    phone = db.Column(
        db.String(30),
        nullable=False
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

    student_links = db.relationship(
        "ExtraClassStudentParent",
        back_populates="parent",
        cascade="all, delete-orphan"
    )

    payments = db.relationship(
        "ExtraClassPayment",
        back_populates="parent"
    )

    def __repr__(self):
        return f"<ExtraClassParent {self.first_name} {self.surname}>"