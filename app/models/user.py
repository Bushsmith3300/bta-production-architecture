# app/models/user.py

from app.extensions import db


class User(db.Model):

    __tablename__ = "users"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    username = db.Column(
        db.String(80),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(200),
        nullable=False
    )

    first_name = db.Column(
        db.String(100),
        nullable=False
    )

    surname = db.Column(
        db.String(100),
        nullable=False
    )

    other_name = db.Column(
        db.String(100),
        nullable=True
    )

    email = db.Column(
        db.String(200),
        unique=True,
        nullable=True
    )

    role = db.Column(
        db.String(20),
        default="student",
        nullable=False,
        index=True

    )

    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False,
        index=True
    )


    subject = db.Column(
        db.String(50),
        nullable=True
    )


    # ====================================
    # STUDENT SIDE RELATIONSHIPS
    # ====================================

    user_progress = db.relationship(
        "UserProgress",
        back_populates="user"
    )

    user_history = db.relationship(
        "UserHistory",
        back_populates="user"
    )

    assignment_submissions = db.relationship(
        "AssignmentSubmission",
        back_populates="student"
    )


    live_quiz_answers = db.relationship(
        "LiveQuizAnswer",
        back_populates="student",
        cascade="all, delete-orphan"
    )

    live_quiz_results = db.relationship(
        "LiveQuizResult",
        back_populates="student"
    )

    # ====================================
    # ADMIN SIDE RELATIONSHIPS
    # ====================================

    assignments_created = db.relationship(
        "Assignment",
        back_populates="admin"
    )

    live_class = db.relationship(
        "LiveClass",
        back_populates="admin",
        cascade="all, delete-orphan"
    )


    live_quiz_results = db.relationship(
       "LiveQuizResult",
       back_populates="student"
    )

    announcements_created = db.relationship(
       "Announcement",
       back_populates="admin"
    )


    # ====================================
    # OPTIONAL SUPER ADMIN FEATURES
    # ====================================

    quotes_created = db.relationship(
        "Quote",
        back_populates="admin"
    )

    def __repr__(self):
        return f"<User {self.username}>"