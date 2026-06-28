from app.extensions import db
from datetime import datetime


class LiveQuizResult(db.Model):

    __tablename__ = "live_quiz_results"

    __table_args__ = (
        db.UniqueConstraint(
            "live_class_id",
            "student_id",
            name="uq_live_class_student"
        ),
        db.Index(
            "ix_live_class_rank",
            "live_class_id",
            "rank"
        ),
        db.CheckConstraint(
            "percentage >= 0 AND percentage <= 100",
            name="check_percentage_range"
        ),
        db.CheckConstraint(
            "rank > 0",
            name="check_positive_rank"
        ),
        db.CheckConstraint(
            "correct_answers <= total_questions",
            name="check_correct_answers"
        ),
        db.CheckConstraint(
            "total_score >= 0",
            name="check_positive_score"
        ),
        db.CheckConstraint(
            "correct_answers >= 0",
            name="check_positive_correct_answers"
        ),
        db.CheckConstraint(
           "total_questions >= 0",
           name="check_positive_total_questions"
        )  

    )


    id = db.Column(
        db.Integer,
        primary_key=True
    )

    live_class_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "live_class.id",
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

    total_score = db.Column(
        db.Integer,
        default=0,
        nullable=False
    )

    correct_answers = db.Column(
        db.Integer,
        default=0,
        nullable=False
    )

    total_questions = db.Column(
        db.Integer,
        default=0,
        nullable=False

    )

    #------- Optional (useful for analytics without recalculating)-----

    percentage = db.Column(
        db.Float,
        default=0,
        nullable=False
    )

    rank = db.Column(
        db.Integer,
        nullable=True
    )

    completed_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        nullable=False
    )

    # =========================
    # RELATIONSHIPS
    # =========================

    live_class = db.relationship(
        "LiveClass",
        back_populates="quiz_results"
    )

    student = db.relationship(
        "User",
        back_populates="live_quiz_results"
    )

    def __repr__(self):
        return f"<LiveQuizResult student={self.student_id} score={self.total_score}>"