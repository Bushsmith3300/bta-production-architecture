from app.extensions import db


# ---------------- QUESTIONS ----------------
class Question(db.Model):
    __tablename__ = "question"

    id = db.Column(db.Integer, primary_key=True)

    topic = db.Column(db.String(100), nullable=False)

    question_text = db.Column(db.String(500), nullable=False)

    option_a = db.Column(db.String(300), nullable=False)
    option_b = db.Column(db.String(300), nullable=False)
    option_c = db.Column(db.String(300), nullable=False)
    option_d = db.Column(db.String(300), nullable=False)

    correct_answer = db.Column(db.String(1), nullable=False)

    explanation = db.Column(db.String(1000), nullable=True)


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