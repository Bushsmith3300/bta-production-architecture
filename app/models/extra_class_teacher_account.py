from datetime import datetime

from app.extensions import db


class ExtraClassTeacherAccount(db.Model):
    __tablename__ = "extra_class_teacher_accounts"

    id = db.Column(
        db.BigInteger,
        primary_key=True
    )

    teacher_id = db.Column(
        db.BigInteger,
        db.ForeignKey(
            "extra_class_teachers.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        unique=True,
        index=True
    )

    username = db.Column(
        db.String(80),
        nullable=False,
        unique=True,
        index=True
    )

    password = db.Column(
        db.String(255),
        nullable=False
    )

    is_active = db.Column(
        db.Boolean,
        nullable=False,
        default=True
    )

    last_login_at = db.Column(
        db.DateTime(timezone=True),
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
    # RELATIONSHIPS
    # ====================================

    teacher = db.relationship(
        "ExtraClassTeacher",
        back_populates="account",
        uselist=False
    )

    def __repr__(self):
        return (
            f"<ExtraClassTeacherAccount "
            f"username={self.username!r}>"
        )