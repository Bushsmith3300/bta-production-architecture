from datetime import datetime, timezone

from sqlalchemy import CheckConstraint

from app.extensions import db


class PracticeSession(db.Model):

    __tablename__ = "practice_sessions"

    # DATABASE CONSTRAINTS
    __table_args__ = (

        CheckConstraint(
            "current_question_index >= 0",
            name="check_practice_session_question_index"
        ),

        CheckConstraint(
            "total_questions > 0",
            name="check_practice_session_total_questions"
        ),

        CheckConstraint(
            "correct_answers >= 0 AND correct_answers <= total_questions",
            name="check_practice_session_correct_answers"
        ),

    )

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "users.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    subject_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "subjects.id"
        ),
        nullable=False,
        index=True
    )

    topic = db.Column(
        db.String(150),
        nullable=False,
        index=True
    )

    # Preserves the original randomised question sequence.
    question_ids = db.Column(
        db.JSON,
        nullable=False
    )

    # Tracks the student's current position in the quiz.
    current_question_index = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    total_questions = db.Column(
        db.Integer,
        nullable=False
    )

    correct_answers = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    status = db.Column(
        db.String(20),
        nullable=False,
        default="in_progress",
        index=True
    )

    started_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    last_activity_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc)
    )

    completed_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True
    )

    # RELATIONSHIPS

    user = db.relationship(
        "User",
        back_populates="practice_sessions"
    )

    subject = db.relationship(
        "Subject",
        back_populates="practice_sessions"
    )

    user_history = db.relationship(
        "UserHistory",
        back_populates="practice_session"
    )

    # REPRESENTATION

    def __repr__(self):

        return (
            f"<PracticeSession "
            f"id={self.id} "
            f"user_id={self.user_id} "
            f"status={self.status}>"
        )
