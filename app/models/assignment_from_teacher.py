from app.extensions import db
from datetime import datetime


class Assignment(db.Model):

    __tablename__ = "assignments"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    admin_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "users.id",
            ondelete="SET NULL"
        ),
        nullable=True,
        index=True
    )

    title = db.Column(
        db.String(100),
        nullable=False
    )

    subject = db.Column(
        db.String(30),
        nullable=False,
        index=True
    )

    deadline = db.Column(
        db.DateTime,
        nullable=False,
        index=True
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

#----------RELATIONSHIPS-----------

    admin = db.relationship(
        "User",
        back_populates="assignments_created"
    )

    questions = db.relationship(
        "AssignmentQuestion",
        back_populates="assignment",
        cascade="all, delete-orphan"
    )

    submissions = db.relationship(
        "AssignmentSubmission",
        back_populates="assignment_submitted",
        cascade="all, delete-orphan"
    )