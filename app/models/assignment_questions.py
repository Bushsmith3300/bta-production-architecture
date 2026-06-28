from app.extensions import db


class AssignmentQuestion(db.Model):

    __tablename__ = "assignment_questions"

    __table_args__ = (
        db.UniqueConstraint(
            "assignment_id",
            "question_id",
            name="uq_assignment_question"
        ),
        db.UniqueConstraint(
            "assignment_id",
            "position",
            name="uq_assignment_position"
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

    question_id = db.Column(
        db.Integer,
        db.ForeignKey(
            "question.id",
            ondelete="CASCADE"
        ),
        nullable=False,
        index=True
    )

    position = db.Column(
        db.Integer,
        nullable=False
        
    )

    # =========================
    # RELATIONSHIPS
    # =========================

    assignment = db.relationship(
        "Assignment",
        back_populates="questions"
    )

    question = db.relationship(
        "Question",
        back_populates="assignment_questions"
    )