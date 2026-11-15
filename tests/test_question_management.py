from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import User, Subject, Question
from app.utils.question_hash import generate_question_hash


# ======================================================
# TEST HELPERS
# ======================================================

def create_subject(name, code, is_active=True):
    subject = Subject(
        name=name,
        code=code,
        is_active=is_active
    )

    db.session.add(subject)
    db.session.commit()

    return subject


def create_test_user(username, role="super_admin", subject=None):
    user = User(
        username=username,
        password=generate_password_hash("testpass123"),
        first_name="Test",
        surname="User",
        role=role,
        subject=subject,
        is_active=True
    )

    db.session.add(user)
    db.session.commit()

    return user


def login_user(client, user):
    with client.session_transaction() as session:
        session["user_id"] = user.id
        session["username"] = user.username
        session["role"] = user.role

        if user.subject:
            session["subject"] = user.subject


def valid_question_data(subject="Chemistry"):
    return {
        "topic": "Atomic Structure",
        "subject": subject,
        "difficulty": "DOK_1",
        "question_text": "What is the charge of a proton?",
        "option_a": "Positive charge",
        "option_b": "Negative charge",
        "option_c": "No charge",
        "option_d": "Variable charge",
        "correct_answer": "A",
        "explanation": "A proton carries a positive electrical charge.",
    }


# ======================================================
# QUESTION CREATION TESTS
# ======================================================

def test_question_is_saved_with_correct_subject_id(question_client):

    subject = create_subject("Chemistry", "CHEM")

    admin = create_test_user("question_super_admin")

    login_user(question_client, admin)

    response = question_client.post(
        "/admin/questions/add",
        data=valid_question_data(),
        follow_redirects=False
    )

    assert response.status_code == 302

    question = Question.query.filter_by(
        question_text="What is the charge of a proton?"
    ).first()

    assert question is not None
    assert question.subject == "Chemistry"
    assert question.subject_id == subject.id
    assert question.subject_ref.name == "Chemistry"


def test_question_with_invalid_subject_is_rejected(question_client):

    admin = create_test_user("invalid_subject_admin")

    login_user(question_client, admin)

    response = question_client.post(
        "/admin/questions/add",
        data=valid_question_data("Unknown Subject"),
        follow_redirects=False
    )

    assert response.status_code == 302

    assert Question.query.count() == 0


def test_question_with_inactive_subject_is_rejected(question_client):

    create_subject(
        "Chemistry",
        "CHEM",
        is_active=False
    )

    admin = create_test_user("inactive_subject_admin")

    login_user(question_client, admin)

    response = question_client.post(
        "/admin/questions/add",
        data=valid_question_data(),
        follow_redirects=False
    )

    assert response.status_code == 302

    assert Question.query.count() == 0


def test_duplicate_question_is_rejected(question_client):

    subject = create_subject("Chemistry", "CHEM")

    admin = create_test_user("duplicate_question_admin")

    login_user(question_client, admin)

    data = valid_question_data()

    question_hash = generate_question_hash(
        topic=data["topic"],
        subject=subject.name,
        question_text=data["question_text"],
        option_a=data["option_a"],
        option_b=data["option_b"],
        option_c=data["option_c"],
        option_d=data["option_d"],
        correct_answer=data["correct_answer"],
    )

    existing_question = Question(
        topic=data["topic"],
        subject=subject.name,
        subject_id=subject.id,
        difficulty=data["difficulty"],
        question_text=data["question_text"],
        option_a=data["option_a"],
        option_b=data["option_b"],
        option_c=data["option_c"],
        option_d=data["option_d"],
        correct_answer=data["correct_answer"],
        explanation=data["explanation"],
        question_hash=question_hash
    )

    db.session.add(existing_question)
    db.session.commit()

    response = question_client.post(
        "/admin/questions/add",
        data=data,
        follow_redirects=False
    )

    assert response.status_code == 302

    assert Question.query.count() == 1


# ======================================================
# TOPIC ACCESS CONTROL TESTS
# ======================================================

def create_question_for_subject(subject, topic, hash_character):

    question = Question(
        topic=topic,
        subject=subject.name,
        subject_id=subject.id,
        difficulty="DOK_1",
        question_text=f"Test question for {topic}",
        option_a="Option A",
        option_b="Option B",
        option_c="Option C",
        option_d="Option D",
        correct_answer="A",
        explanation="Test explanation",
        question_hash=hash_character * 64
    )

    db.session.add(question)
    db.session.commit()

    return question


def test_admin_can_access_topics_for_assigned_subject(question_client):

    chemistry = create_subject("Chemistry", "CHEM")
    create_question_for_subject(
        chemistry, "Atomic Structure", "a"
    )

    admin = create_test_user(
        "chemistry_topic_admin",
        role="admin",
        subject="Chemistry"
    )

    login_user(question_client, admin)

    response = question_client.get(
        f"/admin/questions/topics/{chemistry.id}"
    )

    assert response.status_code == 200
    assert "Atomic Structure" in response.json["topics"]


def test_admin_cannot_access_another_subject_topics(question_client):

    create_subject("Chemistry", "CHEM")
    physics = create_subject("Physics", "PHYS")

    create_question_for_subject(
        physics, "Mechanics", "b"
    )

    admin = create_test_user(
        "chemistry_restricted_admin",
        role="admin",
        subject="Chemistry"
    )

    login_user(question_client, admin)

    response = question_client.get(
        f"/admin/questions/topics/{physics.id}"
    )

    assert response.status_code == 403
    assert "error" in response.json


def test_super_admin_can_access_another_subject_topics(question_client):

    chemistry = create_subject("Chemistry", "CHEM")
    physics = create_subject("Physics", "PHYS")

    create_question_for_subject(
        physics, "Mechanics", "c"
    )

    admin = create_test_user(
        "super_topic_admin",
        role="super_admin"
    )

    login_user(question_client, admin)

    response = question_client.get(
        f"/admin/questions/topics/{physics.id}"
    )

    assert response.status_code == 200
    assert "Mechanics" in response.json["topics"]


# ======================================================
# QUESTION VIEW ACCESS CONTROL TESTS
# ======================================================


def test_admin_can_view_question_from_assigned_subject(question_client):

    chemistry = create_subject("Chemistry", "CHEM")

    question = create_question_for_subject(
        chemistry,
        "Atomic Structure",
        "d"
    )

    admin = create_test_user(
        "chemistry_view_admin",
        role="admin",
        subject="Chemistry"
    )

    login_user(question_client, admin)

    response = question_client.get(
        f"/admin/questions/view/{question.id}"
    )

    assert response.status_code == 200

    assert question.question_text.encode("utf-8") in response.data


def test_admin_cannot_view_question_from_another_subject(question_client):

    physics = create_subject("Physics", "PHYS")

    question = create_question_for_subject(
        physics,
        "Mechanics",
        "e"
    )

    admin = create_test_user(
        "chemistry_view_restricted_admin",
        role="admin",
        subject="Chemistry"
    )

    create_subject("Chemistry", "CHEM")

    login_user(question_client, admin)

    response = question_client.get(
        f"/admin/questions/view/{question.id}"
    )

    assert response.status_code == 302
    assert "/admin/questions" in response.location


def test_super_admin_can_view_question_from_another_subject(question_client):

    physics = create_subject("Physics", "PHYS")

    question = create_question_for_subject(
        physics,
        "Mechanics",
        "f"
    )

    admin = create_test_user(
        "super_view_admin",
        role="super_admin"
    )

    login_user(question_client, admin)

    response = question_client.get(
        f"/admin/questions/view/{question.id}"
    )

    assert response.status_code == 200


# ======================================================
# QUESTION EDITING TESTS
# ======================================================

def test_super_admin_can_edit_question(question_client):

    chemistry = create_subject("Chemistry", "CHEM")

    question = create_question_for_subject(
        chemistry,
        "Atomic Structure",
        "g"
    )

    admin = create_test_user(
        "super_edit_admin",
        role="super_admin"
    )

    login_user(question_client, admin)

    data = valid_question_data()
    data["subject"] = str(chemistry.id)
    data["question_text"] = "What is the relative charge of a proton?"
    data["explanation"] = "A proton has a positive charge."

    response = question_client.post(
        f"/admin/questions/edit/{question.id}",
        data=data,
        follow_redirects=False
    )

    assert response.status_code == 302

    db.session.refresh(question)

    assert question.question_text == (
        "What is the relative charge of a proton?"
    )

    assert question.explanation == (
        "A proton has a positive charge."
    )

    assert question.subject_id == chemistry.id

    expected_hash = generate_question_hash(
        topic=data["topic"],
        subject=chemistry.name,
        question_text=data["question_text"],
        option_a=data["option_a"],
        option_b=data["option_b"],
        option_c=data["option_c"],
        option_d=data["option_d"],
        correct_answer=data["correct_answer"]
    )

    assert question.question_hash == expected_hash


def test_admin_can_edit_question_from_assigned_subject(question_client):

    chemistry = create_subject("Chemistry", "CHEM")

    question = create_question_for_subject(
        chemistry,
        "Atomic Structure",
        "h"
    )

    admin = create_test_user(
        "chemistry_edit_admin",
        role="admin",
        subject="Chemistry"
    )

    login_user(question_client, admin)

    data = valid_question_data()
    data["question_text"] = "What is the charge of an electron?"

    response = question_client.post(
        f"/admin/questions/edit/{question.id}",
        data=data,
        follow_redirects=False
    )

    assert response.status_code == 302

    db.session.refresh(question)

    assert question.question_text == (
        "What is the charge of an electron?"
    )

    assert question.subject_id == chemistry.id


def test_admin_cannot_edit_question_from_another_subject(question_client):

    chemistry = create_subject("Chemistry", "CHEM")
    physics = create_subject("Physics", "PHYS")

    question = create_question_for_subject(
        physics,
        "Mechanics",
        "i"
    )

    admin = create_test_user(
        "restricted_edit_admin",
        role="admin",
        subject="Chemistry"
    )

    login_user(question_client, admin)

    original_text = question.question_text

    data = valid_question_data()
    data["question_text"] = "Unauthorized modification attempt."

    response = question_client.post(
        f"/admin/questions/edit/{question.id}",
        data=data,
        follow_redirects=False
    )

    assert response.status_code == 302

    db.session.refresh(question)

    assert question.question_text == original_text
    assert question.subject_id == physics.id


def test_edit_nonexistent_question_returns_404(question_client):

    admin = create_test_user(
        "missing_question_edit_admin",
        role="super_admin"
    )

    login_user(question_client, admin)

    response = question_client.get(
        "/admin/questions/edit/999999"
    )

    assert response.status_code == 404


def test_edit_rejects_duplicate_options_without_modifying_question(
    question_client
):

    chemistry = create_subject("Chemistry", "CHEM")

    question = create_question_for_subject(
        chemistry,
        "Atomic Structure",
        "j"
    )

    admin = create_test_user(
        "duplicate_options_edit_admin",
        role="super_admin"
    )

    login_user(question_client, admin)

    original_text = question.question_text

    data = valid_question_data()
    data["subject"] = str(chemistry.id)
    data["question_text"] = "This question should not be saved."
    data["option_b"] = data["option_a"]

    response = question_client.post(
        f"/admin/questions/edit/{question.id}",
        data=data,
        follow_redirects=False
    )

    assert response.status_code == 302

    db.session.refresh(question)

    assert question.question_text == original_text


# ======================================================
# QUESTION DELETION TESTS
# ======================================================

def test_super_admin_can_delete_unused_question(
    question_client, monkeypatch
):
    import app.admin.questions_management as question_module

    chemistry = create_subject("Chemistry", "CHEM")

    question = create_question_for_subject(
        chemistry, "Atomic Structure", "k"
    )

    admin = create_test_user(
        "super_delete_admin",
        role="super_admin"
    )

    login_user(question_client, admin)

    monkeypatch.setattr(
        question_module,
        "question_has_dependencies",
        lambda question_id: False
    )

    response = question_client.post(
        f"/admin/questions/delete/{question.id}",
        follow_redirects=False
    )

    assert response.status_code == 302
    assert db.session.get(Question, question.id) is None


def test_admin_can_delete_question_from_assigned_subject(
    question_client, monkeypatch
):
    import app.admin.questions_management as question_module

    chemistry = create_subject("Chemistry", "CHEM")

    question = create_question_for_subject(
        chemistry, "Atomic Structure", "l"
    )

    admin = create_test_user(
        "chemistry_delete_admin",
        role="admin",
        subject="Chemistry"
    )

    login_user(question_client, admin)

    monkeypatch.setattr(
        question_module,
        "question_has_dependencies",
        lambda question_id: False
    )

    response = question_client.post(
        f"/admin/questions/delete/{question.id}",
        follow_redirects=False
    )

    assert response.status_code == 302
    assert db.session.get(Question, question.id) is None



def test_admin_cannot_delete_question_from_another_subject(
    question_client, monkeypatch
):
    import app.admin.questions_management as question_module

    chemistry = create_subject("Chemistry", "CHEM")
    physics = create_subject("Physics", "PHYS")

    question = create_question_for_subject(
        physics, "Mechanics", "m"
    )

    admin = create_test_user(
        "restricted_delete_admin",
        role="admin",
        subject="Chemistry"
    )

    login_user(question_client, admin)

    monkeypatch.setattr(
        question_module,
        "question_has_dependencies",
        lambda question_id: False
    )

    original_text = question.question_text

    response = question_client.post(
        f"/admin/questions/delete/{question.id}",
        follow_redirects=False
    )

    assert response.status_code == 302

    db.session.refresh(question)

    assert question.question_text == original_text
    assert question.subject_id == physics.id


def test_delete_nonexistent_question_returns_404(question_client):

    admin = create_test_user(
        "missing_question_delete_admin",
        role="super_admin"
    )

    login_user(question_client, admin)

    response = question_client.post(
        "/admin/questions/delete/999999",
        follow_redirects=False
    )

    assert response.status_code == 404


def test_question_with_dependencies_cannot_be_deleted(
    question_client, monkeypatch
):
    import app.admin.questions_management as question_module

    chemistry = create_subject("Chemistry", "CHEM")

    question = create_question_for_subject(
        chemistry, "Atomic Structure", "n"
    )

    admin = create_test_user(
        "dependent_question_admin",
        role="super_admin"
    )

    login_user(question_client, admin)

    monkeypatch.setattr(
        question_module,
        "question_has_dependencies",
        lambda question_id: True
    )

    response = question_client.post(
        f"/admin/questions/delete/{question.id}",
        follow_redirects=False
    )

    assert response.status_code == 302

    db.session.refresh(question)

    assert question.id is not None
    assert Question.query.filter_by(id=question.id).first() is not None