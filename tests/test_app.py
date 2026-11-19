def test_basic_python_operation():
    result = 10 + 5

    assert result == 15


def test_app_uses_separate_test_database(app):
    assert app.config["TESTING"] is True

    assert app.config["SQLALCHEMY_DATABASE_URI"] == "sqlite://"

    with app.app_context():
        from app.extensions import db

        assert db.engine.dialect.name == "sqlite"


def test_app_has_maximum_upload_size(app):
    assert app.config["MAX_CONTENT_LENGTH"] == 5 * 1024 * 1024
