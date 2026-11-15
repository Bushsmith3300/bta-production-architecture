from werkzeug.security import generate_password_hash

from app.extensions import db
from app.models import User


def create_test_user(
    username,
    role="student",
    subject=None,
    is_active=True
):
    user = User(
        username=username,
        password=generate_password_hash("testpass123"),
        first_name="Test",
        surname="User",
        role=role,
        subject=subject,
        is_active=is_active
    )

    db.session.add(user)
    db.session.commit()

    return user


def set_login_session(client, user):
    with client.session_transaction() as session:
        session["user_id"] = user.id
        session["username"] = user.username
        session["role"] = user.role


def test_unauthenticated_user_cannot_access_student_dashboard(auth_client):
    response = auth_client.get("/dashboard")

    assert response.status_code == 302
    assert "/login" in response.location


def test_unauthenticated_user_cannot_access_admin_dashboard(auth_client):
    response = auth_client.get("/admin/")

    assert response.status_code == 302
    assert "/login" in response.location


def test_unauthenticated_user_cannot_access_super_admin_dashboard(auth_client):
    response = auth_client.get("/super-admin/")

    assert response.status_code == 302
    assert "/login" in response.location


def test_student_cannot_access_super_admin_dashboard(auth_client):
    student = create_test_user("auth_student")
    set_login_session(auth_client, student)

    response = auth_client.get("/super-admin/")

    assert response.status_code == 302
    assert "/dashboard" in response.location


def test_regular_admin_cannot_access_super_admin_dashboard(auth_client):
    admin = create_test_user(
        "auth_admin",
        role="admin",
        subject="Chemistry"
    )

    set_login_session(auth_client, admin)

    response = auth_client.get("/super-admin/")

    assert response.status_code == 302
    assert "/dashboard" in response.location


def test_student_cannot_access_admin_dashboard(auth_client):
    student = create_test_user("auth_student_admin")
    set_login_session(auth_client, student)

    response = auth_client.get("/admin/")

    assert response.status_code == 302
    assert "/dashboard" in response.location


def test_suspended_user_existing_session_is_cleared(auth_client):
    user = create_test_user(
        "suspended_user",
        is_active=False
    )

    set_login_session(auth_client, user)

    response = auth_client.get("/dashboard")

    assert response.status_code == 302
    assert "/login" in response.location

    with auth_client.session_transaction() as session:
        assert "user_id" not in session


def test_nonexistent_user_existing_session_is_cleared(auth_client):

    with auth_client.session_transaction() as session:
        session["user_id"] = 999999
        session["username"] = "deleted_user"
        session["role"] = "student"

    response = auth_client.get("/dashboard")

    assert response.status_code == 302
    assert "/login" in response.location

    with auth_client.session_transaction() as session:
        assert "user_id" not in session
        assert "username" not in session
        assert "role" not in session