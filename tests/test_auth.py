from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db
from app.models import User, UserProgress


def test_student_registration(auth_client):
    response = auth_client.post(
        "/register",
        data={
            "username": "student01",
            "password": "secret123",
            "confirm_password": "secret123",
            "first_name": "John",
            "surname": "Mensah",
            "other_name": "Kofi"
        }
    )

    assert response.status_code == 302
    assert response.location.endswith("/login")

    user = User.query.filter_by(username="student01").first()

    assert user is not None
    assert user.first_name == "John"
    assert user.surname == "Mensah"
    assert user.role == "student"
    assert user.is_active is True

    # Confirm that the password is hashed.
    assert user.password != "secret123"
    assert check_password_hash(user.password, "secret123")

    # Confirm that a progress record was created.
    progress = UserProgress.query.filter_by(
        user_id=user.id
    ).first()

    assert progress is not None


def test_registration_rejects_short_username(auth_client):
    response = auth_client.post(
        "/register",
        data={
            "username": "ab",
            "password": "secret123",
            "confirm_password": "secret123",
            "first_name": "John",
            "surname": "Mensah"
        }
    )

    assert response.status_code == 302
    assert response.location.endswith("/register")

    assert User.query.filter_by(username="ab").first() is None


def test_registration_rejects_short_password(auth_client):
    response = auth_client.post(
        "/register",
        data={
            "username": "student02",
            "password": "123",
            "confirm_password": "123",
            "first_name": "John",
            "surname": "Mensah"
        }
    )

    assert response.status_code == 302
    assert response.location.endswith("/register")

    assert User.query.filter_by(username="student02").first() is None


def test_registration_rejects_password_mismatch(auth_client):
    response = auth_client.post(
        "/register",
        data={
            "username": "student03",
            "password": "secret123",
            "confirm_password": "different123",
            "first_name": "John",
            "surname": "Mensah"
        }
    )

    assert response.status_code == 302
    assert response.location.endswith("/register")

    assert User.query.filter_by(username="student03").first() is None


def test_student_login(auth_client):
    user = User(
        username="student04",
        password=generate_password_hash("secret123"),
        first_name="Ama",
        surname="Boateng"
    )

    db.session.add(user)
    db.session.commit()

    response = auth_client.post(
        "/login",
        data={
            "username": "student04",
            "password": "secret123"
        }
    )

    assert response.status_code == 302
    assert response.location.endswith("/dashboard")

    with auth_client.session_transaction() as session:
        assert session["user_id"] == user.id
        assert session["username"] == "student04"
        assert session["role"] == "student"


def test_login_rejects_incorrect_password(auth_client):
    user = User(
        username="student05",
        password=generate_password_hash("secret123"),
        first_name="Kojo",
        surname="Asare"
    )

    db.session.add(user)
    db.session.commit()

    response = auth_client.post(
        "/login",
        data={
            "username": "student05",
            "password": "wrongpassword"
        }
    )

    assert response.status_code == 302
    assert response.location.endswith("/login")

    with auth_client.session_transaction() as session:
        assert "user_id" not in session


def test_suspended_student_cannot_login(auth_client):
    user = User(
        username="student06",
        password=generate_password_hash("secret123"),
        first_name="Akosua",
        surname="Owusu",
        is_active=False
    )

    db.session.add(user)
    db.session.commit()

    response = auth_client.post(
        "/login",
        data={
            "username": "student06",
            "password": "secret123"
        }
    )

    assert response.status_code == 302
    assert response.location.endswith("/login")

    with auth_client.session_transaction() as session:
        assert "user_id" not in session


def test_logout_clears_session(auth_client):
    with auth_client.session_transaction() as session:
        session["user_id"] = 10
        session["username"] = "student07"
        session["role"] = "student"

    response = auth_client.get("/logout")

    assert response.status_code == 302
    assert response.location.endswith("/login")

    with auth_client.session_transaction() as session:
        assert "user_id" not in session
        assert "username" not in session
        assert "role" not in session