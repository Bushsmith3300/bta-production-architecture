from flask import (
Blueprint,
jsonify,
render_template,
request,
session,
)

from sqlalchemy import func
from datetime import datetime, timezone

from app.extensions import db
from app.models.question import Question
from app.models.subject import Subject
from app.models.user import User
from app.models.user_history import UserHistory
from app.models.user_progress import UserProgress
from app.practice_session import PracticeSession
from app.utils.decorators import login_required

quiz_bp = Blueprint("quiz", name)

def get_logged_in_user():
"""Retrieve the authenticated user."""
user_id = session.get("user_id")

if not user_id:
    return None

return db.session.get(User, user_id)

--------------------------------------------------

START PERSONAL PRACTICE SESSION

--------------------------------------------------

@quiz_bp.route(
"/practice/start/<subject>/"path:topic" (path:topic)",
methods=["POST"]
)
@login_required
def start_practice_session(subject, topic):

user = get_logged_in_user()

if not user:
    return jsonify({"error": "Please log in again."}), 401

subject = subject.strip()
topic = topic.strip()

selected_subject = (
    Subject.query
    .filter(Subject.name == subject)
    .first()
)

if not selected_subject:
    return jsonify({"error": "Subject not found."}), 404

questions = (
    Question.query
    .filter(
        Question.subject_id == selected_subject.id,
        Question.topic == topic
    )
    .order_by(func.random())
    .limit(50)
    .all()
)

if not questions:
    return jsonify({
        "error": "No questions found for this topic."
    }), 404

question_ids = [question.id for question in questions]

practice = PracticeSession(
    user_id=user.id,
    subject_id=selected_subject.id,
    topic=topic,
    question_ids=question_ids,
    current_question_index=0,
    total_questions=len(questions),
    correct_answers=0,
    status="in_progress"
)

try:
    db.session.add(practice)
    db.session.commit()

    return jsonify({
        "success": True,
        "session_id": practice.id,
        "subject": subject,
        "topic": topic,
        "total_questions": len(questions),
        "questions": [
            {
                "question_id": q.id,
                "question": q.question_text,
                "options": [
                    {"letter": "A", "text": q.option_a},
                    {"letter": "B", "text": q.option_b},
                    {"letter": "C", "text": q.option_c},
                    {"letter": "D", "text": q.option_d}
                ]
            }
            for q in questions
        ]
    })

except Exception:
    db.session.rollback()
    return jsonify({
        "error": "Unable to start practice session."
    }), 500

--------------------------------------------------

SUBMIT AN ANSWER

--------------------------------------------------

@quiz_bp.route(
"/practice/answer/"int:session_id" (int:session_id)",
methods=["POST"]
)
@login_required
def submit_practice_answer(session_id):

user = get_logged_in_user()

if not user:
    return jsonify({"error": "Please log in again."}), 401

data = request.get_json(silent=True) or {}

question_id = data.get("question_id")
selected_answer = data.get("selected_answer")

if not question_id or selected_answer not in ["A", "B", "C", "D"]:
    return jsonify({"error": "Invalid answer submission."}), 400

practice = PracticeSession.query.filter_by(
    id=session_id,
    user_id=user.id
).with_for_update().first()

if not practice:
    return jsonify({"error": "Practice session not found."}), 404

if practice.status != "in_progress":
    return jsonify({
        "error": "This practice session is no longer active."
    }), 409

if question_id not in (practice.question_ids or []):
    return jsonify({
        "error": "This question does not belong to the practice session."
    }), 403

# Prevent the same question from being recorded twice.
existing_answer = UserHistory.query.filter_by(
    user_id=user.id,
    question_id=question_id,
    practice_session_id=practice.id
).first()

if existing_answer:
    return jsonify({
        "error": "This question has already been answered."
    }), 409

question = db.session.get(Question, question_id)

if not question:
    return jsonify({"error": "Question not found."}), 404

correct = (
    selected_answer == question.correct_answer.strip().upper()
)

history = UserHistory(
    user_id=user.id,
    question_id=question.id,
    selected_answer=selected_answer,
    is_correct=correct,
    practice_session_id=practice.id
)

try:
    db.session.add(history)

    if correct:
        practice.correct_answers += 1

    practice.last_activity_at = datetime.now(timezone.utc)

    db.session.commit()

    return jsonify({
        "success": True,
        "is_correct": correct,
        "correct_answer": question.correct_answer,
        "explanation": question.explanation
    })

except Exception:
    db.session.rollback()
    return jsonify({
        "error": "Unable to record your answer."
    }), 500

--------------------------------------------------

UPDATE CURRENT QUESTION POSITION

--------------------------------------------------

@quiz_bp.route(
"/practice/progress/"int:session_id" (int:session_id)",
methods=["POST"]
)
@login_required
def update_practice_position(session_id):

user = get_logged_in_user()

if not user:
    return jsonify({"error": "Please log in again."}), 401

data = request.get_json(silent=True) or {}
index = data.get("current_question_index")

if not isinstance(index, int) or index < 0:
    return jsonify({"error": "Invalid question position."}), 400

practice = PracticeSession.query.filter_by(
    id=session_id,
    user_id=user.id,
    status="in_progress"
).first()

if not practice:
    return jsonify({"error": "Active session not found."}), 404

if index >= practice.total_questions:
    return jsonify({"error": "Invalid question position."}), 400

try:
    practice.current_question_index = index
    practice.last_activity_at = datetime.now(timezone.utc)
    db.session.commit()

    return jsonify({"success": True})

except Exception:
    db.session.rollback()
    return jsonify({"error": "Unable to update progress."}), 500

--------------------------------------------------

COMPLETE PERSONAL PRACTICE SESSION

--------------------------------------------------

@quiz_bp.route(
"/practice/complete/"int:session_id" (int:session_id)",
methods=["POST"]
)
@login_required
def complete_practice_session(session_id):

user = get_logged_in_user()

if not user:
    return jsonify({"error": "Please log in again."}), 401

practice = PracticeSession.query.filter_by(
    id=session_id,
    user_id=user.id
).with_for_update().first()

if not practice:
    return jsonify({"error": "Practice session not found."}), 404

if practice.status == "completed":
    return jsonify({
        "success": True,
        "message": "This session has already been completed.",
        "correct_answers": practice.correct_answers,
        "total_questions": practice.total_questions
    })

if practice.status != "in_progress":
    return jsonify({
        "error": "This session cannot be completed."
    }), 409

try:
    selected_subject = db.session.get(
        Subject,
        practice.subject_id
    )

    if not selected_subject:
        return jsonify({"error": "Subject not found."}), 404

    answered_count = UserHistory.query.filter_by(
        user_id=user.id,
        practice_session_id=practice.id
    ).count()

    correct_count = UserHistory.query.filter_by(
        user_id=user.id,
        practice_session_id=practice.id,
        is_correct=True
    ).count()

    practice.correct_answers = correct_count
    practice.status = "completed"
    practice.completed_at = datetime.now(timezone.utc)
    practice.last_activity_at = datetime.now(timezone.utc)

    progress = UserProgress.query.filter_by(
        user_id=user.id,
        subject=selected_subject.name
    ).first()

    if not progress:
        progress = UserProgress(
            user_id=user.id,
            subject=selected_subject.name,
            questions_attempted=0,
            correct_answers=0
        )
        db.session.add(progress)

    progress.questions_attempted += answered_count
    progress.correct_answers += correct_count
    progress.last_attempt = datetime.now(timezone.utc)

    db.session.commit()

    accuracy = (
        round((correct_count / answered_count) * 100, 1)
        if answered_count else 0
    )

    return jsonify({
        "success": True,
        "correct_answers": correct_count,
        "questions_attempted": answered_count,
        "total_questions": practice.total_questions,
        "accuracy": accuracy
    })

except Exception:
    db.session.rollback()
    return jsonify({
        "error": "Unable to complete practice session."
    }), 500

--------------------------------------------------

EXISTING QUIZ PAGE

--------------------------------------------------

@quiz_bp.route("/quiz/<subject>/"path:topic" (path:topic)")
@login_required
def quiz(subject, topic):

user = get_logged_in_user()

if not user:
    session.clear()
    return jsonify({"error": "Please log in again."}), 401

return render_template(
    "quiz_screen2.html",
    user=user,
    subject=subject,
    topic=topic
)
