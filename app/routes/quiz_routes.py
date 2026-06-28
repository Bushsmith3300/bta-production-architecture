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
@quiz_bp.route("/questions/<path:topic>")
@login_required
def get_questions(topic):

    topic = topic.lower().strip()

    questions = (
        Question.query
        .filter(Question.topic.ilike(f"%{topic}%"))
        .order_by(func.random())
        .all()
    )

    return jsonify({
        "questions": [
            {
                "question": q.question_text,
                "options": [
                    {
                        "letter": "A",
                        "text": q.option_a
                    },
                    {
                        "letter": "B",
                        "text": q.option_b
                    },
                    {
                        "letter": "C",
                        "text": q.option_c
                    },
                    {
                        "letter": "D",
                        "text": q.option_d
                    }
                ],
                "answer": q.correct_answer,
                "explanation": q.explanation
            }
            for q in questions
        ]
    })


# ---------------- QUIZ PAGE ----------------
@quiz_bp.route("/quiz/<path:topic>")
@login_required
def quiz(topic):

    user = db.session.get(
        User,
        session["user_id"]
    )

    if not user:
        session.clear()
        return redirect(
            url_for("auth.login")
        )

    return render_template(
        "quiz_screen2.html",
        topic=topic,
        user=user
    )