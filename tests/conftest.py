import pytest

from app import create_app
from app.extensions import db
from app.models import (
    User,
    UserProgress,
    Subject,
    Question
)

@pytest.fixture
def app():
    test_app = create_app({
        "TESTING": True,
        "SECRET_KEY": "test-secret-key",
        "SQLALCHEMY_DATABASE_URI": "sqlite://",
        "SQLALCHEMY_ENGINE_OPTIONS": {},
        "WTF_CSRF_ENABLED": False,
    })

    yield test_app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(app):
    tables = [
        User.__table__,
        UserProgress.__table__,
    ]

    with app.app_context():
        db.metadata.create_all(
            bind=db.engine,
            tables=tables
        )

        yield app.test_client()

        db.session.remove()

        db.metadata.drop_all(
            bind=db.engine,
            tables=tables
        )


@pytest.fixture
def question_client(app):

    tables = [
        User.__table__,
        UserProgress.__table__,
        Subject.__table__,
        Question.__table__,
    ]

    with app.app_context():

        db.metadata.create_all(
            bind=db.engine,
            tables=tables
        )

        yield app.test_client()

        db.session.remove()

        db.metadata.drop_all(
            bind=db.engine,
            tables=tables
        )