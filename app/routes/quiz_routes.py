# app/routes/quiz_routes.py

from flask import (
    Blueprint,
    jsonify,
    render_template,
    redirect,
    url_for,
    session
)

from sqlalchemy import func

from app.extensions import db

from app.models.question import Question
from app.models.user import User

from app.utils.decorators import login_required


# ---------------- BLUEPRINT ----------------
quiz_bp = Blueprint(
    "quiz",
    __name__
)


# ---------------- QUESTIONS API ----------------

@quiz_bp.route("/questions/<subject>/<path:topic>")
@login_required
def get_questions(subject, topic):

    subject = subject.strip().title()
    topic = topic.strip().lower()

    questions = (
        Question.query
        .filter(
            Question.subject == subject,
            Question.topic.ilike(f"%{topic}%")
        )
        .order_by(func.random())
        .all()
    )

    return jsonify({
        "questions": [
            {
                "question_id": q.id,
                "question": q.question_text,
                "options": [
                    {"letter": "A", "text": q.option_a},
                    {"letter": "B", "text": q.option_b},
                    {"letter": "C", "text": q.option_c},
                    {"letter": "D", "text": q.option_d},
                ],
                "answer": q.correct_answer,
                "explanation": q.explanation
            }
            for q in questions
        ]
    })



# ---------------- QUIZ PAGE ----------------
@quiz_bp.route("/quiz/<subject>/<path:topic>")
@login_required
def quiz(subject, topic):

    user = db.session.get(User, session["user_id"])

    if not user:
        session.clear()
        return redirect(
            url_for("auth.login")
        )

    return render_template(
        "quiz_screen2.html",
        user=user,
        subject=subject,
        topic=topic
    )