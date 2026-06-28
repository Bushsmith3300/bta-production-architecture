from app.extensions import db
from datetime import datetime


class LiveQuizQuestion(db.Model):

    __tablename__ = "live_quiz_questions"

    id = db.Column(db.Integer, primary_key=True)

    live_class_id = db.Column(
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

    order_index = db.Column(
        db.Integer,
        nullable=False
    )

    started_at = db.Column(
        db.DateTime,
        nullable=True
    )

    duration_seconds = db.Column(
        db.Integer,
        default=30
    )

    # =========================
    # RELATIONSHIPS
    # =========================

    live_class = db.relationship(
        "LiveClass",
        back_populates="live_quiz_questions"
    )

    question = db.relationship(
        "Question",
        back_populates="live_quiz_questions"
    )