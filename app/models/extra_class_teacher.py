from datetime import datetime

from app.extensions import db


class ExtraClassTeacher(db.Model):
    __tablename__ = "extra_class_teachers"

    id = db.Column(
        db.BigInteger,
        primary_key=True
    )

    teacher_code = db.Column(
        db.String(50),
        unique=True,
        nullable=True,
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


    account = db.relationship(
        "ExtraClassTeacherAccount",
        back_populates="teacher",
        uselist=False,
        cascade="all, delete-orphan"
    ) 


    subjects = db.relationship(
        "ExtraClassSubject",
        back_populates="teacher"
    )

    payment_items = db.relationship(
        "ExtraClassPaymentItem",
        back_populates="teacher"
    )

    settlements = db.relationship(
        "ExtraClassTeacherSettlement",
        back_populates="teacher"
    )

    def __repr__(self):
        return (
            f"<ExtraClassTeacher "
            f"{self.first_name} {self.surname}>"
        )