# app/admin/questions.py

from flask import (
    Blueprint,
    jsonify,
    render_template,
    request,
    flash,
    redirect,
    url_for,
    session
)

from flask import current_app

from sqlalchemy.exc import SQLAlchemyError

from datetime import datetime

import json

from io import BytesIO

from flask import send_file

from sqlalchemy.exc import IntegrityError

from sqlalchemy import or_, func

from app.extensions import db

from app.models import (
    Question,
    Subject,
    AssignmentQuestion,
    StudentAnswer,
    UserHistory,
    LiveQuizQuestion,
    LiveQuizAnswer
)

from app.utils.decorators import (
    admin_subject_required
)

from app.utils.question_hash import generate_question_hash


# ======================================================
# BLUEPRINT
# ======================================================

questions_bp = Blueprint(
    "questions",
    __name__,
    url_prefix="/admin/questions"
)



# ======================================================
# HELPER FUNCTIONS
# ======================================================

def question_has_dependencies(question_id):

    return any([

        db.session.query(UserHistory.id)
        .filter_by(question_id=question_id)
        .first(),

        db.session.query(AssignmentQuestion.id)
        .filter_by(question_id=question_id)
        .first(),

        db.session.query(StudentAnswer.id)
        .filter_by(question_id=question_id)
        .first(),

        db.session.query(LiveQuizQuestion.id)
        .filter_by(question_id=question_id)
        .first(),

        db.session.query(LiveQuizAnswer.id)
        .filter_by(question_id=question_id)
        .first()

    ])





# ======================================================
# QUESTION DASHBOARD / LIST
# ======================================================


@questions_bp.route("/")
@admin_subject_required
def view_questions():

    """
    Display questions with:

    - pagination
    - search
    - topic filtering
    - subject filtering
    - difficulty filtering

    Uses the Subject model and Question.subject_id.
    """

    page = request.args.get("page", 1, type=int)

    search = request.args.get(
        "search", "", type=str
    ).strip()

    filter_topic = request.args.get(
        "filter_topic", "", type=str
    ).strip()

    filter_subject = request.args.get(
        "filter_subject", "", type=str
    ).strip()

    filter_difficulty = request.args.get(
        "filter_difficulty", "", type=str
    ).strip()

    question_id = request.args.get(
        "question_id", "", type=int
    )


    # ==================================================
    # SUBJECT CONTEXT
    # ==================================================

    admin_subject = None
    selected_subject = None


    # --------------------------------------------------
    # Regular Admin
    # --------------------------------------------------

    if session.get("role") == "admin":

        admin_subject = (
            Subject.query
            .filter(
                Subject.name == session.get("subject")
            )
            .first()
        )

        if not admin_subject:

            flash(
                "Your assigned subject could not be found.",
                "danger"
            )

            return redirect(
                url_for("admin.dashboard")
            )


    # --------------------------------------------------
    # Super Admin selected subject
    # --------------------------------------------------

    elif filter_subject:

        selected_subject = (
            Subject.query
            .filter(
                Subject.name == filter_subject
            )
            .first()
        )

        if not selected_subject:

            flash(
                "Selected subject could not be found.",
                "warning"
            )

            return redirect(
                url_for("questions.view_questions")
            )


    # ==================================================
    # MAIN QUESTION QUERY
    # ==================================================

    query = Question.query


    # --------------------------------------------------
    # Question ID
    # --------------------------------------------------

    if question_id:

        query = query.filter(
            Question.id == question_id
        )


    # --------------------------------------------------
    # SUBJECT RESTRICTION
    # --------------------------------------------------

    if session.get("role") == "admin":

        query = query.filter(
            Question.subject_id == admin_subject.id
        )

    elif selected_subject:

        query = query.filter(
            Question.subject_id == selected_subject.id
        )


    # ==================================================
    # SEARCH
    # ==================================================

    if search:

        query = query.filter(
            or_(
                Question.question_text.ilike(
                    f"%{search}%"
                ),

                Question.topic.ilike(
                    f"%{search}%"
                ),

                Question.explanation.ilike(
                    f"%{search}%"
                )
            )
        )


    # ==================================================
    # TOPIC FILTER
    # ==================================================

    if filter_topic:

        query = query.filter(
            Question.topic == filter_topic
        )


    # ==================================================
    # DIFFICULTY FILTER
    # ==================================================

    if filter_difficulty:

        query = query.filter(
            Question.difficulty == filter_difficulty
        )


    # ==================================================
    # SORTING
    # ==================================================

    query = query.order_by(
        Question.created_at.desc(),
        Question.id.desc()
    )


    # ==================================================
    # PAGINATION
    # ==================================================

    questions = query.paginate(
        page=page,
        per_page=25,
        error_out=False
    )


    # ==================================================
    # STATISTICS
    # ==================================================

    stats_query = Question.query


    # Regular Admin statistics
    if session.get("role") == "admin":

        stats_query = stats_query.filter(
            Question.subject_id == admin_subject.id
        )

    # Super Admin selected subject statistics
    elif selected_subject:

        stats_query = stats_query.filter(
            Question.subject_id == selected_subject.id
        )


    total_questions = stats_query.count()


    total_topics = (
        stats_query
        .with_entities(
            func.count(
                func.distinct(Question.topic)
            )
        )
        .scalar()
    )


    # ==================================================
    # TOPIC DROPDOWN
    # ==================================================

    topic_query = db.session.query(
        Question.topic
    ).filter(
        Question.topic.isnot(None),
        Question.topic != ""
    )


    # Regular Admin topics
    if session.get("role") == "admin":

        topic_query = topic_query.filter(
            Question.subject_id == admin_subject.id
        )

    # Super Admin selected subject topics
    elif selected_subject:

        topic_query = topic_query.filter(
            Question.subject_id == selected_subject.id
        )


    topics = (
        topic_query
        .distinct()
        .order_by(Question.topic)
        .all()
    )


    # ==================================================
    # SUBJECT DROPDOWN
    # ==================================================

    if session.get("role") == "admin":

        subjects = [
            (admin_subject.name,)
        ]

    else:

        subject_records = (
            Subject.query
            .order_by(
                Subject.display_order,
                Subject.name
            )
            .all()
        )

        subjects = [
            (subject.name,)
            for subject in subject_records
        ]


    # ==================================================
    # RENDER
    # ==================================================

    return render_template(
        "admin/view_questions.html",

        subjects=subjects,

        page=page,

        search=search,

        questions=questions,

        total_questions=total_questions,

        total_topics=total_topics,

        topics=topics,

        filter_topic=filter_topic,

        filter_subject=filter_subject,

        filter_difficulty=filter_difficulty
    )


# ======================================================
# VIEW SINGLE QUESTION
# ======================================================

@questions_bp.route("/view/<int:question_id>")
@admin_subject_required
def view_question(question_id):

    question = Question.query.get_or_404(question_id)

    # --------------------------------------------------
    # Preserve current page and filters
    # --------------------------------------------------

    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "", type=str).strip()
    filter_topic = request.args.get("filter_topic", "", type=str).strip()
    filter_subject = request.args.get("filter_subject", "", type=str).strip()
    filter_difficulty = request.args.get("filter_difficulty", "", type=str).strip()
    
   

    if (
        session.get("role") == "admin"
        and question.subject != session.get("subject")):

        flash(
            "You do not have permission to view this question.",
            "danger"
    )
        return redirect(url_for("questions.view_questions",
             page=page,
             search=search,
             filter_topic=filter_topic,
             filter_subject=filter_subject,
             filter_difficulty=filter_difficulty,
             ))


    return render_template("admin/view_question.html",
             question=question, 
             question_id=question_id,
             page=page,
             search=search,
             filter_topic=filter_topic,             
             filter_subject=filter_subject,
             filter_difficulty=filter_difficulty,
    )



# ======================================================
# ADD QUESTION
# ======================================================

@questions_bp.route("/add", methods=["GET", "POST"])
@admin_subject_required
def add_question():

    
    # -----------------------------------------
    # State preservation after GET
    # ----------------------------------------- 

    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "")
    filter_topic = request.args.get("filter_topic", "")
    filter_subject = request.args.get("filter_subject", "")
    filter_difficulty = request.args.get("filter_difficulty", "")
    
    
    if request.method == "POST":

        # -----------------------------------------
        # State preservation after POST
        # -----------------------------------------
        
        page = request.form.get("page", 1, type=int)
        search = request.form.get("search", "").strip()
        filter_topic = request.form.get("filter_topic", "").strip()
        filter_subject = request.form.get("filter_subject", "").strip()
        filter_difficulty = request.form.get("filter_difficulty", "").strip()

        # -----------------------------------------
        # Question data
        # -----------------------------------------
        
        topic = request.form.get("topic", "").strip()  
        
        difficulty = request.form.get("difficulty", "").strip()
 
        if session.get("role") == "admin":
            subject = session.get("subject")
        else:
            subject = request.form.get("subject", "").strip()


        question_text = request.form.get(
            "question_text",
            ""
        ).strip()

        option_a = request.form.get(
            "option_a",
            ""
        ).strip()

        option_b = request.form.get(
            "option_b",
            ""
        ).strip()

        option_c = request.form.get(
            "option_c",
            ""
        ).strip()

        option_d = request.form.get(
            "option_d",
            ""
        ).strip()

        correct_answer = request.form.get(
            "correct_answer",
            ""
        ).strip().upper()

        explanation = request.form.get(
            "explanation",
            ""
        ).strip()
       

        # --------------------------------------------------
        # Validation
        # --------------------------------------------------
        
        print(request.form)
        print("Topic:", request.form.get("topic"))

        if not topic:
            flash(
                "Topic is required.",
                "danger"
            )
            return redirect(
                url_for("questions.add_question")
            )

        if not subject:
            flash(
                "Subject is required.",
                "danger"
            )
            return redirect(
                url_for("questions.add_question")
            )

        if not question_text:
            flash(
                "Question text is required.",
                "danger"
            )
            return redirect(
                url_for("questions.add_question")
            )

        if not option_a:
            flash(
                "Option A is required.",
                "danger"
            )
            return redirect(
                url_for("questions.add_question")
            )

        if not option_b:
            flash(
                "Option B is required.",
                "danger"
            )
            return redirect(
                url_for("questions.add_question")
            )

        if not option_c:
            flash(
                "Option C is required.",
                "danger"
            )
            return redirect(
                url_for("questions.add_question")
            )

        if not option_d:
            flash(
                "Option D is required.",
                "danger"
            )
            return redirect(
                url_for("questions.add_question")
            )

        options = [
            option_a.lower(),
            option_b.lower(),
            option_c.lower(),
            option_d.lower(),
        ]

        if len(set(options)) != 4:
            flash(
                "All options must be different.",
                "danger"
            )
            return redirect(
                url_for("questions.add_question")
            )

        if correct_answer not in [
            "A",
            "B",
            "C",
            "D"
        ]:
            flash(
                "Correct answer must be A, B, C or D.",
                "danger"
            )
            return redirect(
                url_for("questions.add_question")
            )

        if difficulty not in [
            "DOK_1",
            "DOK_2",
            "DOK_3",
            "DOK_4"
        ]:
            flash(
                "Invalid difficulty level. Choose DOK_1, DOK_2, DOK_3 or DOK_4.",
                "danger"
            )
            return redirect(
                url_for("questions.add_question")
            )

        # --------------------------------------------------
        # Generate question hash
        # --------------------------------------------------

        question_hash = generate_question_hash(
            topic=topic,
            subject=subject,
            question_text=question_text,
            option_a=option_a,
            option_b=option_b,
            option_c=option_c,
            option_d=option_d,
            correct_answer=correct_answer,
        )

        # --------------------------------------------------
        # Duplicate check
        # --------------------------------------------------

        duplicate = Question.query.filter_by(question_hash=question_hash).first()

        if duplicate:
            flash(
                f"This question already exists (Question ID: {duplicate.id}).",
                "warning"
            )
            return redirect(
                url_for("questions.add_question")
            )


        # --------------------------------------------------
        # Save question
        # --------------------------------------------------

        try:

            question = Question(

                topic=topic,

                subject=subject,

                difficulty=difficulty,

                question_text=question_text,

                option_a=option_a,

                option_b=option_b,

                option_c=option_c,

                option_d=option_d,

                correct_answer=correct_answer,

                explanation=explanation,

                question_hash=question_hash

            )

            db.session.add(question)

            db.session.commit()

            flash(
                "Question added successfully.",
                "success"
            )

            return redirect(
                url_for("questions.view_questions",
                page=page,
                search=search,
                filter_topic=filter_topic,
                filter_subject=filter_subject,
                filter_difficulty=filter_difficulty,
                )
            )

        except IntegrityError:

            db.session.rollback()

            flash(
                "A duplicate question already exists.",
                "warning"
            )

            return redirect(
                url_for("questions.add_question")
            )

        except Exception as e:

            db.session.rollback()

            flash(
                f"Error adding question: {e}",
                "danger"
            )

            return redirect(
                url_for("questions.add_question")
            )

    return render_template("admin/add_question.html",
            page=page,
            search=search,
            filter_topic=filter_topic,
            filter_subject=filter_subject,
            filter_difficulty=filter_difficulty,
            )


# ======================================================
# GET TOPICS FOR SUBJECT
# ======================================================

@questions_bp.route("/topics/<int:subject_id>")
@admin_subject_required
def get_topics_for_subject(subject_id):

    subject = Subject.query.get_or_404(subject_id)

    topics = (
        db.session.query(Question.topic)
        .filter(
            Question.subject_id == subject.id,
            Question.topic.isnot(None),
            Question.topic != ""
        )
        .distinct()
        .order_by(Question.topic)
        .all()
    )

    return jsonify({
        "topics": [
            topic[0]
            for topic in topics
        ]
    })



# ======================================================
# EDIT QUESTION
# ======================================================

@questions_bp.route("/edit/<int:question_id>", methods=["GET", "POST"])
@admin_subject_required
def edit_question(question_id):

    question = Question.query.get_or_404(question_id)

    # --------------------------------------------------
    # Preserve current page and filters
    # --------------------------------------------------

    page = request.args.get(
        "page",
        1,
        type=int
    )

    search = request.args.get(
        "search",
        "",
        type=str
    ).strip()

    filter_topic = request.args.get(
        "filter_topic",
        "",
        type=str
    ).strip()

    filter_subject = request.args.get(
        "filter_subject",
        "",
        type=str
    ).strip()

    filter_difficulty = request.args.get(
        "filter_difficulty",
        "",
        type=str
    ).strip()


    # ==================================================
    # DETERMINE CURRENT SUBJECT
    # ==================================================

    current_subject = question.subject_ref


    if not current_subject:

        flash(
            "This question is not linked to a valid subject.",
            "danger"
        )

        return redirect(
            url_for(
                "questions.view_questions",
                page=page,
                search=search,
                filter_topic=filter_topic,
                filter_subject=filter_subject,
                filter_difficulty=filter_difficulty
            )
        )


    # ==================================================
    # REGULAR ADMIN PERMISSION
    # ==================================================

    if session.get("role") == "admin":

        admin_subject = (
            Subject.query
            .filter(
                Subject.name == session.get("subject")
            )
            .first()
        )

        if not admin_subject:

            flash(
                "Your assigned subject could not be found.",
                "danger"
            )

            return redirect(
                url_for("questions.view_questions")
            )


        if question.subject_id != admin_subject.id:

            flash(
                "You do not have permission to edit this question.",
                "danger"
            )

            return redirect(
                url_for(
                    "questions.view_questions",
                    page=page,
                    search=search,
                    filter_topic=filter_topic,
                    filter_subject=filter_subject,
                    filter_difficulty=filter_difficulty
                )
            )


    # ==================================================
    # SUBJECT LIST
    # ==================================================

    subjects = (
        Subject.query
        .filter(
            Subject.is_active.is_(True)
        )
        .order_by(
            Subject.display_order,
            Subject.name
        )
        .all()
    )


    # ==================================================
    # TOPICS FOR CURRENT SUBJECT
    # ==================================================

    topics = (
        db.session.query(Question.topic)
        .filter(
            Question.subject_id == current_subject.id,
            Question.topic.isnot(None),
            Question.topic != ""
        )
        .distinct()
        .order_by(Question.topic)
        .all()
    )

    topics = [
        row[0]
        for row in topics
    ]


    # --------------------------------------------------
    # Make sure current topic is included
    # --------------------------------------------------

    if (
        question.topic
        and question.topic not in topics
    ):

        topics.insert(
            0,
            question.topic
        )


    # ==================================================
    # POST
    # ==================================================

    if request.method == "POST":

        # --------------------------------------------------
        # Preserve page and filters
        # --------------------------------------------------

        page = request.form.get(
            "page",
            1,
            type=int
        )

        search = request.form.get(
            "search",
            "",
            type=str
        ).strip()

        filter_topic = request.form.get(
            "filter_topic",
            "",
            type=str
        ).strip()

        filter_subject = request.form.get(
            "filter_subject",
            "",
            type=str
        ).strip()

        filter_difficulty = request.form.get(
            "filter_difficulty",
            "",
            type=str
        ).strip()


        # ==================================================
        # SUBJECT
        # ==================================================

        if session.get("role") == "admin":

            # ----------------------------------------------
            # Regular Admin
            # ----------------------------------------------
            # Regular Admin cannot change the subject.
            # Use the subject assigned to the admin.
            # ----------------------------------------------

            selected_subject = admin_subject

        else:

            # ----------------------------------------------
            # Super Admin
            # ----------------------------------------------
            # The form sends Subject.id.
            # ----------------------------------------------

            subject_id = request.form.get(
                "subject",
                type=int
            )

            selected_subject = (
                Subject.query
                .filter(
                    Subject.id == subject_id,
                    Subject.is_active.is_(True)
                )
                .first()
            )


            if not selected_subject:

                flash(
                    "Please select a valid subject.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "questions.edit_question",
                        question_id=question.id,
                        page=page,
                        search=search,
                        filter_topic=filter_topic,
                        filter_subject=filter_subject,
                        filter_difficulty=filter_difficulty
                    )
                )


        # ==================================================
        # QUESTION DATA
        # ==================================================

        topic = request.form.get(
            "topic",
            ""
        ).strip()

        difficulty = request.form.get(
            "difficulty",
            ""
        ).strip()

        question_text = request.form.get(
            "question_text",
            ""
        ).strip()

        option_a = request.form.get(
            "option_a",
            ""
        ).strip()

        option_b = request.form.get(
            "option_b",
            ""
        ).strip()

        option_c = request.form.get(
            "option_c",
            ""
        ).strip()

        option_d = request.form.get(
            "option_d",
            ""
        ).strip()

        correct_answer = request.form.get(
            "correct_answer",
            ""
        ).strip().upper()

        explanation = request.form.get(
            "explanation",
            ""
        ).strip()


        # ==================================================
        # REQUIRED FIELD VALIDATION
        # ==================================================

        if not topic:

            flash(
                "Topic is required.",
                "danger"
            )

            return redirect(
                url_for(
                    "questions.edit_question",
                    question_id=question.id,
                    page=page,
                    search=search,
                    filter_topic=filter_topic,
                    filter_subject=filter_subject,
                    filter_difficulty=filter_difficulty
                )
            )


        if not question_text:

            flash(
                "Question text is required.",
                "danger"
            )

            return redirect(
                url_for(
                    "questions.edit_question",
                    question_id=question.id,
                    page=page,
                    search=search,
                    filter_topic=filter_topic,
                    filter_subject=filter_subject,
                    filter_difficulty=filter_difficulty
                )
            )


        if not option_a:

            flash(
                "Option A is required.",
                "danger"
            )

            return redirect(
                url_for(
                    "questions.edit_question",
                    question_id=question.id,
                    page=page,
                    search=search,
                    filter_topic=filter_topic,
                    filter_subject=filter_subject,
                    filter_difficulty=filter_difficulty
                )
            )


        if not option_b:

            flash(
                "Option B is required.",
                "danger"
            )

            return redirect(
                url_for(
                    "questions.edit_question",
                    question_id=question.id,
                    page=page,
                    search=search,
                    filter_topic=filter_topic,
                    filter_subject=filter_subject,
                    filter_difficulty=filter_difficulty
                )
            )


        if not option_c:

            flash(
                "Option C is required.",
                "danger"
            )

            return redirect(
                url_for(
                    "questions.edit_question",
                    question_id=question.id,
                    page=page,
                    search=search,
                    filter_topic=filter_topic,
                    filter_subject=filter_subject,
                    filter_difficulty=filter_difficulty
                )
            )


        if not option_d:

            flash(
                "Option D is required.",
                "danger"
            )

            return redirect(
                url_for(
                    "questions.edit_question",
                    question_id=question.id,
                    page=page,
                    search=search,
                    filter_topic=filter_topic,
                    filter_subject=filter_subject,
                    filter_difficulty=filter_difficulty
                )
            )


        # ==================================================
        # OPTION UNIQUENESS VALIDATION
        # ==================================================

        options = [
            option_a.lower().strip(),
            option_b.lower().strip(),
            option_c.lower().strip(),
            option_d.lower().strip()
        ]

        if len(set(options)) != 4:

            flash(
                "All options must be different.",
                "danger"
            )

            return redirect(
                url_for(
                    "questions.edit_question",
                    question_id=question.id,
                    page=page,
                    search=search,
                    filter_topic=filter_topic,
                    filter_subject=filter_subject,
                    filter_difficulty=filter_difficulty
                )
            )


        # ==================================================
        # CORRECT ANSWER VALIDATION
        # ==================================================

        if correct_answer not in [
            "A",
            "B",
            "C",
            "D"
        ]:

            flash(
                "Correct answer must be A, B, C or D.",
                "danger"
            )

            return redirect(
                url_for(
                    "questions.edit_question",
                    question_id=question.id,
                    page=page,
                    search=search,
                    filter_topic=filter_topic,
                    filter_subject=filter_subject,
                    filter_difficulty=filter_difficulty
                )
            )


        # ==================================================
        # DIFFICULTY VALIDATION
        # ==================================================

        if difficulty not in [
            "DOK_1",
            "DOK_2",
            "DOK_3",
            "DOK_4"
        ]:

            flash(
                "Invalid difficulty level.",
                "danger"
            )

            return redirect(
                url_for(
                    "questions.edit_question",
                    question_id=question.id,
                    page=page,
                    search=search,
                    filter_topic=filter_topic,
                    filter_subject=filter_subject,
                    filter_difficulty=filter_difficulty
                )
            )


        # ==================================================
        # VALIDATE TOPIC BELONGS TO SELECTED SUBJECT
        # ==================================================

        valid_topic = (
            db.session.query(Question.id)
            .filter(
                Question.subject_id == selected_subject.id,
                Question.topic == topic
            )
            .first()
        )


        # --------------------------------------------------
        # Allow the question's existing topic when editing
        # --------------------------------------------------

        if not valid_topic:

            if (
                selected_subject.id == question.subject_id
                and topic == question.topic
            ):

                valid_topic = True


        if not valid_topic:

            flash(
                "Please select a valid topic for the selected subject.",
                "danger"
            )

            return redirect(
                url_for(
                    "questions.edit_question",
                    question_id=question.id,
                    page=page,
                    search=search,
                    filter_topic=filter_topic,
                    filter_subject=filter_subject,
                    filter_difficulty=filter_difficulty
                )
            )


        # ==================================================
        # GENERATE QUESTION HASH
        # ==================================================

        question_hash = generate_question_hash(
            topic=topic,
            subject=selected_subject.name,
            question_text=question_text,
            option_a=option_a,
            option_b=option_b,
            option_c=option_c,
            option_d=option_d,
            correct_answer=correct_answer,
        )


        # ==================================================
        # DUPLICATE CHECK
        # ==================================================

        duplicate = (
            Question.query
            .filter(
                Question.question_hash == question_hash,
                Question.id != question.id
            )
            .first()
        )


        if duplicate:

            flash(
                f"Another question with the same content already exists "
                f"(Question ID: {duplicate.id}).",
                "warning"
            )

            return redirect(
                url_for(
                    "questions.edit_question",
                    question_id=question.id,
                    page=page,
                    search=search,
                    filter_topic=filter_topic,
                    filter_subject=filter_subject,
                    filter_difficulty=filter_difficulty
                )
            )


        # ==================================================
        # UPDATE QUESTION
        # ==================================================

        try:

            # ----------------------------------------------
            # Update relational Subject
            # ----------------------------------------------

            question.subject_id = selected_subject.id


            # ----------------------------------------------
            # Keep legacy subject field synchronized
            # during migration stage.
            # ----------------------------------------------

            question.subject = selected_subject.name


            # ----------------------------------------------
            # Update question data
            # ----------------------------------------------

            question.topic = topic

            question.difficulty = difficulty

            question.question_text = question_text

            question.option_a = option_a
            question.option_b = option_b
            question.option_c = option_c
            question.option_d = option_d

            question.correct_answer = correct_answer

            question.explanation = explanation

            question.question_hash = question_hash


            db.session.commit()


            flash(
                "Question updated successfully.",
                "success"
            )


            return redirect(
                url_for(
                    "questions.view_questions",
                    page=page,
                    search=search,
                    filter_topic=filter_topic,
                    filter_subject=filter_subject,
                    filter_difficulty=filter_difficulty
                )
            )


        except IntegrityError:

            db.session.rollback()

            flash(
                "Update failed because another question "
                "with the same content already exists.",
                "warning"
            )

            return redirect(
                url_for(
                    "questions.edit_question",
                    question_id=question.id,
                    page=page,
                    search=search,
                    filter_topic=filter_topic,
                    filter_subject=filter_subject,
                    filter_difficulty=filter_difficulty
                )
            )


        except Exception as e:

            db.session.rollback()

            flash(
                f"Error updating question: {e}",
                "danger"
            )

            return redirect(
                url_for(
                    "questions.edit_question",
                    question_id=question.id,
                    page=page,
                    search=search,
                    filter_topic=filter_topic,
                    filter_subject=filter_subject,
                    filter_difficulty=filter_difficulty
                )
            )


    # ==================================================
    # GET
    # ==================================================

    return render_template(
        "admin/edit_question.html",

        question=question,

        subjects=subjects,

        topics=topics,

        current_subject=current_subject,

        page=page,

        search=search,

        filter_topic=filter_topic,

        filter_subject=filter_subject,

        filter_difficulty=filter_difficulty,
    )


# ======================================================
# DELETE QUESTION
# ======================================================

@questions_bp.route("/delete/<int:question_id>", methods=["POST"])
@admin_subject_required
def delete_question(question_id):

    question = Question.query.get_or_404(question_id)

    # --------------------------------------------------
    # Preserve current page and filters
    # --------------------------------------------------

    page = request.form.get("page", 1, type=int)
    search = request.form.get("search", "")
    filter_topic = request.form.get("filter_topic", "")
    filter_subject = request.form.get("filter_subject", "")
    filter_difficulty = request.form.get("filter_difficulty", "")


    # ==================================================
    # REGULAR ADMIN AUTHORIZATION
    # ==================================================

    if session.get("role") == "admin":

        admin_subject = (
            Subject.query
            .filter(
                Subject.name == session.get("subject"),
                Subject.is_active.is_(True)
            )
            .first()
        )


        # --------------------------------------------------
        # Assigned subject could not be found
        # --------------------------------------------------

        if not admin_subject:

            flash(
                "Your assigned subject could not be found.",
                "danger"
            )

            return redirect(
                url_for(
                    "questions.view_questions",
                    page=page,
                    search=search,
                    filter_topic=filter_topic,
                    filter_subject=filter_subject,
                    filter_difficulty=filter_difficulty,
                )
            )


        # --------------------------------------------------
        # Prevent Regular Admin from deleting a question
        # belonging to another subject.
        # --------------------------------------------------

        if question.subject_id != admin_subject.id:

            flash(
                "You do not have permission to delete this question.",
                "danger"
            )

            return redirect(
                url_for(
                    "questions.view_questions",
                    page=page,
                    search=search,
                    filter_topic=filter_topic,
                    filter_subject=filter_subject,
                    filter_difficulty=filter_difficulty,
                )
            )


    # ==================================================
    # CHECK QUESTION DEPENDENCIES
    # ==================================================

    if question_has_dependencies(question.id):

        flash(
            "This question cannot be deleted because it has already been used.",
            "warning"
        )

        return redirect(
            url_for(
                "questions.view_questions",
                page=page,
                search=search,
                filter_topic=filter_topic,
                filter_subject=filter_subject,
                filter_difficulty=filter_difficulty,
            )
        )


    # ==================================================
    # DELETE QUESTION
    # ==================================================

    try:

        db.session.delete(question)

        db.session.commit()

        flash(
            "Question deleted successfully.",
            "success"
        )


    except IntegrityError:

        db.session.rollback()

        flash(
            "This question cannot be deleted because it is referenced elsewhere.",
            "warning"
        )


    except Exception as e:

        db.session.rollback()

        flash(
            f"Error deleting question: {e}",
            "danger"
        )


    # ==================================================
    # RETURN TO QUESTION LIST
    # ==================================================

    return redirect(
        url_for(
            "questions.view_questions",
            page=page,
            search=search,
            filter_topic=filter_topic,
            filter_subject=filter_subject,
            filter_difficulty=filter_difficulty,
        )
    )


# ======================================================
# BULK DELETE
# ======================================================

@questions_bp.route("/bulk-delete", methods=["POST"])
@admin_subject_required
def bulk_delete_questions():

    ids = request.form.getlist("question_ids")

    # --------------------------------------------------
    # Preserve current page and filters
    # --------------------------------------------------

    page = request.form.get("page", 1, type=int)
    search = request.form.get("search", "")
    question_id = request.form.get("question_id", type=int)
    filter_topic = request.form.get("filter_topic", "")
    filter_subject = request.form.get("filter_subject", "")
    filter_difficulty = request.form.get("filter_difficulty", "")


    # ==================================================
    # NO QUESTIONS SELECTED
    # ==================================================

    if not ids:

        flash(
            "Please select at least one question.",
            "warning"
        )

        return redirect(
            url_for(
                "questions.view_questions",
                page=page,
                search=search,
                filter_topic=filter_topic,
                filter_subject=filter_subject,
                filter_difficulty=filter_difficulty,
            )
        )


    deleted = 0
    skipped = 0


    # ==================================================
    # GET REGULAR ADMIN'S SUBJECT
    # ==================================================

    admin_subject = None

    if session.get("role") == "admin":

        admin_subject = (
            Subject.query
            .filter(
                Subject.name == session.get("subject"),
                Subject.is_active.is_(True)
            )
            .first()
        )

        # --------------------------------------------------
        # Assigned subject could not be found
        # --------------------------------------------------

        if not admin_subject:

            flash(
                "Your assigned subject could not be found.",
                "danger"
            )

            return redirect(
                url_for(
                    "questions.view_questions",
                    page=page,
                    search=search,
                    filter_topic=filter_topic,
                    filter_subject=filter_subject,
                    filter_difficulty=filter_difficulty,
                )
            )


    # ==================================================
    # PROCESS SELECTED QUESTIONS
    # ==================================================

    try:

        for question_id in ids:

            # --------------------------------------------------
            # Validate question ID
            # --------------------------------------------------

            try:

                question_id = int(question_id)

            except (ValueError, TypeError):

                print(" -> Invalid ID")

                skipped += 1

                continue


            # --------------------------------------------------
            # Get question
            # --------------------------------------------------

            question = db.session.get(
                Question,
                question_id
            )


            if not question:

                print(" -> Question not found")

                skipped += 1

                continue


            # ==================================================
            # REGULAR ADMIN AUTHORIZATION
            # ==================================================

            if (
                session.get("role") == "admin"
                and question.subject_id != admin_subject.id
            ):

                print(" -> Unauthorized")

                skipped += 1

                continue


            # ==================================================
            # CHECK QUESTION DEPENDENCIES
            # ==================================================

            if question_has_dependencies(question.id):

                print(" -> Has dependencies")

                skipped += 1

                continue


            # ==================================================
            # DELETE QUESTION
            # ==================================================

            print(" -> Deleting")

            db.session.delete(question)

            deleted += 1


        print(
            f"\nDeleted={deleted}, Skipped={skipped}"
        )


        # ==================================================
        # COMMIT CHANGES
        # ==================================================

        db.session.commit()


        # ==================================================
        # SUCCESS MESSAGE
        # ==================================================

        if deleted:

            flash(
                f"{deleted} question(s) deleted successfully.",
                "success"
            )


        # ==================================================
        # SKIPPED MESSAGE
        # ==================================================

        if skipped:

            flash(
                f"{skipped} question(s) were skipped because they were invalid, unauthorized, not found, or already in use.",
                "warning"
            )


    # ==================================================
    # DATABASE INTEGRITY ERROR
    # ==================================================

    except IntegrityError:

        db.session.rollback()

        flash(
            "Some questions could not be deleted because they are referenced elsewhere.",
            "warning"
        )


    # ==================================================
    # GENERAL ERROR
    # ==================================================

    except Exception as e:

        db.session.rollback()

        flash(
            f"Error: {e}",
            "danger"
        )


    # ==================================================
    # RETURN TO QUESTION LIST
    # ==================================================

    return redirect(
        url_for(
            "questions.view_questions",
            page=page,
            search=search,
            filter_topic=filter_topic,
            filter_subject=filter_subject,
            filter_difficulty=filter_difficulty,
        )
    )



# ======================================================
# DELETE ALL UNUSED QUESTIONS
# ======================================================

@questions_bp.route("/delete-unused", methods=["POST"])
@admin_subject_required
def delete_unused_questions():

    # --------------------------------------------------
    # Preserve current page and filters
    # --------------------------------------------------

    page = request.form.get("page", 1, type=int)
    search = request.form.get("search", "")
    topic = request.form.get("topic", "")
    filter_topic = request.form.get("filter_topic", "")
    filter_subject = request.form.get("filter_subject", "")
    question_id = request.form.get("question_id", type=int)
    filter_difficulty = request.form.get("filter_difficulty", "")


    deleted = 0


    # ==================================================
    # GET QUESTIONS AVAILABLE TO CURRENT ADMIN
    # ==================================================

    if session.get("role") == "admin":

        # --------------------------------------------------
        # Resolve the Regular Admin's assigned Subject
        # --------------------------------------------------

        admin_subject = (
            Subject.query
            .filter(
                Subject.name == session.get("subject"),
                Subject.is_active.is_(True)
            )
            .first()
        )


        # --------------------------------------------------
        # Assigned subject could not be found
        # --------------------------------------------------

        if not admin_subject:

            flash(
                "Your assigned subject could not be found.",
                "danger"
            )

            return redirect(
                url_for(
                    "questions.view_questions",
                    page=page,
                    search=search,
                    filter_topic=filter_topic,
                    filter_subject=filter_subject,
                    filter_difficulty=filter_difficulty,
                )
            )


        # --------------------------------------------------
        # Only retrieve questions belonging to the
        # Regular Admin's assigned Subject
        # --------------------------------------------------

        questions = (
            Question.query
            .filter(
                Question.subject_id == admin_subject.id
            )
            .all()
        )


    else:

        # --------------------------------------------------
        # Super Admin can access all questions
        # --------------------------------------------------

        questions = Question.query.all()


    # ==================================================
    # DELETE UNUSED QUESTIONS
    # ==================================================

    try:

        for question in questions:

            # --------------------------------------------------
            # Do not delete questions already being used
            # --------------------------------------------------

            if question_has_dependencies(
                question.id
            ):
                continue


            # --------------------------------------------------
            # Delete unused question
            # --------------------------------------------------

            db.session.delete(question)

            deleted += 1


        # --------------------------------------------------
        # Commit deletions
        # --------------------------------------------------

        db.session.commit()


        # --------------------------------------------------
        # Success message
        # --------------------------------------------------

        flash(
            f"{deleted} unused question(s) deleted successfully.",
            "success"
        )


    # ==================================================
    # DATABASE INTEGRITY ERROR
    # ==================================================

    except IntegrityError:

        db.session.rollback()

        flash(
            "Some questions could not be deleted because they are referenced elsewhere.",
            "warning"
        )


    # ==================================================
    # GENERAL ERROR
    # ==================================================

    except Exception as e:

        db.session.rollback()

        flash(
            f"Error: {e}",
            "danger"
        )


    # ==================================================
    # RETURN TO QUESTION LIST
    # ==================================================

    return redirect(
        url_for(
            "questions.view_questions",
            page=page,
            search=search,
            question_id=question_id,
            filter_topic=filter_topic,
            filter_subject=filter_subject,
            filter_difficulty=filter_difficulty,
        )
    )


# ======================================================
# BULK QUESTIONS UPLOAD
# ======================================================

@questions_bp.route("/bulk-upload", methods=["GET", "POST"])
@admin_subject_required
def bulk_upload_questions():

    # ==================================================
    # STATE PRESERVATION
    # ==================================================

    page = request.args.get(
        "page",
        1,
        type=int
    )

    search = request.args.get(
        "search",
        "",
        type=str
    )

    filter_topic = request.args.get(
        "filter_topic",
        "",
        type=str
    )

    filter_subject = request.args.get(
        "filter_subject",
        "",
        type=str
    )

    filter_difficulty = request.args.get(
        "filter_difficulty",
        "",
        type=str
    )


    # ==================================================
    # POST REQUEST
    # ==================================================

    if request.method == "POST":

        # --------------------------------------------------
        # State preservation after POST
        # --------------------------------------------------

        page = request.form.get(
            "page",
            1,
            type=int
        )

        search = request.form.get(
            "search",
            ""
        )

        filter_topic = request.form.get(
            "filter_topic",
            ""
        )

        filter_subject = request.form.get(
            "filter_subject",
            ""
        )

        filter_difficulty = request.form.get(
            "filter_difficulty",
            ""
        )


        # ==================================================
        # GET UPLOADED FILE
        # ==================================================

        file = request.files.get("file")


        if not file or file.filename == "":

            flash(
                "Please select a JSON file.",
                "warning"
            )

            return redirect(
                url_for(
                    "questions.bulk_upload_questions",
                    page=page,
                    search=search,
                    filter_topic=filter_topic,
                    filter_subject=filter_subject,
                    filter_difficulty=filter_difficulty,
                )
            )


        if not file.filename.lower().endswith(".json"):

            flash(
                "Only JSON files are allowed.",
                "danger"
            )

            return redirect(
                url_for(
                    "questions.bulk_upload_questions",
                    page=page,
                    search=search,
                    filter_topic=filter_topic,
                    filter_subject=filter_subject,
                    filter_difficulty=filter_difficulty,
                )
            )


        # ==================================================
        # READ JSON FILE
        # ==================================================

        try:

            questions = json.load(file)


            # --------------------------------------------------
            # JSON must contain a list
            # --------------------------------------------------

            if not isinstance(questions, list):

                flash(
                    "JSON must contain a list of questions.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "questions.bulk_upload_questions",
                        page=page,
                        search=search,
                        filter_topic=filter_topic,
                        filter_subject=filter_subject,
                        filter_difficulty=filter_difficulty,
                    )
                )


            # --------------------------------------------------
            # JSON must not be empty
            # --------------------------------------------------

            if not questions:

                flash(
                    "The uploaded JSON file contains no questions.",
                    "warning"
                )

                return redirect(
                    url_for(
                        "questions.bulk_upload_questions",
                        page=page,
                        search=search,
                        filter_topic=filter_topic,
                        filter_subject=filter_subject,
                        filter_difficulty=filter_difficulty,
                    )
                )


            # ==================================================
            # UPLOAD STATISTICS
            # ==================================================

            added = 0
            duplicates = 0
            invalid = 0
            errors = 0

            total = len(questions)


            # ==================================================
            # LOAD EXISTING QUESTION HASHES
            # ==================================================

            existing_hashes = {
                row[0]
                for row in (
                    db.session
                    .query(Question.question_hash)
                    .filter(
                        Question.question_hash.isnot(None)
                    )
                    .all()
                )
            }


            # ==================================================
            # RESOLVE REGULAR ADMIN SUBJECT
            # ==================================================

            admin_subject = None


            if session.get("role") == "admin":

                admin_subject = (
                    Subject.query
                    .filter(
                        Subject.name == session.get("subject"),
                        Subject.is_active.is_(True)
                    )
                    .first()
                )


                # --------------------------------------------------
                # Assigned subject does not exist
                # --------------------------------------------------

                if not admin_subject:

                    flash(
                        "Your assigned subject could not be found. Contact Super-Administrator (Bush).",
                        "danger"
                    )

                    return redirect(
                        url_for(
                            "questions.bulk_upload_questions",
                            page=page,
                            search=search,
                            filter_topic=filter_topic,
                            filter_subject=filter_subject,
                            filter_difficulty=filter_difficulty,
                        )
                    )


            # ==================================================
            # PROCESS QUESTIONS
            # ==================================================

            for item in questions:

                # --------------------------------------------------
                # Each item must be an object/dictionary
                # --------------------------------------------------

                if not isinstance(item, dict):

                    invalid += 1

                    continue


                # ==================================================
                # READ QUESTION DATA
                # ==================================================

                topic = str(
                    item.get("topic") or ""
                ).strip()


                json_subject = str(
                    item.get("subject") or ""
                ).strip()


                question_difficulty = str(
                    item.get("difficulty") or ""
                ).strip()


                question_text = str(
                    item.get("question_text") or ""
                ).strip()


                option_a = str(
                    item.get("option_a") or ""
                ).strip()


                option_b = str(
                    item.get("option_b") or ""
                ).strip()


                option_c = str(
                    item.get("option_c") or ""
                ).strip()


                option_d = str(
                    item.get("option_d") or ""
                ).strip()


                correct_answer = str(
                    item.get("correct_answer") or ""
                ).strip().upper()


                explanation = str(
                    item.get("explanation") or ""
                ).strip()


                # ==================================================
                # DETERMINE SUBJECT
                # ==================================================

                # --------------------------------------------------
                # Regular Admin
                #
                # The JSON subject is ignored.
                # Questions are ALWAYS assigned to the admin's
                # assigned Subject model record.
                # --------------------------------------------------

                if session.get("role") == "admin":

                    question_subject = admin_subject.name

                    subject_id = admin_subject.id


                # --------------------------------------------------
                # Super Admin
                #
                # Subject comes from the JSON file and must exist
                # in the Subject model.
                # --------------------------------------------------

                else:

                    question_subject = json_subject


                    if not question_subject:

                        invalid += 1

                        continue


                    selected_subject = (
                        Subject.query
                        .filter(
                            Subject.name == question_subject,
                            Subject.is_active.is_(True)
                        )
                        .first()
                    )


                    if not selected_subject:

                        invalid += 1

                        current_app.logger.warning(
                            f"Bulk upload skipped question because "
                            f"subject does not exist: "
                            f"{question_subject}"
                        )

                        continue


                    subject_id = selected_subject.id


                # ==================================================
                # REQUIRED FIELDS
                # ==================================================

                if not all([
                    topic,
                    question_subject,
                    question_difficulty,
                    question_text,
                    option_a,
                    option_b,
                    option_c,
                    option_d,
                    correct_answer
                ]):

                    invalid += 1

                    continue


                # ==================================================
                # VALIDATE OPTIONS
                # ==================================================

                options = [
                    option_a.lower(),
                    option_b.lower(),
                    option_c.lower(),
                    option_d.lower()
                ]


                if len(set(options)) != 4:

                    invalid += 1

                    continue


                # ==================================================
                # VALIDATE CORRECT ANSWER
                # ==================================================

                if correct_answer not in [
                    "A",
                    "B",
                    "C",
                    "D"
                ]:

                    invalid += 1

                    continue


                # ==================================================
                # VALIDATE DIFFICULTY
                # ==================================================

                if question_difficulty not in [
                    "DOK_1",
                    "DOK_2",
                    "DOK_3",
                    "DOK_4"
                ]:

                    invalid += 1

                    continue


                # ==================================================
                # GENERATE QUESTION HASH
                # ==================================================

                question_hash = generate_question_hash(
                    topic=topic,
                    subject=question_subject,
                    question_text=question_text,
                    option_a=option_a,
                    option_b=option_b,
                    option_c=option_c,
                    option_d=option_d,
                    correct_answer=correct_answer,
                )


                # ==================================================
                # DUPLICATE CHECK
                # ==================================================

                if question_hash in existing_hashes:

                    duplicates += 1

                    continue


                # ==================================================
                # CREATE QUESTION
                # ==================================================

                question = Question(

                    topic=topic,

                    # --------------------------------------------------
                    # Keep legacy subject column synchronized
                    # --------------------------------------------------

                    subject=question_subject,

                    # --------------------------------------------------
                    # New Subject model relationship
                    # --------------------------------------------------

                    subject_id=subject_id,

                    difficulty=question_difficulty,

                    question_text=question_text,

                    option_a=option_a,

                    option_b=option_b,

                    option_c=option_c,

                    option_d=option_d,

                    correct_answer=correct_answer,

                    explanation=explanation,

                    question_hash=question_hash,

                )


                # ==================================================
                # SAVE QUESTION
                # ==================================================

                try:

                    with db.session.begin_nested():

                        db.session.add(question)

                        db.session.flush()


                    existing_hashes.add(
                        question_hash
                    )


                    added += 1


                except SQLAlchemyError:

                    current_app.logger.exception(
                        f"Failed to import question. "
                        f"Subject={question_subject}, "
                        f"Topic={topic}, "
                        f"Question={question_text}"
                    )

                    errors += 1

                    continue


            # ==================================================
            # COMMIT ALL QUESTIONS
            # ==================================================

            try:

                db.session.commit()


            except SQLAlchemyError:

                db.session.rollback()

                current_app.logger.exception(
                    "Bulk upload database commit failed."
                )

                flash(
                    "A database error occurred while saving the uploaded questions. Please try again.",
                    "danger"
                )

                return redirect(
                    url_for(
                        "questions.bulk_upload_questions",
                        page=page,
                        search=search,
                        filter_topic=filter_topic,
                        filter_subject=filter_subject,
                        filter_difficulty=filter_difficulty,
                    )
                )


            # ==================================================
            # LOG UPLOAD SUMMARY
            # ==================================================

            current_app.logger.info(
                f"Bulk upload completed. "
                f"Processed={total}, "
                f"Added={added}, "
                f"Duplicates={duplicates}, "
                f"Invalid={invalid}, "
                f"Errors={errors}"
            )


            # ==================================================
            # FLASH RESULTS
            # ==================================================

            flash(
                f"Processed {total} questions.",
                "info"
            )


            flash(
                f"{added} question(s) imported successfully.",
                "success"
            )


            if duplicates:

                flash(
                    f"{duplicates} duplicate question(s) skipped.",
                    "warning"
                )


            if invalid:

                flash(
                    f"{invalid} invalid question(s) skipped.",
                    "warning"
                )


            if errors:

                flash(
                    f"{errors} question(s) could not be saved.",
                    "warning"
                )


            # ==================================================
            # RETURN TO QUESTION LIST
            # ==================================================

            return redirect(
                url_for(
                    "questions.view_questions",
                    page=page,
                    search=search,
                    filter_topic=filter_topic,
                    filter_subject=filter_subject,
                    filter_difficulty=filter_difficulty,
                )
            )


        # ==================================================
        # INVALID JSON
        # ==================================================

        except json.JSONDecodeError:

            db.session.rollback()

            flash(
                "Invalid JSON file.",
                "danger"
            )

            return redirect(
                url_for(
                    "questions.bulk_upload_questions",
                    page=page,
                    search=search,
                    filter_topic=filter_topic,
                    filter_subject=filter_subject,
                    filter_difficulty=filter_difficulty,
                )
            )


        # ==================================================
        # UNEXPECTED ERROR
        # ==================================================

        except Exception as e:

            db.session.rollback()

            current_app.logger.exception(
                "Unexpected bulk upload error."
            )

            flash(
                f"Error reading file: {e}",
                "danger"
            )

            return redirect(
                url_for(
                    "questions.bulk_upload_questions",
                    page=page,
                    search=search,
                    filter_topic=filter_topic,
                    filter_subject=filter_subject,
                    filter_difficulty=filter_difficulty,
                )
            )


    # ==================================================
    # GET REQUEST
    # ==================================================

    return render_template(
        "admin/bulk_upload.html",
        page=page,
        search=search,
        filter_topic=filter_topic,
        filter_subject=filter_subject,
        filter_difficulty=filter_difficulty,
    )


    
# ======================================================
# EXPORT QUESTIONS
# ======================================================

@questions_bp.route("/export")
@admin_subject_required
def export_questions():

    # ==================================================
    # PRESERVE FILTERS
    # ==================================================

    page = request.args.get(
        "page",
        1,
        type=int
    )

    search = request.args.get(
        "search",
        "",
        type=str
    ).strip()

    filter_topic = request.args.get(
        "filter_topic",
        "",
        type=str
    ).strip()

    filter_subject = request.args.get(
        "filter_subject",
        "",
        type=str
    ).strip()

    filter_difficulty = request.args.get(
        "filter_difficulty",
        "",
        type=str
    ).strip()


    # ==================================================
    # BASE QUERY
    # ==================================================

    query = Question.query


    # ==================================================
    # SUBJECT CONTEXT
    # ==================================================

    admin_subject = None
    selected_subject = None


    # --------------------------------------------------
    # REGULAR ADMIN
    # --------------------------------------------------

    if session.get("role") == "admin":

        admin_subject = (
            Subject.query
            .filter(
                Subject.name == session.get("subject"),
                Subject.is_active.is_(True)
            )
            .first()
        )


        if not admin_subject:

            flash(
                "Your assigned subject could not be found.",
                "danger"
            )

            return redirect(
                url_for(
                    "questions.view_questions",
                    page=page,
                    search=search,
                    filter_topic=filter_topic,
                    filter_subject=filter_subject,
                    filter_difficulty=filter_difficulty
                )
            )


        # --------------------------------------------------
        # Restrict Regular Admin to assigned subject
        # --------------------------------------------------

        query = query.filter(
            Question.subject_id == admin_subject.id
        )


        # --------------------------------------------------
        # Use assigned subject name for filename
        # --------------------------------------------------

        export_subject = admin_subject.name


    # --------------------------------------------------
    # SUPER ADMIN
    # --------------------------------------------------

    else:

        export_subject = filter_subject


        # --------------------------------------------------
        # Optional Subject filter
        # --------------------------------------------------

        if filter_subject:

            selected_subject = (
                Subject.query
                .filter(
                    Subject.name == filter_subject,
                    Subject.is_active.is_(True)
                )
                .first()
            )


            if not selected_subject:

                flash(
                    "Selected subject could not be found.",
                    "warning"
                )

                return redirect(
                    url_for(
                        "questions.view_questions",
                        page=page,
                        search=search,
                        filter_topic=filter_topic,
                        filter_subject=filter_subject,
                        filter_difficulty=filter_difficulty
                    )
                )


            query = query.filter(
                Question.subject_id == selected_subject.id
            )


    # ==================================================
    # SEARCH
    # ==================================================

    if search:

        query = query.filter(
            or_(
                Question.question_text.ilike(
                    f"%{search}%"
                ),

                Question.topic.ilike(
                    f"%{search}%"
                ),

                Question.explanation.ilike(
                    f"%{search}%"
                )
            )
        )


    # ==================================================
    # TOPIC FILTER
    # ==================================================

    if filter_topic:

        query = query.filter(
            Question.topic == filter_topic
        )


    # ==================================================
    # DIFFICULTY FILTER
    # ==================================================

    if filter_difficulty:

        query = query.filter(
            Question.difficulty == filter_difficulty
        )


    # ==================================================
    # GET QUESTIONS
    # ==================================================

    questions = (
        query
        .order_by(
            Question.topic,
            Question.id
        )
        .all()
    )


    # ==================================================
    # NOTHING TO EXPORT
    # ==================================================

    if not questions:

        flash(
            "No questions found to export.",
            "warning"
        )

        return redirect(
            url_for(
                "questions.view_questions",
                page=page,
                search=search,
                filter_topic=filter_topic,
                filter_subject=filter_subject,
                filter_difficulty=filter_difficulty
            )
        )


    # ==================================================
    # BUILD EXPORT DATA
    # ==================================================

    data = []


    for question in questions:

        data.append({

            "topic": question.topic,

            "subject": (
                question.subject_ref.name
                if question.subject_ref
                else ""
            ),

            "difficulty": question.difficulty,

            "question_text": question.question_text,

            "option_a": question.option_a,

            "option_b": question.option_b,

            "option_c": question.option_c,

            "option_d": question.option_d,

            "correct_answer": question.correct_answer,

            "explanation": question.explanation

        })


    # ==================================================
    # CONVERT TO JSON
    # ==================================================

    json_data = json.dumps(
        data,
        indent=4,
        ensure_ascii=False
    )


    # ==================================================
    # GENERATE FILENAME
    # ==================================================

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )


    filename_parts = []


    if export_subject:

        filename_parts.append(
            export_subject
            .lower()
            .replace(" ", "_")
        )


    if filter_topic:

        filename_parts.append(
            filter_topic
            .lower()
            .replace(" ", "_")
        )


    if filter_difficulty:

        filename_parts.append(
            filter_difficulty
            .lower()
        )


    if filename_parts:

        filename = "_".join(
            filename_parts
        )

    else:

        filename = "all_questions"


    filename = (
        f"{filename}_{today}.json"
    )


    # ==================================================
    # DOWNLOAD JSON FILE
    # ==================================================

    return send_file(

        BytesIO(
            json_data.encode("utf-8")
        ),

        mimetype="application/json",

        as_attachment=True,

        download_name=filename

    )


        