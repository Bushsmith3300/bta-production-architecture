from app.extensions import db
from datetime import datetime, timezone


class LiveQuizAnswer(db.Model):

    __tablename__ = "live_quiz_answers"

    __table_args__ = (
        db.UniqueConstraint(
            "live_quiz_id",
            "question_id",
            "student_id",
            name="uq_livequiz_question_student"
        ),

        db.Index(
            "idx_quiz_student_score",
            "live_quiz_id",
            "student_id",
            "score"
        ),
    )

    id = db.Column(db.Integer, primary_key=True)

    live_quiz_id = db.Column(
        db.Integer,
        db.ForeignKey("live_class.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    question_id = db.Column(
        db.Integer,
        db.ForeignKey("question.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    student_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    selected_answer = db.Column(
        db.String(1),
        nullable=False
    )

    is_correct = db.Column(
        db.Boolean,
        nullable=False
    )

    score = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    answered_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # =========================
    # RELATIONSHIPS
    # =========================

    live_class = db.relationship(
        "LiveClass",
        back_populates="live_quiz_answers"
    )

    question = db.relationship(
        "Question",
        back_populates="live_quiz_answers"
    )

    student = db.relationship(
        "User",
        back_populates="live_quiz_answers"
    )