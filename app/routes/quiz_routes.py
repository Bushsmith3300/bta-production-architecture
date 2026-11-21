from datetime import datetime, timedelta, timezone

from flask import (
    Blueprint,
    jsonify,
    render_template,
    request,
    session
)

from sqlalchemy import func, or_, and_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

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


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def utc_now():
    """Return the current timezone-aware UTC time."""

    return datetime.now(timezone.utc)


def session_has_expired(practice_session):
    """Determine whether a practice session has expired."""

    last_activity = practice_session.last_activity_at

    if last_activity is None:
        return True

    if last_activity.tzinfo is None:
        last_activity = last_activity.replace(
            tzinfo=timezone.utc
        )

    return utc_now() - last_activity > SESSION_DURATION


def get_current_user():
    """Retrieve the currently authenticated user."""

    user_id = session.get("user_id")

    if not user_id:
        return None

    return db.session.get(User, user_id)


def lock_current_user(user_id):
    """
    Lock the user row.

    This serialises session creation and completion operations
    for the same user.
    """

    return User.query.filter_by(
        id=user_id
    ).with_for_update().first()


def get_available_subject(subject_name):
    """Retrieve an active subject that permits personal practice."""

    return Subject.query.filter(
        func.lower(Subject.name) == subject_name.lower(),
        Subject.is_active.is_(True),
        Subject.is_practice_enabled.is_(True)
    ).first()


def question_subject_filter(subject_id, subject_name):
    """
    Match questions to the correct subject.

    Older questions without subject_id are supported through
    the subject string field.

    If subject_id is populated, it must match the selected
    subject. A conflicting subject string cannot override it.
    """

    return or_(
        Question.subject_id == subject_id,

        and_(
            Question.subject_id.is_(None),
            func.lower(Question.subject) == subject_name.lower()
        )
    )


def get_subject_questions(subject):
    """Return questions belonging to a selected subject."""

    return Question.query.filter(
        question_subject_filter(
            subject.id,
            subject.name
        )
    )


def serialize_question(question):
    """
    Return question information without exposing the correct
    answer before submission.
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


def get_session_questions(practice_session):
    """
    Retrieve questions in their originally stored order.

    Also verifies that the questions still belong to the
    session's subject and topic.
    """

    question_ids = practice_session.question_ids or []

    if not question_ids:
        return []

    questions = Question.query.filter(
        Question.id.in_(question_ids),
        Question.topic == practice_session.topic,
        question_subject_filter(
            practice_session.subject_id,
            practice_session.subject.name
        )
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


def get_saved_answers(practice_session):
    """
    Retrieve answers previously submitted during this session.

    Correct answers and explanations are only returned for
    questions the student has already answered.
    """

    records = UserHistory.query.filter_by(
        user_id=practice_session.user_id,
        practice_session_id=practice_session.id
    ).all()

    saved_answers = {}

    for record in records:

        question = db.session.get(
            Question,
            record.question_id
        )

        if not question:
            continue

        saved_answers[str(record.question_id)] = {
            "selected_answer": record.selected_answer,
            "is_correct": record.is_correct,
            "correct_answer": question.correct_answer,
            "explanation": question.explanation
        }

    return saved_answers


def abandon_session(practice_session):
    """Mark an unfinished session as abandoned."""

    practice_session.status = "abandoned"

    practice_session.last_activity_at = utc_now()


def validate_active_session(practice_session):
    """
    Validate a session before accepting answers or progress.

    Returns None when valid.
    Otherwise returns a Flask JSON response.
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

    if practice_session.status != "in_progress":

        return jsonify({
            "success": False,
            "message": "This practice session is not active."
        }), 409

    if session_has_expired(practice_session):

        abandon_session(practice_session)

        db.session.commit()

        return jsonify({
            "success": False,
            "message": "Your 24-hour practice session has expired. Please start a new quiz."
        }), 410

    return None


def get_answered_question_ids(practice_session):
    """Retrieve the IDs of questions already answered."""

    records = UserHistory.query.filter_by(
        user_id=practice_session.user_id,
        practice_session_id=practice_session.id
    ).with_entities(
        UserHistory.question_id
    ).all()

    return {
        record.question_id
        for record in records
    }


def calculate_session_results(practice_session):
    """
    Calculate results using database records rather than
    browser-submitted scores.
    """

    records = UserHistory.query.filter_by(
        user_id=practice_session.user_id,
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

    return {
        "total_questions": practice_session.total_questions,
        "attempted": attempted,
        "correct": correct,
        "incorrect": incorrect,
        "unanswered": unanswered,
        "accuracy": accuracy
    }


# =========================================================
# START OR RESUME PERSONAL PRACTICE
# =========================================================

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

    try:

        # Lock the user row to prevent simultaneous requests
        # from creating multiple active sessions.

        locked_user = lock_current_user(user.id)

        if not locked_user:

            return jsonify({
                "success": False,
                "message": "User account not found."
            }), 404

        selected_subject = get_available_subject(subject)

        if not selected_subject:

            return jsonify({
                "success": False,
                "message": "This subject is currently unavailable for practice."
            }), 404

        now = utc_now()

        # -------------------------------------------------
        # 1. Mark expired sessions as abandoned.
        # -------------------------------------------------

        active_sessions = PracticeSession.query.filter_by(
            user_id=user.id,
            status="in_progress"
        ).with_for_update().all()

        for old_session in active_sessions:

            if session_has_expired(old_session):

                abandon_session(old_session)

        # -------------------------------------------------
        # 2. Look for an unfinished session for this topic.
        # -------------------------------------------------

        existing_session = PracticeSession.query.filter(
            PracticeSession.user_id == user.id,
            PracticeSession.subject_id == selected_subject.id,
            PracticeSession.topic == topic,
            PracticeSession.status == "in_progress"
        ).order_by(
            PracticeSession.last_activity_at.desc()
        ).first()

        if existing_session:

            questions = get_session_questions(
                existing_session
            )

            if len(questions) != existing_session.total_questions:

                abandon_session(existing_session)

                db.session.commit()

                return jsonify({
                    "success": False,
                    "message": "Some questions in your previous session are no longer available. Please start a new quiz."
                }), 409

            if not (
                0 <= existing_session.current_question_index
                < existing_session.total_questions
            ):

                existing_session.current_question_index = 0

            existing_session.last_activity_at = now

            db.session.commit()

            saved_answers = get_saved_answers(
                existing_session
            )

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

                "saved_answers": saved_answers

            })

        # -------------------------------------------------
        # 3. No resumable session. Create a fresh session.
        # -------------------------------------------------

        selected_questions = get_subject_questions(
            selected_subject
        ).filter(
            Question.topic == topic
        ).order_by(
            func.random()
        ).limit(
            MAX_QUESTIONS
        ).all()

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

    except SQLAlchemyError:

        db.session.rollback()

        return jsonify({
            "success": False,
            "message": "Unable to start or restore your practice session. Please try again."
        }), 500


# =========================================================
# SUBMIT AN ANSWER
# =========================================================

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

    if question_id is None or selected_answer is None:

        return jsonify({
            "success": False,
            "message": "Question ID and selected answer are required."
        }), 400

    try:

        question_id = int(question_id)

    except (TypeError, ValueError):

        return jsonify({
            "success": False,
            "message": "Invalid question ID."
        }), 400

    selected_answer = str(
        selected_answer
    ).strip().upper()

    if selected_answer not in ["A", "B", "C", "D"]:

        return jsonify({
            "success": False,
            "message": "Invalid answer selection."
        }), 400

    try:

        # Lock the session to prevent concurrent answer
        # submissions from being recorded twice.

        practice_session = PracticeSession.query.filter_by(
            id=session_id,
            user_id=user.id
        ).with_for_update().first()

        if not practice_session:

            return jsonify({
                "success": False,
                "message": "Practice session not found."
            }), 404

        validation_error = validate_active_session(
            practice_session
        )

        if validation_error:
            return validation_error

        question_ids = practice_session.question_ids or []

        if question_id not in question_ids:

            return jsonify({
                "success": False,
                "message": "This question does not belong to your practice session."
            }), 403

        question = Question.query.filter(
            Question.id == question_id,

            Question.topic == practice_session.topic,

            question_subject_filter(
                practice_session.subject_id,
                practice_session.subject.name
            )

        ).first()

        if not question:

            return jsonify({
                "success": False,
                "message": "Question not found or does not belong to this session."
            }), 404

        # -------------------------------------------------
        # Check whether the question was already answered.
        # -------------------------------------------------

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

        # -------------------------------------------------
        # Save the answer.
        # -------------------------------------------------

        is_correct = (
            selected_answer ==
            str(question.correct_answer).strip().upper()
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

    except IntegrityError:

        # The unique database constraint provides a second
        # layer of protection against duplicate answers.

        db.session.rollback()

        existing_answer = UserHistory.query.filter_by(
            user_id=user.id,
            practice_session_id=session_id,
            question_id=question_id
        ).first()

        if existing_answer:

            question = db.session.get(
                Question,
                question_id
            )

            return jsonify({

                "success": True,

                "already_answered": True,

                "selected_answer": existing_answer.selected_answer,

                "is_correct": existing_answer.is_correct,

                "correct_answer": question.correct_answer,

                "explanation": question.explanation,

                "message": "Your answer has already been saved."

            })

        return jsonify({
            "success": False,
            "message": "Your answer could not be saved. Please try again."
        }), 409

    except SQLAlchemyError:

        db.session.rollback()

        return jsonify({
            "success": False,
            "message": "A database error occurred while saving your answer."
        }), 500


# =========================================================
# SAVE CURRENT QUESTION POSITION
# =========================================================

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

    try:

        practice_session = PracticeSession.query.filter_by(
            id=session_id,
            user_id=user.id
        ).with_for_update().first()

        if not practice_session:

            return jsonify({
                "success": False,
                "message": "Practice session not found."
            }), 404

        validation_error = validate_active_session(
            practice_session
        )

        if validation_error:
            return validation_error

        if not (
            0 <= current_index
            < practice_session.total_questions
        ):

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

    except SQLAlchemyError:

        db.session.rollback()

        return jsonify({
            "success": False,
            "message": "Unable to save your practice progress."
        }), 500


# =========================================================
# COMPLETE PERSONAL PRACTICE SESSION
# =========================================================

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

    try:

        # Lock the user row first. This helps prevent two
        # simultaneous completions from creating conflicting
        # UserProgress updates for the same user.

        locked_user = lock_current_user(user.id)

        if not locked_user:

            return jsonify({
                "success": False,
                "message": "User account not found."
            }), 404

        practice_session = PracticeSession.query.filter_by(
            id=session_id,
            user_id=user.id
        ).with_for_update().first()

        if not practice_session:

            return jsonify({
                "success": False,
                "message": "Practice session not found."
            }), 404

        # -------------------------------------------------
        # If already completed, return existing results.
        # Do not update UserProgress again.
        # -------------------------------------------------

        if practice_session.status == "completed":

            results = calculate_session_results(
                practice_session
            )

            return jsonify({

                "success": True,

                "already_completed": True,

                **results

            })

        validation_error = validate_active_session(
            practice_session
        )

        if validation_error:
            return validation_error

        # -------------------------------------------------
        # Calculate results from saved answers.
        # -------------------------------------------------

        results = calculate_session_results(
            practice_session
        )

        now = utc_now()

        # -------------------------------------------------
        # Mark the session as completed.
        # -------------------------------------------------

        practice_session.status = "completed"

        practice_session.correct_answers = results["correct"]

        practice_session.completed_at = now

        practice_session.last_activity_at = now

        # -------------------------------------------------
        # Update subject-level UserProgress.
        # -------------------------------------------------

        subject_name = practice_session.subject.name

        progress = UserProgress.query.filter_by(
            user_id=user.id,
            subject=subject_name
        ).with_for_update().first()

        if not progress:

            progress = UserProgress(

                user_id=user.id,

                subject=subject_name,

                questions_attempted=0,

                correct_answers=0

            )

            db.session.add(progress)

            # Flush to check the unique constraint before
            # updating the progress totals.

            db.session.flush()

        progress.questions_attempted += results["attempted"]

        progress.correct_answers += results["correct"]

        progress.last_attempt = datetime.utcnow()

        db.session.commit()

        return jsonify({

            "success": True,

            "already_completed": False,

            **results,

            "message": "Your practice session has been completed."

        })

    except IntegrityError:

        db.session.rollback()

        return jsonify({
            "success": False,
            "message": "A conflicting progress record was detected. Please try again."
        }), 409

    except SQLAlchemyError:

        db.session.rollback()

        return jsonify({
            "success": False,
            "message": "Unable to complete your practice session. Please try again."
        }), 500


# =========================================================
# DISPLAY QUIZ PAGE
# =========================================================

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
