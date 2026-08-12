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
    filter_subject = request.args.get("filter_subject", "", type=str).strip()
    filter_difficulty = request.args.get("filter_difficulty", "", type=str).strip()
    
    
    question_id = request.args.get("question_id", "", type=int)

   
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


    if filter_subject and session.get("role") != "admin":

        query = query.filter(Question.subject == filter_subject)


    if filter_difficulty:

        query = query.filter(
            Question.difficulty == filter_difficulty)
            
           

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
            subjects=subjects,            
            page=page,                    
            search=search,
            questions=questions,
            total_questions=total_questions,
            total_topics=total_topics,
            topics=topics,
            filter_topic=filter_topic,
            filter_subject=filter_subject,
            filter_difficulty=filter_difficulty,    
        
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
@admin_required
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
    filter_subject = request.args.get("filter_subject", "", type=str).strip()
    filter_difficulty = request.args.get("filter_difficulty", "", type=str).strip()
   
    
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

        page = request.args.get("page", 1, type=int)
        search = request.args.get("search", "", type=str).strip()
        filter_topic = request.args.get("filter_topic", "", type=str).strip()
        filter_subject = request.args.get("filter_subject", "", type=str).strip()
        filter_difficulty = request.args.get("filter_difficulty", "", type=str).strip()
   
   
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
               filter_subject=filter_subject,
               filter_difficulty=filter_difficulty,
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
               filter_subject=filter_subject,
               filter_difficulty=filter_difficulty, )
        )


        if not question_text:
            flash("Question text is required.", "danger")
            return redirect(
               url_for("questions.edit_question",
               question_id=question.id,
               page=page,
               search=search,
               filter_topic=filter_topic,
               filter_subject=filter_subject,
               filter_difficulty=filter_difficulty,	
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
               filter_subject=filter_subject,
               filter_difficulty=filter_difficulty,
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
               filter_subject=filter_subject,
               filter_difficulty=filter_difficulty,
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
               filter_subject=filter_subject,
               filter_difficulty=filter_difficulty,  
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
               filter_subject=filter_subject,
               filter_difficulty=filter_difficulty,
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
               filter_subject=filter_subject,
               filter_difficulty=filter_difficulty,
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
               filter_subject=filter_subject,
               filter_difficulty=filter_difficulty,
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
               filter_subject=filter_subject,
               filter_difficulty=filter_difficulty,
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
               filter_subject=filter_subject,
               filter_difficulty=filter_difficulty,
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
               filter_subject=filter_subject,
               filter_difficulty=filter_difficulty,
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
               filter_subject=filter_subject,
               filter_difficulty=filter_difficulty,
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
               filter_subject=filter_subject,
               filter_difficulty=filter_difficulty,
           )
        )

    return render_template("admin/edit_question.html",
           question=question,
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
@admin_required
def delete_question(question_id):

    question = Question.query.get_or_404(question_id)

    page = request.form.get("page", 1, type=int)
    search = request.form.get("search", "")
    question_id = request.form.get("question_id", type=int)
    filter_topic = request.form.get("filter_topic", "")
    filter_subject = request.form.get("filter_subject", "")
    filter_difficulty = request.form.get("filter_difficulty", "")
    

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
            filter_subject=filter_subject,
            filter_difficulty=filter_difficulty,
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
            filter_topic=filter_topic,
            filter_subject=filter_subject,
            filter_difficulty=filter_difficulty, 
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
            filter_topic=filter_topic,
            filter_subject=filter_subject,
            filter_difficulty=filter_difficulty,
         )       
        ) 
    

# ======================================================
# BULK DELETE
# ======================================================

@questions_bp.route("/bulk-delete", methods=["POST"])
@admin_required
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

    try:

        for question_id in ids:


            try:
                question_id = int(question_id)

            except ValueError:
                print(" -> Invalid ID")
                skipped += 1
                continue

            question = db.session.get(Question, question_id)

            if not question:
                print(" -> Question not found")
                skipped += 1
                continue

            if (
                session.get("role") == "admin"
                and question.subject != session.get("subject")
            ):
                print(" -> Unauthorized")
                skipped += 1
                continue

            if question_has_dependencies(question.id):
                print(" -> Has dependencies")
                skipped += 1
                continue

            print(" -> Deleting")
            db.session.delete(question)
            deleted += 1

        print(f"\nDeleted={deleted}, Skipped={skipped}")

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
            filter_topic=filter_topic,
            filter_subject=filter_subject,
            filter_difficulty=filter_difficulty,
        )
    )


# ======================================================
# DELETE ALL UNUSED QUESTIONS
# ======================================================

@questions_bp.route("/delete-unused", methods=["POST"])
@admin_required
def delete_unused_questions():

    # --------------------------------------------------
    # Preserve current page and filters
    # --------------------------------------------------

    page = request.form.get("page", 1, type=int)
    search = request.form.get("search", "")
    topic = request.form.get("topic", "")
    filter_topic = request.form.get("filter_topic", "")
    filter_subject = request.form.get("filter_subject", "")
    question_id = request.args.get("question_id", type=int)
    filter_difficulty = request.form.get("filter_difficulty", "")
   

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
            question_id=question_id,
            filter_topic=filter_topic,
            subject=subject,
            difficulty=difficulty
        )
    )
    
    

# ======================================================
# BULK QUESTIONS UPLOAD
# ======================================================
    
    
@questions_bp.route("/bulk-upload", methods=["GET", "POST"])
@admin_required
def bulk_upload_questions():
    
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
        search = request.form.get("search", "")
        filter_topic = request.form.get("filter_topic", "")
        filter_subject = request.form.get("filter_subject", "")
        filter_difficulty = request.form.get("filter_difficulty", "") 

        # -----------------------------------------
        # Uploaded file
        # -----------------------------------------

        file = request.files.get("file")

        if not file or file.filename == "":
            
            flash("Please select a JSON file.", "warning")
            
            return redirect(url_for(
                        "questions.bulk_upload_questions",
                        page=page,
                        search=search,
                        filter_topic=filter_topic,
                        filter_subject=filter_subject,
                        filter_difficulty=filter_difficulty,
                    )
                )


        if not file.filename.lower().endswith(".json"):
            
            flash("Only JSON files are allowed.", "danger")
            
            return redirect(url_for(
                        "questions.bulk_upload_questions",
                        page=page,
                        search=search,
                        filter_topic=filter_topic,
                        filter_subject=filter_subject,
                        filter_difficulty=filter_difficulty,
                    )
                )


        try:

            questions = json.load(file)
            
            
            if not isinstance(questions, list):
                
                flash("JSON must contain a list of questions.", "danger")
                
                return redirect(url_for(
                        "questions.bulk_upload_questions",
                        page=page,
                        search=search,
                        filter_topic=filter_topic,
                        filter_subject=filter_subject,
                        filter_difficulty=filter_difficulty,
                    )
                )

            
                 
            if not questions:
                
                flash("The uploaded JSON file contains no questions.", "warning")
                
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
            

            

            # -----------------------------------------
            # Upload statistics variables
            # -----------------------------------------

            added = 0
            duplicates = 0
            invalid = 0
            errors = 0
            total = len(questions)


            # -----------------------------------------
            # Load all existing hashes once
            # -----------------------------------------

            existing_hashes = {row[0]
            for row in db.session.query(Question.question_hash)
            .filter(Question.question_hash.isnot(None)).all()

            }
            
            # -----------------------------------------
            # Process questions
            # -----------------------------------------


            for item in questions:

                if not isinstance(item, dict):
                    invalid += 1
                    continue

                topic = str(item.get("topic") or "").strip()
                question_subject = str(item.get("subject") or "").strip()
                question_difficulty = str(item.get("difficulty") or "").strip()
                question_text = str(item.get("question_text") or "").strip()
                option_a = str(item.get("option_a") or "").strip()
                option_b = str(item.get("option_b") or "").strip()
                option_c = str(item.get("option_c") or "").strip()
                option_d = str(item.get("option_d") or "").strip()
                correct_answer = str(item.get("correct_answer") or "").strip().upper()
                explanation = str(item.get("explanation") or "").strip()


                # -----------------------------------------
                # Restrict normal admins
                # -----------------------------------------

                if session.get("role") == "admin":
                    question_subject = session.get("subject")

                    if not question_subject:
                        flash("Your account has no assigned subject. Contact Super-Administrator (Bush)", "danger")
                        return redirect(url_for("questions.bulk_upload_questions"))
                                        
                                        
                # -----------------------------------------
                # Required fields
                # -----------------------------------------

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

                options = [
                    option_a.lower(),
                    option_b.lower(),
                    option_c.lower(),
                    option_d.lower()
                ]


                if len(set(options)) != 4:
                    invalid += 1
                    continue    


                if correct_answer not in [
                    "A",
                    "B",
                    "C",
                    "D"
                ]:
                    invalid += 1
                    continue         


                if question_difficulty not in [
                    "DOK_1",
                    "DOK_2",
                    "DOK_3",
                    "DOK_4"
                ]:
                    invalid += 1
                    continue      


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
                
                
                if question_hash in existing_hashes:
                    duplicates += 1
                    continue

                    
                question = Question(
                    topic=topic,
                    subject=question_subject,
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

                try:

                    with db.session.begin_nested():

                        db.session.add(question)
                        
                        db.session.flush()
                        
                    existing_hashes.add(question_hash)    

                    added += 1


                except SQLAlchemyError:
                    
                    
                    current_app.logger.exception(
                    f"Failed to import question. "
                    f"Subject={question_subject}, "
                    f"Topic={topic}, "
                    f"Question={question_text}")

                    errors += 1

                    continue

                                                                                       
            try:
                db.session.commit()


            except SQLAlchemyError:
                
                db.session.rollback()
                
                current_app.logger.exception("Bulk upload database commit failed.")

                flash("A database error occurred while saving the uploaded questions. Please try again.",
                      "danger")

                return redirect(url_for(
                    "questions.bulk_upload_questions",
                    page=page,
                    search=search,
                    filter_topic=filter_topic,
                    filter_subject=filter_subject,
                    filter_difficulty=filter_difficulty,
                )
                
                )
                
            # -----------------------------------------
            # Log upload summary
            # -----------------------------------------

            current_app.logger.info(
                f"Bulk upload completed. "
                f"Processed={total}, "
                f"Added={added}, "
                f"Duplicates={duplicates}, "
                f"Invalid={invalid}, "
                f"Errors={errors}"
            )
 

            flash(f"Processed {total} questions.", "info")
            
        
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
                            
                        
            return redirect(url_for(

                    "questions.view_questions",

                    page=page,

                    search=search,

                    filter_topic=filter_topic,

                    filter_subject=filter_subject,
                    
                    filter_difficulty=filter_difficulty,
                )

            ) 


        except json.JSONDecodeError:

            db.session.rollback()

            flash(
                "Invalid JSON file.",
                "danger"
            )
            
            
            return redirect(url_for(
                "questions.bulk_upload_questions",
                page=page,
                search=search,
                filter_topic=filter_topic,
                filter_subject=filter_subject,
                filter_difficulty=filter_difficulty, 
                )
            )
            

        except Exception as e:
                db.session.rollback()

                current_app.logger.exception("Unexpected bulk upload error.")

                flash(
                    f"Error reading file: {e}",
                    "danger"
                )
                        
                return redirect(url_for(
                    "questions.bulk_upload_questions",
                    page=page,
                    search=search,
                    filter_topic=filter_topic,
                    filter_subject=filter_subject,
                    filter_difficulty=filter_difficulty,
               )
             )
            
             

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
@admin_required
def export_questions():


    # -----------------------------------------
    # Preserve filters (optional)
    # -----------------------------------------

    page = request.args.get("page", 1, type=int)
    search = request.args.get("search", "")
    filter_topic = request.args.get("filter_topic", "")
    subject = request.args.get("subject", "")
    difficulty = request.args.get("difficulty", "")

    query = Question.query

    # -----------------------------------------
    # Restrict normal admins
    # -----------------------------------------

    if session.get("role") == "admin":

        subject = session.get("subject")

        query = query.filter_by(
            subject=subject
    )

    else:

        if subject:
           query = query.filter_by(subject=subject)

    if filter_topic:
        query = query.filter_by(topic=filter_topic)

    if difficulty:
        query = query.filter_by(difficulty=difficulty)


    questions = query.order_by(Question.topic, Question.id).all()

    # -----------------------------------------
    # Nothing to export
    # -----------------------------------------

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
            subject=subject,
            difficulty=difficulty,
        )
    )



    data = []

    for question in questions:

        data.append({

            "topic": question.topic,

            "subject": question.subject,

            "difficulty": question.difficulty,

            "question_text": question.question_text,

            "option_a": question.option_a,

            "option_b": question.option_b,

            "option_c": question.option_c,

            "option_d": question.option_d,

            "correct_answer": question.correct_answer,

            "explanation": question.explanation

        })

    json_data = json.dumps(
        data,
        indent=4,
        ensure_ascii=False
    )

    # -----------------------------------------
    # Generate filename
    # -----------------------------------------

    today = datetime.now().strftime("%Y-%m-%d")

    filename_parts = []

    if subject:
        filename_parts.append(subject.lower().replace(" ", "_"))

    if filter_topic:
        filename_parts.append(filter_topic.lower())

    if difficulty:
        filename_parts.append(difficulty.lower())

    if filename_parts:
        filename = "_".join(filename_parts)
    else:
        filename = "all_questions"

    filename = f"{filename}_{today}.json"


    return send_file(

        BytesIO(json_data.encode("utf-8")),

        mimetype="application/json",

        as_attachment=True,

        download_name=filename

    )
        
        