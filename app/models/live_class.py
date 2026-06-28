from app.extensions import db
from datetime import datetime


class LiveClass(db.Model):

    __tablename__ = "live_class"

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

    subject = db.Column(
        db.String(30),
        nullable=False,
        index=True
    )

    link = db.Column(
        db.String(200),
        nullable=True
    )

    is_live = db.Column(
        db.Boolean,
        default=False,
        nullable=False
    )

    # =========================
    # LIVE QUIZ FEATURES
    # =========================


    started_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    ended_at = db.Column(
        db.DateTime,
        nullable=True
    )

    # =========================
    # RELATIONSHIPS
    # =========================

    live_quiz_questions = db.relationship(
        "LiveQuizQuestion",
        back_populates="live_class",
        cascade="all, delete-orphan"
    )

    admin = db.relationship(
        "User",
        back_populates="live_class"
    )

    live_quiz_answers = db.relationship(
        "LiveQuizAnswer",
        back_populates="live_class",
        cascade="all, delete-orphan"
    )

    quiz_results = db.relationship(
        "LiveQuizResult",
        back_populates="live_class",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<LiveClass {self.id}>"