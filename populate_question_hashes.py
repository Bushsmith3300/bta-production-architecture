from app import create_app
from app.extensions import db
from app.models import Question
from app.utils.question_hash import generate_question_hash

app = create_app()

with app.app_context():

    questions = Question.query.all()

    print(f"Found {len(questions)} questions.")

    updated = 0

    for question in questions:

        question.question_hash = generate_question_hash(
            topic=question.topic,
            question_text=question.question_text,
            option_a=question.option_a,
            option_b=question.option_b,
            option_c=question.option_c,
            option_d=question.option_d,
            correct_answer=question.correct_answer,
            subject=question.subject,
        )

        updated += 1

    db.session.commit()

    print(f"Updated {updated} questions successfully.")