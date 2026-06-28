from app.extensions import db
from datetime import datetime


class AssignmentSubmission(db.Model):

    __tablename__ = "assignment_submissions"

    __table_args__ = (
        db.UniqueConstraint(
            "assignment_id",
            "student_id",
            name="unique_assignment_submission"
        ),
    )

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    assignment_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "assignments.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "users.id",
            ondelete="SET NULL"
        ),
        nullable=True,
        index=True
    )


    score = db.Column(
        db.Integer
    )

    total_questions = db.Column(
        db.Integer,
        nullable=False
    )

    percentage = db.Column(
        db.Float
    )

    submitted_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    submit_status = db.Column(
        db.Enum(
            "pending",
            "submitted",
            "graded",
            name="submission_status"
        ),
        default="pending",
        nullable=False
    )

    # ---------------- Relationships ----------------

    assignment_submitted = db.relationship(
        "Assignment",
        back_populates="submissions"
    )

    student = db.relationship(
        "User",
        back_populates="assignment_submissions"
    )

    answers = db.relationship(
        "StudentAnswer",
        back_populates="submission",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<AssignmentSubmission {self.id}>"