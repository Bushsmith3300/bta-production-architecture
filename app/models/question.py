from app.extensions import db


# ---------------- QUESTIONS ----------------
class Question(db.Model):
    __tablename__ = "question"

    id = db.Column(db.Integer, primary_key=True)

    topic = db.Column(db.String(100), nullable=False)

    question_text = db.Column(db.Text, nullable=False)

    option_a = db.Column(db.String(300), nullable=False)
    option_b = db.Column(db.String(300), nullable=False)
    option_c = db.Column(db.String(300), nullable=False)
    option_d = db.Column(db.String(300), nullable=False)

    correct_answer = db.Column(db.String(1), nullable=False)

    explanation = db.Column(db.Text, nullable=True)

    subject = db.Column(db.String(50), default="chemistry", nullable=False)

    difficulty = db.Column(
        db.Enum(
        "DOK_1",
        "DOK_2",
        "DOK_3",
        "DOK_4",
        name="difficulty_level"
    ),
        nullable=False,
        default="DOK_1"
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=db.func.now()
    )

    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=db.func.now(),
        onupdate=db.func.now()
    )


    question_hash = db.Column(
        db.String(64),
        nullable=False,
        index=True
    )

    # ======================================
    # RELATIONSHIPS (FIXED)
    # ======================================

    user_history = db.relationship(
        "UserHistory",
        back_populates="question"
    )

    assignment_questions = db.relationship(
        "AssignmentQuestion",
        back_populates="question"
    )

    live_quiz_questions = db.relationship(
        "LiveQuizQuestion",
        back_populates="question"
    )

    student_answers = db.relationship(
        "StudentAnswer",
        back_populates="question"
    )

    live_quiz_answers = db.relationship(
        "LiveQuizAnswer",
        back_populates="question",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Question {self.id}>"