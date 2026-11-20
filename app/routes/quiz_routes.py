from datetime import datetime, timedelta, timezone

from flask import (
    Blueprint,
    jsonify,
    render_template,
    request,
    session
)

from sqlalchemy import func, or_

from app.extensions import db

from app.models.question import Question
from app.models.subject import Subject
from app.models.user import User
from app.models.user_history import UserHistory
from app.models.user_progress import UserProgress
from app.models.practice_session import PracticeSession

from app.utils.decorators import login_required


quiz_bp = Blueprint("quiz", __name__)

SESSION_DURATION = timedelta(hours=24)
MAX_QUESTIONS = 50


# ---------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------

def utc_now():
    """Return the current timezone-aware UTC time."""
    return datetime.now(timezone.utc)


def make_naive_utc(value):
    """
    Convert a datetime to naive UTC.

    UserHistory.attempted_at and UserProgress.last_attempt
    may use timezone-naive database columns.
    """
    if value is None:
        return datetime.utcnow()

    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    return value


def session_has_expired(practice_session):
    """Check whether a practice session has exceeded 24 hours."""

    last_activity = practice_session.last_activity_at

    if last_activity.tzinfo is None:
        last_activity = last_activity.replace(tzinfo=timezone.utc)

    return utc_now() - last_activity > SESSION_DURATION


def get_current_user():
    """Retrieve the logged-in user."""

    user_id = session.get("user_id")

    if not user_id:
        return None

    return db.session.get(User, user_id)


def get_available_subject(subject_name):
    """
    Retrieve an active subject that permits personal practice.
    """

    return Subject.query.filter(
        func.lower(Subject.name) == subject_name.lower(),
        Subject.is_active.is_(True),
        Subject.is_practice_enabled.is_(True)
    ).first()


def get_subject_questions(subject):
    """
    Retrieve questions belonging to the selected subject.

    Supports both subject_id and the older subject string
    field because some existing questions may have a NULL
    subject_id.
    """

    return Question.query.filter(
        Question.topic.isnot(None),
        or_(
            Question.subject_id == subject.id,
            func.lower(Question.subject) == subject.name.lower()
        )
    )


def serialize_question(question):
    """
    Return question data without exposing the correct answer
    or explanation before the student submits an answer.
    """

    return {
        "question_id": question.id,
        "question": question.question_text,
        "options": {
            "A": question.option_a,
            "B": question.option_b,
            "C": question.option_c,
            "D": question.option_d
        }
    }


def get_saved_answers(practice_session):
    """
    Retrieve previously submitted answers for a session.

    Correct answers and explanations are returned only for
    questions the student has already answered.
    """

    records = UserHistory.query.filter_by(
        user_id=practice_session.user_id,
        practice_session_id=practice_session.id
    ).all()

    saved_answers = {}

    for record in records:

        question = db.session.get(Question, record.question_id)

        if not question:
            continue

        saved_answers[str(record.question_id)] = {
            "selected_answer": record.selected_answer,
            "is_correct": record.is_correct,
            "correct_answer": question.correct_answer,
            "explanation": question.explanation
        }

    return saved_answers


def get_session_questions(practice_session):
    """
    Retrieve questions in their originally stored order.
    """

    question_ids = practice_session.question_ids or []

    if not question_ids:
        return []

    questions = Question.query.filter(
        Question.id.in_(question_ids)
    ).all()

    question_map = {
        question.id: question
        for question in questions
    }

    ordered_questions = []

    for question_id in question_ids:

        question = question_map.get(question_id)

        if question:
            ordered_questions.append(question)

    return ordered_questions


def abandon_session(practice_session):
    """Mark an unfinished session as abandoned."""

    practice_session.status = "abandoned"
    practice_session.last_activity_at = utc_now()


def validate_active_session(practice_session):
    """
    Check whether a session can still accept answers.

    Returns None if valid, otherwise a JSON response.
    """

    if practice_session.status == "completed":

        return jsonify({
            "success": False,
            "message": "This practice session has already been completed."
        }), 409

    if practice_session.status == "abandoned":

        return jsonify({
            "success": False,
            "message": "This practice session has expired."
        }), 410

    if session_has_expired(practice_session):

        abandon_session(practice_session)
        db.session.commit()

        return jsonify({
            "success": False,
            "message": "Your 24-hour practice session has expired. Please start a new quiz."
        }), 410

    return None


# ---------------------------------------------------------
# START OR RESUME PERSONAL PRACTICE
# ---------------------------------------------------------

@quiz_bp.route(
    "/practice/start/<subject>/<path:topic>",
    methods=["POST"]
)
@login_required
def start_practice(subject, topic):

    user = get_current_user()

    if not user:
        return jsonify({
            "success": False,
            "message": "Please log in again."
        }), 401

    selected_subject = get_available_subject(subject)

    if not selected_subject:
        return jsonify({
            "success": False,
            "message": "This subject is currently unavailable for practice."
        }), 404

    now = utc_now()

    # -----------------------------------------------------
    # 1. Find expired sessions belonging to this student.
    # -----------------------------------------------------

    expired_sessions = PracticeSession.query.filter(
        PracticeSession.user_id == user.id,
        PracticeSession.status == "in_progress",
        PracticeSession.last_activity_at < now - SESSION_DURATION
    ).all()

    for old_session in expired_sessions:
        abandon_session(old_session)

    # -----------------------------------------------------
    # 2. Look for an unfinished session for this topic.
    # -----------------------------------------------------

    existing_session = PracticeSession.query.filter(
        PracticeSession.user_id == user.id,
        PracticeSession.subject_id == selected_subject.id,
        PracticeSession.topic == topic,
        PracticeSession.status == "in_progress",
        PracticeSession.last_activity_at >= now - SESSION_DURATION
    ).order_by(
        PracticeSession.last_activity_at.desc()
    ).first()

    if existing_session:

        questions = get_session_questions(existing_session)

        if len(questions) != existing_session.total_questions:

            abandon_session(existing_session)
            db.session.commit()

            return jsonify({
                "success": False,
                "message": "Some questions in your previous session are no longer available. Please start a new quiz."
            }), 409

        existing_session.last_activity_at = now

        db.session.commit()

        return jsonify({
            "success": True,
            "resumed": True,
            "message": "Your previous practice session has been restored.",
            "session_id": existing_session.id,
            "subject": selected_subject.name,
            "topic": existing_session.topic,
            "total_questions": existing_session.total_questions,
            "current_question_index": existing_session.current_question_index,
            "questions": [
                serialize_question(question)
                for question in questions
            ],
            "saved_answers": get_saved_answers(existing_session)
        })

    # -----------------------------------------------------
    # 3. No resumable session. Create a fresh session.
    # -----------------------------------------------------

    question_query = get_subject_questions(selected_subject)

    selected_questions = question_query.filter(
        Question.topic == topic
    ).order_by(
        func.random()
    ).limit(MAX_QUESTIONS).all()

    if not selected_questions:

        db.session.commit()

        return jsonify({
            "success": False,
            "message": "No questions are currently available for this topic."
        }), 404

    question_ids = [
        question.id
        for question in selected_questions
    ]

    new_session = PracticeSession(
        user_id=user.id,
        subject_id=selected_subject.id,
        topic=topic,
        question_ids=question_ids,
        current_question_index=0,
        total_questions=len(question_ids),
        correct_answers=0,
        status="in_progress",
        started_at=now,
        last_activity_at=now
    )

    db.session.add(new_session)
    db.session.commit()

    return jsonify({
        "success": True,
        "resumed": False,
        "message": "A new practice session has started.",
        "session_id": new_session.id,
        "subject": selected_subject.name,
        "topic": topic,
        "total_questions": new_session.total_questions,
        "current_question_index": 0,
        "questions": [
            serialize_question(question)
            for question in selected_questions
        ],
        "saved_answers": {}
    })


# ---------------------------------------------------------
# SUBMIT AN ANSWER
# ---------------------------------------------------------

@quiz_bp.route(
    "/practice/answer/<int:session_id>",
    methods=["POST"]
)
@login_required
def submit_practice_answer(session_id):

    user = get_current_user()

    if not user:
        return jsonify({
            "success": False,
            "message": "Please log in again."
        }), 401

    data = request.get_json(silent=True) or {}

    question_id = data.get("question_id")
    selected_answer = data.get("selected_answer")

    if not question_id or not selected_answer:

        return jsonify({
            "success": False,
            "message": "Question ID and selected answer are required."
        }), 400

    selected_answer = str(selected_answer).strip().upper()

    if selected_answer not in ["A", "B", "C", "D"]:

        return jsonify({
            "success": False,
            "message": "Invalid answer selection."
        }), 400

    # Lock the session row to protect concurrent submissions.
    practice_session = PracticeSession.query.filter_by(
        id=session_id,
        user_id=user.id
    ).with_for_update().first()

    if not practice_session:

        return jsonify({
            "success": False,
            "message": "Practice session not found."
        }), 404

    validation_error = validate_active_session(practice_session)

    if validation_error:
        return validation_error

    question_ids = practice_session.question_ids or []

    try:
        question_id = int(question_id)
    except (TypeError, ValueError):

        return jsonify({
            "success": False,
            "message": "Invalid question ID."
        }), 400

    if question_id not in question_ids:

        return jsonify({
            "success": False,
            "message": "This question does not belong to your practice session."
        }), 403

    question = Question.query.filter(
        Question.id == question_id,
        Question.topic == practice_session.topic,
        or_(
            Question.subject_id == practice_session.subject_id,
            func.lower(Question.subject) == (
                practice_session.subject.name.lower()
            )
        )
    ).first()

    if not question:

        return jsonify({
            "success": False,
            "message": "Question not found."
        }), 404

    # -----------------------------------------------------
    # Idempotency: do not save the same answer twice.
    # -----------------------------------------------------

    existing_answer = UserHistory.query.filter_by(
        user_id=user.id,
        practice_session_id=practice_session.id,
        question_id=question.id
    ).first()

    if existing_answer:

        practice_session.last_activity_at = utc_now()
        db.session.commit()

        return jsonify({
            "success": True,
            "already_answered": True,
            "selected_answer": existing_answer.selected_answer,
            "is_correct": existing_answer.is_correct,
            "correct_answer": question.correct_answer,
            "explanation": question.explanation,
            "message": "Your answer has already been saved."
        })

    # -----------------------------------------------------
    # Save the new answer.
    # -----------------------------------------------------

    is_correct = (
        selected_answer == str(question.correct_answer).strip().upper()
    )

    answer_record = UserHistory(
        user_id=user.id,
        question_id=question.id,
        selected_answer=selected_answer,
        is_correct=is_correct,
        attempted_at=datetime.utcnow(),
        practice_session_id=practice_session.id
    )

    db.session.add(answer_record)

    if is_correct:
        practice_session.correct_answers += 1

    practice_session.last_activity_at = utc_now()

    db.session.commit()

    return jsonify({
        "success": True,
        "already_answered": False,
        "selected_answer": selected_answer,
        "is_correct": is_correct,
        "correct_answer": question.correct_answer,
        "explanation": question.explanation,
        "message": "Your answer has been saved."
    })


# ---------------------------------------------------------
# SAVE CURRENT QUESTION POSITION
# ---------------------------------------------------------

@quiz_bp.route(
    "/practice/progress/<int:session_id>",
    methods=["POST"]
)
@login_required
def update_practice_progress(session_id):

    user = get_current_user()

    if not user:
        return jsonify({
            "success": False,
            "message": "Please log in again."
        }), 401

    data = request.get_json(silent=True) or {}

    current_index = data.get("current_question_index")

    if current_index is None:

        return jsonify({
            "success": False,
            "message": "Current question position is required."
        }), 400

    try:
        current_index = int(current_index)
    except (TypeError, ValueError):

        return jsonify({
            "success": False,
            "message": "Invalid question position."
        }), 400

    practice_session = PracticeSession.query.filter_by(
        id=session_id,
        user_id=user.id
    ).with_for_update().first()

    if not practice_session:

        return jsonify({
            "success": False,
            "message": "Practice session not found."
        }), 404

    validation_error = validate_active_session(practice_session)

    if validation_error:
        return validation_error

    if not 0 <= current_index < practice_session.total_questions:

        return jsonify({
            "success": False,
            "message": "Invalid question position."
        }), 400

    practice_session.current_question_index = current_index
    practice_session.last_activity_at = utc_now()

    db.session.commit()

    return jsonify({
        "success": True,
        "current_question_index": current_index
    })


# ---------------------------------------------------------
# COMPLETE PERSONAL PRACTICE SESSION
# ---------------------------------------------------------

@quiz_bp.route(
    "/practice/complete/<int:session_id>",
    methods=["POST"]
)
@login_required
def complete_practice(session_id):

    user = get_current_user()

    if not user:
        return jsonify({
            "success": False,
            "message": "Please log in again."
        }), 401

    practice_session = PracticeSession.query.filter_by(
        id=session_id,
        user_id=user.id
    ).with_for_update().first()

    if not practice_session:

        return jsonify({
            "success": False,
            "message": "Practice session not found."
        }), 404

    # -----------------------------------------------------
    # Return existing results if already completed.
    # This prevents double-counting in UserProgress.
    # -----------------------------------------------------

    if practice_session.status == "completed":

        records = UserHistory.query.filter_by(
            user_id=user.id,
            practice_session_id=practice_session.id
        ).all()

        attempted = len(records)

        correct = sum(
            1 for record in records
            if record.is_correct
        )

        accuracy = (
            round((correct / attempted) * 100, 2)
            if attempted else 0
        )

        return jsonify({
            "success": True,
            "already_completed": True,
            "total_questions": practice_session.total_questions,
            "attempted": attempted,
            "correct": correct,
            "incorrect": attempted - correct,
            "unanswered": practice_session.total_questions - attempted,
            "accuracy": accuracy
        })

    validation_error = validate_active_session(practice_session)

    if validation_error:
        return validation_error

    # -----------------------------------------------------
    # Calculate results using saved server-side answers.
    # -----------------------------------------------------

    records = UserHistory.query.filter_by(
        user_id=user.id,
        practice_session_id=practice_session.id
    ).all()

    attempted = len(records)

    correct = sum(
        1 for record in records
        if record.is_correct
    )

    incorrect = attempted - correct

    unanswered = (
        practice_session.total_questions - attempted
    )

    accuracy = (
        round((correct / attempted) * 100, 2)
        if attempted else 0
    )

    now = utc_now()

    # -----------------------------------------------------
    # Mark session completed.
    # -----------------------------------------------------

    practice_session.status = "completed"
    practice_session.correct_answers = correct
    practice_session.completed_at = now
    practice_session.last_activity_at = now

    # -----------------------------------------------------
    # Update overall subject progress.
    # -----------------------------------------------------

    progress = UserProgress.query.filter_by(
        user_id=user.id,
        subject=practice_session.subject.name
    ).with_for_update().first()

    if not progress:

        progress = UserProgress(
            user_id=user.id,
            subject=practice_session.subject.name,
            questions_attempted=0,
            correct_answers=0
        )

        db.session.add(progress)

    progress.questions_attempted += attempted
    progress.correct_answers += correct
    progress.last_attempt = datetime.utcnow()

    db.session.commit()

    return jsonify({
        "success": True,
        "already_completed": False,
        "total_questions": practice_session.total_questions,
        "attempted": attempted,
        "correct": correct,
        "incorrect": incorrect,
        "unanswered": unanswered,
        "accuracy": accuracy,
        "message": "Your practice session has been completed."
    })


# ---------------------------------------------------------
# DISPLAY QUIZ PAGE
# ---------------------------------------------------------

@quiz_bp.route(
    "/quiz/<subject>/<path:topic>",
    methods=["GET"]
)
@login_required
def quiz(subject, topic):

    user = get_current_user()

    if not user:
        return "Please log in again.", 401

    return render_template(
        "quiz_screen2.html",
        user=user,
        subject=subject,
        topic=topic
)
