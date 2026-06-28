from app.extensions import db
from datetime import datetime


class StudentAnswer(db.Model):

    __tablename__ = "student_answers"

    __table_args__ = (

        # One answer per question per submission
        db.UniqueConstraint(
            "submission_id",
            "question_id",
            name="uq_submission_question"
        ),

        # Ensure only one answer type is used (MCQ OR essay, not both)
        db.CheckConstraint(
            "NOT (selected_option IS NOT NULL AND text_answer IS NOT NULL)",
            name="check_single_answer_type"
        ),

        # Ensure at least one answer exists
        db.CheckConstraint(
            "selected_option IS NOT NULL OR text_answer IS NOT NULL",
            name="check_answer_exists"
        ),

        # Valid MCQ options only (NULL allowed for essay questions)
        db.CheckConstraint(
            "selected_option IS NULL OR selected_option IN ('A','B','C','D')",
            name="check_valid_answer"
        ),

        # Score cannot be negative
        db.CheckConstraint(
            "score_awarded >= 0",
            name="check_positive_score"
        ),
    )

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    submission_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "assignment_submissions.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    question_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "question.id",
            ondelete="RESTRICT"
        ),
        nullable=False,
        index=True
    )

    # =========================
    # ANSWERS
    # =========================

    # MCQ / True-False
    selected_option = db.Column(
        db.String(1),
        nullable=True
    )

    # Essay / Short Answer
    text_answer = db.Column(
        db.Text,
        nullable=True
    )

    # =========================
    # GRADING
    # =========================

    score_awarded = db.Column(
        db.Integer,
        default=0,
        nullable=False
    )

    # True / False / NULL (not graded yet)
    is_correct = db.Column(
        db.Boolean,
        nullable=True
    )

    graded_at = db.Column(
        db.DateTime,
        nullable=True
    )

    # =========================
    # TIMESTAMPS
    # =========================

    answered_at = db.Column(
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

    # =========================
    # RELATIONSHIPS
    # =========================

    submission = db.relationship(
        "AssignmentSubmission",
        back_populates="answers"
    )

    question = db.relationship(
        "Question",
        back_populates="student_answers"
    )

    # =========================
    # DEBUG
    # =========================

    def __repr__(self):
        return (
            f"<StudentAnswer "
            f"submission={self.submission_id} "
            f"question={self.question_id}>"
        )