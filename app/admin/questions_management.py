# app/admin/questions.py

from flask import (
    Blueprint,
    render_template,
    request,
    flash,
    redirect,
    url_for,
    session
)

from sqlalchemy.exc import IntegrityError

from sqlalchemy import or_, func

from app.extensions import db

from app.models import (
    Question,
    AssignmentQuestion,
    StudentAnswer,
    UserHistory,
    LiveQuizQuestion,
    LiveQuizAnswer
)

from app.utils.decorators import (
    admin_required
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
@admin_required
def view_questions():

    """
    Display questions with:

    - pagination
    - search
    - topic filtering
    - subject filtering
    - difficulty filtering

    Optimized for large question banks.
    """

    page = request.args.get("page", 1, type=int)

    search = request.args.get("search", "", type=str).strip()

    filter_topic = request.args.get("filter_topic", "", type=str).strip()

    subject = request.args.get("subject", "", type=str).strip()

    difficulty = request.args.get("difficulty", "", type=str).strip()

    question_id = request.args.get("question_id", type=int)



    query = Question.query


    if question_id:
        query = query.filter(Question.id == question_id)


    if session.get("role") == "admin":

        query = query.filter(Question.subject == session.get("subject")
    )



    # ---------------- SEARCH ----------------


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



    # ---------------- FILTERS ----------------


    if filter_topic:

        query = query.filter(
            Question.topic == filter_topic
        )


    if subject and session.get("role") != "admin":

        query = query.filter(Question.subject == subject)


    if difficulty:

        query = query.filter(
            Question.difficulty == difficulty)
            
           

    # ---------------- SORTING ----------------


    query = query.order_by(
        Question.created_at.desc()
    )



    # ---------------- PAGINATION ----------------


    questions = query.paginate(
        page=page,
        per_page=25,
        error_out=False
    )



    # ==================================================
    # STATISTICS
    # ==================================================


    if session.get("role") == "admin":

        total_questions = Question.query.filter_by(
            subject=session.get("subject")
        ).count()

    else:

        total_questions = Question.query.count()



    if session.get("role") == "admin":

        total_topics = (
        db.session.query(
        func.count(
        func.distinct(Question.topic)
            )
        )
        .filter(
            Question.subject == session.get("subject")
        )
        .scalar()
    )


    else:

        total_topics = (
        db.session.query(
            func.count(
                func.distinct(Question.topic)
            )
        )
        .scalar()
    )
   


    if session.get("role") == "admin":

        topics = (
            db.session.query(Question.topic)
            .filter(
                Question.subject == session.get("subject")
            )
            .distinct()
            .order_by(Question.topic)
            .all()
        )


    else:

        topics = (
            db.session.query(Question.topic)
            .distinct()
            .order_by(Question.topic)
            .all()
        )
    

    if session.get("role") == "admin":

        subjects = [
            (session.get("subject"),)
        ]

    else:

        subjects = (
            db.session.query(Question.subject)
            .distinct()
            .order_by(Question.subject)
            .all()
        )

    

    return render_template("admin/view_questions.html",
            questions=questions,
            total_questions=total_questions,
            total_topics=total_topics,
            topics=topics,
            subjects=subjects,
            page=page,                    
            search=search,
            question_id=question_id,
            filter_topic=filter_topic,
            subject=subject,
            difficulty=difficulty,    
        
        )



# ======================================================
# VIEW SINGLE QUESTION
# ======================================================

@questions_bp.route("/view/<int:question_id>")
@admin_required
def view_question(question_id):

    question = Question.query.get_or_404(question_id)

    # --------------------------------------------------
    # Preserve current page and filters
    # --------------------------------------------------

    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "")
    filter_topic = request.args.get("filter_topic", "")
    subject = request.args.get("subject", "")
    difficulty = request.args.get("difficulty", "")
    question_id = request.args.get("question_id", type=int)

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
             question_id=question.id,
             filter_topic=filter_topic,
             subject=subject,
             difficulty=difficulty))


    return render_template("admin/view_question.html",
             question=question,
             page=page,
             search=search,
             question_id=question_id,
             filter_topic=filter_topic,
             subject=subject,
             difficulty=difficulty,
    )



# ======================================================
# ADD QUESTION
# ======================================================

@questions_bp.route("/add", methods=["GET", "POST"])
@admin_required
def add_question():

    if request.method == "POST":

        topic = request.form.get("topic", "").strip()

        if session.get("role") == "admin":
            subject = session.get("subject")
        else:
            subject = request.form.get(
                "subject",
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

        # --------------------------------------------------
        # Validation
        # --------------------------------------------------

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

        duplicate = Question.query.filter_by(
            question_hash=question_hash
        ).first()

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
                 filter_question_id=filter_question_id,
                 topic=topic,
                 subject=subject,
                 difficulty=difficulty)
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

    return render_template(
        "admin/add_question.html"
    )



# ======================================================
# EDIT QUESTION
# ======================================================

@questions_bp.route("/edit/<int:question_id>", methods=["GET", "POST"])
@admin_required
def edit_question(question_id):

    question = Question.query.get_or_404(question_id)
   

    # --------------------------------------------------
    # Preserve current page and filters
    # --------------------------------------------------
    
    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "", type=str).strip()
    filter_topic = request.args.get("filter_topic", "", type=str).strip()
    subject = request.args.get("subject", "", type=str).strip()
    difficulty = request.args.get("difficulty", "", type=str).strip()
   
    
    # --------------------------------------------------
    # Permission check
    # --------------------------------------------------

    if (
        session.get("role") == "admin"
        and question.subject != session.get("subject")
    ):
        flash(
            "You do not have permission to edit this question.",
            "danger"
        )
        return redirect(url_for("questions.view_questions"))

    if request.method == "POST":

        page = request.form.get("page", 1, type=int)
        search = request.form.get("search", "").strip()
        filter_topic = request.form.get("filter_topic", "").strip()
        question_id = request.form.get("question_id", "").strip()

        

        if session.get("role") == "admin":
            subject = session.get("subject")
            
        else:
            subject = request.form.get("subject", "").strip()
            
            

        topic = request.form.get("topic", "").strip()
        
        difficulty = request.form.get("difficulty", "").strip()
        

        question_text = request.form.get("question_text", "").strip()


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

        if not topic:
            flash("Topic is required.", "danger")
            return redirect(
               url_for("questions.edit_question",
               question_id=question.id,
               page=page,
               search=search,
               filter_topic=filter_topic,
               subject=subject,
               difficulty=difficulty,
           )
        )

        if not subject:
            flash("Subject is required.", "danger")
            return redirect(
               url_for("questions.edit_question",
               question_id=question.id,
               page=page,
               search=search,
               filter_topic=filter_topic,
               subject=subject,
               difficulty=difficulty,
           )
        )


        if not question_text:
            flash("Question text is required.", "danger")
            return redirect(
               url_for("questions.edit_question",
               question_id=question.id,
               page=page,
               search=search,
               filter_topic=filter_topic,
               subject=subject,
               difficulty=difficulty,	
           )
        )

        if not option_a:
            flash("Option A is required.", "danger")
            return redirect(
               url_for("questions.edit_question",
               question_id=question.id,
               page=page,
               search=search,
               filter_topic=filter_topic,
               subject=subject,
               difficulty=difficulty,
           )
        )


        if not option_b:
            flash("Option B is required.", "danger")
            return redirect(
               url_for("questions.edit_question",
               question_id=question.id,
               page=page,
               search=search,
               filter_topic=filter_topic,
               subject=subject,
               difficulty=difficulty,
           )
        )

        if not option_c:
            flash("Option C is required.", "danger")
            return redirect(
               url_for("questions.edit_question",
               question_id=question.id,
               page=page,
               search=search,
               filter_topic=filter_topic,
               subject=subject,
               difficulty=difficulty,
           )
        )

        if not option_d:
            flash("Option D is required.", "danger")
            return redirect(
               url_for("questions.edit_question",
               question_id=question.id,
               page=page,
               search=search,
               filter_topic=filter_topic,
               subject=subject,
               difficulty=difficulty,
           )
        )

        options = [
            option_a.lower(),
            option_b.lower(),
            option_c.lower(),
            option_d.lower()
        ]

        if len(set(options)) != 4:
            flash(
                "All options must be different.",
                "danger"
            )
            return redirect(
               url_for("questions.edit_question",
               question_id=question.id,
               page=page,
               search=search,
               filter_topic=filter_topic,
               subject=subject,
               difficulty=difficulty,
           )
        )
                
            

        if correct_answer not in ["A", "B", "C", "D"]:
            flash(
                "Correct answer must be A, B, C or D.",
                "danger"
            )
            return redirect(
               url_for("questions.edit_question",
               question_id=question.id,
               page=page,
               search=search,
               filter_topic=filter_topic,
               subject=subject,
               difficulty=difficulty,
           )
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
               url_for("questions.edit_question",
               question_id=question.id,
               page=page,
               search=search,
               filter_topic=filter_topic,
               subject=subject,
               difficulty=difficulty,
           )
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

        duplicate = Question.query.filter(
            Question.question_hash == question_hash, Question.id != question.id).first()

        if duplicate:
            flash(
                f"This question already exists (Question ID: {duplicate.id}).",
                "warning"
            )
            return redirect(
               url_for("questions.edit_question",
               question_id=question.id,
               page=page,
               search=search,
               filter_topic=filter_topic,
               subject=subject,
               difficulty=difficulty,
           )
        )
        


        # --------------------------------------------------
        # Update question
        # --------------------------------------------------

        try:

            question.topic = topic
            question.subject = subject
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
               url_for("questions.edit_question",
               question_id=question.id,
               page=page,
               search=search,
               filter_topic=filter_topic,
               subject=subject,
               difficulty=difficulty,
           )
        )

        except IntegrityError:

            db.session.rollback()

            flash(
                "Update failed because another question with the same content already exists.",
                "warning"
            )

            return redirect(
               url_for("questions.edit_question",
               question_id=question.id,
               page=page,
               search=search,
               filter_topic=filter_topic,
               subject=subject,
               difficulty=difficulty,
           )
        )
                      

        except Exception as e:

            db.session.rollback()

            flash(
                f"Error updating question: {e}",
                "danger"
            )

            return redirect(
               url_for("questions.edit_question",
               question_id=question.id,
               page=page,
               search=search,
               filter_topic=filter_topic,
               subject=subject,
               difficulty=difficulty,
           )
        )

    return render_template("admin/edit_question.html",
           question=question,
           page=page,
           search=search,
           filter_topic=filter_topic,
           subject=subject,
           difficulty=difficulty,
       )
    

# ======================================================
# DELETE QUESTION
# ======================================================

@questions_bp.route("/delete/<int:question_id>", methods=["POST"])
@admin_required
def delete_question(question_id):

    question = Question.query.get_or_404(
        question_id
    )

    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "")
    filter_question_id = request.args.get("question_id", type=int)
    topic = request.args.get("topic", "")
    subject = request.args.get("subject", "")
    difficulty = request.args.get("difficulty", "")

    if (
        session.get("role") == "admin" and question.subject != session.get("subject")
    ):
        flash(
            "You do not have permission to delete this question.",
            "danger"
        )

        return redirect(url_for(
            "questions.view_questions",
            page=page,
            search=search,
            filter_topic=filter_topic,
            filter_question_id=filter_question_id,
            subject=subject,
            difficulty=difficulty,
        )

        )
 

    if question_has_dependencies(question.id):

        flash(
            "This question cannot be deleted because it has already been used.",
            "warning"
        )

        return redirect(
            url_for("questions.view_questions",
            page=page,
            search=search,
            question_id=question_id,
            filter_topic=filter_topic,
            filter_question_id=filter_question_id,
            subject=subject,
            difficulty=difficulty, 
        )
        )

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

    return redirect(
        url_for("questions.view_questions",
            page=page,
            search=search,
            filter_question_id=filter_question_id,
            filter_topic=filter_topic,
            subject=subject,
            difficulty=difficulty,
         )       
        ) 
    

# ======================================================
# BULK DELETE
# ======================================================

@questions_bp.route("/bulk-delete", methods=["POST"]
)
@admin_required
def bulk_delete_questions():

    ids = request.form.getlist("question_ids")

    # --------------------------------------------------
    # Preserve current page and filters
    # --------------------------------------------------

    page = request.form.get("page", 1, type=int)
    search = request.form.get("search", "")
    filter_question_id = request.args.get("question_id", type=int)
    filter_topic = request.form.get("filter_topic", "")
    subject = request.form.get("subject", "")
    difficulty = request.form.get("difficulty", "")

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
                filter_question_id=filter_question_id,
                subject=subject,
                difficulty=difficulty,
            )
        )

    deleted = 0
    skipped = 0

    try:

        for question_id in ids:

            try:
                question_id = int(question_id)

            except ValueError:
                skipped += 1
                continue

            question = db.session.get(Question, question_id)

            if not question:
                skipped += 1
                continue

            if (
                session.get("role") == "admin"
                and question.subject != session.get("subject")
            ):
                skipped += 1
                continue

            if question_has_dependencies(question.id):
                skipped += 1
                continue

            db.session.delete(question)
            deleted += 1

        db.session.commit()

        if deleted:

            flash(
                f"{deleted} question(s) deleted successfully.",
                "success"
            )

        if skipped:

            flash(
                f"{skipped} question(s) were skipped because they were invalid, unauthorized, not found, or already in use.",
                "warning"
            )

    except IntegrityError:

        db.session.rollback()

        flash(
            "Some questions could not be deleted because they are referenced elsewhere.",
            "warning"
        )

    except Exception as e:

        db.session.rollback()

        flash(
            f"Error: {e}",
            "danger"
        )

    return redirect(
        url_for(
            "questions.view_questions",
            page=page,
            search=search,
            filter_question_id=filter_question_id,
            filter_topic=filter_topic,
            subject=subject,
            difficulty=difficulty,
        )
    )


# ======================================================
# DELETE ALL UNUSED QUESTIONS
# ======================================================

@questions_bp.route("/delete-unused", methods=["POST"]
)
@admin_required
def delete_unused_questions():

    # --------------------------------------------------
    # Preserve current page and filters
    # --------------------------------------------------

    page = request.form.get("page", 1, type=int)
    search = request.form.get("search", "")
    topic = request.form.get("topic", "")
    subject = request.form.get("subject", "")
    filter_question_id = request.args.get("question_id", type=int)
    difficulty = request.form.get("difficulty", "")
   

    deleted = 0

    if session.get("role") == "admin":

        questions = Question.query.filter_by(
            subject=session.get("subject")
        ).all()

    else:

        questions = Question.query.all()

    try:

        for question in questions:

            if question_has_dependencies(
                question.id
            ):
                continue

            db.session.delete(question)

            deleted += 1

        db.session.commit()

        flash(
            f"{deleted} unused question(s) deleted successfully.",
            "success"
        )

    except IntegrityError:

        db.session.rollback()

        flash(
            "Some questions could not be deleted because they are referenced elsewhere.",
            "warning"
        )

    except Exception as e:

        db.session.rollback()

        flash(
            f"Error: {e}",
            "danger"
        )

    return redirect(
        url_for(
            "questions.view_questions",
            page=page,
            search=search,
            filter_question_id=filter_question_id,
            filter_topic=filter_topic,
            subject=subject,
            difficulty=difficulty
        )
    )